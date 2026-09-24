"""Replace floating rack actuators with fixed housings and telescoping rams."""
from pathlib import Path
import json,shutil
import build_tv_machinery_r16 as m
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/combat_rebuild_r35/facility'
FILE=ROOT/'src/main/resources/assets/projectseele/mesh/tv_facilities_r16.json'
BLACK=0x171c23;EDGE=0x3b434d;STEEL=0x9aa6b0

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    backup=OUT/'rack_before.json'
    if not backup.exists():shutil.copy2(FILE,backup)
    data=json.loads(backup.read_text());m.PARTS.clear();mounts=json.loads((ROOT/'artifacts/facility_r28/machinery/contact_measurements.json').read_text())
    m.use('carrier_support_members')
    # Crossmembers sit at the actuator bearings and reel mounting plate,
    # overlapping the two continuous load columns at x=+/-6.25.
    for y in (17.,36.8,43.,47.):
        m.housing(-6.62,y-.38,9.60,13.24,.76,1.76,.14,BLACK)
        for x in (-6.25,6.25):
            m.housing(x-.52,y-.65,9.24,1.04,1.3,.48,.14,EDGE)
            m.bolts(x-.36,y-.47,9.20,.72,.94)
    # Deck guides remain fixed while the foot clamps retract along them.
    m.use('carrier_deck_guides')
    for x in (-6.05,-.45,.45,6.05):
        m.housing(x-.18,.02,-11.5,.36,.26,15,.08,BLACK)
    m.use('carrier_actuator_housings')
    for row in [r for r in mounts if r['unit']==0]:
        x,y,_=row['centre'];m.cylinder((x,y,9.3),(x,y,11.2),.48,EDGE,24)
        m.housing(x-.66,y-.64,10.12,1.32,1.28,.46,.18,BLACK)
    m.use('carrier_ram_unit');m.cylinder((0,0,0),(0,0,1),.28,STEEL,24)
    bindings={}
    for unit in range(3):
        m.use('carrier_contact_pads_'+str(unit));bindings[str(unit)]=[]
        for row in [r for r in mounts if r['unit']==unit]:
            x,y,z=row['centre'];m.housing(x-.58,y-.6,z,1.16,1.2,.32,.16,BLACK)
            m.housing(x-.68,y-.72,z+.32,1.36,1.44,.28,.20,EDGE)
            m.bolts(x-.45,y-.45,z-.018,.9,.9)
            bindings[str(unit)].append([x,y,z+.6,10.25])
    data['parts'].update(m.PARTS);data['carrier_actuator_mounts']=bindings;data['carrier_attachment_revision']=35
    FILE.write_text(json.dumps(data,separators=(',',':')))
    report={'fixed_crossmember_y':[17,36.8,43,47],'column_x':[-6.25,6.25],'actuators':bindings,'stroke_policy':'Pad and ram tip move; ram end and housing stay at their physical beam mount','world_blocks_changed':0}
    (OUT/'carrier_connections.json').write_text(json.dumps(report,indent=2));print('18 pad assemblies now have fixed bearings and variable-length connecting rods')
if __name__=='__main__':main()
