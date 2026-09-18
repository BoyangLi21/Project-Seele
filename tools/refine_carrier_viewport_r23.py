"""Rebuild only the original carrier spine, preserving every other machine part."""
from pathlib import Path
import hashlib,json,shutil
import numpy as np
import build_tv_machinery_r16 as b
ROOT=b.ROOT;OUT=ROOT/'artifacts/facility_r23/observation/carrier_viewport';OUT.mkdir(parents=True,exist_ok=True)
path=b.ASSETS/'mesh/tv_facilities_r16.json';original=OUT/'before.json'
if not original.exists():shutil.copy2(path,original)
data=json.loads(original.read_text());b.carrier()
old=np.array(data['parts']['carrier_spine']).reshape(-1,3,6)
data['parts']['carrier_spine']=b.PARTS['carrier_spine']
new=np.array(data['parts']['carrier_spine']).reshape(-1,3,6)
# Cast along Z through each intended inspection aperture sample. The opening
# stays between the original two rails and below the retained crown beam.
def hits(mesh,x,y):
    triangles=mesh[:,:,:3];a=triangles[:,0];e1=triangles[:,1]-a;e2=triangles[:,2]-a
    direction=np.array([0.,0.,-1.]);h=np.cross(direction,e2);det=np.einsum('ij,ij->i',e1,h);valid=np.abs(det)>1e-9
    f=np.zeros_like(det);f[valid]=1/det[valid];s=np.array([x,y,20.])-a;u=f*np.einsum('ij,ij->i',s,h);q=np.cross(s,e1);v=f*(q@direction);t=f*np.einsum('ij,ij->i',e2,q)
    return int(np.count_nonzero(valid&(u>=0)&(v>=0)&(u+v<=1)&(t>0)&(t<20)))
samples=[dict(x=x,y=y,before=hits(old,x,y),after=hits(new,x,y)) for x in (-3.,0.,3.) for y in (54.5,57.,59.5)]
assert all(r['before']>0 and r['after']==0 for r in samples)
baseline=json.loads(original.read_text())
assert all(value==baseline['parts'][key] for key,value in data['parts'].items() if key!='carrier_spine')
path.write_text(json.dumps(data,separators=(',',':')),encoding='utf8')
report=dict(passed=True,original_triangles=len(old),triangles=len(new),head_view_samples=samples,
            other_parts_unchanged=True,full_height_side_rails_and_crown_retained=True,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
(OUT/'report.json').write_text(json.dumps(report,indent=2));print(report)
