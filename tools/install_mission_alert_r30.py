"""Give the command hall a separate red alert circuit on five existing ceiling fixtures."""
import argparse,json
import regional_voxels as v
from query_blocks import read_box

WORLD=v.ROOT/'run/saves/SEELE_FIELD_R30_REVIEW';OUT=v.ROOT/'artifacts/facility_r30/mission_alert'
POINTS=[(24,-421,276),(24,-412,276),(30,-415,276),(30,-416,282),(30,-412,282)]
def main(apply):
    v.WORLD=WORLD;v.OUT=OUT;p=v.Painter()
    b=read_box(WORLD,v.DIM,(24,-421,276),(30,-411,282))
    for q in POINTS:
        old=b[q];assert old=='projectseele:nerv_ceiling_light[hanging=true,lit=false]',(q,old)
        p.match((*q,*q),old,'projectseele:nerv_alert_light[hanging=true,lit=false]','r30/command_mission_alert')
    p.meta['landmarks']=[{'id':'command_mission_alert','beacons':POINTS,'purpose':'Separate red battle-alert circuit on known ceiling mounts; normal command lighting lever remains independent'}]
    p.save_plan('command_mission_alert')
    if apply:
        p.apply('command_mission_alert');f=WORLD/'facility_lighting_r30.json';data=json.loads(f.read_text());data['command_lamps']=[q for q in data['command_lamps'] if tuple(q) not in POINTS];f.write_text(json.dumps(data,indent=2))
        (WORLD/'mission_alert_r30.json').write_text(json.dumps({'revision':30,'command_beacons':POINTS},indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
