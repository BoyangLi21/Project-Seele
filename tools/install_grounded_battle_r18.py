"""Promote the exact candidate checked offline and exercised in native playback."""
from pathlib import Path
import hashlib,json,shutil,datetime
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/grounded_battle_r18'

def main():
    source=OUT/'candidate_final.json';sha=hashlib.sha256(source.read_bytes()).hexdigest()
    surface=json.loads((OUT/'surface_audit.json').read_text());geometry=json.loads((OUT/'paired_geometry_audit.json').read_text())
    native=json.loads((OUT/'native_full_checks.json').read_text());movie=json.loads((OUT/'native_movie_checks.json').read_text())
    assert surface['passed'] and surface['sha256']==sha
    assert geometry['passed'] and geometry['source_sha256']==sha
    assert native['passed'] and not native['failure'] and len(native['checks'])>=18 and all(r['passed'] for r in native['checks'])
    assert movie['passed'] and not movie['failure'] and movie['clip_sha256']==sha
    target=ROOT/'run/projectseele-local-maps/first_battle_r18.json'
    if target.exists():shutil.copy2(target,OUT/('previous_r18_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.json'))
    temporary=target.with_suffix('.tmp');shutil.copy2(source,temporary);temporary.replace(target)
    (OUT/'installed.json').write_text(json.dumps({'file':str(target),'sha256':sha,'native_checks':len(native['checks']),'movie_checks':len(movie['checks']),'geometry_samples':geometry['samples']},indent=2),encoding='utf8')
    print('Installed verified R18 clip',sha)

if __name__=='__main__':main()
