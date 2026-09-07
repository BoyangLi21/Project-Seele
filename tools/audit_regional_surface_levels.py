"""Measure the complete natural-ground height field under the authored regional districts."""
from pathlib import Path
from collections import defaultdict
import argparse,json,time
import numpy as np
from query_blocks import iter_selected_sections

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_quality_r02'
SOIL={'minecraft:stone','minecraft:dirt','minecraft:grass_block','minecraft:coarse_dirt','minecraft:gravel','minecraft:sand','minecraft:sandstone','minecraft:clay','minecraft:rooted_dirt','minecraft:bedrock'}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--current',action='store_true');parser.add_argument('--reference',action='store_true');parser.add_argument('--wide',action='store_true');parser.add_argument('--label');parser.add_argument('--envelope',type=Path);args=parser.parse_args()
    baseline=json.loads((OUT/'source_manifest.json').read_text(encoding='utf-8'))
    world=Path(baseline['world'] if args.current else baseline['backup'])
    if args.reference:world=ROOT/'.Codex/world-expansion/pre-regional-geometry'
    plan=json.loads((ROOT/'artifacts/world_expansion_20260907/regional_plan.json').read_text(encoding='utf-8'))
    zones=[z for z in plan['zones'] if z['kind'] in ('district','airport','gateway')]
    # Bounds include actual terminal buildings, not the superseded conceptual airport boxes.
    boxes=[z['bounds'] for z in zones]+[[-2210,-1390,-425,120],[440,1250,1025,1570]]
    generated={tuple(c) for c in plan['chunks']};selected={}
    for a,b,c,d in boxes:
        for cx in range((a-32)//16,(b+32)//16+1):
            for cz in range((c-32)//16,(d+32)//16+1):
                if (cx,cz) in generated:selected[cx,cz]=set(range(3,14))
    if args.wide or args.envelope:
        envelope=json.loads((args.envelope or OUT/'terrain_envelope.json').read_text(encoding='utf-8'))
        selected={tuple(c):set(range(2,16)) for c in envelope['chunks']}
    lowx=min(x for x,z in selected)*16;lowz=min(z for x,z in selected)*16
    nx=(max(x for x,z in selected)+1)*16-lowx;nz=(max(z for x,z in selected)+1)*16-lowz
    height=np.full((nz,nx),-32768,dtype=np.int16);known=np.zeros((nz,nx),dtype=bool);start=time.monotonic();count=0
    for cx,cz,sy,pal,idx in iter_selected_sections(world,'projectseele:geofront',selected,skip_unfinished=args.reference):
        mask=np.asarray([s.split('[')[0] in SOIL for s in pal])[idx].reshape(16,16,16)
        top=np.where(mask,np.arange(16)[:,None,None]+sy*16,-32768).max(axis=0)
        zz,xx=cz*16-lowz,cx*16-lowx
        height[zz:zz+16,xx:xx+16]=np.maximum(height[zz:zz+16,xx:xx+16],top)
        known[zz:zz+16,xx:xx+16]=True;count+=1
        if count%16384==0:print('Sections',count,'seconds',round(time.monotonic()-start,1),flush=True)
    suffix=args.label or ('reference' if args.reference else 'after' if args.current else 'before')
    np.savez_compressed(OUT/f'surface_levels_{suffix}.npz',height=height,known=known,origin=[lowx,lowz])
    report=[]
    for zone in zones:
        x0,x1,z0,z1=zone['bounds'];a=height[z0-lowz:z1-lowz+1,x0-lowx:x1-lowx+1];ok=a>-32768
        if not ok.any():continue
        dx=np.abs(np.diff(a.astype(int),axis=1));dz=np.abs(np.diff(a.astype(int),axis=0))
        report.append(dict(id=zone['id'],min=int(a[ok].min()),max=int(a[ok].max()),median=float(np.median(a[ok])),
            adjacent_jumps_over_two=int(((dx>2)&ok[:,:-1]&ok[:,1:]).sum()+((dz>2)&ok[:-1]&ok[1:]).sum())))
    (OUT/f'surface_levels_{suffix}.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('MEASURED',report,flush=True)

if __name__=='__main__':main()
