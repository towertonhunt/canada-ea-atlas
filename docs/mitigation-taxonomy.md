# Mitigation Taxonomy — Classification Framework

Schema for the EA Mitigation Prediction Tool. This is the controlled vocabulary
that automated condition-extraction (BC EAO tables of conditions, federal
decision statements, Ontario REA/ECA/EA approvals, Quebec REE decrees, Atlantic
approvals) maps raw condition text into, and that the matching engine keys on.

Design rules:

- Every enumerated value below is a **stable slug** (lowercase, underscore).
  Extraction code emits slugs, never display labels.
- When extraction cannot classify confidently, it uses the `*_other` /
  `unclassified` fallback in each axis rather than guessing — a human-review
  queue drains those.
- One raw approval condition may map to **multiple records** (a single BC EAO
  condition often bundles a plan requirement + monitoring + reporting). Split
  into one record per (discipline × measure_type) pair.
- Slugs here align with `data/projects_canada.geojson` `category` values
  (the map's 15-category taxonomy) so predictions link back to map pins.

---

## 1. Project archetypes

Top level = map `category`. Second level = archetype, used where regulatory
treatment genuinely differs (different Acts, different standard condition sets).
Extraction stores the archetype; the map category is derivable (prefix before
the first `.`).

| Map category | Archetype slug | Scope / regulatory notes |
|---|---|---|
| wind | `wind.onshore` | Ontario REA Class 4/5, BC EAO reviewable >50 MW; bird/bat and noise-receptor regimes |
| wind | `wind.offshore` | Federal IAA + offshore accords; rare in corpus, keep separate |
| solar | `solar.ground_mount` | Ontario REA Class 3, glare/drainage/ag-soil regimes |
| solar | `solar.rooftop_distributed` | Minimal EA footprint; usually ECA-only |
| biogas | `biogas.anaerobic_digestion` | REA Class 1/2 anaerobic digestion; odour + digestate management |
| biogas | `biogas.landfill_gas` | Landfill gas capture/utilization; ties to `waste.landfill` sites |
| hydro | `hydro.reservoir` | Large storage hydro (e.g., Site C class); flooding, mercury, fish passage |
| hydro | `hydro.run_of_river` | Instream flow, ramping rates, fish screens |
| hydro | `hydro.dam_water_control` | Non-generating dams, LRIA/dam-safety driven |
| nuclear | `nuclear.reactor` | CNSC licensing + IAA; radiological regimes out of scope for most disciplines but conventional EA conditions still apply |
| nuclear | `nuclear.waste_facility` | DGR/near-surface disposal |
| energy_other | `energy.transmission_line` | Linear ROW; note: transmission may appear under transport-like linear logic — classify by function, not geometry |
| energy_other | `energy.substation_storage` | Substations, BESS; fire/spill + noise |
| energy_other | `energy.thermal_generation` | Gas/biomass thermal plants; air quality dominant |
| oil_gas | `oil_gas.pipeline` | CER/federal; watercourse crossings, geohazards |
| oil_gas | `oil_gas.upstream` | Wells, batteries, gas plants |
| oil_gas | `oil_gas.lng_terminal` | BC EAO staple; marine + air disciplines |
| mining | `mining.open_pit_metal` | MDMER, tailings, large water balance, closure FA |
| mining | `mining.underground_metal` | Smaller footprint, subsidence, water treatment |
| mining | `mining.quarry_aggregate` | Ontario ARA licences, pit-below-water-table triggers, no MDMER |
| mining | `mining.coal` | MDMER coal provisions, selenium |
| mining | `mining.processing_smelting` | Mills/smelters standalone; air quality dominant |
| transport | `transport.highway_road` | Ontario MTO Class EA / GO-style; salt, wildlife passage |
| transport | `transport.rail` | Federal (CTA) or provincial; vibration, whistle, crossings |
| transport | `transport.port_marine` | Marine terminals; fish habitat, dredging, underwater noise |
| transport | `transport.airport` | Federal lands; noise contours, bird hazard (conflicting with wildlife attraction) |
| transport | `transport.transit_urban` | LRT/subway; vibration, dewatering, archaeology-heavy |
| water | `water.water_treatment_supply` | WTPs, intakes, watermains; Class EA + PTTW |
| water | `water.wastewater` | WWTPs, sewers, outfalls; assimilative capacity |
| water | `water.stormwater_flood` | SWM facilities, channelization, flood control |
| industrial | `industrial.manufacturing` | ECA-driven air/noise/waste conditions |
| industrial | `industrial.chemical_refining` | Higher accident/malfunction weighting |
| waste | `waste.landfill` | Leachate, gas, groundwater monitoring networks, post-closure care (Ontario ~25+ yr horizon) |
| waste | `waste.transfer_processing` | Transfer stations, MRFs, composting; odour/litter/vectors |
| waste | `waste.hazardous_incineration` | Hazardous waste + EFW; strictest air conditions |
| agriculture | `agriculture.livestock_operation` | Nutrient management, NMA; mostly non-EA but conditions exist in ECAs |
| agriculture | `agriculture.drainage_irrigation` | Drainage Act works, wetland conversion pressure |
| tourism | `tourism.resort_recreation` | Resorts, marinas, golf; shoreline + septic + visual |
| other | `other.unclassified` | Fallback; matching engine backs off to discipline-level priors |

Back-off rule for the matching engine: if no precedent at archetype level,
fall back to map-category level, then to all-archetype discipline priors.

---

## 2. Discipline domains

One flat list, 21 values. These mirror how BC EAO tables of conditions and
federal decision statements are actually headed, so extraction can often
classify from the condition's section heading alone.

| Slug | Covers |
|---|---|
| `surface_water` | Water quality/quantity, ESC during construction, water management/balance, discharge limits, PTTW-type takings |
| `groundwater` | Wells, dewatering, aquifer drawdown, hydrogeology monitoring networks |
| `fish_habitat` | Fisheries Act s.34.4/35, DFO offsetting, instream work windows, fish passage/screens, MDMER |
| `wetlands` | Provincially significant / evaluated wetlands, wetland function, water balance for wetlands |
| `vegetation` | Vegetation communities, ecosystems (ELC), old growth, invasive species, revegetation |
| `wildlife` | General wildlife + birds (MBCA nests/timing), bats, movement corridors, wildlife attractants |
| `species_at_risk` | Federal SARA + provincial ESA permits/overall-benefit; separate from `wildlife` because it triggers distinct permits |
| `air_quality` | Dust, stack emissions, odour, O. Reg. 419-type limits |
| `noise_vibration` | Receptor-based noise limits (e.g., REA 40 dBA), construction noise, blasting vibration |
| `light` | Light trespass, dark-sky, aviation lighting mitigation |
| `soils_terrain` | Erosion, topsoil salvage, terrain stability/geohazards, contaminated soils encountered, acid rock drainage / metal leaching (ARD/ML) |
| `waste_hazmat` | Waste management, hazardous materials handling, spills prevention, fuel storage |
| `accidents_malfunctions` | Emergency response, spill response, dam/tailings breach scenarios, fire |
| `human_health` | Health risk pathways (drinking water, country foods, EMF), distinct from the emitting discipline |
| `socio_economic` | Employment/procurement commitments, housing, traffic during construction, property |
| `indigenous_rights` | s.35 rights, traditional land use, harvesting continuity, consultation-through-life-of-project conditions, Indigenous monitors |
| `archaeology_heritage` | Stage 1-4 archaeology (Ontario), chance-find protocols, built heritage, burial sites |
| `visual_landscape` | Viewscapes, screening/berming, design controls |
| `climate_ghg` | GHG limits/reporting, net-zero plans (federal decision statements post-2019), climate resilience of design |
| `cumulative_effects` | Regional/cumulative effect conditions, participation in regional monitoring |
| `closure_post_closure` | Decommissioning, reclamation, closure plans, post-closure care & monitoring |
| `general_admin` | Fallback: reporting schedules, condition-holder obligations, document control — kept out of prediction output but retained in the KB |

---

## 3. Measure types

The mitigation-hierarchy axis. Eight values.

| Slug | Definition | Cue phrases in condition text |
|---|---|---|
| `avoidance` | Siting or timing that avoids the effect entirely | "shall not be located within", "no works between [dates]", setbacks, MBCA nesting window (roughly Apr 1 – Aug 31, region-dependent), instream timing windows |
| `minimization` | Design/technology choice reducing effect at source | "shall be designed to", low-noise equipment, directional drilling instead of open cut, bird-safe / feathering, enclosed conveyors |
| `mitigation_operational` | Operational controls during works | dust suppression, speed limits, silt fences maintained, wildlife shutdown protocols, ramping-rate limits |
| `compensation_offsetting` | Residual-effect compensation | Fisheries Act offsetting plans, ESA overall-benefit actions, wetland replacement ratios, habitat compensation |
| `management_plan` | A named plan must be prepared/approved before a phase | "shall develop, in consultation with, a ... Plan, to the satisfaction of ..." — see plan-name vocabulary below |
| `monitoring_followup` | Effects/compliance monitoring and follow-up programs | post-construction mortality surveys, groundwater monitoring networks, follow-up programs under IAA s.64 |
| `financial_assurance` | Security/bonding | Ontario Mining Act closure FA, landfill FA under EPA, letters of credit, ECA financial assurance |
| `engagement_commitment` | Ongoing consultation/notification obligations | "in consultation with [Nation]", complaint response protocols, community liaison committees, notification before blasting |

**Named plan vocabulary** (for `plan_required`; normalize to these where the
text is a close variant, else keep the verbatim name):
Erosion and Sediment Control Plan; Water Management Plan; Groundwater
Monitoring Plan; Stormwater Management Plan; Fish Habitat Offsetting Plan;
Wetland Management/Compensation Plan; Vegetation Management Plan; Invasive
Species Management Plan; Wildlife Management Plan; Bird and Bat Monitoring
Plan (post-construction); Species at Risk Mitigation/Overall Benefit Plan;
Air Quality/Dust Management Plan; Odour Management Plan (incl. Odour Best
Management Practices Plan); Noise Management/Monitoring Plan; Blasting
Management Plan; Soil Management Plan; Acid Rock Drainage/Metal Leaching
Management Plan; Waste Management Plan; Spill Prevention and Response Plan;
Emergency Response Plan; Emergency Response and Communications Plan (REA);
Tailings Management Plan / OMS Manual; Traffic Management Plan; Heritage/
Archaeological Resources Protection Plan (incl. chance-find protocol);
Indigenous/Aboriginal Consultation Plan; Environmental Management Plan
(umbrella — also tag the specific sub-plans if enumerated); Construction
Environmental Management Plan (CEMP); Decommissioning/Closure Plan;
Post-Closure Care Plan; Follow-up Program (IAA); Adaptive Management Plan;
Lighting Management Plan; Groundwater and Surface Water Monitoring Program;
Complaint Response Protocol.

---

## 4. Condition record schema

Each extracted record is one JSON object. Target of every parser regardless of
source jurisdiction.

```json
{
  "condition_id": "bc-eao|iaac|on-rea|on-eca|on-ea|on-closure|qc-ree|ns-ea|nb-ea|pe-ea|nl-ea + '-' + project slug + '-' + condition number/letter path (e.g. 'bc-eao-blackwater-14.2')",
  "source_doc": "path or URL of the source PDF/text in data/corpus/<jurisdiction>/",
  "jurisdiction": "federal|bc|on|qc|ns|nb|pe|nl|yt|nt|nu",
  "project_id": "map pin id from projects_canada.geojson, or null if not yet linked",
  "project_archetype": "slug from section 1, e.g. 'mining.open_pit_metal'",
  "discipline": "slug from section 2; if a bundled condition, split into multiple records",
  "measure_type": "slug from section 3",
  "trigger": {
    "spatial": "free text or slug: what geography activates it (e.g. 'within 120m of provincially significant wetland', 'all watercourse crossings'), null if site-wide",
    "temporal": "activation window (e.g. 'during nesting season Apr 1-Aug 31', 'instream works Jul 15-Sep 15 only'), null if always",
    "receptor": "protected thing (e.g. 'noise receptor', 'little brown myotis', 'domestic well'), null if none named"
  },
  "measure_text": "verbatim condition text (the split fragment for bundled conditions), whitespace-normalized, no paraphrase",
  "plan_required": "normalized plan name from section 3 vocabulary, verbatim name if unlisted, or null",
  "timing": "pre_construction|construction|operation|closure|post_closure|all_phases",
  "verification": {
    "who": "regulator/role that approves or audits (e.g. 'EAO', 'Agency', 'District Manager MECP', 'Qualified Professional', 'Independent Environmental Monitor')",
    "how": "mechanism (e.g. 'plan approval prior to construction', 'annual report', 'notification within 24h', 'QP sign-off')"
  }
}
```

Extraction conventions:

- `timing` = when the **obligation is performed**, not when it is prepared.
  A closure plan prepared pre-construction but executed at closure →
  `measure_type: management_plan`, `timing: pre_construction` for the
  preparation record; the substantive closure obligations it contains are not
  extracted (they live in the plan, not the approval).
- `all_phases` is legitimate and common ("at all times during the life of the
  project"); do not force a phase.
- Never null `measure_text`; a record without verbatim text is not a record.
- Confidence: parsers may add an optional `_confidence` (0-1) and `_notes`
  field with a leading underscore; downstream ignores underscore fields except
  for the review queue.

---

## 5. Worked matrix — standard condition families per archetype

Priors for the matching engine before (and alongside) real extracted
frequencies. "Near-universal" = expected in the large majority of approvals of
that archetype in the corpus. Format: family — discipline / measure_type.

### wind.onshore
1. Bird and bat post-construction mortality monitoring (typically 3 yrs, with mortality thresholds triggering operational mitigation such as blade feathering / cut-in speed increase) — `wildlife` / `monitoring_followup`
2. Setbacks from provincially significant/evaluated wetlands and woodlands (Ontario 120 m study trigger) — `wetlands` / `avoidance`
3. Noise limits at receptors (REA: 40 dBA at non-participating receptors) + acoustic audit — `noise_vibration` / `mitigation_operational` + `monitoring_followup`
4. Turbine setback from non-participating dwellings (Ontario 550 m baseline) — `noise_vibration` / `avoidance`
5. Vegetation clearing outside MBCA nesting window or nest sweeps by avian biologist — `wildlife` / `avoidance`
6. ESA permit / SAR mitigation for bats (little brown myotis) and Blanding's turtle where ranges intersect — `species_at_