"""Stage isolated R31 UN assets and support profiles; never replace the installed main pack."""
from pathlib import Path
import hashlib,json,shutil
import numpy as np
from scipy.spatial import ConvexHull
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/facility_r31/models';PACK=ROOT/'run/resourcepacks/eva_un_r31_review';DEST=PACK/'assets/projectseele';MAPS=ROOT/'run/projectseele-local-maps'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    body=json.loads((MAPS/'eva_body_r25.json').read_text(encoding='utf8'));dorsal_path=MAPS/'eva_dorsal_r30.json';dorsal=json.loads((dorsal_path if dorsal_path.exists() else ROOT/'src/main/resources/assets/projectseele/motion/eva_dorsal_r13.json').read_text(encoding='utf8'));manifest={'schema':'projectseele.un-models-r30.v1','generation':'R31','models':{}};records=[]
    original_motion=json.dumps(body['motion'],sort_keys=True);original_rigs={k:json.dumps(v,sort_keys=True) for k,v in body.get('rigs',{}).items() if k not in ('3','4')}
    validation=json.loads((ART/'candidate_validation.json').read_text(encoding='utf8'));valid={r['unit']:r for r in validation['models']}
    for unit,name in [('00','eva_prototype'),('01','eva_un01')]:
        source=ART/('un'+unit)/'runtime/assets/projectseele';assert sha(source/'mesh/eva_prototype.mesh.json')==valid[unit]['meshSha256'],'Candidate changed after its structural check';mesh=json.loads((source/'mesh/eva_prototype.mesh.json').read_text(encoding='utf8'));geo=json.loads((source/'geo/eva_prototype.geo.json').read_text(encoding='utf8'));bones=geo['minecraft:geometry'][0]['bones'];by_name={b['name']:b for b in bones};assert len(bones)==len(by_name)
        assert set(body['motion']['bones'])<=set(by_name),'The native pose contract must remain complete'
        triangles=0;support={};carrier_triangles=[]
        for bone,part in mesh['parts'].items():
            values=np.asarray(part['vertices']).reshape(-1,8);assert bone in by_name and len(values)%3==0 and np.isfinite(values).all();triangles+=len(values)//3
            assert np.allclose(np.linalg.norm(values[:,5:8],axis=1),1,atol=2e-4),bone
            assert values[:,3:5].min()>=-1e-5 and values[:,3:5].max()<=1.00001,bone
            hull=(values[:,:3]+part['pivot'])*[-1,1,1]*5/16
            if bone.startswith('r30_thruster_'):
                # Both the 65-degree ground stow and transport's neutral
                # nozzle are real states. Keep their conservative union.
                carrier_triangles.append(hull.reshape(-1,3,3).copy())
                pivot=np.asarray(by_name[bone]['pivot'])*[-1,1,1]*5/16;angle=np.deg2rad(65)
                rotation=np.array([[1,0,0],[0,np.cos(angle),-np.sin(angle)],[0,np.sin(angle),np.cos(angle)]])
                hull=(hull-pivot)@rotation.T+pivot
            carrier_triangles.append(hull.reshape(-1,3,3))
            if bone in mesh.get('jointSkins',{}):
                spec=mesh['jointSkins'][bone];assert set(spec['influences'])<=set(by_name);weights=np.array(list(spec['influences'].values()));assert weights.shape[1]==len(values) and np.isfinite(weights).all() and weights.min()>=-1e-5 and np.allclose(weights.sum(0),1,atol=3e-4),bone
            if bone.startswith(('foot_','shin_','leg_','torso_','pylon_')) or bone=='head':
                points=np.unique(np.round((values[:,:3]+part['pivot'])*[-1,1,1],5),axis=0);support[bone]=points[ConvexHull(points).vertices].tolist()
        assert triangles==mesh['triangleCount']
        for side in ('l','r'):
            for digit in ('index','middle','ring','little'):
                for joint in ('','_tip','_distal'):assert 'finger_'+digit+joint+'_'+side in mesh['parts']
            for joint in ('','_tip'):assert 'finger_thumb'+joint+'_'+side in mesh['parts']
        if unit=='01':assert len(mesh['r30_thrusters'])==2
        geo['minecraft:geometry'][0]['description']['identifier']='geometry.'+name
        for folder in ('mesh','geo','animations','textures/entity','eva'):(DEST/folder).mkdir(parents=True,exist_ok=True)
        (DEST/'mesh'/(name+'.mesh.json')).write_text(json.dumps(mesh,separators=(',',':')),encoding='utf8');(DEST/'geo'/(name+'.geo.json')).write_text(json.dumps(geo,separators=(',',':')),encoding='utf8')
        shutil.copy2(source/'animations/eva_prototype.animation.json',DEST/'animations'/(name+'.animation.json'))
        for suffix in ('','_mr','_s','_n','_eyes'):shutil.copy2(source/'textures/entity'/('eva_prototype'+suffix+'.png'),DEST/'textures/entity'/(name+suffix+'.png'))
        key=str(3+int(unit));body['rigs'][key]=bones;body.setdefault('rig_support',{})[key]=support;body['eye_positions'][key]=mesh['eye_socket_model']
        hulls=[]
        for hull_tri in carrier_triangles:
            for bottom in range(0,62,2):
                selected=hull_tri[(hull_tri[:,:,1].max(1)>=bottom)&(hull_tri[:,:,1].min(1)<bottom+2)]
                if not len(selected):continue
                lo=selected.min((0,1));hi=selected.max((0,1));lo[1]=max(bottom,lo[1]);hi[1]=min(bottom+2,hi[1])
                hulls.append(np.r_[lo,hi].round(6).tolist())
        body.setdefault('carrier_hulls',{})[key]=hulls
        frame=mesh['r13_dorsal_socket'];dorsal['profiles'][name]={k:frame[k] for k in ('centre','outward','hinge','hinge_axis','open_angle_degrees')}
        paths={'mesh':'mesh/'+name+'.mesh.json','geo':'geo/'+name+'.geo.json','animation':'animations/'+name+'.animation.json','texture':'textures/entity/'+name+'.png'}
        manifest['models'][name]={'triangles':triangles,'parts':len(mesh['parts']),'sha256':{k:sha(DEST/p) for k,p in paths.items()},'pbr':{f'textures/entity/{name}{s}.png':sha(DEST/'textures/entity'/(name+s+'.png')) for s in ('_mr','_s','_n','_eyes')},'source_task':mesh['lux3d_task'],'rig_key':int(key),'texture_size':[4096,4096]}
        records.append({'unit':unit,'triangles':triangles,'parts':len(mesh['parts']),'bones':len(bones),'support_hull_points':sum(map(len,support.values())),'hands':mesh['r30_hands'],'eye':mesh['eye_socket_model'],'dorsal':frame})
    (DEST/'eva/un_models_r30.json').write_text(json.dumps(manifest,indent=2),encoding='utf8');(PACK/'pack.mcmeta').write_text(json.dumps({'pack':{'pack_format':15,'description':'EVA UN R31 — corrected shoulder/hip ownership and mechanical armour details'}},ensure_ascii=False),encoding='utf8')
    (MAPS/'eva_body_r31_review.json').write_text(json.dumps(body,separators=(',',':')),encoding='utf8');(MAPS/'eva_dorsal_r31_review.json').write_text(json.dumps(dorsal,indent=2),encoding='utf8')
    assert json.dumps(body['motion'],sort_keys=True)==original_motion
    assert all(json.dumps(body['rigs'][k],sort_keys=True)==v for k,v in original_rigs.items()),'NERV rig must remain exact'
    (ART/'staging.json').write_text(json.dumps({'status':'R31 review only; original model pack preserved','pack':str(PACK),'body':str(MAPS/'eva_body_r31_review.json'),'dorsal':str(MAPS/'eva_dorsal_r31_review.json'),'body_sha256':sha(MAPS/'eva_body_r31_review.json'),'dorsal_sha256':sha(MAPS/'eva_dorsal_r31_review.json'),'main_unchanged':True,'nerv_motion_and_rigs_unchanged':True,'normalization_required':False,'models':records},indent=2),encoding='utf8');print(json.dumps([{k:v for k,v in r.items() if k not in ('hands','dorsal')} for r in records],indent=2))
if __name__=='__main__':main()
