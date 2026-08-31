# F2 — Visual Design System & Key Screens

Deliverable of Fable task F2. Design tokens in
`docs/design/tokens.json`; hi-fi mockups of the hero screens in
`docs/design/mockup.html` (self-contained, light+dark, desktop+phone).
This doc records the *decisions* so Opus can extend the system without
re-deriving taste.

## 1. Identity: a public-record instrument

The product is an instrument for reading Canada's environmental-
assessment record — closer to a survey map and a statute book than to
a SaaS dashboard. The identity is built from that world:

- **Ground**: cool paper. Light theme `#F5F7F4` (paper with a faint
  conifer bias — deliberately not cream); dark theme `#111917`
  ("duff" — spruce-black, not neutral black).
- **Ink**: `#1A312B` deep spruce green-black. Text and chrome carry a
  green bias throughout; there is no pure grey in the system.
- **Accent — "blaze"**: `#E8620C` (dark theme `#FF7E33`), surveyor's
  flagging-tape orange. It marks exactly two things: **where the
  project is now** (current stage on the process rail) and **the
  primary action**. It never decorates. If a screen shows blaze in
  more than two places, something is misdesigned.
- **Secondary — "glacial"**: `#3E7CA6`, hydrographic blue for links
  and informational UI.
- **Semantic** (never used as accent): ok `#2E7D4F`, caution
  `#B7791F`, stop `#B3402E`.
- **Sector chips**: the map's existing 15 `CATEGORY_META` colours are
  retained unchanged (continuity with the current map, and they're a
  reasonable categorical ramp). Chips render as `colour`-on-
  `colour·12%` tint, as the map sidebar already does.

## 2. Typography

| Role | Product (webfont) | Mockup fallback (CSP-safe) |
|---|---|---|
| Display / headings | **Archivo** — tight cartographic grotesque | Avenir Next / Seravek / Segoe UI |
| Body | **Public Sans** — designed for government digital services; exactly the register we want | system-ui |
| Data (ids, dates, coords, counts) | **IBM Plex Mono** | ui-monospace |

Scale (rem): 2.0 / 1.5 / 1.17 / 1.0 / 0.88 / 0.76. Body line-height
1.55; running text ≤ 68ch. Uppercase labels get `+0.06em` tracking.
All numeric columns set `font-variant-numeric: tabular-nums`.
Monospace is a semantic signal: if it's mono, it came from a registry
verbatim (id, date, coordinate) — prose is never mono.

## 3. Signature components

**Process rail** (F3's renderer, the product's signature): a
horizontal survey line with six station ticks (the macro-stages).
Completed stations solid spruce; current station a blaze diamond with
the native stage name beneath; future stations hollow. Confidence
renders physically: `exact` = solid geometry; `inferred` = hollow
current marker + shaded plausible range + caption; `unknown` = the
rail at 40% with an honest caption. Outcome overlays (terminated /
withdrawn) stamp a flag at the last station — the rail never fills to
100% for a dead project. BC post-decision sub-phases render as five
smaller ticks expanding under station 6.

**Depth badge** (F1 §5): three core-sample diamonds ◆◆◇ — filled
count = tier ("Deep dive" / "Documented" / "Mapped"). Always paired
with its word on first use per screen; diamonds alone thereafter.

**Commitment card** (F4's renderer): discipline colour-chip + plain-
language summary line (bold, ≤140 chars) + expandable verbatim legal
text + tag row (measure type · timing · jurisdiction) + source-
document link. Verbatim text renders in a quoted block with a spruce
left rule — visually "from the record".

**Status pill**: semantic colour on 12% tint; lifecycle text verbatim
from the registry (mono) with normalized enum as the pill colour.

**Provenance strip**: every detail page ends with source registry,
fetch date, geocode quality, enrichment flags. Set small, mono, never
hidden — provenance is the product's authority.

## 4. Layout & spacing

- Spacing scale: 4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 px.
- Radius: 6px controls, 10px cards, 999px pills. No larger radii.
- Elevation: borders first (`1px` ink·12%); shadows only for overlays.
- Desktop detail page: 760px content column + 280px sticky section
  nav. Results: 380px list pane + map. Phone: single column, bottom
  tab bar (Search · Map · Commitments · Saved), sections as anchors.
- Density: results list is a data surface (compact, 8px rhythm);
  detail page is a reading surface (24px rhythm). Don't mix rhythms.

## 5. Motion & themes

- Motion budget: 150–200ms ease-out on reveal/hover; the only
  choreographed moment is the process rail drawing its line once on
  first view (respects `prefers-reduced-motion`).
- Both themes are first-class; tokens only (`:root` custom properties,
  redefined under `@media (prefers-color-scheme: dark)` and
  `[data-theme]` overrides). Blaze shifts brighter on dark; sector
  chip tints go from 12% to 22% opacity on dark grounds.

## 6. What Opus builds from this
1. Port `tokens.json` to CSS custom properties module (one file, both
   themes) — the mockup's `<style>` block is the reference
   implementation.
2. Components in build order: status pill → depth badge → sector chip
   (reuse map colours) → result card → process rail → commitment card
   → provenance strip.
3. Web app screens per F1; the mockup is the acceptance target for
   S2/S3 fidelity.
