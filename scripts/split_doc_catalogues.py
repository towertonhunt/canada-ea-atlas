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

# ── Federal archive (pre-CEAA-2012 CEAR records) ─────────────────────
# These never had per-project catalogues: their documents only exist in the
# harvested search index as 'archive-document' rows carrying a relative_path
# into https://iaac-aeic.gc.ca/archives/evaluations.
import gzip

FED_ARCHIVE_BASE = 'https://iaac-aeic.gc.ca/archives/evaluations'
src = os.path.join(RAW, 'federal_list_all.json.gz')
if os.path.exists(src):
    outdir = os.path.join(ROOT, 'data', 'docs', 'federal')
    os.makedirs(outdir, exist_ok=True)
    by_project = {}
    for e in json.load(gzip.open(src, 'rt')):
        if e.get('document_type') != 'archive-document':
            continue
        pid, rel = e.get('project_id'), e.get('relative_path')
        if not pid or not rel:
            continue
        by_project.setdefault(pid, []).append({
            'title': ' '.join((e.get('document_title_en')
                               or e.get('file_name') or 'Document').split()),
            'category': e.get('document_category_en') or 'Archived',
            'url': FED_ARCHIVE_BASE + rel.replace('\\', '/'),
        })
    n = 0
    for pid, docs in by_project.items():
        seen, uniq = set(), []
        for d in docs:
            if d['url'] in seen:
                continue
            seen.add(d['url'])
            uniq.append(d)
        json.dump({'project': pid, 'docs': uniq},
                  open(os.path.join(outdir, f'{pid}.json'), 'w'), ensure_ascii=False)
        n += len(uniq)
    print(f'federal archive: {len(by_project)} files, {n} docs')

# ── Ontario provincial EA (ontario.ca project pages) ─────────────────
# The "Project documentation" sidebar on each project page links the notice
# of approval, ministry review and terms of reference -- these are the EA
# record, and they are the only documents Ontario publishes centrally.
src = os.path.join(RAW, 'on_ea_project_pages.json')
if os.path.exists(src):
    outdir = os.path.join(ROOT, 'data', 'docs', 'on')
    os.makedirs(outdir, exist_ok=True)
    n = 0
    for rec in json.load(open(src)):
        docs = rec.get('docs') or []
        if not docs:
            continue
        json.dump({'project': rec.get('name') or rec['slug'], 'docs': docs},
                  open(os.path.join(outdir, f"{rec['slug']}.json"), 'w'),
                  ensure_ascii=False)
        n += len(docs)
    print(f'ontario provincial EA: {len(os.listdir(outdir))} files, {n} docs')
