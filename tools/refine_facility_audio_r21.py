"""Natural Mandarin PA and restrained fixed-pitch facility warning pulses."""
from pathlib import Path
import asyncio,hashlib,json,shutil,subprocess,sys,wave
import numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_repair_r21/audio_v2';ASSET=ROOT/'src/main/resources/assets/projectseele'
sys.path.insert(0,str(ROOT/'.Codex/audio-runtime'))
import edge_tts
VOICE={
 'pa_prepare':'出击准备，登机通道正在收回。','pa_insert':'插入栓开始对接。','pa_lock':'插入栓已锁定，同步连接正常。',
 'pa_drain':'开始排出 LCL，解除机体固定。','pa_transfer':'机体开始转运，轨道区人员请避让。','pa_ready':'弹射器已连接，等待发射指令。',
 'pa_recover':'回收作业开始，请保持安全距离。','pa_return':'机体正在返回机库。','pa_fill':'机体已入库，开始注入 LCL。',
 'pa_standby':'机体固定完成，进入待机。','pa_fault':'作业暂停，请检查安全联锁。',
 'pa_door_open':'舱门开启，请确认出舱通道安全。','pa_door_close':'舱门即将关闭，请离开移动范围。',
 'pa_3':'三。','pa_2':'二。','pa_1':'一。','pa_launch':'发射。'}
def ffmpeg(*args):subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',*map(str,args)],check=True)
def duration(path):return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(path)]))
async def synthesize():
 semaphore=asyncio.Semaphore(2)
 async def line(name,text):
  target=OUT/(name+'.mp3')
  if target.exists() and target.stat().st_size>1000:return
  async with semaphore:
   await edge_tts.Communicate(text,'zh-CN-XiaoxiaoNeural',rate='+0%' if name in ('pa_1','pa_2','pa_3','pa_launch') else '-5%',pitch='-1Hz').save(str(target))
   print('Natural PA',name,flush=True)
 await asyncio.gather(*(line(n,t) for n,t in VOICE.items()))
def main():
 OUT.mkdir(parents=True,exist_ok=True);backup=OUT/'before';backup.mkdir(exist_ok=True)
 for name in [*VOICE,'facility_siren']:
  p=ASSET/'sounds'/(name+'.ogg')
  if p.exists() and not (backup/p.name).exists():shutil.copy2(p,backup/p.name)
 asyncio.run(synthesize());sources=[];metrics=[]
 trim='silenceremove=start_periods=1:start_threshold=-48dB:start_silence=0.025,areverse,silenceremove=start_periods=1:start_threshold=-48dB:start_silence=0.09,areverse'
 for name,text in VOICE.items():
  target=ASSET/'sounds'/(name+'.ogg');ffmpeg('-i',OUT/(name+'.mp3'),'-af',trim+',highpass=f=85,lowpass=f=7800,loudnorm=I=-18:TP=-2:LRA=8','-ar',48000,'-ac',1,'-c:a','libvorbis','-q:a',5,target)
  seconds=duration(target)
  if name in ('pa_1','pa_2','pa_3'):assert seconds<.95,(name,seconds,'Countdown must finish before the next second')
  metrics.append(dict(name=name,duration_seconds=seconds))
  sources.append(dict(name=name,text=text,source='Microsoft Xiaoxiao neural speech; original project text; generated through edge-tts 7.2.8',reference='https://learn.microsoft.com/azure/ai-services/speech-service/language-support?tabs=tts',sha256=hashlib.file_digest(target.open('rb'),'sha256').hexdigest()))
 # A pair of short, stable buzzer tones with a deliberate quiet interval.
 # There is no pitch sweep, vocal formant, beating or siren-like glissando.
 rate=48000;t=np.arange(rate*2)/rate;a=np.zeros_like(t)
 for start,length in ((.06,.29),(.61,.29)):
  u=t-start;window=(u>=0)&(u<length);envelope=np.zeros_like(t)
  envelope[window]=np.minimum(1,u[window]/.025)*np.minimum(1,(length-u[window])/.05)
  a+=envelope*(np.sin(2*np.pi*660*t)+.12*np.sin(2*np.pi*1320*t)+.035*np.sin(2*np.pi*1980*t))
 a*=.31/max(abs(a));wav=OUT/'facility_siren_fixed_pulses.wav'
 with wave.open(str(wav),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes((a*32767).astype('<i2').tobytes())
 target=ASSET/'sounds/facility_siren.ogg';ffmpeg('-i',wav,'-c:a','libvorbis','-q:a',5,target)
 definitions=ASSET/'sounds.json';events=json.loads(definitions.read_text(encoding='utf8'))
 events['alarm']['sounds']=[dict(name='projectseele:facility_siren',stream=False)]
 definitions.write_text(json.dumps(events,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 sources.append(dict(name='facility_siren',source='Original additive synthesis: 660 Hz fixed-pitch pair, restrained harmonics, short envelope, no copied TV audio',sha256=hashlib.file_digest(target.open('rb'),'sha256').hexdigest()))
 for code in ('zh_cn','en_us'):
  path=ASSET/'lang'/f'{code}.json';d=json.loads(path.read_text(encoding='utf8'))
  if code=='zh_cn':
   for name,text in VOICE.items():d['subtitles.projectseele.'+name]=text
   d['subtitles.projectseele.facility_siren']='NERV 出动提示警报'
  path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 (OUT/'sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2),encoding='utf8')
 (OUT/'metrics.json').write_text(json.dumps(dict(voices=metrics,alarm_peak=float(abs(a).max()),alarm_rms=float(np.sqrt(np.mean(a*a))),alarm_duty_cycle=float(np.mean(abs(a)>.005)),pitch_sweep=False),indent=2))
 ffmpeg('-i',ASSET/'sounds/pa_prepare.ogg','-i',ASSET/'sounds/pa_lock.ogg','-i',target,'-filter_complex','[0:a]apad=pad_dur=0.5[a];[1:a]apad=pad_dur=0.5[b];[a][b][2:a]concat=n=3:v=0:a=1[out]','-map','[out]','-c:a','libmp3lame','-q:a',3,OUT/'new_PA_and_alarm_sample.mp3')
 print('Natural PA and fixed-pitch warning installed',len(sources),flush=True)
if __name__=='__main__':main()
