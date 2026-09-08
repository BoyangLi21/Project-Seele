"""Finish campus circulation, railings and the local operator handbook."""
import json
import nbtlib
import regional_voxels as vox
from build_r07_installations import ramp,walk,CASES
OUT=vox.ROOT/'artifacts/world_expansion_r07';vox.OUT=OUT;p=vox.Painter()
F='projectseele:nerv_floor_panel';AIR='minecraft:air';D='minecraft:gray_concrete'
def path(name,points,f=74,width=5):
    for (x,z),(xx,zz) in zip(points,points[1:]):
        assert x==xx or z==zz
        r=width//2;box=(min(x,xx)-r,min(z,zz)-r,max(x,xx)+r,max(z,zz)+r)
        a,b,c,d=box;p.fill(a,f-2,b,c,f,d,D,name);p.fill(a,f,b,c,f,d,F,name);p.fill(a,f+1,b,c,f+3,d,AIR,name)
    walk(name,[[x+.5,f+1,z+.5] for x,z in points])
path('base/operations_walk',[(6432,-6541),(6554,-6541),(6554,-6456)])
for x in (6379,6459):path('base/barracks_walk_'+str(x),[(x,-6461),(x,-6456)])
path('base/workshop_walk',[(6636,-6341),(6560,-6341)])
path('base/power_walk',[(6380,-5989),(6380,-5988),(6560,-5988)])
path('base/terminal_walk',[(6652,-5981),(6560,-5981)])
path('secret/staff_front_walk',[(6402,-6133),(6402,-6118)],76,7)
ramp(p,-6118,-6080,6402,7,76,74,'secret/staff_road_ramp','z')
walk('secret/staff_to_base_road',[[6402.5,77,-6133.5],[6402.5,77,-6117.5],[6402.5,75,-6079.5]])
# An unmarked maintenance apron replaces the old cross-road stub behind the first shelter.
p.fill(6602,74,-6558,6607,74,-6546,F,'r07/base/service_apron','owned')
# Continuous guardrails on the upper galleries, retaining the tower entrance.
NS='minecraft:iron_bars[east=false,north=true,south=true,waterlogged=false,west=false]'
EW='minecraft:iron_bars[east=true,north=false,south=false,waterlogged=false,west=true]'
p.fill(6419,127,-6252,6419,127,-6142,NS,'r07/secret/gallery_guard')
for z0,z1 in [(-6252,-6251),(-6248,-6142)]:p.fill(6465,127,z0,6465,127,z1,NS,'r07/secret/gallery_guard')
for x in (6424,6460):p.fill(x,127,-6252,x,127,-6228,NS,'r07/secret/gallery_inner_guard')
for cx,cz in [(6344,-6680),(6856,-6680),(6344,-5976),(6856,-5976)]:
    for x in (cx-7,cx+7):p.fill(x,84,cz-7,x,84,cz+7,NS,'r07/base/weapon_deck_guard')
    for z in (cz-7,cz+7):p.fill(cx-7,84,z,cx+7,84,z,EW,'r07/base/weapon_deck_guard')
pages=[
    'NERV / UN\n港湾・遠隔試験基地\n\nP1 电车：城市东南部\nX512 / Y81 / Z472\n\n港区：X1264 / Y69 / Z504\n基地：X6560 / Y75 / Z-5968\n\n港口舰上直升机可驾驶。基地远离城市，路程约9千格。',
    '地表试验格纳库\nX6442 / Y77 / Z-6205\n\n携带NERV身份卡。控制室依次操作：\nDRAIN 排空LCL\nGATE 打开大门\n\n沿内部阶梯上到Y127栈桥，面对试验机背部插入栓右键上机。',
    '返回保管\n\n将试验机回到初始位置：\nX6442.5 / Y77 / Z-6205.5\n朝南（Yaw 0）。\n\n下机回到栈桥，控制室关闭GATE，再按FILL。\n\n试验机未归位、有人留在液舱或门区有障碍时，相关操作会被锁定。',
    '载具默认按键\n\n右键上车，左Alt下车。\n坦克：W/S前后，A/D转向。\n旋翼机：W起动和升力，S降低。\n固定翼：W/S油门，鼠标控制姿态；空格收放起落架。\n左键开火，右键瞄准。\n可在设置中修改SBW按键。',
    '补给与防御\n\n基地与港区动力装置为本区载具补充FE。载具已装入弹药补给箱。\n\n基地管制室有防御启用与能源开关。\n两艘大舰为固定靠泊建筑，舰炮可操作；巡逻艇、坦克和航空器为真实SBW载具。'
]
for x,y,z in [(1334,69,514),(6568,75,-5970)]:
    p.chest(x,y,z,[('projectseele:nerv_employee_card',8),('minecraft:written_book',1)],'r07/operator_store')
    book=p.block_entities[x,y,z]['Items'][1]
    book['tag']=nbtlib.Compound({'title':nbtlib.String('港湾・試験基地 案内'),'author':nbtlib.String('NERV Operations'),'pages':nbtlib.List[nbtlib.String]([nbtlib.String(json.dumps({'text':t},ensure_ascii=False)) for t in pages])})
    p.fill(x,y,z+1,x,y+2,z+1,D,'r07/operator_store_sign')
    p.sign(x,y+2,z,['NERV / UN','基地・港湾案内','操作手冊 / 身份卡',''], 'r07/operator_store')
p.meta['walk_cases']=CASES;p.apply('campus_finish');(OUT/'campus_walk_cases.json').write_text(json.dumps(CASES,indent=2),encoding='utf8')
