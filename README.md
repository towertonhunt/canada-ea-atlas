# Canada EA Atlas

An interactive national map of Canadian environmental-assessment (EA) projects,
a searchable document corpus, and an early-stage mitigation-prediction tool.
Built to run and grow largely unattended via scheduled GitHub Actions.

**Live site:** GitHub Pages (served from `main`, custom domain via `CNAME`).

## What's here

| Page | What it does |
|------|--------------|
| `index.html` | Leaflet map of ~18,400 EA projects across 9 federal/provincial sources, with per-project document sidebars |
| `wiki.html` | Full-text search over 594 corpus documents (BC · Federal · Ontario), in-browser via SQLite FTS5 |
| `predict.html` | Mitigation-register predictor: pick a project archetype + site constraints, get ranked precedent measures |

## Data

- **Map** — `data/projects_canada.geojson`, built by `scripts/build_national_geojson.py`
  from raw registry harvests in `data/raw/`.
- **Documents** — ~73k document links indexed under `data/docs/`; full text for the
  corpus under `data/corpus/<jurisdiction>/`.
- **Conditions knowledge base** — `data/conditions/*_conditions_v2.json.gz`: 7,265
  classified mitigation measures (BC 692, Federal 4,946, Ontario 1,627), each tagged
  with discipline, measure type, and project phase against a 22-category taxonomy.
- **Search index** — `data/corpus_search.sqlite3.gz`, an FTS5 database built by
  `scripts/build_corpus_search.py`.

## How it's harvested

Government sites aren't reachable from the development sandbox, so all fetching runs
on GitHub Actions runners (`.github/workflows/*.yml`) that commit results back to the
repo. Scheduled lanes keep the data fresh, archive documents to the Wayback Machine,
and watch federal + provincial registries (and a proponent-site watchlist) for new
filings. See `CLAUDE.md` for the full lane inventory and operational notes.

## Rebuilding locally

```sh
python3 scripts/build_national_geojson.py     # rebuild the map GeoJSON
python3 scripts/build_corpus_search.py        # rebuild the FTS5 search index
python3 scripts/mitigation_predict.py mining wetland watercourse   # query the predictor
python3 scripts/mitigation_predict.py <archetype> --full           # regenerate a register
python3 scripts/validate_data.py                                   # integrity checks over all artifacts
```

## Third-party components

- [Leaflet](https://leafletjs.com/) + Leaflet.markercluster (map)
- [SQLite WASM](https://sqlite.org/wasm) (`vendor/sqlite3.*`) — public domain — powers
  in-browser corpus search; FTS5 enabled.

## Project notes

`CLAUDE.md` is the working log: architecture, every data source and its harvest
method, the scheduled lanes, the prioritized roadmap, and hard-won environment
lessons. Read it first when picking up the project.
