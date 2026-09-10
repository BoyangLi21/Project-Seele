"""Decode the locally licensed source BVHs; no dataset is redistributed here."""
from pathlib import Path
import json,hashlib
import numpy as np
from scipy.spatial.transform import Rotation as R
from bvh_motion_r12 import load_bvh,save_npz

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/first_battle_refinement_r12'
CMU=ROOT/'external-assets/incoming/mocap/eva-original-combat-seed-r01/cmu_bvh'
CMU81=ROOT/'external-assets/incoming/mocap/cmu/subject81/bvh'
BNR=ROOT/'external-assets/incoming/bandai-namco-motiondataset/dataset/Bandai-Namco-Research-Motiondataset-1/data'
TUFFLES=ROOT/'external-assets/incoming/mocap/eva-action-source-r02/tuffles/HaleyTufflesPremadeMocapPack/BVH Converted'
SOURCES={
 'pull_a':(CMU/'18_03.bvh','CMU'),'resist_b':(CMU/'19_03.bvh','CMU'),
 'grab_a':(CMU/'18_05.bvh','CMU'),'grab_b':(CMU/'19_05.bvh','CMU'),
 'heavy_push':(CMU81/'81_05.bvh','CMU'),'heavy_pull':(CMU81/'81_07.bvh','CMU'),
 'punch':(BNR/'dataset-1_punch_normal_001.bvh','BNR CC BY-NC 4.0'),
 'punch2':(BNR/'dataset-1_punch_normal_002.bvh','BNR CC BY-NC 4.0'),
 'kick':(BNR/'dataset-1_kick_normal_001.bvh','BNR CC BY-NC 4.0'),
 'frontkick':(TUFFLES/'Combat/LegsSingleKick.bvh','Haley Tuffles'),
 'jump':(TUFFLES/'General/Jump01.bvh','Haley Tuffles'),
 'fall':(TUFFLES/'General/Falling.bvh','Haley Tuffles'),
 'downstrike':(TUFFLES/'Combat/SlapDownwards.bvh','Haley Tuffles'),
 'land':(TUFFLES/'General/LandingOnGroundStanding.bvh','Haley Tuffles'),
 'pushed':(TUFFLES/'Combat/PushedBackwards.bvh','Haley Tuffles')}

def main():
 missing=[str(p) for p,license in SOURCES.values() if not p.is_file()]
 if missing:raise FileNotFoundError('Install licensed local capture sources first: '+', '.join(missing))
 folder=OUT/'sources';folder.mkdir(parents=True,exist_ok=True);records=[]
 for name,(path,license) in SOURCES.items():
  d=load_bvh(path)
  if license=='Haley Tuffles':
   up=R.from_euler('x',-90,degrees=True);d['positions']=up.apply(d['positions'].reshape(-1,3)).reshape(d['positions'].shape);d['rotations']=(up*R.from_quat(d['rotations'].reshape(-1,4))).as_quat().reshape(d['rotations'].shape);d['axis_conversion']='Z-up to Y-up: -90 degrees X'
  save_npz(folder/(name+'.npz'),d);records.append(dict(name=name,source=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),license=license,used_in_final=name in {'pull_a','grab_a','grab_b','punch2','frontkick','jump','fall','downstrike','land','pushed'},frames=len(d['positions']),fps=d['fps']))
 (folder/'provenance.json').write_text(json.dumps(dict(sources=records,links=['https://mocap.cs.cmu.edu/','https://github.com/BandaiNamcoResearchInc/Bandai-Namco-Research-Motiondataset','https://haleytuffles.com/motioncapture']),indent=2))
 baseline=OUT/'baseline_r10.json'
 if not baseline.exists():baseline.write_bytes((ROOT/'src/main/resources/assets/projectseele/motion/first_battle_r10.json').read_bytes())
 print('Decoded',len(records),'private capture sources; production clip unchanged')
if __name__=='__main__':main()
