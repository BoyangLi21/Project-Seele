"""Promote the pinned R31 UN pair only, with JVM exclusion, backups and bounded JSON merges.

Default mode checks the frozen plan. --apply additionally requires the real
native UN mechanics pass. This tool never touches a save, NERV asset, or source.
"""
from pathlib import Path
from contextlib import contextmanager
import argparse,copy,datetime,hashlib,json,math,os,re,shutil,subprocess,tempfile
import msvcrt

ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/facility_r31/models';STAGING=ART/'staging.json';PLAN=ART/'promotion_expected.json'
REVIEW=ROOT/'run/resourcepacks/eva_un_r31_review/assets/projectseele';MAIN=ROOT/'run/resourcepacks/eva_real_model/assets/projectseele';MAPS=ROOT/'run/projectseele-local-maps'
MODELS=('eva_prototype','eva_un01');GROUPS=('rigs','rig_support','eye_positions','carrier_hulls')
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf8'))
def json_bytes(value):return (json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n').encode('utf8')
def bounded(path,root,must_exist=False):
    path=Path(path).resolve(strict=must_exist);root=Path(root).resolve()
    if not path.is_relative_to(root):raise RuntimeError('Path escaped its designated root: '+str(path))
    return path
def no_minecraft():
    # Read-only inspection. Do not log complete JVM arguments: launchers may
    # include the player's authentication token there.
    command="@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'java.exe' -or $_.Name -eq 'javaw.exe' } | Select-Object ProcessId,Name,CommandLine) | ConvertTo-Json -Compress"
    result=subprocess.run(['powershell','-NoProfile','-Command',command],capture_output=True,text=True,encoding='utf8',errors='replace')
    if result.returncode:raise RuntimeError('Cannot inspect JVM processes; refusing model promotion.')
    rows=json.loads(result.stdout.strip() or '[]');rows=rows if isinstance(rows,list) else [rows]
    marker=re.compile(r'minecraft|bootstraplauncher|cpw[.]mods[.]modlauncher|fabricmc|quiltmc|client-[^\r\n]*[.]args|(?:^|[\\/\s\"])(?:server|forge)[^\s\"]*[.]jar|(?:win|unix)_args[.]txt',re.I)
    blocked=[]
    for process in rows:
        args=process.get('CommandLine')
        if not args:blocked.append((process['ProcessId'],'unreadable JVM command line'));continue
        if marker.search(args):blocked.append((process['ProcessId'],'Minecraft launch signature'));continue
        # An opaque @argfile can conceal the main class. Fail closed if its
        # contents cannot be located, rather than assuming that Java is idle.
        for quoted,bare in re.findall(r'@(?:"([^"]+)"|([^\s]+))',args):
            raw=Path(quoted or bare);candidates=[raw] if raw.is_absolute() else [ROOT/raw,ROOT/'run'/raw]
            file=next((p for p in candidates if p.is_file()),None)
            if file is None:blocked.append((process['ProcessId'],'unresolved Java argument file'));break
            if marker.search(file.read_text(encoding='utf8',errors='replace')):blocked.append((process['ProcessId'],'Minecraft argument file'));break
    if blocked:raise RuntimeError('Minecraft or an uninspectable JVM is running; close it before promotion. PIDs/reasons: '+repr(blocked))
@contextmanager
def lock():
    ART.mkdir(parents=True,exist_ok=True)
    with (ART/'.promotion.lock').open('a+b') as f:
        f.seek(0,2)
        if f.tell()==0:f.write(b'0');f.flush()
        f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
        try:yield
        finally:f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
def source_inventory():
    stage=read(STAGING)
    if Path(stage['pack']).resolve()!=REVIEW.parents[1].resolve():raise RuntimeError('Unexpected R31 review-pack root')
    body=bounded(stage['body'],MAPS,True);dorsal=bounded(stage['dorsal'],MAPS,True)
    if body.name!='eva_body_r31_review.json' or dorsal.name!='eva_dorsal_r31_review.json':raise RuntimeError('Unexpected review profile names')
    if sha(body)!=stage['body_sha256'] or sha(dorsal)!=stage['dorsal_sha256']:raise RuntimeError('Review body/dorsal changed after staging')
    manifest_path=bounded(REVIEW/'eva/un_models_r30.json',REVIEW,True);manifest=read(manifest_path)
    if manifest.get('schema')!='projectseele.un-models-r30.v1' or manifest.get('generation')!='R31' or set(manifest.get('models',{}))!=set(MODELS):raise RuntimeError('Not the bounded R31 pair manifest')
    files=[]
    for name in MODELS:
        model=manifest['models'][name];core={'mesh':f'mesh/{name}.mesh.json','geo':f'geo/{name}.geo.json','animation':f'animations/{name}.animation.json','texture':f'textures/entity/{name}.png'}
        expected_pbr={f'textures/entity/{name}{suffix}.png' for suffix in ('_mr','_s','_n','_eyes')}
        if set(model['pbr'])!=expected_pbr:raise RuntimeError('Unexpected PBR file list for '+name)
        for key,relative in core.items():files.append((relative,model['sha256'][key]))
        files.extend(sorted(model['pbr'].items()))
    files.append(('eva/un_models_r30.json',sha(manifest_path)))
    pack_meta=bounded(REVIEW.parents[1]/'pack.mcmeta',REVIEW.parents[1],True)
    expected={str(STAGING.resolve()):sha(STAGING),str(pack_meta):sha(pack_meta),str(body):sha(body),str(dorsal):sha(dorsal)}
    for relative,digest in files:
        source=bounded(REVIEW/relative,REVIEW,True)
        if sha(source)!=digest:raise RuntimeError('Source does not match manifest: '+relative)
        expected[str(source)]=digest
    return stage,manifest,files,body,dorsal,expected
def freeze():
    _,_,_,_,_,expected=source_inventory()
    plan={'schema':'projectseele.un-promotion-plan-r31.v1','revision':'R31','frozenAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'expected_sources':expected}
    PLAN.write_bytes(json_bytes(plan));print('Frozen source plan: '+str(PLAN))
def verify_plan(expected):
    if not PLAN.is_file():raise RuntimeError('Freeze the reviewed batch first with --freeze.')
    plan=read(PLAN)
    if plan.get('schema')!='projectseele.un-promotion-plan-r31.v1' or plan.get('expected_sources')!=expected:raise RuntimeError('A source or its staged manifest changed after the frozen promotion plan; rerun the affected review before freezing a new batch.')
    for path,digest in expected.items():
        if sha(path)!=digest:raise RuntimeError('Frozen source changed: '+path)
def strip_un_body(value):
    result=copy.deepcopy(value)
    for group in GROUPS:
        for key in ('3','4'):result.get(group,{}).pop(key,None)
    return result
def strip_un_dorsal(value):
    result=copy.deepcopy(value)
    for name in MODELS:result.get('profiles',{}).pop(name,None)
    return result
def merged_profiles(review_body,review_dorsal):
    body_path=bounded(MAPS/'eva_body_r25.json',MAPS,True);dorsal_path=bounded(MAPS/'eva_dorsal_r30.json',MAPS,True)
    body_bytes=body_path.read_bytes();dorsal_bytes=dorsal_path.read_bytes();before_body=json.loads(body_bytes.decode('utf8'));before_dorsal=json.loads(dorsal_bytes.decode('utf8'));body=copy.deepcopy(before_body);dorsal=copy.deepcopy(before_dorsal)
    source_body=read(review_body);source_dorsal=read(review_dorsal)
    for group in GROUPS:
        for key in ('3','4'):
            if key not in source_body.get(group,{}):raise RuntimeError('Missing reviewed UN profile: '+group+'/'+key)
            body.setdefault(group,{})[key]=copy.deepcopy(source_body[group][key])
    for name in MODELS:dorsal.setdefault('profiles',{})[name]=copy.deepcopy(source_dorsal['profiles'][name])
    if strip_un_body(before_body)!=strip_un_body(body) or strip_un_dorsal(before_dorsal)!=strip_un_dorsal(dorsal):raise RuntimeError('A non-UN body or dorsal field would change')
    return [(body_path,json_bytes(body),hashlib.sha256(body_bytes).hexdigest()),(dorsal_path,json_bytes(dorsal),hashlib.sha256(dorsal_bytes).hexdigest())],before_body,before_dorsal
def temp_bytes(destination,blob=None,source=None):
    destination.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.'+destination.name+'.r31-',dir=destination.parent);os.close(fd);temp=Path(name)
    try:
        if source is not None:shutil.copyfile(source,temp)
        else:temp.write_bytes(blob)
        with temp.open('r+b') as f:f.flush();os.fsync(f.fileno())
        return temp
    except Exception:temp.unlink(missing_ok=True);raise
def apply(evidence,reset_evidence=None):
    stage,manifest,files,body_source,dorsal_source,expected=source_inventory();verify_plan(expected)
    evidence=Path(evidence);evidence=bounded(evidence if evidence.is_absolute() else ROOT/evidence,ROOT,True);proof=read(evidence)
    if proof.get('passed') is not True or any(proof.get('original_unit_retained_'+str(i)) is not True for i in (0,1)):raise RuntimeError('Supply the real passing R31 UN mechanics report with both original identities retained')
    # Earlier mechanics reports could say passed without gating the actual
    # rendered body-to-capsule error. A 22.69 m mismatch exposed that gap.
    if proof.get('transport_requested') is not True:raise RuntimeError('The promotion evidence must include the original airlift')
    media=Path(proof['media']);media=media if media.is_absolute() else ROOT/'run'/media
    visual_path=bounded(media/'render_witnesses.json',ROOT,True);visual=read(visual_path)
    if visual.get('gate_revision',0)<3 or visual.get('client_error') or visual.get('transport_orientation')!='face_down':raise RuntimeError('Need the face-down native gate with actual cradle/head draw, not a legacy false-pass report')
    sockets=visual.get('transport_socket_frames',[])
    if len(sockets)<30 or sum(38<row.get('pitch',-1)<52 for row in sockets)<3 or sum(row.get('pitch',-1)>89 for row in sockets)<3:raise RuntimeError('Insufficient actual 45/90-degree socket draw samples')
    errors=[float(row['actual_mesh_to_capsule_error']) for row in sockets]
    if not all(math.isfinite(error) and 0<=error<=.25 for error in errors):raise RuntimeError('Actual mesh/capsule alignment failed; do not promote')
    cradles=visual.get('cradle_draw_frames',[])
    if visual.get('actual_cradle_draw_samples',0)<30 or len(cradles)<30 or any(row.get('submitted_nondegenerate_triangles',0)<=0 or row.get('submitted_rod_segments')!=8 for row in cradles):raise RuntimeError('Cradle and its eight rod segments must actually submit visible geometry')
    heads=[row for row in visual.get('head_facing_frames',[]) if row.get('signal_pitch',-1)>89]
    if visual.get('actual_90deg_head_facing_samples',0)<3 or len(heads)<3 or not (-1.0001<=visual.get('maximum_90deg_head_forward_y',1)<-.9):raise RuntimeError('Missing face-down cruise evidence from the actual rendered head')
    if any(len(row.get('actual_head_front_world',[]))!=3 or not (-1.0001<=row['actual_head_front_world'][1]<-.9) for row in heads):raise RuntimeError('Rendered head did not face the ground throughout horizontal cruise')
    photos={row['photo']:row for row in visual.get('actual_draw_photo_frames',[])}
    for name in ('horizontal_00_clamp','horizontal_01_45deg','horizontal_02_90deg','horizontal_03_unload'):
        row=photos.get(name,{})
        if row.get('same_frame_eva_mesh_draw') is not True or row.get('same_frame_aircraft_mesh_draw') is not True or not (visual_path.parent/(name+'.png')).is_file():raise RuntimeError('Missing same-frame aircraft/body visual evidence: '+name)
        if row.get('same_frame_cradle_mesh_draw') is not True or row.get('submitted_cradle_triangles',0)<=0 or row.get('submitted_rod_segments')!=8:raise RuntimeError('Missing actual supporting cradle/rods in photo: '+name)
        if name=='horizontal_02_90deg' and (row.get('same_frame_head_mesh_draw') is not True or len(row.get('actual_head_front_world',[]))!=3 or row['actual_head_front_world'][1]>=-.9):raise RuntimeError('The cruise photograph does not show the actual face-down head')
    reset_evidence=Path(reset_evidence) if reset_evidence is not None else ART.parent/'mechanics_functional_pass_before_socket_fix.json'
    reset_evidence=bounded(reset_evidence if reset_evidence.is_absolute() else ROOT/reset_evidence,ROOT,True);reset=read(reset_evidence)
    reset_fields=('same_original_capsule_','real_original_ride_chain_','reset_state_cleared_','dock_canonical_','original_unit_retained_')
    if reset.get('passed') is not True or any(reset.get(prefix+str(i)) is not True for prefix in reset_fields for i in (0,1)):raise RuntimeError('Need the separate two-UN reset/capsule functional evidence; transport-only is not reset coverage')
    if evidence.stat().st_mtime+1<max(Path(p).stat().st_mtime for p in expected):raise RuntimeError('Native report predates this source batch')
    updates,before_body,before_dorsal=merged_profiles(body_source,dorsal_source)
    assets=[(bounded(MAIN/rel,MAIN),bounded(REVIEW/rel,REVIEW,True),digest) for rel,digest in files]
    backup=bounded(ART/'promotion_backups'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'),ART);backup.mkdir(parents=True,exist_ok=False)
    jobs=[];receipts=[];installed=[]
    for destination,source,digest in assets:jobs.append({'destination':destination,'source':source,'digest':digest})
    for destination,blob,before in updates:jobs.append({'destination':destination,'blob':blob,'digest':hashlib.sha256(blob).hexdigest(),'expectedBefore':before})
    try:
        for job in jobs:
            destination=job['destination'];relative=destination.relative_to(ROOT);saved=backup/'before'/relative;old=sha(destination) if destination.exists() else None
            if 'expectedBefore' in job and old!=job['expectedBefore']:raise RuntimeError('Profile changed while preparing its bounded merge: '+str(relative))
            if old is not None:
                saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(destination,saved)
                if sha(saved)!=old:raise RuntimeError('Backup failed: '+str(relative))
            job['backup']=saved;job['before']=old
            temp=temp_bytes(destination,blob=job.get('blob'),source=job.get('source'));job['temp']=temp
            if sha(temp)!=job['digest']:raise RuntimeError('Staged bytes changed: '+str(relative))
            receipts.append({'file':str(relative),'before':old,'after':job['digest']})
        verify_plan(expected);no_minecraft()
        for job in jobs:
            no_minecraft();destination=job['destination'];current=sha(destination) if destination.exists() else None
            if current!=job['before']:raise RuntimeError('Installed target changed concurrently: '+str(destination))
            os.replace(job['temp'],destination);installed.append(job)
            if sha(destination)!=job['digest']:raise RuntimeError('Installed hash mismatch: '+str(destination))
        after_body=read(MAPS/'eva_body_r25.json');after_dorsal=read(MAPS/'eva_dorsal_r30.json')
        if strip_un_body(after_body)!=strip_un_body(before_body) or strip_un_dorsal(after_dorsal)!=strip_un_dorsal(before_dorsal):raise RuntimeError('Non-UN deep comparison failed after installation')
        models={name:{'mesh_sha256':manifest['models'][name]['sha256']['mesh'],'geo_sha256':manifest['models'][name]['sha256']['geo'],'animation_sha256':manifest['models'][name]['sha256']['animation'],'texture_sha256':manifest['models'][name]['sha256']['texture'],'pbr':manifest['models'][name]['pbr'],'triangles':manifest['models'][name]['triangles'],'parts':manifest['models'][name]['parts']} for name in MODELS}
        result={'installed':True,'revision':'R31','installedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'models':models,'backup':str(backup),'source_plan_sha256':sha(PLAN),'native_evidence':{'transport':{'path':str(evidence),'sha256':sha(evidence),'scope':visual.get('scope','transport'),'render_witness_path':str(visual_path),'render_witness_sha256':sha(visual_path),'max_mesh_to_capsule_error':max(errors)},'reset_and_capsules':{'path':str(reset_evidence),'sha256':sha(reset_evidence),'scope':'both original UN units reset and capsule mechanics; not a replay in the transport-only run'}},'nerv_body_and_motion_unchanged':True,'nerv_dorsal_unchanged':True,'worlds_modified':False,'receipts':receipts,'body_sha256':sha(MAPS/'eva_body_r25.json'),'dorsal_sha256':sha(MAPS/'eva_dorsal_r30.json')}
        (backup/'receipt.json').write_bytes(json_bytes(result));os.replace(temp_bytes(ART/'promotion.json',blob=json_bytes(result)),ART/'promotion.json');print('R31 UN pair installed; promotion receipt: '+str(ART/'promotion.json'))
    except Exception as error:
        recovery={'installed':False,'error':str(error),'backup':str(backup),'changed':[str(j['destination']) for j in installed],'rolledBack':False}
        try:
            no_minecraft()
            for job in reversed(installed):
                destination=job['destination']
                if job['before'] is None:destination.unlink(missing_ok=True)
                else:os.replace(temp_bytes(destination,source=job['backup']),destination)
            recovery['rolledBack']=True
        except Exception as restore_error:recovery['restoreError']=str(restore_error)
        (backup/'failure.json').write_bytes(json_bytes(recovery));raise
    finally:
        for job in jobs:
            if 'temp' in job:job['temp'].unlink(missing_ok=True)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--freeze',action='store_true');parser.add_argument('--apply',action='store_true');parser.add_argument('--evidence',type=Path);parser.add_argument('--reset-evidence',type=Path);args=parser.parse_args()
    if args.freeze and args.apply:parser.error('--freeze and --apply are separate actions')
    no_minecraft()
    with lock():
        if args.freeze:freeze();return
        if args.apply:
            if args.evidence is None:parser.error('--apply requires --evidence')
            apply(args.evidence,args.reset_evidence);return
        _,_,_,_,_,expected=source_inventory();verify_plan(expected);print('R31 source hashes match frozen plan; no targets modified.')
if __name__=='__main__':main()
