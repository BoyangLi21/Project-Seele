"""Fit the current UN docking mechanism to the private R19 body candidate."""
import json,shutil
from pathlib import Path
import numpy as np
import build_dorsal_tv_r13 as dorsal

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_repair_r19/un00_local';BODY=OUT/'assets/projectseele';TARGET=OUT/'runtime_candidate/assets/projectseele'

def main():
    installed=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele'
    old=json.loads((installed/'mesh/eva_prototype.mesh.json').read_text());frame=old['r13_dorsal_socket']
    for category in ('geo','mesh','animations','textures/entity'):(TARGET/category).mkdir(parents=True,exist_ok=True)
    for relative in ('animations/eva_prototype.animation.json','textures/entity/eva_prototype.png','textures/entity/eva_prototype_eyes.png'):shutil.copy2(BODY/relative,TARGET/relative)
    dorsal.main(models=['eva_prototype'],source_root=BODY,target_root=TARGET,frame_overrides={'eva_prototype':frame},manifest_path=OUT/'runtime_dorsal_manifest.json')
    mesh=json.loads((TARGET/'mesh/eva_prototype.mesh.json').read_text());geo=json.loads((TARGET/'geo/eva_prototype.geo.json').read_text());bones={b['name']:b for b in geo['minecraft:geometry'][0]['bones']}
    for key in ('centre','outward','hinge','hinge_axis'):assert np.allclose(mesh['r13_dorsal_socket'][key],frame[key],atol=1e-5),key
    for name,part in mesh['parts'].items():
        a=np.asarray(part['vertices']);assert a.size%24==0 and np.isfinite(a).all();assert np.allclose(part['pivot'],bones[name]['pivot'],atol=1e-5)
    report={'stage':'PRIVATE RUNTIME CANDIDATE - not installed','triangles':mesh['triangleCount'],'parts':len(mesh['parts']),'bones':len(bones),'docking_frame_unchanged':True,'eye_socket_model':mesh['eye_socket_model'],'candidate':str(TARGET)}
    (OUT/'runtime_candidate_report.json').write_text(json.dumps(report,indent=2));print(report)

if __name__=='__main__':main()
