"""Open the measured residual wall thickness behind the named U2 west portal."""
import argparse,json
import regional_voxels as vox
from query_blocks import read_box,AIR

def main(apply=False):
    vox.OUT=vox.ROOT/'artifacts/world_repair_r19/connections';p=vox.Painter()
    blocks=read_box(vox.WORLD,vox.DIM,(109,-443,-47),(114,-438,-45))
    for pos,state in blocks.items():
        x,y,z=pos
        if y==-443 and state.split('[')[0] in AIR:raise RuntimeError(('Portal support is absent',pos))
        if y not in (-442,-441,-440,-439):continue
        if state not in ('projectseele:nerv_wall_panel','projectseele:nerv_wall_datum'):continue
        p.match((*pos,*pos),state,'minecraft:air','r19/U2_portal_residual_wall')
    p.meta.update(reason='Native walk blocked behind X108 doorway at X109..112/Z-47; measured old corridor end wall remained four blocks deep',
        portal=[108,-442,-47,114,-439,-45],roof_and_floor_preserved=True)
    p.apply('U2_portal_thickness') if apply else p.save_plan('U2_portal_thickness')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');main(ap.parse_args().apply)
