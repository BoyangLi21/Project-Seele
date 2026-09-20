"""Refresh native collision cases and collect every newly introduced block state."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/facility_r28';WORLD=ROOT/'run/saves/SEELE_FIELD_R28_REVIEW'

def main():
    out=ART/'validation';out.mkdir(exist_ok=True);walks=[];states=set(json.loads((WORLD/'regional_states.json').read_text()))
    for name in ('reported','airport/civil','science_underpass','finish'):
        data=json.loads((ART/name/'contract.json').read_text());walks+=data.get('walk_nodes',[])
    for path in ART.rglob('states.json'):states.update(json.loads(path.read_text()))
    # Deliberately walk both sides of the new platform, clear of doors and belts.
    for z in (118.5,137.5):
        for x in range(542,657,10):walks.append(dict(id=f'r28/airport/deck/{x}/{z}',path=[[x+.5,105,z],[x+7.5,105,z]]))
    walks=list({q['id']:q for q in walks}.values())
    (out/'affected_walk_cases.json').write_text(json.dumps(walks,ensure_ascii=False,indent=2),encoding='utf8')
    (WORLD/'r28_walk_cases.json').write_text(json.dumps(walks,ensure_ascii=False,indent=2),encoding='utf8')
    (WORLD/'regional_states.json').write_text(json.dumps(sorted(states),ensure_ascii=False),encoding='utf8')
    print('R28 native cases',len(walks),'registered block states',len(states),flush=True)

if __name__=='__main__':main()
