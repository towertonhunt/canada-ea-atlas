import json
d=json.load(open('/home/user/ontario-rea-map/data/conditions/shards_ontario/in/shard02.json'))
HB="Hearing-notice appeal boilerplate fragment, not an obligation"
DH="Document header/address block, not a condition"
C=[
(50,"other",[],"other","operation",False,None),
(51,"other",[],"engagement","operation",False,None),
(52,"other",[],"engagement","operation",False,None),
(53,"groundwater",[],"engagement","operation",False,None),
(54,"other",[],"other",None,False,None),
(55,"other",[],"other",None,False,None),
(56,"other",[],"other",None,False,None),
(57,"other",[],"other",None,False,None),
(58,"other",[],"other",None,False,None),
(59,"other",[],"other",None,False,None),
(60,"other",[],"other",None,False,None),
(61,"other",[],"other",None,False,None),
(62,"other",[],"other",None,False,None),
(63,"other",[],"other",None,False,None),
(64,"other",[],"other",None,False,None),
(65,"other",[],"other",None,True,HB),
(66,"other",[],"other",None,True,HB),
(67,"other",[],"other",None,True,HB),
(68,"other",[],"other",None,True,DH),
(69,"other",[],"other",None,True,HB),
(70,"other",[],"other",None,True,HB),
(71,"other",[],"other",None,True,HB),
(72,"other",[],"other",None,True,DH),
(73,"surface_water",["soils_terrain"],"mitigation","all_phases",False,None),
(74,"other",[],"other",None,True,HB),
(75,"other",[],"other",None,True,HB),
(76,"other",[],"other",None,True,HB),
(77,"other",[],"other",None,True,HB),
(78,"other",[],"other",None,True,HB),
(79,"other",[],"other",None,True,HB),
(80,"noise_vibration",[],"mitigation","operation",False,None),
(81,"noise_vibration",[],"mitigation","operation",False,None),
(82,"noise_vibration",[],"mitigation","operation",False,None),
(83,"other",[],"other",None,False,None),
(84,"other",[],"other",None,False,None),
(85,"other",[],"other",None,False,None),
(86,"other",[],"other",None,False,None),
(87,"other",[],"other",None,False,None),
(88,"other",[],"other",None,False,None),
(89,"other",[],"other",None,False,None),
(90,"other",[],"other",None,False,None),
(91,"other",[],"other",None,False,None),
(92,"other",[],"other",None,False,None),
(93,"other",[],"other",None,False,None),
(94,"other",[],"other",None,False,None),
(95,"other",[],"other",None,True,HB),
(96,"other",[],"other",None,True,HB),
(97,"other",[],"other",None,True,HB),
(98,"other",[],"other",None,True,DH),
(99,"other",[],"other",None,False,None),
]
out=[]
for i,disc,sec,mt,tim,dis,reason in C:
    e={"condition_id":d[i]["condition_id"],"discipline":disc,"discipline_secondary":sec,"measure_type":mt,"timing":tim,"discard":dis}
    if dis: e["discard_reason"]=reason
    out.append(e)
json.dump(out,open('/home/user/ontario-rea-map/data/conditions/shards_ontario/work/s02/chunk1.json','w'),indent=1)
print("chunk1 ok",len(out))
