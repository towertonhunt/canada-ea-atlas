#!/usr/bin/env python3
"""Spatial Baseline Engine v0 — query Ontario LIO layers around a site.

Usage: python3 scripts/baseline_query.py <lat> <lon> [buffer_m]
Produces a constraints report: which baseline layers intersect the buffered
site, with feature counts and sample attributes. Needs open internet
(run in GitHub Actions or any unrestricted environment).
"""
import json
import sys
import urllib.parse
import urllib.request

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'

# LIO open data service roots discovered via GeoHub DCAT (data/raw/on_geohub_layers.json).
# Each entry: (label, service_or_layer_url, discipline_triggers)
LAYERS = [
    ('Wetland', 'wetland', ['wetlands', 'surface_water']),
    ('ANSI', 'areas of natural and scientific interest', ['vegetation_ecosystems', 'species_at_risk']),
    ('Natural Heritage System Area', 'natural heritage system area', ['vegetation_ecosystems']),
    ('First Nation Reserve', 'first nation reserve', ['indigenous_engagement']),
    ('Conservation reserve', 'conservation reserve regulated', ['vegetation_ecosystems']),
    ('OHN Waterbody', 'waterbody', ['fish_habitat', 'surface_water']),
    ('OHN Watercourse', 'watercourse', ['fish_habitat', 'surface_water']),
    ('Aggregate site (active)', 'aggregate site authorized - active', ['cumulative_effects']),
]


def http_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    body = urllib.request.urlopen(req, timeout=90).read()
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        raise RuntimeError(f'non-JSON response: {body[:150]!r}')


def resolve_layer_urls(catalog_path='data/raw/on_geohub_layers.json'):
    """Map our layer labels to concrete .../MapServer/<id> query URLs."""
    cat = json.load(open(catalog_path))
    resolved = {}
    for label, match, triggers in LAYERS:
        for entry in cat:
            if (entry['title'] or '').strip().lower() != match and \
               match not in (entry['title'] or '').lower():
                continue
            for rest in entry.get('rest') or []:
                if not rest or 'arcgis' not in rest.lower():
                    continue
                base = rest.split('?')[0].rstrip('/')
                try:
                    if base.endswith(('MapServer', 'FeatureServer')):
                        meta = http_json(base + '?f=json')
                        for lyr in meta.get('layers', []):
                            if match.split(' ')[0].lower() in lyr['name'].lower():
                                resolved[label] = (f"{base}/{lyr['id']}", triggers)
                                break
                        else:
                            if meta.get('layers'):
                                lyr = meta['layers'][0]
                                resolved[label] = (f"{base}/{lyr['id']}", triggers)
                    else:
                        resolved[label] = (base, triggers)
                except Exception as e:
                    print(f'  resolve fail {label}: {str(e)[:80]}', file=sys.stderr)
            if label in resolved:
                break
    return resolved


def query_layer(layer_url, lat, lon, buffer_m):
    # Buffer client-side as an envelope: many LIO MapServer layers silently
    # ignore the distance/units params, which made every query degenerate to
    # a point-in-polygon test and return 0 features.
    import math
    dlat = buffer_m / 111320.0
    dlon = buffer_m / (111320.0 * max(0.1, math.cos(math.radians(lat))))
    params = {
        'f': 'json',
        # simple comma syntax — the JSON-object form drew HTML error pages
        # from the LIO servers
        'geometry': f'{lon - dlon},{lat - dlat},{lon + dlon},{lat + dlat}',
        'geometryType': 'esriGeometryEnvelope',
        'inSR': 4326,
        'spatialRel': 'esriSpatialRelIntersects',
        'outFields': '*',
        'returnGeometry': 'false',
        'resultRecordCount': 5,
    }
    return http_json(layer_url + '/query?' + urllib.parse.urlencode(params))


def main():
    lat, lon = float(sys.argv[1]), float(sys.argv[2])
    buffer_m = int(sys.argv[3]) if len(sys.argv) > 3 else 500
    print(f'Site: {lat}, {lon}  buffer {buffer_m} m')
    resolved = resolve_layer_urls()
    print(f'resolved {len(resolved)}/{len(LAYERS)} layers\n')
    report = {'site': [lat, lon], 'buffer_m': buffer_m, 'constraints': []}
    for label, (url, triggers) in resolved.items():
        try:
            d = query_layer(url, lat, lon, buffer_m)
            feats = d.get('features', [])
            hit = len(feats) > 0
            print(f'{"HIT " if hit else "    "} {label}: {len(feats)} feature(s)')
            if hit:
                sample = {k: v for k, v in list(feats[0]['attributes'].items())[:6]}
                report['constraints'].append({'layer': label, 'count': len(feats),
                                              'disciplines': triggers,
                                              'sample': sample, 'source': url})
        except Exception as e:
            print(f'ERR  {label}: {str(e)[:100]}')
    out = 'data/raw/baseline_demo_report.json'
    json.dump(report, open(out, 'w'), ensure_ascii=False, indent=1)
    print(f'\nreport -> {out}')
    print('disciplines triggered:',
          sorted({t for c in report['constraints'] for t in c['disciplines']}))


if __name__ == '__main__':
    main()
