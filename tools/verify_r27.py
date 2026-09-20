"""Fresh native city/button and F5 witnesses; preserve original user work."""
from pathlib import Path
import datetime,hashlib,json,math

ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/facility_r27';WORLD=ROOT/'run/saves/SEELE_R27_REVIEW'

def main():
    baseline=json.loads((ART/'baseline.json').read_text(encoding='utf8'))
    for name,sha in baseline['original_user_files'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
    assert not (WORLD/'r27_city_failure.txt').exists()
    assert not (WORLD/'r20_factory_failure.txt').exists()
    city=json.loads((WORLD/'r27_city_pass.json').read_text());assert city['passed'] and city['physical_presses']==2 and city['max_depth']>0
    cycle=json.loads((WORLD/'r20_factory_pass.json').read_text());assert len(cycle)>100
    assert (WORLD/'r20_factory_pass.json').stat().st_mtime>(ART/'baseline.json').stat().st_mtime
    folders=sorted(ART.glob('native_cycle_*'));folder=folders[-1]
    video=json.loads((folder/'frames.json').read_text());assert not video['write_failure']
    samples=[];types=set()
    for f in video['frames']:
        if not (f.get('carrier') or f.get('locked') and f.get('locked_capsule')) or f['phase'] not in ('prepare_transfer','launch','recover_from_sideways'):continue
        # Factory review fixes pilot pitch at +12; vanilla mirrored F5 negates it.
        radius=math.hypot(f['camera_x']-f['eva_x'],f['camera_z']-f['eva_z'])
        sign=-1 if f['camera_type']=='THIRD_PERSON_FRONT' else 1
        pivot=f['camera_y']-f['eva_y']-sign*radius*math.tan(math.radians(12))
        samples.append(dict(file=f['file'],phase=f['phase'],type=f['camera_type'],pivot=pivot,radius=radius))
        types.add(f['camera_type'])
    assert len(samples)>200 and len(types)==2,(len(samples),types)
    bad=[s for s in samples if not 47.7<s['pivot']<48.3]
    assert not bad,bad[:10]
    report=dict(passed=True,city=city,cycle_samples=len(cycle),camera_frames=len(samples),camera_pivot_range=[min(s['pivot'] for s in samples),max(s['pivot'] for s in samples)],native_folder=str(folder),scope='Native Fuyutsuki physical city buttons, nonzero building descent and return; actual occupied prepare/launch/recover; both real F5 camera directions during locked machinery. No cinematic camera override.',checked=datetime.datetime.now().astimezone().isoformat())
    (ART/'camera_samples.json').write_text(json.dumps(samples,indent=2))
    (ART/'acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
