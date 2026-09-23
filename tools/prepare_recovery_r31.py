"""Trim the recorded get-up, replace source root bob with measured contact, and publish an isolated recovery profile."""
from pathlib import Path
import hashlib,json,gc
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/facility_r31/recovery';OUT.mkdir(parents=True,exist_ok=True)
body=json.loads((ROOT/'run/projectseele-local-maps/eva_body_r31_review.json').read_text());names=body['motion']['bones'];records={};reports=[]
def decode(rig,frame):
    q={n:Rotation.from_euler('xyz',np.asarray(b.get('rotation',b.get('bindRotationDegrees',[0,0,0])))*[-1,-1,1],degrees=True) if '_axis_' in n else Rotation.identity() for n,b in rig.items()};p={n:np.zeros(3) for n in rig}
    for n,r in zip(names,frame['rotation_wxyz']):q[n]=Rotation.from_quat([-r[1],-r[2],r[3],r[0]])
    for n,v in frame.get('bone_position_xyz',{}).items():p[n]=np.asarray(v)*[-1,1,1]/16
    p['root']=np.asarray(frame['root_m'])*[-1,1,1]*7
    return q,p
def matrices(rig,q,p):
    cache={}
    def make(n):
        if n not in cache:
            b=rig[n];pivot=np.asarray(b['pivot'])*[-1,1,1]/16;r=q[n].as_matrix();local=np.eye(4);local[:3,:3]=r;local[:3,3]=p[n]+pivot-r@pivot;cache[n]=make(b['parent'])@local if b.get('parent') else local
        return cache[n]
    for n in rig:make(n)
    return cache
def support_floor(points,mats):
    low=1e9;contact=''
    for n,v in points.items():
        if n not in mats:continue
        m=mats[n];floor=float((v@m[1,:3]+m[1,3]).min())
        if floor<low:low=floor;contact=n
    return low,contact
for key in ('0','1','2','3','4'):
    unit=int(key);name=('eva_unit00','eva_unit01','eva_unit02','eva_prototype','eva_un01')[unit]
    source=(ROOT/'run/resourcepacks/eva_real_model/assets/projectseele' if unit<3 else ROOT/'artifacts/facility_r31/models'/('un00' if unit==3 else 'un01')/'runtime/assets/projectseele')/'mesh'/((name if unit<3 else 'eva_prototype')+'.mesh.json')
    mesh=json.loads(source.read_text());rig={b['name']:b for b in body['rigs'][key]};support={}
    for bone,part in mesh['parts'].items():
        if bone not in rig or bone in mesh.get('jointSkins',{}) or bone in ('cannon','knife','shield','lance','n2'):continue
        a=np.asarray(part['vertices']).reshape(-1,8);v=np.unique(np.round((a[:,:3]+part['pivot'])*[-1,1,1]/16,7),axis=0)
        if len(v)>4:
            try:v=v[ConvexHull(v).vertices]
            except Exception:pass
        support[bone]=v
    capture_path=ROOT/'run/projectseele-local-maps'/('eva_combat_capture_r31'+('_un00' if unit==3 else '_un01' if unit==4 else '')+'.json');capture=json.loads(capture_path.read_text());assert capture['bones']==names
    # The first four seconds contain a prolonged low support/repositioning
    # section; the final attempt has one coherent hand-to-foot-to-hip rise.
    frames=capture['clips']['r31_get_up']['frames'][240:369]
    foot=support['foot_l'];sole=foot[foot[:,1]<=foot[:,1].min()+.04].mean(0)
    iq,ip=decode(rig,body['motion']['clips']['idle']['frames'][0]);im=matrices(rig,iq,ip);idle_floor,_=support_floor(support,im);anchor=(im['foot_l']@np.r_[sole,1])[:3];anchor[1]-=idle_floor
    output=[];floors=[];hand_clear=[];contacts=[];root_heights=[];feet=[]
    for index,frame in enumerate(frames):
        q,p=decode(rig,frame);p['root'][:]=0;mat=matrices(rig,q,p);at=(mat['foot_l']@np.r_[sole,1])[:3]
        p['root'][[0,2]]=anchor[[0,2]]-at[[0,2]];mat=matrices(rig,q,p);floor,contact=support_floor(support,mat);p['root'][1]-=floor;mat=matrices(rig,q,p)
        low,_=support_floor(support,mat);floors.append(low*5);contacts.append(contact);root_heights.append(float(p['root'][1]*5));feet.append(((mat['foot_l']@np.r_[sole,1])[:3]*5).tolist())
        hands=[float((support[n]@mat[n][1,:3]+mat[n][1,3]).min())*5 for n in ('hand_l','hand_r') if n in support];hand_clear.append(min(hands))
        output.append({'rotation_xyzw':[np.round(q[n].as_quat(),8).tolist() for n in names],'positions':[np.round(p[n],8).tolist() for n in names]})
    assert min(floors)>-1e-5 and min(hand_clear)>-1e-5
    slip=float(np.linalg.norm(np.diff(np.asarray(feet)[:,[0,2]],axis=0),axis=1).max())
    assert slip<1e-5
    records[key]={'frames':output,'support':{n:np.round(v,7).tolist() for n,v in support.items()},'sole_l':np.round(sole,8).tolist(),'anchor':np.round(anchor,8).tolist(),'source_sha256':hashlib.sha256(capture_path.read_bytes()).hexdigest(),'rig_sha256':hashlib.sha256(json.dumps(body['rigs'][key],sort_keys=True).encode()).hexdigest()}
    reports.append({'rig':key,'model':name,'sourceFrames':[240,368],'sampleCount':len(output),'sourceDurationSeconds':128/60,'supportPoints':sum(map(len,support.values())),'minimumHullFloorBlocks':min(floors),'minimumPalmHullFloorBlocks':min(hand_clear),'maximumLockedFootXZDeltaBlocks':slip,'requiredRootYBlocks':[min(root_heights),max(root_heights)],'contactAtKeyFrames':[{'sourceFrame':240+i,'part':contacts[i]} for i in (0,24,48,72,96,128)]})
    print(json.dumps(reports[-1]),flush=True);del mesh,support;gc.collect()
result={'schema':'projectseele.recovery-r31.v1','bones':names,'sourceClip':'r31_get_up','sourceFrames':[240,368],'sourceDurationSeconds':128/60,'stages':['fallen','right-hand brace','left-foot plant','hip drive','settle'],'rootPolicy':'Raw source root_m is discarded; full rigid body/palm/foot support replaces Y, left sole anchors XZ. No model scaling.','models':records}
path=OUT/'eva_recovery_r31.json';path.write_text(json.dumps(result,separators=(',',':')),encoding='utf8');(OUT/'recovery_profile_report.json').write_text(json.dumps({'status':'isolated CPU pose/contact preparation; no native-game acceptance','profiles':reports,'file':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()},indent=2),encoding='utf8')
