"""Measure the final R20 world, including the relocated cages and empty UN annex."""
import render_world_maps_r16 as render
if __name__=='__main__':
    render.OUT=render.ROOT/'artifacts/world_rebuild_r20/maps'
    render.OUT.mkdir(parents=True,exist_ok=True)
    render.REVISION='R20';render.CAGE_Z=-240
    render.UN_BOUNDS=(6190,-6770,6960,-5870)
    render.GEO_BOUNDS=(-950,-360,780,1040)
    render.CAGE_BOUNDS=(-40,-289,114,-12)
    render.NATIVE_TRACKS=render.ROOT/'artifacts/world_rebuild_r20/transit/samples11.json'
    render.main()
