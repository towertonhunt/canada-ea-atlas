#!/usr/bin/env python3
"""Build data/projects_canada.geojson from the raw registry harvests.

Sources merged:
  - projects.geojson            Ontario REA projects (existing, with doc libraries)
  - data/raw/federal_layer*.geojson   IAAC assessment inventory (Completed / In progress / Terminated)
  - data/raw/bc_epic_projects.json    BC EAO project list (EPIC API)
  - data/raw/ns_ea_projects.html      Nova Scotia EA project table (no coordinates yet)
"""
import json
import re
import html as htmllib
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'data', 'raw')
OUT = os.path.join(ROOT, 'data', 'projects_canada.geojson')

features = []


def add(feat):
    p = feat['properties']
    if 'category' not in p:
        p['category'] = categorize(p.get('type') or '')
    features.append(feat)


CATEGORY_RULES = [
    ('wind', ['wind', 'éolien', 'eolien']),
    ('solar', ['solar', 'solaire']),
    ('biogas', ['biogas', 'anaerobic', 'biomass', 'bioenergy', 'biométhane',
                'biomethane', 'biomasse']),
    ('hydro', ['hydro', 'dam', 'water power', 'waterpower', 'barrage',
               'digue', 'rivière', 'riviere']),
    ('mining', ['mine', 'mining', 'quarry', 'aggregate', 'coal', 'metal',
                'minier', 'minière', 'miniere', 'carrière', 'carriere',
                "banc d'emprunt"]),
    ('oil_gas', ['oil', 'gas', 'lng', 'pipeline', 'petroleum', 'refinery',
                 'hydrocarbure', 'oléoduc', 'oleoduc', 'gazoduc',
                 'pétrolière', 'petroliere', 'gaz naturel']),
    ('nuclear', ['nuclear', 'uranium', 'nucléaire', 'nucleaire']),
    ('energy_other', ['energy', 'electric', 'transmission', 'power',
                      'énergie', 'energie', 'centrale']),
    ('transport', ['highway', 'road', 'rail', 'bridge', 'port', 'terminal',
                   'airport', 'ferry', 'transport', 'marine', 'routière',
                   'routiere', 'ferroviaire', 'aéroport', 'aeroport', 'quai']),
    ('water', ['water', 'wastewater', 'sewage', 'flood', 'irrigation',
               'reservoir', 'dredg', 'milieux humides', 'hydrique',
               'réservoir', 'dragage', 'eaux']),
    ('industrial', ['industrial', 'plant', 'facility', 'manufactur', 'pulp',
                    'mill', 'smelter', 'industrie', 'métallurgique',
                    'metallurgique', 'chimique', 'usine']),
    ('waste', ['waste', 'landfill', 'hazardous', 'matières résiduelles',
               'matieres residuelles', 'déchet', 'dechet', 'sols contaminés',
               'sols contamines']),
    ('agriculture', ['agricult', 'production animale', 'farm', 'élevage',
                     'elevage']),
    ('tourism', ['tourist', 'resort', 'récréotouristique', 'recreotouristique']),
]


def categorize(type_str):
    t = str(type_str).lower()
    for cat, keys in CATEGORY_RULES:
        if any(k in t for k in keys):
            return cat
    return 'other'


# ── Ontario REA (existing map data, keep everything) ─────────────────
ont = json.load(open(os.path.join(ROOT, 'projects.geojson')))
for f in ont['features']:
    p = f['properties']
    p['jurisdiction'] = 'Ontario (REA)'
    p['source'] = 'ontario_rea'
    p['status'] = 'Approved'
    add(f)
print(f'ontario REA: {len(ont["features"])}')

# ── Federal IAAC inventory ───────────────────────────────────────────
LAYER_STATUS = {0: 'Completed', 1: 'In progress', 2: 'Terminated'}
n_fed = 0
for lid, status in LAYER_STATUS.items():
    path = os.path.join(RAW, f'federal_layer{lid}.geojson')
    if not os.path.exists(path):
        continue
    d = json.load(open(path))
    for f in d['features']:
        p = f.get('properties') or {}
        geom = f.get('geometry')
        if not geom or geom.get('coordinates') in (None, [None, None]):
            continue
        name = (p.get('ProjectName') or p.get('Name') or p.get('NAME') or
                p.get('project_name') or p.get('Title') or 'Unnamed project')
        url = (p.get('RegistryLink') or p.get('URL') or p.get('Link') or
               p.get('registry_url') or None)
        props = {
            'name': str(name).strip(),
            'jurisdiction': 'Federal (IAAC)',
            'source': 'federal_iaac',
            'status': status,
            'type': (p.get('ProjectType') or p.get('Type') or 'other'),
            'proponent': p.get('Proponent') or p.get('proponent'),
            'registry_url': url,
            'raw': {k: v for k, v in p.items() if v not in (None, '')},
        }
        add({'type': 'Feature', 'geometry': geom, 'properties': props})
        n_fed += 1
print(f'federal: {n_fed}')

# ── BC EPIC ──────────────────────────────────────────────────────────
bc_path = os.path.join(RAW, 'bc_epic_projects.json')
n_bc = 0
if os.path.exists(bc_path):
    bc = json.load(open(bc_path))[0]['searchResults']
    for p in bc:
        c = p.get('centroid') or []
        try:
            lon, lat = float(c[0]), float(c[1])
        except (ValueError, TypeError, IndexError):
            continue
        dec = p.get('eacDecision')
        if isinstance(dec, dict):
            dec = dec.get('name')
        props = {
            'name': p.get('name'),
            'jurisdiction': 'British Columbia (EAO)',
            'source': 'bc_epic',
            'status': p.get('status') or p.get('eaStatus'),
            'type': p.get('type') or 'other',
            'proponent': (p.get('proponent') or {}).get('name')
                         if isinstance(p.get('proponent'), dict) else p.get('proponent'),
            'decision': dec,
            'region': p.get('region'),
            'location': p.get('location'),
            'registry_url': 'https://projects.eao.gov.bc.ca/p/' + p['_id']
                            if p.get('_id') else None,
            'description': (p.get('description') or '')[:400],
        }
        add({'type': 'Feature',
             'geometry': {'type': 'Point', 'coordinates': [lon, lat]},
             'properties': props})
        n_bc += 1
print(f'bc: {n_bc}')

# ── Federal IAAC (full inventory via exploration api-map) ────────────
apimap = os.path.join(RAW, 'federal_apimap.geojson')
n_fed2 = 0
if os.path.exists(apimap):
    d = json.load(open(apimap))
    for f in d['features']:
        p = f.get('properties') or {}
        geom = f.get('geometry')
        # normalize MultiPoint -> Point (first location)
        if geom and geom.get('type') == 'MultiPoint' and geom.get('coordinates'):
            geom = {'type': 'Point', 'coordinates': geom['coordinates'][0]}
        pid = p.get('project_id')
        props = {
            'name': p.get('project_name_en') or p.get('project_name_fr') or 'Unnamed',
            'jurisdiction': 'Federal (IAAC)',
            'source': 'federal_iaac',
            'status': p.get('project_state_en'),
            'type': p.get('project_cat_en') or 'other',
            'proponent': p.get('proponent_en'),
            'location': p.get('location_en'),
            'province_codes': p.get('province_codes'),
            'description': (p.get('description_en') or '')[:400],
            'registry_url': f'https://iaac-aeic.gc.ca/050/evaluations/proj/{pid}'
                            if pid else p.get('project_url_en'),
        }
        add({'type': 'Feature', 'geometry': geom, 'properties': props})
        n_fed2 += 1
print(f'federal (api-map): {n_fed2}')

# ── Ontario provincial EAs (Individual/Comprehensive, by sector) ─────
on_cat = os.path.join(RAW, 'on_ea_projects_category.html')
n_onp = 0
if os.path.exists(on_cat):
    h = open(on_cat, encoding='utf-8', errors='replace').read()
    SECTIONS = ['Electricity', 'Mining', 'Forestry', 'Municipal infrastructure',
                'Waste management', 'Transit', 'Transportation', 'Other']
    for part in re.split(r'<h2[^>]*>', h):
        mt = re.match(r'\s*([^<]+)</h2>(.*)', part, re.S)
        if not mt or mt.group(1).strip() not in SECTIONS:
            continue
        sector = mt.group(1).strip()
        for u, t in re.findall(r'<a href="([^"]+)"[^>]*>(.*?)</a>', mt.group(2), re.S):
            name = re.sub(r'\s+', ' ',
                          htmllib.unescape(re.sub(r'<[^>]+>', ' ', t))).strip()
            # skip guides/reference pages mixed into the lists
            if (not name or 'back to top' in name.lower()
                    or name.lower().startswith(('guide', 'environmental assessment requirement'))):
                continue
            if u.startswith('/'):
                u = 'https://www.ontario.ca' + u
            props = {
                'name': name,
                'jurisdiction': 'Ontario (Provincial EA)',
                'source': 'on_provincial_ea',
                'status': None,
                'type': sector,
                'proponent': None,
                'registry_url': u,
            }
            add({'type': 'Feature', 'geometry': None, 'properties': props})
            n_onp += 1
print(f'ontario provincial EA (no coords yet): {n_onp}')

# ── Quebec REE (table + coordinates scraped from carte.asp pages) ────
qc_path = os.path.join(RAW, 'qc_ree_resultats.html')
n_qc = 0
if os.path.exists(qc_path):
    coords = {}
    cpath = os.path.join(RAW, 'qc_coords.json')
    if os.path.exists(cpath):
        coords = json.load(open(cpath))
    h = open(qc_path, encoding='utf-8', errors='replace').read()
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', h, re.S)
    for r in rows[1:]:
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', r, re.S)
        if len(cells) < 5:
            continue
        strip = lambda c: re.sub(r'\s+', ' ',
                                 htmllib.unescape(re.sub(r'<[^>]+>', ' ', c))).strip()
        name, prop, sector, muni, updated = (strip(c) for c in cells[:5])
        if not name or name.startswith('Nom du projet'):
            continue
        dm = re.search(r'no_dossier=([^"&]+)', r)
        dossier = dm.group(1) if dm else None
        geom = None
        if dossier and dossier in coords:
            lat, lon = coords[dossier]
            # sanity: QC latitudes 44..63, longitudes -80..-57
            if 40 < lat < 65 and -85 < lon < -50:
                geom = {'type': 'Point', 'coordinates': [lon, lat]}
        props = {
            'name': name,
            'jurisdiction': 'Quebec (MELCCFP)',
            'source': 'qc_ree',
            'status': None,
            'type': sector,
            'proponent': prop,
            'municipality': muni,
            'updated': updated,
            'registry_url': ('https://www.ree.environnement.gouv.qc.ca/fiche.asp?no_dossier=' + dossier)
                            if dossier else None,
        }
        add({'type': 'Feature', 'geometry': geom, 'properties': props})
        n_qc += 1
print(f'quebec: {n_qc}')

# ── Nova Scotia (no coordinates in source; parsed for list/search) ───
ns_path = os.path.join(RAW, 'ns_ea_projects.html')
n_ns = 0
if os.path.exists(ns_path):
    h = open(ns_path, encoding='utf-8', errors='replace').read()
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', h, re.S)
    for r in rows[1:]:
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', r, re.S)
        if len(cells) < 3:
            continue
        link = re.search(r'href="([^"]+)"', cells[0])
        strip = lambda c: re.sub(r'\s+', ' ',
                                 htmllib.unescape(re.sub(r'<[^>]+>', ' ', c))).strip()
        name, prop, date = strip(cells[0]), strip(cells[1]), strip(cells[2])
        if not name or name == 'NAME':
            continue
        url = link.group(1) if link else None
        if url and url.startswith('/'):
            url = 'https://novascotia.ca' + url
        props = {
            'name': name,
            'jurisdiction': 'Nova Scotia (NSECC)',
            'source': 'ns_ea',
            'status': None,
            'type': 'other',
            'proponent': prop,
            'date': date,
            'registry_url': url,
        }
        # No coordinates published; geometry null keeps them list-searchable
        add({'type': 'Feature', 'geometry': None, 'properties': props})
        n_ns += 1
print(f'nova scotia (no coords yet): {n_ns}')

json.dump({'type': 'FeatureCollection', 'features': features}, open(OUT, 'w'))
print(f'TOTAL: {len(features)} -> {OUT}')
