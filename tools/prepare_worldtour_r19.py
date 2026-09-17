"""Camera evidence uses the rendered review copy and exact installed board positions."""
import json,math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def main():
    shots=[]
    def shot(name,eye,target):shots.append(dict(name=name,eye=eye,target=target))
    boards=json.loads((ROOT/'artifacts/world_repair_r19/stations/display_clearance/places.json').read_text())['boards']
    for key in ('C1_tokyo_central','U1_geo_arrival','U2_hangar','S2_kirisato','P1_port'):
        matches=[b for b in boards if b['id'].startswith(key+'/')]
        if not matches:continue
        b=matches[0];x,y,z=b['pos'];dx,dz={'north':(0,-1),'south':(0,1),'west':(-1,0),'east':(1,0)}[b['facing']]
        shot('board_'+key,[x+.5+dx*5,y+.2,z+.5+dz*5],[x+.5,y+.65,z+.5])
    shot('C1_reported_cut',[-615,106,660],[-602,87,682])
    shot('shore_reported_seam',[493,77,347],[513,61,370])
    shot('arrival_tree_clearance',[-310,-461,787],[-310,-465,765])
    shot('escalator_transition',[32,-401.5,254.5],[27.5,-402.5,259.5])
    shot('dogma_lift',[12.5,-563.8,265.5],[12.5,-564.8,256])
    shot('pyramid_stair_join',[112.5,-446.4,255.8],[112.5,-442,248.5])
    shot('hangar_station_join',[118.5,-440.4,-16.5],[150.5,-440.4,-21.5])
    shot('upper_walkway',[101.5,-392.9,-98],[101.5,-393,20])
    shot('hangar_amber_lcl',[36,-389,-116],[30,-397,-94])
    shot('launch_transfer_before',[103,-367,-135],[30,-423,-60])
    roster=json.loads((ROOT/'run/saves/SEELE_TV_WORLD_PREVIEW_20260906/nerv_staff_r15.json').read_text(encoding='utf8'))['stations']
    for name in ('misato','ritsuko','maya','fuyutsuki'):
        s=next((s for s in roster if s['id']==name),None)
        if s:
            x,y,z=s['feet'];yaw=math.radians(s['yaw']);dx,dz=-math.sin(yaw),math.cos(yaw)
            shot('staff_'+name,[x+.5+dx*3.2,y+1.75,z+.5+dz*3.2],[x+.5,y+1.35,z+.5])
    dest=ROOT/'run/projectseele-local-maps/r19_worldtour.json';dest.write_text(json.dumps(shots,ensure_ascii=False,indent=2),encoding='utf8')
    print('Camera shots',len(shots))

if __name__=='__main__':main()
