"""Native paired-pose inspections in the disposable model lab."""
import json,math,msvcrt
from pathlib import Path
from prepare_r10_model_review import ROOT,WORLD,main as ensure_lab
def main():
    ensure_lab();data=json.loads((ROOT/'src/main/resources/assets/projectseele/motion/first_battle_r10.json').read_text());views=[]
    for label,t in [('press',2.4),('tear',4.8),('grip',7.5),('kick',9.2),('pounce',10.9),('core',12.75),('rib',16.05),('wrap',18.35),('emerge',21.0)]:
        i=round(t*data['fps']);p=data['camera']['position'][i].copy();target=data['camera']['target'][i].copy();p[1]-=60+1.62;target[1]-=60
        dx,dy,dz=target[0]-p[0],target[1]-p[1]-1.62,target[2]-p[2]
        views.append(dict(file='r10_pose_'+label+'.png',position=p,yaw=math.degrees(math.atan2(-dx,dz)),pitch=math.degrees(math.atan2(-dy,math.hypot(dx,dz))),warmupTicks=240,action='pose:'+str(t)))
    with (WORLD/'session.lock').open('r+b') as lock:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);(WORLD/'r07_photo_views.json').write_text(json.dumps(views,indent=2),encoding='utf8')
    (ROOT/'artifacts/first_battle_world_r10/choreography/native_views.json').write_text(json.dumps(views,indent=2),encoding='utf8')
if __name__=='__main__':main()
