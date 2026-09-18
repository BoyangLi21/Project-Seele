"""Large, physically wall-mounted signs at measured pedestrian decisions."""
import json
import nbtlib
import regional_voxels as v
from query_blocks import read_box,AIR
WORLD=v.ROOT/'run/saves/SEELE_R21_REVIEW';OUT=v.ROOT/'artifacts/world_repair_r21/wayfinding'
BOARDS=[
 (123,-440,234,'west','北联络廊','本部联络层',['← 发射区车站 / 三机机库','→ 金字塔内部 / 大指挥室','两侧自动步道均可使用']),
 (123,-440,128,'west','北联络廊','通往机库与发射区',['← 发射区车站','→ 金字塔内部','到站后可换乘 U2 联络线']),
 (106,-440,241,'south','金字塔北侧接驳厅','本部联络层',['右侧：北联络廊 / 发射区车站','身后楼梯：大指挥室','地面入口：东侧公共电梯']),
 (117,-440,-55,'south','发射区换乘厅','U2 联络线 / 机库入口',['→ 乘车站台','← 公共电梯 / 机库通廊','金字塔：经东侧北联络廊']),
 (112,-392,-65,'west','机库登机层','三机登机通廊',['← 零号 / 初号 / 二号机登机厅','→ 电梯 / 发射区车站','上层观察廊请乘电梯']),
 (91,-392,-270,'south','三机登机厅','机库前部连廊',['← 零号机 / 初号机 / 二号机','东侧通廊：公共电梯','观察廊：电梯上行']),
 (112,-365,-220,'west','机库观察层','三机贯通观察廊',['← 机库正面观察窗','→ 公共电梯 / 下层登机廊','身后：三机后侧观察廊']),
 (-12,-365,-225,'south','零号机观察位','三机后侧观察廊',['前方：零号机整备舱','→ 初号机 / 二号机观察位','公共电梯在东端']),
 (30,-365,-225,'south','初号机观察位','三机后侧观察廊',['前方：初号机整备舱','← 零号机    二号机 →','公共电梯在东端']),
 (72,-365,-225,'south','二号机观察位','三机后侧观察廊',['前方：二号机整备舱','← 初号机 / 零号机观察位','→ 东端公共电梯']),
 (35,-464,452,'west','NERV 总部站','金字塔南侧进站通道',['→ U2：机库 / 发射区方向','← 金字塔内部 / 大指挥室','跨线请使用站内通道']),
 (87,-446,371,'east','金字塔内部导向','南侧公共通廊',['→ 大指挥室 / 北联络廊','← 科研区联络桥','上层房间请走内部楼梯'])]
def main():
 v.WORLD=WORLD;v.OUT=OUT;p=v.Painter();records=[]
 p.protect((6,-445,262,52,-388,365),'retained_main_command_room')
 for x,y,z,face,title,place,rows in BOARDS:
  dx,dz={'west':(1,0),'east':(-1,0),'south':(0,-1),'north':(0,1)}[face]
  front=[(x+(i if dz else 0),y+j,z+(i if dx else 0)) for i in (-1,0,1) for j in (0,1)]
  back=[(xx+dx,yy,zz+dz) for xx,yy,zz in front];all_points=front+back
  lo=tuple(min(q[i] for q in all_points) for i in range(3));hi=tuple(max(q[i] for q in all_points) for i in range(3));observed=read_box(WORLD,v.DIM,lo,hi)
  allowed={'projectseele:nerv_wall_panel','projectseele:nerv_structural_panel','projectseele:clear_glass','minecraft:gray_stained_glass','minecraft:light_gray_stained_glass','minecraft:light_gray_concrete','minecraft:gray_concrete','minecraft:smooth_stone','minecraft:polished_deepslate'}
  assert all(observed[q] in allowed for q in back),(title,'No full backing',back)
  assert all(observed[q].split('[')[0] in AIR or observed[q].startswith('minecraft:oak_wall_sign[') for q in front),(title,'Occupied sign face')
  pos=(x,y,z);p.match((*pos,*pos),observed[pos],f'projectseele:station_departure_board[facing={face}]','r21/registered_wayfinding_board')
  tag=nbtlib.Compound({'id':nbtlib.String('projectseele:station_departure_board'),'x':nbtlib.Int(x),'y':nbtlib.Int(y),'z':nbtlib.Int(z),'Wayfinding':nbtlib.Byte(1),'Station':nbtlib.String(place),'Route':nbtlib.String(title),'PlatformCentre':nbtlib.Long(0)})
  for i,text in enumerate(rows):tag['Row'+str(i)]=nbtlib.String(text)
  p.block_entities[pos]=tag
  records.append(dict(position=pos,facing=face,title=title,place=place,rows=rows,full_backing=[dict(pos=q,state=observed[q]) for q in back],clear_height=2.25))
 # These small signs are superseded by the adjacent large panels; do not
 # leave multiple competing directions at one decision point.
 for q in [(123,-440,239),(112,-391,-60),(35,-464,446)]:
  s=read_box(WORLD,v.DIM,q,q)[q]
  if s.startswith('minecraft:oak_wall_sign['):p.match((*q,*q),s,'minecraft:air','r21/replace_superseded_small_sign')
 p.meta.update(boards=records,main_command_layout_unchanged=True,standing_headroom_preserved=True)
 p.apply('mounted_destination_boards')
 (WORLD/'wayfinding_r21.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf8')
 print('Mounted wayfinding boards',len(records),flush=True)
if __name__=='__main__':main()
