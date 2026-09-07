"""Replace the airport's two-metre corner with three forty-metre curves."""
import json
from quality_structures import OUT,OLD,load

def build():
    old=load(OLD/'transit_plan.json');retired=next(r for r in old['rails'] if r['id']=='S1_section_1_underpass')
    definitions=[
        ('S1_tunnel_shift_a',[-1720,65,120],[-1760,65,80],'N','E'),
        ('S1_tunnel_shift_b',[-1760,65,80],[-1800,65,40],'W','S'),
        ('S1_tunnel_main',[-1800,65,40],[-1800,65,-225],'N','S'),
        ('S1_tunnel_curve',[-1800,65,-225],[-1760,65,-265],'N','W'),
        ('S1_tunnel_entry',[-1760,65,-265],[-1718,65,-265],'E','W')]
    additions=[dict(id=name,**{'from':a,'to':b},from_angle=aa,to_angle=ab,kind='rail',mode='TRAIN',speed=60) for name,a,b,aa,ab in definitions]
    platforms=[p for p in old['platforms'] if p['line']=='S1'];keys={p['station'] for p in platforms}
    prototype=dict(rails=[r for r in old['rails'] if r['id'].startswith('S1_') and r['id']!=retired['id']]+additions,
        platforms=platforms,stations=[s for s in old['stations'] if s['id'] in keys],lines=[l for l in old['lines'] if l['id']=='S1'])
    (OUT/'airport_rail_splice.json').write_text(json.dumps(dict(retire=[retired],additions=additions),indent=2),encoding='utf-8')
    (OUT/'airport_rail_splice_prototype.json').write_text(json.dumps(prototype,ensure_ascii=False,indent=2),encoding='utf-8')
    print('S1 splice:1 old rail ->5 rails; original platforms/route/siding retained')

if __name__=='__main__':build()
