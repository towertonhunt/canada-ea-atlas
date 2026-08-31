#!/usr/bin/env python3
"""Merge classified Ontario REA condition shards into ontario_conditions_v2.json.gz.

Joins shard classifications (data/conditions/shards_ontario/out/*.json) back
onto the extracted records (ontario_conditions.json.gz), drops
discards, validates enums, and dedupes template repetition: identical (project_id, normalized
measure_text) pairs collapse to their first occurrence (REA approvals and
their amendment notices repeat the same conditions verbatim).

Usage: python3 scripts/merge_ontario_conditions.py [--allow-partial]
Without --allow-partial, refuses to write output unless every input shard
has a classified counterpart.
"""
import glob
import gzip
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTRACTED = os.path.join(ROOT, 'data', 'conditions',
                         'ontario_conditions.json.gz')
SHARD_IN = os.path.join(ROOT, 'data', 'conditions', 'shards_ontario', 'in')
SHARD_OUT = os.path.join(ROOT, 'data', 'conditions', 'shards_ontario', 'out')
OUT = os.path.join(ROOT, 'data', 'conditions', 'ontario_conditions_v2.json.gz')

DISCIPLINES = {
    'surface_water', 'groundwater', 'fish_fish_habitat', 'wetlands',
    'vegetation_ecosystems', 'wildlife_birds', 'species_at_risk',
    'air_quality', 'noise_vibration', 'light', 'soils_terrain',
    'waste_hazmat', 'accidents_malfunctions', 'human_health',
    'socio_economic', 'indigenous_rights_tluse', 'archaeology_heritage',
    'visual_landscape', 'climate_ghg', 'cumulative_effects',
    'closure_postclosure', 'other'}
MEASURE_TYPES = {
    'avoidance', 'minimization', 'mitigation', 'compensation_offset',
    'management_plan', 'monitoring_followup', 'financial_assurance',
    'engagement', 'other'}
TIMING = {'pre_construction', 'construction', 'operation', 'closure',
          'post_closure', 'all_phases', None}


def norm_text(t):
    return re.sub(r'\W+', '', (t or '').lower())[:400]


def main():
    allow_partial = '--allow-partial' in sys.argv
    n_in = len(glob.glob(os.path.join(SHARD_IN, 'shard*.json')))
    outs = sorted(glob.glob(os.path.join(SHARD_OUT, 'shard*.json')))
    if len(outs) < n_in and not allow_partial:
        done = {os.path.basename(p) for p in outs}
        missing = [f'shard{i:02d}' for i in range(n_in)
                   if f'shard{i:02d}.json' not in done]
        sys.exit(f'{len(outs)}/{n_in} shards classified; missing: '
                 f'{", ".join(missing)} (use --allow-partial to override)')

    # Shards were built by slicing the extracted array in order, 250 apiece,
    # so positional join is exact; condition_ids repeat in the source and
    # cannot be used as a unique key.
    extracted = json.load(gzip.open(EXTRACTED, 'rt'))
    cls = []
    for p in outs:
        idx = int(re.search(r'shard(\d+)', p).group(1))
        shard = json.load(open(p))
        for j, c in enumerate(shard):
            cls.append((idx * 250 + j, c))

    merged, bad, discards, dupes = [], [], 0, 0
    seen = set()
    for pos, c in cls:
        if pos >= len(extracted):
            bad.append(f'position {pos} out of range')
            continue
        r = dict(extracted[pos])
        if c.get('condition_id') != r['condition_id']:
            bad.append(f"id mismatch at {pos}: {c.get('condition_id')} "
                       f"!= {r['condition_id']}")
            continue
        if c.get('discard'):
            discards += 1
            continue
        errs = []
        if c.get('discipline') not in DISCIPLINES:
            errs.append(f"discipline={c.get('discipline')}")
        if c.get('measure_type') not in MEASURE_TYPES:
            errs.append(f"measure_type={c.get('measure_type')}")
        if c.get('timing') not in TIMING:
            errs.append(f"timing={c.get('timing')}")
        secs = c.get('discipline_secondary') or []
        if (not isinstance(secs, list) or
                any(s not in DISCIPLINES for s in secs) or
                c.get('discipline') in secs):
            errs.append(f'secondary={secs}')
        if errs:
            bad.append(f"{r['condition_id']}: {'; '.join(errs)}")
            continue
        key = (r.get('project_id') or r.get('project'),
               norm_text(r.get('measure_text')))
        if key in seen:
            dupes += 1
            continue
        seen.add(key)
        r.update({'discipline': c['discipline'],
                  'discipline_secondary': secs,
                  'measure_type': c['measure_type'],
                  'timing': c.get('timing'),
                  'discipline_source': 'lm_classified'})
        merged.append(r)

    if bad:
        print(f'{len(bad)} invalid records (first 10):')
        for b in bad[:10]:
            print('  ', b)
        sys.exit(1)

    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode='wb', mtime=0) as gz:
        gz.write(json.dumps(merged).encode())
    open(OUT, 'wb').write(buf.getvalue())

    from collections import Counter
    print(f'merged {len(merged)} conditions '
          f'({discards} discarded, {dupes} deduped) -> {OUT}')
    print('disciplines:', Counter(r['discipline']
                                  for r in merged).most_common())
    print('measure types:', Counter(r['measure_type']
                                    for r in merged).most_common())


if __name__ == '__main__':
    main()
