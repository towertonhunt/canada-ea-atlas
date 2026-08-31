# Unceded Futures × Canada Project Map — Content Pipeline

How the map/database powers the substack (towerton.substack.com,
"Unceded Futures") and its planned YouTube expansion. Written 2026-07-10
after reading the 7 mirrored posts (`data/raw/substack/posts/`).

## The publication, in one paragraph

A settler EA-practitioner's account of infrastructure, land, and power:
one project per month, each following the arc *scene on the land →
project history → the legal turning point (Calder → Berger → Sparrow →
Delgamuukw → Haida → Tsilhqot'in → Yahey) → bridge to the present
(Bill C-5 / Ontario Bill 5)*. Published: CPR, Canol, Mackenzie
Valley/Berger, James Bay, Grassy Narrows, Ipperwash. Announced:
Coastal GasLink, Prosperity/Tsilhqot'in, Elsipogtog, Site C, Lubicon,
Ring of Fire. The author's authority claim is exactly the database's
premise: *the record exists; make it harder to ignore.*

## Subject coverage — verified 2026-07-10

Every announced subject already has records + document libraries here:

| Post subject | In the database |
|---|---|
| Coastal GasLink | BC EAO + federal records, both with doc libraries |
| Prosperity / Tsilhqot'in | **3 records**: BC EA + federal panel + New Prosperity re-application — the twice-rejected trail IS the story |
| Site C | BC + federal; federal record is deep-tier (analysed conditions + decision statement in corpus) |
| Lubicon Lake | 8 records — incl. the solar array, roads, health centre: what got built after the settlement |
| Ring of Fire | 12 records — Webequie Supply Road, Marten Falls Access Road, and the live Regional Assessment |
| Elsipogtog | 5 community-infrastructure records (the SWN shale project itself never reached a registry — itself a datapoint) |
| Grassy Narrows | 7 records — **including the Mercury Care Home federal authority record**: the facility the post's youth quote demands is a row in this database |
| Mackenzie Valley | Mackenzie Gas Project federal record (unpinned — geocode it) |

Pattern worth a post of its own: for the historical subjects, what the
database holds is the *aftermath layer* — care homes, water plants,
housing recovery — the built record of what followed each struggle.

## Repeatable formats (each backed by an existing data asset)

1. **The companion dossier** (per post, immediate). Each post gets a
   standing "the record" box: map link (project.html page), document
   library, process rail, commitments where analysed. Substack post =
   narrative; map = receipts. Zero new writing — links.
2. **The promise audit** (the thesis, made data). "Promises that
   dissolved once the shovels were in the ground" — the conditions KB
   (7,265 classified, incl. `indigenous_rights_tluse` discipline) is
   the ledger of what was promised, tagged by phase. Format: what the
   certificate said / what the record shows. Start where both sides
   exist (BC EAO compliance filings are in the doc libraries).
3. **The invisible projects** (Bill C-5/Bill 5 series). The gap
   harness quantifies the streamlining debate: 490 majors with no
   registry record, Ontario Class-EA-tier projects (Kakabeka, Atura
   plants) invisible in every registry. "This is what 'faster' looks
   like: you can't even see them" — with the Unmatched-majors map
   layer as the visual.
4. **New filings watch** (recurring segment). The daily watcher lanes
   diff every registry; a monthly "what was filed on whose land"
   roundup writes itself from new_filings queues.

## YouTube translation

The map IS the b-roll: cluster fly-ins, the process rail as animated
explainer (six stations; where it stalled; where it was terminated),
the gap overlay reveal ("now turn on the layer they don't show you").
Each existing post storyboards as: cold open (the post's opening scene,
narrated) → map fly-in → the record (docs on screen, verbatim
conditions as pull-quotes) → the legal turning point → present-day
bridge. Site C or Prosperity first — richest record trails.

## Next data tasks feeding this (in order)
1. Geocode + enrich the Mackenzie Gas Project record (unpinned today).
2. Per-post dossier links: a `subjects.json` mapping post slug → map
   project ids (trivial; powers the companion box).
3. Northey book ingest (when files arrive): project list → inventory
   reconcile (verification), excerpts → corpus + project pages
   (private storage for full text; published facts only).
4. Indigenous-rights commitments cut: pre-filtered S4 view of
   `indigenous_rights_tluse` conditions across all projects — the
   promise-audit workbench.
