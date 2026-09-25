"""Check the reviewed jaw, two-stage chain, feral profiles, and material set."""
from pathlib import Path
import contextlib,io,json
from check_runtime_r36 import check as check_foundation
ROOT=Path(__file__).resolve().parents[1]

def check(directory=None,assets=None):
    directory=Path(directory) if directory else ROOT/'run/projectseele-local-maps'
    assets=Path(assets) if assets else ROOT/'run/resourcepacks/eva_real_model/assets'
    with contextlib.redirect_stdout(io.StringIO()):check_foundation(directory)
    for key in range(5):
        data=json.loads((directory/f'eva_gameplay_r32_{key}.json').read_text())
        if data.get('combat_revision')!=37 or data.get('ordinary_sequence')!=['jab','cross']:raise ValueError('Missing R37 two-stage chain')
        if key==1:
            for clip in ['berserk_l','berserk_r','berserk_upper','berserk_drive','berserk_down','berserk_guard','berserk_run']:
                if 'r32_'+clip not in data['clips']:raise ValueError('Missing feral phrase '+clip)
    mesh=json.loads((assets/'projectseele/mesh/eva_unit01.mesh.json').read_text())
    geo=json.loads((assets/'projectseele/geo/eva_unit01.geo.json').read_text())
    if mesh.get('r37_mouth',{}).get('contract')!='tv2-serrated-jaw':raise ValueError('The rejected denture must not be installed')
    if mesh['r37_mouth'].get('seam_revision')!=2:raise ValueError('The refined interlocking jaw seam is missing')
    names=[b['name'] for b in geo['minecraft:geometry'][0]['bones']]
    if len(names)!=len(set(names)) or 'r37_jaw' not in names:raise ValueError('Invalid jaw skeleton')
    print('R37 TV jaw and feral profiles ready; protocol 42. Visual acceptance remains with the user.')
if __name__=='__main__':check()
