"""Original mechanical synthesis and locally synthesized Mandarin announcements."""
from pathlib import Path
import json, subprocess, wave, hashlib
import numpy as np
from scipy.signal import butter,sosfilt
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_repair_r21/audio';ASSET=ROOT/'src/main/resources/assets/projectseele';RATE=48000
VOICE={'pa_door_open':'舱门开启。请确认出舱通道安全。','pa_door_close':'舱门即将关闭。请离开门体移动范围。','pa_prepare':'出击准备。登机通道正在收回。','pa_insert':'插入栓开始插入。','pa_lock':'插入栓锁定。同步连接确认。','pa_drain':'开始排出 L C L。解除机体固定。','pa_transfer':'转运开始。请远离运输轨道。','pa_ready':'弹射器连接完成。等待发射指令。','pa_recover':'回收作业开始。人员保持安全距离。','pa_return':'机体正在返回机库。','pa_fill':'回收入库。开始注液。','pa_standby':'机体固定完成。恢复待机。','pa_fault':'作业暂停。检查安全联锁。','pa_3':'三','pa_2':'二','pa_1':'一','pa_launch':'发射。'}
MECH={'facility_rail_motion':('轨道转运电机',2.0),'facility_hydraulic':('液压机构运转',2.0),'facility_lock':('机械锁闭',.65),'facility_catapult':('EVA 弹射',3.0),'facility_siren':('出动区域警报',2.0)}
def main():
 OUT.mkdir(parents=True,exist_ok=True);rng=np.random.default_rng(210917);manifest=json.loads((ASSET/'sounds.json').read_text());langs={c:json.loads((ASSET/'lang'/f'{c}.json').read_text(encoding='utf8')) for c in ['zh_cn','en_us']};sources=[]
 for name,(label,duration) in MECH.items():
  t=np.arange(round(RATE*duration))/RATE;noise=rng.standard_normal(len(t));low=sosfilt(butter(3,[45,1200],btype='band',fs=RATE,output='sos'),noise)
  if name.endswith('rail_motion'):
   a=.24*np.sin(2*np.pi*57*t)+.1*np.sin(2*np.pi*171*t)+.12*low
   for delay in np.arange(0,duration,.23):a+=.15*low*np.exp(-np.maximum(t-delay,0)/.025)*(t>=delay)
  elif name.endswith('hydraulic'):a=.15*low+.2*np.sin(2*np.pi*(131*t+4*np.sin(2*np.pi*.45*t)))+.04*np.sin(2*np.pi*377*t)
  elif name.endswith('lock'):a=(.8*low+.4*np.sin(2*np.pi*79*t))*np.exp(-t*11)+.4*noise*np.exp(-np.maximum(t-.14,0)*25)*(t>=.14)
  elif name.endswith('catapult'):
   a=.7*low*np.sin(np.pi*np.minimum(t/1.8,1))**.7+.25*np.sin(2*np.pi*(40*t+160*t*t))*np.exp(-t/1.3)
  else:
   f=480+170*(.5-.5*np.cos(2*np.pi*t));phase=np.cumsum(f)/RATE;a=.28*np.sin(2*np.pi*phase)+.07*np.sin(4*np.pi*phase)
  a*=np.minimum(1,t/.025)*np.minimum(1,(duration-t)/.05);a*=.69/max(abs(a))
  with wave.open(str(OUT/(name+'.wav')),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(RATE);w.writeframes((a*32767).astype('<i2').tobytes())
 for name in MECH:
  label=VOICE.get(name,MECH.get(name,('',0))[0]);path=ASSET/'sounds'/(name+'.ogg')
  # Voice band pass gives the PA a restrained loudspeaker timbre. Count words
  # retain their complete ending; no resampling changes the countdown rhythm.
  cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(OUT/(name+'.wav')),'-ac','1','-ar','48000']
  if name in VOICE:cmd+=['-af','silenceremove=start_periods=1:start_threshold=-45dB,highpass=f=170,lowpass=f=4200,alimiter=limit=0.8']
  cmd+=['-c:a','libvorbis','-q:a','5',str(path)];subprocess.run(cmd,check=True)
  manifest[name]=dict(subtitle='subtitles.projectseele.'+name,sounds=[dict(name='projectseele:'+name,attenuation_distance=220,stream=False)])
  for c in langs:langs[c]['subtitles.projectseele.'+name]=label if c=='zh_cn' else name.replace('_',' ')
  sources.append(dict(name=name,source='Local Microsoft Huihui synthesized speech; original text' if name in VOICE else 'Original seeded procedural mechanical audio',sha256=hashlib.file_digest(path.open('rb'),'sha256').hexdigest()))
 (ASSET/'sounds.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
 for c,d in langs.items():(ASSET/'lang'/f'{c}.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 (OUT/'sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2),encoding='utf8')
 from refine_facility_audio_r21 import main as preferred_pa
 preferred_pa()
 print('R21 mechanical bank and preferred neural PA installed')
if __name__=='__main__':main()
