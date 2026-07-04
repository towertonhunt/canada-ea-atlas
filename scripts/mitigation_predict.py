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
FLOOR = ['indigenous_rights_tluse']
# archetype-rule disciplines
ARCHETYPE_FLOOR = {
    'mining': ['closure_postclosure', 'waste_hazmat', 'groundwater'],
    'oil_gas': ['accidents_malfunctions', 'ghg_climate'],
    'waste': ['groundwater', 'waste_hazmat'],
    'hydro': ['fish_fish_habitat', 'surface_water'],
    'wind': ['wildlife_birds', 'noise_vibration'],
    'solar': ['vegetation_ecosystems'],
}


def main():
    archetype = sys.argv[1] if len(sys.argv) > 1 else 'mining'
    constraints = sys.argv[2:]

    disciplines = set(FLOOR) | set(ARCHETYPE_FLOOR.get(archetype, []))
    for c in constraints:
        disciplines.update(TRIGGER_MAP.get(c, []))
    print(f'archetype: {archetype} | constraints: {constraints or "none"}')
    print(f'disciplines fired: {sorted(disciplines)}\n')

    recs = json.load(gzip.open(os.path.join(ROOT, 'data', 'conditions',
                                            'bc_conditions.json.gz'), 'rt'))
    # candidate pool: same archetype (strong precedent) or same discipline
    # from any archetype (weak precedent)
    strong = [r for r in recs if r['project_archetype'] == archetype
              and r['discipline'] in disciplines]
    weak = [r for r in recs if r['project_archetype'] != archetype
            and r['discipline'] in disciplines]

    def register(pool):
        # group by (discipline, measure_type, plan) and rank by distinct projects
        groups = defaultdict(list)
        for r in pool:
            key = (r['discipline'], r['measure_type'], r.get('plan_required'))
            groups[key].append(r)
        rows = []
        n_projects = len({r['project_id'] for r in pool}) or 1
        for (disc, mt, plan), rs in groups.items():
            projs = sorted({r['project'] for r in rs})
            rows.append({
                'discipline': disc,
                'measure_type': mt,
                'plan_required': plan,
                'precedent_projects': len(projs),
                'frequency': f'{len(projs)}/{n_projects} comparable projects',
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
          f'across {len({r["project_id"] for r in strong})} {archetype} projects\n')
    for row in reg[:12]:
        plan = f' -> {row["plan_required"]}' if row['plan_required'] else ''
        print(f'[{row["precedent_projects"]:>2} projects] {row["discipline"]} / '
              f'{row["measure_type"]}{plan}')
        print(f'    e.g. {row["examples"][0]}: "{row["sample_condition"][:110]}..."')
    print(f'\nfull register -> {path}')


if __name__ == '__main__':
    main()
