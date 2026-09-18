"""Small review MP4s from real, timestamped Minecraft frames; cuts only."""
import argparse,json,subprocess
from pathlib import Path
from export_tv_movies_r16 import choose
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_rebuild_r20/media'
def main(folder,kind,name,flight_proof=None):
    folder=Path(folder);data=json.loads((folder/'frames.json').read_text());frames=data['frames'];assert len(frames)>25 and not data['write_failure'];OUT.mkdir(exist_ok=True)
    if kind=='train':
        proof=json.loads((OUT.parent/'transit/p1_native_pass.json').read_text());assert proof['passed']
        assert any(f.get('riding') and f.get('travel',0)>500 and f.get('doors') and f.get('speed',1)<.001 for f in frames)
        segments=choose(frames,'train')
    elif kind=='flight':
        proof=json.loads(Path(flight_proof or OUT.parent/'transit/f1_native_pass.json').read_text());assert proof['passed'] and proof['oppositeAirportStop'];segments=choose(frames,'flight')
    else:
        intervals=[]
        def add(a,b):
            ids=[i for i,f in enumerate(frames) if a<=f['seconds']<=b]
            if ids:intervals.append((ids[0],ids[-1]+1))
        if kind=='insertion':
            selected=[f for f in frames if f.get('mechanical_closeup')];assert selected,'A real closeup recording is required';add(selected[0]['seconds'],min(selected[0]['seconds']+22,selected[-1]['seconds']))
        else:
            active=[f for f in frames if f.get('carrier') and f['phase']=='prepare_transfer'];assert active
            add(max(0,active[0]['seconds']-2),active[-1]['seconds']+1)
            launch=[f for f in frames if f['phase']=='launch'];add(launch[0]['seconds'],launch[-1]['seconds'])
            rest=[f for f in frames if f['phase']=='free_surface_hold'];add(rest[0]['seconds'],rest[0]['seconds']+3)
            ret=[f for f in frames if f.get('carrier') and f['phase']=='recover_from_sideways'];add(ret[0]['seconds'],ret[0]['seconds']+8);add(ret[-1]['seconds']-9,ret[-1]['seconds'])
        segments=[]
        for a,b in sorted(intervals):
            if segments and a<=segments[-1][1]:segments[-1]=(segments[-1][0],max(b,segments[-1][1]))
            else:segments.append((a,b))
    lines=[];duration=0;intervals=[];count=0
    for first,last in segments:
        intervals.append([frames[first]['seconds'],frames[last-1]['seconds']])
        for i in range(first,last):
            frame=frames[i];dt=frames[i+1]['seconds']-frame['seconds'] if i+1<last else .05;assert 0<dt<10
            path=(folder/frame['file']).resolve();assert path.is_file() and path.parent==folder.resolve()
            lines += ["file '"+path.as_posix()+"'",'option framerate 1000',f'duration {dt:.8f}'];duration+=dt;count+=1
    lines += ["file '"+(folder/frames[segments[-1][1]-1]['file']).resolve().as_posix()+"'",'option framerate 1000']
    script=OUT/(name+'.concat.txt');script.write_text('\n'.join(lines)+'\n',encoding='utf8');target=OUT/(name+'.mp4')
    command=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(script),'-fps_mode','vfr','-c:v','libx264','-threads','2','-preset','fast','-crf','24','-bf','0','-pix_fmt','yuv420p','-an','-movflags','+faststart',str(target)]
    subprocess.run(command,check=True)
    if target.stat().st_size>18*1048576:
        command[command.index('-crf')+1]='27';command[-1:-1]=['-vf','scale=960:-2'];subprocess.run(command,check=True)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration,size','-of','json',str(target)]))['format']
    assert abs(float(probe['duration'])-duration)<.25
    (OUT/(name+'.json')).write_text(json.dumps(dict(file=str(target),source=str(folder),frames=count,source_intervals=intervals,source_dropped=data.get('dropped'),timing='Original wall-clock frame timing; edits are cuts only',audio='No audio track',**probe),ensure_ascii=False,indent=2),encoding='utf8');print(target,probe)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder');p.add_argument('--kind',choices=['train','flight','f5','insertion'],required=True);p.add_argument('--name',required=True);a=p.parse_args();main(a.folder,a.kind,a.name)
