import json
d=json.load(open('/home/user/ontario-rea-map/data/conditions/shards_ontario/in/shard02.json'))
HB="Hearing-notice appeal boilerplate fragment, not an obligation"
DH="Document header/address block, not a condition"
C=[
(150,"other",[],"engagement","operation",False,None),
(151,"other",[],"engagement","operation",False,None),
(152,"other",[],"other",None,False,None),
(153,"air_quality",[],"monitoring_followup","operation",False,None),
(154,"noise_vibration",[],"mitigation","operation",False,None),
(155,"noise_vibration",[],"mitigation","operation",False,None),
(156,"noise_vibration",[],"mitigation","operation",False,None),
(157,"other",[],"other",None,False,None),
(158,"other",[],"other",None,False,None),
(159,"other",[],"other",None,False,None),
(160,"other",[],"other",None,False,None),
(161,"other",[],"other",None,False,None),
(162,"other",[],"other",None,False,None),
(163,"other",[],"other",None,False,None),
(164,"other",[],"other",None,False,None),
(165,"other",[],"other",None,False,None),
(166,"other",[],"other",None,False,None),
(167,"other",[],"other",None,True,HB),
(168,"other",[],"other",None,True,HB),
(169,"other",[],"other",None,True,HB),
(170,"other",[],"other",None,False,None),
(171,"other",[],"other",None,False,None),
(172,"other",[],"other",None,False,None),
(173,"other",[],"other",None,False,None),
(174,"other",[],"other",None,False,None),
(175,"other",[],"other",None,False,None),
(176,"other",[],"other",None,False,None),
(177,"other",[],"other",None,False,None),
(178,"other",[],"other",None,False,None),
(179,"other",[],"other",None,False,None),
(180,"other",[],"other",None,False,None),
(181,"other",[],"other",None,False,None),
(182,"other",[],"other",None,False,None),
(183,"other",[],"other",None,False,None),
(184,"other",[],"other",None,False,None),
(185,"other",[],"other",None,False,None),
(186,"other",[],"other",None,True,HB),
(187,"other",[],"other",None,True,HB),
(188,"other",[],"other",None,True,HB),
(189,"other",[],"other",None,True,DH),
(190,"other",[],"other",None,True,HB),
(191,"other",[],"other",None,True,HB),
(192,"other",[],"other",None,True,HB),
(193,"other",[],"other",None,False,None),
(194,"other",[],"other","pre_construction",False,None),
(195,"other",[],"other",None,False,None),
(196,"other",[],"other",None,False,None),
(197,"other",[],"other",None,False,None),
(198,"other",[],"other",None,False,None),
(199,"other",[],"other",None,False,None),
]
out=[]
for i,disc,sec,mt,tim,dis,reason in C:
    e={"condition_id":d[i]["condition_id"],"discipline":disc,"discipline_secondary":sec,"measure_type":mt,"timing":tim,"discard":dis}
    if dis: e["discard_reason"]=reason
    out.append(e)
json.dump(out,open('/home/user/ontario-rea-map/data/conditions/shards_ontario/work/s02/chunk3.json','w'),indent=1)
print("chunk3 ok",len(out))
