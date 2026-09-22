"""Current grading profiles with actual world readback at the airport seam."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from query_blocks import read_box

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/facility_r30/city_edge_grading'
rows=[('nerv_airport_edge','x',733,'NERV airport north edge'),('hakone_east_edge','x',-1050,'Hakone east station landscape'),('tokyo_west_edge','z',300,'Tokyo west boundary')]
fig,axes=plt.subplots(3,1,figsize=(13,9),layout='constrained')
for ax,(name,axis,value,title) in zip(axes,rows):
    d=np.load(OUT/(name+'.npz'));lo=d['lo'];g=d['before'];a=d['after']
    if axis=='x':index=value-int(lo[0]);coordinates=np.arange(g.shape[0])+lo[2];old,new=g[:,index],a[:,index]
    else:index=value-int(lo[2]);coordinates=np.arange(g.shape[1])+lo[0];old,new=g[index],a[index]
    ax.plot(coordinates,old,color='#bd7838',label='Before');ax.plot(coordinates,new,color='#22785c',label='Installed grading')
    ax.set_title(f'{title}: {axis.upper()}={value}');ax.set_xlabel('Z' if axis=='x' else 'X');ax.set_ylabel('Y (blocks)');ax.grid(alpha=.17);ax.legend()
axes[0].set_xlim(-250,-150)
fig.savefig(OUT/'grade_sections.png',dpi=130)
world=ROOT/'run/saves/SEELE_R30_WORLD';cells=read_box(world,'projectseele:geofront',(733,32,-230),(733,120,-195))
soil={'minecraft:grass_block','minecraft:dirt','minecraft:stone','minecraft:sand','minecraft:gravel','minecraft:clay','minecraft:coarse_dirt','minecraft:podzol'}
d=np.load(OUT/'nerv_airport_edge.npz');lo=d['lo'];checks=[]
for z in range(-230,-194):
    row=z-int(lo[2]);col=733-int(lo[0]);target=int(d['after'][row,col]);actual=max(y for y in range(32,121) if cells[733,y,z].split('[')[0] in soil)
    checks.append({'x':733,'z':z,'target':target,'actual_ground':actual,'changed':bool(d['active'][row,col])})
assert all(c['actual_ground']==c['target'] for c in checks if c['changed'])
(OUT/'airport_seam_native_voxel_readback.json').write_text(json.dumps(checks,indent=2));print('Airport grading readback',sum(c['changed'] for c in checks),'changed columns passed')
