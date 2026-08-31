import json
d=json.load(open('/home/user/ontario-rea-map/data/conditions/shards_ontario/in/shard02.json'))
HB="Hearing-notice appeal boilerplate fragment, not an obligation"
DH="Document header/address block, not a condition"
C=[
(200,"other",[],"other",None,False,None),
(201,"other",[],"other",None,False,None),
(202,"other",[],"other",None,False,None),
(203,"other",[],"other",None,False,None),
(204,"other",[],"other",None,False,None),
(205,"other",[],"other",None,False,None),
(206,"other",[],"other",None,False,None),
(207,"other",[],"other",None,False,None),
(208,"other",[],"other",None,False,None),
(209,"other",[],"other",None,True,DH),
(210,"other",[],"other",None,False,None),
(211,"other",[],"other","pre_construction",False,None),
(212,"other",[],"other",None,False,None),
(213,"other",[],"other",None,True,HB),
(214,"other",[],"other",None,True,HB),
(215,"other",[],"other",None,True,HB),
(216,"other",[],"other",None,False,None),
(217,"other",[],"other",None,False,None),
(218,"other",[],"other",None,False,None),
(219,"other",[],"other",None,False,None),
(220,"other",[],"other",None,False,None),
(221,"other",[],"other",None,False,None),
(222,"other",[],"other",None,False,None),
(223,"other",[],"other",None,False,None),
(224,"other",[],"other",None,False,None),
(225,"other",[],"other",None,False,None),
(226,"other",[],"other",None,False,None),
(227,"other",[],"other",None,False,None),
(228,"other",[],"other",None,False,None),
(229,"other",[],"other",None,False,None),
(230,"other",[],"other",None,False,None),
(231,"other",[],"other",None,False,None),
(232,"other",[],"other",None,True,HB),
(233,"other",[],"other",None,True,HB),
(234,"other",[],"other",None,True,HB),
(235,"other",[],"other","all_phases",False,None),
(236,"other",[],"other",None,False,None),
(237,"other",[],"engagement","all_phases",False,None),
(238,"other",[],"engagement","pre_construction",False,None),
(239,"closure_postclosure",[],"management_plan","closure",False,None),
(240,"closure_postclosure",[],"management_plan","closure",False,None),
(241,"other",[],"other","pre_construction",False,None),
(242,"other",[],"other","construction",False,None),
(243,"other",[],"other",None,False,None),
(244,"noise_vibration",[],"minimization","operation",False,None),
(245,"noise_vibration",[],"other","pre_construction",False,None),
(246,"noise_vibration",[],"monitoring_followup","construction",False,None),
(247,"surface_water",["soils_terrain"],"mitigation","all_phases",False,None),
(248,"surface_water",["groundwater"],"minimization","all_phases",False,None),
(249,"archaeology_heritage",[],"mitigation","pre_construction",False,None),
]
out=[]
for i,disc,sec,mt,tim,dis,reason in C:
    e={"condition_id":d[i]["condition_id"],"discipline":disc,"discipline_secondary":sec,"measure_type":mt,"timing":tim,"discard":dis}
    if dis: e["discard_reason"]=reason
    out.append(e)
json.dump(out,open('/home/user/ontario-rea-map/data/conditions/shards_ontario/work/s02/chunk4.json','w'),indent=1)
print("chunk4 ok",len(out))
