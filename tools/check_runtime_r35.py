"""Validate the complete, matching motion and articulated-body profile contract."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]

def check(directory=None,body_file=None):
    directory=Path(directory) if directory else ROOT/'run/projectseele-local-maps'
    for key in [0,1,2,3,4,'sachiel']:
        name='sachiel_gameplay_r32.json' if key=='sachiel' else f'eva_gameplay_r32_{key}.json'
        data=json.loads((directory/name).read_text())
        if data.get('schema')!=2 or data.get('rig_key')!=key or data.get('combat_foundation')!=35:raise ValueError('Incomplete R35 motion: '+name)
        for clip in ['guard','jab','cross','hook','heavy','advance','retreat','left','right']:
            if 'r32_'+clip not in data['clips']:raise ValueError('Missing '+name+': '+clip)
    body=json.loads((Path(body_file) if body_file else directory/'articulated_bodies_r35.json').read_text())
    if body.get('schema')!='projectseele.articulated-body.v1' or set(body['models'])!={'0','1','2','3','4','sachiel'}:raise ValueError('Incomplete physical body set')
    for key,model in body['models'].items():
        if len(model['bodies'])!=15 or not model.get('recovery',{}).get('frames'):raise ValueError('Incomplete physical body: '+key)
        if not all(row.get('hulls') and row.get('hull_planes') for row in model['bodies']):raise ValueError('Missing measured collision surfaces: '+key)
    print('R35: five EVA rigs and Sachiel, matched contacts, articulated impacts; protocol 39.')
if __name__=='__main__':check()
