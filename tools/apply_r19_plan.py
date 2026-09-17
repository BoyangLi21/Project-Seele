"""Apply an already measured R19 plan without repeating the whole-world survey."""
import argparse,gzip,json
from pathlib import Path
import nbtlib
import regional_voxels as vox

def main(relative):
    root=(vox.ROOT/'artifacts/world_repair_r19').resolve()
    folder=(root/relative).resolve()
    if not folder.is_relative_to(root):raise ValueError('Plan must remain inside the R19 artifact directory')
    if not (root/'baseline.json').exists():raise RuntimeError('Cold baseline is required')
    with gzip.open(folder/'ops.json.gz','rt',encoding='utf8') as stream:ops=json.load(stream)
    p=vox.Painter()
    for row in ops:
        p.fill(*row['box'],row['state'],row['owner'],row['mode'])
        p.ops[-1]=vox.Op(tuple(row['box']),row['state'],row['owner'],row['mode'],tuple(row.get('extra',())))
    p.meta=json.loads((folder/'places.json').read_text(encoding='utf8'))
    p.keep_boxes=json.loads((folder/'protected.json').read_text(encoding='utf8'))
    for row in json.loads((folder/'block_entities.json').read_text(encoding='utf8')):
        p.block_entities[tuple(row['pos'])]=nbtlib.parse_nbt(row['snbt'])
    vox.OUT=folder.parent
    p.apply(folder.name)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('plan');main(ap.parse_args().plan)
