import json
d=json.load(open('/home/user/ontario-rea-map/data/conditions/shards_ontario/in/shard02.json'))
HB="Hearing-notice appeal boilerplate fragment, not an obligation"
DH="Document header/address block, not a condition"
C=[
(100,"other",[],"other",None,False,None),
(101,"other",[],"other",None,False,None),
(102,"other",[],"other",None,False,None),
(103,"other",[],"other",None,False,None),
(104,"other",[],"other",None,False,None),
(105,"other",[],"other",None,False,None),
(106,"other",[],"other",None,False,None),
(107,"other",[],"other",None,False,None),
(108,"other",[],"other",None,False,None),
(109,"other",[],"other",None,False,None),
(110,"other",[],"other",None,False,None),
(111,"other",[],"other",None,False,None),
(112,"other",[],"other",None,True,HB),
(113,"other",[],"other",None,True,HB),
(114,"other",[],"other",None,True,HB),
(115,"other",[],"other",None,True,DH),
(116,"other",[],"other","construction",False,None),
(117,"noise_vibration",[],"minimization","operation",False,None),
(118,"noise_vibration",[],"mitigation","operation",False,None),
(119,"accidents_malfunctions",["surface_water"],"mitigation","operation",False,None),
(120,"surface_water",[],"monitoring_followup","operation",False,None),
(121,"archaeology_heritage",[],"mitigation","construction",False,None),
(122,"vegetation_ecosystems",["surface_water"],"mitigation","all_phases",False,None),
(123,"vegetation_ecosystems",[],"other",None,False,None),
(124,"species_at_risk",[],"other","pre_construction",False,None),
(125,"other",[],"other",None,True,HB),
(126,"other",[],"other",None,True,HB),
(127,"other",[],"other",None,True,HB),
(128,"other",[],"other",None,True,DH),
(129,"other",[],"other","all_phases",False,None),
(130,"other",[],"other",None,False,None),
(131,"other",[],"engagement","all_phases",False,None),
(132,"other",[],"engagement","pre_construction",False,None),
(133,"closure_postclosure",[],"management_plan","closure",False,None),
(134,"closure_postclosure",[],"management_plan","closure",False,None),
(135,"other",[],"other","construction",False,None),
(136,"other",[],"other",None,False,None),
(137,"noise_vibration",[],"minimization","operation",False,None),
(138,"noise_vibration",[],"mitigation","operation",False,None),
(139,"air_quality",[],"monitoring_followup","operation",False,None),
(140,"surface_water",["soils_terrain"],"mitigation","all_phases",False,None),
(141,"archaeology_heritage",[],"other","construction",False,None),
(142,"air_quality",["noise_vibration"],"management_plan","pre_construction",False,None),
(143,"air_quality",["noise_vibration"],"management_plan","operation",False,None),
(144,"air_quality",["noise_vibration"],"management_plan","operation",False,None),
(145,"accidents_malfunctions",[],"mitigation","operation",False,None),
(146,"air_quality",["noise_vibration"],"minimization","operation",False,None),
(147,"other",[],"other","operation",False,None),
(148,"other",[],"other","operation",False,None),
(149,"other",[],"other","operation",False,None),
]
out=[]
for i,disc,sec,mt,tim,dis,reason in C:
    e={"condition_id":d[i]["condition_id"],"discipline":disc,"discipline_secondary":sec,"measure_type":mt,"timing":tim,"discard":dis}
    if dis: e["discard_reason"]=reason
    out.append(e)
json.dump(out,open('/home/user/ontario-rea-map/data/conditions/shards_ontario/work/s02/chunk2.json','w'),indent=1)
print("chunk2 ok",len(out))
