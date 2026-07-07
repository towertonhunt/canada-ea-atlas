import json
d=json.load(open('/home/user/ontario-rea-map/data/conditions/shards_ontario/in/shard02.json'))
# (index, discipline, secondary_list, measure_type, timing, discard, discard_reason)
C=[
(0,"other",[],"minimization","operation",False,None),
(1,"noise_vibration",[],"mitigation","operation",False,None),
(2,"other",[],"management_plan","operation",False,None),
(3,"air_quality",[],"management_plan","operation",False,None),
(4,"air_quality",[],"monitoring_followup","operation",False,None),
(5,"other",[],"other","operation",False,None),
(6,"surface_water",[],"minimization","operation",False,None),
(7,"fish_fish_habitat",["surface_water"],"minimization","operation",False,None),
(8,"surface_water",[],"avoidance","operation",False,None),
(9,"other",[],"other",None,False,None),
(10,"other",[],"other",None,False,None),
(11,"other",[],"other",None,False,None),
(12,"other",[],"other",None,False,None),
(13,"other",[],"other",None,False,None),
(14,"other",[],"other",None,False,None),
(15,"other",[],"other",None,False,None),
(16,"other",[],"other",None,False,None),
(17,"other",[],"other",None,False,None),
(18,"other",[],"other",None,False,None),
(19,"other",[],"other",None,False,None),
(20,"other",[],"other",None,False,None),
(21,"other",[],"other",None,False,None),
(22,"other",[],"other",None,False,None),
(23,"other",[],"other",None,False,None),
(24,"other",[],"other",None,False,None),
(25,"other",[],"other",None,True,"Hearing-notice appeal boilerplate fragment, not an obligation"),
(26,"other",[],"other",None,True,"Hearing-notice appeal boilerplate fragment, not an obligation"),
(27,"other",[],"other",None,True,"Hearing-notice service-address boilerplate, not an obligation"),
(28,"other",[],"other","all_phases",False,None),
(29,"other",[],"other",None,False,None),
(30,"other",[],"engagement","all_phases",False,None),
(31,"other",[],"engagement","pre_construction",False,None),
(32,"closure_postclosure",[],"management_plan","closure",False,None),
(33,"closure_postclosure",[],"management_plan","closure",False,None),
(34,"other",[],"other","construction",False,None),
(35,"other",[],"other",None,False,None),
(36,"noise_vibration",[],"minimization","operation",False,None),
(37,"noise_vibration",[],"other","pre_construction",False,None),
(38,"noise_vibration",[],"monitoring_followup","construction",False,None),
(39,"surface_water",["soils_terrain"],"mitigation","all_phases",False,None),
(40,"surface_water",["groundwater"],"minimization","all_phases",False,None),
(41,"archaeology_heritage",[],"other","construction",False,None),
(42,"socio_economic",[],"management_plan","pre_construction",False,None),
(43,"socio_economic",[],"engagement","pre_construction",False,None),
(44,"socio_economic",[],"other","pre_construction",False,None),
(45,"other",[],"management_plan","pre_construction",False,None),
(46,"other",[],"management_plan","operation",False,None),
(47,"other",[],"management_plan","operation",False,None),
(48,"other",[],"other","operation",False,None),
(49,"other",[],"other","operation",False,None),
]
out=[]
for i,disc,sec,mt,tim,dis,reason in C:
    e={"condition_id":d[i]["condition_id"],"discipline":disc,"discipline_secondary":sec,"measure_type":mt,"timing":tim,"discard":dis}
    if dis: e["discard_reason"]=reason
    out.append(e)
json.dump(out,open('/home/user/ontario-rea-map/data/conditions/shards_ontario/work/s02/chunk0.json','w'),indent=1)
print("chunk0 ok",len(out))
