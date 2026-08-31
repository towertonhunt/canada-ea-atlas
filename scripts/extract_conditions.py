#!/usr/bin/env python3
"""Condition extraction v1 — heuristic pass over the BC conditions corpus.

Segments condition-style documents into numbered condition records and
classifies each into the docs/mitigation-taxonomy.md controlled vocabularies
via keyword rules. Verbatim text is always preserved; classification is a
starting point the LM layer can refine later.

Output: data/conditions/bc_conditions.json
"""
import gzip
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, 'data', 'corpus', 'bc')
OUT_DIR = os.path.join(ROOT, 'data', 'conditions')

DISCIPLINE_RULES = [
    ('fish_fish_habitat', ['fish', 'riparian', 'instream', 'spawn']),
    ('wetlands', ['wetland', 'bog', 'fen', 'marsh']),
    ('surface_water', ['surface water', 'water quality', 'sediment', 'erosion',
                       'turbidity', 'discharge', 'effluent', 'runoff']),
    ('groundwater', ['groundwater', 'aquifer', 'well']),
    ('wildlife_birds', ['wildlife', 'bird', 'nest', 'bat', 'ungulate', 'bear',
                        'moose', 'caribou', 'raptor', 'migratory']),
    ('species_at_risk', ['species at risk', 'endangered', 'threatened', 'sara']),
    ('vegetation_ecosystems', ['vegetation', 'plant', 'ecosystem', 'old growth',
                               'invasive', 'revegetat', 'reclam']),
    ('air_quality', ['air quality', 'dust', 'emission', 'particulate']),
    ('noise_vibration', ['noise', 'vibration', 'sound']),
    ('ghg_climate', ['greenhouse gas', 'ghg', 'climate', 'carbon']),
    ('indigenous_rights_tluse', ['indigenous', 'first nation', 'aboriginal',
                                 'traditional use', 'treaty', 'nation']),
    ('archaeology_heritage', ['archaeolog', 'heritage', 'cultural site']),
    ('human_health', ['human health', 'country food', 'drinking water']),
    ('socio_economic', ['employment', 'training', 'housing', 'community',
                        'economic', 'workforce']),
    ('waste_hazmat', ['waste', 'hazardous', 'spill', 'fuel', 'chemical',
                      'tailings']),
    ('soils_terrain', ['soil', 'terrain', 'slope', 'geotechnical', 'acid rock',
                       'metal leaching']),
    ('closure_postclosure', ['closure', 'decommission', 'post-closure',
                             'reclamation security', 'bond']),
    ('accidents_malfunctions', ['accident', 'malfunction', 'emergency',
                                'contingency']),
]

MEASURE_RULES = [
    ('management_plan', ['management plan', 'plan must', 'develop a plan',
                         'monitoring plan', 'protection plan', 'mitigation plan']),
    ('monitoring_followup', ['monitor', 'sampling', 'survey', 'report annually',
                             'follow-up', 'audit']),
    ('avoidance_timing', ['timing window', 'least risk', 'no construction during',
                          'avoid', 'setback', 'buffer']),
    ('engagement_commitment', ['consult', 'engage', 'notify', 'communicate']),
    ('financial_assurance', ['security', 'bond', 'financial assurance']),
    ('compensation_offsetting', ['offset', 'compensat', 'habitat replacement']),
    ('minimization_design', ['design', 'install', 'use of', 'equip']),
]

PLAN_NAME = re.compile(
    r'\b([A-Z][A-Za-z]+(?:\s+[A-Za-z&-]+){0,5}\s+(?:Management|Monitoring|'
    r'Protection|Mitigation|Response|Contingency)\s+Plan)\b')

# condition segment boundaries: "1." / "1.1" / "Condition 12" at line start
SEG = re.compile(r'\n\s*(?=(?:\d{1,2}(?:\.\d{1,2})?[.)]\s+[A-Z])|(?:Condition\s+\d))')


def classify(rules, text, default):
    t = text.lower()
    best, score = default, 0
    for name, keys in rules:
        s = sum(t.count(k) for k in keys)
        if s > score:
            best, score = name, s
    return best if score else default


def run_jurisdiction(jur, corpus_dir, arch, title_filter):
    idx_path = os.path.join(corpus_dir, 'index.json')
    if not os.path.exists(idx_path):
        return [], 0
    idx = {e['doc_id']: e for e in json.load(open(idx_path))}
    records, docs_used = [], 0
    for doc_id, meta in idx.items():
        title = (meta.get('title') or '').lower()
        if title_filter and not any(k in title for k in title_filter):
            continue
        path = os.path.join(corpus_dir, f'{doc_id}.txt.gz')
        if not os.path.exists(path):
            continue
        text = gzip.open(path, 'rt', encoding='utf-8').read()
        segs = [s.strip() for s in SEG.split(text) if 120 < len(s.strip()) < 6000]
        if len(segs) < 3:
            continue
        docs_used += 1
        for n, seg in enumerate(segs):
            head = seg[:1200]
            plan = PLAN_NAME.search(head)
            records.append({
                'condition_id': f'{jur}-{doc_id}-{n:03d}',
                'source_doc': meta.get('url'),
                'source_title': meta.get('title'),
                'jurisdiction': jur,
                'project_id': meta.get('project_id'),
                'project': meta.get('project'),
                'project_archetype': arch(meta),
                'discipline': classify(DISCIPLINE_RULES, head, 'other'),
                'measure_type': classify(MEASURE_RULES, head, 'other'),
                'plan_required': plan.group(1) if plan else None,
                'measure_text': seg[:2500],
            })
    return records, docs_used


def main():
    from collections import Counter
    geo = json.load(open(os.path.join(ROOT, 'data', 'projects_canada.geojson')))
    bc_arch, fed_arch, rea_arch = {}, {}, {}
    for f in geo['features']:
        p = f['properties']
        if p.get('source') == 'bc_epic' and p.get('registry_url'):
            bc_arch[p['registry_url'].rsplit('/', 1)[-1]] = p.get('category', 'other')
        elif p.get('source') == 'federal_iaac' and p.get('registry_url'):
            fed_arch[p['registry_url'].rsplit('/', 1)[-1]] = p.get('category', 'other')
        elif p.get('source') == 'ontario_rea':
            rea_arch[(p.get('name') or '').lower()[:40]] = p.get('category', 'other')

    JURS = [
        ('bc', os.path.join(ROOT, 'data', 'corpus', 'bc'),
         lambda m: bc_arch.get(m.get('project_id'), 'other'),
         ('condition', 'certificate', 'schedule', 'commitment', 'management plan')),
        ('federal', os.path.join(ROOT, 'data', 'corpus', 'federal'),
         lambda m: fed_arch.get(m.get('project_id'), 'other'),
         None),  # all federal corpus docs are condition-targeted already
        ('ontario', os.path.join(ROOT, 'data', 'corpus', 'ontario'),
         lambda m: rea_arch.get((m.get('project') or '').lower()[:40],
                                categorize(m.get('title') or '')),
         None),
    ]
    os.makedirs(OUT_DIR, exist_ok=True)
    for jur, cdir, arch, tf in JURS:
        records, docs_used = run_jurisdiction(jur, cdir, arch, tf)
        if not records:
            print(f'{jur}: no records')
            continue
        json.dump(records, gzip.open(os.path.join(OUT_DIR, f'{jur}_conditions.json.gz'),
                                     'wt', encoding='utf-8'), ensure_ascii=False)
        summary = {
            'docs_used': docs_used, 'records': len(records),
            'by_discipline': dict(Counter(r['discipline'] for r in records).most_common(8)),
            'by_archetype': dict(Counter(r['project_archetype'] for r in records).most_common(8)),
        }
        json.dump(summary, open(os.path.join(OUT_DIR, f'{jur}_summary.json'), 'w'), indent=1)
        print(f'{jur}: {len(records)} records from {docs_used} docs; top disciplines:',
              list(summary['by_discipline'])[:5])


def categorize(t):
    t = t.lower()
    for cat, keys in (('wind', ('wind',)), ('solar', ('solar',)),
                      ('mining', ('mine', 'mining', 'quarry')),
                      ('waste', ('waste', 'landfill')),
                      ('water', ('water', 'sewage'))):
        if any(k in t for k in keys):
            return cat
    return 'other'


if __name__ == '__main__':
    main()
