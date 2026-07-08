#!/usr/bin/env python3
"""Drop exact duplicate conditions within a project from the v2 sets.

The federal and Ontario merges dedupe on (project, normalized text); the
earlier BC pipeline (merge_reclassified_conditions.py) did not, so the BC
set carried exact-duplicate conditions (e.g. Willow Creek listed the same
condition table twice). This applies a conservative EXACT full-text dedup —
identical measure_text within the same project — to every
*_conditions_v2.json.gz. Idempotent: already-clean sets are no-ops.

Note: this is deliberately stricter than the merges' 400-char normalized
dedup, so it cannot remove distinct '-a'/'-b' multi-measure splits (they
have different text). Run: python3 scripts/dedupe_conditions.py
"""
import glob
import gzip
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    for path in sorted(glob.glob(os.path.join(ROOT, 'data', 'conditions',
                                              '*_conditions_v2.json.gz'))):
        name = os.path.basename(path)
        recs = json.load(gzip.open(path, 'rt'))
        seen, kept = set(), []
        for r in recs:
            key = (r.get('project'), r.get('measure_text'))
            if key in seen:
                continue
            seen.add(key)
            kept.append(r)
        removed = len(recs) - len(kept)
        if not removed:
            print(f'  ok  {name}: {len(recs)} conditions, no exact duplicates')
            continue
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode='wb', mtime=0) as gz:
            gz.write(json.dumps(kept).encode())
        open(path, 'wb').write(buf.getvalue())
        print(f'  FIXED {name}: {len(recs)} -> {len(kept)} '
              f'({removed} exact duplicates removed)')


if __name__ == '__main__':
    main()
