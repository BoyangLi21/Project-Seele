"""Native-survey-based isolated estate and a street-aligned commuter branch."""
import json,math
from pathlib import Path
from quality_structures import ROOT,OUT,OLD,load

def plan():
    rails=[];platforms=[];stations=[];chunks=set()
    def rail(key,a,b,ha='E',hb='W',kind='rail',speed=70):
        rails.append(dict(id=key,**{'from':a,'to':b},from_angle=ha,to_angle=hb,kind=kind,mode='TRAIN',speed=speed))
    def platform(key,name,center,length=64,**extra):
        x,y,z=center;rail(key,[x-length//2,y,z],[x+length//2,y,z],kind='platform')
        platforms.append(dict(id=key,station=key,name=name,center=center,heading='E',length=length,line='S2',surface=True,**extra))
        stations.append(dict(id=key,name=name,min=[x-length//2-18,y-5,z-18],max=[x+length//2+18,y+18,z+18]))
    platform('S2_kirisato','霧里団地',[-2752,70,-960])
    platform('S2_hakone','新箱根中央',[-1496,105,748],half_width=11,outer_walk_height=105,compact=True)
    rail('S2_depot',[-2944,70,-960],[-2816,70,-960],kind='siding',speed=30)
    rail('S2_depot_link',[-2816,70,-960],[-2784,70,-960],speed=30)
    rail('S2_estate_east',[-2720,70,-960],[-2448,70,-960])
    rail('S2_north_curve',[-2448,70,-960],[-2400,74,-912],'E','N')
    rail('S2_country',[-2400,74,-912],[-2400,100,700],'S','N',speed=90)
    rail('S2_south_curve',[-2400,100,700],[-2352,105,748],'S','W')
    rail('S2_city_street',[-2352,105,748],[-1528,105,748],speed=40)
    rail('S2_terminal_buffer',[-1464,105,748],[-1440,105,748],kind='turnback',speed=25)
    cars=[dict(id='eidan_9000_mini_cab_1',length=10,width=2,bogie1=-1,bogie2=5,padding1=1,padding2=0),dict(id='eidan_9000_mini_cab_2',length=10,width=2,bogie1=-5,bogie2=1,padding1=0,padding2=1)]
    line=dict(id='S2',name='霧里団地連絡線',color=0x75857A,platforms=['S2_kirisato','S2_hakone','S2_kirisato'],siding='S2_depot',cars=cars,frequency=2,dwell=10000,repeat=False)
    transit=dict(revision=1,rails=rails,platforms=platforms,stations=stations,lines=[line])
    roads=[]
    def road(name,points,width=9):roads.append(dict(id=name,points=points,width=width,walkway=width<=5))
    road('estate_outer',[[-2896,70,-1136],[-2608,70,-1136],[-2608,70,-984],[-2896,70,-984],[-2896,70,-1136]])
    for x in (-2797,-2709):road('estate_cross_'+str(x),[[x,70,-1136],[x,70,-984]],5)
    road('estate_courtyard',[[-2896,70,-1056],[-2608,70,-1056]],5)
    road('estate_connection',[[-2608,70,-1056],[-2376,70,-1056],[-2376,80,172],[-2232,80,172]])
    road('hakone_airport_access',[[-1670,80,-412],[-1670,80,-448],[-2232,80,-448],[-2232,80,172],[-1944,96,172],[-1944,104,300],[-1880,104,300]])
    road('bay_airport_access',[[740,80,1038],[740,80,992],[168,80,992],[168,80,960]])
    estate=dict(id='kirisato',name='霧里団地',center=[-2752,70,-1040],bounds=[-2896,-2608,-1136,-944],floor=70,
                reference='Original TV episode 05 architectural descriptions, interpreted as playable architecture',blocks=[])
    for row,z in enumerate((-1112,-1016)):
        for col,x in enumerate((-2878,-2790,-2702)):
            estate['blocks'].append(dict(id='kirisato/'+chr(65+row*3+col),bounds=[x,x+74,z,z+20],floor=70,storeys=8,rei_room=row==0 and col==0))
            road('estate_entry_'+str(row)+'_'+str(col),[[x+12,70,z-4],[x+12,70,-1136 if row==0 else -1056]],3)
    # The compact urban stop and its approach occupy street space, never a lot.
    for b in load(OUT/'surface_layout.json')['kept_plots']:
        x0,x1,z0,z1=b['bounds']
        if max(x0,-1538)<=min(x1,-1454) and max(z0,738)<=min(z1,758):raise RuntimeError('Estate interchange intersects '+b['id'])
        if max(x0,-1880)<=min(x1,-1440) and max(z0,746)<=min(z1,750):raise RuntimeError('Street tram intersects '+b['id'])
    result=dict(estate=estate,roads=roads,transit=transit)
    (OUT/'extension_plan.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'estate_transit_draft.json').write_text(json.dumps(transit,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Estate planned:6 bars,48 floors; native commuter branch',len(rails),'rails; road corridors',len(roads))
    return result

if __name__=='__main__':plan()
