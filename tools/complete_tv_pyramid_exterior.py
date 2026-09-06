"""Complete the measured pyramid shell omitted by the initial interior envelope.

Only the not-yet-handed-off TV preview is writable. Retain room air and the
earlier facility masks, except the measured empty footing beneath the east
outdoor apron. Transfer the source's physical shell/base, never its
old raised apron or natural terrain. Grade new natural ground around its base.
"""
import argparse
from collections import defaultdict, Counter
from datetime import datetime
from functools import lru_cache
import gzip
import json
import math
from pathlib import Path
import shutil

from query_blocks import read_box, iter_box_cells, dimension_dir, AIR
from apply_s20_approved_semantic_repairs import Change, rewrite_region, atomic_replace

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'run/saves/SEELE_PYRAMID_TV_PREVIEW_20260905'
WORLD=ROOT/'run/saves/SEELE_TV_WORLD_PREVIEW_20260906'
OUT=ROOT/'artifacts/tv_world_preview_20260906'
DIM='projectseele:geofront'
NATURAL=AIR|{'minecraft:stone','minecraft:dirt','minecraft:grass_block','minecraft:gravel',
             'minecraft:sand','minecraft:water','minecraft:coarse_dirt'}


def smooth(value):
    t=max(0,min(1,value))
    return t*t*(3-2*t)


@lru_cache(maxsize=None)
def ground(x,z,extended):
    lake=((x+310)/310)**2+((z-340)/200)**2+.075*math.sin((x+z)/47)+.045*math.cos(z/37)
    def gaussian(cx,cz,r): return math.exp(-((x-cx)**2+(z-cz)**2)/(r*r))
    y=-478+3.5*math.sin(x/137)*math.cos(z/193)+2.4*math.sin((x+z)/67)
    y+=29*gaussian(420,830,310)+17*gaussian(-230,1030,390)+11*gaussian(720,330,290)
    if lake<1.2:
        t=smooth((lake-.60)/.60)
        y=-484*(1-t)-471*t
    left,bottom=(-90,447) if extended else (-68,400)
    distance=math.hypot(max(left-x,0,x-160),max(96-z,0,z-bottom))
    campus=1-smooth(distance/64)
    return math.floor(y*(1-campus)-467*campus+.5)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    marker_path=WORLD/'.projectseele_tv_world_preview.json'
    marker=json.loads(marker_path.read_text())
    if marker.get('handed_off'): raise RuntimeError('Preview already handed off')
    boxes=[b for _,b in json.loads((OUT/'facility_payload/manifest.json').read_text())['boxes']]
    def protected(p):
        x,y,z=p
        return any(a<=x<=d and b<=y<=e and c<=z<=f for a,b,c,d,e,f in boxes)
    selected=defaultdict(set)
    # The v18 shell bounds are confirmed by source plan + two exact sections.
    for y in range(-466,-293):
        half=math.floor(120*(1-(y+466)/172)+.5)
        next_half=math.floor(120*(1-min(1,(y+467)/172))+.5)
        for z in range(327-half,328+half):
            for x in range(30-half,31+half):
                p=(x,y,z)
                if y != -466 and abs(x-30)<next_half and abs(z-327)<next_half: continue
                if not protected(p): selected[x>>4,z>>4].add(p)
    patch=[]
    for (cx,cz),points in selected.items():
        lo=(cx*16,min(p[1] for p in points),cz*16)
        hi=(cx*16+15,max(p[1] for p in points),cz*16+15)
        source=read_box(SOURCE,DIM,lo,hi)
        current=read_box(WORLD,DIM,lo,hi)
        for p in points:
            after=source.get(p)
            if after is None: raise RuntimeError(f'Unmeasured source {p}')
            if after.split('[')[0] in NATURAL: continue
            before=current.get(p)
            if before==after: continue
            if before is None or before.split('[')[0] not in NATURAL:
                raise RuntimeError(f'Unexpected authored target at {p}: {before}')
            patch.append(dict(pos=p,before=before,after=after,reason='complete-source-pyramid-shell'))
    print('Missing source shell/base cells:',len(patch),flush=True)
    for p,before in iter_box_cells(WORLD,DIM,(-154,-490,32),(224,-467,511)):
        x,y,z=p
        old,new=ground(x,z,False),ground(x,z,True)
        if old==new or y<old-3 or y>new or protected(p): continue
        if before.split('[')[0] not in NATURAL: continue
        after='minecraft:grass_block' if y==new else 'minecraft:dirt' if y>=new-3 else 'minecraft:stone'
        if before.split('[')[0]!=after:
            patch.append(dict(pos=p,before=before,after=after,reason='grade-new-campus-ground'))
    # The retained east service apron was supported by the old high ground.
    # Its measured outer edge needs a structural wall down to the new base;
    # this is outside the TV rooms (x <= 86) and public lift (x <= 137).
    apron=read_box(WORLD,DIM,(138,-466,207),(159,-444,400))
    apron_materials={'minecraft:polished_deepslate','minecraft:light_gray_concrete',
                     'minecraft:chiseled_polished_blackstone'}
    for x in range(138,160):
        for z in range(207,401):
            if apron.get((x,-444,z),'').split('[')[0] not in apron_materials: continue
            for y in range(-466,-444):
                if y!=-466 and x!=159 and z not in (207,400): continue
                p=(x,y,z);before=apron.get(p)
                if before is not None and before.split('[')[0] in AIR:
                    patch.append(dict(pos=p,before=before,after='minecraft:reinforced_deepslate',
                                      reason='east-service-apron-bearing-wall'))
    print('Proposed changes:',len(patch),dict(Counter(p['reason'] for p in patch)),flush=True)
    if not args.apply or not patch: return
    import msvcrt
    lock=(WORLD/'session.lock').open('r+b')
    msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    output=OUT/('pyramid_exterior_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    (output/'region_before').mkdir(parents=True)
    with gzip.open(output/'forward_patch.json.gz','wt',encoding='utf-8') as f: json.dump(patch,f)
    with gzip.open(output/'inverse_patch.json.gz','wt',encoding='utf-8') as f:
        json.dump([{**p,'before':p['after'],'after':p['before']} for p in patch],f)
    regions=defaultdict(lambda:defaultdict(list))
    for p in patch:
        x,y,z=p['pos']
        regions[x>>9,z>>9][x>>4,z>>4].append(Change('tv-pyramid-exterior',x,y,z,
            p['before'],p['after'],'restore',p['reason']))
    written=[]
    try:
        for (rx,rz),chunks in regions.items():
            path=dimension_dir(WORLD,DIM)/f'region/r.{rx}.{rz}.mca'
            backup=output/'region_before'/path.name
            shutil.copy2(path,backup)
            atomic_replace(path,rewrite_region(path,chunks))
            written.append((path,backup))
            for (cx,cz),changes in chunks.items():
                cells=read_box(WORLD,DIM,(cx*16,min(p.y for p in changes),cz*16),
                               (cx*16+15,max(p.y for p in changes),cz*16+15))
                for p in changes:
                    if cells.get((p.x,p.y,p.z))!=p.after: raise RuntimeError(f'Readback failed {p}')
    except Exception:
        for path,backup in written: atomic_replace(path,backup.read_bytes())
        raise
    receipt=dict(cells=len(patch),reasons=dict(Counter(p['reason'] for p in patch)),
                 source=str(SOURCE),verified=True,accepted_tv_rooms_and_lift_cells_changed=0)
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2))
    history=marker.setdefault('exterior_receipts',[])
    if marker.get('exterior_receipt') and marker['exterior_receipt'] not in history:
        history.append(marker['exterior_receipt'])
    history.append(str(output/'receipt.json'))
    marker['exterior_receipt']=str(output/'receipt.json')
    marker_path.write_text(json.dumps(marker,indent=2),encoding='utf-8')
    print('Verified:',output,flush=True)


if __name__=='__main__': main()
