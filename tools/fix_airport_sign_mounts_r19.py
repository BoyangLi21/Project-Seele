"""Replace incomplete single-chain airport hangers with paired ceiling rods."""
import argparse,json
import regional_voxels as vox
from query_blocks import AIR,read_box

def main(apply=False):
    vox.OUT=vox.ROOT/'artifacts/world_repair_r19/sign_mounts';p=vox.Painter();rows=json.loads((vox.OUT.parent/'global_components/contact_classification.json').read_text())['groups'];boards=[]
    for r in rows:
        if r['kind']!='isolated_structure' or r['lo'][1]!=88 or r['hi'][1]!=97 or r['lo'][2] not in (-386,1064):continue
        if not set(s.split('[')[0] for s in r['states'])<={'minecraft:black_concrete','minecraft:chain'}:continue
        lo,hi=r['lo'],r['hi'];z=lo[2];blocks=read_box(vox.WORLD,vox.DIM,tuple(lo),(hi[0],110,z));black=[q for q,s in blocks.items() if s=='minecraft:black_concrete'];top=max(q[1] for q in black)
        mounts=[]
        for x in (lo[0]+3,hi[0]-3):
            roof=next((y for y in range(top+1,111) if blocks[x,y,z].split('[')[0] not in AIR|{'minecraft:chain'}),None)
            if roof is None or blocks[x,roof,z] not in ('minecraft:light_gray_concrete','minecraft:white_concrete','minecraft:iron_block','projectseele:nerv_structural_panel'):raise RuntimeError(('No verified structural roof',x,z,roof))
            for y in range(top+1,roof):
                before=blocks[x,y,z]
                if before.split('[')[0] not in AIR|{'minecraft:chain'}:raise RuntimeError(('Hanger obstruction',x,y,z,before))
                p.match((x,y,z,x,y,z),before,'minecraft:iron_bars[east=false,north=false,south=false,waterlogged=false,west=false]','r19/paired_airport_sign_hangers')
            mounts.append([x,top+1,z,x,roof,z])
        for q,s in blocks.items():
            if s.startswith('minecraft:chain['):p.match((*q,*q),s,'minecraft:air','r19/retire_short_single_chain')
        boards.append(dict(bounds=[lo,hi],mounts=mounts))
    assert len(boards)==6
    p.meta.update(boards=boards,sign_positions_unchanged=True,ceiling_contact_verified=True,port_crane_hooks_untouched=True)
    p.apply('airport_hanging_boards') if apply else p.save_plan('airport_hanging_boards')

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--apply',action='store_true');main(a.parse_args().apply)
