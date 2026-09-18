"""Seal measured wet-cell returns and remove leaked LCL outside the live fill contract."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.ndimage import label
import regional_voxels as v
import scan_regional_completion as scan
import plan_factory_r20 as factory
from query_blocks import AIR
ROOT=v.ROOT;WORLD=ROOT/'run/saves/SEELE_R22_REVIEW';OUT=ROOT/'artifacts/facility_r23/containment';LO=(-60,-530,-305);HI=(180,-330,25)
def sightlines(array,palette):
 transparent=np.array([s.split('[')[0] in AIR|{'minecraft:light','minecraft:barrier'} or 'glass' in s or s.startswith(('projectseele:lcl','minecraft:water')) for s in palette]);rows=[]
 for c in (-12,30,72):
  for name,z in [('front_near',-276.5),('front_centre',-281.5),('rear_near',-209.5),('rear_centre',-205.5)]:
   eye=np.array([c+.5,-365.38,z])
   for target_name,target_y in [('head',-385.5),('shoulders',-398.0)]:
    target=np.array([c+.5,target_y,-240.5]);hits=[];seen=set()
    for t in np.linspace(0,1,math_ceil(np.linalg.norm(target-eye)*10)):
     q=tuple(np.floor(eye*(1-t)+target*t).astype(int));x,y,zz=np.array(q)-LO
     if q in seen:continue
     seen.add(q);state=int(array[y,zz,x])
     if not transparent[state]:hits.append({'pos':list(map(int,q)),'state':palette[state]})
    rows.append(dict(cage=c,view=name,target=target_name,eye=eye.tolist(),first_obstruction=hits[0] if hits else None,obstructing_cells=len(hits)))
 return rows
def math_ceil(x):return int(np.ceil(x))+1
def main(apply=False):
 OUT.mkdir(parents=True,exist_ok=True);v.WORLD=scan.WORLD=WORLD;v.OUT=OUT;factory.LO=LO;factory.HI=HI;s=factory.Scene();p=v.Painter()
 before_views=sightlines(s.before,s.palette);yy,zz,xx=np.ogrid[LO[1]:HI[1]+1,LO[2]:HI[2]+1,LO[0]:HI[0]+1];allowed=np.zeros(s.before.shape,bool)
 for c in (-12,30,72):allowed|=(abs(xx-c)<=19)&(yy>=-442)&(yy<=-399)&(zz>=-266)&(zz<=-214)
 lcl=np.array([q.startswith('projectseele:lcl[') for q in s.palette])[s.before];escaped=lcl&~allowed;leaks=int(escaped.sum());s.after[escaped]=s.state('minecraft:air')
 repairs=[]
 # Fixed returns flank the 35-wide native moving gate. Never narrow the EVA
 # transport opening or replace the invisible central pressure seal.
 for c in (-12,30,72):
  for x in (c-20,c-19,c-18,c+18,c+19,c+20):
   for y in range(-443,-398):
    q=(x,y,-213);old=s.palette[s.before[y-LO[1],-213-LO[2],x-LO[0]]]
    if old.split('[')[0] in AIR|{'minecraft:light'} or old.startswith('projectseele:lcl'):
     s.fill((*q,*q),'projectseele:nerv_shaft_panel');repairs.append({'pos':q,'before':old})
  # A real shell must also be continuous along the retained side faces.
  for x in (c-20,c+20):
   for y in range(-442,-399+1):
    for z in range(-267,-213+1):
     q=(x,y,z);old=s.palette[s.after[y-LO[1],z-LO[2],x-LO[0]]]
     if old.split('[')[0] in AIR|{'minecraft:light'} or old.startswith('projectseele:lcl'):
      s.fill((*q,*q),'projectseele:nerv_shaft_panel');repairs.append({'pos':q,'before':old})
 count=s.delta(p,'r23/sealed_pressure_returns');after_lcl=np.array([q.startswith('projectseele:lcl[') for q in s.palette])[s.after];components,n=label(after_lcl)
 p.meta.update(leaked_liquid_removed=leaks,sealed_return_cells=repairs,remaining_liquid=int(after_lcl.sum()),liquid_components=n,escaped_after=int((after_lcl&~allowed).sum()),sightlines_before=before_views,changed_cells=count)
 assert p.meta['escaped_after']==0
 p.save_plan('pressure_returns_and_leak_cleanup')
 if apply:p.apply('pressure_returns_and_leak_cleanup')
 (OUT/'report.json').write_text(json.dumps(p.meta,ensure_ascii=False,indent=2),encoding='utf8');print('Removed leaked LCL',leaks,'sealed returns',len(repairs),'remaining liquid components',n,'changed',count)
 print('Near window obstructed rays',[(r['cage'],r['view'],r['target'],r['first_obstruction']) for r in before_views if 'near' in r['view'] and r['first_obstruction']])
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
