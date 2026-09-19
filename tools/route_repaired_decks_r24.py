"""Inspect repaired floor bands as separate walkable spans around known station rooms.

The floor repair crosses beneath existing waiting-room walls; that does not
authorize a straight pedestrian route through the walls. Retain the evidence.
"""
from pathlib import Path
import json
from query_blocks import read_box,AIR
ROOT=Path(__file__).resolve().parents[1];WORLD=ROOT/'run/saves/SEELE_R24_TV_REVIEW';OUT=ROOT/'artifacts/facility_r24/station_decks'
def main():
    path=OUT/'contract.json';data=json.loads(path.read_text(encoding='utf8'));stations=json.loads((ROOT/'artifacts/access_r22/transit/civil/station_contract.json').read_text(encoding='utf8'))['stations'];routes=[];blocked=[]
    for station in stations:
        x,y,z=station['center'];h=station['half'];start=-h+5+(y-station['ground'])+7;hor=station['horizontal'];dx,dz=(h+2,19) if hor else (19,h+2)
        b=read_box(WORLD,'projectseele:geofront',(x-dx,y,z-dz),(x+dx,y+4,z+dz))
        def at(u,Y,w):return (x+u,Y,z+w) if hor else (x+w,Y,z+u)
        for side in (-1,1):
            span=[];spans=[]
            for u in range(start,h-2):
                states=[b[at(u,Y,side*15)] for Y in (y+1,y+2)]
                if all(s in AIR|{'minecraft:light'} for s in states):span.append(u)
                else:
                    if span:spans.append(span);span=[]
                    blocked.append(dict(station=station['station'],line=station['line'],pos=at(u,y+1,side*15),states=states))
            if span:spans.append(span)
            for i,span in enumerate(spans):
                if len(span)<2:continue
                a=at(span[0],y+1,side*15);c=at(span[-1],y+1,side*15);key=f'r24/deck_span/{station["platform_ids"][0]}/{side}/{i}'
                aa=[a[0]+.5,a[1],a[2]+.5];cc=[c[0]+.5,c[1],c[2]+.5]
                routes.extend([dict(id=key,start=aa,end=cc),dict(id=key+'/return',start=cc,end=aa)])
    data['walk_nodes']=routes;data['floor_band_structures']=blocked
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    from collections import Counter
    print('Measured floor spans:',len(routes),'separating structural cells',len(blocked),Counter(s for r in blocked for s in r['states'] if s not in AIR))
if __name__=='__main__':main()
