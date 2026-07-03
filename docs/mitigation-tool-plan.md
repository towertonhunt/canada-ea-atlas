# Early-Stage EA Mitigation Prediction Tool — Build Plan

## Goal
Given a basic/detailed project description and location, predict the avoidance,
mitigation and management measures a proponent should expect, grounded in
(a) precedent from every Canadian EA we have harvested and (b) spatial baseline
constraints at the proposed site. Purpose: de-risk the EA process and enable
credible early engagement with Indigenous communities, stakeholders and regulators.

## Components

### 1. Mitigation Knowledge Base (precedent engine)
Source material, in priority order:
- **BC EAO certificate conditions** — every certificate has a legally binding
  "Table of Conditions"; 17,628 docs already catalogued, condition docs filterable
  by title. STATUS: extraction pilot launched.
- **Federal decision statements** — enforceable condition lists per project
  (IAAC proj pages, doc harvest pending federal completeness).
- **Ontario REA approvals** — condition schedules in the 197 approval PDFs already
  linked in projects.geojson.
- **Ontario ECAs + mine closure plans** — condition/financial-assurance content
  (ERO notices banked: 565 ECA + 209 closure).
- Quebec REE decrees, NS approval conditions — via banked document catalogues.

Pipeline: Actions runner downloads each PDF once → extracts text (pypdf) →
gzipped text + index committed to `data/corpus/<jurisdiction>/` → parse into
structured conditions: {project_type, discipline, trigger, measure_text, source_doc}.

### 2. Spatial Baseline Engine
Layers to acquire (Ontario first, then other provinces):
- Ecological Land Classification (ELC)
- Forest Resource Inventory (FRI)
- Wetlands (evaluated + unevaluated), ANSIs, conservation reserves
- Species at risk ranges / natural heritage
- Waterbodies, watercourses, floodplains
- Abandoned mines (AMIS — 6,207 sites, in hand)
- Treaty boundaries / Indigenous territories (respectfully: for identifying
  which communities to engage, using official Crown treaty layers)
Discovery route: ArcGIS Hub DCAT catalogues (geohub.lio.gov.on.ca) → layer REST
endpoints → point-in-polygon/buffer queries at tool runtime (no bulk download of
huge layers; query the live services per site).

### 3. Matching Engine
project archetype (from the 15-category taxonomy already in the map) ×
site constraints (from #2) → ranked mitigation set from #1, each measure
citing precedent projects (linked to map pins) and frequency
("required in 92% of wind projects within 120m of evaluated wetland").

### 4. Output layer
Draft mitigation register (CSV/PDF) + plain-language engagement summary.
Later: RAG over the corpus so proponents can ask free-form questions.

## Agent/lane deployment map
- Lane: `fetch-bc-conditions.yml` — condition-document text extraction pilot (BC)
- Lane: `fetch-geohub-catalog.yml` — DCAT catalogue discovery for Ontario GeoHub + LIO
- Subagent: mitigation taxonomy framework (docs/mitigation-taxonomy.md)
- Existing lanes keep feeding: federal, QC/NS docs, permits, territories, gazetteer

## Honest constraints
- Condition extraction quality varies with PDF quality; older scans may need OCR
  (defer OCR; prioritize born-digital PDFs).
- "Prediction" = precedent retrieval + frequency, not ML, for v1. That is also
  what makes it defensible in front of regulators and communities.
- Treaty/territory layers must use official sources and be framed as
  "communities to engage", never as authority boundaries.
