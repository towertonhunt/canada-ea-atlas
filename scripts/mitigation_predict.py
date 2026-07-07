#!/usr/bin/env python3
"""Mitigation prediction v0 — precedent retrieval for a proposed project.

Usage:
  python3 scripts/mitigation_predict.py <archetype> [constraint ...]

  archetype:   a map category (mining, wind, solar, hydro, oil_gas, transport,
               water, waste, industrial, energy_other, ...)
  constraint:  optional spatial constraints, as discipline triggers:
               wetland, watercourse, waterbody, species_at_risk, reserve,
               ansi, abandoned_mine  (later supplied by baseline_query.py)

Output: ranked mitigation register with precedent frequencies and citations,
written to data/predictions/<archetype>_register.json and summarized to stdout.
"""
import gzip
import json
import os
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# spatial constraint -> disciplines fired (per docs/mitigation-taxonomy.md)
TRIGGER_MAP = {
    'wetland': ['wetlands', 'surface_water'],
    'watercourse': ['fish_fish_habitat', 'surface_water'],
    'waterbody': ['fish_fish_habitat', 'surface_water'],
    'species_at_risk': ['species_at_risk', 'wildlife_birds', 'vegetation_ecosystems'],
    'reserve': ['indigenous_rights_tluse'],
    'ansi': ['vegetation_ecosystems', 'species_at_risk'],
    'abandoned_mine': ['soils_terrain', 'waste_hazmat'],
}
# non-suppressible floors: fire for every project regardless of constraints
FLOOR = ['indigenous_rights_tluse', 'accidents_malfunctions',
         'archaeology_heritage']
# archetype-rule disciplines
ARCHETYPE_FLOOR = {
    'mining': ['closure_postclosure', 'waste_hazmat', 'groundwater',
               'surface_water'],
    'oil_gas': ['accidents_malfunctions', 'climate_ghg', 'waste_hazmat'],
    'waste': ['groundwater', 'waste_hazmat', 'air_quality'],
    'hydro': ['fish_fish_habitat', 'surface_water'],
    'wind': ['wildlife_birds', 'noise_vibration', 'closure_postclosure'],
    'solar': ['vegetation_ecosystems', 'noise_vibration',
              'closure_postclosure'],
    'biogas': ['air_quality', 'waste_hazmat', 'surface_water'],
    'transport': ['noise_vibration', 'surface_water', 'socio_economic'],
    'nuclear': ['human_health', 'waste_hazmat', 'accidents_malfunctions'],
    'industrial': ['air_quality', 'surface_water'],
}


def main():
    archetype = sys.argv[1] if len(sys.argv) > 1 else 'mining'
    args = sys.argv[2:]
    juris = [a.split('=')[1] for a in args if a.startswith('jur=')]
    constraints = [a for a in args if not a.startswith('jur=')]

    full = '--full' in constraints
    constraints = [c for c in constraints if c != '--full']
    if full:
        # every taxonomy discipline: page-side filtering picks the fired set
        disciplines = {d for ds in TRIGGER_MAP.values() for d in ds}
        disciplines |= {d for ds in ARCHETYPE_FLOOR.values() for d in ds}
        disciplines |= set(FLOOR) | {
            'air_quality', 'noise_vibration', 'light', 'soils_terrain',
            'human_health', 'socio_economic', 'visual_landscape',
            'climate_ghg', 'cumulative_effects', 'wetlands', 'groundwater',
            'vegetation_ecosystems', 'wildlife_birds', 'species_at_risk',
            'fish_fish_habitat', 'surface_water', 'waste_hazmat',
            'accidents_malfunctions', 'archaeology_heritage',
            'closure_postclosure', 'indigenous_rights_tluse'}
    else:
        disciplines = set(FLOOR) | set(ARCHETYPE_FLOOR.get(archetype, []))
        for c in constraints:
            disciplines.update(TRIGGER_MAP.get(c, []))
    print(f'archetype: {archetype} | constraints: {constraints or "none"}')
    print(f'disciplines fired: {sorted(disciplines)}\n')

    import glob
    recs = []
    for path in sorted(glob.glob(os.path.join(ROOT, 'data', 'conditions',
                                              '*_conditions_v2.json.gz'))):
        recs += json.load(gzip.open(path, 'rt'))
    if juris:
        recs = [r for r in recs if r.get('jurisdiction') in juris]
    print(f'precedent pool: {len(recs)} v2 conditions from jurisdictions: '
          f'{sorted({r.get("jurisdiction") for r in recs})}')

    def hits(r):
        # a condition counts for a fired discipline via primary OR secondary
        return (r['discipline'] in disciplines or
                any(s in disciplines for s in r.get('discipline_secondary') or []))

    # candidate pool: same archetype (strong precedent) or same discipline
    # from any archetype (weak precedent). Admin 'other' never fires.
    strong = [r for r in recs if r['project_archetype'] == archetype and hits(r)]
    weak = [r for r in recs if r['project_archetype'] != archetype and hits(r)]
    # denominator: all projects of this archetype in the pool, whether or
    # not they triggered the fired disciplines
    arch_projects = {r['project_id'] or r['project'] for r in recs
                     if r['project_archetype'] == archetype}

    def register(pool):
        # group by (discipline, measure_type) and rank by distinct projects
        groups = defaultdict(list)
        for r in pool:
            groups[(r['discipline'], r['measure_type'])].append(r)
        rows = []
        n_projects = len(arch_projects) or 1
        for (disc, mt), rs in groups.items():
            if disc == 'other' and mt == 'other':
                continue                     # pure admin machinery
            projs = sorted({r['project'] for r in rs})
            timings = Counter(r.get('timing') for r in rs if r.get('timing'))
            juris_mix = Counter(r['jurisdiction'] for r in rs)
            rows.append({
                'discipline': disc,
                'measure_type': mt,
                'precedent_projects': len(projs),
                'frequency': f'{len(projs)}/{n_projects} comparable projects',
                'typical_timing': (timings.most_common(1)[0][0]
                                   if timings else None),
                'jurisdictions': dict(juris_mix),
                'examples': projs[:4],
                'sample_condition': rs[0]['measure_text'][:300],
                'sample_source': rs[0]['source_doc'],
            })
        rows.sort(key=lambda r: -r['precedent_projects'])
        return rows

    reg = register(strong)
    out = {'archetype': archetype, 'constraints': constraints,
           'disciplines': sorted(disciplines),
           'strong_precedents': reg, 'weak_pool_size': len(weak)}
    os.makedirs(os.path.join(ROOT, 'data', 'predictions'), exist_ok=True)
    path = os.path.join(ROOT, 'data', 'predictions', f'{archetype}_register.json')
    json.dump(out, open(path, 'w'), ensure_ascii=False, indent=1)

    print(f'{len(reg)} mitigation families from {len(strong)} conditions '
          f'across {len({r["project_id"] or r["project"] for r in strong})} {archetype} projects\n')
    for row in reg[:12]:
        timing = f' @ {row["typical_timing"]}' if row['typical_timing'] else ''
        print(f'[{row["precedent_projects"]:>2} projects] {row["discipline"]} / '
              f'{row["measure_type"]}{timing}')
        print(f'    e.g. {row["examples"][0]}: "{row["sample_condition"][:110]}..."')
    print(f'\nfull register -> {path}')


if __name__ == '__main__':
    main()
