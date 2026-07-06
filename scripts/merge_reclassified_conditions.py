#!/usr/bin/env python3
"""Merge LM-reclassified condition shards into bc_conditions_v2.json.gz.

Reads every JSON array in the shard directory (agents used varying file
names), dedupes by condition_id (last write wins), validates enums against
docs/mitigation-taxonomy.md, and reports coverage against the v1 file.

Usage: python3 scripts/merge_reclassified_conditions.py <shard_dir>
"""
import glob
import gzip
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V1 = os.path.join(ROOT, 'data', 'conditions', 'bc_conditions.json.gz')
OUT = os.path.join(ROOT, 'data', 'conditions', 'bc_conditions_v2.json.gz')

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
          'post_closure', 'all_phases'}


def main(shard_dir):
    v1_ids = {r['condition_id']
              for r in json.load(gzip.open(V1, 'rt'))}
    merged, discarded = {}, {}
    bad = []
    for path in sorted(glob.glob(os.path.join(shard_dir, '*.json'))):
        try:
            data = json.load(open(path))
        except Exception as e:
            print(f'SKIP unreadable {path}: {e}')
            continue
        if isinstance(data, dict):
            data = data.get('records', [])
        for r in data:
            cid = r.get('condition_id')
            if not cid:
                continue
            if r.get('discard'):
                discarded[cid] = r.get('discard_reason', '')
                continue
            errs = []
            if r.get('discipline') not in DISCIPLINES:
                errs.append(f"discipline={r.get('discipline')}")
            if r.get('measure_type') not in MEASURE_TYPES:
                errs.append(f"measure_type={r.get('measure_type')}")
            if r.get('timing') and r['timing'] not in TIMING:
                errs.append(f"timing={r.get('timing')}")
            for s in (r.get('discipline_secondary') or []):
                if s not in DISCIPLINES:
                    errs.append(f'secondary={s}')
            if errs:
                bad.append((cid, errs, path))
                continue
            merged[cid] = r

    base_of = lambda cid: (cid.rsplit('-', 1)[0]
                           if cid.rsplit('-', 1)[-1].isalpha()
                           and len(cid.rsplit('-', 1)[-1]) == 1 else cid)
    covered = ({base_of(c) for c in merged} | set(discarded)) & v1_ids
    missing = sorted(v1_ids - covered)

    print(f'kept {len(merged)}  discarded {len(discarded)}  '
          f'invalid {len(bad)}  coverage {len(covered)}/{len(v1_ids)}')
    if bad:
        print('first invalid:', bad[:5])
    if missing:
        json.dump(missing, open(os.path.join(shard_dir, 'missing_ids.json'), 'w'))
        print(f'{len(missing)} still missing -> missing_ids.json')

    records = sorted(merged.values(), key=lambda r: r['condition_id'])
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode='wb', mtime=0) as gz:
        gz.write(json.dumps(records, ensure_ascii=False).encode())
    open(OUT, 'wb').write(buf.getvalue())
    print(f'wrote {OUT} ({len(records)} records)')

    from collections import Counter
    print('disciplines:', Counter(r['discipline'] for r in records).most_common())
    print('measure_types:', Counter(r['measure_type'] for r in records).most_common())
    other_pct = sum(1 for r in records if r['discipline'] == 'other') / max(1, len(records))
    print(f"discipline 'other' share: {other_pct:.1%} (v1 was ~35%)")


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else
         input('shard dir: ').strip())
