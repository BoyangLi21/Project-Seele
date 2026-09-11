"""Finish the clearance arc and event timing without altering grounded contacts."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/grounded_battle_r18'

def main():
    source=OUT/'candidate_v14.json';data=json.loads(source.read_text())
    # Four additional metres at the apex clear the fallen opponent while the
    # right leg opens. Constant acceleration and the contact endpoint remain.
    first,last=303,366
    for i in range(first,last+1):
        u=(i-first)/(last-first);lift=4*4*u*(1-u)
        data['eva']['frames'][i]['root_m'][1]+=lift/35
        for key,points in data['eva'].items():
            if key.endswith('_blocks') and key!='root_blocks':points[i][1]+=lift
    offsets={'eva':[],'angel':[]}
    for i in range(691):
        time=i/30
        recoil=max(0,min(1,(time-9.2)/.6));enemy_shift=30*(1-(1-recoil)**2)
        hero_shift=30*max(0,min(1,(time-10.1)/2.1))
        for role,amount in (('eva',hero_shift),('angel',enemy_shift)):
            offsets[role].append(amount)
            for key,points in data[role].items():
                if key.endswith('_blocks'):points[i][2]+=amount
        camera_shift=(hero_shift+enemy_shift)/2
        for key in ('position','target'):data['camera'][key][i][2]+=camera_shift
    data['r18_scene_offsets']=offsets
    data['landing_tick']=244
    data['reference']='R18: captured TV battle order with supported kneepads and toes, an exact ballistic pounce, laid-out Sachiel legs, continuous withdrawal and rigid two-step clinch. No vertex-morph mantle.'
    path=OUT/'candidate_final.json';path.write_text(json.dumps(data,separators=(',',':')),encoding='utf8')
    (OUT/'final_lineage.json').write_text(json.dumps({'source':source.name,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'final_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'changed_pose_frames':[first,last],'change':'Whole-EVA ballistic vertical clearance; immediate extra 30 m enemy recoil and the matching EVA leap. Both actors and camera share the same final translation, preserving all grounded relative contacts. Landing cue at 12.2 s.'},indent=2),encoding='utf8')
    print(path)

if __name__=='__main__':main()
