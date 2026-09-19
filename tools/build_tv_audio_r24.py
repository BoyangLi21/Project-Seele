"""Original deterministic radio, telephone and physical energy-whip sound cues."""
from pathlib import Path
import hashlib,json,subprocess,wave
import numpy as np
from scipy.signal import butter,sosfilt

ROOT=Path(__file__).resolve().parents[1];ASSET=ROOT/'src/main/resources/assets/projectseele';OUT=ROOT/'artifacts/facility_r24/audio';RATE=48000
rng=np.random.default_rng(19950924)
def band(n,lo,hi):return sosfilt(butter(3,[lo,hi],fs=RATE,btype='bandpass',output='sos'),rng.normal(size=n))
def synth(name,seconds):
    t=np.arange(round(seconds*RATE))/RATE;n=len(t);a=np.zeros(n)
    if name=='shamshel_whip_charge':
        u=t/seconds;env=np.sin(np.pi*u)**.8
        # Tension builds from filtered friction and low inharmonic resonances.
        a=(band(n,220,2600)*.23+np.sin(2*np.pi*(137*t+30*t*t))*.12+np.sin(2*np.pi*263*t)*.06)*env
    elif name=='shamshel_whip_crack':
        env=np.exp(-t*17)*(1-np.exp(-t*1200))
        a=band(n,900,9200)*env*.65+band(n,100,1100)*np.exp(-t*6)*.16
        a+=.26*np.sin(2*np.pi*(74*t+4*(1-np.exp(-t*30))))*np.exp(-t*12)
        a+=band(n,2400,11000)*np.exp(-np.maximum(0,t-.035)*30)*(t>.035)*.12
    elif name=='period_phone_busy':
        for start in (0,.5,1.0):
            u=t-start;gate=(u>=0)&(u<.25);env=np.clip(u/.01,0,1)*np.clip((.25-u)/.015,0,1)*gate
            a+=(np.sin(2*np.pi*400*t)+.04*np.sin(2*np.pi*800*t))*env*.17
    else:
        for start,freq in ((.02,880),(.12,1100)) if name=='staff_radio_connect' else ((.01,740),):
            u=np.maximum(0,t-start);a+=(t>=start)*(1-np.exp(-u*600))*np.exp(-u*40)*np.sin(2*np.pi*freq*u)*.24
        a+=band(n,500,3200)*np.exp(-t*35)*.025
    a*=np.clip(t/.004,0,1)*np.clip((seconds-t)/.04,0,1);a-=a.mean()
    peak=max(abs(a));limit=.66 if 'whip' in name else .30
    if peak>limit:a*=limit/peak
    return a
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    definitions=json.loads((ASSET/'sounds.json').read_text(encoding='utf8'));languages={code:json.loads((ASSET/'lang'/f'{code}.json').read_text(encoding='utf8')) for code in ('zh_cn','en_us')};report=[]
    for name,seconds,distance,zh,en in [('shamshel_whip_charge',.6,160,'使徒光鞭蓄势','Angel whip tension'),('shamshel_whip_crack',.8,192,'使徒光鞭甩击','Angel whip crack'),('period_phone_busy',1.3,12,'公共电话忙音','Public telephone busy'),('staff_radio_connect',.3,12,'指挥频道接通','Command channel connected'),('staff_radio_ack',.18,12,'指挥频道回应','Command channel reply')]:
        a=synth(name,seconds);wav=OUT/(name+'.wav');target=ASSET/'sounds'/(name+'.ogg')
        with wave.open(str(wav),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(RATE);f.writeframes((a*32767).astype('<i2').tobytes())
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(wav),'-c:a','libvorbis','-q:a','5',str(target)],check=True)
        definitions[name]={'subtitle':'subtitles.projectseele.'+name,'sounds':[{'name':'projectseele:'+name,'attenuation_distance':distance}]}
        languages['zh_cn']['subtitles.projectseele.'+name]=zh;languages['en_us']['subtitles.projectseele.'+name]=en
        report.append(dict(name=name,seconds=seconds,peak=float(abs(a).max()),rms=float(np.sqrt(np.mean(a*a))),sha256=hashlib.file_digest(target.open('rb'),'sha256').hexdigest(),source='Original seeded synthesis in tools/build_tv_audio_r24.py',license='MIT'))
    (ASSET/'sounds.json').write_text(json.dumps(definitions,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for code,data in languages.items():(ASSET/'lang'/f'{code}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (OUT/'sources.json').write_text(json.dumps(report,indent=2),encoding='utf8');print('Original cues installed:',len(report))
if __name__=='__main__':main()
