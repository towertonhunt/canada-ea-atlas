# F4 — Commitments UX & Plain-Language Layer

Deliverable of Fable task F4. How 7,265 dense legal conditions become
the product's most compelling surface — scannable, filterable,
trustworthy — and the exact spec for the plain-language summary layer.
Rendered form: the commitment card in `mockup.html` §04.

## 1. The reading problem, precisely

A condition is a legal obligation written for compliance officers:
long sentences, agency acronyms, cross-references ("in accordance with
Schedule A"). Users arrive with three different questions:

1. *Scanning*: "what kinds of obligations does this project carry?"
2. *Locating*: "what does it say about fish / noise / caribou?"
3. *Citing*: "give me the exact wording and where it comes from."

The design serves all three in one component by strict layering:
**summary → verbatim → source**, in that visual order, always.

## 2. The commitment card (anatomy, top to bottom)

1. **Plain-language line** (bold, ≤140 chars): the obligation in one
   sentence. This is the scanning layer.
2. **Verbatim block** (quoted, spruce left rule, expandable beyond 4
   lines): the record itself, character-exact, OCR warts included.
   Never paraphrased, never truncated silently — "show full text"
   expands in place.
3. **Tag row**: discipline chip (colour from a 22-discipline ramp) ·
   measure-type tag · timing tag (mono) · source-document link.
4. On the cross-project explorer (S4), a **project attribution line**
   sits above the card: project name · jurisdiction · decision year.

Card rules: the summary may never appear without the verbatim being
one interaction away; tags are facts from the classifier, and
clicking any tag filters the current view by it.

## 3. Grouping, filtering, ordering

- **Default grouping: by discipline**, ordered by count descending —
  the project's "obligation fingerprint" is visible before any
  reading. A count-per-discipline header row doubles as filter chips
  (`Surface water · 12`).
- Secondary facets: measure type (avoidance → financial assurance),
  timing (indexes into F3's post-decision sub-phases: a project in
  Construction phase highlights construction-timed commitments — the
  process rail and commitments cross-link), and free-text search
  within conditions.
- **Timeline lens** (toggle): commitments re-grouped by timing —
  "what must happen before construction / during / in operation /
  at closure". This is the practitioner's checklist view.
- Empty-filter states name their cause: "No closure-phase commitments
  were extracted from this certificate" — extraction coverage, not
  project virtue.

## 4. The bridge module (non-flagship projects)

For the ~18,350 projects without analysed conditions the commitments
section renders the **precedent bridge** (never an empty state):

> "Conditions for this project haven't been analysed yet. Projects
> like it — {sector}, {jurisdiction-mix} — typically carry
> commitments in: {top-5 disciplines with counts}."

One tap opens S4 pre-filtered to the project's sector — powered by
the existing predictor registers (`data/predictions/`). Provenance
label mandatory: "based on N conditions from M comparable projects",
because these are precedents, not this project's obligations. The
visual treatment must differ from real commitments (no verbatim
block, dashed card border) so the two are never confusable.

## 5. Plain-language summary spec (the generation contract)

Summaries are generated offline in batch (same shard pattern as the
classification pipeline: export shards → LM pass → positional merge →
validate), one per condition, stored alongside the classified record
as `plain_summary`.

**Hard rules (validated mechanically post-merge):**
- ≤140 characters, one sentence, active voice, present tense.
- MUST preserve: who is obliged (proponent name → "the proponent"),
  the deontic strength (must / should / commits to — never upgrade
  "will consider" to "must"), all numeric thresholds and dates
  verbatim (numbers are copied, not rounded), and the regulator
  named if approval is required ("to DFO's satisfaction" survives).
- MUST NOT: add obligations, merge multiple conditions, interpret
  legal effect, or editorialize ("importantly…").
- Acronym policy: expand on the summary line only when obscure
  (MELP → "BC's environment ministry"); DFO, EA, GHG stay.
- Untranslatable boilerplate (e.g. "comply with Schedule A") gets a
  typed fallback: `plain_summary_kind: boilerplate` and the UI shows
  "General compliance clause" in muted style instead of a fake
  summary.
- Validator additions: length bound, no new numbers (every digit
  sequence in the summary must appear in the source text), enum on
  `plain_summary_kind ∈ {substantive, boilerplate, unclear}`.

Prompt skeleton for the LM pass (per shard):
> For each numbered condition, write one sentence (≤140 chars) stating
> who must do what, when, preserving every number and named regulator.
> If the condition only references other documents or is unreadable,
> output kind=boilerplate or kind=unclear instead.

Cost note: 7,265 conditions ≈ 30–40 shards; a single-session batch
job on the established pipeline. Rerunnable per-jurisdiction.

## 6. Comparison & export (P2's payoff)

- S4 supports **pin-to-compare** (up to 4 projects): pinned projects
  become columns, disciplines become rows, cells hold counts that
  expand to the cards. This is the "what will *my* project be asked
  for" workflow, and it is the predictor's UI made general.
- Export: current filter state → CSV (tags + verbatim + source URL)
  and printable register. No login; the URL is the saved state.

## 7. Build order (hand-off)
1. Commitment card + discipline grouping on flagship S3 (data
   already shipped in conditions v2 files).
2. S4 explorer = same components + project attribution + facets.
3. Bridge module (predictor registers already exist).
4. Plain-language batch pass (spec §5) — cards render `measure_text`
   first-line as interim summary until then.
5. Compare + export.
