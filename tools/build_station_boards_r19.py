"""Mount real departure displays at the existing, named MTR station platforms."""
from pathlib import Path
import argparse,json
import nbtlib
import regional_voxels as vox
from query_blocks import AIR,read_box
from build_furniture_r19 import box

OUT=vox.ROOT/'artifacts/world_repair_r19/stations'
ASSETS=vox.ROOT/'src/main/resources/assets/projectseele'

def models():
    model={'parent':'minecraft:block/block','textures':{'particle':'minecraft:block/gray_concrete','metal':'minecraft:block/gray_concrete','screen':'minecraft:block/black_concrete','led':'minecraft:block/lime_concrete'},
           'elements':[box([-16,4,6],[32,20,10],'metal'),box([-14.6,5.4,10],[30.6,18.6,10.08],'screen'),box([4,8,0],[12,12,6],'metal'),box([28,4.5,10.08],[29,5,10.14],'led')]}
    rows=[('models/block/station_departure_board.json',model),('models/item/station_departure_board.json',{'parent':'projectseele:block/station_departure_board'}),
          ('blockstates/station_departure_board.json',{'variants':{f'facing={d}':{'model':'projectseele:block/station_departure_board','y':r} for d,r in [('south',0),('north',180),('east',270),('west',90)]}})]
    for path,data in rows:(ASSETS/path).write_text(json.dumps(data,indent=2)+'\n')
    for lang,label in [('zh_cn','铁路实时发车显示屏'),('en_us','Live railway departure display')]:
        path=ASSETS/'lang'/(lang+'.json');d=json.loads(path.read_text(encoding='utf8'));d['block.projectseele.station_departure_board']=label;path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def packed(pos):
    x,y,z=pos;n=((x&0x3ffffff)<<38)|((z&0x3ffffff)<<12)|(y&0xfff)
    return n-(1<<64) if n>=(1<<63) else n

def main(apply=False):
    models();vox.OUT=OUT;p=vox.Painter();boards=[]
    platforms=json.loads((vox.ROOT/'artifacts/world_expansion_20260907/transit_plan.json').read_text(encoding='utf8'))['platforms']
    platforms+=json.loads((vox.ROOT/'artifacts/world_quality_r02/extension_plan.json').read_text(encoding='utf8'))['transit']['platforms']
    platforms+=json.loads((vox.ROOT/'artifacts/world_expansion_r07/port_transit_plan.json').read_text(encoding='utf8'))['platforms']
    for station in platforms:
        if station.get('mode')=='AIRPLANE':continue
        cx,y,cz=map(int,station['center']);horizontal=station['heading'] in ('E','W');side=10 if station.get('compact') else 15;u=-min(18,station['length']//2-4)
        def xyz(uu,yy,vv):return (cx+uu,yy,cz+vv) if horizontal else (cx+vv,yy,cz+uu)
        for sign in (-1,1):
            v=sign*side;at=xyz(u,y+3,v-sign);wall=xyz(u,y+3,v)
            facing=('north' if sign>0 else 'south') if horizontal else ('west' if sign>0 else 'east')
            lo=xyz(u-2,y,v-1);hi=xyz(u+2,y+11,v+1)
            lo=tuple(min(a,b) for a,b in zip(lo,hi));hi=tuple(max(a,b) for a,b in zip(xyz(u-2,y,v-1),xyz(u+2,y+11,v+1)))
            measured=read_box(vox.WORLD,vox.DIM,lo,hi)
            before=measured[at]
            if before.split('[')[0] not in AIR|{'minecraft:light'}:raise RuntimeError(('Departure display site occupied',station['id'],at,before))
            # The mounting column connects the screen to the platform floor
            # and canopy, rather than attaching its text to an empty voxel.
            for yy in range(y+1,y+11):
                pos=xyz(u,yy,v);old=measured[pos];name=old.split('[')[0]
                if name in AIR|{'minecraft:light','minecraft:glass','minecraft:gray_stained_glass','minecraft:white_concrete','minecraft:light_gray_concrete','projectseele:clear_glass','projectseele:nerv_wall_panel'}:
                    p.match((*pos,*pos),old,'projectseele:nerv_structural_panel','r19/station_display_mount')
            p.match((*at,*at),before,f'projectseele:station_departure_board[facing={facing}]','r19/native_departure_display')
            tag=nbtlib.Compound({'id':nbtlib.String('projectseele:station_departure_board'),'x':nbtlib.Int(at[0]),'y':nbtlib.Int(at[1]),'z':nbtlib.Int(at[2]),
                'PlatformCentre':nbtlib.Long(packed((cx,y,cz))),'Station':nbtlib.String(station['name']),'Route':nbtlib.String(station['line']),
                'Row0':nbtlib.String('運行情報を確認中'),'Row1':nbtlib.String('')})
            p.block_entities[at]=tag;boards.append({'id':station['id']+'/'+str(sign),'pos':at,'platform':(cx,y,cz),'facing':facing,'mount':wall})
    p.meta.update(boards=boards,native_source='MTR ArrivalsRequest.getArrivals',fixed_timetable_strings=False)
    p.apply('live_departure_boards') if apply else p.save_plan('live_departure_boards')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
