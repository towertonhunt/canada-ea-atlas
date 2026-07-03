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


def main():
    idx = {e['doc_id']: e for e in json.load(open(os.path.join(CORPUS, 'index.json')))}
    # project archetypes from the map
    geo = json.load(open(os.path.join(ROOT, 'data', 'projects_canada.geojson')))
    arch = {}
    for f in geo['features']:
        p = f['properties']
        if p.get('source') == 'bc_epic' and p.get('registry_url'):
            arch[p['registry_url'].rsplit('/', 1)[-1]] = p.get('category', 'other')

    records, docs_used = [], 0
    for doc_id, meta in idx.items():
        title = (meta.get('title') or '').lower()
        if not any(k in title for k in ('condition', 'certificate', 'schedule',
                                        'commitment', 'management plan')):
            continue
        path = os.path.join(CORPUS, f'{doc_id}.txt.gz')
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
                'condition_id': f'bc-{doc_id}-{n:03d}',
                'source_doc': meta.get('url'),
                'source_title': meta.get('title'),
                'jurisdiction': 'bc',
                'project_id': meta.get('project_id'),
                'project': meta.get('project'),
                'project_archetype': arch.get(meta.get('project_id'), 'other'),
                'discipline': classify(DISCIPLINE_RULES, head, 'other'),
                'measure_type': classify(MEASURE_RULES, head, 'other'),
                'plan_required': plan.group(1) if plan else None,
                'measure_text': seg[:2500],
            })
    os.makedirs(OUT_DIR, exist_ok=True)
    json.dump(records, gzip.open(os.path.join(OUT_DIR, 'bc_conditions.json.gz'),
                                 'wt', encoding='utf-8'), ensure_ascii=False)
    # summary for quick inspection
    from collections import Counter
    summary = {
        'docs_used': docs_used,
        'records': len(records),
        'by_discipline': dict(Counter(r['discipline'] for r in records).most_common()),
        'by_measure': dict(Counter(r['measure_type'] for r in records).most_common()),
        'by_archetype': dict(Counter(r['project_archetype'] for r in records).most_common()),
    }
    json.dump(summary, open(os.path.join(OUT_DIR, 'bc_summary.json'), 'w'), indent=1)
    print(json.dumps(summary, indent=1)[:1200])


if __name__ == '__main__':
    main()
