#!/usr/bin/env python3
"""Merge a lane run's manifest into whatever is on origin/main, conflict-free.

The lane used to `git pull --rebase`, which fails on the binary manifest and
on catalogue files another commit touched -- and a failed rebase meant the
whole run's manifest was lost. Instead: keep the run's manifest aside, reset
to origin/main, union the two, and regenerate the catalogue links from the
merged result. Usage (in the lane):

  cp data/raw/archive_manifest.json.gz /tmp/run_manifest.json.gz
  git fetch origin && git reset --hard origin/main
  python3 scripts/merge_archive_manifest.py /tmp/run_manifest.json.gz
  python3 scripts/split_doc_catalogues.py --archive-only
"""
import gzip
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from archive_docs import MANIFEST, load_manifest, merge_manifests, save_manifest  # noqa: E402

run = json.load(gzip.open(sys.argv[1], 'rt'))
base = load_manifest(all_parts=False)
before = sum(1 for v in base.values() if v.get('key'))
merge_manifests(base, run)
after = sum(1 for v in base.values() if v.get('key'))
save_manifest(base)
print(f'merged: {before} -> {after} archived records in {MANIFEST}')
