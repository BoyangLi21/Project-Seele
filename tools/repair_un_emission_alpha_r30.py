"""Encode a true cutout mask for the generated powered optical/nozzle layer."""
import bpy,numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for unit in ('00','01'):
    p=ROOT/'artifacts/facility_r30/models'/('un'+unit)/'runtime/assets/projectseele/textures/entity/eva_prototype_eyes.png';image=bpy.data.images.load(str(p));values=np.empty(len(image.pixels),np.float32);image.pixels.foreach_get(values);values=values.reshape(-1,4);mask=np.max(values[:,:3],axis=1)>.00001;values[:,3]=mask.astype(np.float32);image.pixels.foreach_set(values.ravel());image.update();image.filepath_raw=str(p);image.file_format='PNG';image.save();print(unit,'emissive coverage',float(mask.mean()),flush=True);bpy.data.images.remove(image)
