#!/usr/bin/env python3
"""Backfill proponent + coordinates into our map features from external
major-project inventories, using the gap reconciler's matcher.

Motivation (2026-07-10, Hydro One case): the Ontario provincial EA source
publishes only name+url, so majors like the Waasigan transmission line sat
on the map with no proponent and no pin — unfindable by proponent search
and invisible spatially — while NRCan's Major Projects Inventory carries
both fields for the same projects.

Reads:  data/projects_canada.geojson, data/raw/gap_inventories/*.json
Writes: data/raw/inventory_enrichment.json
          { "<jurisdiction>||<name>": { "proponent": ..., "coords": [lon,lat],
              "source": "nrcan_mpi", "ext_name": ..., "score": ... }, ... }

build_national_geojson.py applies this file at build time: proponent fills
only when ours is empty; coords fill only when we have no geometry (flagged
geocode='inventory'). Conservative: only STRONG matches enrich.

Run:  python3 scripts/enrich_from_inventories.py
"""
import glob
import json
import os
import sys

from gap_reconcile import INV_DIR, build_idf, load_ours, name_score, tokens

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, 'data', 'raw', 'inventory_enrichment.json')

# Enrichment is held to a much stricter standard than gap detection: a
# wrong pin or proponent corrupts data, a missed enrichment costs nothing.
MAX_SIDE = 0.72   # best-covered name side must clear this
MIN_SIDE = 0.50   # AND the other side must also be mostly explained

# our jurisdiction string -> province code, for consistency gating
JUR_PROV = {
    'British Columbia (EAO)': 'BC', 'Quebec (MELCCFP)': 'QC',
    'Nova Scotia (NSECC)': 'NS', 'Newfoundland & Labrador (ECC)': 'NL',
    'Manitoba (Environment Act)': 'MB', 'Ontario (REA)': 'ON',
    'Ontario (Provincial EA)': 'ON',
}
# AMIS entries are historic abandoned-mine sites with short generic names;
# never take active-project attributes onto them.
SKIP_JUR = {'Ontario (Abandoned Mines)'}


def main():
    ours = load_ours()
    idf = build_idf(ours)
    # only features missing proponent or coords can benefit
    needy = [r for r in ours
             if r['jurisdiction'] not in SKIP_JUR
             and (not r['prop_tok'] or not r['coords'])]
    print(f'{len(ours)} features, {len(needy)} enrichable '
          f'(missing proponent and/or coords, non-AMIS)')

    enrich = {}
    for path in sorted(glob.glob(os.path.join(INV_DIR, '*.json'))):
        inv = json.load(open(path))
        src = inv.get('source') or os.path.basename(path)
        for ext in inv.get('projects') or []:
            et = tokens(ext.get('name'))
            if not et:
                continue
            eprov = (ext.get('province') or '').strip().upper() or None
            best, best_r = 0.0, None
            for r in needy:
                oprov = JUR_PROV.get(r['jurisdiction'])
                if eprov and oprov and eprov != oprov:
                    continue
                if len(et & r['name_tok']) < 2:
                    continue  # one shared word is never enough to enrich
                cov_ext = name_score(et, r['name_tok'], idf)
                cov_our = name_score(r['name_tok'], et, idf)
                if max(cov_ext, cov_our) < MAX_SIDE or \
                        min(cov_ext, cov_our) < MIN_SIDE:
                    continue
                s = (cov_ext + cov_our) / 2
                if s > best:
                    best, best_r = s, r
            if best_r is None:
                continue
            r = best_r
            key = f"{r['jurisdiction']}||{r['name']}"
            prev = enrich.get(key)
            if prev and prev['score'] >= round(best, 3):
                continue
            rec = {'source': src, 'ext_name': ext.get('name'),
                   'score': round(best, 3)}
            if not r['prop_tok'] and ext.get('proponent'):
                rec['proponent'] = str(ext['proponent']).strip()
            if not r['coords'] and ext.get('coords'):
                rec['coords'] = ext['coords']
            if 'proponent' in rec or 'coords' in rec:
                enrich[key] = rec

    json.dump(enrich, open(OUT, 'w'), ensure_ascii=False, indent=1,
              sort_keys=True)
    n_prop = sum(1 for v in enrich.values() if 'proponent' in v)
    n_geo = sum(1 for v in enrich.values() if 'coords' in v)
    print(f'wrote {len(enrich)} enrichments ({n_prop} proponents, '
          f'{n_geo} coordinate fills) -> {OUT}')
    for k, v in sorted(enrich.items()):
        tags = '+'.join(t for t in ('proponent', 'coords') if t in v)
        print(f'  [{tags:>16}] {k[:70]}  <- {v["ext_name"][:40]} '
              f'({v["score"]})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
