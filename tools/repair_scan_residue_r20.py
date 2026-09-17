"""Resolve verified isolated soil, vegetation and obsolete railway/factory parts."""
import json,math,gzip
from pathlib import Path
from collections import Counter
import numpy as np
from scipy.ndimage import label,generate_binary_structure
from scipy.spatial import cKDTree
import regional_voxels as vox
from query_blocks import read_box,AIR
from scan_world_components_r19 import WATER

ROOT=vox.ROOT;OUT=ROOT/'artifacts/world_rebuild_r20/global_cleanup';SCAN=OUT.parent/'global_components';REVIEW=ROOT/'run/saves/SEELE_R20_REVIEW'
def cells(row):
    lo,hi=row['lo'],row['hi'];b=read_box(REVIEW,vox.DIM,lo,hi);shape=(hi[1]-lo[1]+1,hi[2]-lo[2]+1,hi[0]-lo[0]+1);coords=[(x,y,z) for y in range(lo[1],hi[1]+1) for z in range(lo[2],hi[2]+1) for x in range(lo[0],hi[0]+1)];a=np.array([b[p].split('[')[0] not in AIR|WATER|{'minecraft:light'} for p in coords]).reshape(shape);groups,_=label(a,generate_binary_structure(3,1));x,y,z=np.asarray(row['seed'])-lo;code=groups[y,z,x];ids=np.flatnonzero(groups.ravel()==code);assert code and len(ids)==row['cells'];return {coords[int(i)]:b[coords[int(i)]] for i in ids}
def main():
    OUT.mkdir(exist_ok=True);vox.OUT=OUT;p=vox.Painter();raw=json.loads((SCAN/'report.json').read_text())['candidates'];groups=json.loads((SCAN/'contact_classification.json').read_text())['groups']
    before=json.loads((OUT.parent/'transit/native_snapshot.json').read_text(encoding='utf8'));after=json.loads((OUT.parent/'transit/built7/native_commission.json').read_text(encoding='utf8'));old=np.asarray([q for r in before['curves'] if r['mode']=='TRAIN' for q in r['points']]);new=np.asarray([q for r in after['curves'] if r['mode']=='TRAIN' for q in r['points']]);oldtree=cKDTree(old[:,[0,2]]);newtree=cKDTree(new[:,[0,2]])
    obsolete={'minecraft:gray_concrete','minecraft:light_gray_concrete','minecraft:iron_block','minecraft:iron_bars','minecraft:polished_basalt','minecraft:polished_deepslate','minecraft:gray_stained_glass','minecraft:smooth_stone','minecraft:polished_blackstone_slab','minecraft:chain','minecraft:black_concrete'}
    removed=[];retained=[];selected={}
    for g in groups:
        reason=None
        if g['kind'] in ('isolated_soil','isolated_vegetation'):reason='Detached from all 26 neighbouring cells; no terrain, fluid or tree support'
        elif g['kind']=='isolated_structure':
            lo,hi=g['lo'],g['hi'];names={s.split('[')[0] for s in g['states']}
            if lo==[-46,-443,-142] and hi==[-37,-353,-56]:reason='Retired original west factory facade left beyond the old copy boundary'
            elif 20<=lo[0]<=hi[0]<=48 and -425<=lo[1]<=hi[1]<=-410 and -10<=lo[2]<=hi[2]<=-8:reason='Remaining fragments of the explicitly retired lower observation connector'
            elif names<=obsolete and lo[1]>=32:
                points=np.asarray([raw[i]['seed'] for i in g['components']]);dist,idx=oldtree.query(points[:,[0,2]]+.5);_,j=newtree.query(points[:,[0,2]]+.5)
                if np.max(dist)<10 and hi[1]<=float(new[j,1].min())-3.5 and hi[1]<=float(old[idx,1].max())+13:reason='Disconnected legacy catenary/railing/pier beneath the raised native railway'
            if reason is None and names<=obsolete:
                for station in before['platforms']:
                    if station['transportMode']!='TRAIN':continue
                    a=station['position1'];b=station['position2'];horizontal=a['z']==b['z'];cx=(a['x']+b['x'])/2;cz=(a['z']+b['z'])/2;half=(abs(a['x']-b['x'])+abs(a['z']-b['z']))/2+12
                    xmin,xmax,zmin,zmax=(cx-half,cx+half,cz-21,cz+21) if horizontal else (cx-21,cx+21,cz-half,cz+half)
                    if xmin<=lo[0]<=hi[0]<=xmax and zmin<=lo[2]<=hi[2]<=zmax and a['y']+1<=lo[1]<=hi[1]<=a['y']+15:
                        reason='Detached exterior trim or old transfer bridge of a completely rebuilt station';break
            if reason is None and names=={'minecraft:polished_deepslate'} and ((220<=lo[0]<=hi[0]<=242 and -35<=lo[2]<=hi[2]<=-20) or (305<=lo[0]<=hi[0]<=316 and 660<=lo[2]<=hi[2]<=675)) and 77<=lo[1]<=hi[1]<=79:
                reason='Small unsupported remnants of old surface retaining/paving posts'
            if reason is None and names=={'minecraft:lantern','minecraft:iron_bars','minecraft:polished_blackstone_slab'} and g['cells']==4:
                reason='Unattached old station lantern bracket; rebuilt platform now has continuous fitted strip lighting'
            if reason is None and g['cells']==1 and any(n.endswith('_wall_sign') for n in names):
                reason='Obsolete unsupported station label; replacement Chinese signs and live departure boards are installed'
            if reason is None:retained.append(g);continue
        if reason:
            current={}
            for i in g['components']:current.update(cells(raw[i]))
            assert len(current)==g['cells'];selected.update(current);removed.append(dict(kind=g['kind'],cells=len(current),lo=g['lo'],hi=g['hi'],reason=reason))
    # The current new-route catalogue must not depend on any retired fragment.
    cases=json.loads((REVIEW/'quality_walk_cases.json').read_text());violations=[]
    for c in cases:
        route=c.get('path',[c.get('start'),c.get('end')])
        for a,b in zip(route,route[1:]):
            a=np.array(a,float);b=np.array(b,float);n=max(1,int(np.linalg.norm(b-a)*3))
            for q in np.linspace(a,b,n+1):
                for dx,dz in ((0,0),(-.29,0),(.29,0),(0,-.29),(0,.29)):
                    pos=(math.floor(q[0]+dx),math.floor(q[1]-.05),math.floor(q[2]+dz))
                    if pos in selected:violations.append(dict(route=c['id'],pos=pos))
    assert not violations,violations[:10]
    for q,state in sorted(selected.items()):p.match((*q,*q),state,'minecraft:air','r20/verified_old_component')
    p.meta.update(removed=removed,removed_cells=len(selected),remaining_isolated_structures=retained,retained_reason='Original displays, modeled crane attachments and parts requiring a targeted support/role check',new_route_floor_intersections=0,full_scan_chunks=36360,full_scan_regions=126)
    p.save_plan('verified_residue');print('Verified residues',len(selected),'cells',Counter(r['kind'] for r in removed),'remaining structures',len(retained),flush=True)
if __name__=='__main__':main()
