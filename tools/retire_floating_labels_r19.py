"""Remove only catalogued architectural text displays with measured empty backing."""
import argparse,hashlib,json,math,msvcrt,shutil,uuid
from datetime import datetime
from pathlib import Path
import nbtlib
import regional_voxels as vox
from query_blocks import AIR,read_box
from transplant_s22_authority import read_region,parse_chunk,build_region,chunk_blob
from apply_s20_approved_semantic_repairs import atomic_replace

OUT=vox.ROOT/'artifacts/world_repair_r19/labels'
def identity(row):return str(uuid.UUID(bytes=b''.join((int(n)&0xffffffff).to_bytes(4,'big') for n in row)))
def label_id(name):return str(uuid.UUID(bytes=hashlib.md5(('SEELE_R03_SIGN/'+name).encode()).digest(),version=3))

def survey():
    OUT.mkdir(parents=True,exist_ok=True);catalog=json.loads((vox.WORLD/'regional_wayfinding.json').read_text(encoding='utf8'));cache={};report=[]
    def state(pos):
        x,y,z=pos;k=(x//16,y//16,z//16)
        if k not in cache:
            a,b,c=k;cache[k]=read_box(vox.WORLD,vox.DIM,(a*16,b*16,c*16),(a*16+15,b*16+15,c*16+15))
        return cache[k].get(pos,'UNKNOWN')
    for row in catalog:
        x,y,z=row['position'];angle=math.radians(row['yaw']);normal=(-math.sin(angle),math.cos(angle))
        # Fixed displays are placed a few hundredths outside their intended
        # wall. Test both text baseline and centre, not arbitrary nearby air.
        samples={tuple(map(math.floor,(x-normal[0]*depth,y+dy,z-normal[1]*depth))) for depth in (.08,.3,.65) for dy in (0,.3,.65)}
        observed={','.join(map(str,p)):state(p) for p in samples}
        empty=all(v.split('[')[0] in AIR|{'minecraft:light'} for v in observed.values())
        report.append(dict(id=row['id'],uuid=label_id(row['id']),position=row['position'],backing=observed,unsupported=empty))
    (OUT/'backing_survey.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print('Catalogued labels',len(report),'unsupported',sum(r['unsupported'] for r in report),flush=True)
    print('Unsupported IDs',[r['id'] for r in report if r['unsupported']],flush=True)

def apply():
    report=json.loads((OUT/'backing_survey.json').read_text(encoding='utf8'));wanted={r['uuid']:r for r in report if r['unsupported']}
    catalog_path=vox.WORLD/'regional_wayfinding.json';catalog=json.loads(catalog_path.read_text(encoding='utf8'))
    current={row['id'] for row in catalog};retired={r['id'] for r in wanted.values()}
    if not retired<=current:raise RuntimeError('Label catalogue changed since measured survey')
    folder=OUT/('applied_'+datetime.now().strftime('%Y%m%d_%H%M%S'));folder.mkdir();removed=[];pending=[]
    with (vox.WORLD/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        shutil.copy2(catalog_path,folder/catalog_path.name)
        for path in sorted((vox.WORLD/'dimensions/projectseele/geofront/entities').glob('r.*.*.mca')):
            if path.stat().st_size==0:continue
            stamps,chunks=read_region(path);dirty=False
            for i,blob in enumerate(chunks):
                if blob is None:continue
                root=parse_chunk(blob);old=root.get('Entities',[]);keep=[];changed=False
                for entity in old:
                    ident=identity(entity['UUID']) if 'UUID' in entity else ''
                    if ident not in wanted:keep.append(entity);continue
                    if str(entity.get('id'))!='minecraft:text_display' or 'projectseele_r03_wayfinding' not in map(str,entity.get('Tags',[])):raise RuntimeError(('Wrong entity at known label UUID',ident))
                    if any(abs(float(a)-float(b))>.02 for a,b in zip(entity['Pos'],wanted[ident]['position'])):raise RuntimeError(('Label moved since catalogue',ident))
                    removed.append(dict(id=wanted[ident]['id'],uuid=ident,snbt=entity.snbt(),region=path.name,chunk=i));changed=True
                if changed:root['Entities']=nbtlib.List[nbtlib.Compound](keep);chunks[i]=chunk_blob(root);dirty=True
            if dirty:pending.append((path,build_region(stamps,chunks)))
        missing=set(wanted)-{r['uuid'] for r in removed}
        if missing:raise RuntimeError(('Catalogued labels not found; inspect saved backup before continuing',missing))
        for path,data in pending:
            shutil.copy2(path,folder/path.name);atomic_replace(path,data)
            if path.read_bytes()!=data:raise RuntimeError(('Entity patch readback mismatch',path))
        catalog_path.write_text(json.dumps([row for row in catalog if row['id'] not in retired],ensure_ascii=False,indent=2),encoding='utf8')
        (folder/'receipt.json').write_text(json.dumps(dict(world=str(vox.WORLD),verified=True,removed=removed,remaining_labels=len(catalog)-len(retired)),ensure_ascii=False,indent=2),encoding='utf8')
    print('Removed known floating labels',len(removed),'backup',folder,flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');args=ap.parse_args();apply() if args.apply else survey()
