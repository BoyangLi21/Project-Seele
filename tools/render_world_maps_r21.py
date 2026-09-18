"""Annotated maps from the same frozen blocks used by the global audit."""
import render_world_maps_r16 as r
def main():
 r.OUT=r.ROOT/'artifacts/world_repair_r21/maps';r.OUT.mkdir(parents=True,exist_ok=True)
 r.WORLD=r.ROOT/'artifacts/world_repair_r21/global_audit/world_geometry';r.REVISION='R21';r.CAGE_Z=-240
 r.UN_BOUNDS=(6190,-6770,6960,-5870);r.GEO_BOUNDS=(-950,-360,780,1040);r.CAGE_BOUNDS=(-40,-289,114,-12)
 r.NATIVE_TRACKS=r.ROOT/'artifacts/world_rebuild_r20/transit/samples11.json'
 town=r.scan('surface',(-3072,-1360,1800,1695),0,319);base=r.scan('un_base',r.UN_BOUNDS,32,255)
 geo=r.scan('geofront',r.GEO_BOUNDS,-514,-300,True);cages=r.scan('cages',r.CAGE_BOUNDS,-447,-394,True);dogma=r.scan('dogma',(-60,220,130,450),-645,-566,True)
 r.surface(town,base);r.underground(geo,cages,dogma)
 print('R21 annotated surface/underground maps ready',r.OUT,flush=True)
if __name__=='__main__':main()
