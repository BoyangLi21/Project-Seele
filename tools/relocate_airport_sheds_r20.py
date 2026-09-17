"""Move complete empty maintenance sheds clear of the elevated stations."""
import json,copy
from pathlib import Path
import nbtlib
import regional_voxels as vox
from query_blocks import read_box,iter_block_entities,AIR

OUT=vox.ROOT/'artifacts/world_rebuild_r20/transit/airport_revision'
MOVES=[(773,857,1180,1220,200),(878,962,1180,1220,200),(-1867,-1783,-270,-230,-250),(-1762,-1678,-270,-230,-250)]
def main():
    vox.OUT=OUT;p=vox.Painter();stations=json.loads((OUT.parent/'civil/viaduct_stations_and_streets/places.json').read_text(encoding='utf8'))['stations'];report=[]
    for s in stations:
        if s['old_center'][1]!=65:continue
        x,y,z=s['center'];h=s['half'];p.protect((x-h,81,z-15,x+h,y+14,z+15),'completed_airport_station')
    for x,X,z,Z,dx in MOVES:
        lo=(x-1,80,z-1);hi=(X+1,114,Z+1);source=read_box(vox.WORLD,vox.DIM,lo,hi);target=read_box(vox.WORLD,vox.DIM,(lo[0]+dx,81,lo[2]),(hi[0]+dx,hi[1],hi[2]));assert all(s.split('[')[0] in AIR or s.startswith('minecraft:light[') for s in target.values()),'Destination is occupied'
        owner='r20/airport/complete_shed_move/'+str(x)
        p.fill(x-1,81,z-1,X+1,114,Z+1,'minecraft:air',owner,'owned')
        p.fill(x-1,80,z-1,X+1,80,Z+1,'minecraft:gray_concrete',owner,'owned')
        for (xx,yy,zz),s in source.items():
            if s.split('[')[0] not in AIR:p.put(xx+dx,yy,zz,s,owner)
        for pos,tag in iter_block_entities(vox.WORLD,vox.DIM,lo,hi):
            t=copy.deepcopy(tag);new=(pos[0]+dx,pos[1],pos[2]);t['x']=nbtlib.Int(new[0]);p.block_entities[new]=t
        # A north-side staff door gives a direct service route from the
        # terminal; it does not send pedestrians into taxiing aircraft.
        cx=(x+X)//2+dx;p.fill(cx-2,81,z,cx+2,85,z,'minecraft:air',owner,'owned');p.fill(cx-3,80,z-6,cx+3,80,z,'minecraft:smooth_stone',owner,'owned')
        p.fill(cx-4,80,z-5,cx-4,85,z-5,'projectseele:nerv_machine_edge',owner,'owned');p.sign(cx-4,84,z-6,['航空维修库','工作人员入口','货运 · 检修','禁止穿越滑行道'],owner,'north')
        report.append(dict(source=[lo,hi],offset=[dx,0,0],destination=[[lo[0]+dx,80,lo[2]],[hi[0]+dx,hi[1],hi[2]]],staff_entry=[cx+.5,81,z-3.5]))
    p.meta.update(moved_sheds=report,original_inventories_preserved=True,station_shells_protected=True);p.save_plan('complete_shed_relocation');print('Whole sheds moved',len(report),flush=True)
if __name__=='__main__':main()
