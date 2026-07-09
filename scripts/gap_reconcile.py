#!/usr/bin/env python3
"""Gap reconciliation: find major projects that authoritative external
inventories list but our map is missing.

Offline engine. Reads:
  - data/projects_canada.geojson                 (our dataset)
  - data/raw/gap_inventories/*.json              (external inventories,
                                                  common schema below)
Writes:
  - data/gap_report.json                         (matched / weak / gap)

External inventory schema (one JSON file per source, emitted by the
fetch-gap-reconcile lane):
  {
    "source": "nrcan_mpi",
    "source_label": "NRCan Major Projects Inventory",
    "fetched": "2026-07-09",
    "projects": [
      { "ext_id": "...", "name": "...", "proponent": null,
        "province": null, "sector": null, "value_cad": null,
        "coords": [lon, lat] | null, "url": null, "status": null },
      ...
    ]
  }

Matching is deliberately conservative: a project is only called a GAP
(likely missing) when no candidate in our dataset scores above a low
floor. Everything in the grey zone is emitted as WEAK for human review
rather than silently asserted present or absent.

Run:  python3 scripts/gap_reconcile.py
"""
import glob
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEOJSON = os.path.join(HERE, 'data', 'projects_canada.geojson')
INV_DIR = os.path.join(HERE, 'data', 'raw', 'gap_inventories')
OUT = os.path.join(HERE, 'data', 'gap_report.json')

# Score thresholds. score is in [0, ~1.3] (overlap 0-1 + geo/proponent boosts).
STRONG = 0.72   # >= this: confidently already in our dataset
FLOOR = 0.40    # <  this: likely a genuine gap; in between: weak/review

# Tokens that carry no identifying signal for a project name.
STOP = {
    'project', 'projects', 'the', 'of', 'and', 'a', 'to', 'for', 'in', 'on',
    'at', 'inc', 'ltd', 'limited', 'corp', 'corporation', 'company', 'co',
    'lp', 'llc', 'ulc', 'partnership', 'phase', 'stage', 'expansion',
    'extension', 'proposed', 'new', 'existing', 'redevelopment',
    'development', 'construction', 'canada', 'canadian', 'ontario', 'quebec',
    'alberta', 'manitoba', 'saskatchewan', 'columbia', 'british', 'scotia',
    'nova', 'brunswick', 'newfoundland', 'labrador', 'yukon', 'nunavut',
    'northwest', 'territories', 'nl', 'bc', 'ab', 'sk', 'mb', 'on', 'qc',
    'ns', 'nb', 'pe', 'pei', 'yt', 'nt', 'nu',
}

_WS = re.compile(r'[^a-z0-9]+')


def tokens(s):
    """Normalize a name to a set of identifying tokens."""
    if not s:
        return set()
    raw = _WS.split(str(s).lower())
    return {t for t in raw if t and t not in STOP and len(t) > 1}


def build_idf(ours):
    """Document frequency -> IDF over our project-name tokens. Rare tokens
    ('detour', 'prosperity') carry real identifying signal; common ones
    ('mine', 'west', 'lake', 'terminal') carry almost none. Unseen tokens
    get the maximum weight."""
    from collections import Counter
    df = Counter()
    for r in ours:
        for t in r['name_tok']:
            df[t] += 1
    n = len(ours)

    def idf(t):
        return math.log((n + 1) / (df.get(t, 0) + 1)) + 1.0
    return idf


def name_score(ext_tok, cand_tok, idf):
    """Fraction of the EXTERNAL name's distinctive (IDF) mass that this
    candidate explains. Using the external side as the denominator means a
    short generic candidate ('Project West') can't score high against a
    distinctive external name ('West Detour') just by sharing one common
    word."""
    if not ext_tok or not cand_tok:
        return 0.0
    shared = ext_tok & cand_tok
    if not shared:
        return 0.0
    tot = sum(idf(t) for t in ext_tok)
    if tot == 0:
        return 0.0
    return sum(idf(t) for t in shared) / tot


def prop_score(ext_tok, cand_tok, idf):
    """Same IDF-weighted coverage for proponent names."""
    return name_score(ext_tok, cand_tok, idf)


def haversine_km(c1, c2):
    lon1, lat1 = c1
    lon2, lat2 = c2
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(h)))


def load_ours():
    d = json.load(open(GEOJSON))
    rows = []
    for f in d['features']:
        p = f['properties']
        g = f.get('geometry')
        coords = None
        if g and g.get('type') == 'Point' and g.get('coordinates'):
            c = g['coordinates']
            if isinstance(c, list) and len(c) == 2:
                coords = (c[0], c[1])
        rows.append({
            'id': p.get('id'),
            'name': p.get('name') or '',
            'name_tok': tokens(p.get('name')),
            'prop_tok': tokens(p.get('proponent')),
            'jurisdiction': p.get('jurisdiction'),
            'coords': coords,
        })
    return rows


def best_match(ext, ours, idf):
    """Return (best_score, best_row) for one external project. Score is
    IDF-weighted name coverage in [0,1], plus small proponent/geo boosts."""
    et = tokens(ext.get('name'))
    ep = tokens(ext.get('proponent'))
    ec = ext.get('coords')
    ec = tuple(ec) if isinstance(ec, list) and len(ec) == 2 else None
    best_s, best_r = 0.0, None
    for r in ours:
        s = name_score(et, r['name_tok'], idf)
        if s == 0:
            continue  # need at least one shared distinctive token to anchor
        # proponent agreement is a strong corroborator
        if ep and r['prop_tok']:
            s += 0.25 * prop_score(ep, r['prop_tok'], idf)
        # geographic proximity: reward near, don't punish (many of ours
        # lack coords or are gazetteer-approximate)
        if ec and r['coords']:
            dkm = haversine_km(ec, r['coords'])
            if dkm <= 10:
                s += 0.20
            elif dkm <= 35:
                s += 0.10
            elif dkm > 150 and s < STRONG:
                s -= 0.15  # name looked similar but far away -> distrust
        if s > best_s:
            best_s, best_r = s, r
    return best_s, best_r


def classify(score):
    if score >= STRONG:
        return 'matched'
    if score >= FLOOR:
        return 'weak'
    return 'gap'


def value_sort_key(rec):
    v = rec['ext'].get('value_cad')
    return -(v if isinstance(v, (int, float)) else 0)


def main():
    if not os.path.isdir(INV_DIR):
        print(f'No inventory dir yet ({INV_DIR}); nothing to reconcile.')
        print('The fetch-gap-reconcile lane populates it on Actions.')
        # still emit an empty, well-formed report so downstream is stable
        json.dump({'inventories': [], 'summary': {}, 'results': []},
                  open(OUT, 'w'), indent=2)
        return 0

    ours = load_ours()
    idf = build_idf(ours)
    print(f'loaded {len(ours)} of our projects')

    inv_files = sorted(glob.glob(os.path.join(INV_DIR, '*.json')))
    if not inv_files:
        print('inventory dir empty; nothing to reconcile yet.')
        json.dump({'inventories': [], 'summary': {}, 'results': []},
                  open(OUT, 'w'), indent=2)
        return 0

    inventories = []
    results = []
    for path in inv_files:
        try:
            inv = json.load(open(path))
        except Exception as e:
            print(f'SKIP {os.path.basename(path)}: {e}')
            continue
        projs = inv.get('projects') or []
        inventories.append({
            'source': inv.get('source') or os.path.basename(path),
            'label': inv.get('source_label'),
            'fetched': inv.get('fetched'),
            'count': len(projs),
        })
        for ext in projs:
            score, r = best_match(ext, ours, idf)
            results.append({
                'source': inv.get('source') or os.path.basename(path),
                'ext': ext,
                'verdict': classify(score),
                'score': round(score, 3),
                'match': None if r is None else {
                    'id': r['id'], 'name': r['name'],
                    'jurisdiction': r['jurisdiction'],
                },
            })

    # gaps first (majors by value), then weak, then matched
    order = {'gap': 0, 'weak': 1, 'matched': 2}
    results.sort(key=lambda x: (order[x['verdict']], value_sort_key(x)))

    summary = {}
    for v in ('gap', 'weak', 'matched'):
        summary[v] = sum(1 for x in results if x['verdict'] == v)

    report = {
        'inventories': inventories,
        'summary': summary,
        'thresholds': {'strong': STRONG, 'floor': FLOOR},
        'results': results,
    }
    json.dump(report, open(OUT, 'w'), indent=2, ensure_ascii=False)

    print(f'\nreconciled {sum(i["count"] for i in inventories)} external '
          f'projects across {len(inventories)} inventories')
    print(f'  GAP   (likely missing): {summary["gap"]}')
    print(f'  WEAK  (review):         {summary["weak"]}')
    print(f'  MATCHED:                {summary["matched"]}')
    gaps = [x for x in results if x['verdict'] == 'gap'][:20]
    if gaps:
        print('\ntop likely-missing majors:')
        for x in gaps:
            v = x['ext'].get('value_cad')
            vs = f' (${v/1e9:.1f}B)' if isinstance(v, (int, float)) and v else ''
            prov = x['ext'].get('province') or '?'
            print(f'  - {x["ext"].get("name")}{vs} [{prov}]  score={x["score"]}')
    print(f'\nwrote {OUT}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
