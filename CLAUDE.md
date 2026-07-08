# Canada Project Map + Mitigation Prediction Tool

Public name: "Canada Project Map" (renamed from the REA map 2026-07-08).

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
- Build corpus search index: `python3 scripts/build_corpus_search.py` (FTS5 -> data/corpus_search.sqlite3.gz for wiki.html)
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
- archive-wayback.yml: 4x daily — submits all known document URLs to
  web.archive.org/save (progress: data/raw/wayback_done.json.gz; full
  sweep of ~73k URLs takes ~2.5 months at SPN-safe pace, then freshness).
- watch-new-filings.yml: daily — diffs newest federal registry entries
  (sort=PostedDateDesc) vs federal_list_all.json.gz, appends new ones,
  waybacks new doc pages immediately, queues them in
  data/raw/new_filings_queue.json, and mirrors files to Drive
  (gdrive:Canada-EA-Archive/) IF the repo secret RCLONE_DRIVE_TOKEN is
  set — until then the queue just accumulates, nothing is lost.
  PROVINCIAL pass added 2026-07-08 (PR #4): BC EPIC newest documents
  (direct download URLs -> Drive-mirrorable), QC REE dossier diff by
  update date, NS/MB/NL project-page diff; state in
  data/raw/watch_state.json, queue in new_filings_prov_queue.json.
  Still open: proponent-site adapters (wayback-on-discovery is the
  fallback), ERO/Ontario notice diffing, BAPE per-project doc diffing.
- fetch-on-permits.yml: daily — AMIS/compliance/assurance + active-mines recon.
NOTE: scheduled runs execute the workflow version on MAIN. After fixing a
lane on the branch, sync to main via PR (user authorized Claude to create
and merge PRs via GitHub MCP — pattern established PR #1, #2).

## Known open threads (priority order)
1. Corpus quality: BC DONE 2026-07-06 -> bc_conditions_v2.json.gz
   (741 real measures kept of 1,884 v1 records; 1,242 were OCR/boilerplate
   noise — v1 was inflated. discipline 'other' 35% -> 18.8%; 0 enum
   violations; multi-measure splits use -a/-b ids). Merge tool:
   scripts/merge_reclassified_conditions.py. FEDERAL DONE 2026-07-06 ->
   federal_conditions_v2.json.gz: 4,946 clean conditions from 110 decision
   statements (8,272 extracted; 216 non-obligation discards; 3,110 dupes
   from repeated/annual-report text removed by (project_id, normalized
   text) dedup). Pipeline: scripts/extract_federal_conditions.py ->
   34 shards in data/conditions/shards_federal/ -> LM agents classify
   (prompts carry hint-override rules: health-section dust/noise ->
   air_quality/noise_vibration, SAR species list, ARD/tailings ->
   waste_hazmat, etc.) -> scripts/merge_federal_conditions.py (positional
   join; condition_ids repeat in source, never join on them). NEXT:
   Ontario REA conditions same pass (ontario_conditions.json.gz is v1),
   ONTARIO DONE 2026-07-07 ->
   ontario_conditions_v2.json.gz: 1,037 clean REA conditions of 2,319 v1
   records (508 ERT hearing-notice/header/definition discards, 774
   template dupes). Same shard pipeline: shards_ontario/ + 
   scripts/merge_ontario_conditions.py. DONE 2026-07-07: all three v2
   sets wired into scripts/mitigation_predict.py (Ontario re-merged with
   project-name keying -> 1,627; pool 7,314). Predictor matches
   primary+secondary disciplines, reports timing + jurisdiction mix;
   --full pre-generates data/predictions/<archetype>_register.json.
2. Baseline engine: VALIDATED 2026-07-06 — Adelaide demo returns 4
   constraint HITs (wetland, waterbody, watercourse, aggregate). Root
   causes were (a) LIO ignoring distance/units -> client-side envelope;
   (b) GeoHub catalogue mixing WMS endpoints into `rest` -> normalize
   /services/ to /rest/services/ and strip WMSServer suffix.
3. Gazetteer: FIXED 2026-07-05 (cd /tmp bug) — data/geo/ca_places.json
   committed; build script geocodes MB/NL/NS/ON-prov by municipality field
   then name n-grams (1,871 pins, flagged geocode=approximate).
4. Routing v1: add DEM terrain (12% weight), CLUPA/mining claims/railways
   (DCAT title mismatches), finer grid, corridor export; demo overlay page.
5. Demo UI: DONE 2026-07-07 -> predict.html (archetype + constraint
   checkboxes -> filtered register from data/predictions/; linked from
   map header). Map-click -> live baseline_query constraints still open.
6. Wiki: DONE 2026-07-08 -> wiki.html. FTS5 index (594 docs) built by
   scripts/build_corpus_search.py -> data/corpus_search.sqlite3.gz
   (15MB gz), loaded in-browser via OFFICIAL @sqlite.org/sqlite-wasm
   (vendor/sqlite3.mjs+wasm) using sqlite3_deserialize. NOTE: stock
   sql.js has NO fts5 - must use the sqlite.org build. Ranked bm25 +
   snippet(); raw-query-then-tokenized fallback for bad FTS syntax.
   Future: sql.js-httpvfs range requests to avoid the 15MB upfront load.
7. Active mines layer: NRCan 900A / OGSEarth (recon files in data/raw).
8. SK/NB/PE parsing — probes analyzed 2026-07-07, all need refetch:
   PEI pei_ea_list.html is a JS-rendered shell (0 links; find the ajax
   endpoint in page source); NB registrations URL 404s (find current EIA
   registrations path on www2.gnb.ca); SK envrbrportal is a Dynamics
   portal — data loads client-side, try the portal's OData/API endpoints
   (Dynamics portals expose /_odata or /_api) before scraping.

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
