# Canada EA Map + Mitigation Prediction Tool

National environmental-assessment map, document corpus, and an early-stage
mitigation prediction tool ("reverse-engineer an EA from a project description
and location"). Owner: towertonhunt. Built July 2026, designed to run and grow
unattended via scheduled GitHub Actions.

## Architecture in one paragraph
GitHub Actions workflows ("lanes", `.github/workflows/fetch-*.yml`) harvest
government registries — the session sandbox has NO general internet, so ALL
fetching happens on Actions runners, committing results to the branch
`claude/mac-mini-connection-ceehl5`. Local scripts integrate raw data into
`data/projects_canada.geojson` (the map) and `data/corpus/` (text for the
knowledge base). `index.html` is a static Leaflet map (GitHub Pages from
`main`, custom domain via CNAME) with per-project lazy-loaded document
sidebars (`docs_path` property -> `data/docs/<jur>/<id>.json`).

## Key commands
- Rebuild map: `python3 scripts/build_national_geojson.py`
- Split doc catalogues: `python3 scripts/split_doc_catalogues.py`
- Extract conditions: `python3 scripts/extract_conditions.py` (BC; extend per source)
- Predict mitigations: `python3 scripts/mitigation_predict.py <archetype> [constraints...]`
- Baseline constraints (needs internet -> run in Actions): `scripts/baseline_query.py lat lon buffer_m`
- Routing engine: `scripts/routing/build_routes.py` per `routing/framework.json`

## Data inventory (as of 2026-07-05)
- Map: 18,401 features. Federal 6,576 (complete registry incl. federal-lands
  + archived), BC 358, QC 402, NS 248, NL 1,508, MB 2,716, ON REA 197,
  ON provincial EA 189, ON abandoned mines (AMIS) 6,207 (opt-in layer).
- Documents linked (data/docs/): federal 44,230 / BC 17,628 / QC (BAPE) 7,359 /
  NS 2,199 / ON REA in projects.geojson. ~73k total.
- Corpus (data/corpus/): bc/ 291 docs ~3.8M words; federal/ + ontario/ filling
  via lanes fetch-fed-decisions + fetch-on-conditions (576 decision statements
  + 580 condition docs federal; REA approval PDFs + 774 ERO notices Ontario).
- Conditions (data/conditions/): bc_conditions.json.gz — 1,884 records,
  heuristic classification (~35% 'other' — needs LM refinement pass).
- Routing: routing/framework.json (Dillon Wawa-Timmins study transcribed),
  routing/layers/ (12 LIO clips), routing/results/ v0 validated within 10%
  of the professional study (see validation_notes.md).

## Scheduled lanes (server-side, run from main's workflow copies)
- fetch-ea-data.yml: every 2h — federal index crawl (COMPLETE; now freshness).
  Crawl capped by Azure search 100k-skip: comments tail unreachable, accepted.
- fetch-north-geo.yml: every 6h — territories probes + GeoNames gazetteer
  (BROKEN: never commits data/geo/ca_places.json — debug unzip/csv step).
- fetch-on-permits.yml: daily — AMIS/compliance/assurance + active-mines recon.
NOTE: scheduled runs execute the workflow version on MAIN. After fixing a
lane on the branch, sync to main via PR (user authorized Claude to create
and merge PRs via GitHub MCP — pattern established PR #1, #2).

## Known open threads (priority order)
1. Corpus quality: LM reclassification of conditions per
   docs/mitigation-taxonomy.md (controlled vocab, split multi-measure,
   deterministic ids). Keep jurisdictions SEPARATE: one conditions file per
   jurisdiction, `jurisdiction` field on every record; predictor must filter.
2. Baseline engine bug: scripts/baseline_query.py resolves LIO layer URLs but
   demo returned 0 constraints — check "Spatial baseline engine demo" logs.
3. Gazetteer (pins for MB/NL/NS/ON-prov): fix fetch-north-geo.
4. Routing v1: add DEM terrain (12% weight), CLUPA/mining claims/railways
   (DCAT title mismatches), finer grid, corridor export; demo overlay page.
5. Demo UI: map page -> click point + pick archetype -> mitigation register.
6. Wiki: SQLite FTS5 over corpus + sql.js-httpvfs static search.
7. Active mines layer: NRCan 900A / OGSEarth (recon files in data/raw).
8. SK/NB/PE parsing (list pages fetched, thin registries).

## Hard-won environment lessons
- Government sites 404/500 GitHub runners with generic UAs: ALWAYS use a full
  Chrome UA string for gc.ca/ontario.ca; retry loops mandatory.
- IAAC exploration API: POST search='%2A' (pre-encoded), sort='BestMatchDesc',
  cookies + Referer + X-Requested-With required; responses double-JSON-encoded.
- Actions runners get evicted ~60min: checkpoint + resume (see fetch-ea-data).
- GitHub rejects files >100MB: slim + gzip with mtime=0 (deterministic).
- Quebec REE has no document links; documents live at BAPE (voute dl/?id=).
- ArcGIS Hub portals expose DCAT at /api/feed/dcat-us/1.1.json — always try
  that before scraping HTML.
- Session containers restart often, killing crons/waiters: re-arm on wake;
  scheduled Actions on main are the only truly durable automation.
