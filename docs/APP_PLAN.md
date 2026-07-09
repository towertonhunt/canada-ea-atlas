# Canada Project Map — Website + iPhone App Plan

Scope: turn the harvested EA dataset into a polished website + iPhone app where
users search projects and view project details, the permitting process, the EA,
current status, and all commitments.

This doc has three parts: (1) an honest **data-readiness audit** of what's
actually present today, (2) a **recommended architecture + unified data model**,
and (3) a **task split** — what Opus builds (mechanical/integration) vs. the
specific **Fable tasks** worth paying for (judgment/design invention).

---

## 1. Data-readiness audit (as of 2026-07-08)

18,401 projects across 9 sources. Coverage of the app's five core concepts is
**uneven** — this is the single most important planning fact.

### Identity, location, documents — STRONG, near-universal
- Every project has name, jurisdiction, type, and a registry URL.
- 15,644 (85%) are mapped with coordinates. Federal 96%, BC/QC/Ontario-REA/AMIS
  100%; MB/NL/NS/ON-prov 41–55% (gazetteer-geocoded, flagged approximate).
- Documents: federal 86% of projects have linked docs, BC 100%, Ontario REA
  100%, NS 65%. ~73k document links total.

### Current status — PARTIAL, and coarse where present
| Source | Status data |
|---|---|
| Federal (6,576) | lifecycle: Completed / In progress / Terminated / Suspended |
| BC (358) | real phases: Post Decision–Operation, Pre-Construction, Complete, … |
| Ontario REA (197) | all "Approved" (these are completed approvals) |
| QC, MB, NS, ON-prov, AMIS | **no status captured** (None) |

- BC's raw EPIC data (`data/raw/bc_epic_projects.json`) additionally contains
  **`currentPhaseName`, `phaseHistory`, `decisionDate`, `eaStatus`** — a genuine
  process timeline — that the current build script **drops**. Recoverable.
- Federal raw carries `status_en` + `ea_type_en` (already used) but the list API
  did not retain `ea_phase_en`; phase granularity would need a per-project fetch.

### Permitting process (structured steps) — NOT MODELED anywhere
- No jurisdiction currently has a normalized "here are the permitting stages and
  where this project sits." BC's `phaseHistory` is the closest raw material.
- This is the biggest **new modeling task**, not just a UI task: the federal
  (IAAC), BC (EAO), and Ontario (REA/EA) processes are different and need a
  common abstraction before a UI can show "where is this project in the process."

### Commitments (classified conditions) — DEEP but NARROW
- The crown jewel: 7,265 conditions classified against a 22-discipline taxonomy,
  each tagged discipline / measure type / project phase.
- **But coverage is ~150 projects, not 18,400**: 44 BC + 49 federal + 57 Ontario
  distinct projects have extracted commitments (they came from the ~420-doc
  corpus, not every project). Name-join to map projects is clean where present
  (44/44, 49/49, 57/57 match).
- Expanding coverage is **mechanical and already-tooled** (extract → shard →
  classify → merge pipeline exists), but each new project needs its
  decision/conditions document in the corpus first.

### Readiness verdict
- **Browse + search + documents + coarse status**: ready for ~all 18,400 today.
- **Rich phase timeline**: ready for BC (recover from raw) + coarse for federal.
- **Full commitments detail**: ready for ~150 flagship projects — a compelling
  MVP/demo surface, not yet universal.
- **Structured permitting process**: needs modeling before it can be shown.

Implication: **an MVP should lead with the ~150 commitment-rich flagship
projects** (the differentiated content) while offering browse/search/documents
across the full 18,400. Don't gate launch on universal commitments coverage.

---

## 2. Recommended architecture

Keep the durable engine (GitHub Actions harvest → committed data → static build).
Add a normalization layer that emits an app-ready **static JSON API**, consumed
identically by web and mobile. No server to run; scales on a CDN; preserves the
cron-driven, zero-ops model.

```
harvest lanes (Actions)  ->  data/raw/*  ->  build scripts  ->
    data/api/projects.json            (search list: id, name, jur, type, status, coords)
    data/api/project/<id>.json        (full detail: identity, location, status,
                                        phase timeline, documents, commitments,
                                        provenance)
    data/api/search.sqlite3(.gz)      (FTS over names + doc text)
        |                                   |
     Web app (React/Next static, PWA)   iPhone app (Expo/React Native or SwiftUI)
```

- **Static-API pattern**: one JSON per project + slim index files. Cache-friendly,
  offline-capable, no backend. A real backend/API is only needed later if you add
  accounts, saved searches, or write features.
- **Web first, as an installable PWA.** Delivers an app-like iPhone experience
  from the home screen, one codebase, no App Store review. Go native only for
  push notifications, deep offline, or store presence.
- **Mobile**: recommend **Expo / React Native** to share the TypeScript data
  layer + types with web and keep the iOS iteration loop fast. (SwiftUI is a fine
  alternative if you want fully native feel and are willing to maintain a second
  codebase.) **Either way, iOS builds/signing/submission require a Mac + Xcode or
  EAS — this environment can't compile iOS.**
- **Search on mobile**: bundle a SQLite FTS DB (SQLite is native on iOS) or hit a
  hosted search endpoint. The web FTS5-in-browser approach (already built in
  `wiki.html`) is the reference.

### Unified data model (the canonical `Project` the apps consume)

```jsonc
{
  "id": "fed-80125",                    // stable, source-prefixed
  "name": "...", "jurisdiction": "Federal (IAAC)", "type": "mining",
  "proponent": "...",
  "location": { "coords": [lon,lat], "approx": false, "text": "...",
                "province": "...", "municipality": "..." },
  "status": { "code": "in_progress", "label": "In progress",   // normalized enum
              "as_of": "2026-05-01" },
  "process": {                          // NEW model (see Fable task F3)
    "framework": "IAAC-2019",
    "stages": [ { "key": "planning", "label": "Planning", "state": "done" },
                { "key": "impact_statement", "state": "current" }, ... ] },
  "ea": { "type": "...", "decision": "...", "decision_date": "..." },
  "documents": [ { "title": "...", "category": "...", "url": "...",
                   "archived_url": "..." } ],
  "commitments": [ { "id": "...", "discipline": "fish_fish_habitat",
                     "measure_type": "monitoring_followup", "timing": "operation",
                     "text": "...", "plain_summary": "..." } ],   // ~150 projects
  "sources": [ { "registry": "IAAC", "url": "...", "fetched": "..." } ]
}
```

---

## 3. Task split

### Opus builds (mechanical / integration — no quality penalty, no Fable cost)
1. **Project-id unification** across the 9 sources (stable ids, name/dedup).
2. **Status normalization** to one enum; **recover BC `phaseHistory`** from raw
   into the phase timeline; wire federal lifecycle status.
3. **Static-API build script**: emit `data/api/*` (index + per-project + search)
   from the existing committed data; add to the validate/CI harness.
4. **Web app** implementation against the design system + IA from Fable.
5. **Mobile app** (Expo) implementation sharing the data layer.
6. **Search integration** (web FTS + mobile bundle), deployment, and wiring the
   whole app build into the existing Actions pipeline so it refreshes with data.
7. **Commitments coverage expansion** via the existing extract→classify→merge
   pipeline (scale the corpus; mechanical).

### Fable tasks (buy tokens for these — judgment/design invention, high-leverage)
Each is discrete, has a concrete deliverable, and is scoped to run efficiently.

- **F1 — Product & information architecture.**
  Define core user journeys and the screen inventory (search → results →
  project → detail sections: Overview / Permitting Process / EA / Status /
  Commitments), navigation model, empty/partial-data states (critical given the
  uneven coverage above).
  *Deliverable:* an IA spec + annotated screen list. *~1 focused session.*

- **F2 — Visual design system + key screens.**
  Brand, color, type, spacing, component library, and hi-fi mockups of the 4–5
  hero screens in both web and iOS idioms — the "great UI" pass.
  *Deliverable:* design tokens + self-contained mockup artifacts Opus can build
  against. *~1–2 sessions.*

- **F3 — Permitting-process model design.** *(hardest, highest value)*
  Invent the normalized cross-jurisdiction permitting/EA process model: a common
  set of stages/gates that the federal, BC, and Ontario processes each map onto,
  plus the per-jurisdiction mapping rules, so the UI can show "where is this
  project and what's next." This is genuine domain + data-model invention.
  *Deliverable:* the process schema + per-jurisdiction stage-mapping spec.
  *~1–2 sessions.*

- **F4 — Commitments UX + plain-language layer.**
  Design how dense legal commitments become a compelling, scannable experience
  (grouping, discipline/phase filtering, and a plain-language summary treatment
  per commitment). Decide the summarization approach.
  *Deliverable:* the commitments detail-view design + summary spec.
  *~1 session.*

Sequencing: **F1 → F3 (in parallel with F2) → F4**, then Opus builds. F1+F3 are
the unblockers; F2+F4 make it great. Total Fable footprint is deliberately small
(~4–6 focused sessions) because everything downstream is Opus-executable.

---

## 4. Honest constraints & open decisions (for the owner)
- **iOS needs a Mac + Xcode / EAS** for builds, signing, and submission — no
  model removes this. Web PWA sidesteps it entirely for v1.
- **Commitments are the differentiator but cover ~150 projects.** Decide: launch
  MVP flagship-first, or invest in corpus expansion before launch.
- **"Permitting process" is a modeling project, not a screen.** F3 must precede
  any UI that claims to show process state.
- Data refresh stays automated via the existing lanes; the app build just needs
  to hang off that pipeline.
