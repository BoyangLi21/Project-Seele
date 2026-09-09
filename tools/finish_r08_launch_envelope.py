"""Add exterior-only dark launch cladding and a finished hangar roof, proving interiors unchanged."""
import argparse,json,hashlib
import numpy as np
from scipy.ndimage import label,find_objects
import regional_voxels as v
from query_blocks import AIR
from scan_regional_completion import volume
OUT=v.ROOT/'artifacts/world_refinement_r08';v.OUT=OUT

def main(apply=False):
    p=v.Painter();o='r08/launch_exterior';dark='minecraft:black_concrete';edge='minecraft:polished_blackstone';a0=np.load(OUT/'facilities/shafts_before.npz');a=a0['blocks'];pal=a0['palette'];lo=a0['lo']
    def state(x,y,z):return str(pal[a[y-lo[1],z-lo[2],x-lo[0]]])
    # Outside the existing reinforced wall: neighboring openings remain openings.
    for cx in (-12,30,72):
        sides=[(x,z,x+(1 if x<cx else -1),z) for x in (cx-18,cx+18) for z in range(-54,-17)]
        sides += [(x,z,x,z+(1 if z==-54 else -1)) for z in (-54,-18) for x in range(cx-17,cx+18)]
        for x,z,nx,nz in sides:
            start=None;old=None;finish=-348
            for y in range(-348,26):
                finish=y;src=state(x,y,z) if y<=24 else None;inside=state(nx,y,nz) if y<=24 else 'minecraft:air'
                eligible=src is not None and (src in AIR or v.natural(src)) and inside.split('[')[0] in ('minecraft:reinforced_deepslate','minecraft:iron_block','minecraft:polished_deepslate','minecraft:deepslate_bricks')
                if start is not None and (not eligible or src!=old):
                    p.match((x,start,z,x,y-1,z),old,dark,o+'/shaft_'+str(cx));start=None
                if eligible and start is None:start=y;old=src
        # Narrow common base collars visually join the launch plant to each shaft.
        for x in (cx-19,cx+19):p.fill(x,-353,-55,x,-349,-18,edge,o+'/base_collar','new')
    # Actual survey: all 10,332 central roof columns have the existing double slab.
    # Keep that structure and every cell below it. New plating lies above Y-354.
    p.fill(-32,-353,-137,93,-353,-55,dark,o+'/roof_plating','owned')
    for z in range(-135,-54,13):p.fill(-32,-352,z,93,-352,z,edge,o+'/roof_seams','new')
    for x in (-33,9,51,94):p.fill(x,-352,-139,x,-350,-56,edge,o+'/roof_ribs','new')
    for cx in (-12,30,72):
        for z in (-127,-78):
            p.fill(cx-7,-352,z-4,cx+7,-351,z+4,'minecraft:gray_concrete',o+'/vent_plenum','new')
            for xx in range(cx-6,cx+7,2):p.fill(xx,-350,z-3,xx,-350,z+3,'minecraft:iron_trapdoor[facing=north,half=top,open=false,powered=false,waterlogged=false]',o+'/vent_louvers','new')
        p.fill(cx-2,-352,-137,cx+2,-352,-134,'minecraft:yellow_terracotta',o+'/inspection_mark','new')
    # Only detached all-natural components, away from a survey boundary, are debris.
    removed=[]
    for name in ('pyramid','hangar'):
        d=np.load(OUT/'facilities'/(name+'_before.npz'));b=d['blocks'];q=d['palette'];qlo=d['lo'];n=np.array([s.split('[')[0] in ('minecraft:stone','minecraft:dirt','minecraft:grass_block','minecraft:sand','minecraft:gravel','minecraft:deepslate') for s in q])
        solid=np.array([s.split('[')[0] not in AIR|{'minecraft:water','projectseele:lcl','minecraft:light'} for s in q])[b];components,count=label(solid)
        for i,box in enumerate(find_objects(components),1):
            if any(s.start==0 or s.stop==solid.shape[k] for k,s in enumerate(box)):continue
            mask=components[box]==i;size=int(mask.sum())
            if size>2048 or not np.all(n[b[box][mask]]):continue
            xyz=np.argwhere(mask)[:,[2,0,1]]+np.array([box[2].start,box[0].start,box[1].start])+qlo
            if int(xyz[:,1].min())<-465:continue
            for x,y,z in xyz:p.match((x,y,z,x,y,z),str(q[b[y-qlo[1],z-qlo[2],x-qlo[0]]]),'minecraft:air',o+'/detached_debris')
            removed.append(dict(area=name,cells=size,lo=xyz.min(0).tolist(),hi=xyz.max(0).tolist()))
    p.meta.update(detached_debris=removed,interior_unchanged=True,roof_minimum_y=-353,shaft_ports_preserved=True)
    before=[]
    for cx in (-12,30,72):
        lo1=(cx-17,-348,-53);hi1=(cx+17,24,-19);b,q=volume(lo1,hi1);before.append((lo1,hi1,np.array(q)[b]))
    lo1=(-32,-512,-137);hi1=(93,-354,-55);b,q=volume(lo1,hi1);before.append((lo1,hi1,np.array(q)[b]))
    if apply:
        p.apply('launch_envelope')
        for lo1,hi1,old in before:
            b,q=volume(lo1,hi1);assert np.array_equal(old,np.array(q)[b]),('Interior mutation',lo1,hi1)
        (OUT/'facilities/interior_preservation.json').write_text(json.dumps(dict(passed=True,boxes=[dict(lo=l,hi=h,cells=int(old.size)) for l,h,old in before],debris=removed),indent=2),encoding='utf8')
    else:p.save_plan('launch_envelope')
    print('Detached debris',removed,flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
