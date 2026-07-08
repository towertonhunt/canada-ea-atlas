#!/usr/bin/env python3
"""Integrity checks over the project's data artifacts.

Fast, offline, re-runnable smoke test. Hard FAILs (schema/enum breaks that
would corrupt the map, predictor, or search) exit non-zero; soft WARNs
(suspicious-but-tolerable data, e.g. an out-of-Canada coordinate) are
reported but don't fail. Run after any data rebuild or before merging a
lane's output:  python3 scripts/validate_data.py
"""
import glob
import gzip
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
# generous Canada bounding box (lon then lat)
CA_BBOX = (-141.5, 41.5, -52.0, 84.0)

fails, warns = [], []


def fail(msg):
    fails.append(msg)


def warn(msg):
    warns.append(msg)


def check_conditions():
    files = sorted(glob.glob(os.path.join(ROOT, 'data', 'conditions',
                                          '*_conditions_v2.json.gz')))
    if not files:
        return fail('no *_conditions_v2.json.gz found')
    total = 0
    for path in files:
        name = os.path.basename(path)
        recs = json.load(gzip.open(path, 'rt'))
        if not recs:
            fail(f'{name}: empty')
            continue
        # NOTE: condition_id is NOT unique by design — the federal source
        # repeats numbering across documents, so the merge dedupes on
        # (project, normalized text) and joins positionally. The real
        # invariant to verify is that text-level dedup held.
        seen_text = set()
        for i, r in enumerate(recs):
            where = f'{name}[{i}]'
            for k in ('discipline', 'measure_type', 'project',
                      'jurisdiction', 'measure_text'):
                if k not in r:
                    fail(f'{where}: missing key {k}')
            if r.get('discipline') not in DISCIPLINES:
                fail(f'{where}: bad discipline {r.get("discipline")!r}')
            if r.get('measure_type') not in MEASURE_TYPES:
                fail(f'{where}: bad measure_type {r.get("measure_type")!r}')
            if r.get('timing') not in TIMING:
                fail(f'{where}: bad timing {r.get("timing")!r}')
            secs = r.get('discipline_secondary') or []
            if not isinstance(secs, list) or any(s not in DISCIPLINES
                                                 for s in secs):
                fail(f'{where}: bad discipline_secondary {secs!r}')
            if r.get('discipline') in secs:
                fail(f'{where}: primary repeated in secondary')
            # verify the merge's text-level dedup held
            key = (r.get('project'),
                   re.sub(r'\W+', '', (r.get('measure_text') or '').lower())[:400])
            if key in seen_text:
                warn(f'{name}: dedup miss — repeated (project, text): '
                     f'{str(r.get("project"))[:40]!r} / {r.get("condition_id")}')
            seen_text.add(key)
        total += len(recs)
        print(f'  ok  {name}: {len(recs)} conditions')
    print(f'  -> {total} conditions across {len(files)} jurisdictions')


def check_geojson():
    path = os.path.join(ROOT, 'data', 'projects_canada.geojson')
    if not os.path.exists(path):
        return fail('projects_canada.geojson missing')
    d = json.load(open(path))
    feats = d.get('features')
    if d.get('type') != 'FeatureCollection' or not isinstance(feats, list):
        return fail('projects_canada.geojson: not a FeatureCollection')
    mapped = oob = 0
    for i, f in enumerate(feats):
        p = f.get('properties') or {}
        if not p.get('name'):
            fail(f'feature[{i}]: no name')
        if not p.get('jurisdiction'):
            fail(f'feature[{i}]: no jurisdiction')
        g = f.get('geometry')
        if g:
            c = g.get('coordinates')
            if (not isinstance(c, list) or len(c) != 2
                    or not all(isinstance(x, (int, float)) for x in c)):
                fail(f'feature[{i}] ({p.get("name","?")[:30]}): bad coords {c!r}')
                continue
            mapped += 1
            lon, lat = c
            if not (CA_BBOX[0] <= lon <= CA_BBOX[2]
                    and CA_BBOX[1] <= lat <= CA_BBOX[3]):
                oob += 1
                warn(f'{p.get("jurisdiction")}: "{p.get("name","?")[:40]}" '
                     f'at [{lon:.3f},{lat:.3f}] outside Canada bbox')
    print(f'  ok  geojson: {len(feats)} features, {mapped} mapped, '
          f'{oob} out-of-bounds')


def check_corpus_search():
    path = os.path.join(ROOT, 'data', 'corpus_search.sqlite3.gz')
    if not os.path.exists(path):
        return warn('corpus_search.sqlite3.gz missing (run '
                    'build_corpus_search.py)')
    try:
        raw = gzip.open(path, 'rb').read()
        tmp = os.path.join(ROOT, 'data', '.validate_tmp.sqlite3')
        open(tmp, 'wb').write(raw)
        db = sqlite3.connect(tmp)
        n = db.execute('SELECT count(*) FROM docs').fetchone()[0]
        hit = db.execute("SELECT count(*) FROM docs WHERE docs MATCH "
                         "'environment'").fetchone()[0]
        db.close()
        os.remove(tmp)
        if n < 100:
            fail(f'corpus search: only {n} docs indexed')
        else:
            print(f'  ok  corpus search: {n} docs, MATCH returns {hit} hits')
    except Exception as e:
        fail(f'corpus search DB unreadable: {e}')


def check_predictions():
    files = glob.glob(os.path.join(ROOT, 'data', 'predictions', '*.json'))
    if not files:
        return warn('no prediction registers (run mitigation_predict --full)')
    for path in files:
        d = json.load(open(path))
        for row in d.get('strong_precedents', []):
            if row['discipline'] not in DISCIPLINES:
                fail(f'{os.path.basename(path)}: bad discipline '
                     f'{row["discipline"]!r}')
    print(f'  ok  predictions: {len(files)} registers')


def main():
    print('Validating data artifacts...\n')
    for name, fn in (('conditions', check_conditions),
                     ('geojson', check_geojson),
                     ('corpus search', check_corpus_search),
                     ('predictions', check_predictions)):
        print(f'[{name}]')
        try:
            fn()
        except Exception as e:
            fail(f'{name} check crashed: {e}')
        print()

    if warns:
        print(f'{len(warns)} WARNING(S):')
        for w in warns:
            print(f'  ! {w}')
        print()
    if fails:
        print(f'{len(fails)} FAILURE(S):')
        for f in fails:
            print(f'  X {f}')
        sys.exit(1)
    print('All checks passed.')


if __name__ == '__main__':
    main()
