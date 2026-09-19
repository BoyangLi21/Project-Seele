"""Original code-native satellite handset and heavy EVA rifle report."""
from pathlib import Path
import json,hashlib,wave,subprocess
import numpy as np
from scipy.signal import butter,sosfilt
ROOT=Path(__file__).resolve().parents[1];ASSET=ROOT/'src/main/resources/assets/projectseele';OUT=ROOT/'artifacts/facility_r25/audio'
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 faces=lambda texture:{k:{'texture':'#'+texture} for k in ('up','down','north','south','east','west')}
 elements=[]
 def box(a,b,texture):elements.append({'from':a,'to':b,'faces':faces(texture)})
 box([4,1,5],[12,13,9],'body');box([4.5,.5,5.5],[11.5,13.5,8.5],'body')
 box([5,12.5,6],[6.4,23,7.4],'body');box([4.8,21,5.8],[6.6,23.5,7.6],'rim')
 box([5,8,4.8],[11,11.8,5.05],'rim');box([5.4,8.4,4.6],[10.6,11.3,4.85],'screen')
 for x in (5.2,7.3,9.4):
  for y in (2.3,3.8,5.3,6.8):box([x,y,4.55],[x+1.35,y+.9,5.1],'keys')
 for x in (5,6.3,7.6,8.9,10.2):box([x,12.2,4.6],[x+.65,12.5,5.1],'keys')
 box([11.9,8,5.4],[12.3,10.8,7.3],'keys')
 model={'parent':'minecraft:block/block','textures':{'particle':'minecraft:block/black_concrete','body':'minecraft:block/black_concrete','rim':'minecraft:block/gray_concrete','screen':'minecraft:block/green_concrete','keys':'minecraft:block/light_gray_concrete'},'elements':elements,
 'display':{'thirdperson_righthand':{'rotation':[0,0,0],'translation':[0,2,1],'scale':[.5,.5,.5]},'firstperson_righthand':{'rotation':[0,-15,0],'translation':[1,2,0],'scale':[.7,.7,.7]},'gui':{'rotation':[12,25,0],'translation':[0,-3,0],'scale':[.65,.65,.65]},'ground':{'scale':[.4,.4,.4]},'fixed':{'scale':[.65,.65,.65]}}}
 (ASSET/'models/item/satellite_phone.json').write_text(json.dumps(model,indent=2)+'\n',encoding='utf8')
 for lang,phone,key in [('zh_cn','NERV 卫星通信电话','指挥室通信 / 卫星电话'),('en_us','NERV Satellite Handset','Command radio / satellite phone')]:
  path=ASSET/'lang'/f'{lang}.json';d=json.loads(path.read_text(encoding='utf8'));d['item.projectseele.satellite_phone']=phone;d['key.projectseele.command_radio']=key;path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 rate=48000;t=np.arange(int(rate*.78))/rate;rng=np.random.default_rng(199525)
 def noise(lo,hi):return sosfilt(butter(3,[lo,hi],fs=rate,btype='bandpass',output='sos'),rng.normal(size=len(t)))
 # Short dry muzzle shock, a decaying pressure body, then mechanical action.
 shock=noise(1100,15500)*np.exp(-t*90)*2.8
 body=(noise(65,1100)*.9+np.sin(2*np.pi*(74*t+1.6*(1-np.exp(-t*45))))*.9)*np.exp(-t*15)
 tail=noise(400,4600)*np.exp(-t*8)*.18
 bolt=np.zeros_like(t)
 for start in (.066,.112):
  u=np.maximum(0,t-start);bolt+=(t>=start)*np.exp(-u*150)*(noise(1400,9800)*.36+np.sin(2*np.pi*1320*u)*.11)
 a=(shock+body+tail+bolt)*(1-np.exp(-t*6500))*np.minimum(1,(.78-t)/.07)
 a=np.tanh(a*1.3);a-=a.mean();a*=.94/max(abs(a))
 wav=OUT/'eva_rifle_fire.wav'
 with wave.open(str(wav),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes((a*32767).astype('<i2').tobytes())
 target=ASSET/'sounds/eva_rifle_fire.ogg';subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(wav),'-c:a','libvorbis','-q:a','6',str(target)],check=True)
 report={'source':'Original seeded synthesis; no sampled recording','script':'tools/build_radio_audio_r25.py','peak':float(max(abs(a))),'rms':float(np.sqrt(np.mean(a*a))),'seconds':.78,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'license':'MIT'}
 (OUT/'source.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(report)
if __name__=='__main__':main()
