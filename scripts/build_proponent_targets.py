#!/usr/bin/env python3
"""Build the ranked list of proponents whose own websites are worth crawling.

Registries capture only what a regulator files. Class EA reports, ESRs, open
house material and monitoring reports live on the proponent's site (the
Hydro One harvest in ontario-classea/ is the model). This aggregates every
proponent named across the map and the major-project inventories, drops
government bodies (their documents are already on a registry), merges
naming variants, ranks by footprint, and looks up official websites on
Wikidata for the top tier.

  python3 scripts/build_proponent_targets.py              # rebuild + lookup
  python3 scripts/build_proponent_targets.py --no-lookup  # rebuild only

-> data/raw/proponents/targets.json  (consumed by proponent_discover.py)
Hand corrections go in data/raw/proponents/overrides.json:
  {"<key>": {"website": "...", "skip": true, "aliases": ["..."]}}
"""
import argparse
import collections
import glob
import json
import os
import re
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'data', 'raw')
OUT_DIR = os.path.join(RAW, 'proponents')
OUT = os.path.join(OUT_DIR, 'targets.json')
OVERRIDES = os.path.join(OUT_DIR, 'overrides.json')
UA = {'User-Agent': 'CanadaEAAtlas/1.0 (https://canadaeaatlas.towerton.ca)'}

# Public bodies, utilities of the Crown excepted below, and generic labels.
GOV = re.compile(
    r"\b(department|ministry|minist[èe]re|parks canada|fisheries|oceans canada|"
    r"canada border|coast guard|national capital|transport canada|correctional|"
    r"environment and climate|national defence|dnd|pspc|public services|rcmp|"
    r"royal canadian|canada post|nav canada|agriculture and agri|national research|"
    r"city of|town of|village of|municipality|county|region of|regional|district of|"
    r"township|first nation|nation|band|tribal|province of|government|agency|"
    r"secretariat|infrastructure canada|indigenous services|crown-indigenous|"
    r"natural resources canada|nrcan|health canada|statistics|revenue|library|"
    r"museum|school|university|college|hospital|health|conservation authority|"
    r"external proponent|external|not applicable|upland owner|security|"
    r"transportation|ducks unlimited|telus|bell canada|rogers|shaw|airport|"
    r"a[ée]roport|port authority|airports|metro vancouver|translink|commission)\b", re.I)

# Names that trip GOV but are exactly the proponents we want.
KEEP = re.compile(r"\b(hydro|power|energy|generation|nuclear|mines?|mining|gold|"
                  r"lithium|nickel|iron|potash|uranium|lng|pipeline|resources)\b", re.I)

ALIAS = {
    'hydro one': ['hydro one networks', 'hydro one networks incorporated'],
    'tc energy': ['transcanada', 'transcanada energy', 'transcanada pipelines',
                  'nova gas transmission'],
    'teck resources': ['teck coal', 'evr operations', 'elk valley resources'],
    'ontario power generation': ['opg', 'ontario power generation inc'],
    'canadian natural resources': ['canadian natural upgrading',
                                   'canadian natural resources limited', 'cnrl'],
    'suncor energy': ['fort hills energy', 'suncor'],
    'shell canada': ['shell canada energy', 'lng canada'],
    'agnico eagle mines': ['detour gold', 'kirkland lake gold', 'agnico eagle'],
    'enbridge': ['enbridge frontier', 'enbridge pipelines', 'northern gateway pipelines',
                 'enbridge inc'],
    'nova scotia power': ['nova scotia power incorporated nspi', 'nspi'],
    'atura power': ['portlands energy centre', 'napanee generating station'],
    'fortis bc': ['fortisbc', 'fortisbc energy', 'fortis bc inc'],
    'woodfibre lng': ['woodfibre natural gas'],
    'north west redwater partnership': ['north west upgrading'],
    'capital power': ['capital power corporation', 'capital power generation'],
    'newfoundland and labrador hydro': ['nalcor energy', 'nalcor'],
    'bc hydro': ['bc hydro and power authority', 'british columbia hydro'],
    'vale': ['vale canada', 'vale inco', 'inco'],
    'glencore': ['glencore canada', 'xstrata', 'falconbridge'],
}

# Known Class-EA / proponent-hosted document publishers the data may under-count.
SEED = [
    'Ontario Power Generation', 'Atura Power', 'TC Energy', 'Capital Power',
    'Hydro One', 'Bruce Power', 'Nuclear Waste Management Organization', 'Enbridge',
    'BC Hydro', 'Manitoba Hydro', 'Hydro-Québec', 'SaskPower', 'NB Power',
    'Nova Scotia Power', 'Newfoundland and Labrador Hydro', 'Metrolinx',
    'Ontario Northland', 'Agnico Eagle Mines', 'Newmont', 'Barrick Gold', 'Vale',
    'Glencore', 'Teck Resources', 'Suncor Energy', 'Canadian Natural Resources',
    'Imperial Oil', 'Cenovus Energy', 'Rio Tinto', 'Iron Ore Company of Canada',
    'ArcelorMittal', 'Champion Iron', 'Wyloo', 'Generation Mining', 'Frontier Lithium',
    'Canada Nickel', 'IAMGOLD', 'Equinox Gold', 'Kinross Gold', 'New Gold',
    'Alamos Gold', 'Evolution Mining', 'Wesdome', 'First Quantum Minerals',
    'Hudbay Minerals', 'Foran Mining', 'Nutrien', 'BHP', 'K+S Potash', 'Cameco',
    'Orano', 'Denison Mines', 'NexGen Energy', 'Ring of Fire Metals',
    'Northern Graphite', 'Avalon Advanced Materials', 'Rock Tech Lithium',
    'Electra Battery Materials', 'Boralex', 'Northland Power', 'Innergex',
    'EDF Renewables', 'Pattern Energy', 'Brookfield Renewable', 'TransAlta', 'ATCO',
    'Fortis BC', 'Emera', 'AltaLink', 'Woodfibre LNG', 'Cedar LNG', 'Coastal GasLink',
    'Trans Mountain', 'Xeneca Power', 'Coral Rapids Power', 'Algonquin Power',
    'Evolugen', 'Kruger Energy', 'Elenchus', 'Ontario Waterpower Association',
]


def norm(n):
    n = re.sub(r'\(.*?\)', '', n).replace('&', 'and')
    n = re.sub(r"\b(inc|incorporated|ltd|limited|corp|corporation|co|company|llp|lp|"
               r"l\.p|ulc|s\.e\.c|the|ltée|s\.a|plc)\b\.?", '', n, flags=re.I)
    return re.sub(r'[^a-z0-9 ]+', ' ', n.casefold()).strip()


LEAD_GOV = re.compile(r'^\s*(the\s+)?(department|ministry|minist[èe]re|city|town|village|'
                      r'municipality|county|region|district|province|government|'
                      r'her majesty|his majesty|crown)\b', re.I)


def is_public_body(name):
    if LEAD_GOV.search(name):
        return True            # "Department of Natural Resources" is not a proponent site
    return bool(GOV.search(name)) and not KEEP.search(name)


def aggregate():
    T = collections.defaultdict(lambda: {
        'variants': collections.Counter(), 'projects': 0, 'docs': 0,
        'sources': collections.Counter(), 'sectors': collections.Counter(),
        'value_cad': 0, 'websites': collections.Counter()})

    def add(name, source, docs=0, sector=None, value=0, website=None):
        name = (name or '').strip()
        if not name or is_public_body(name):
            return
        parts = re.split(r'\s*(?:;|/|\band\b)\s*', name) if len(name) > 70 else [name]
        for part in parts:
            part = part.strip(' ,)(')
            k = norm(part)
            if len(k) < 3 or is_public_body(part):
                continue
            t = T[k]
            t['variants'][part] += 1
            t['projects'] += 1
            t['docs'] += docs or 0
            t['sources'][source] += 1
            if sector:
                t['sectors'][sector] += 1
            t['value_cad'] += value or 0
            if website:
                t['websites'][website] += 1

    geo = json.load(open(os.path.join(ROOT, 'data', 'projects_canada.geojson')))
    for f in geo['features']:
        p = f['properties']
        add(p.get('proponent'), p.get('source'), p.get('doc_count'),
            p.get('category'), 0, p.get('proponent_url'))
    for path in glob.glob(os.path.join(RAW, 'gap_inventories', '*.json')):
        d = json.load(open(path))
        rows = d if isinstance(d, list) else d.get('rows') or d.get('projects') or []
        for r in rows:
            add(r.get('proponent'), 'inv:' + os.path.basename(path)[:-5], 0,
                r.get('sector'), r.get('value_cad') or 0)
    for s in SEED:
        add(s, 'seed')
    return T


def merge_aliases(T, overrides):
    canon = {}
    for k, vs in ALIAS.items():
        for v in vs:
            canon[norm(v)] = k
    for k, o in overrides.items():
        for v in o.get('aliases', []):
            canon[norm(v)] = k
    merged = {}
    for k, t in T.items():
        target = canon.get(k, k)
        if target == k:
            for ak in list(ALIAS) + list(overrides):
                if ak != k and re.search(rf'\b{re.escape(ak)}\b', k):
                    target = ak
                    break
        m = merged.setdefault(target, {
            'variants': collections.Counter(), 'projects': 0, 'docs': 0,
            'sources': collections.Counter(), 'sectors': collections.Counter(),
            'value_cad': 0, 'websites': collections.Counter()})
        m['variants'].update(t['variants'])
        m['projects'] += t['projects']
        m['docs'] += t['docs']
        m['sources'].update(t['sources'])
        m['sectors'].update(t['sectors'])
        m['value_cad'] += t['value_cad']
        m['websites'].update(t['websites'])
    return merged


def site_root(url):
    """Crawl seeds are site roots; a deep project URL (e.g. Ontario's
    proponent_url) is kept separately as an extra seed."""
    if not url:
        return None
    if not url.startswith('http'):
        url = 'https://' + url
    p = urllib.parse.urlsplit(url)
    return f'{p.scheme}://{p.netloc}/'


def display_name(key, variants):
    """For an alias group, the variant that best matches the canonical key;
    otherwise the most common spelling."""
    if key in ALIAS:
        for v, _ in variants.most_common():
            if norm(v) == key:
                return v
        return key.title()
    return variants.most_common(1)[0][0]


def score(t):
    return (t['projects'] * 3 + t['docs'] * 0.05 + t['value_cad'] / 1e8
            + (20 if 'seed' in t['sources'] else 0))


STOP = {'inc', 'ltd', 'limited', 'corp', 'corporation', 'company', 'co', 'the',
        'plc', 'canada', 'canadian', 'group', 'of', 'and'}


def wikidata_site(name):
    """Official website (P856) of the best company-like Wikidata match."""
    def api(**params):
        q = urllib.parse.urlencode(dict(params, format='json'))
        req = urllib.request.Request('https://www.wikidata.org/w/api.php?' + q, headers=UA)
        return json.load(urllib.request.urlopen(req, timeout=30))
    r = api(action='wbsearchentities', search=name, language='en', type='item', limit=4)
    want = {w for w in re.findall(r'[a-z0-9]+', name.lower())
            if w not in STOP and len(w) > 2}
    for hit in r.get('search', []):
        got = set(re.findall(r'[a-z0-9]+', (hit.get('label') or '').lower()))
        # "Canadian Natural Resources" must not resolve to "Canadian National Railway"
        if want and len(want & got) < max(1, len(want) - 1):
            continue
        d = (hit.get('description') or '').lower()
        if not re.search(r'compan|corporat|utility|business|enterprise|mining|energy|'
                         r'producer|subsidiary|operator|developer|firm|conglomerate|'
                         r'organi[sz]ation|crown|electric|pipeline|manufactur|oil|gas',
                         d):
            continue
        c = api(action='wbgetclaims', entity=hit['id'], property='P856')
        for cl in c.get('claims', {}).get('P856', []):
            u = cl.get('mainsnak', {}).get('datavalue', {}).get('value')
            if u:
                return u, hit['id']
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-lookup', action='store_true')
    ap.add_argument('--top', type=int, default=300, help='lookup websites for top N')
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    overrides = json.load(open(OVERRIDES)) if os.path.exists(OVERRIDES) else {}
    overrides = {k: v for k, v in overrides.items() if isinstance(v, dict)}  # drop _doc
    prior = {t['key']: t for t in json.load(open(OUT))} if os.path.exists(OUT) else {}

    merged = merge_aliases(aggregate(), overrides)
    out = []
    for k, t in merged.items():
        o = overrides.get(k, {})
        if o.get('skip'):
            continue
        rec = {
            'key': k,
            'name': (o.get('name') or display_name(k, t['variants'])),
            'variants': [v for v, _ in t['variants'].most_common(8)],
            'projects': t['projects'], 'docs': t['docs'],
            'value_cad': round(t['value_cad']),
            'sources': dict(t['sources']),
            'sectors': dict(t['sectors'].most_common(3)),
            'website': site_root(o.get('website')
                                 or (t['websites'].most_common(1)[0][0] if t['websites'] else None)
                                 or prior.get(k, {}).get('website')),
            'seed_urls': sorted({u for u in list(t['websites']) + prior.get(k, {}).get('seed_urls', [])
                                 if u and urllib.parse.urlsplit(u).path.strip('/')})[:10],
            'website_source': ('override' if o.get('website') else
                               prior.get(k, {}).get('website_source')),
            'wikidata': prior.get(k, {}).get('wikidata'),
            'score': round(score(t), 1),
            'browser_first': bool(o.get('browser_first')),
        }
        out.append(rec)
    out.sort(key=lambda x: -x['score'])
    print(f'{len(out)} corporate/utility proponents; '
          f'{sum(1 for t in out if t["website"])} with a website')

    if not args.no_lookup:
        found = 0
        for i, t in enumerate(out[:args.top]):
            if t['website'] or t.get('wikidata_miss'):
                continue
            try:
                u, qid = wikidata_site(t['name'])
                if not u:
                    base = re.sub(r'\b(inc|ltd|limited|corp|corporation|company|plc)\b\.?',
                                  '', t['name'], flags=re.I).strip(' .,')
                    if base != t['name']:
                        u, qid = wikidata_site(base)
                if u:
                    t.update(website=site_root(u), wikidata=qid, website_source='wikidata')
                    found += 1
                else:
                    t['wikidata_miss'] = True
            except Exception:                                    # noqa: BLE001
                pass
            time.sleep(0.25)
        print(f'wikidata: {found} websites found; top {args.top} now '
              f'{sum(1 for t in out[:args.top] if t["website"])} with a site')
    json.dump(out, open(OUT, 'w'), ensure_ascii=False, indent=1)
    print('->', OUT)


if __name__ == '__main__':
    main()
