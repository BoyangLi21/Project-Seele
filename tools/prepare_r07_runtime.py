"""Install the authored R07 runtime manifest and operator fixtures after static construction."""
import json
import nbtlib
import regional_voxels as vox
from scan_regional_completion import volume

OUT=vox.ROOT/'artifacts/world_expansion_r07';vox.OUT=OUT;p=vox.Painter()
def put(pos,state):
    a,pal=volume(pos,pos);p.match((*pos,*pos),pal[int(a[0,0,0])],state,'r07/operator_fixtures')
button='minecraft:stone_button[face=wall,facing=north,powered=false]'
put((6402,78,-6141),'minecraft:air');put((6406,78,-6141),button)
for x in (6400,6404):put((x,76,-6545),button)
put((1330,69,474),'minecraft:iron_block')
for x,label in [(6394,'排液 DRAIN'),(6398,'舱门 GATE'),(6406,'注液 FILL')]:
    p.sign(x,79,-6141,['試験制御',label,'NERV CARD',''], 'r07/operator_labels','north')
for x,label in [(6400,'防御 DEFENSE'),(6404,'供电 POWER')]:p.sign(x,77,-6545,['基地・港区',label,'NERV CARD',''],'r07/base_labels','north')
# A real existing NERV pylon charges the independent prototype near its berth.
put((6442,77,-6230),'projectseele:umbilical_pylon')
p.block_entities[6442,77,-6230]=nbtlib.Compound({'id':nbtlib.String('projectseele:umbilical_pylon'),'x':nbtlib.Int(6442),'y':nbtlib.Int(77),'z':nbtlib.Int(-6230)})
p.apply('operator_fixtures')
items=[]
for group,path in [('fleet',OUT/'fleet_vehicles.json'),('base',OUT/'base_architecture/places.json')]:
    data=json.loads(path.read_text(encoding='utf8'));data=data['vehicles'] if isinstance(data,dict) else data
    for i,item in enumerate(data):items.append(dict(item,key=f'vehicle/{group}/{i}'))
vehicles=[('m_1a_2',6606,75,-6360,0,'tank'),('t_90a',6634,75,-6360,0,'tank'),('ztz_99a',6662,75,-6360,0,'tank'),
          ('m_1a_2',6624,75,-6312,0,'tank'),('j_16',6640,75,-6570,0,'fighter'),('j_16',6640,75,-6482,0,'fighter'),
          ('kv_16',6640,75,-6220,0,'fighter'),('a_10a',6692,75,-6320,0,'attack_aircraft'),('ah_6',6664,75,-6140,0,'helicopter'),
          ('truck',6592,75,-6320,0,'truck'),('laser_tower',6528,75,-6672,0,'defense'),('laser_tower',6824,75,-6016,180,'defense')]
for i,(name,x,y,z,yaw,role) in enumerate(vehicles):items.append(dict(key='vehicle/operational/'+str(i),id='superbwarfare:'+name,position=[x+.5,y,z+.5],yaw=yaw,role=role))
items.append(dict(key='prototype',id='projectseele:eva_prototype',position=[6442.5,77,-6205.5],yaw=0,role='experimental'))
plan=dict(schema=1,world=vox.WORLD.name,entities=items,secret=json.loads((OUT/'secret_architecture/places.json').read_text(encoding='utf8'))['secret'])
plan['secret']['controls']=[[6394,78,-6141],[6398,78,-6141],[6406,78,-6141]]
for path in (OUT/'runtime_plan.json',vox.WORLD/'r07_installations.json'):path.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
print('R07 runtime manifest',len(items),'entities')
