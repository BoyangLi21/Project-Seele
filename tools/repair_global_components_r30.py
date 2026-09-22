"""Resolve all detached architectural component groups with explicit ownership evidence."""
from pathlib import Path
import argparse,gzip,json
import regional_voxels as v
import repair_scan_residue_r20 as extract
from query_blocks import read_box,AIR

ROOT=v.ROOT;BASE=ROOT/'run/saves/SEELE_R30_WORLD';WORLD=ROOT/'run/saves/SEELE_FIELD_R30_REVIEW';OUT=ROOT/'artifacts/facility_r30/global_repairs';SCAN=OUT.parent/'global_scan/components'
def main(apply):
    v.WORLD=WORLD;v.OUT=OUT;extract.REVIEW=BASE;p=v.Painter();raw=json.loads((SCAN/'report.json').read_text())['candidates'];groups=json.loads((SCAN/'contact_classification.json').read_text())['groups'];decisions=[];removed={}
    reasons={
        (95,-436,-279):'Retired R20 north support frame outside current upper gallery (starts Z=-271); disconnected and nearest registered walking floor is12m away',
        (204,86,-56):'Isolated pillar remnant on recorded retired railway (0.39m from former alignment), within R29 abandoned-cut restoration, no current surface railway',
        (-675,77,-196):'Detached base of former elevated alignment,153m from current rails and32m from public walks',
        (-670,77,-196):'Detached base of the same retired elevated alignment'}
    for g in groups:
        if g['kind']!='isolated_structure':continue
        lo=tuple(g['lo']);states=set(g['states']);reason=None;action='retain'
        if lo in reasons:
            reason=reasons[lo];action='retire'
            for i in g['components']:removed.update(extract.cells(raw[i]))
        elif any('station_departure_board' in s for s in states):reason='Existing route-board position and text retained; physical ceiling/stanchion mount supplied by board_mounts receipt';action='mount'
        elif lo in [(-110,-62,150),(139,-62,128),(120,-61,291)]:reason='Registered retractable imported skyscraper at stored district depth312; legitimate ceiling-city cargo'
        elif lo==(144,-62,302):reason='Imported tower2 travel receipt: skyscraperMarker(base=(142,-61,302),index=2)=base.below().offset(2,0,0)'
        elif lo==(19,-443,313):reason='Original command-room MAGI display and luminous glazing; user explicitly preserves this layout'
        elif lo in [(1407,84,362),(1407,84,502),(1427,74,370),(1427,74,510)]:reason='R08/R21 harbour crane deck or hook with modelled structural legs/hoist; voxel contact alone is not its support model'
        elif states=={'minecraft:structure_void'}:reason='Invisible noncolliding construction receipts'
        elif states=={'projectseele:nerv_machine_edge'} and g['cells']==18:reason='Lowered hoist runway cut by gallery seam at Z=-226; reconnect only the two rail cells beneath preserved double-glass floor';action='connect'
        elif any('street_light_head' in s for s in states):reason='Existing functional street lamp; replace its missing mast down to measured stone datumY92';action='support'
        assert reason,('Unclassified architecture',g['lo'],g['hi'],g['cells'])
        decisions.append({'lo':g['lo'],'hi':g['hi'],'cells':g['cells'],'action':action,'reason':reason})
    with gzip.open(SCAN/'isolated_soil_points.json.gz','rt') as f:
        for row in json.load(f):removed[tuple(row['pos'])]=row['state']
    for q,s in removed.items():
        assert read_box(WORLD,v.DIM,q,q)[q]==s,(q,'changed since frozen scan');p.match((*q,*q),s,'minecraft:air','r30/proven_detached_residue')
    for cx in [-12,30,72]:
        for x in [cx-4,cx+4]:
            b=read_box(WORLD,v.DIM,(x,-372,-227),(x,-368,-225))
            for y in [-372,-371]:
                q=x,y,-226;assert b[q] in AIR and b[x,y,-227]=='projectseele:nerv_machine_edge' and b[x,y,-225]=='projectseele:nerv_machine_edge'
                p.match((*q,*q),b[q],'projectseele:nerv_machine_edge','r30/continuous_lowered_hoist_rail')
            assert b[x,-369,-226]=='projectseele:nerv_structural_panel'
    b=read_box(WORLD,v.DIM,(-711,92,651),(-711,98,651));assert b[-711,92,651]=='minecraft:stone' and 'street_light_head' in b[-711,98,651]
    for y in range(93,98):
        q=-711,y,651;assert b[q] in AIR;p.match((*q,*q),b[q],'projectseele:nerv_sign_post[arm=false,facing=north]','r30/existing_street_lamp_mast')
    p.meta.update(architectural_groups=len(decisions),decisions=decisions,removed_cells=len(removed),rail_gap_cells=12,street_mast_cells=5,preserved_all_board_NBT_and_runtime_actors=True)
    p.save_plan('classified_global_component_repairs')
    if apply:p.apply('classified_global_component_repairs')
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
