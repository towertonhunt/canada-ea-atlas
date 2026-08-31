#!/usr/bin/env python3
"""Extract numbered conditions from federal decision-statement corpus docs.

IAAC decision statements number legally binding conditions as `N.M The
Proponent shall ...` inside a Conditions region, grouped under numbered
section headings whose titles name the discipline ("3 Fish and fish
habitat"). Text in data/corpus/federal/ is whitespace-flattened, so both
markers are matched inline. Sub-clauses (N.M.K) stay embedded in their
parent condition's text.

Writes data/conditions/federal_conditions_extracted.json.gz (staging input
for the LM reclassification pass -> federal_conditions_v2.json.gz).
"""
import gzip
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, 'data', 'corpus', 'federal')
OUT = os.path.join(ROOT, 'data', 'conditions',
                   'federal_conditions_extracted.json.gz')

# Section-title keywords -> taxonomy discipline (docs/mitigation-taxonomy.md)
SECTION_MAP = [
    ('fish', 'fish_fish_habitat'),
    ('migratory bird', 'wildlife_birds'),
    ('bird', 'wildlife_birds'),
    ('wildlife', 'wildlife_birds'),
    ('caribou', 'species_at_risk'),
    ('species at risk', 'species_at_risk'),
    ('wetland', 'wetlands'),
    ('vegetation', 'vegetation_ecosystems'),
    ('air quality', 'air_quality'),
    ('greenhouse gas', 'climate_ghg'),
    ('noise', 'noise_vibration'),
    ('light', 'light'),
    ('groundwater', 'groundwater'),
    ('surface water', 'surface_water'),
    ('water quality', 'surface_water'),
    ('soil', 'soils_terrain'),
    ('human health', 'human_health'),
    ('health', 'human_health'),
    ('socio-economic', 'socio_economic'),
    ('current use of lands', 'indigenous_rights_tluse'),
    ('indigenous', 'indigenous_rights_tluse'),
    ('aboriginal', 'indigenous_rights_tluse'),
    ('first nation', 'indigenous_rights_tluse'),
    ('heritage', 'archaeology_heritage'),
    ('archaeolog', 'archaeology_heritage'),
    ('structure, site or thing', 'archaeology_heritage'),
    ('accident', 'accidents_malfunctions'),
    ('malfunction', 'accidents_malfunctions'),
    ('waste', 'waste_hazmat'),
    ('effluent', 'surface_water'),
    ('decommissioning', 'closure_postclosure'),
    ('reclamation', 'closure_postclosure'),
    ('follow-up', 'other'),          # program-mechanics sections
    ('general condition', 'other'),
    ('administrative', 'other'),
    ('documentation', 'other'),
    ('implementation schedule', 'other'),
]

ARCHETYPES = [
    ('mining', ['mine', 'mining', 'nickel', 'gold', 'copper', 'iron',
                'coal', 'quarry', 'potash', 'uranium', 'lithium', 'diamond']),
    ('oil_gas', ['lng', 'gas', 'oil', 'pipeline', 'petroleum', 'well',
                 'offshore', 'drilling']),
    ('transport', ['highway', 'bridge', 'terminal', 'port', 'rail',
                   'marine', 'airport', 'wharf']),
    ('hydro', ['hydro', 'dam', 'generating station', 'reservoir']),
    ('wind', ['wind']),
    ('nuclear', ['nuclear', 'reactor']),
    ('industrial', ['plant', 'facility', 'smelter', 'refinery']),
]


def archetype(name):
    n = (name or '').lower()
    for a, keys in ARCHETYPES:
        if any(k in n for k in keys):
            return a
    return 'other'


def section_discipline(title):
    t = (title or '').lower()
    for k, d in SECTION_MAP:
        if k in t:
            return d
    return None


# Top-level condition marker: space, N.M, space, capital/quote start
COND = re.compile(r'(?<=[\s;.])(\d{1,2}\.\d{1,2})\s+(?=[A-Z“"])')
# Section heading in the gap before a section's first condition; some docs
# write "6 Title", others "6. Title", and intro sentences may follow, so
# match anywhere and keep the last occurrence whose number fits.
SECT = re.compile(r'(?:^|[\s.;])(\d{1,2})\.?\s+([A-Z][A-Za-z][^0-9.;]{2,90})')
DEFN = re.compile(r'^[“"]?[A-Za-z][^.]{0,80}\bmeans\b')


def extract(text):
    """Yield (cond_no, section_title, cond_text) for one document."""
    # bound the conditions region
    start = 0
    m = re.search(r'\bConditions\b', text)
    if m:
        start = m.start()
    m = re.search(r'\b(Issuance|Original signed|Signed at|SIGNATURE)\b',
                  text[start:])
    end = start + m.start() if m else len(text)
    region = text[start:end]

    marks = list(COND.finditer(region))
    sections = {}
    out = []
    for i, mk in enumerate(marks):
        no = mk.group(1)
        body_start = mk.end()
        body_end = marks[i + 1].start() if i + 1 < len(marks) else len(region)
        body = region[body_start:body_end].strip()
        major = no.split('.')[0]
        # a heading for section <major> lives in the gap before its .1
        if no.endswith('.1') or major not in sections:
            gap_start = marks[i - 1].end() if i else 0
            gap = region[gap_start:mk.start()]
            for sm in SECT.finditer(gap):
                if sm.group(1) == major:
                    sections[major] = sm.group(2).strip()
        if len(body) < 40:          # fragments / TOC rows
            continue
        # section 1 is Definitions/interpretation boilerplate, not a measure
        if major == '1' and (DEFN.match(body) or 'shall' not in body[:600]):
            continue
        out.append((no, sections.get(major), body))
    return out


def main():
    index = json.load(open(os.path.join(CORPUS, 'index.json')))
    records, per_doc = [], {}
    for e in index:
        path = os.path.join(CORPUS, f"{e['doc_id']}.txt.gz")
        if not os.path.exists(path):
            continue
        text = gzip.open(path, 'rt', errors='replace').read()
        conds = extract(text)
        per_doc[e['doc_id']] = len(conds)
        arch = archetype(e.get('project'))
        for no, sect, body in conds:
            records.append({
                'condition_id': f"federal-{e['doc_id']}-{no}",
                'source_doc': e.get('url'),
                'source_title': (e.get('title') or '')[:120],
                'jurisdiction': 'federal',
                'project_id': e.get('project_id'),
                'project': e.get('project'),
                'project_archetype': arch,
                'condition_no': no,
                'section_title': sect,
                'discipline': section_discipline(sect) or 'other',
                'discipline_source': 'section_title' if sect else 'none',
                'measure_text': body[:2500],
            })
    buf = gzip.compress(json.dumps(records).encode(), mtime=0)
    open(OUT, 'wb').write(buf)
    docs_with = sum(1 for v in per_doc.values() if v)
    print(f'{len(records)} conditions from {docs_with}/{len(per_doc)} docs '
          f'-> {OUT}')
    from collections import Counter
    print('by discipline:', Counter(r['discipline']
                                    for r in records).most_common(10))
    print('no-section share:',
          sum(1 for r in records if r['discipline_source'] == 'none'),
          '/', len(records))


if __name__ == '__main__':
    main()
