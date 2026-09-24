"""Recordings-only foley: load, strike, armor/body contact, stone/soil footfall.

Sources are separate CC0 field recordings. Public previews are retained with
their pages and hashes; these are not claimed to be anime master sound effects.
"""
from pathlib import Path
import hashlib,json,re,subprocess,argparse
import numpy as np
from scipy.signal import butter,sosfilt,resample_poly,find_peaks
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'artifacts/combat_direction_r36/audio_sources';ASSET=ROOT/'src/main/resources/assets/projectseele';RATE=48000
SOURCES={
 'container':('Sheyvan','569413'), 'steel':('newagesoup','337832'),
 'strain':('Nox_Sound','585734'),'sweep':('velcronator','733888'),
 'stone':('Nox_Sound','554148'),'gravel':('Nox_Sound','567701'),'body':('TRP','616953')}
def fetch():
 import requests
 SRC.mkdir(parents=True,exist_ok=True);rows=[]
 for label,(author,number) in SOURCES.items():
  url=f'https://freesound.org/people/{author}/sounds/{number}/';page=SRC/(number+'.html')
  if not page.exists():r=requests.get(url,timeout=35);r.raise_for_status();page.write_text(r.text,encoding='utf8')
  html=page.read_text(encoding='utf8');license=re.findall(r'https?://creativecommons.org/[^\s\"<>]+',html)
  if not any('/publicdomain/zero/1.0/' in x for x in license):raise ValueError('CC0 not found: '+url)
  media=re.findall(r'https://[^\s\"<>]+?-hq\.mp3',html)[0];file=SRC/(number+'.mp3')
  if not file.exists():r=requests.get(media,timeout=35);r.raise_for_status();file.write_bytes(r.content)
  rows.append(dict(label=label,author=author,url=url,download=media,license='CC0 1.0',file=file.name,sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
 (SRC/'sources.json').write_text(json.dumps(rows,indent=2));return rows
def read(label):
 path=SRC/(SOURCES[label][1]+'.mp3')
 raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-ar',str(RATE),'-ac','1','-f','f32le','-']);return np.frombuffer(raw,dtype='<f4').copy()
def level(a,peak=1):return a*peak/max(.00001,np.max(abs(a)))
def band(a,lo,hi):return sosfilt(butter(2,[lo,hi],btype='bandpass',fs=RATE,output='sos'),a)
def pitch(a,factor):return resample_poly(a,1000,round(factor*1000))
def trim(a,seconds):
 a=a[:round(seconds*RATE)].copy();n=min(len(a),round(RATE*.06));a[-n:]*=np.linspace(1,0,n);return a
def attacks(a,count,length,gap):
 env=np.sqrt(np.mean(a[:len(a)//240*240].reshape(-1,240)**2,axis=1));p,_=find_peaks(env,distance=round(gap*200),prominence=env.max()*.16)
 p=sorted(sorted(p,key=lambda i:env[i],reverse=True)[:count])
 if len(p)<count:raise ValueError('Not enough separate recorded takes')
 return [trim(a[max(0,i*240-480):],length) for i in p]
def mix(layers):
 out=np.zeros(max(len(a)+round(delay*RATE) for a,delay,gain in layers))
 for a,delay,gain in layers:
  n=round(delay*RATE);out[n:n+len(a)]+=a*gain
 return out
def write(name,a,peak):
 a=band(a,32,14500);a=level(a,peak*.62);a[:96]*=np.linspace(0,1,96);a=trim(a,len(a)/RATE)
 target=ASSET/'sounds'/(name+'.ogg');subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar',str(RATE),'-ac','1','-i','-','-c:a','libvorbis','-q:a','7',str(target)],input=a.astype('<f4').tobytes(),check=True)
 return dict(file=str(target.relative_to(ROOT)),seconds=len(a)/RATE,peak=float(abs(a).max()),sha256=hashlib.sha256(target.read_bytes()).hexdigest())
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--fetch',action='store_true');args=ap.parse_args()
 if args.fetch:fetch()
 defs=json.loads((ASSET/'sounds.json').read_text(encoding='utf8'));outputs=[]
 stones=attacks(read('stone'),3,.72,2);gravel=attacks(read('gravel'),6,.48,.95);steel=attacks(read('steel'),1,.8,1)[0];container=attacks(read('container'),1,.8,1)[0]
 strain=attacks(read('strain'),3,.26,.5);punches=attacks(read('body'),6,.50,.5);sweep=read('sweep');events={}
 def emit(event,name,a,peak=.84):outputs.append(write(name,a,peak));events.setdefault(event,[]).append({'name':'projectseele:'+name,'attenuation_distance':384})
 for i in range(6):
  ground=level(pitch(stones[i%3],.67));mass=level(band(pitch(container,.50),35,240));shell=level(band(steel,600,4600));grit=level(gravel[i])
  # One short sole transient, low structural body, then loose fragments.
  step=mix([(ground,0,.68),(trim(mass,.58),.008,.58),(trim(shell,.16),.018,.16),(grit,.055,.12)])
  emit('eva_foot_concrete',f'eva_foot_solid_r36_{i}',step,.78)
  soil=mix([(level(pitch(gravel[i],.68)),0,.67),(trim(mass,.44),.005,.43),(trim(ground,.23),.005,.18)])
  emit('eva_foot_soil',f'eva_foot_earth_r36_{i}',soil,.72)
  body=mix([(trim(level(pitch(punches[i],.60)),.57),0,.87),(trim(ground,.18),.005,.16),(trim(mass,.55),.014,.37)])
  emit('eva_impact',f'eva_contact_body_r36_{i}',body)
  armor=mix([(trim(level(pitch(steel,.82)),.55),0,.57),(body,0,.82)])
  emit('eva_armor_impact',f'eva_contact_armor_r36_{i}',armor)
  heavy=mix([(body,0,.84),(trim(level(pitch(stones[i%3],.46)),.95),.018,.63),(grit,.1,.18)])
  emit('eva_impact_heavy',f'eva_contact_heavy_r36_{i}',heavy,.91)
 for i in range(3):
  load=trim(level(band(pitch(strain[i],.65),190,2300)),.34)
  emit('eva_joint_load',f'eva_load_r36_{i}',load,.24)
  swing=trim(level(pitch(sweep,.72+i*.045)),.55)
  emit('eva_swing',f'eva_air_r36_{i}',swing,.48)
  emit('sachiel_swing',f'sachiel_air_r36_{i}',trim(level(pitch(sweep,.54+i*.04)),.66),.44)
  landing=mix([(level(pitch(stones[i],.50)),0,.8),(trim(level(band(pitch(container,.43),35,250)),.9),.012,.60)])
  emit('eva_land',f'eva_landing_r36_{i}',landing,.91)
  emit('sachiel_foot',f'sachiel_foot_r36_{i}',mix([(level(pitch(stones[i],.55)),0,.8),(level(pitch(gravel[i],.7)),.04,.18)]),.80)
 for event,sounds in events.items():defs[event]={'subtitle':'subtitles.projectseele.'+event,'sounds':sounds}
 # Shield contact has a shorter body and no metal ringing.
 defs['eva_at_pressure']['sounds']=[dict(s,volume=.65,pitch=1.15) for s in events['eva_impact']]
 (ASSET/'sounds.json').write_text(json.dumps(defs,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 out=ROOT/'artifacts/combat_direction_r36/audio';out.mkdir(parents=True,exist_ok=True)
 (out/'manifest.json').write_text(json.dumps({'sources':json.loads((SRC/'sources.json').read_text()),'outputs':outputs,'review':'Timing/source/peak checked; no claim of subjective auditory approval.'},indent=2))
 print('Wrote',len(outputs),'recorded foley assets')
if __name__=='__main__':main()
