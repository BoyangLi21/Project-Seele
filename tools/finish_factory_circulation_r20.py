"""Complete the relocated factory's three gallery levels and observation room."""
import json
from pathlib import Path
import regional_voxels as v
from plan_factory_r20 import FLOOR,WALL,STRUCT,GLASS,LIGHT,EDGE
OUT=v.ROOT/'artifacts/world_rebuild_r20/factory'
def main():
    v.OUT=OUT;p=v.Painter();owner='r20/factory_gallery_finish';walks=[]
    def box(b,s):p.fill(*b,s,owner,'owned')
    # The retained upper observation stop now reaches the moved wet cages.
    # This also absorbs the old observation fragments carried with the source
    # plant, instead of leaving an inaccessible partial booth near the roof.
    box((94,-371,-282,111,-363,-83),STRUCT)
    box((95,-369,-281,110,-364,-82),'minecraft:air');box((95,-370,-281,110,-370,-83),FLOOR)
    for x in (94,111):box((x,-368,-280,x,-365,-84),GLASS)
    # The plant's portal columns continue through the wall; glazing stops at
    # each structural bay rather than replacing its supports.
    for z in (-282,-250,-216):box((93,-467,z-1,95,-349,z+1),STRUCT)
    for z in range(-276,-83,24):box((111,-467,z,112,-363,z+1),STRUCT)
    for z in range(-276,-83,12):box((101,-363,z,104,-363,z+1),LIGHT)
    box((95,-369,-84,110,-364,-83),'minecraft:air')
    # The two lower service galleries end with bulkheads after their real
    # branching doors, never an open mouth into the cavern.
    for x0,x1,z,f in [(103,111,-289,-443),(95,103,-271,-395),(103,111,-42,-443),(95,103,-42,-395)]:
        box((x0,f+1,z,x1,f+5,z),WALL)
    # Upper copied cage gallery enters beside the compact lift's old landing.
    box((96,-394,-269,101,-389,-263),'minecraft:air')
    # Furnish the saved upper observer room around its existing lift access.
    for z in (-77,-65,-41,-29):
        for x in (90,91):p.put(x,-369,z,'projectseele:nerv_workstation[facing=west]',owner)
        p.put(93,-369,z,'projectseele:nerv_office_chair[facing=west]',owner)
        p.put(112,-369,z,'projectseele:nerv_storage_panel[facing=west]',owner)
    for z in (-77,-29):
        p.put(108,-369,z,'minecraft:potted_fern',owner)
    for label,pts in [('high_observation',[[103.5,-369,-70.5],[103.5,-369,-278.5]]),('middle_service',[[99.5,-394,-263.5],[99.5,-394,-60.5],[101.5,-394,-60.5],[101.5,-394,-46.5]]),('lower_service',[[107.5,-442,-284.5],[107.5,-442,-44.5]]),('station_link',[[107.5,-442,-44.5],[130.5,-442,-44.5]])]:
        walks.extend([dict(id='r20/factory/'+label,path=pts),dict(id='r20/factory/'+label+'/return',path=list(reversed(pts)))])
    p.meta.update(walk_nodes=walks,upper_observation_connected_to_moved_cages=True,structural_portals_preserved=True,closed_service_ends=4)
    p.save_plan('gallery_and_observer_finish')
if __name__=='__main__':main()
