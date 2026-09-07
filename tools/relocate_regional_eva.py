"""Move the parked EVA plant as one measured payload, preserving actor identities.

Block IO is centralized in query_blocks and the shared measured patch engine.
The old pyramid stays in its own coordinate frame. Runtime state is moved
only after exact block readback succeeds; the regional marker activates last.
"""
from collections import defaultdict,Counter
from datetime import datetime
from pathlib import Path
import argparse,copy,json,math,shutil
import nbtlib
import numpy as np
from query_blocks import iter_selected_sections,iter_block_entities,dimension_dir,AIR
from regional_voxels import Painter,ROOT,WORLD,OUT,natural
from regional_architecture import FLOOR,DARK,STEEL,LIGHT
from transplant_s22_authority import read_region,parse_chunk,build_region,chunk_blob
from apply_s20_approved_semantic_repairs import atomic_replace

BOXES=[(-46,-505,116,110,-350,248)]+[(x-18,-500,202,x+18,89,238) for x in (-12,30,72)]
DZ=-256


def selected_boxes(boxes):
    selected=defaultdict(set)
    for x0,y0,z0,x1,y1,z1 in boxes:
        for cx in range(x0//16,x1//16+1):
            for cz in range(z0//16,z1//16+1):selected[cx,cz].update(range(y0//16,y1//16+1))
    return selected


def shell(x,y,z):
    if not -466<=y<=-294:return False
    h=math.floor(120*(1-(y+466)/172)+.5);nh=math.floor(120*(1-min(1,(y+467)/172))+.5)
    return abs(x-30)<=h and abs(z-327)<=h and (y==-466 or abs(x-30)>=nh or abs(z-327)>=nh)


def runs(p,xs,states,y,z,owner,delta=0,mode='owned'):
    start=0
    while start<len(xs):
        end=start+1
        while end<len(xs) and xs[end]==xs[end-1]+1 and states[end]==states[start]:end+=1
        p.fill(int(xs[start]),int(y),int(z+delta),int(xs[end-1]),int(y),int(z+delta),str(states[start]),owner,mode)
        start=end


def geometry(source):
    p=Painter();counts=Counter()
    for cx,cz,sy,pal,idx in iter_selected_sections(source,'projectseele:geofront',selected_boxes(BOXES)):
        state_array=np.asarray(pal)[idx].reshape(16,16,16)
        for ly in range(16):
            y=sy*16+ly
            for lz in range(16):
                z=cz*16+lz;xs=[];payload=[];retired=[]
                for lx in range(16):
                    x=cx*16+lx
                    if not any(a<=x<=d and b<=y<=e and c<=z<=f for a,b,c,d,e,f in BOXES):continue
                    old=str(state_array[ly,lz,lx])
                    if shell(x,y,z):
                        # Keep actual shell material at headquarters; never translate it into the machine plant.
                        continue
                    xs.append(x)
                    soil=old.split('[')[0] in {'minecraft:stone','minecraft:dirt','minecraft:grass_block','minecraft:gravel','minecraft:sand','minecraft:coarse_dirt'}
                    payload.append('minecraft:air' if soil and y>-467 else old)
                    retired.append('minecraft:stone' if y<-467 or 24<y<80 else 'minecraft:grass_block[snowy=false]' if y==-467 else FLOOR if y==80 else 'minecraft:air')
                    counts['payload_cells']+=1
                runs(p,xs,payload,y,z,'eva/move_existing_plant',DZ)
                runs(p,xs,retired,y,z,'eva/retire_old_plant')
    for box in BOXES:
        for pos,tag in iter_block_entities(source,'projectseele:geofront',box[:3],box[3:]):
            if shell(*pos):continue
            t=copy.deepcopy(tag);new=(pos[0],pos[1],pos[2]+DZ);t['z']=nbtlib.Int(new[2])
            if 'data' in t and 'controllerZ' in t['data']:t['data']['controllerZ']=nbtlib.Int(int(t['data']['controllerZ'])+DZ)
            p.block_entities[new]=t
    # Reclose former launch holes only where they intersect the actual pyramid shell.
    for y in range(-466,-293):
        h=math.floor(120*(1-(y+466)/172)+.5);nh=math.floor(120*(1-min(1,(y+467)/172))+.5)
        for z in range(327-h,328-nh):
            for x in range(30-h,31+h):
                if any(a<=x<=d and b<=y<=e and c<=z<=f for a,b,c,d,e,f in BOXES):
                    p.put(x,y,z,'minecraft:reinforced_deepslate','eva/restore_headquarters_shell','owned')
    # Measured residual soil: a thin old terrain slab floating over the new campus.
    clean=[(-76,-466,80,174,-350,262)]
    soils={'minecraft:stone','minecraft:dirt','minecraft:grass_block','minecraft:gravel','minecraft:sand','minecraft:coarse_dirt'}
    for cx,cz,sy,pal,idx in iter_selected_sections(source,'projectseele:geofront',selected_boxes(clean)):
        a=np.asarray(pal)[idx].reshape(16,16,16)
        for ly in range(16):
            y=sy*16+ly
            if not -466<=y<=-350:continue
            for lz in range(16):
                z=cz*16+lz;xs=[]
                if not 80<=z<=262:continue
                for lx in range(16):
                    x=cx*16+lx
                    if -76<=x<=174 and str(a[ly,lz,lx]).split('[')[0] in soils and not shell(x,y,z):xs.append(x)
                runs(p,xs,['minecraft:air']*len(xs),y,z,'eva/clear_confirmed_old_soil')
                counts['old_soil_cells']+=len(xs)
    # Foundation and apron surround the preserved wet basins and machine cavities.
    p.fill(-55,-512,-150,162,-506,14,'minecraft:deepslate_bricks','eva/new_foundation')
    for a,b,c,d in [(-55,-47,-150,14),(111,162,-150,14),(-46,110,-150,-141),(-46,110,-7,14)]:
        p.fill(a,-505,c,b,-444,d,'minecraft:deepslate_bricks','eva/new_plinth')
        p.fill(a,-443,c,b,-443,d,DARK,'eva/new_apron')
    for z in range(-135,10,24):
        p.fill(113,-466,z,160,-461,z,'minecraft:polished_basalt[axis=x]','eva/plinth_ribs')
        p.put(158,-442,z,LIGHT,'eva/plinth_lighting')
    # Lower cage lift south landing -> station: a real supported gallery.
    p.fill(90,-443,-45,151,-443,-41,FLOOR,'eva/platform_join')
    p.fill(91,-442,-45,151,-438,-41,'minecraft:air','eva/platform_join','owned')
    p.meta['relocation']=dict(delta=[0,0,DZ],boxes=BOXES,counts=dict(counts),source=str(source))
    return p


def runtime():
    import msvcrt
    lock=(WORLD/'session.lock').open('r+b');msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    rel=Path('dimensions/projectseele/geofront');directory=WORLD/rel/'entities'
    backup=OUT/('eva_runtime_'+datetime.now().strftime('%Y%m%d_%H%M%S'));backup.mkdir()
    regions={};additions=defaultdict(list);moved=[];all_ids=set()
    fleet_path=WORLD/'data/projectseele_eva_fleet.dat';fleet=nbtlib.load(fleet_path)
    cap_path=WORLD/rel/'data/capabilities.dat';cap=nbtlib.load(cap_path)
    for key in ('96;204','97;241'):
        if int(cap['data']['movingelevators:elevator_groups'][key]['group']['isMoving']):raise RuntimeError('Native personnel car is moving')
    fleet_ids={tuple(map(int,e['Canonical'])) for e in fleet['data']['Fleet']}
    plug_ids={tuple(map(int,e['EntryPlug'])) for e in fleet['data']['Fleet']}
    if any(str(e['Phase'])!='PARKED' for e in fleet['data']['Fleet']):raise RuntimeError('Fleet must be parked before relocation')
    for path in directory.glob('r.*.*.mca'):
        if path.stat().st_size<8192:continue
        stamps,blobs=read_region(path);dirty=False
        for slot,blob in enumerate(blobs):
            if blob is None:continue
            root=parse_chunk(blob);keep=[]
            for entity in root.get('Entities',[]):
                ident=tuple(map(int,entity.get('UUID',[])));name=str(entity.get('id'));pos=list(map(float,entity.get('Pos',[0,0,0])))
                if ident in all_ids:raise RuntimeError('Duplicate preexisting actor identity')
                all_ids.add(ident)
                inside=any(a<=pos[0]<=d+1 and b<=pos[1]<=e+1 and c<=pos[2]<=f+1 for a,b,c,d,e,f in BOXES)
                move=ident in fleet_ids|plug_ids or name=='projectseele:training_pilot' and inside or inside and name in {'minecraft:armor_stand','projectseele:entry_plug_crane'}
                armament=name=='projectseele:nerv_armament_station'
                if not move and not armament:keep.append(entity);continue
                newpos=[30.5,81.,-120.5] if armament else [pos[0],pos[1],pos[2]+DZ]
                entity['Pos']=nbtlib.List[nbtlib.Double](map(nbtlib.Double,newpos))
                additions[math.floor(newpos[0])//16,math.floor(newpos[2])//16].append(entity)
                moved.append(dict(id=name,uuid=ident,before=pos,after=newpos));dirty=True
            root['Entities']=nbtlib.List[nbtlib.Compound](keep);blobs[slot]=chunk_blob(root)
        if dirty:regions[path]=(stamps,blobs)
    if not fleet_ids|plug_ids <= {tuple(e['uuid']) for e in moved}:raise RuntimeError('Missing canonical EVA or plug')
    for (cx,cz),entities in additions.items():
        path=directory/f'r.{cx//32}.{cz//32}.mca'
        if path not in regions:regions[path]=read_region(path) if path.exists() and path.stat().st_size>=8192 else (bytes(4096),[None]*1024)
        stamps,blobs=regions[path];slot=(cx&31)+(cz&31)*32
        root=parse_chunk(blobs[slot]) if blobs[slot] else nbtlib.File({'DataVersion':nbtlib.Int(3465),'Position':nbtlib.IntArray([cx,cz]),'Entities':nbtlib.List[nbtlib.Compound]()})
        root['Entities'].extend(entities);blobs[slot]=chunk_blob(root)
    for path,(stamps,blobs) in regions.items():
        if path.exists():shutil.copy2(path,backup/path.name)
        atomic_replace(path,build_region(stamps,blobs))
    shutil.copy2(fleet_path,backup/fleet_path.name)
    for entry in fleet['data']['Fleet']:entry['Carrier']=nbtlib.Int(int(entry['Carrier'])+DZ)
    fleet.save(fleet_path)
    shutil.copy2(cap_path,backup/'capabilities.dat')
    groups=cap['data']['movingelevators:elevator_groups']
    for old,new in [('96;204','96;-52'),('97;241','97;-15')]:
        group=groups.pop(old)
        if int(group['group']['isMoving']):raise RuntimeError('Native personnel car is moving')
        group['pos']['z']=nbtlib.Int(int(group['pos']['z'])+DZ);groups[new]=group
    cap.save(cap_path)
    receipt=dict(moved=moved,canonical_evas=len(fleet_ids),canonical_plugs=len(plug_ids),native_groups=2)
    (backup/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    for path in (WORLD/'regional_plan.json',OUT/'regional_plan.json'):
        plan=json.loads(path.read_text(encoding='utf-8'));plan['eva_migrated']=True;plan['eva_runtime_receipt']=str(backup/'receipt.json');plan['main_lift']['exit']='north'
        path.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    print('EVA RUNTIME MOVED',Counter(e['id'] for e in moved),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    plan=json.loads((WORLD/'regional_plan.json').read_text(encoding='utf-8'))
    if plan['eva_migrated']:raise RuntimeError('EVA sector has already been migrated')
    source=WORLD if args.apply else ROOT/'backups/SEELE_REGIONAL_EXPANSION_20260907_052718'
    p=geometry(source)
    if args.apply:
        p.apply('eva_relocation');runtime()
    else:p.save_plan('eva_relocation')


if __name__=='__main__':main()
