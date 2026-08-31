# F1 — Product & Information Architecture

Deliverable of Fable task F1 (see `docs/APP_PLAN.md`). Defines the user
journeys, screen inventory, navigation model, URL scheme, and — most
critically for this dataset — the **partial-data behaviour** of every
screen. The design premise: coverage is deliberately uneven (18.5k
browseable projects, ~150 commitment-rich flagships), so the IA treats
data depth as a first-class, visible concept instead of hiding it.

## 1. Who it's for, and the three journeys

**P1 — The looker-upper** (consultant, journalist, resident): "What is
this project near me / in the news, and where does it stand?"
Search → Project → Overview + Status. Needs: fast search, plain status,
source links. Depth needed: universal (all 18.5k).

**P2 — The practitioner** (environmental consultant, proponent staff,
regulator): "What did projects *like mine* commit to? What conditions
should I expect?" Search/filter by sector+jurisdiction → compare
Commitments across precedents → export. This is the differentiated
journey; it runs on the deep ~150 + the 7,265-condition knowledge base
and the predictor. Depth needed: flagship tier.

**P3 — The watcher** (community group, investor, researcher): "What's
coming in my region / sector? What's moving?" Map/region browse →
saved-view recall → status changes. Depth needed: universal + freshness.

Journey P2 is the product's reason to exist; P1 is the volume use case
that makes it feel complete; P3 is retention. Rank screens accordingly.

## 2. Screen inventory

### S1. Home / Search
- One search box (project, proponent, place), 3 entry tiles below:
  **Explore the map** · **Browse by sector/region** · **Predict
  mitigations** (the existing predictor, P2 bait).
- A "deep-dive projects" shelf: the ~150 commitment-rich flagships,
  labelled honestly ("full conditions analysed"). This shelf is the
  primary route into the differentiated content — don't bury it.
- Search behaviour: typeahead over name+proponent+municipality
  (client-side index); full-text corpus search offered as a second
  scope: "Search inside 594 documents instead →" (wiki.html capability).

### S2. Results (list ⇄ map, one screen, two lenses)
- Toggle list/map; filters persist across lenses: jurisdiction, sector,
  status (normalized enum), year range, **data-depth** ("has analysed
  commitments", "has documents", "mapped only").
- Each result card: name, proponent, sector chip, jurisdiction, status,
  and a **depth badge** (see §5). Cards are honest previews: what you
  see on the card is what the detail page can actually deliver.
- Empty state: never "no results" alone — always "no results in X;
  nearest matches / remove filter Y" (filter-relaxation suggestions).

### S3. Project Detail — the core screen
Single scrolling page, sticky section nav (works identically as tabs on
mobile). Section order = confidence order: identity first, deepest
content last, so partial projects degrade by truncation, not by holes
in the middle.

1. **Header**: name, proponent, sector chip, jurisdiction, status
   pill, location (mini-map), depth badge, registry source link + "view
   archived copy" (wayback) — provenance is a header citizen, not a
   footnote.
2. **Overview**: description, key facts table (capacity, decision
   date, EA type), lifecycle status.
3. **Process** (F3's consumer): the stage tracker — canonical
   6-macro-stage rail with the jurisdiction's native stage labels
   underneath; current position marked; per-stage dates where known;
   `stage_confidence` drives rendering (exact = solid marker, inferred
   = hollow marker + "inferred from registry status", unknown = rail
   shown with "position not published by this registry").
4. **Documents**: the existing lazy-loaded catalogue, grouped by
   category, with archived-copy links.
5. **Commitments** (F4's consumer): full commitment explorer for
   flagship projects; for non-flagship projects, a **bridge module**:
   "Conditions for this project haven't been analysed yet — see
   typical commitments for {sector} projects" → links to the
   predictor register filtered to the project's sector. Every project
   therefore has a useful commitments section; only its provenance
   differs (this project vs. precedent-based).
6. **Provenance strip** (bottom): sources, fetch dates, geocode
   quality ("location approximate — geocoded from municipality"),
   enrichment flags ("proponent from NRCan inventory").

### S4. Commitments Explorer (cross-project, P2's workbench)
- Entry: from Home, or "compare across projects" inside any S3
  commitments section.
- Facets: discipline (22), measure type, timing/phase, jurisdiction,
  sector. Result = commitment cards (see F4 spec) with project
  attribution; groupable by discipline or by project.
- This screen and the predictor converge: predictor = this screen with
  an archetype+constraints preset. Implement once.

### S5. Document Search (existing wiki.html, re-skinned)
- Scope selector: all corpus / this project's documents.
- Results deep-link into S3's document section.

### S6. About / Data
- Coverage table per source (auto-generated from build stats), lane
  freshness, methodology, the gap-report summary ("what we know we're
  missing" — publishing this builds trust), API pointer.

Deliberately **not** in v1: accounts, saved searches (localStorage
"pinned projects" only), comments, alerts. Each would force a backend;
the static-API architecture stays intact without them.

## 3. Navigation model

- **Web/PWA**: top bar = logo/name, search (always visible), Map,
  Commitments, About. Mobile: bottom tab bar — Search · Map ·
  Commitments · Saved. S3 is reached only by content links, never a tab.
- **iOS app**: same four tabs; S3 pushed onto the stack. The IA is
  tab-count-identical across platforms so the mental model transfers.

## 4. URL scheme (stable, shareable, static-API-aligned)

```
/                      S1
/search?q=&sector=&jur=&status=&depth=   S2 (list)
/map?…same params      S2 (map lens)
/project/{id}          S3   (id = source-prefixed stable id, e.g. fed-80125)
/project/{id}/commitments|documents|process   S3 deep-link anchors
/commitments?discipline=&timing=&sector=      S4
/docs/search?q=        S5
/about                 S6
```
Every filter state is a URL. The static API mirrors this: S2 reads
`data/api/projects.json`, S3 reads `data/api/project/{id}.json`.

## 5. The depth badge (the IA's honesty mechanism)

Three tiers, computed at build time, shown on cards and S3 headers:

| Tier | Label | Criteria | Count today |
|---|---|---|---|
| ◆◆◆ | "Deep dive" | analysed commitments present | ~150 |
| ◆◆◇ | "Documented" | linked documents present | ~10k |
| ◆◇◇ | "Mapped" | registry record only | rest |

Rules: the badge is descriptive, never apologetic ("Mapped" not
"limited data"). Filters can select on it. It is the single mechanism
that lets uneven coverage coexist with a trustworthy feel: users learn
in one session that the badge predicts exactly what they'll find.

## 6. Partial-data behaviour matrix (per S3 section)

| Section | Missing behaviour |
|---|---|
| Status | Show lifecycle only; if none (QC/MB/NS/ON-prov today): "Status not published by {registry}" + registry link |
| Process | Rail always renders; unknown position states it plainly (never a fake progress bar) |
| Location | Approximate → dashed pin ring + note; none → region text, no map |
| Documents | None → link to registry page + "notify when documents are archived" (future) |
| Commitments | Bridge module to sector precedents (§S3.5) — never an empty section |

Principle: **every absence names its source**. "Not published by the
Ontario EA registry" is information; a blank is a bug.

## 7. Build order (hand-off to Opus)

1. S2 + S3 (Overview/Documents) on the static API — the complete P1 loop.
2. Depth badge + data-depth filter (needs only build-time counts).
3. S3 Process section once F3's `process_frameworks.json` ships.
4. S4 + S3 Commitments (F4 spec) — the P2 loop.
5. S1 shelf, S5 re-skin, S6 auto-stats.
