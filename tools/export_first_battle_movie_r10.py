"""Encode timestamped native frames, with clearly identified original, event-timed review sound."""
import argparse,json,wave,subprocess
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/first_battle_world_r10/choreography';RATE=48000
def main(folder,output=OUT,name='eva_sachiel_first_battle_r10'):
 output.mkdir(parents=True,exist_ok=True)
 data=json.loads((folder/'frames.json').read_text());frames=data['frames'];assert frames and any(f['active'] for f in frames)
 lines=[]
 for i,f in enumerate(frames):
  lines+=[f"file '{(folder/f['file']).resolve().as_posix()}'",f"duration {(frames[i+1]['seconds']-f['seconds']) if i+1<len(frames) else .05:.7f}"]
 lines.append(f"file '{(folder/frames[-1]['file']).resolve().as_posix()}'");source=output/'native_first_battle.concat.txt';source.write_text('\n'.join(lines)+'\n',encoding='utf8')
 duration=frames[-1]['seconds']+.05;audio=np.zeros(round(duration*RATE)+RATE*3,dtype=np.float32);active=[f for f in frames if f['active']]
 cues=[(0,'berserk_roar',.65),(.95,'foot_concrete',.7),(1.4,'at_pressure',.7),(2.65,'at_pressure',.5),(3.75,'at_pressure',.6),(4.95,'at_tear',.85),(6.1,'foot_concrete',.6),(8,'armor_impact',.7),(9.2,'impact',.8),(11.7,'land',.9),(12.75,'impact',.85),(14.15,'impact',.85),(15.35,'armor_impact',.6),(16.05,'core_break',.8),(17.7,'at_pressure',.8),(18.6,'core_break',1),(20.5,'foot_concrete',.6),(21.4,'foot_concrete',.6)]
 for time,cue_name,gain in cues:
  at=min(active,key=lambda f:abs(f['scene_seconds']-time))['seconds'];path=ROOT/'artifacts/first_battle_world_r10/audio'/('eva_'+cue_name+'.wav')
  with wave.open(str(path),'rb') as f:sample=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').astype(np.float32)/32768
  offset=round(at*RATE);audio[offset:offset+len(sample)]+=sample*gain
 audio=audio[:round(duration*RATE)];audio*=min(1,.88/max(abs(audio)));wav=output/'native_first_battle_review_mix.wav'
 with wave.open(str(wav),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(RATE);f.writeframes((audio*32767).astype('<i2').tobytes())
 target=output/(name+'.mp4')
 subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(source),'-i',str(wav),'-fps_mode','vfr','-c:v','libx264','-preset','fast','-crf','22','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart',str(target)],check=True)
 probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration,size','-of','json',str(target)]))
 (output/'native_video_manifest.json').write_text(json.dumps(dict(source=str(folder),frames=len(frames),dropped=data['dropped'],visual='Actual native game framebuffer with captured wall-clock durations; no interpolated motion',audio='Original synthesized SFX mixed offline at measured scene-event times; not a recording of game audio',file=str(target),**probe['format']),indent=2),encoding='utf8');print(target,probe)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('folder',type=Path);ap.add_argument('--output-dir',type=Path,default=OUT);ap.add_argument('--name',default='eva_sachiel_first_battle_r10');args=ap.parse_args();main(args.folder,args.output_dir,args.name)
