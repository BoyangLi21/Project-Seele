"""Encode honest timestamped native frames with an original, event-synchronized review mix."""
from pathlib import Path
import argparse,json,subprocess,wave,collections,bisect
import numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/tv_facilities_r16/review';OUT.mkdir(parents=True,exist_ok=True);RATE=48000

def audio_asset(name):
 source=ROOT/'src/main/resources/assets/projectseele/sounds'/(name+'.ogg')
 if not source.exists():return np.zeros(1,np.float32)
 data=subprocess.check_output(['ffmpeg','-v','error','-i',str(source),'-ac','1','-ar',str(RATE),'-f','f32le','-'])
 return np.frombuffer(data,dtype='<f4')

def choose(frames,kind):
 if kind in ('insertion','launch'):return [(0,len(frames))]
 n=len(frames);intervals=[]
 def add(start,end):
  ids=[i for i,f in enumerate(frames) if start<=f['seconds']<=end]
  if ids:intervals.append((ids[0],ids[-1]+1))
 def steady(rows,length):
  times=[f['seconds'] for f in rows]
  if not times:return
  if times[-1]-times[0]<=length:add(times[0],times[-1]);return
  candidates=[]
  for i,t in enumerate(times):
   if t+length>times[-1]:break
   j=bisect.bisect_right(times,t+length);gaps=np.diff(times[i:j]);worst=float(gaps.max()) if len(gaps) else length
   candidates.append((j-i-1000*worst,i,j))
  _,i,j=max(candidates);add(times[i],times[j-1])
 if kind.endswith('-exterior'):
  if kind=='train-exterior':
   moving=[f for f in frames if f['phase']=='station_departure' and f['speed']>.001]
   assert moving;add(max(0,moving[0]['seconds']-3),moving[0]['seconds']+10)
   steady([f for f in frames if f['phase']=='train_travel'],7)
   for phase in ['station_approach','station_arrival']:
    rows=[f for f in frames if f['phase']==phase and (phase!='station_arrival' or f['x']>1145)]
    if rows:add(rows[0]['seconds'],rows[-1]['seconds'])
  else:
   flying=[i for i,f in enumerate(frames) if f['y']>155];assert flying
   begin=flying[0];takeoff=next(i for i in range(begin+1) if frames[i]['y']>84)
   land=next(i for i in range(begin+1,n) if frames[i]['y']<85 and frames[i]['doors'])
   descend=next(i for i in range(begin+1,land+1) if frames[i]['y']<155)
   touchdown=next(i for i in range(descend,land+1) if frames[i]['y']<84)
   add(max(0,frames[takeoff]['seconds']-8),frames[begin]['seconds']+3)
   steady([f for f in frames[begin:descend] if f['phase']=='cruise'],7)
   add(max(frames[begin]['seconds'],frames[descend]['seconds']-3),frames[touchdown]['seconds']+6)
   add(max(frames[touchdown]['seconds']+6,frames[-1]['seconds']-5),frames[-1]['seconds'])
 elif kind=='train':
  ridden=[i for i,f in enumerate(frames) if f.get('riding')]
  assert ridden,'No actual native passenger footage'
  boarding=frames[ridden[0]]['seconds'];add(max(0,boarding-5),boarding+12)
  moving=[f for f in frames if f['phase']=='station_departure' and f.get('riding') and f.get('speed',0)>.001]
  if moving:add(max(boarding,moving[0]['seconds']-2),min(moving[-1]['seconds'],moving[0]['seconds']+9))
  for phase,length in [('passenger_ride',8),('station_approach',12),('station_arrival',6)]:
   rows=[f for f in frames if f['phase']==phase]
   if rows:
    if phase=='passenger_ride':steady(rows,length)
    else:add(rows[0]['seconds'],min(rows[-1]['seconds'],rows[0]['seconds']+length))
 elif kind=='flight':
  riding=[f for f in frames if f.get('riding')];assert riding
  add(max(0,riding[0]['seconds']-3),riding[0]['seconds']+5)
  # Complete first takeoff and destination landing, with short cruise views.
  flying=[i for i,f in enumerate(frames) if f.get('riding') and f.get('y',0)>155];assert flying
  begin=flying[0];land=next((i for i in range(begin+1,n) if frames[i].get('y',999)<84 and frames[i].get('doors')),None);assert land is not None,'No recorded destination landing'
  takeoff=next((i for i in range(begin) if frames[i].get('riding') and frames[i].get('y',0)>84),begin)
  add(max(riding[0]['seconds'],frames[takeoff]['seconds']-8),frames[begin]['seconds']+3)
  for phase in ['cruise','passenger_cruise']:
   rows=[f for f in frames[begin:land] if f['phase']==phase]
   if rows:steady(rows,7)
  descending=next((i for i in range(begin+1,land) if frames[i].get('y',999)<145),land)
  add(frames[descending]['seconds']-3,frames[land]['seconds']+5)
 intervals.sort();merged=[]
 for a,b in intervals:
  if merged and a<=merged[-1][1]:merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
  else:merged.append((a,b))
 return merged

def main(folder,kind,name):
 data=json.loads((folder/'frames.json').read_text());assert not data.get('write_failure');frames=data['frames'];assert len(frames)>25
 if kind.endswith('-exterior'):assert data.get('passed'),'Exterior native journey did not complete'
 if kind=='train':
  assert any(f.get('riding') and f.get('travel',0)>500 and f.get('player_x',0)>1145 and f.get('player_y',999)<74 and f.get('doors') and f.get('speed',1)<.001 for f in frames),'No actual passenger arrival at the harbor'
  assert {'station_departure','passenger_ride','station_arrival'} <= {f['phase'] for f in frames},'Missing requested train views'
 if kind=='flight':
  ridden=[f for f in frames if f.get('riding')];assert ridden and max(f.get('travel',0) for f in ridden)>6000,'Native round trip is incomplete'
  assert max(f['y'] for f in ridden)>160,'No actual airborne phase'
  origin_west=ridden[0]['player_x']<0
  assert any((f['player_x']<0)==origin_west and f['travel']>6000 and f.get('doors') and f['player_y']<86 for f in ridden),'No native return to the origin airport'
 segments=choose(frames,kind);selected=[];duration=0.;concat=[];source_intervals=[]
 for first,last in segments:
  source_intervals.append([frames[first]['seconds'],frames[last-1]['seconds']]);segment_start=duration
  for i in range(first,last):
   f=frames[i];dt=frames[i+1]['seconds']-f['seconds'] if i+1<last else min(.1,frames[i]['seconds']-frames[i-1]['seconds'] if i else .05)
   assert .0001<dt<10,(i,dt);concat.extend([f"file '{(folder/f['file']).resolve().as_posix()}'",f'duration {dt:.8f}']);selected.append(dict(f,edited_seconds=duration,segment=len(source_intervals)-1));duration+=dt
 concat.append(f"file '{(folder/frames[segments[-1][1]-1]['file']).resolve().as_posix()}'");listfile=OUT/(name+'.concat.txt');listfile.write_text('\n'.join(concat)+'\n',encoding='utf8')
 audio=np.zeros(round((duration+5)*RATE),np.float32);rng=np.random.default_rng(16);t=np.arange(len(audio))/RATE
 # Original low mechanical room/vehicle tone. No TV music or extracted voices.
 base=.024*np.sin(2*np.pi*(47 if kind in ('insertion','launch') else 61)*t)+.012*np.sin(2*np.pi*94*t)
 if kind.startswith('flight'):base+=rng.normal(0,.016,len(t))
 audio+=base.astype(np.float32);assets={n:audio_asset(n) for n in ['eva_servo','eva_armor_impact','eva_cockpit_confirm','eva_drive_loop','eva_land']}
 def cue(at,asset,gain):
  sample=assets[asset]*gain;start=max(0,round(at*RATE));end=min(len(audio),start+len(sample));audio[start:end]+=sample[:end-start]
 last_phase=None;last_segment=-1;last_loop=-100
 events=[]
 for f in selected:
  phase=f['phase'];at=f['edited_seconds']
  if phase!=last_phase or f['segment']!=last_segment:
   last_phase=phase;last_segment=f['segment'];events.append(dict(time=round(at,3),phase=phase))
   if phase in ['BRIDGE_RETRACTING','PLUG_INSERTING','TO_SILO','taxi','station_departure']:cue(at,'eva_servo',.35)
   if phase in ['PLUG_LOCKING','SILO_READY','at_gate','station_arrival']:cue(at,'eva_cockpit_confirm',.27);cue(at+.25,'eva_armor_impact',.24)
   if phase=='DEPLOYED':cue(at,'eva_land',.48)
  if phase in ['PLUG_INSERTING','DRAINING','TO_SILO','SILO_READY','taxi','takeoff_or_landing','cruise','passenger_cruise','passenger_ride','station_departure'] and at-last_loop>2.0:
   cue(at,'eva_drive_loop',.07 if kind=='flight' else .12);last_loop=at
 audio=audio[:round(duration*RATE)];fade=np.ones(len(audio),np.float32);r=min(RATE//3,len(audio)//2);fade[:r]=np.linspace(0,1,r);fade[-r:]=np.linspace(1,0,r);audio*=fade;audio*=min(1,.85/max(.001,float(abs(audio).max())))
 wav=OUT/(name+'_review_mix.wav')
 with wave.open(str(wav),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(RATE);f.writeframes((audio*32767).astype('<i2').tobytes())
 target=OUT/(name+'.mp4');subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(listfile),'-i',str(wav),'-fps_mode','vfr','-c:v','libx264','-threads','2','-crf','21','-preset','fast','-pix_fmt','yuv420p','-c:a','aac','-b:a','96k','-shortest','-movflags','+faststart',str(target)],check=True)
 probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration,size','-of','json',str(target)]))['format']
 manifest=dict(file=str(target),source=str(folder),kind=kind,frames=len(selected),source_intervals=source_intervals,source_dropped=data.get('dropped'),visual='Native Minecraft framebuffer, source wall-clock timing retained, only cuts; no generated or interpolated motion frames',audio='Original review sound design synchronized to recorded phases; not a live audio capture',events=events,**probe)
 (OUT/(name+'_manifest.json')).write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8');print(target,probe)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('folder',type=Path);ap.add_argument('--kind',required=True,choices=['insertion','launch','train','flight','train-exterior','flight-exterior']);ap.add_argument('--name',required=True);a=ap.parse_args();main(a.folder,a.kind,a.name)
