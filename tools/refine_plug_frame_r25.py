"""Build the two owned frame assemblies around the measured capsule envelope."""
from pathlib import Path
import json,hashlib
import build_tv_machinery_r16 as b
ROOT=b.ROOT;OUT=ROOT/'artifacts/facility_r25/plug_clearance'
def main():
 OUT.mkdir(parents=True,exist_ok=True);source=b.ASSETS/'mesh/tv_facilities_r16.json';before=OUT/'machinery_before.json'
 if not before.exists():before.write_bytes(source.read_bytes())
 data=json.loads(before.read_text());b.cage();b.carrier()
 for key in ('cage_frame','carrier_spine'):data['parts'][key]=b.PARTS[key]
 old=json.loads(before.read_text());assert all(value==old['parts'][key] for key,value in data['parts'].items() if key not in ('cage_frame','carrier_spine'))
 (OUT/'tv_facilities_r25_candidate.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf8')
 print('Raised cage/carrying-frame crowns, open dorsal service window; other assemblies unchanged')
if __name__=='__main__':main()
