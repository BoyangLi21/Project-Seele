"""Encode only real framebuffer frames, retaining recorded time intervals."""
from pathlib import Path
import hashlib,json,subprocess

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/combat_sortie_r32'

def encode(report_name,stages,name):
    report=OUT/report_name;d=json.loads(report.read_text(encoding='utf8'));assert d.get('passed')
    media=(ROOT/'run'/d['media']).resolve();evidence=media/'client_evidence.json';data=json.loads(evidence.read_text(encoding='utf8'))
    frames=[r for r in data['frames'] if r['stage'] in stages];assert len(frames)>15
    lines=['ffconcat version 1.0'];seconds=0
    for i,row in enumerate(frames):
        path=(media/row['file']).resolve();assert path.parent==media and path.is_file()
        dt=frames[i+1]['render_elapsed_seconds']-row['render_elapsed_seconds'] if i+1<len(frames) and frames[i+1]['stage']==row['stage'] else 1/24
        assert dt>0;seconds+=dt
        lines.extend(["file '"+path.as_posix()+"'",'option framerate 1000','duration '+format(dt,'.9f')])
    lines.extend(["file '"+(media/frames[-1]['file']).as_posix()+"'",'option framerate 1000'])
    concat=OUT/(name+'.ffconcat');concat.write_text('\n'.join(lines)+'\n',encoding='utf8')
    video=OUT/(name+'.mp4')
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-safe','0','-f','concat','-i',str(concat),'-an','-c:v','libx264','-preset','medium','-crf','21','-threads','2','-pix_fmt','yuv420p','-fps_mode','vfr','-video_track_timescale','90000','-movflags','+faststart',str(video)],check=True)
    receipt={'video':str(video),'native_media':str(media),'frames':len(frames),'recorded_seconds':seconds,'stages':stages,'silent':True,'synthetic_frames':False,'source_evidence_sha256':hashlib.sha256(evidence.read_bytes()).hexdigest(),'sha256':hashlib.sha256(video.read_bytes()).hexdigest()}
    video.with_suffix('.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8');print(video,video.stat().st_size,flush=True)

if __name__=='__main__':
    encode('duel_anatomical_pass.json',['duel'],'R32_Combat_Driver')
    encode('jump_final_pass.json',['air_strike','air_slam'],'R32_Jump_Attacks')
