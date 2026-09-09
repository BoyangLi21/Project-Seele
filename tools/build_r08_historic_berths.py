"""Privately import Nekoseal's downloaded DD6 builds with native states and safe access."""
import argparse,json,copy,math
import numpy as np
import nbtlib
from query_blocks import AIR,iter_block_entities
from prepare_r08_ship_import import SOURCE,SPECS
import regional_voxels as v
from regional_architecture import stairs
OUT=v.ROOT/'artifacts/world_refinement_r08';v.OUT=OUT
CASES=[]
def walk(name,path):
    CASES.extend([dict(id='r08/port/'+name,path=path),dict(id='r08/port/'+name+'/return',path=path[::-1])])

DIR={'north':'east','east':'south','south':'west','west':'north'}
def rotate(state):
    if '[' not in state:return state
    name,props=state[:-1].split('[');new={}
    for item in props.split(','):
        key,value=item.split('=')
        if key in DIR:key=DIR[key]
        if key=='facing':value=DIR.get(value,value)
        elif key=='axis':value={'x':'z','z':'x'}.get(value,value)
        elif key=='rotation':value=str((int(value)+4)%16)
        elif key=='shape':
            value={'north_south':'east_west','east_west':'north_south','north_east':'south_east','south_east':'south_west','south_west':'north_west','north_west':'north_east',**{'ascending_'+a:'ascending_'+b for a,b in DIR.items()}}.get(value,value)
        new[key]=value
    return name+'['+','.join(k+'='+new[k] for k in sorted(new))+']'

def main(apply=False):
    p=v.Painter();o='r08/historic_berths';F='minecraft:smooth_stone';D='minecraft:gray_concrete';BLACK='minecraft:black_concrete';BAR='minecraft:iron_bars[east=false,north=true,south=true,waterlogged=false,west=false]'
    # Retire only the two explicitly superseded hulls, their boarding bridges and cranes.
    for z0,z1 in [(338,447),(462,561)]:
        p.fill(1432,58,z0,1456,62,z1,'minecraft:water[level=0]',o+'/retire_hull','owned')
        p.fill(1432,63,z0,1456,100,z1,'minecraft:air',o+'/retire_hull','owned')
    for z in (426,546):
        p.fill(1425,61,z-4,1438,62,z+4,'minecraft:water[level=0]',o+'/retire_gangway','owned')
        p.fill(1425,63,z-4,1438,72,z+4,'minecraft:air',o+'/retire_gangway','owned')
    for z in (386,498):p.fill(1400,65,z-9,1454,90,z+10,'minecraft:air',o+'/retire_crane','owned')
    imports=[]
    for s in SPECS:
        d=np.load(OUT/'ships'/(s['id']+'_source.npz'));a=d['blocks'];pal=d['palette'];lo=d['lo'];xyz=np.argwhere(np.array([q.split('[')[0] not in AIR|{'minecraft:water','minecraft:barrier'} for q in pal])[a])
        bounds=json.loads((OUT/'ships/selected.json').read_text());b=next(i for i in bounds if i['id']==s['id'])['actual_bounds'];xmin=b[0][0];cz=(b[0][2]+b[1][2])//2;cx,z0=s['destination']
        def transform(q):return (int(cx-(q[2]-cz)),int(q[1]-43),int(z0+q[0]-xmin))
        # Measured basin is already deeper than the 8-block draft: no broad terrain flattening.
        for iy,iz,ix in xyz:
            source=(int(ix+lo[0]),int(iy+lo[1]),int(iz+lo[2]));pos=transform(source)
            p.put(*pos,rotate(str(pal[a[iy,iz,ix]])),o+'/'+s['id'],'owned')
        for source,entry in iter_block_entities(SOURCE,'minecraft:overworld',s['lo'],s['hi']):
            pos=transform(source);entry=copy.deepcopy(entry)
            if str(entry.get('id','')) not in ('minecraft:sign','minecraft:bell'):continue
            for key,value in zip(('x','y','z'),pos):entry[key]=nbtlib.Int(value)
            if str(entry['id'])=='minecraft:sign':
                face=nbtlib.Compound({'messages':nbtlib.List[nbtlib.String]([nbtlib.String(str(entry.get('Text'+str(i),'{"text":""}'))) for i in range(1,5)]),'color':nbtlib.String('black'),'has_glowing_text':nbtlib.Byte(0)})
                entry=nbtlib.Compound({'id':nbtlib.String('minecraft:sign'),'x':nbtlib.Int(pos[0]),'y':nbtlib.Int(pos[1]),'z':nbtlib.Int(pos[2]),'front_text':face,'back_text':copy.deepcopy(face),'is_waxed':nbtlib.Byte(1)})
            p.block_entities[pos]=entry
        imports.append(dict(id=s['id'],source_bounds=b,destination_bounds=[transform((b[0][0],b[0][1],b[1][2])),transform((b[1][0],b[1][1],b[0][2]))],solid_cells=len(xyz),source_waterline=105,destination_waterline=62,rotation='east to south',author='Nekoseal',source_url='https://www.planetminecraft.com/project/ijn-destroyer-division-6-akatsuki-class-destroyer/'))
    # A pile-supported U pier gives each vessel its own boarding face.
    for x0,z0,x1,z1 in [(1423,578,1512,588),(1465,368,1477,578)]:
        p.fill(x0,63,z0,x1,64,z1,D,o+'/pier','new');p.fill(x0,64,z0,x1,64,z1,F,o+'/pier','owned')
        for x in (x0+1,x1-1):
            for z in range(z0+2,z1,18):p.fill(x,38,z,x+1,63,z+1,'minecraft:polished_deepslate',o+'/piles')
    # Continue the existing quay south to the transverse access pier, at Y64.
    p.fill(1412,60,569,1424,64,588,D,o+'/quay_extension');p.fill(1412,64,569,1424,64,588,F,o+'/quay_extension','owned')
    for z in range(372,575,18):
        for x in (1465,1477):
            p.fill(x,61,z,x,63,z+3,BLACK,o+'/fender','owned');p.put(x,65,z+1,'minecraft:polished_blackstone_wall[east=none,north=none,south=none,up=true,waterlogged=false,west=none]',o+'/bollard')
    for cx,start,label in [(1444,1423,'01'),(1494,1475,'02')]:
        # Deck survey selected the unobstructed aft waist (native deck Y68).
        end=cx-8;z=420
        for x in range(start,end+1):
            h=round((64+4*(x-start)/(end-start))*2)/2;yy=math.floor(h)
            p.fill(x,yy-1,z-2,x,yy,z+2,D,o+'/gangway_'+label,'owned')
            if h%1:p.fill(x,yy+1,z-2,x,yy+1,z+2,'minecraft:smooth_stone_slab[type=bottom,waterlogged=false]',o+'/gangway_'+label,'owned')
            p.fill(x,yy+2,z-2,x,72,z+2,'minecraft:air',o+'/gangway_headroom','owned')
            for zz in (z-3,z+3):p.put(x,yy+2,zz,'minecraft:iron_bars[east=true,north=false,south=false,waterlogged=false,west=true]',o+'/gangway_rail','owned')
        # Open the rail at this exact connection, retaining original hull and deck.
        p.fill(cx-10,69,z-2,cx-7,72,z+2,'minecraft:air',o+'/boarding_gate','owned')
        p.fill(cx-10,68,z-2,cx-8,68,z+2,'minecraft:spruce_planks',o+'/boarding_sill','owned')
        walk('ship_'+label+'/board',[[start+.5,65,z+.5],[end+.5,69,z+.5],[cx-7.5,69,z+.5]])
        walk('ship_'+label+'/aft_deck',[[cx-7.5,69,z+.5],[cx-7.5,69,402.5]])
        p.fill(start,65,z+5,start,68,z+6,D,o+'/credit_panel','owned')
        p.sign(start,67,z+7,['暁級・保存艦 '+label,'DD6 / 旧日本海軍','BUILD: NEKOSEAL','研究・見学用'],o+'/credit','south')
    walk('pier_main',[[1418.5,65,550.5],[1418.5,65,582.5],[1471.5,65,582.5],[1471.5,65,420.5]])
    # Clear full-width dock routes, and delineate drainage/edge strips rather than noise.
    for z in range(340,565,12):p.fill(1422,64,z,1422,64,z+5,'minecraft:yellow_terracotta',o+'/safety_line','owned')
    for x,z in [(1415,580),(1471,568),(1471,376),(1506,582)]:
        p.fill(x,65,z,x,72,z,D,o+'/lamp');p.fill(x-2,73,z,x+2,73,z,'projectseele:nerv_strip_light',o+'/lamp')
    p.meta.update(imports=imports,walk_cases=CASES,private_asset_only=True,removed_barriers=True,preserved_source_palette=True)
    p.apply('historic_berths') if apply else p.save_plan('historic_berths')
    (OUT/'port_walk_cases.json').write_text(json.dumps(CASES,ensure_ascii=False,indent=2),encoding='utf8')
    (OUT/'ship_imports.json').write_text(json.dumps(imports,indent=2),encoding='utf8')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
