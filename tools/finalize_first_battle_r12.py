"""Contact-preserving transition filtering and cameras for the private capture clip.

This evaluates the same DQS geometry as the private game model. It does not
promote a clip: --install is separate from offline authoring and inspection.
"""
from pathlib import Path
import argparse,json,math,hashlib,shutil,time
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.ndimage import maximum_filter1d,gaussian_filter1d
import author_first_battle_r12 as a
from preview_first_battle_r12 import angel_pose

OUT=a.OUT;UNIT=a.UNIT;b=a.b;eva=a.eva
PARTS=['torso_lower','torso_upper','head','arm_l','arm_r','forearm_l','forearm_r','hand_l','hand_r','leg_l','leg_r','shin_l','shin_r','foot_l','foot_r']

def smooth_rotations(poses,names):
    original=np.array([[p.q[n].as_quat() for n in names] for p in poses]);result=original.copy()
    # Only transition/constraint spikes receive a wider filter. Most captured
    # frames remain unchanged, including their anticipation and follow-through.
    angle=np.zeros(original.shape[:2]);angle[1:]=np.degrees(2*np.arccos(np.clip(np.abs(np.sum(original[1:]*original[:-1],2)),0,1)))
    weight=np.clip((maximum_filter1d(angle,size=11,axis=0)-19)/26,0,1)
    for _ in range(3):
        before=result.copy()
        for i in range(len(poses)):
            indices=np.clip(np.arange(i-4,i+5),0,len(poses)-1);samples=before[indices].copy();centre=before[i];sign=np.where(np.sum(samples*centre,2)<0,-1.,1.);samples*=sign[:,:,None]
            kernel=np.exp(-.5*(np.arange(-4,5)/1.7)**2);mean=(samples*kernel[:,None,None]).sum(0);mean/=np.linalg.norm(mean,axis=1,keepdims=True)
            result[i]=centre*(1-weight[i,:,None])+mean*weight[i,:,None];result[i]/=np.linalg.norm(result[i],axis=1,keepdims=True)
    for i,p in enumerate(poses):
        for j,n in enumerate(names):p.setq(n,R.from_quat(result[i,j]))
    return dict(filtered_bone_frames=int((weight>.01).sum()),total_bone_frames=int(weight.size))

def recompute(data,heroes,angels):
    hero=data['eva'];enemy=data['angel'];cameras=data['camera'];floor=[];contacts=[]
    i=round(16.05*30);p=heroes[i];hr=np.array(hero['root_blocks'][i]);ar=np.array(enemy['root_blocks'][i]);hand=b.hero_world(p,hr,'hand_r',eva.P['finger_middle_r']);core=b.angel_world(angels[i],ar,'torso_upper',b.ANGEL.core)
    q=R.from_matrix(p.matrix('hand_r')[:3,:3]);rib_axis=q.inv().apply(a.retarget.unit(core-hand)*a.MIRROR);rib_side=q.inv().apply(a.retarget.unit(np.cross(a.retarget.unit(core-hand),[0,0,1]),(1,0,0))*a.MIRROR)
    for role in [hero,enemy]:
        for key in role:
            if key.endswith('_blocks') and key!='root_blocks':role[key]=[]
    hero['rib_tip_blocks']=[];hero['rib_side_blocks']=[]
    shots=[(0,[-65,48,8],[0,34,20]),(1.2,[-52,45,8],[0,39,21]),(4.2,[-48,46,12],[0,40,21]),(5.1,[-55,48,35],[-3,38,27]),(6.4,[-42,44,40],[-4,39,27]),(8.5,[-72,43,26],[0,30,28]),(9.65,[-78,60,70],[0,33,45]),(10.8,[-90,76,91],[3,40,55]),(347/30,[-90,76,91],[3,40,55]),(11.6,[58,53,33],[3,23,61]),(14.4,[43,42,35],[3,20,64]),(16.7,[67,51,44],[3,32,56]),(18.6,[78,49,96],[3,31,56]),(19.4,[62,46,89],[3,37,56]),(23,[62,46,89],[3,37,56])]
    cameras['cuts']=[348]
    for i,(p,angel) in enumerate(zip(heroes,angels)):
        t=i/30;hr=np.array(hero['root_blocks'][i]);ar=np.array(enemy['root_blocks'][i]);hero['frames'][i]=eva.encode(p,bone_names=hero['bones']);enemy['frames'][i]=angel.encode()
        for side in ['l','r']:
            hero['hand_'+side+'_blocks'].append(b.hero_world(p,hr,'hand_'+side,eva.P['finger_middle_'+side]).round(6).tolist());hero['foot_'+side+'_blocks'].append(b.hero_world(p,hr,'foot_'+side,eva.P['foot_'+side]+b.SOLE[side]).round(6).tolist());enemy['hand_'+side+'_blocks'].append(b.angel_world(angel,ar,'hand_'+side).round(6).tolist())
        eye=b.hero_world(p,hr,'head',b.EYE);hero['eye_blocks'].append(eye.round(6).tolist());direction=p.matrix('head')[:3,:3]@np.array([0,0,-1]);hero['look_blocks'].append((eye+direction*a.MIRROR*20).round(6).tolist())
        for name,bone,marker in [('eye_blocks','head',b.ANGEL.eye),('core_blocks','torso_upper',b.ANGEL.core),('waist_blocks','torso_lower',b.ANGEL.waist)]:enemy[name].append(b.angel_world(angel,ar,bone,marker).round(6).tolist())
        socket=b.hero_world(p,hr,'torso_upper',np.array([0,52.9,4.35])/UNIT);rotation=p.matrix('torso_upper')[:3,:3];outward=(rotation@np.array([0,.8660254,.5]))*a.MIRROR;up=(rotation@np.array([0,.5,-.8660254]))*a.MIRROR
        hero['socket_blocks'].append(socket.round(6).tolist());hero['socket_outward_blocks'].append((socket+outward*2).round(6).tolist());hero['socket_up_blocks'].append((socket+up*2).round(6).tolist())
        hand=np.array(hero['hand_r_blocks'][-1]);q=R.from_matrix(p.matrix('hand_r')[:3,:3]);hero['rib_tip_blocks'].append((hand+q.apply(rib_axis)*a.MIRROR*6.05).round(6).tolist());hero['rib_side_blocks'].append((hand+q.apply(rib_side)*a.MIRROR).round(6).tolist())
        cameras['position'][i]=b.curve([(at,pos) for at,pos,target in shots],t).round(6).tolist();cameras['target'][i]=b.curve([(at,target) for at,pos,target in shots],t).round(6).tolist()
        if i%3==0:floor.append(dict(t=t,eva=float(a.surface.floor(p,PARTS)*UNIT+hr[1]),angel=float(angel.skin()[:,1].min()*UNIT+ar[1])))
    return floor

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--install',action='store_true');args=ap.parse_args()
    if args.install:
        source=OUT/'first_battle_r12.json';audit=json.loads((OUT/'final_audit.json').read_text());assert audit['passed'];assert hashlib.sha256(source.read_bytes()).hexdigest()==audit['sha256']
        target=eva.ROOT/'run/projectseele-local-maps/first_battle_r12.json'
        if target.exists():shutil.copy2(target,OUT/('installed_before_'+str(int(time.time()))+'.json'))
        temp=target.with_suffix('.tmp');shutil.copy2(source,temp);temp.replace(target);print('Private R12 clip installed; bundled R10 retained');return
    data=json.loads((OUT/'candidate_v1.json').read_text());heroes=[eva.decode(f,data['eva']['bones']) for f in data['eva']['frames']];angels=[angel_pose(f,data['angel']['bones']) for f in data['angel']['frames']];original_hero=[a.clone(p) for p in heroes]
    evidence={'eva':smooth_rotations(heroes,data['eva']['bones']),'angel':smooth_rotations(angels,data['angel']['bones'])};pins=[]
    for i,(p,angel) in enumerate(zip(heroes,angels)):
        t=i/30;ar=np.array(data['angel']['root_blocks'][i]);hr=np.array(data['eva']['root_blocks'][i]);original=original_hero[i]
        minimum=angel.skin()[:,1].min()*UNIT+ar[1]
        if minimum<0:angel.setp('root',angel.p['root']+[0,-minimum/UNIT,0])
        minimum=a.surface.floor(p,PARTS)*UNIT+hr[1]
        if minimum<0:p.setp('root',p.p['root']+[0,-minimum/UNIT,0])
        for side in ['l','r']:
            keep=(.8<=t<=5.1) or (side=='r' and 6.2<=t<=8.1) or (side=='l' and 12.2<=t<=16.4) or (side=='r' and i in [round(at*30) for at in [12.75,14.15,16.05]])
            if not keep:continue
            target=original.point('hand_'+side);q=R.from_matrix(original.matrix('hand_'+side)[:3,:3]);pole=p.point('arm_'+side,eva.E[side])-p.point('arm_'+side)
            err=a.retarget.solve_ik(p,'arm_'+side,'forearm_'+side,'hand_'+side,eva.E[side],target,pole,q)*UNIT;pins.append(dict(t=t,side=side,error=err))
        if t>19.4:
            for n in data['eva']['bones']:
                if n.startswith('finger_'):p.setq(n,b.qmix(p.q[n],eva.idle.q[n],b.smooth((t-19.4)/3.6)))
    floors=recompute(data,heroes,angels);data['reference']='R12 capture adaptation: CMU paired pull and grip, BNR professional-actor punches, Tuffles front kick/jump/fall/kneeling support; authored nonhuman wrap. Private CC BY-NC component.'
    destination=OUT/'first_battle_r12.json';destination.write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    maximum={}
    for role in ['eva','angel']:
        qs=np.array([f['rotation_wxyz'] for f in data[role]['frames']]);angle=np.degrees(2*np.arccos(np.clip(np.abs((qs[1:]*qs[:-1]).sum(2)),0,1)));index=np.unravel_index(angle.argmax(),angle.shape);maximum[role]=dict(degrees=float(angle[index]),t=(int(index[0])+1)/30,bone=data[role]['bones'][index[1]])
    minimum=min(min(item['eva'],item['angel']) for item in floors);max_contact=max(item['error'] for item in pins);report=dict(passed=minimum>=-.08 and max_contact<.45 and all(item['degrees']<45 for item in maximum.values()),sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),duration_seconds=23,frames=691,filter=evidence,max_joint_step=maximum,min_floor=minimum,max_contact_error=max_contact,floors=floors,contacts=pins)
    (OUT/'final_audit.json').write_text(json.dumps(report,indent=2));print({k:v for k,v in report.items() if k not in ['floors','contacts']})
if __name__=='__main__':main()
