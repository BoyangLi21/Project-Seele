"""Inspect measured BVH poses and locate strikes before any EVA retargeting."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/first_battle_refinement_r12';SOURCE=OUT/'sources'
def main():
 names=['heavy_push','heavy_pull','pull_a','resist_b','grab_a','grab_b','punch','punch2','kick'];fig=plt.figure(figsize=(14,25),facecolor='#f2f4f6');report=[]
 for row,name in enumerate(names):
  d=np.load(SOURCE/(name+'.npz'));joints=list(d['names']);p=d['positions'];fps=float(d['fps']);parents=d['parents'];hips=joints.index('Hips');height=np.percentile(p[:,:,1].max(1)-p[:,:,1].min(1),95)
  hand='Hand_R' if 'Hand_R' in joints else 'RightHand';foot='Foot_L' if 'Foot_L' in joints else 'LeftFoot';foot2='Foot_R' if 'Foot_R' in joints else 'RightFoot'
  velocity=np.linalg.norm(np.gradient(p[:,joints.index(hand)]-p[:,hips],axis=0)*fps,axis=1)/height;peaks,_=find_peaks(velocity,distance=int(fps*.40),prominence=.35)
  foot_speed=np.maximum(p[:,joints.index(foot),1],p[:,joints.index(foot2),1]);kicks,_=find_peaks(foot_speed,distance=int(fps*.5),prominence=height*.1)
  choice=np.round(np.linspace(.12,.88,4)*(len(p)-1)).astype(int)
  events=kicks if name=='kick' else peaks
  if len(events)>=4:choice=np.sort(events[np.argsort(velocity[events])[-4:]]) if name!='kick' else events[:4]
  floor=min(np.percentile(p[:,joints.index(foot),1],3),np.percentile(p[:,joints.index(foot2),1],3));source_summary=dict(name=name,height=height,hand_speed_peaks=[dict(frame=int(i),seconds=round(float(i/fps),3),speed_Hps=round(float(velocity[i]),3)) for i in peaks],kick_peaks=[int(v) for v in kicks]);report.append(source_summary)
  for col,index in enumerate(choice):
   a=fig.add_subplot(len(names),4,row*4+col+1,projection='3d');q=(p[index]-[p[index,hips,0],floor,p[index,hips,2]])/height
   for i,parent in enumerate(parents):
    if parent<0:continue
    line=q[[i,parent]];n=joints[i];colour='#3167a2' if n.startswith('Left') or n.endswith('_L') else '#c67d32' if n.startswith('Right') or n.endswith('_R') else '#344251'
    a.plot(line[:,0],line[:,2],line[:,1],c=colour,lw=2.5)
   for n in [foot,foot2]:
    point=q[joints.index(n)];a.scatter(*point[[0,2,1]],c='#258761' if point[1]<.035 else '#d84f40',s=20)
   a.set_xlim(-.7,.7);a.set_ylim(-.7,.7);a.set_zlim(-.05,1.13);a.set_box_aspect((1.2,1.2,1));a.view_init(elev=12,azim=-65);a.set_axis_off();a.set_title(f'{name}  frame {index} / {index/fps:.2f}s',fontsize=10,pad=-6)
 fig.subplots_adjust(left=.01,right=.99,bottom=.01,top=.99,wspace=0,hspace=.12);fig.savefig(OUT/'human_source_poses.png',dpi=150);plt.close(fig);(SOURCE/'motion_events.json').write_text(json.dumps(report,indent=2));print('Human source pose sheet and measured strike windows saved')
if __name__=='__main__':main()
