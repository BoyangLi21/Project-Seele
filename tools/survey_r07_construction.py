"""Exact saved-volume survey of the authorized port and remote-base envelopes."""
import json
import numpy as np
from pathlib import Path
from scan_regional_completion import volume,AIR
from regional_voxels import ROOT

OUT=ROOT/'artifacts/world_expansion_r07/survey';OUT.mkdir(parents=True,exist_ok=True)
AREAS={'base':((6288,32,-6736),(6911,223,-5921)),
       'port':((1184,32,288),(1655,143,624)),
       'connection_west':((384,32,256),(975,159,527)),
       'connection_joint':((976,32,384),(1007,159,479)),
       'connection_east':((1008,32,288),(1231,159,528))}
def main():
    reports=[]
    for name,(lo,hi) in AREAS.items():
        file=OUT/(name+'.npz')
        if file.exists():
            data=np.load(file);a=data['blocks'];pal=data['palette'];top=data['top'];water=data['water']
        else:
            a,pal=volume(lo,hi);empty=np.array([s.split('[')[0] in AIR or s.startswith('minecraft:light[') for s in pal])[a]
            occupied=~empty;top=hi[1]-np.argmax(occupied[::-1],axis=0);z,x=np.indices(top.shape);codes=a[top-lo[1],z,x]
            water=np.array([s.startswith('minecraft:water') for s in pal])[codes]
            np.savez_compressed(file,blocks=a,palette=np.array(pal),lo=lo,hi=hi,top=top,water=water)
        row=dict(name=name,bounds=[lo,hi],columns=int(top.size),top_percentiles=np.percentile(top,[0,5,25,50,75,95,100]).tolist(),water_fraction=float(water.mean()),palette=len(pal))
        reports.append(row);print(row,flush=True)
    (OUT/'summary.json').write_text(json.dumps(reports,indent=2))
if __name__=='__main__':main()
