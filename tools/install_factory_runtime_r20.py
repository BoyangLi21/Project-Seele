"""Move the parked fleet and its typed bindings after the R20 civil patch."""
import argparse,copy,json,math,msvcrt,shutil
from pathlib import Path
from collections import defaultdict
import nbtlib
import regional_voxels as vox
from query_blocks import read_box
from transplant_s22_authority import read_region,parse_chunk,build_region,chunk_blob
from apply_s20_approved_semantic_repairs import atomic_replace

OUT=vox.ROOT/'artifacts/world_rebuild_r20/factory';DZ=-144

def packed(x,y,z):
    v=((x&0x3ffffff)<<38)|((z&0x3ffffff)<<12)|(y&0xfff)
    return v-(1<<64) if v>=1<<63 else v

def main(world):
    world=Path(world);receipt=OUT/('runtime_'+world.name+'.json');assert not receipt.exists(),'Runtime already migrated; do not move twice'
    backup=OUT/('runtime_before_'+world.name);backup.mkdir();moved=[]
    with (world/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        for x in (-12,30,72):assert read_box(world,vox.DIM,(x,-411,-36),(x,-411,-36))[(x,-411,-36)]=='minecraft:lodestone'
        fp=world/'data/projectseele_eva_fleet.dat';fleet=nbtlib.load(fp);entries=fleet['data']['Fleet'];assert all(str(e['Phase'])=='PARKED' for e in entries)
        ids={tuple(map(int,e['Canonical'])):int(e['Variant']) for e in entries};plugs={tuple(map(int,e['EntryPlug'])) for e in entries}
        roster_path=world/'nerv_staff_r15.json';roster=json.loads(roster_path.read_text(encoding='utf8'));stations={s['id']:s for s in roster['stations'] if s['id'].startswith('hangar/') and -165<s['feet'][2]<-50}
        entities_dir=world/'dimensions/projectseele/geofront/entities';regions={};add=defaultdict(list);seen=set()
        for path in entities_dir.glob('r.*.*.mca'):
            if path.stat().st_size<8192:continue
            stamps,blobs=read_region(path);changed=False
            for slot,blob in enumerate(blobs):
                if blob is None:continue
                root=parse_chunk(blob);keep=[];dirty=False
                for e in root.get('Entities',[]):
                    uid=tuple(map(int,e.get('UUID',[])));assert uid not in seen;seen.add(uid);kind=str(e.get('id'));pos=list(map(float,e.get('Pos',[0,0,0])))
                    staff=str(e.get('StaffId','')) in stations
                    dummy=kind=='projectseele:training_pilot' and -50<pos[0]<116 and -165<pos[2]<-50
                    if uid not in ids and uid not in plugs and not staff and not dummy:keep.append(e);continue
                    old=copy.deepcopy(e);newpos=[pos[0],pos[1],pos[2]+DZ]
                    if staff:
                        s=stations[str(e['StaffId'])];x,y,z=s['feet'];newpos=[x+.5,y,z+DZ+.5];e['StaffStation']=nbtlib.Long(packed(x,y,z+DZ))
                    if uid in ids:
                        x=(-12,30,72)[ids[uid]];newpos=[x+.5,-442,-239.5];e['SeeleSortieParkingBed']=nbtlib.Long(packed(x,-443,-240));e['Rotation']=nbtlib.List[nbtlib.Float]([180,0]);e['SeeleNervLogisticsYaw']=nbtlib.Float(180)
                    e['Pos']=nbtlib.List[nbtlib.Double](newpos);e['Motion']=nbtlib.List[nbtlib.Double]([0,0,0]);e['FallDistance']=nbtlib.Float(0)
                    cx,cz=math.floor(newpos[0])//16,math.floor(newpos[2])//16;target=entities_dir/f'r.{cx//32}.{cz//32}.mca';newslot=(cz%32)*32+cx%32;add[target,newslot].append(e);dirty=True
                    moved.append({'id':kind,'uuid':uid,'before':pos,'after':newpos,'before_nbt':old.snbt()})
                if dirty:root['Entities']=nbtlib.List[nbtlib.Compound](keep);blobs[slot]=chunk_blob(root);changed=True
            if changed:regions[path]=(stamps,blobs)
        assert ids.keys()<=seen and plugs<=seen
        for (path,slot),items in add.items():
            if path not in regions:regions[path]=read_region(path) if path.exists() and path.stat().st_size>=8192 else (bytes(4096),[None]*1024)
            stamps,blobs=regions[path];root=parse_chunk(blobs[slot]) if blobs[slot] else nbtlib.File({'DataVersion':nbtlib.Int(3465),'Position':nbtlib.IntArray([math.floor(float(items[0]['Pos'][0]))//16,math.floor(float(items[0]['Pos'][2]))//16]),'Entities':nbtlib.List[nbtlib.Compound]()})
            root['Entities'].extend(items);blobs[slot]=chunk_blob(root)
            assert parse_chunk(blobs[slot])==root,'Entity chunk must round-trip as a named NBT file before commit'
        for path,(stamps,blobs) in regions.items():
            if path.exists():shutil.copy2(path,backup/path.name)
            atomic_replace(path,build_region(stamps,blobs))
        shutil.copy2(fp,backup/fp.name)
        for e in entries:e['Carrier']=nbtlib.Int(-240)
        fleet.save(fp)
        shutil.copy2(roster_path,backup/roster_path.name)
        for s in stations.values():s['feet'][2]+=DZ
        roster_path.write_text(json.dumps(roster,ensure_ascii=False,indent=2),encoding='utf8')
        cp=world/'dimensions/projectseele/geofront/data/capabilities.dat';caps=nbtlib.load(cp);groups=caps['data']['movingelevators:elevator_groups'];assert '97;-15' in groups;shutil.copy2(cp,backup/cp.name);del groups['97;-15'];caps.save(cp)
        # Preserve inventory and health; only a player standing in the removed
        # works is moved to the retained, newly roofed observation room.
        players=[]
        level_path=world/'level.dat';level=nbtlib.load(level_path)
        host=level['Data'].get('Player')
        if host is not None and str(host.get('Dimension',''))=='projectseele:geofront':
            q=list(map(float,host.get('Pos',[0,0,0])))
            if -48<=q[0]<=164 and -513<=q[1]<=-310 and -302<=q[2]<=24:
                shutil.copy2(level_path,backup/'level.dat');host['Pos']=nbtlib.List[nbtlib.Double]([104.5,-369,-70.5]);host['Motion']=nbtlib.List[nbtlib.Double]([0,0,0]);host['FallDistance']=nbtlib.Float(0);level.save(level_path);players.append({'file':'level.dat/Data/Player','before':q,'after':[104.5,-369,-70.5]})
        for path in (world/'playerdata').glob('*.dat'):
            d=nbtlib.load(path);q=list(map(float,d.get('Pos',[0,0,0])))
            if -48<=q[0]<=164 and -513<=q[1]<=-310 and -302<=q[2]<=24:
                shutil.copy2(path,backup/('player_'+path.name));d['Pos']=nbtlib.List[nbtlib.Double]([104.5,-369,-70.5]);d['Motion']=nbtlib.List[nbtlib.Double]([0,0,0]);d['FallDistance']=nbtlib.Float(0);d.save(path);players.append({'file':path.name,'before':q,'after':[104.5,-369,-70.5]})
        manifest=json.loads((OUT/'layout.json').read_text());manifest['installed']=True;manifest['runtime_identity_receipt']=str(receipt);(world/'eva_facility_r20.json').write_text(json.dumps(manifest,indent=2))
        result={'world':str(world),'moved':moved,'retired_native_lift':'97;-15','repositioned_players':players,'backup':str(backup),'original_fleet_and_plug_ids_preserved':True};receipt.write_text(json.dumps(result,indent=2))
    print('R20 runtime installed',world.name,'moved actors',len(moved))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--world',type=Path,default=vox.WORLD);main(a.parse_args().world)
