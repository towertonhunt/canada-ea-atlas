import json
from collections import Counter
W='/home/user/ontario-rea-map/data/conditions/shards_ontario/work/s02'
inp=json.load(open('/home/user/ontario-rea-map/data/conditions/shards_ontario/in/shard02.json'))
out=[]
for c in range(5):
    out += json.load(open(f'{W}/chunk{c}.json'))
assert len(out)==len(inp)==250, (len(out),len(inp))
for r_in,r_out in zip(inp,out):
    assert r_in['condition_id']==r_out['condition_id'], (r_in['condition_id'],r_out['condition_id'])
DISC={"surface_water","groundwater","fish_fish_habitat","wetlands","vegetation_ecosystems","wildlife_birds","species_at_risk","air_quality","noise_vibration","light","soils_terrain","waste_hazmat","accidents_malfunctions","human_health","socio_economic","indigenous_rights_tluse","archaeology_heritage","visual_landscape","climate_ghg","cumulative_effects","closure_postclosure","other"}
MT={"avoidance","minimization","mitigation","compensation_offset","management_plan","monitoring_followup","financial_assurance","engagement","other"}
TIM={"pre_construction","construction","operation","closure","post_closure","all_phases",None}
for r in out:
    assert r['discipline'] in DISC, r
    assert r['measure_type'] in MT, r
    assert r['timing'] in TIM, r
    assert isinstance(r['discipline_secondary'],list) and all(s in DISC for s in r['discipline_secondary']), r
    assert r['discipline'] not in r['discipline_secondary'], r
    assert isinstance(r['discard'],bool), r
    if r['discard']: assert r.get('discard_reason'), r
json.dump(out,open('/home/user/ontario-rea-map/data/conditions/shards_ontario/out/shard02.json','w'),indent=1)
print("records:",len(out))
print("discards:",sum(r['discard'] for r in out))
print("disciplines:",dict(Counter(r['discipline'] for r in out).most_common()))
print("measure_types:",dict(Counter(r['measure_type'] for r in out).most_common()))
