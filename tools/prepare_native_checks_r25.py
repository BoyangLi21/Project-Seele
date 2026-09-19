"""Cases cover the user's endpoints and complete newly authored connectors."""
from pathlib import Path
import json,shutil
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/facility_r25';WORLD=ROOT/'run/saves/SEELE_R25_REVIEW'
def main():
 out=ART/'validation';out.mkdir(parents=True,exist_ok=True);walks=[];states=set(json.loads((WORLD/'regional_states.json').read_text()))
 for name in ('command_links','lifts','route_repairs','walkways','station_maps','port_finish'):
  d=json.loads((ART/name/'contract.json').read_text(encoding='utf8'));walks.extend(d.get('walk_nodes',[]))
  for path in (ART/name).glob('*/states.json'):states.update(json.loads(path.read_text()))
 assert len({q['id'] for q in walks})==len(walks)
 (WORLD/'r25_walk_cases.json').write_text(json.dumps(walks,ensure_ascii=False,indent=2),encoding='utf8')
 (out/'affected_walk_cases.json').write_text(json.dumps(walks,ensure_ascii=False,indent=2),encoding='utf8')
 (WORLD/'regional_states.json').write_text(json.dumps(sorted(states),ensure_ascii=False),encoding='utf8')
 print('Prepared',len(walks),'native routes;',len(states),'block states')
if __name__=='__main__':main()
