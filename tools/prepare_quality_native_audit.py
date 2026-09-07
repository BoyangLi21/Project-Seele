"""Prepare native collision cases and an independent terrain siting survey."""
import json
import argparse
import numpy as np
from pathlib import Path
from quality_structures import ROOT,OUT,OLD,load
from regional_voxels import WORLD

def prepare(quick=False,extension=False,crossings=False):
    cases=[];states=set(load(WORLD/'regional_states.json'))
    for path in sorted(OUT.glob('walk_cases_*.json')):
        incoming=load(path)
        if extension:
            if path.stem.startswith('walk_cases_estate'):cases.extend(incoming)
            elif path.name=='walk_cases_stations.json':cases.extend(c for c in incoming if any(s in c['id'] for s in ('R1_hakone_central','S1_hakone_central','interchange/-1480')))
            elif path.name=='walk_cases_airports.json':cases.extend(c for c in incoming if '/entry' in c['id'])
        else:cases.extend(incoming)
    for path in OUT.glob('*/states.json'):states.update(load(path))
    roads=np.load(OUT/'road_surfaces.npz');ox,oz=roads['origin'];mask=roads['mask'];h=roads['height2']
    for path in [] if extension else load(OUT/'road_plan.json').get('station_paths',[]):
        for index,(a,b) in enumerate(zip(path['points'],path['points'][1:])):
            if a==b:continue
            n=max(abs(a[0]-b[0]),abs(a[1]-b[1]));cells=[(round(a[0]+(b[0]-a[0])*i/n),round(a[1]+(b[1]-a[1])*i/n)) for i in range(n+1)]
            if not all(mask[z-oz,x-ox] for x,z in cells):continue
            start=[a[0]+.5,int(h[a[1]-oz,a[0]-ox])/2,a[1]+.5];end=[b[0]+.5,int(h[b[1]-oz,b[0]-ox])/2,b[1]+.5]
            cases.extend([dict(id='station_road/'+path['id']+'/'+str(index),start=start,end=end),dict(id='station_road/'+path['id']+'/'+str(index)+'/return',start=end,end=start)])
    # The retained airport flights are checked before their architecture is refined.
    for sx,gx,rz in [(740,650,1430),(-1670,-1610,-20)]:
        for label,a,b in [('terminal',[sx+.5,72,rz-296.5],[sx+.5,81,rz-308.5]),('apron',[gx+.5,72,rz-235.5],[gx+.5,81,rz-223.5])]:
            cases.extend([dict(id=f'airport/{sx}/{label}',start=a,end=b),dict(id=f'airport/{sx}/{label}/return',start=b,end=a)])
    if extension:
        road_data=np.load(OUT/'extension_road_surfaces.npz');h=road_data['height2'];ox,oz=map(int,road_data['origin'])
        for road in load(OUT/'extension_plan.json')['roads']:
            for index,(a,b) in enumerate(zip(road['points'],road['points'][1:])):
                n=max(abs(b[0]-a[0]),abs(b[2]-a[2]));points=[]
                for distance in list(range(0,n,32))+[n]:
                    x=round(a[0]+(b[0]-a[0])*distance/max(1,n));z=round(a[2]+(b[2]-a[2])*distance/max(1,n));points.append([x+.5,int(h[z-oz,x-ox])/2,z+.5])
                for j,(start,end) in enumerate(zip(points,points[1:])):
                    cases.extend([dict(id=f'extension_road/{road["id"]}/{index}/{j}',start=start,end=end),dict(id=f'extension_road/{road["id"]}/{index}/{j}/return',start=end,end=start)])
    # Start with the newly repaired junctions so a failure is visible immediately.
    cases.sort(key=lambda c:(1 if '/stair_core/' in c['id'] else 0,c['id']))
    if quick:
        cases=[c for c in cases if '/stair_core/' not in c['id']]+[c for c in cases if '/stair_core/' in c['id']][:72]
    if crossings:
        cases=[c for c in cases if c['id'].startswith('airport/')]
        # Both directions across the last edited C1 crossing and its road seams.
        # Heights are expected datums; the server independently walks real blocks.
        a=np.load(OUT/'road_surfaces.npz');h=a['height2'];mask=a['mask'];ox,oz=map(int,a['origin'])
        for horizontal in (True,False):
            for fixed in range(-180,-87,4) if horizontal else range(-756,-679,4):
                cells=[(v,fixed) if horizontal else (fixed,v) for v in (range(-756,-679) if horizontal else range(-180,-87))]
                runs=[];run=[]
                for x,z in cells:
                    if mask[z-oz,x-ox]:run.append((x,z))
                    elif run:runs.append(run);run=[]
                if run:runs.append(run)
                for index,run in enumerate(runs):
                    if len(run)<3:continue
                    points=[[x+.5,int(h[z-oz,x-ox])/2,z+.5] for x,z in (run[0],run[-1])]
                    key=f'final_crossing/{"x" if horizontal else "z"}/{fixed}/{index}'
                    cases.extend([dict(id=key,start=points[0],end=points[1]),dict(id=key+'/return',start=points[1],end=points[0])])
    (WORLD/'quality_walk_cases.json').write_text(json.dumps(cases,ensure_ascii=False),encoding='utf-8')
    (WORLD/'regional_states.json').write_text(json.dumps(sorted(states),ensure_ascii=False),encoding='utf-8')
    points=[[x,z] for x in range(-3344,-2320,32) for z in range(-1520,-495,32)]
    points += [[x,z] for x in range(-2320,-1375,32) for z in range(-480,305,32)]
    points += [[x,z] for x in range(160,801,32) for z in range(960,1089,32)]
    if not (WORLD/'quality_terrain_survey.json').exists():(WORLD/'quality_survey_points.json').write_text(json.dumps(points),encoding='utf-8')
    print('Native audit cases',len(cases),'states',len(states),'siting samples',len(points))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--quick',action='store_true');ap.add_argument('--extension',action='store_true');ap.add_argument('--crossings',action='store_true');args=ap.parse_args();prepare(args.quick,args.extension,args.crossings)
