"""Register bounded scene captures and affected native walking checks."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1];WORLD=ROOT/'run/saves/SEELE_R24_TV_REVIEW';OUT=ROOT/'artifacts/facility_r24/validation'
def main():
    walks=[]
    for name in ('stations','station_decks','shops','pyramid_life','kirisato_life','city_frontages'):
        d=json.loads((ROOT/'artifacts/facility_r24'/name/'contract.json').read_text(encoding='utf8'));walks.extend(d['walk_nodes'])
    assert len({w['id'] for w in walks})==len(walks)
    (WORLD/'r24_walk_cases.json').write_text(json.dumps(walks,ensure_ascii=False,indent=2),encoding='utf8')
    (OUT/'affected_walk_cases.json').write_text(json.dumps(walks,ensure_ascii=False,indent=2),encoding='utf8')
    states=json.loads((WORLD/'regional_states.json').read_text(encoding='utf8'))
    kinds=['public_phone','notice_board','utility_box','pipe_run','bollard','hydrant','wall_clock','drinking_fountain','cafe_counter','cafe_table','cafe_stool','newspaper_rack','coffee_machine','shop_sign','document_cart','tech_bench','parked_bicycle','vending_machine','letter_box']
    states=sorted(set(states)|{f'projectseele:period_fixture[facing={f},kind={k}]' for f in ('north','south','east','west') for k in kinds})
    states.append('projectseele:period_station_floor')
    states.extend(['projectseele:station_drain','projectseele:period_fixture_part[offset=1]','projectseele:period_fixture_part[offset=2]'])
    (WORLD/'regional_states.json').write_text(json.dumps(states,ensure_ascii=False),encoding='utf8')
    shots=[]
    def shot(name,eye,target,distance=6):shots.append(dict(name=name,eye=eye,target=target,renderDistance=distance,warmupTicks=160))
    shot('tokyo_concourse_shops',[-133,84,-178],[-120,82.6,-186])
    shot('tokyo_cafe_interior',[-122.5,82.62,-185.5],[-125,81.9,-186.5])
    shot('tokyo_public_phone',[-150,96.62,-160],[-147.5,96.3,-155.5])
    shot('tokyo_deck_repaired',[-173,96.62,-157],[-118,95.5,-157])
    shot('hakone_period_shop',[-1455,108,630],[-1446,106.6,622])
    shot('kirisato_period_shop',[-2729,74,-954],[-2718,72.6,-974])
    shot('nerv_station_period_shop',[-373,84,678],[-360,82.6,670])
    shot('shop_enamel_close',[-123,83,-180],[-122.5,84.4,-182.9])
    shot('kirisato_bicycle_shelter',[-2869,73,-1121],[-2872,72,-1114])
    shot('kirisato_residential_entrance',[-2860,76,-1125],[-2869,74,-1111])
    shot('tokyo_bookshop_frontage',[-155,84,-292],[-144,83,-305])
    shot('tokyo_bookshop_equipment',[-133,82.62,-301],[-134.5,81.95,-305.9])
    shot('hakone_stationery_frontage',[-1542,108,624],[-1528,107,610])
    shot('s1_bridge_underside_clean',[-960,111,653],[-945,113,680])
    shot('hakone_retired_alignment_clean',[-1750,139,610],[-1715,126,645])
    room_data=json.loads((ROOT/'artifacts/facility_r24/pyramid_life/contract.json').read_text(encoding='utf8'))
    room_specs=json.loads((ROOT/'artifacts/first_battle_world_r10/world_art/pyramid_rooms/places.json').read_text(encoding='utf8'))['rooms']
    for purpose in ('CAFETERIA','ANALYSIS','MEDICAL','ARCHIVE','QUARTERS','SUPPLIES'):
        room=next(r for r in room_specs if r['purpose']==purpose);items=[q for q in room_data['placed'] if q['room']==room['id']]
        if not items:continue
        focus=items[0];x,y,z=focus['position'];direction={'north':(0,-1),'south':(0,1),'west':(-1,0),'east':(1,0)}[focus['facing']]
        dx,dz=direction;shot('pyramid_'+purpose.lower(),[x+.5+dx*3.5,y+1.62,z+.5+dz*3.5],[x+.5,y+.9,z+.5])
    previous=json.loads((ROOT/'artifacts/facility_r23/validation/client_tour_receipt.json').read_text(encoding='utf8'))
    for old in previous:
        if old['name'] in ('observation_front','observation_rear'):
            shots.append({k:v for k,v in old.items() if k in ('name','eye','target','renderDistance','warmupTicks')})
    (ROOT/'run/projectseele-local-maps/r24_worldtour.json').write_text(json.dumps(shots,ensure_ascii=False,indent=2),encoding='utf8')
    (OUT/'worldtour.json').write_text(json.dumps(shots,ensure_ascii=False,indent=2),encoding='utf8');print('Affected native routes',len(walks),'scene captures',len(shots))
if __name__=='__main__':main()
