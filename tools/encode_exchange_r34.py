"""VFR native framebuffer + timestamp-aligned WASAPI audio, with source receipts."""
from pathlib import Path
import argparse,json,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/combat_direction_r34'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('media',type=Path);ap.add_argument('audio',type=Path);ap.add_argument('name');ap.add_argument('--output-dir',type=Path,default=OUT);a=ap.parse_args();out=a.output_dir.resolve();out.mkdir(parents=True,exist_ok=True)
    media=a.media.resolve();e=json.loads((media/'client_evidence.json').read_text());frames=[f for f in e['frames'] if f['stage']=='duel']
    if e.get('server_failure') or e.get('capture_write_failure') or len(frames)<20:raise ValueError('Native capture incomplete')
    pcm=json.loads(a.audio.with_suffix('.capture.json').read_text());offset=frames[0]['capture_epoch_ms']/1000-pcm['start_epoch_seconds']
    if offset<0 or pcm['peak']<.00001:raise ValueError('Audio capture is empty or outside video timestamps')
    lines=['ffconcat version 1.0'];seconds=0
    for i,f in enumerate(frames):
        dt=frames[i+1]['render_elapsed_seconds']-f['render_elapsed_seconds'] if i<len(frames)-1 else 1/24
        if dt<=0:raise ValueError('Non-monotonic frame times')
        path=media/f['file'];lines.extend(["file '"+path.as_posix()+"'",'option framerate 1000','duration '+str(dt)]);seconds+=dt
    lines.append("file '"+(media/frames[-1]['file']).as_posix()+"'")
    concat=out/(a.name+'.ffconcat');concat.write_text('\n'.join(lines)+'\n');target=out/(a.name+'.mp4')
    subprocess.run(['ffmpeg','-v','error','-y','-safe','0','-f','concat','-i',str(concat),'-ss',str(offset),'-i',str(a.audio),'-t',str(seconds),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-crf','20','-preset','medium','-threads','2','-pix_fmt','yuv420p','-fps_mode','vfr','-c:a','aac','-b:a','192k','-movflags','+faststart',str(target)],check=True)
    receipt={'video':str(target),'native_media':str(media),'source_pcm':str(a.audio),'audio_offset_seconds':offset,'seconds':seconds,'frames':len(frames),'audio':'Actual selected-speaker loopback; no added soundtrack','source_evidence_sha256':hashlib.sha256((media/'client_evidence.json').read_bytes()).hexdigest(),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
    target.with_suffix('.json').write_text(json.dumps(receipt,indent=2));print(target)
if __name__=='__main__':main()
