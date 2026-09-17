"""Restore measured edges where the old railway crossed a later extension road."""
import json
import numpy as np
import regional_voxels as v
from query_blocks import read_box,AIR
OUT=v.ROOT/'artifacts/world_rebuild_r20/road_actual';REVIEW=v.ROOT/'run/saves/SEELE_R20_REVIEW'
def main():
    report=json.loads((OUT/'extension_actual.json').read_text());v.OUT=OUT;p=v.Painter()
    with np.load(OUT/'extension_contract_final.npz') as f:a={k:f[k] for k in f.files}
    ox,oz=map(int,a['origin'])
    for row in report['bad']:
        x,y,z=row['pos'];ix,iz=x-ox,z-oz;h=int(a['height2'][iz,ix]);kind=2 if a.get('stripe',np.zeros_like(a['mask']))[iz,ix] else 1 if a.get('carriage',a['mask'])[iz,ix] else 0
        surface=['minecraft:smooth_stone','minecraft:black_concrete','minecraft:white_concrete'][kind]
        if h%2:surface=['minecraft:smooth_stone_slab','projectseele:road_asphalt_slab','projectseele:road_marking_slab'][kind]+'[type=bottom,waterlogged=false]'
        before=read_box(REVIEW,v.DIM,(x,y-3,z),(x,y,z))
        assert before[x,y,z].split('[')[0] in AIR,('Review road changed',row)
        for yy in range(y-3,y+1):
            q=(x,yy,z);p.match((*q,*q),before[q],surface if yy==y else 'minecraft:stone','r20/extension_road_formation')
    p.meta.update(restored_columns=len(report['bad']),measured_contract='extension_contract_final.npz',unchanged_route=True);p.save_plan('restore_extension_formation')
if __name__=='__main__':main()
