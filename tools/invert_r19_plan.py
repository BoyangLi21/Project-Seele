"""Revert a recorded, block-only R19 candidate through the same measured writer."""
import argparse,gzip,json
import regional_voxels as vox

def main(relative,name):
    root=(vox.ROOT/'artifacts/world_repair_r19').resolve();folder=(root/relative).resolve()
    if not folder.is_relative_to(root):raise ValueError('R19 plan boundary')
    if json.loads((folder/'block_entities.json').read_text()):raise ValueError('Use an NBT-aware inverse for block entities')
    with gzip.open(folder/'ops.json.gz','rt',encoding='utf8') as f:ops=json.load(f)
    p=vox.Painter()
    for row in ops:
        if row['mode']!='match' or len(row['extra'])!=1:raise ValueError('Exact before/after operations required')
        p.match(tuple(row['box']),row['state'],row['extra'][0],'r19/revision_inverse')
    p.meta.update(source_plan=str(folder),reason='Replace a rejected candidate with a geometrically validated revision')
    vox.OUT=root/'revisions';p.apply(name)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('plan');a.add_argument('name');q=a.parse_args();main(q.plan,q.name)
