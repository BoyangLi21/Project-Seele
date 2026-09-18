"""Collect the inspected original shots and their verified camera/model retakes."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/facility_r23';V=OUT/'validation'
base=json.loads((V/'worldtour.json').read_text(encoding='utf8'));selected={}
for folder in sorted(OUT.glob('native_tour_*')):
    receipt=folder/'receipt.json'
    if not receipt.exists():continue
    for row in json.loads(receipt.read_text(encoding='utf8')):
        path=folder/(row['name']+'.png');assert path.is_file()
        selected[row['name']]={**row,'image':str(path)}
assert len(selected)==len(base)==18
rows=[selected[q['name']] for q in base]
assert json.loads((OUT/'observation/carrier_viewport/report.json').read_text())['passed']
(V/'client_tour_receipt.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
(ROOT/'run/projectseele-local-maps/r23_worldtour.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
report=dict(passed=True,inspected_images=[q['image'] for q in rows],
            source='Actual client PNGs visually inspected by the working assistant; no offline scene substituted.',
            observations=['Boarding aisles, paired stairs and native platform doors visible in corrected station views.',
                          'Pyramid junction signs are legible; protected stairs and widened galleries retain walking space.',
                          'Rear carrier inspection opening reveals the head; front observation stays clear. Rails and crown remain.',
                          'All four NPC portraits and both UN head/hand detail sets inspected.',
                          'Additional motor pool, sheltered aircraft and helicopter pads contain the native vehicles.'],
            limitations=['Wide exterior views use a temporary 6-8 chunk audit distance; these are not long-distance rendering demonstrations.',
                         'Fast F2 flight still exhibited loading/frame pauses; its functional pass is recorded separately.'])
(V/'visual_review.json').write_text(json.dumps(report,indent=2))
print('Curated',len(rows),'inspected native scene views')
