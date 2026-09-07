"""Finish the retained public-lift link and separate Sigma laboratories from railway traffic."""
import json
from regional_voxels import Painter,OUT
from regional_architecture import *
from build_regional_underground import hall
p=Painter()

def lane(a,b,floor,width=5):
    x,z=a;xx,zz=b;r=width//2
    x0,x1=(x-r,x+r) if x==xx else (min(x,xx),max(x,xx))
    z0,z1=(z-r,z+r) if z==zz else (min(z,zz),max(z,zz))
    p.fill(x0,floor,z0,x1,floor,z1,FLOOR,'facility/final_handoff','owned')
    p.fill(x0,floor+1,z0,x1,floor+4,z1,AIR,'facility/final_handoff','owned')

lane((89,254),(89,271),-449)
lane((89,254),(112,254),-449)
lane((112,247),(123,247),-443)
lane((123,247),(123,273),-443)
stairs(p,112,254,-449,6,'north','hq/public_transfer_stair',5,'owned')

# The measured native curve crosses the former trial footprint. Keep that
# area as a trackside garden; the complete laboratory programme moves south.
p.fill(213,-466,453,288,-443,547,AIR,'science/retire_crossed_trial_hall','owned')
p.fill(271,-466,439,279,-459,556,AIR,'science/retire_trial_gallery','owned')
p.put(250,-448,548,AIR,'science/retire_trial_label','owned')
p.fill(214,-467,454,287,-467,479,'minecraft:grass_block[snowy=false]','science/trackside_garden','owned')
for x in (225,250,275):tree(p,x,465,-467,'science/geofront_garden')
lane((214,475),(287,475),-467,3)

name='science/sigma';floor=-467
hall(p,(213,288,590,684),floor,name,24,[(250,684,'south',9)],mode='new')
for i,z in enumerate((607,633,659)):
    box_room(p,(223,266,z-9,z+9),floor,16,name+f'/cell{i+1}',WHITE)
    p.fill(224,-464,z+9,265,-453,z+9,'minecraft:light_gray_stained_glass',name)
    p.fill(240,-466,z-5,248,-465,z+5,STEEL,name)
    p.fill(243,-464,z-1,245,-455,z+1,'minecraft:white_terracotta',name)
    p.fill(241,-455,z-2,247,-454,z+2,'minecraft:white_terracotta',name)
    p.fill(243,-453,z-1,245,-451,z+1,'minecraft:red_stained_glass',name)
    p.put(270,-465,z,STEEL,name);p.put(270,-464,z,'minecraft:black_stained_glass',name)
    opening(p,266,z,floor,name,'east',3,3)
    lane((266,z),(275,z),floor,3)
lane((275,552),(275,689),floor)
lane((250,689),(275,689),floor)
lane((250,681),(250,689),floor)
p.sign(250,-448,685,['SIGMA UNIT','PRIBNOW BOX','BIO-TEST / SIMULATION','AUTHORIZED PERSONNEL'],name,'south')

samples=json.loads((OUT/'transit2/track_samples.json').read_text(encoding='utf-8'))
for rail in samples:
    if rail['id']!='U1_section_1':continue
    for x,y,z in {tuple(map(round,v)) for v in rail['points']}:
        p.fill(x-1,y,z-1,x+1,y+5,z+1,AIR,'science/retained_rail_envelope','owned')
p.apply('facility_route_completion')
places=OUT/'geometry_all/places.json';data=json.loads(places.read_text(encoding='utf-8'))
for item in data['landmarks']:
    if item['id']=='science/sigma':item['entry']=[250,-466,685]
data['sigma_bounds']=[213,288,590,684]
places.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
