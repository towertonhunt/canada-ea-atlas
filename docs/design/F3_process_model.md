# F3 — Cross-Jurisdiction Permitting-Process Model

Deliverable of Fable task F3. Defines the canonical process abstraction
that lets one UI answer "where is this project in its process, and
what's next?" across federal (4 regimes), BC (2 Acts), and Ontario —
without pretending the regimes are the same or fabricating precision
the registries don't publish.

Machine-readable companion: **`data/process_frameworks.json`** — the
stage definitions and per-source mapping tables the build script and UI
consume. This doc explains the *decisions*; the JSON is the contract.

## 1. Core design decisions

**D1. Six macro-stages, native stages underneath.** Every regime maps
onto the same six questions; the UI aligns projects cross-jurisdiction
at macro level while displaying each regime's own stage names:

| # | key | The question it answers |
|---|---|---|
| 1 | `intake` | Does this project require assessment, and by whom? |
| 2 | `scoping` | What must be studied, and how? |
| 3 | `study` | Proponent prepares the evidence (studies, application) |
| 4 | `review` | Regulator + public test the evidence (review, hearings) |
| 5 | `decision` | Approve/refuse; set the conditions |
| 6 | `post_decision` | Build, operate, comply, monitor, close |

Rationale: fewer than 6 loses the study/review distinction users care
about ("is it the company's move or the government's?" — the **actor**
field on every native stage makes this explicit); more than 6 forces
regimes into stages they don't have.

**D2. Termination is an outcome, not a stage.** Withdrawn / terminated
/ suspended / refused projects keep their furthest-reached stage and
carry an `outcome` overlay (`terminated_at: review`). The rail renders
progress + a flag — never a fake seventh stage, never 100%-complete for
a dead project.

**D3. Confidence is part of the model.** Every project's process state
carries `confidence`:
- `exact` — the registry publishes a phase field (BC EPIC
  `currentPhaseName`; federal `ea_phase_en` on ~76 active IAA-2019
  projects).
- `inferred` — derived from a lifecycle status ("Completed" ⇒ decision
  reached; "In progress" ⇒ somewhere in scoping–review, shown as a
  *range*, not a point).
- `unknown` — registry publishes nothing (QC/MB/NS/ON-prov today).
The UI contract: `exact` = solid stage marker; `inferred` = hollow
marker or shaded range + "inferred from registry status"; `unknown` =
rail rendered with an honest caption. **No fabricated positions.**

**D4. Substituted/delegated processes annotate, not fork.** Federal
"Substitution" (province runs the review) renders as an annotation on
`review` ("review conducted by BC EAO under substitution") rather than
a separate framework — users care where it stands, not the
intergovernmental plumbing (which the Overview can explain).

**D5. `post_decision` has sub-phases where data exists.** BC's
Post-Decision phases (Pre-Construction → Construction → Operation →
Care & Maintenance → Complete) are the richest lifecycle data we hold;
they render as a sub-rail inside macro-stage 6. Other regimes show a
single post-decision block. This is also where commitments (F4)
attach: each condition's `timing` tag points into these sub-phases.

## 2. Frameworks defined (in the JSON)

| framework | applies to | native stages (→ macro) |
|---|---|---|
| `iaa_2019` | Federal IA Act 2019 | Planning (scoping) → Impact Statement (study) → Impact Assessment (review) → Decision making (decision) → Post Decision (post_decision); Substitution = review annotation |
| `ceaa_2012` | CEAA 2012 EAs | Screening (intake) → EA in progress (study+review merged: the registry doesn't split them — macro range) → Decision statement (decision) → Follow-up (post_decision) |
| `ceaa_1992` | Screenings/Comp. Studies/Panels 1992 | analogous; panel adds hearings under review |
| `federal_lands` | s.82/67 projects on federal lands (5,911 projects) | Determination posted (intake) → Comment period (review) → Determination (decision) — a 3-stage lightweight rail; most of the federal volume |
| `bc_2018` | BC 2018 Act | Project Designation (intake) → Early Engagement (scoping) → Readiness/Process Planning (scoping) → Application Development & Review (study) → Effects Assessment (review) → Referral/Decision (decision) → Post-Decision sub-phases (post_decision) |
| `bc_2002` | BC 2002 Act | Pre-Application (study) → Application Review (review) → Decision (decision) → Post Decision – {Pre-Construction, Construction, Operation, Care & Maintenance, Complete} (post_decision) |
| `on_rea` | Ontario REA | Application submitted (intake) → Technical review (review) → Decision + ERT appeal window (decision) → Operation & compliance (post_decision) |
| `on_ea` | Ontario individual/Class EA | ToR/Screening (scoping) → EA preparation (study) → Ministry/public review (review) → Decision (decision) → Implementation (post_decision) |

Frameworks not yet modelled (QC, MB, NS, NL, territories): projects
render the macro rail with `confidence: unknown`. Adding a regime =
adding one JSON entry; no UI change.

## 3. Per-source mapping rules (the tables in the JSON)

**Federal** — framework chosen from `ea_type_en` (e.g. "Project on
federal lands" → `federal_lands`; "…CEAA 2012" → `ceaa_2012`; IAA
types → `iaa_2019`). Stage: `ea_phase_en` when present (`exact`),
else from `status_en`: Completed → decision (inferred; decision date
unknown ⇒ no post-decision claims), In progress → range scoping–review
(inferred), Terminated/Suspended → outcome overlay at last-known or
unknown stage.

**BC EPIC** — `currentPhaseName.name` maps 1:1 (`exact`), legislation
field picks `bc_2002` vs `bc_2018`. `phaseHistory` (when harvested —
currently dropped by the build; recovery is Opus task O2 in
APP_PLAN §3) yields dated stage history: entered/exited per stage.
Withdrawal/Termination → outcome overlay. `eaStatus` ("Requires EAC" /
"Does not require EAC") gates whether the rail renders at all — "does
not require" projects show an intake-only rail with that determination
as the outcome.

**Ontario REA** — all records are approvals: stage = post_decision
(`inferred`, but safe), decision date = approval_date (`exact`).

**Everything else** — macro rail, `unknown`, caption from the
partial-data matrix (F1 §6).

## 4. Project process state (what the API emits per project)

```jsonc
"process": {
  "framework": "bc_2002",
  "confidence": "exact",              // exact | inferred | unknown
  "macro_stage": "post_decision",     // null when unknown
  "macro_range": null,                // ["scoping","review"] for ranges
  "native_stage": "Post Decision - Operation",
  "sub_phase": "operation",           // post_decision sub-rail position
  "outcome": null,                    // {state, at_stage} | null
  "annotations": [],                  // e.g. substitution note
  "history": [                        // when phaseHistory recovered
    {"stage": "Pre-Application", "entered": "2004-02-10", "exited": "2005-06-01"}
  ],
  "as_of": "2026-07-09"               // harvest date of the source field
}
```

## 5. What this unblocks, in order
1. Build-time `process` derivation for federal + BC + ON-REA (mapping
   tables are complete in the JSON — pure lookup code).
2. S3 Process section (F1) renders from `process` alone.
3. BC `phaseHistory` recovery upgrades BC from point-in-time to dated
   timelines (no schema change — `history` just fills).
4. Commitments timing tags (F4) index into `post_decision` sub-phases.
