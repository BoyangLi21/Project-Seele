"""Encode measured/source material channels as LabPBR data, retaining albedo UVs."""
from pathlib import Path
import json,hashlib,shutil,numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele/textures/entity';OUT=ROOT/'artifacts/combat_beast_r37/materials'
def main():
    global SRC
    original=ROOT/'artifacts/combat_beast_r37/materials_source/assets/projectseele'
    if not (original/'eva/un_models_r30.json').is_file():
        for name in ['eva_unit00','eva_unit01','eva_unit02','eva_prototype','eva_un01']:
            for suffix in ['', '_n','_s','_mr','_eyes']:
                p=SRC/(name+suffix+'.png')
                if p.is_file():
                    target=original/'textures/entity'/p.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
        manifest=original/'eva/un_models_r30.json';manifest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(SRC.parent.parent/'eva/un_models_r30.json',manifest)
    SRC=original/'textures/entity'
    target=OUT/'assets/projectseele/textures/entity';target.mkdir(parents=True,exist_ok=True);rows=[]
    for name in ['eva_unit00','eva_unit01','eva_unit02','eva_prototype','eva_un01']:
        p=SRC/(name+'.png');a=np.asarray(Image.open(p).convert('RGBA'));rgb=a[:,:,:3].astype(np.float32)/255;value=rgb.max(2);chroma=value-rgb.min(2);lum=rgb@np.array([.2126,.7152,.0722],np.float32)
        mr=SRC/(name+'_mr.png')
        if mr.exists():
            values=np.asarray(Image.open(mr));rough=np.clip(values[:,:,1].astype(np.float32)/255,.18,.65);metal=values[:,:,2]>160
        else:
            rough=np.full(value.shape,.30,np.float32);rough[value<.17]=.61;rough[chroma>.30]=.25
            metal=(chroma<.10)&(value>.30)&(value<.72)
        spec=np.zeros((*value.shape,4),np.uint8);spec[:,:,0]=np.rint((1-np.sqrt(rough))*255);spec[:,:,1]=13;spec[:,:,1][metal]=230;spec[:,:,3]=255
        if name=='eva_prototype':
            gold=metal&(rgb[:,:,0]>rgb[:,:,1]*1.08)&(rgb[:,:,1]>rgb[:,:,2]*1.25);spec[:,:,1][gold]=231
        prior=SRC/(name+'_n.png')
        if prior.exists():normal=np.array(Image.open(prior).convert('RGBA'))
        else:
            # Very shallow seam relief; painted markings never become large
            # displacement. Blue stores AO, alpha stores height, not opacity.
            broad=gaussian_filter(lum,1.2);dy,dx=np.gradient(broad);nx=np.clip(-dx*.28,-.12,.12);ny=np.clip(dy*.28,-.12,.12)
            normal=np.zeros_like(a);normal[:,:,0]=np.rint((nx*.5+.5)*255);normal[:,:,1]=np.rint((ny*.5+.5)*255);normal[:,:,2]=255;normal[:,:,3]=255
        spec[a[:,:,3]==0]=[0,10,0,255];normal[a[:,:,3]==0]=[128,128,255,255]
        for suffix,data in [('s',spec),('n',normal)]:Image.fromarray(data).save(target/(name+'_'+suffix+'.png'))
        rows.append(dict(model=name,dimensions=[a.shape[1],a.shape[0]],albedo_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),source_mr=mr.exists(),preserved_existing_normal=prior.exists()))
        print('LabPBR',name,flush=True)
    declaration=OUT/'assets/minecraft/optifine/texture.properties';declaration.parent.mkdir(parents=True,exist_ok=True);declaration.write_text('format=lab-pbr/1.3\n')
    marker=OUT/'assets/projectseele/eva/materials_r37.json';marker.parent.mkdir(exist_ok=True);marker.write_text(json.dumps(dict(version=37,format='lab-pbr/1.3',models=rows),indent=2))
    # Existing UN models use hash-bound material manifests. Keep their mesh
    # identity and update only the material files produced by this pass.
    prior_manifest=SRC.parent.parent/'eva/un_models_r30.json'
    manifest=json.loads(prior_manifest.read_text())
    for model in manifest['models'].values():
        for relative in model['pbr']:
            candidate=OUT/'assets/projectseele'/relative
            if candidate.is_file():model['pbr'][relative]=hashlib.sha256(candidate.read_bytes()).hexdigest()
    (marker.parent/'un_models_r30.json').write_text(json.dumps(manifest,indent=2))
if __name__=='__main__':main()
