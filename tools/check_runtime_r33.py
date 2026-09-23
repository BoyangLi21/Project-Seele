"""Reject a partially copied R33 animation update before opening a world."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def check(directory=None):
    folder=Path(directory) if directory else ROOT/'run/projectseele-local-maps'
    for key in range(5):
        p=folder/f'eva_gameplay_r32_{key}.json';d=json.loads(p.read_text(encoding='utf8'))
        if d.get('schema')!=2 or d.get('rig_key')!=key or d.get('combat_foundation')!=33:raise ValueError('Install the complete R33 update: '+str(p))
        for name in ['guard','jab','cross','hook','heavy','advance','retreat','left','right']:
            if 'r32_'+name not in d['clips']:raise ValueError('Missing R33 action '+name)
    d=json.loads((folder/'sachiel_gameplay_r32.json').read_text(encoding='utf8'))
    if d.get('combat_foundation')!=33:raise ValueError('Sachiel R33 motion is missing')
    print('R33 runtime profiles ready: five EVA rigs and Sachiel; protocol 37.')
if __name__=='__main__':check()
