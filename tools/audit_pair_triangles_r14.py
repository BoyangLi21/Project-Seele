"""Blender BVH cross-actor triangle intersections on evaluated, exported game meshes."""
import json,sys,numpy as np
from collections import Counter
from pathlib import Path
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];label=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'contacts';folder=ROOT/'artifacts/world_refinement_r14'/('pair_'+label);rows=[]
def exact_pairs(pairs,hero,angel):
 if not pairs:return []
 ids=np.array(pairs);a=hero.reshape(-1,3,3)[ids[:,0]];b=angel.reshape(-1,3,3)[ids[:,1]];ea=np.roll(a,-1,axis=1)-a;eb=np.roll(b,-1,axis=1)-b;na=np.cross(ea[:,0],ea[:,1]);nb=np.cross(eb[:,0],eb[:,1]);axes=[na,nb]
 for i in range(3):
  axes.append(np.cross(na,ea[:,i]));axes.append(np.cross(nb,eb[:,i]))
  for j in range(3):axes.append(np.cross(ea[:,i],eb[:,j]))
 good=np.ones(len(ids),bool)
 for axis in axes:
  norm=np.linalg.norm(axis,axis=1);axis/=np.maximum(1e-8,norm)[:,None];pa=np.einsum('vki,vi->vk',a,axis);pb=np.einsum('vki,vi->vk',b,axis);separate=(pa.min(1)>pb.max(1)+1e-5)|(pb.min(1)>pa.max(1)+1e-5);good&=~separate
 return ids[good].tolist()
for item in json.loads((folder/'manifest.json').read_text()):
 data=np.load(folder/(item['name']+'.npz'));trees=[]
 for role in ['hero','angel']:
  vs=data[role];trees.append(BVHTree.FromPolygons(vs,np.arange(len(vs)).reshape(-1,3),all_triangles=True,epsilon=0))
 candidates=trees[0].overlap(trees[1]);overlap=exact_pairs(candidates,data['hero'],data['angel']);names=json.loads((folder/'hero_parts.json').read_text()) if (folder/'hero_parts.json').exists() else [];parts=Counter(names[h] for h,a in overlap) if names else {};rows.append(dict(time=item['time'],pairs=len(overlap),bvh_candidates=len(candidates),examples=overlap[:12],hero_parts=dict(parts),angel_triangles=sorted({a for h,a in overlap})))
 examples={}
 if names:
  for h,a in overlap:
   group=examples.setdefault(names[h],[])
   if len(group)<3:group.append([h,a])
 rows[-1]['part_examples']=examples
 print(item['name'],len(overlap),flush=True)
(folder.parent/('triangle_'+label+'.json')).write_text(json.dumps(rows,indent=2));print('Cross-actor triangle overlap frames',sum(x['pairs']>0 for x in rows),flush=True)
(folder.parent/('triangle_'+label+'_source.json')).write_text((folder/'source.json').read_text())
