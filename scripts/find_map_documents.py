#!/usr/bin/env python3
"""Find the documents that carry project footprints and layouts.

Scans every document catalogue we hold (data/docs/<jur>/*.json plus the
inline doc_sections on Ontario REA features) and classifies documents whose
title or filename says they are maps, figures, site plans, general
arrangements or GIS data. Output: data/raw/map_docs_index.json

  {
    "summary": {...counts by kind and jurisdiction...},
    "projects": {
      "<pid>": {"name":..., "jurisdiction":..., "docs": [
          {"kind": "gis_data|site_plan|layout|location_map|figure",
           "title":..., "url":..., "archive_url":..., "date":...}]}
    },
    "gis_queue": [ {pid, url, title, ext} ... ]   # KML/KMZ/SHP/zip/GeoJSON etc.
  }

Two consumers:
  * index.html hoists the same kinds into a "Maps & drawings" section of the
    sidebar (client-side, same regexes ported to JS -- keep MAP_KINDS in sync)
  * build_footprints.py --source gis downloads gis_queue files in the lane
    and converts them to footprints (the only path that yields geometry from
    documents without georeferencing figures).

Pure standard library. Run: python3 scripts/find_map_documents.py
"""
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from footprints_common import ROOT, fold, make_id  # noqa: E402

GEOJSON = os.path.join(ROOT, 'data', 'projects_canada.geojson')
OUT = os.path.join(ROOT, 'data', 'raw', 'map_docs_index.json')

GIS_EXT = re.compile(r'\.(kmz|kml|shp|gdb|geojson|gpx|dxf|dwg|gpkg|zip)(\?|$)', re.I)
# ordered: first match wins
MAP_KINDS = [
    ('gis_data', re.compile(r'\b(shapefiles?|shp|kmz|kml|geodatabase|gis data|gis files?|spatial data|'
                            r'geospatial|donn[ée]es (?:sig|g[ée]ospatiales)|fichiers? de formes)\b', re.I)),
    ('site_plan', re.compile(r'\b(site plans?|plot plans?|general arrangements?|plan d[\'’]ensemble|'
                             r'plan de site|plan d[\'’]implantation|plan g[ée]n[ée]ral|arrangement g[ée]n[ée]ral|'
                             r'layout drawings?|engineering drawings?|design drawings?|construction drawings?|'
                             r'drawings? (?:package|set)|plan view)\b', re.I)),
    ('layout', re.compile(r'\b(layouts?|footprints?|project (?:area|boundary|boundaries|site) map|'
                          r'turbine (?:locations?|layout|siting)|site layout|facility layout|mine (?:site )?plan|'
                          r'pit (?:shell|design|plan)|tailings (?:facility|management area|storage) (?:plan|design|layout)|'
                          r'(?:transmission|pipeline|route) (?:alignment|corridor|routing)|alignment sheets?|'
                          r'emplacement des [ée]oliennes|implantation|trac[ée] (?:de la ligne|du pipeline))\b', re.I)),
    ('location_map', re.compile(r'\b(location maps?|project location|key maps?|(?:regional|local) (?:study area|setting) maps?|'
                                r'study area maps?|(?:overview|vicinity|index) maps?|carte de localisation|'
                                r'localisation du projet|plan de localisation)\b', re.I)),
    ('figure', re.compile(r'\b(figures?|fig\.|maps?|cartes?|mapbook|map book|atlas|orthophoto|aerial (?:photo|image)|'
                          r'imagery|satellite image)\b', re.I)),
]
# titles that match a MAP kind but are not drawings
NOT_MAP = re.compile(r'\b(request(?:ing)?|response to|letter|correspondence|comments? on|email|courriel|'
                     r'meeting|minutes|agenda|presentation|news release|road ?map|site plan (?:control|approval) '
                     r'(?:by-?law|application)|figure of|map(?:le|ping process)|figured)\b', re.I)


def classify(title, url=''):
    t = f'{title or ""}'
    u = url or ''
    if GIS_EXT.search(u) and not u.lower().endswith('.zip'):
        return 'gis_data'
    if NOT_MAP.search(t):
        return None
    for kind, rx in MAP_KINDS:
        if rx.search(t) or (kind == 'gis_data' and rx.search(os.path.basename(u))):
            return kind
    if u.lower().endswith('.zip') and re.search(r'gis|shp|shape|kml|spatial|map', f'{t} {u}', re.I):
        return 'gis_data'
    return None


def main():
    geo = json.load(open(GEOJSON))
    projects = {}
    gis_queue = []
    summary = Counter()
    by_jur = defaultdict(Counter)

    def add(pid, name, jur, doc):
        kind = classify(doc.get('title'), doc.get('url'))
        if not kind:
            return
        rec = {'kind': kind, 'title': (doc.get('title') or '')[:160], 'url': doc.get('url')}
        for k in ('archive_url', 'date', 'fallback_url'):
            if doc.get(k):
                rec[k] = doc[k]
        ent = projects.setdefault(pid, {'name': name, 'jurisdiction': jur, 'docs': []})
        if any(d['url'] == rec['url'] for d in ent['docs']):
            return
        ent['docs'].append(rec)
        summary[kind] += 1
        by_jur[jur][kind] += 1
        m = GIS_EXT.search(rec['url'] or '')
        if kind == 'gis_data' and m:
            gis_queue.append({'pid': pid, 'name': name, 'url': rec['url'], 'title': rec['title'],
                              'ext': m.group(1).lower()})

    for f in geo['features']:
        p = f['properties']
        pid = make_id(p['jurisdiction'], p['name'])
        for sec in p.get('doc_sections') or []:
            for d in sec.get('docs') or []:
                add(pid, p['name'], p['jurisdiction'], d)
        dp = p.get('docs_path')
        if dp:
            path = os.path.join(ROOT, dp)
            if os.path.exists(path):
                try:
                    cat = json.load(open(path))
                except Exception:
                    continue
                for d in cat.get('docs') or []:
                    add(pid, p['name'], p['jurisdiction'], d)

    n_docs = sum(summary.values())
    out = {
        'summary': {'projects_with_map_docs': len(projects), 'docs': n_docs,
                    'by_kind': dict(summary),
                    'by_jurisdiction': {j: dict(c) for j, c in sorted(by_jur.items())},
                    'gis_queue': len(gis_queue)},
        'projects': dict(sorted(projects.items())),
        'gis_queue': gis_queue,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, 'w'), ensure_ascii=False, indent=0)
    print(json.dumps(out['summary'], indent=1))


if __name__ == '__main__':
    main()
