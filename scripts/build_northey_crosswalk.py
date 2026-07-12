#!/usr/bin/env python3
"""Build the Northey landmark-cases crosswalk.

Reads the curated Northey seed (the 39 landmark Canadian EA/IA projects cited in
Rodney Northey, *A Guide to Canada's Impact Assessment Act* (2023)) from the
sibling enviro-permits repo and reconciles each to a project id in this map.

The pid mapping below was hand-verified (2026-07-11) against
data/api/projects.json: federal (IAAC) records are preferred, since the
case-law Northey cites concerns the *federal* EA of each project. Pre-registry
EARP/EARPGO panels that predate the online registry are recorded as unmatched
(they are genuinely absent from every registry — itself a documented gap).

Writes: data/northey_subjects.json
"""
import json
import os
import re

try:
    import openpyxl
except ImportError:
    raise SystemExit("openpyxl required: pip install openpyxl")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = os.path.expanduser(
    "~/Projects/ea_project/enviro-permits/data/raw/northey_projects_seed.xlsx")
OUT = os.path.join(ROOT, "data", "northey_subjects.json")

# northey_shorthand -> (map_id | None, match, confidence, note)
#   match: registry_id | name_verified | unmatched_pre_registry | unmatched
MAP = {
    # --- registry-era, verified to a Federal (IAAC) record ---------------
    "1996 Express Pipeline":        ("fed-f763a49fb3", "name_verified", "high", None),
    "1996 NWT Diamond Mine":        ("fed-4caf45940e", "name_verified", "high", None),
    "1997 Terra Nova Drilling":     ("fed-e003cff5c9", "name_verified", "high", None),
    "1997 Cheviot Coal Mine":       ("fed-85e2e76ad9", "name_verified", "high", None),
    "1998 Little Bow Diversion":    ("fed-12d0f6f009", "name_verified", "high", None),
    "1999 Voisey's Bay":            ("fed-3a0c19878e", "name_verified", "high", None),
    "2003 GSX Canada Pipeline":     ("fed-d4e7e2b77d", "name_verified", "high", None),
    "2006 Eastmain 1-A and Rupert Diversion": ("fed-a18ddcc719", "name_verified", "high", None),
    "2007 Kemess Mine":             ("fed-467235b806", "name_verified", "high", "Kemess North JRP (not Kemess South/Underground)"),
    "2007 Whites Point Quarry":     ("fed-a7a6af4c90", "name_verified", "high", None),
    "2007 Brunswick Pipeline":      ("fed-24e6716734", "name_verified", "high", None),
    "2008 Kearl Addendum":          ("fed-9ee4a7e904", "name_verified", "high", "May 6 2008 GHG addendum after Pembina Institute v Canada 2008 FC 302"),
    "2009 Encana Shallow Gas":      ("fed-9fa92c8c29", "name_verified", "high", None),
    "2009 Mackenzie Gas":           ("fed-2b6d0c97b7", "name_verified", "high", None),
    "2009 Romaine Hydro":           ("fed-3c01bf355b", "name_verified", "high", None),
    "2010 Prosperity Mine":         ("fed-ea8d6067c5", "name_verified", "high", "Original Prosperity JRP (rejected); distinct from New Prosperity"),
    "2011 Joslyn Mine":             ("fed-aa7ff40182", "name_verified", "high", None),
    "2011 Lower Churchill":         ("fed-7c8a47e57c", "name_verified", "high", None),
    "2011 Matoush Mine":            ("fed-781f9437eb", "name_verified", "high", None),
    "2013 Jackpine Oilsands":       ("fed-6e9bf491be", "name_verified", "high", "Jackpine Mine Expansion (CEAR 59540); not the earlier Jackpine Oil Sands Project"),
    "2013 Inuvik Hwy":             ("fed-8eff70fadc", "name_verified", "high", None),
    "2013 New Prosperity":          ("fed-debfb0da44", "name_verified", "high", "Re-application, rejected 2014; distinct from original Prosperity"),
    "2013 Northern Gateway Pipeline": ("fed-9cba73cac0", "name_verified", "high", "Federal JRP record (CEAR 21799); BC EAO record also exists"),
    "2014 Site C Energy Project":   ("fed-bb140a9017", "registry_id", "high", "Confirmed via registry id 63919 in docs_path"),
    "2016 TransMountain Pipeline":  ("fed-3efe75781b", "name_verified", "high", None),
    "2019 TMX Reconsideration":     ("fed-3efe75781b", "name_verified", "medium", "NEB MH-052-2018 reconsideration; same map project as the 2016 TMX record"),

    # --- registry-era but not confidently resolvable ---------------------
    "2002/2004 Sumas Energy 2":     (None, "unmatched", "low", "Archived CEAA/92-NEB panel absent from modern index; candidate fed-3f4ccdc352 'International Power Line Project' unconfirmed (no proponent/coords/registry id)"),

    # --- pre-registry EARP / EARPGO panels: genuinely not in any registry -
    "1978 Eldorado":                (None, "unmatched_pre_registry", "high", None),
    "1979 Alaska Hwy Gas Pipeline": (None, "unmatched_pre_registry", "high", None),
    "1981 Norman Wells Pipeline":   (None, "unmatched_pre_registry", "high", "Modern gap record gap-0c6e1476b6 is a segment replacement, not the 1981 panel"),
    "1984 Hydrocarbon Production Beaufort Sea": (None, "unmatched_pre_registry", "high", None),
    "1985 CN Rail Twin Tracking":   (None, "unmatched_pre_registry", "high", None),
    "1986 Fraser-Thompson Corridor": (None, "unmatched_pre_registry", "high", "Same FEARO report as 1985 CN Rail Twin Tracking"),
    "1990 Alpac Pulp and Paper Mill": (None, "unmatched_pre_registry", "high", None),
    "1991 Port Hardy Ferrochromium": (None, "unmatched_pre_registry", "high", None),
    "1991 Saskatchewan Water Corp": (None, "unmatched_pre_registry", "high", "Rafferty-Alameda litigation reference (Northey Sec. 1.05), not a panel record"),
    "1992 Oldman River Dam":        (None, "unmatched_pre_registry", "high", None),
    "1992 Air Traffic Mgmt S. Ontario": (None, "unmatched_pre_registry", "high", None),
    "1995 Pine Coulee":             (None, "unmatched_pre_registry", "high", None),
}


def main():
    wb = openpyxl.load_workbook(SEED)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    hdr = rows[0]
    seed = [dict(zip(hdr, r)) for r in rows[1:]]

    # map id -> name, for embedding the resolved name
    idx = {r["i"]: r["n"] for r in
           json.load(open(os.path.join(ROOT, "data", "api", "projects.json")))}

    subjects = []
    unknown = []
    for s in seed:
        sh = s["northey_shorthand"]
        if sh not in MAP:
            unknown.append(sh)
            continue
        pid, match, conf, note = MAP[sh]
        if pid and pid not in idx:
            raise SystemExit(f"pid {pid} for {sh!r} not found in projects.json")
        subjects.append({
            "shorthand": sh,
            "northey_name": s["project_name"],
            "report_year": int(re.match(r"\d{4}", str(s["report_year"])).group()),
            "ea_regime": s["ea_regime"],
            "assessment_type": s["assessment_type"],
            "lead_body": s.get("lead_body"),
            "registry_source": s["registry_source"],
            "map_id": pid,
            "map_name": idx.get(pid),
            "match": match,
            "confidence": conf,
            "note": note,
        })

    if unknown:
        raise SystemExit(f"seed rows missing from MAP: {unknown}")

    matched = [x for x in subjects if x["map_id"]]
    out = {
        "source": "Rodney Northey, A Guide to Canada's Impact Assessment Act (2023)",
        "description": "Landmark Canadian EA/IA projects cited in Northey (2023), "
                       "reconciled to project ids in this map.",
        "generated_from": "enviro-permits/data/raw/northey_projects_seed.xlsx",
        "count": len(subjects),
        "matched": len(matched),
        "distinct_map_ids": len({x["map_id"] for x in matched}),
        "subjects": sorted(subjects, key=lambda x: x["report_year"]),
    }
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)

    print(f"wrote {OUT}")
    print(f"  {len(subjects)} subjects: {len(matched)} matched "
          f"({out['distinct_map_ids']} distinct map ids), "
          f"{len(subjects) - len(matched)} unmatched")
    from collections import Counter
    for k, v in Counter(x["match"] for x in subjects).most_common():
        print(f"    {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
