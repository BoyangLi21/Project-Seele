"""Complete two measured L-shaped interfaces without touching train or cabin envelopes."""
import regional_voxels as v
from build_transit_civil_r20 import ff
OUT=v.ROOT/'artifacts/world_rebuild_r20/legacy_connections'
def main():
    v.OUT=OUT;p=v.Painter();o='r20/cage_and_arrival_handoffs'
    def b(box,state):ff(p,box,state,o)
    b((88,-394,-265,91,-391,-260),'minecraft:air')
    b((88,-395,-265,91,-395,-260),'projectseele:nerv_floor_panel')
    b((88,-390,-265,91,-390,-260),'projectseele:nerv_machine_edge')
    b((-334,-468,765,-304,-461,770),'projectseele:nerv_structural_panel')
    b((-333,-466,766,-305,-462,769),'minecraft:air')
    b((-333,-467,766,-305,-467,769),'projectseele:nerv_floor_panel')
    # Old entrance spine on the east; new central station entry on the south.
    b((-311,-466,765,-306,-462,769),'minecraft:air')
    b((-334,-466,769,-326,-462,771),'minecraft:air')
    b((-334,-467,769,-326,-467,771),'projectseele:nerv_floor_panel')
    for x in (-325,-317):b((x,-461,767,x+1,-461,768),'projectseele:nerv_strip_light')
    b((-333,-464,765,-314,-463,765),'projectseele:clear_glass')
    p.meta.update(cage_port_joins_front_gallery=True,arrival_connection='Existing entry spine to the new central platform doorway',station_track_prism_untouched=True)
    p.save_plan('cage_and_arrival_handoffs')
if __name__=='__main__':main()
