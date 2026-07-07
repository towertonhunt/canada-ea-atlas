import json

IN='/home/user/ontario-rea-map/data/conditions/shards_ontario/in/shard09.json'
OUT='/home/user/ontario-rea-map/data/conditions/shards_ontario/out/shard09.json'
recs=json.load(open(IN))
assert len(recs)==69

ERT="Environmental Review Tribunal hearing-notice boilerplate, not an obligation"
AMEND="Amendment/approval document header with administrative name-address or definition-replacement text, no standalone obligation"

# Hand-assigned classifications, index -> tuple
# (discipline, secondary, measure_type, timing, discard, reason)
R=lambda d,sec=[]: (d,sec,"other",None,False,None)  # rationale block
DISC=lambda reason: ("other",[],"other",None,True,reason)

C={
 0: R("other"),                       # generic adverse-effect rationale (D.1/E.1)
 1: R("archaeology_heritage"),        # rationale: protect archaeological resources
 2: R("other"),                       # rationale: operate per compliance procedure (admin)
 3: R("other"),                       # rationale: records/information (admin)
 4: R("socio_economic"),              # rationale: complaint response
 5: R("other"),                       # rationale: corporate name (admin) + notice bleed
 6: DISC(ERT), 7: DISC(ERT), 8: DISC(ERT),
 9: DISC(AMEND),
 10: DISC(ERT), 11: DISC(ERT), 12: DISC(ERT),
 13: DISC(AMEND),
 14: DISC(ERT), 15: DISC(ERT), 16: DISC(ERT),
 17: R("other"),                      # rationale: as-described / document precedence (admin)
 18: R("socio_economic"),             # rationale: info to public and municipality
 19: R("closure_postclosure",["visual_landscape","human_health"]),  # rationale: final retirement
 20: R("other"),                      # rationale: notify Ministry of commencement (admin)
 21: R("noise_vibration"),            # rationale: NPC-232 noise limits
 22: R("noise_vibration"),            # rationale: O.Reg 359/09 setback prohibitions
 23: R("other"),                      # generic adverse-effect rationale
 24: R("other"), 25: R("other"),
 26: R("socio_economic"),             # complaints
 27: R("other"),                      # corporate name + notice bleed
 28: DISC(ERT), 29: DISC(ERT), 30: DISC(ERT),
 31: DISC(AMEND),
 32: DISC(ERT), 33: DISC(ERT), 34: DISC(ERT),
 35: DISC(ERT), 36: DISC(ERT), 37: DISC(ERT),
 38: DISC(AMEND),
 39: DISC(ERT), 40: DISC(ERT), 41: DISC(ERT),
 42: R("other"),                      # precedence rationale (admin)
 43: R("socio_economic"),
 44: R("closure_postclosure",["visual_landscape","human_health"]),
 45: R("other"),
 46: R("noise_vibration"),
 47: R("noise_vibration"),
 48: R("noise_vibration"),            # rationale: acoustic info to verify noise compliance
 49: R("other"),
 50: R("other"), 51: R("other"),
 52: R("socio_economic"),
 53: R("other"),
 54: DISC(ERT), 55: DISC(ERT), 56: DISC(ERT),
 57: R("other"),
 58: R("socio_economic"),
 59: R("closure_postclosure",["visual_landscape","human_health"]),
 60: R("other"),
 61: R("noise_vibration"),
 62: R("noise_vibration"),
 63: R("other"),
 64: R("other"), 65: R("other"),
 66: R("socio_economic"),
 67: R("other"),
 68: R("accidents_malfunctions",["surface_water"]),  # rationale: fuel-tank spill containment
}

assert set(C)==set(range(69))
out=[]
for i,rec in enumerate(recs):
    d,sec,mt,tm,disc,reason=C[i]
    e={"condition_id":rec["condition_id"],"discipline":d,"discipline_secondary":sec,
       "measure_type":mt,"timing":tm,"discard":disc}
    if disc: e["discard_reason"]=reason
    out.append(e)

# validation
DISCIPLINES={"surface_water","groundwater","fish_fish_habitat","wetlands","vegetation_ecosystems",
"wildlife_birds","species_at_risk","air_quality","noise_vibration","light","soils_terrain",
"waste_hazmat","accidents_malfunctions","human_health","socio_economic","indigenous_rights_tluse",
"archaeology_heritage","visual_landscape","climate_ghg","cumulative_effects","closure_postclosure","other"}
MT={"avoidance","minimization","mitigation","compensation_offset","management_plan",
"monitoring_followup","financial_assurance","engagement","other"}
TIM={"pre_construction","construction","operation","closure","post_closure","all_phases",None}
assert len(out)==len(recs)
for a,b in zip(out,recs):
    assert a["condition_id"]==b["condition_id"]
    assert a["discipline"] in DISCIPLINES
    assert all(s in DISCIPLINES and s!=a["discipline"] for s in a["discipline_secondary"])
    assert a["measure_type"] in MT and a["timing"] in TIM

json.dump(out,open(OUT,'w'),indent=1)
json.dump(out,open('/home/user/ontario-rea-map/data/conditions/shards_ontario/work/s09/shard09_backup.json','w'),indent=1)

from collections import Counter
print("records:",len(out))
print("discards:",sum(e["discard"] for e in out))
print("disciplines:",dict(Counter(e["discipline"] for e in out)))
print("kept disciplines:",dict(Counter(e["discipline"] for e in out if not e["discard"])))
print("measure_types:",dict(Counter(e["measure_type"] for e in out)))
