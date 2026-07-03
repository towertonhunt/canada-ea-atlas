#!/usr/bin/env python3
"""Split bulk document catalogues into per-project JSON files the map UI
lazy-loads when a project sidebar opens (keeps projects_canada.geojson lean)."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'data', 'raw')

# ── BC EPIC ──────────────────────────────────────────────────────────
src = os.path.join(RAW, 'bc_doc_catalogue.json')
if os.path.exists(src):
    outdir = os.path.join(ROOT, 'data', 'docs', 'bc')
    os.makedirs(outdir, exist_ok=True)
    cat = json.load(open(src))
    n = 0
    for pid, entry in cat.items():
        docs = sorted(entry['docs'], key=lambda d: d.get('date') or '', reverse=True)
        json.dump({'project': entry['name'],
                   'docs': [{'title': d['title'] or d['file'], 'date': (d.get('date') or '')[:10],
                             'url': d['url']} for d in docs]},
                  open(os.path.join(outdir, f'{pid}.json'), 'w'), ensure_ascii=False)
        n += len(docs)
    print(f'bc: {len(cat)} files, {n} docs')

# ── Nova Scotia ──────────────────────────────────────────────────────
src = os.path.join(RAW, 'ns_doc_catalogue.json')
if os.path.exists(src):
    outdir = os.path.join(ROOT, 'data', 'docs', 'ns')
    os.makedirs(outdir, exist_ok=True)
    cat = json.load(open(src))
    n = 0
    for url, docs in cat.items():
        slug = url.rstrip('/').rsplit('/', 1)[-1].replace('.asp', '') or 'index'
        json.dump({'project': slug,
                   'docs': [{'title': d['title'], 'url': d['url']} for d in docs]},
                  open(os.path.join(outdir, f'{slug}.json'), 'w'), ensure_ascii=False)
        n += len(docs)
    print(f'ns: {len(cat)} files, {n} docs')
