#!/usr/bin/env python3
"""Seed the R2 archive from PDFs already on disk instead of re-fetching them.

An earlier federal download run (archive/federal-workspace) left 613 PDFs in
folders named <date>_<project name>_<project id>/<document title>.pdf, with
per-project JSON that pairs titles with registry URLs. This joins the two,
maps each file to the catalogue URL the map links, uploads it under the same
key archive_docs.py would have chosen, and records it in the manifest so the
lane skips it.

Run on the machine that holds the files, with the R2_* variables exported in
that shell (never pasted anywhere):

  python3 scripts/seed_archive_local.py --dry-run       # report matches only
  python3 scripts/seed_archive_local.py                 # upload + manifest
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from archive_docs import (MANIFEST, key_for, load_manifest, save_manifest,  # noqa: E402
                          targets, upload_dir)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE = os.path.join(os.path.dirname(ROOT), 'archive', 'federal-workspace')
DOC_ID = re.compile(r'/050/evaluations/document/(\d+)')


def norm(s):
    """Filenames were derived from titles with punctuation stripped; compare
    on letters and digits only."""
    return re.sub(r'[^a-z0-9]+', '', s.casefold())


def local_files():
    """-> [(path, project_id, title_stem)]"""
    out = []
    for path in glob.glob(os.path.join(WORKSPACE, 'data', 'documents', '**', '*.pdf'),
                          recursive=True):
        folder = os.path.basename(os.path.dirname(path))
        m = re.search(r'_(\d{4,6})$', folder)
        if not m:
            continue
        out.append((path, m.group(1), os.path.splitext(os.path.basename(path))[0]))
    return out


def project_docs(pid):
    p = os.path.join(WORKSPACE, 'data', 'raw', f'project_{pid}.json')
    if not os.path.exists(p):
        return []
    return json.load(open(p)).get('documents') or []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    public = os.environ.get('R2_PUBLIC_BASE', '').rstrip('/')
    if not args.dry_run and not public:
        raise SystemExit('R2_PUBLIC_BASE is not set (export the R2_* variables first)')

    # catalogue url by federal document id
    by_docid = {}
    for url, jur, project, title in targets({'federal'}):
        m = DOC_ID.search(url)
        if m:
            by_docid[m.group(1)] = (url, project)

    manifest = load_manifest()
    files = local_files()
    matched, unmatched, already = [], [], 0
    for path, pid, stem in files:
        docs = project_docs(pid)
        hit = None
        for d in docs:
            if norm(d.get('title') or '') == norm(stem):
                m = DOC_ID.search(d.get('url') or '')
                if m and m.group(1) in by_docid:
                    hit = by_docid[m.group(1)]
                    break
        if not hit:
            unmatched.append(path)
            continue
        url, project = hit
        if manifest.get(url, {}).get('key'):
            already += 1
            continue
        matched.append((path, url, project))

    print(f'{len(files)} local PDFs: {len(matched)} map to a catalogue link, '
          f'{already} already archived, {len(unmatched)} unmatched')
    if args.dry_run:
        for path, url, project in matched[:8]:
            print('  ', key_for('federal', project, url), '<-',
                  os.path.relpath(path, WORKSPACE)[:70])
        return

    staging = tempfile.mkdtemp(prefix='ea-seed-')
    n_bytes = 0
    for path, url, project in matched:
        key = key_for('federal', project, url)
        dest = os.path.join(staging, key)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(path, dest)
        data = open(path, 'rb').read()
        n_bytes += len(data)
        manifest.setdefault(url, {'jur': 'federal', 'project': project}).update(
            key=key, archive_url=f'{public}/{key}', bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(), content_type='application/pdf',
            kind='file', source='local:federal-workspace',
            fetched_at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    print(f'uploading {len(matched)} files ({n_bytes / 1e9:.2f} GB)...', flush=True)
    if upload_dir(staging):
        save_manifest(manifest)
        print(f'done -> {MANIFEST}')
    else:
        print('upload failed; manifest not written')
    shutil.rmtree(staging, ignore_errors=True)


if __name__ == '__main__':
    main()
