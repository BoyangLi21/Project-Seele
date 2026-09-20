"""Fit travelling rack pads behind the real bind-pose torso and shins, per EVA."""
from pathlib import Path
import json,sys,shutil
import numpy as np
import build_tv_machinery_r16 as m
import render_unit01_rig_preview as r
ROOT=m.ROOT;ART=ROOT/'artifacts/facility_r28/machinery';PACK=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele'

def surface(triangles,x,y):
    a=triangles[:,0,:2];b=triangles[:,1,:2]-a;c=triangles[:,2,:2]-a;d=np.array([x,y])-a
    det=b[:,0]*c[:,1]-b[:,1]*c[:,0];good=abs(det)>1e-9
    u=np.divide(d[:,0]*c[:,1]-d[:,1]*c[:,0],det,out=np.zeros(len(det)),where=good)
    v=np.divide(b[:,0]*d[:,1]-b[:,1]*d[:,0],det,out=np.zeros(len(det)),where=good)
    mask=good&(u>=0)&(v>=0)&(u+v<=1);assert mask.any(),(x,y)
    return float((triangles[:,0,2]+u*(triangles[:,1,2]-triangles[:,0,2])+v*(triangles[:,2,2]-triangles[:,0,2]))[mask].max())

def main():
    ART.mkdir(parents=True,exist_ok=True);path=m.ASSETS/'mesh/tv_facilities_r16.json'
    if not (ART/'before.json').exists():shutil.copy2(path,ART/'before.json')
    resource=json.loads((ART/'before.json').read_text());receipts=[]
    for unit in range(3):
        name=f'eva_unit0{unit}';mesh=json.loads((PACK/'mesh'/f'{name}.mesh.json').read_text());pv,pa,br=r.load_skeleton(mesh,PACK/'geo'/f'{name}.geo.json');cache={};alltri=[]
        for bone in ('torso_upper','torso_lower','shin_l','shin_r'):
            part=mesh['parts'][bone];matrix=np.array(r.bone_matrix(bone,pv,pa,{}, {},br,cache));a=np.asarray(part['vertices']).reshape(-1,8)[:,:3]+part['pivot'];a*=(-1,1,1)
            alltri.append(((np.c_[a,np.ones(len(a))]@matrix.T)[:,:3]*.3125).reshape(-1,3,3))
        triangles=np.concatenate(alltri);m.use('carrier_contacts_'+str(unit))
        for y,x in ((43,2),(36.8,1.8),(17,4.4)):
            for side in (-1,1):
                X=x*side;depths=[surface(triangles,X+dx,y+dy) for dx in (-.42,0,.42) for dy in (-.45,0,.45)]
                front=max(depths)+.08;assert front<8.8
                m.housing(X-.58,y-.6,front,1.16,1.2,.32,.16,m.DARK)
                m.housing(X-.68,y-.72,front+.32,1.36,1.44,.28,.20,m.EDGE)
                m.cylinder((X,y,front+.6),(X,y,9.95),.28,m.STEEL,24)
                m.cylinder((X,y,7.8),(X,y,10.25),.48,m.BLUE,24)
                m.bolts(X-.45,y-.45,front-.018,.90,.90)
                receipts.append(dict(unit=unit,centre=[X,y,front],body_depth=max(depths),clearance=.08))
        resource['parts']['carrier_contacts_'+str(unit)]=m.PARTS['carrier_contacts_'+str(unit)]
    m.use('carrier_power_reel')
    m.housing(-2.25,44.8,9.3,4.5,4.5,1.8,.48,m.OLIVE)
    m.cylinder((0,47,9.12),(0,47,9.40),1.5,m.DARK,32)
    for t in np.linspace(0,2*np.pi,18,endpoint=False):
        x,y=1.72*np.cos(t),47+1.72*np.sin(t);m.cylinder((x,y,9.15),(x,y,9.3),.09,m.STEEL,8)
    m.warning(-1.8,45.05,9.25,3.6,.36)
    resource['parts']['carrier_power_reel']=m.PARTS['carrier_power_reel']
    path.write_text(json.dumps(resource,separators=(',',':')),encoding='utf8')
    (ART/'contact_measurements.json').write_text(json.dumps(receipts,indent=2));print('Fitted',len(receipts),'contact pads to three original bodies')

if __name__=='__main__':main()
