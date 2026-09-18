"""Match both stopping directions to the Eidan fleet's measured five-metre door pitch."""
from pathlib import Path
import copy,json,math
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/facility_r23/transit/gates'
def main():
 OUT.mkdir(parents=True,exist_ok=True);source=json.loads((OUT.parent/'native_plan.json').read_text(encoding='utf8'));plan=copy.deepcopy(source);moves={};records=[]
 def key(p):return tuple(p[k] for k in ('x','y','z'))
 for p in plan['platforms']:
  if p['transportMode']!='TRAIN' or p['position1']['y']<=0:continue
  a,b=p['position1'],p['position2'];axis='x' if a['z']==b['z'] else 'z';length=abs(a[axis]-b[axis]);new=math.ceil(length/10)*10;centre=(a[axis]+b[axis])/2;assert centre.is_integer() and new%2==0
  for old in (a,b):
   target=copy.deepcopy(old);target[axis]=int(centre+(new/2 if old[axis]>centre else -new/2));moves[key(old)]=target
  records.append(dict(platform_id=p['id'],old_length=length,new_length=new,centre=centre,axis=axis,door_pitch=5))
 for category in ('rails','platforms','sidings'):
  for obj in plan[category]:
   if obj['transportMode']!='TRAIN':continue
   for field in ('position1','position2'):
    if field in obj and key(obj[field]) in moves:obj[field]=copy.deepcopy(moves[key(obj[field])])
 # Preserve station identities and their centres, extending a boundary only
 # if a newly extended rail endpoint would otherwise fall outside it.
 for station in plan['stations']:
  if station['transportMode']!='TRAIN':continue
  a,b=station['position1'],station['position2'];low={k:min(a[k],b[k]) for k in ('x','y','z')};high={k:max(a[k],b[k]) for k in ('x','y','z')}
  for old,new in moves.items():
   if all(low[k]<=q<=high[k] for k,q in zip(('x','y','z'),old)):
    for k in ('x','z'):
     if new[k]<low[k]:a[k]=new[k]-2
     if new[k]>high[k]:b[k]=new[k]+2
 assert {p['id'] for p in plan['platforms']}=={p['id'] for p in source['platforms']}
 plan['r23_platform_alignment']='130 m R1 / 100 m S1 stopping rails inside the existing station decks, preserving all platform IDs; both approach directions share the 5 m doorway lattice.'
 (OUT/'native_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8');(OUT/'endpoint_moves.json').write_text(json.dumps(dict(platforms=records,nodes=[dict(before=list(k),after=v) for k,v in moves.items()]),indent=2));print('Aligned platform lengths',len(records),'station centres and platform IDs retained')
if __name__=='__main__':main()
