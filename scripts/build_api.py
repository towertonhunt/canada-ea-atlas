#!/usr/bin/env python3
"""Build the static JSON API the app consumes (F1 §7 / APP_PLAN §2).

Reads:  data/projects_canada.geojson, data/process_frameworks.json,
        data/conditions/*_v2.json.gz, data/raw/federal_list_all.json.gz
Writes: data/api/meta.json          counts, facets, sector meta, stamp
        data/api/projects.json      slim index of ALL features (compact keys)
        data/api/project/<id>.json  full detail for deep-tier projects
                                    (analysed commitments inline)

Index row keys (compact on purpose — ~18.8k rows ship to the browser):
  i=id  n=name  j=jurisdiction  s=sector(category)  st=status  p=proponent
  c=[lon,lat]|null  d=depth(3 deep|2 documented|1 mapped)  y=approval_year
  dp=docs_path  g=geocode quality  proc={f,stage,label,macro,range,sub,conf,out}

Stable ids: sources mostly publish none, so ids are source-prefixed
content hashes of (jurisdiction, name) — deterministic across rebuilds.
Run:  python3 scripts/build_api.py
"""
import glob
import gzip
import hashlib
import json
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = os.path.join(ROOT, 'data', 'api')
GEOJSON = os.path.join(ROOT, 'data', 'projects_canada.geojson')
FRAMEWORKS = os.path.join(ROOT, 'data', 'process_frameworks.json')
NORTHEY = os.path.join(ROOT, 'data', 'northey_subjects.json')

JUR_PREFIX = {
    'Federal (IAAC)': 'fed', 'British Columbia (EAO)': 'bc',
    'Quebec (MELCCFP)': 'qc', 'Nova Scotia (NSECC)': 'ns',
    'Newfoundland & Labrador (ECC)': 'nl', 'Manitoba (Environment Act)': 'mb',
    'Ontario (REA)': 'rea', 'Ontario (Provincial EA)': 'onp',
    'Ontario (Abandoned Mines)': 'amis',
    'Major projects inventory (unmatched)': 'gap',
}


def make_id(jur, name):
    h = hashlib.md5(f'{jur}||{name}'.encode()).hexdigest()[:10]
    return f'{JUR_PREFIX.get(jur, "x")}-{h}'


def fold(s):
    s = unicodedata.normalize('NFKD', str(s or ''))
    return s.encode('ascii', 'ignore').decode('ascii').lower().strip()


# ── process derivation (F3 source mappings) ─────────────────────────
FW = json.load(open(FRAMEWORKS))
SM = FW['source_mappings']

BC_2018_PHASES = {'Project Designation', 'Early Engagement', 'Readiness Decision',
                  'Process Planning', 'Application Development & Review',
                  'Effects Assessment & Review', 'Effects Assessment & Recommendation',
                  'Recommendation'}


def load_federal_phase_by_name():
    path = os.path.join(ROOT, 'data', 'raw', 'federal_list_all.json.gz')
    if not os.path.exists(path):
        return {}
    out = {}
    for x in json.load(gzip.open(path, 'rt')):
        nm = x.get('project_name_en')
        ph = x.get('ea_phase_en')
        if nm and ph and nm not in out:
            out[nm] = ph
    return out


FED_PHASE = load_federal_phase_by_name()


def stage_label(fw_key, stage_key):
    fw = FW['frameworks'].get(fw_key) or {}
    for s in fw.get('stages', []):
        if s['key'] == stage_key:
            return s['label'], s.get('macro'), s.get('macro_range')
    return None, None, None


def derive_process(p):
    """Return the compact process object for one feature's properties."""
    jur = p.get('jurisdiction')
    proc = {'f': None, 'stage': None, 'label': None, 'macro': None,
            'range': None, 'sub': None, 'conf': 'u', 'out': None}

    if jur == 'Federal (IAAC)':
        fmap = SM['federal']['framework_by_ea_type']
        proc['f'] = fmap.get(p.get('type') or '', fmap['_default'])
        ph = FED_PHASE.get(p.get('name'))
        if ph and ph in SM['federal']['stage_by_ea_phase']:
            rule = SM['federal']['stage_by_ea_phase'][ph]
            proc['f'] = rule['framework']
            proc['stage'] = rule['stage']
            proc['label'], proc['macro'], _ = stage_label(proc['f'], rule['stage'])
            proc['conf'] = 'e'
        else:
            rule = SM['federal']['stage_by_status'].get(p.get('status') or '')
            if rule:
                proc['macro'] = rule.get('macro_stage')
                proc['range'] = rule.get('macro_range')
                proc['out'] = rule.get('outcome')
                proc['conf'] = 'i'
        return proc

    if jur == 'British Columbia (EAO)':
        phase = p.get('status') or ''
        rule = SM['bc_epic']['phase_map'].get(phase)
        proc['f'] = 'bc_2018' if phase in BC_2018_PHASES else 'bc_2002'
        if rule:
            proc['conf'] = 'e'
            if 'outcome' in rule:
                proc['out'] = rule['outcome']
            if 'stage' in rule:
                # stage key must exist in the chosen framework; fall back
                # to the other Act's framework when it doesn't
                lbl, macro, rng = stage_label(proc['f'], rule['stage'])
                if lbl is None:
                    alt = 'bc_2002' if proc['f'] == 'bc_2018' else 'bc_2018'
                    lbl2, macro2, rng2 = stage_label(alt, rule['stage'])
                    if lbl2 is not None:
                        proc['f'], lbl, macro, rng = alt, lbl2, macro2, rng2
                proc['stage'] = rule['stage']
                proc['label'] = lbl or phase
                proc['macro'] = macro
                proc['sub'] = rule.get('subphase')
            if rule.get('confidence') == 'unknown':
                proc['conf'] = 'u'
        return proc

    if jur == 'Ontario (REA)':
        rule = SM['on_rea']['all_records']
        proc.update({'f': rule['framework'], 'stage': rule['stage'],
                     'macro': rule['macro_stage'], 'conf': 'i'})
        proc['label'], _, _ = stage_label(rule['framework'], rule['stage'])
        return proc

    if jur == 'Ontario (Provincial EA)':
        proc['f'] = 'on_ea'
        return proc

    return proc  # unmodelled jurisdictions: confidence 'u'


# ── commitments (deep tier) ─────────────────────────────────────────
def load_commitments():
    by_project = {}
    for path in sorted(glob.glob(os.path.join(ROOT, 'data', 'conditions',
                                              '*_conditions_v2.json.gz'))):
        for r in json.load(gzip.open(path, 'rt')):
            by_project.setdefault(fold(r['project']), []).append({
                'id': r.get('condition_id'),
                'discipline': r['discipline'],
                'discipline_secondary': r.get('discipline_secondary') or [],
                'measure_type': r['measure_type'],
                'timing': r.get('timing'),
                'text': r['measure_text'],
                'jurisdiction': r.get('jurisdiction'),
                'source_doc': r.get('source_doc') or r.get('doc'),
            })
    return by_project


# ── Northey landmark cases (crosswalk) ──────────────────────────────
NORTHEY_SOURCE = ("Rodney Northey, A Guide to Canada's Impact Assessment "
                  "Act (2023)")


def load_northey():
    """map_id -> {source, citations:[...]} for Northey-cited landmark projects.

    Published facts only: the citation reference (year, EA regime, panel type,
    registry source) — not book excerpt text, which stays in private storage.
    Groups by pid because one project can carry more than one citation (e.g.
    the 2016 TMX report and the 2019 reconsideration).
    """
    if not os.path.exists(NORTHEY):
        return {}
    doc = json.load(open(NORTHEY))
    by_pid = {}
    for s in doc.get('subjects', []):
        pid = s.get('map_id')
        if not pid:
            continue
        by_pid.setdefault(pid, {'source': NORTHEY_SOURCE, 'citations': []})
        by_pid[pid]['citations'].append({
            'shorthand': s['shorthand'],
            'report_year': s['report_year'],
            'ea_regime': s['ea_regime'],
            'assessment_type': s['assessment_type'],
            'registry_source': s['registry_source'],
            'confidence': s['confidence'],
            'note': s.get('note'),
        })
    for blk in by_pid.values():
        blk['citations'].sort(key=lambda c: c['report_year'])
        blk['year'] = blk['citations'][0]['report_year']
    return by_pid


def main():
    os.makedirs(os.path.join(API, 'project'), exist_ok=True)
    gj = json.load(open(GEOJSON))
    commitments = load_commitments()
    northey = load_northey()
    northey_seen = set()

    index, details, seen_ids = [], [], set()
    deep_ids = []
    northey_map = []  # sidecar for the map: matched by (jurisdiction, name)
    depth_counts = {1: 0, 2: 0, 3: 0}
    for f in gj['features']:
        p = f['properties']
        jur, name = p.get('jurisdiction'), p.get('name') or ''
        pid = make_id(jur, name)
        while pid in seen_ids:              # same-name collisions in a source
            pid += 'x'
        seen_ids.add(pid)

        cs = commitments.get(fold(name))
        nth = northey.get(pid)
        if nth:
            northey_seen.add(pid)
            northey_map.append({'j': jur, 'n': name, 'y': nth['year'],
                                'regime': nth['citations'][0]['ea_regime']})
        has_docs = bool(p.get('docs_path') or (p.get('doc_count') or 0) > 0
                        or p.get('has_tech_docs'))
        depth = 3 if cs else (2 if has_docs else 1)
        depth_counts[depth] += 1
        g = f.get('geometry')
        coords = g['coordinates'] if g and g.get('type') == 'Point' else None
        proc = derive_process(p)

        row = {'i': pid, 'n': name, 'j': jur, 's': p.get('category') or 'other',
               'st': p.get('status'), 'p': p.get('proponent'),
               'c': coords, 'd': depth, 'y': p.get('approval_year'),
               'dp': p.get('docs_path'), 'g': p.get('geocode'),
               'src': p.get('source'),
               'nth': nth['year'] if nth else None,  # landmark-case flag/year
               'proc': {k: v for k, v in proc.items() if v is not None}}
        index.append({k: v for k, v in row.items() if v is not None})

        # A detail file is emitted for any project with commitments OR a Northey
        # citation, so every landmark case has a project page even with no
        # analysed commitments.
        if cs:
            deep_ids.append(pid)
        if cs or nth:
            det = {
                'id': pid, 'name': name, 'jurisdiction': jur,
                'sector': p.get('category'), 'status': p.get('status'),
                'proponent': p.get('proponent'), 'coords': coords,
                'approval_date': p.get('approval_date'),
                'type': p.get('type'), 'docs_path': p.get('docs_path'),
                'geocode': p.get('geocode'), 'process': proc,
                'note': p.get('note'),
                'commitments': cs or [],
            }
            if nth:
                det['northey'] = nth
            details.append((pid, det))

    json.dump(index, open(os.path.join(API, 'projects.json'), 'w'),
              ensure_ascii=False, separators=(',', ':'))
    for pid, det in details:
        json.dump(det, open(os.path.join(API, 'project', f'{pid}.json'), 'w'),
                  ensure_ascii=False, separators=(',', ':'))

    sectors = {}
    for row in index:
        sectors[row['s']] = sectors.get(row['s'], 0) + 1
    meta = {
        'total': len(index), 'depth': depth_counts,
        'deep_tier_ids': deep_ids,
        'northey_ids': sorted(northey_seen),
        'sectors': sectors,
        'jurisdictions': sorted({r['j'] for r in index if r['j']}),
        'frameworks': 'data/process_frameworks.json',
    }
    json.dump(meta, open(os.path.join(API, 'meta.json'), 'w'),
              ensure_ascii=False, indent=1)

    # Sidecar the legacy map cross-references by (jurisdiction, name) — the same
    # identity the stable id is hashed from — to badge Northey landmark cases.
    json.dump({'source': NORTHEY_SOURCE,
               'projects': sorted(northey_map, key=lambda x: x['y'])},
              open(os.path.join(API, 'northey.json'), 'w'), ensure_ascii=False,
              indent=1)

    sz = os.path.getsize(os.path.join(API, 'projects.json')) / 1e6
    print(f'index: {len(index)} rows, {sz:.1f} MB '
          f'(deep {depth_counts[3]} / documented {depth_counts[2]} / '
          f'mapped {depth_counts[1]})')
    print(f'detail files: {len(details)} '
          f'({len(deep_ids)} deep-tier + {len(northey_seen)} Northey-matched)')
    n_expected = len({s['map_id'] for s in
                      json.load(open(NORTHEY)).get('subjects', [])
                      if s.get('map_id')}) if os.path.exists(NORTHEY) else 0
    print(f'northey: {len(northey_seen)}/{n_expected} crosswalk map ids '
          f'matched features')
    exact = sum(1 for r in index if r['proc'].get('conf') == 'e')
    inf = sum(1 for r in index if r['proc'].get('conf') == 'i')
    print(f'process: {exact} exact, {inf} inferred, '
          f'{len(index) - exact - inf} unknown')
    return 0


if __name__ == '__main__':
    sys.exit(main())
