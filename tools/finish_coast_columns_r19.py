"""Finish three proven natural shore columns previously held by flower names."""
import argparse,json
import regional_voxels as vox
from query_blocks import read_box,AIR
from repair_coast_seams_r19 import GROUND,PLANTS,SEA

def main(apply=False):
    vox.OUT=vox.ROOT/'artifacts/world_repair_r19/coast_final';p=vox.Painter();rows=json.loads((vox.OUT/'sea_level_connections/places.json').read_text())['held_columns']
    assert len(rows)==3 and all(r['states']==['minecraft:azure_bluet'] for r in rows)
    for row in rows:
        x,z=row['x'],row['z'];b=read_box(vox.WORLD,vox.DIM,(x,0,z),(x,SEA,z));allowed=GROUND|PLANTS|AIR|{'minecraft:water','minecraft:azure_bluet'}
        assert all(s.split('[')[0] in allowed for s in b.values())
        floor=max(q[1] for q,s in b.items() if s.split('[')[0] in GROUND)
        for q,s in b.items():
            if q[1]>floor and s.split('[')[0]!='minecraft:water':p.match((*q,*q),s,'minecraft:water[level=0]','r19/flower_held_natural_shore_column')
            elif q[1]==floor and s.split('[')[0]=='minecraft:grass_block':p.match((*q,*q),s,'minecraft:sand','r19/submerged_natural_shore_bed')
    p.meta.update(columns=rows,remaining_unresolved_natural_columns=0)
    p.apply('flower_held_shore_columns') if apply else p.save_plan('flower_held_shore_columns')

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--apply',action='store_true');main(a.parse_args().apply)
