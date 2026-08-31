#!/usr/bin/env python3
"""Wawa-Timmins routing engine v0 — cost surface + least-cost paths.

Reproduces the MCDM routing method from public data: rasterize weighted
constraint layers per routing/framework.json, run least-cost-path from
Wawa TS to Porcupine TS, generate alternatives by path penalization.

Requires: numpy, shapely>=2.0, scikit-image, pyproj (pip install in runner).
Outputs: routing/results/route_v0_*.geojson + stats.json
"""
import json
import math
import os

import numpy as np
from pyproj import Transformer
from shapely.geometry import shape, Point, LineString
from shapely.strtree import STRtree
from skimage import graph

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FW = json.load(open(os.path.join(ROOT, 'routing', 'framework.json')))
LAYERS_DIR = os.path.join(ROOT, 'routing', 'layers')
OUT_DIR = os.path.join(ROOT, 'routing', 'results')

CELL = FW.get('cell_m', 200) * 1.5  # 300 m grid for v0 speed
FB_VALUE = 14000.0
T = Transformer.from_crs(4326, 32617, always_xy=True)   # UTM 17N
T_INV = Transformer.from_crs(32617, 4326, always_xy=True)

aoi = FW['aoi']
x0, y0 = T.transform(aoi['lon_min'], aoi['lat_min'])
x1, y1 = T.transform(aoi['lon_max'], aoi['lat_max'])
nx, ny = int((x1 - x0) / CELL), int((y1 - y0) / CELL)
print(f'grid: {nx} x {ny} = {nx*ny:,} cells at {CELL:.0f} m')

# cell centers (projected)
xs = x0 + (np.arange(nx) + 0.5) * CELL
ys = y0 + (np.arange(ny) + 0.5) * CELL


def project_geoms(gj):
    geoms = []
    for f in gj['features']:
        try:
            g = shape(f['geometry'])
            if g.is_empty:
                continue
            geoms.append(transform_geom(g))
        except Exception:
            continue
    return geoms


def transform_geom(g):
    from shapely.ops import transform as sh_transform
    return sh_transform(lambda x, y, z=None: T.transform(x, y), g)


def burn(mask_grid, geoms, value, buffer_m=0):
    """Add `value` to cells whose center intersects geoms (buffered)."""
    if not geoms:
        return
    if buffer_m:
        geoms = [g.buffer(buffer_m) for g in geoms]
    tree = STRtree(geoms)
    pts_x, pts_y = np.meshgrid(xs, ys)
    pts = [Point(px, py) for px, py in
           zip(pts_x.ravel(), pts_y.ravel())]
    # STRtree bulk query: which points fall in geometry bounding boxes
    idx = tree.query(pts, predicate='intersects')
    hit_cells = np.unique(idx[0])
    flat = mask_grid.ravel()
    flat[hit_cells] += value
    print(f'    burned {len(hit_cells):,} cells @ {value:+}')


def main():
    weights = FW['category_weights']
    cost = np.zeros((ny, nx), dtype=np.float64)

    for spec in FW['layers']:
        path = os.path.join(LAYERS_DIR, f"{spec['key']}.geojson")
        geoms = []
        if spec.get('local'):
            # AMIS points from parsed JSON
            recs = json.load(open(os.path.join(ROOT, spec['local'])))
            geoms = [Point(*T.transform(r['lon'], r['lat'])) for r in recs
                     if aoi['lon_min'] < r['lon'] < aoi['lon_max']
                     and aoi['lat_min'] < r['lat'] < aoi['lat_max']]
        elif os.path.exists(path):
            gj = json.load(open(path))
            geoms = project_geoms(gj)
        if not geoms:
            print(f'  {spec["key"]}: no geometry, skipped')
            continue
        w = sum(weights[c] for c in spec['categories'])
        res = spec['resistance']
        val = FB_VALUE if res == 'FB' else float(res) * w
        print(f'  {spec["key"]}: {len(geoms):,} geoms, weight {w:.2f}')
        burn(cost, geoms, val, spec.get('ring_m', 0) if res == 'FB' else 0)
        for ring in spec.get('rings', []):
            burn(cost, geoms, float(ring['resistance']) *
                 sum(weights[c] for c in spec['categories']),
                 ring['buffer_m'])

    # shift to strictly positive for MCP; keep relative structure
    base = cost - cost.min() + 1.0
    np.save(os.path.join(OUT_DIR, 'cost_surface.npy'), base.astype(np.float32))

    def cell_of(lon, lat):
        px, py = T.transform(lon, lat)
        return (int((py - y0) / CELL), int((px - x0) / CELL))

    start = cell_of(FW['start']['lon'], FW['start']['lat'])
    end = cell_of(FW['end']['lon'], FW['end']['lat'])
    print('start cell:', start, 'end cell:', end)

    os.makedirs(OUT_DIR, exist_ok=True)
    routes = []
    work = base.copy()
    for k in range(3):
        mcp = graph.MCP_Geometric(work)
        costs, _ = mcp.find_costs([start], [end])
        path = mcp.traceback(end)
        coords = [T_INV.transform(x0 + (c + 0.5) * CELL, y0 + (r + 0.5) * CELL)
                  for r, c in path]
        line = LineString(coords)
        length_km = sum(
            haversine(coords[i], coords[i + 1]) for i in range(len(coords) - 1))
        resist = float(np.mean([base[r, c] for r, c in path]))
        routes.append({'type': 'Feature',
                       'geometry': json.loads(json.dumps(line.__geo_interface__)),
                       'properties': {'route': f'V{k+1}',
                                      'length_km': round(length_km, 1),
                                      'mean_resistance': round(resist, 1),
                                      'cells': len(path)}})
        print(f'route V{k+1}: {length_km:.1f} km, mean resistance {resist:.1f}')
        # penalize a corridor around this path to force a distinct alternative
        for r, c in path:
            rr0, rr1 = max(0, r - 5), min(ny, r + 6)
            cc0, cc1 = max(0, c - 5), min(nx, c + 6)
            work[rr0:rr1, cc0:cc1] *= 1.35

    json.dump({'type': 'FeatureCollection', 'features': routes},
              open(os.path.join(OUT_DIR, 'routes_v0.geojson'), 'w'))
    json.dump({'grid': [nx, ny], 'cell_m': CELL,
               'routes': [r['properties'] for r in routes]},
              open(os.path.join(OUT_DIR, 'stats.json'), 'w'), indent=1)
    print('done -> routing/results/routes_v0.geojson')


def haversine(a, b):
    lon1, lat1, lon2, lat2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    h = (math.sin((lat2 - lat1) / 2) ** 2 +
         math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 6371.0 * 2 * math.asin(math.sqrt(h))


if __name__ == '__main__':
    os.makedirs(OUT_DIR, exist_ok=True)
    main()
