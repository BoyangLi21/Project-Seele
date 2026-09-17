"""Refresh the two established annotated maps from the final R19 world."""
import render_world_maps_r16 as render

if __name__=='__main__':
    render.OUT=render.ROOT/'artifacts/world_repair_r19/maps'
    render.OUT.mkdir(parents=True,exist_ok=True)
    render.REVISION='R19'
    render.main()
