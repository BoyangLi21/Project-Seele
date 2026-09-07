"""Scan saved natural ground above the final authored grading field.

Road foundation elevations are included; original moving-city/launch cores and
the accepted gateway remain explicit exclusions. The scanner never edits soil.
"""
from collections import defaultdict,Counter
from pathlib import Path
import json,argparse
import numpy as np
from query_blocks import iter_selected_sections
from regional_voxels import ROOT,WORLD,DIM

R02=ROOT/'artifacts/world_quality_r02';OUT=ROOT/'artifacts/world_quality_r03'
SOIL={'minecraft:stone','minecraft:dirt','minecraft:grass_block','minecraft:coarse_dirt','minecraft:gravel','minecraft:sand','minecraft:sandstone','minecraft:clay'}

def classify_surface_grade():
    load=lambda p:json.loads(p.read_text(encoding='utf-8'))
    old=ROOT/'artifacts/world_expansion_20260907';report=load(OUT/'surface_grade_final.json');ids={r['id'] for r in load(OUT/'transit_clearance.json')['results']};rails={}
    for file in [old/'transit2/track_samples.json',R02/'estate_transit_draft/track_samples.json',R02/'airport_rail_splice_prototype/track_samples.json',R02/'airfield_profile_native/track_samples.json']:
        for r in load(file):
            if r['id'] in ids and r['mode']=='TRAIN':rails[r['id']]=r
    boxes=[]
    for rail in rails.values():
        for x,y,z in {tuple(map(round,p)) for p in rail['points'][::2]}:
            if y>=0:boxes.append(((x-4,y-3,z-4,x+4,y+8,z+4),'rail_engineering_envelope'))
    for b in load(R02/'terrain_repair/protected.json'):
        if b['owner'].startswith(('airport_terminal_access','airport_gate_stair','airport_gate_crossing')):boxes.append((b['box'],'airport_stair_or_underpass'))
    indexed=defaultdict(list)
    for box,kind in boxes:
        x0,y0,z0,x1,y1,z1=box
        for cx in range(x0//16,x1//16+1):
            for cz in range(z0//16,z1//16+1):indexed[cx,cz].append((box,kind))
    roads=[]
    for name in ('road_surfaces.npz','extension_road_surfaces.npz'):
        with np.load(R02/name) as a:roads.append((a['mask'],tuple(map(int,a['origin']))))
    counts=Counter();repair=[]
    for row in report['gaps']:
        x,y,z=row[:3];kind=None
        for b,k in indexed[x//16,z//16]:
            if b[0]<=x<=b[3] and b[1]<=y<=b[4] and b[2]<=z<=b[5]:kind=k;break
        if kind is None:
            for mask,(ox,oz) in roads:
                ix,iz=x-ox,z-oz
                if 0<=iz<mask.shape[0] and 0<=ix<mask.shape[1] and mask[iz,ix]:kind='verified_road_datum';break
        if kind is None:repair.append([x,y,z]);kind='unfilled_grade_edge'
        counts[kind]+=1
    result=dict(candidates=len(report['gaps']),counts=dict(counts),repair_columns=repair,authority='Current commissioned rails with authored four-block grading protection, existing airport access reservations, and independently verified road datums')
    (OUT/'surface_grade_classification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(dict(counts),flush=True)
    print('GROUND EDGE CANDIDATES',len(repair),repair[:12],flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--baseline',action='store_true');ap.add_argument('--grade-only',action='store_true');ap.add_argument('--classify',action='store_true');args=ap.parse_args()
    if args.classify:classify_surface_grade();return
    world=Path(json.loads((OUT/'source_manifest.json').read_text())['backup']) if args.baseline else WORLD
    targets={};exclusions=[(-210,-20,270,464),(-65,-175,195,20),(-432,690,-280,833)]
    for file in ('terrain_target.npz','extension_terrain_target.npz'):
        a=np.load(R02/file);h=a['height'];m=a['active'];ox,oz=map(int,a['origin'])
        for iz in range(0,h.shape[0],16):
            for ix in range(0,h.shape[1],16):
                mask=m[iz:iz+16,ix:ix+16].copy()
                if not mask.any():continue
                cx,cz=(ox+ix)//16,(oz+iz)//16
                old=targets.get((cx,cz));values=h[iz:iz+16,ix:ix+16].copy()
                if old is not None:values=np.where(mask,values,old[0]);mask|=old[1]
                targets[cx,cz]=(values,mask)
    for file in ('road_surfaces.npz','extension_road_surfaces.npz'):
        a=np.load(R02/file);ox,oz=map(int,a['origin']);height=(a['height2']-1)//2;road_mask=a['mask']
        for (cx,cz),(values,mask) in targets.items():
            ix,iz=cx*16-ox,cz*16-oz
            if ix<0 or iz<0 or ix+16>height.shape[1] or iz+16>height.shape[0]:continue
            rm=road_mask[iz:iz+16,ix:ix+16]
            values[rm]=height[iz:iz+16,ix:ix+16][rm] if args.grade_only else np.maximum(values[rm],height[iz:iz+16,ix:ix+16][rm])
    for (cx,cz),(values,mask) in targets.items():
        for x0,z0,x1,z1 in exclusions:
            ax=max(x0-cx*16,0);bx=min(x1-cx*16+1,16);az=max(z0-cz*16,0);bz=min(z1-cz*16+1,16)
            if ax<bx and az<bz:mask[az:bz,ax:bx]=False
    selected={c:set(range(int(v[m].min())//16,int(v[m].max())//16+1 if args.grade_only else 16)) for c,(v,m) in targets.items() if m.any()}
    findings=[];counts=Counter();chunks=Counter();measured=set();gaps=[]
    for cx,cz,sy,pal,idx in iter_selected_sections(world,DIM,selected):
        measured.add((cx,cz,sy))
        values,active=targets[cx,cz];a=idx.reshape(16,16,16)
        if args.grade_only:
            zz,xx=np.indices((16,16));codes=a[np.clip(values-sy*16,0,15),zz,xx]
            empty=np.asarray([s.split('[')[0] in ('minecraft:air','minecraft:cave_air','minecraft:void_air') for s in pal])[codes]
            for z,x in np.argwhere(active&empty&(values//16==sy)):gaps.append([cx*16+int(x),int(values[z,x]),cz*16+int(z),pal[codes[z,x]]])
            continue
        bad=np.asarray([s.split('[')[0] in SOIL for s in pal])[a]&active[None,:,:]&(np.arange(sy*16,sy*16+16)[:,None,None]>values[None,:,:])
        if not bad.any():continue
        for y,z,x in np.argwhere(bad):
            state=pal[a[y,z,x]];counts[state]+=1;chunks[cx,cz]+=1
            findings.append([cx*16+int(x),sy*16+int(y),cz*16+int(z),int(values[z,x]),state])
    missing=[(cx,cz,sy) for (cx,cz),ys in selected.items() for sy in ys if (cx,cz,sy) not in measured]
    if missing:raise RuntimeError(f'Unmeasured terrain sections: {len(missing)} {missing[:8]}')
    result=dict(columns=sum(int(m.sum()) for v,m in targets.values()),scanned_chunks=len(selected),measured_sections=len(measured),unmeasured_sections=0,above_grade_cells=len(findings),states=dict(counts),excluded_original_frames=exclusions,findings=findings)
    if args.grade_only:
        for key in ('above_grade_cells','states','findings'):result.pop(key)
        result.update(air_at_surface=len(gaps),gaps=gaps)
    name='surface_grade_final.json' if args.grade_only else 'ground_baseline.json' if args.baseline else 'ground_final.json';(OUT/name).write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
    if args.grade_only:print('EMPTY SURFACE CANDIDATES',result['columns'],'columns',len(gaps),'empty',gaps[:8],flush=True)
    else:print('GROUND',result['columns'],'columns',len(selected),'chunks','above-grade natural cells',len(findings),'top chunks',chunks.most_common(8),flush=True)

if __name__=='__main__':main()
