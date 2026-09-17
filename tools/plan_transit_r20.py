"""Grade-separated native rails with separate directions between terminals.

Uses the installed engine's ordered path, preserving existing public identities.
Only intermediate stops gain a second platform; terminal tracks remain shared
for a cab reversal, with each direction joining at the terminal throat.
"""
from pathlib import Path
import copy, hashlib, json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/world_rebuild_r20/transit'
CN={'第三新東京環状線':'第三新东京环线','NERV 整備循環線':'NERV 整备联络线','箱根湾・新箱根連絡便':'箱根湾—新箱根航班','NERV 本部連絡線':'NERV 总部联络线','霧里団地連絡線':'雾里住宅区线','新箱根空港連絡線':'新箱根机场线','箱根湾空港快速':'箱根湾机场快线','箱根地域本線':'箱根地区干线','湾岸埠頭連絡線':'湾岸港口线',
    '箱根湾空港':'箱根湾机场','NERV 港湾・埠頭':'NERV 港口','霧里団地':'雾里住宅区','新箱根市民広場':'新箱根市民广场','NERV 表口':'NERV 地面入口','湾岸・都市防衛区':'湾岸防卫区','新箱根中央':'新箱根中央','第三新東京中央':'第三新东京中央','EVA ケイジ':'EVA 机库','NERV 本部':'NERV 总部','南部住宅区':'南部住宅区','研究・シミュレーション区':'研究模拟区','西部市街':'西部城区','湾岸連絡口':'湾岸联络口','地域技術センター':'地区技术中心','GEOFRONT 入構駅':'地下都市入口','新箱根飛行場':'新箱根机场','整備補給センター':'整备补给中心'}
DIR={'E':(1,0),'W':(-1,0),'S':(0,1),'N':(0,-1),'NE':(1,-1),'NW':(-1,-1),'SE':(1,1),'SW':(-1,1)}
def xyz(p):return tuple(p[k] for k in ('x','y','z'))
def key(a,b):return tuple(sorted((xyz(a),xyz(b))))
def lifted(p):
    p=copy.deepcopy(p)
    if p['y']>=0:p['y']=max(94,p['y']+14)
    if (p['x'],p['z']) in {(-672,680),(-720,-152),(-672,-200)}:p['y']=max(110,p['y'])
    return p
def offset(p,angle,side):
    p=lifted(p);dx,dz=DIR[angle];p['x']-=dz*side;p['z']+=dx*side
    return p
def native_id(old):return int.from_bytes(hashlib.sha256(f'projectseele/r20/platform/return/{old}'.encode()).digest()[:8],'big')&0x7fffffffffffffff
def position(x,y,z):return dict(x=x,y=y,z=z)
def airport_changes(s):
    """Parallel arrivals use the same heading as departures at each airport.

    This removes two redundant terminal-area U-turns without moving either
    stand, so the actual aircraft doors retain their boarding bridges.
    """
    air_template=next(r for r in s['rails'] if r['transportMode']=='AIRPLANE' and not r['isPlatform'] and not r['isSiding'] and not r['canConnectRemotely'])
    paths=next(p['path'] for p in s['depot_paths'] if p['depot']==6752294717177047362)
    retire={key(q['startPosition'],q['endPosition']) for i,q in enumerate(paths) if 15<=i<=24 or 40<=i<=49}
    # The generated air path does not contain the whole stored descent rail.
    retire.update(key(r['position1'],r['position2']) for r in s['rails'] if r['transportMode']=='AIRPLANE' and r['canConnectRemotely'] and r['speedLimit1']==180)
    add=[]
    def rail(a,aa,b,bb,speed=40,remote=False):
        q=copy.deepcopy(air_template);q.update(position1=position(*a),angle1=aa,position2=position(*b),angle2=bb,speedLimit1=speed,speedLimit2=0,canConnectRemotely=remote);add.append(q)
    # Hakone arrivals now land eastbound and leave by the east taxiway.
    rail((-2240,180,40),'E',(-1880,80,40),'W',180,True)
    rail((-1880,80,40),'E',(-1600,80,40),'W',180)
    rail((-1600,80,40),'E',(-1560,80,40),'W')
    rail((-1560,80,40),'E',(-1520,80,0),'S')
    rail((-1520,80,0),'N',(-1520,80,-170),'S')
    rail((-1520,80,-170),'N',(-1560,80,-210),'E')
    rail((-1560,80,-210),'W',(-1590,80,-210),'E')
    # Bay arrivals land westbound; two bends lead straight to the existing stand.
    rail((1600,180,1490),'W',(1240,80,1490),'E',180,True)
    rail((1240,80,1490),'W',(960,80,1490),'E',180)
    rail((960,80,1490),'W',(560,80,1490),'E')
    rail((560,80,1490),'W',(520,80,1450),'S')
    rail((520,80,1450),'N',(520,80,1280),'S')
    rail((520,80,1280),'N',(560,80,1240),'W')
    rail((560,80,1240),'E',(592,80,1240),'W')
    rail((592,80,1240),'E',(630,80,1240),'W')
    return retire,add
def main():
    s=json.loads((OUT/'native_snapshot.json').read_text(encoding='utf-8'));out={k:copy.deepcopy(s[k]) for k in ('stations','platforms','routes','sidings','depots','lifts')}
    rails={key(r['position1'],r['position2']):r for r in s['rails']}
    platforms={key(p['position1'],p['position2']):p for p in s['platforms']}
    original_platforms={p['id']:p for p in s['platforms']};routes={r['id']:r for r in s['routes']}
    new_platforms={p['id']:p for p in out['platforms']};used,new_rails=airport_changes(s);identity=[];station_tracks={}
    depot_route={d['id']:routes[d['routeIds'][0]] for d in s['depots']}
    for dp in s['depot_paths']:
        route=depot_route[dp['depot']];line=route['routeNumber']
        if route['transportMode']!='TRAIN':continue
        closed=line=='C1';seq=[a['platformId'] for a in route['routePlatformData']];terminals=set() if closed else {seq[0],seq[len(seq)//2]}
        path=dp['path'] if closed else dp['path'][:len(dp['path'])//2]
        if line=='S1':
            # A viaduct must never cross an aircraft runway at tail height.
            # The railway skirts the airport's east boundary, beyond both
            # runway ends, and approaches the retained station from the east.
            used.update(key(q['startPosition'],q['endPosition']) for q in path[3:-1])
            nodes=[((-1720,104,312),'N'),((-1480,100,200),'E'),((-1380,98,200),'E'),((-1340,98,160),'N'),((-1340,88,-160),'N'),((-1420,82,-265),'W'),((-1622,65,-265),'W')]
            reverse={'N':'S','S':'N','E':'W','W':'E'};middle=[]
            for (a,aa),(b,bb) in zip(nodes,nodes[1:]):middle.append(dict(startPosition=position(*a),startAngle=aa,endPosition=position(*b),endAngle=reverse[bb]))
            last=copy.deepcopy(path[-1]);last['startPosition'],last['endPosition']=last['endPosition'],last['startPosition'];last['startAngle'],last['endAngle']='W','E'
            path=path[:3]+middle+[last]
        elif line=='P1':
            # Both ends of the old single long rail were terminal points, so
            # offsetting only its endpoints produced two identical tracks.
            # Interior nodes provide actual separate running lines and throats.
            original=path[1];used.add(key(original['startPosition'],original['endPosition']))
            nodes=[(544,80,472),(580,80,472),(1124,70,472),(1160,70,472)];middle=[]
            for a,b in zip(nodes,nodes[1:]):middle.append(dict(startPosition=position(*a),startAngle='E',endPosition=position(*b),endAngle='W'))
            path=[path[0]]+middle+[path[-1]]
        terminal_points={xyz(p[k]) for pid in terminals for p in [original_platforms[pid]] for k in ('position1','position2')}
        return_ids={}
        for seg in path:
            oldkey=key(seg['startPosition'],seg['endPosition'])
            if oldkey in used:continue
            used.add(oldkey);old=rails.get(oldkey)
            if old is None:
                old=copy.deepcopy(next(r for r in s['rails'] if r['transportMode']=='TRAIN' and not r['isPlatform'] and not r['isSiding']));old.update(position1=seg['startPosition'],position2=seg['endPosition'],angle1=seg['startAngle'],angle2=seg['endAngle'],speedLimit1=60,speedLimit2=60,signalColors=[])
            platform=platforms.get(oldkey);terminal=platform is not None and platform['id'] in terminals
            sides=[0] if closed or terminal else [4,-4]
            for side in sides:
                r=copy.deepcopy(old)
                def endpoint(p,angle):return lifted(p) if xyz(p) in terminal_points else offset(p,angle,side)
                # The end angle points back along the curve; negate the side.
                a=endpoint(seg['startPosition'],seg['startAngle']);b=lifted(seg['endPosition']) if xyz(seg['endPosition']) in terminal_points else offset(seg['endPosition'],seg['endAngle'],-side)
                if xyz(r['position1'])==xyz(seg['startPosition']):r['position1'],r['position2']=a,b
                else:r['position1'],r['position2']=b,a
                if not r['isPlatform']:
                    # A second physical track does not force a direction.
                    # With only two terminal stops, the native pathfinder took
                    # the shorter track both ways and the minute service jammed.
                    speed=max(r['speedLimit1'],r['speedLimit2']);stored_forward=xyz(r['position1'])==xyz(a)
                    outbound=side>=0
                    r['speedLimit1']=speed if stored_forward==outbound else 0
                    r['speedLimit2']=0 if stored_forward==outbound else speed
                new_rails.append(r)
                if platform:
                    pid=platform['id'] if side>=0 else native_id(platform['id']);p=copy.deepcopy(platform);p.update(id=pid,position1=r['position1'],position2=r['position2'],dwellTime=12000)
                    p['name']='1' if side>=0 else '2';new_platforms[pid]=p
                    if side<0:return_ids[platform['id']]=pid
                    identity.append(dict(line=line,original=platform['id'],id=pid,side=side,old=[xyz(platform['position1']),xyz(platform['position2'])],new=[xyz(p['position1']),xyz(p['position2'])]))
                    station_tracks.setdefault(platform['id'],[]).append(pid)
        current=next(r for r in out['routes'] if r['id']==route['id'])
        for i,rp in enumerate(current['routePlatformData']):
            if not closed and i>len(seq)//2:rp['platformId']=return_ids.get(rp['platformId'],rp['platformId'])
            rp['customDestination']=''
    # Non-route siding links retain their original horizontal geometry.
    for k,r in rails.items():
        if k in used:continue
        q=copy.deepcopy(r)
        if q['transportMode']=='TRAIN':q['position1']=lifted(q['position1']);q['position2']=lifted(q['position2'])
        new_rails.append(q)
    out['rails']=new_rails;out['platforms']=list(new_platforms.values())
    for st in out['stations']:
        st['name']=CN[st['name']]
        ids=[p['id'] for p in s['platforms'] if p['transportMode']=='TRAIN' and all(min(st['position1'][k],st['position2'][k])<=p['position1'][k]<=max(st['position1'][k],st['position2'][k]) for k in ('x','y','z'))]
        ps=[new_platforms[i] for pid in ids for i in station_tracks.get(pid,[pid])]
        for p in ps:
            for k in ('x','y','z'):
                pad=20 if k!='y' else 15
                st['position1'][k]=min(st['position1'][k],p['position1'][k]-pad,p['position2'][k]-pad)
                st['position2'][k]=max(st['position2'][k],p['position1'][k]+pad,p['position2'][k]+pad)
    for r in out['routes']:r['name']=CN[r['name']]
    for d in out['depots']:
        route=depot_route[d['id']];d['name']=CN[route['name']]+'运营所';d['repeatInfinitely']=True
        if d['transportMode']=='TRAIN':
            d['position1']=lifted(d['position1']);d['position2']=lifted(d['position2'])
            # A low site's max(y+14,94) needs an actual range around its siding.
            old=next(x for x in s['sidings'] if x['name'].startswith(route['routeNumber']+' '));p=lifted(old['position1']);d['position1']['y']=p['y']-5;d['position2']['y']=p['y']+15
            d['useRealTime']=True;d['realTimeDepartures']=list(range(0,86400000,60000));d['frequencies']=[240]*24
    for sid in out['sidings']:
        line=sid['name'].split(' ')[0];sid['name']=line+'车辆段'
        # Native path/vehicle caches belong to the old alignment and must be
        # regenerated by the engine; public siding IDs and consists stay fixed.
        for k in ('vehicles','pathSidingToMainRoute','pathMainRouteToSiding','path','departures','trips'):sid.pop(k,None)
        if sid['transportMode']=='TRAIN':
            sid['position1']=lifted(sid['position1']);sid['position2']=lifted(sid['position2']);sid['maxVehicles']=24;sid['earlyVehicleIncreaseDwellTime']=True;sid['delayedVehicleReduceDwellTimePercentage']=0
    assert len({p['id'] for p in out['platforms']})==len(out['platforms'])
    assert {p['id'] for p in s['platforms']} <= {p['id'] for p in out['platforms']}
    out['platform_migrations']=identity;out['timezone']='Asia/Shanghai';out['train_headway_ms']=60000
    (OUT/'native_plan.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('R20 transit plan',len(new_rails),'rails',len(out['platforms']),'platforms')
if __name__=='__main__':main()
