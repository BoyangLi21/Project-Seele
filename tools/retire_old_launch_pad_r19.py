"""Retire the bare, unconnected west pad left outside the old plant's move box."""
import argparse,json
import regional_voxels as vox
from query_blocks import read_box,iter_block_entities

def main(apply=False):
    vox.OUT=vox.ROOT/'artifacts/world_repair_r19/global_cleanup';p=vox.Painter();lo=(-64,-444,207);hi=(-51,-444,214)
    b=read_box(vox.WORLD,vox.DIM,lo,hi);assert len(b)==112 and set(b.values())=={'minecraft:polished_deepslate'}
    assert not list(iter_block_entities(vox.WORLD,vox.DIM,lo,hi))
    # Current personnel routes and registered staff have no use of this pad.
    # It lies west of the old relocation BOXES minimum X=-46; its Z still
    # matches the retired launch plant, whose operational payload moved -256.
    for c in json.loads((vox.WORLD/'quality_walk_cases.json').read_text()):
        path=c.get('path',[c.get('start'),c.get('end')])
        for a,z in zip(path,path[1:]):
            if abs(a[1]+443)>.2 or abs(z[1]+443)>.2:continue
            if max(a[0],z[0])>=-64.3 and min(a[0],z[0])<=-49.7 and max(a[2],z[2])>=206.7 and min(a[2],z[2])<=215.3:raise RuntimeError(('Possible pad route',c['id']))
    for pos,state in b.items():p.match((*pos,*pos),state,'minecraft:air','r19/retire_stranded_old_launch_pad')
    p.meta.update(reason='Isolated 14x8 slab outside old relocation western boundary; no actor, staff, block entity or current route',old_plant_delta=[0,0,-256],bounds=[lo,hi])
    p.apply('old_west_launch_pad') if apply else p.save_plan('old_west_launch_pad')

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--apply',action='store_true');main(a.parse_args().apply)
