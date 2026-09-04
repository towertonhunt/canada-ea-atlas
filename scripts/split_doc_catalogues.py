#!/usr/bin/env python3
"""Split bulk document catalogues into per-project JSON files the map UI
lazy-loads when a project sidebar opens (keeps projects_canada.geojson lean)."""
import gzip
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'data', 'raw')
ARCHIVE_ONLY = '--archive-only' in sys.argv


def attach_archive_urls():
    """Add archive_url beside url in every catalogue entry the R2 archive
    lane has mirrored (data/raw/archive_manifest.json.gz). Idempotent, and
    run last so regenerated catalogues get their links back."""
    src = os.path.join(RAW, 'archive_manifest.json.gz')
    if not os.path.exists(src):
        return
    man = json.load(gzip.open(src, 'rt'))
    n_files = n_docs = 0
    import glob
    for path in glob.glob(os.path.join(ROOT, 'data', 'docs', '*', '*.json')):
        try:
            cat = json.load(open(path))
        except (ValueError, OSError):
            continue
        changed = False
        for d in cat.get('docs') or []:
            rec = man.get(d.get('url'))
            au = rec.get('archive_url') if rec else None
            if au and d.get('archive_url') != au:
                d['archive_url'] = au
                changed = True
                n_docs += 1
        if changed:
            json.dump(cat, open(path, 'w'), ensure_ascii=False)
            n_files += 1
    print(f'archive links: {n_docs} added across {n_files} catalogues')


if ARCHIVE_ONLY:
    attach_archive_urls()
    sys.exit(0)

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

attach_archive_urls()
