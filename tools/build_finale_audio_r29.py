"""Original seeded pressure blast, sub-bass and decaying structural resonance."""
from pathlib import Path
import json,wave,subprocess,hashlib
import numpy as np
from scipy.signal import butter,sosfilt
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/facility_r29/audio';ASSET=ROOT/'src/main/resources/assets/projectseele';RATE=48000
def main():
    OUT.mkdir(parents=True,exist_ok=True);rng=np.random.default_rng(19950929)
    t=np.arange(RATE*9)/RATE;n=len(t)
    def noise(lo,hi):return sosfilt(butter(3,[lo,hi],fs=RATE,btype='bandpass',output='sos'),rng.standard_normal(n))
    pressure=(.9*noise(35,210)+.33*noise(200,1400))*np.exp(-t/1.4)*(1-np.exp(-t*160))
    crack=noise(1600,11000)*np.exp(-t*28)*.4
    rumble=(.24*np.sin(2*np.pi*(43*t-1.4*t*t/(1+t)))+.10*np.sin(2*np.pi*71*t))*np.exp(-t/3.1)
    rubble=noise(65,720)*np.exp(-t/3.8)*(.35+.15*np.sin(t*8.1)**2)
    a=pressure+crack+rumble+rubble
    for delay,gain in ((.14,.24),(.39,.18),(.86,.12),(1.42,.09)):
        k=int(delay*RATE);a[k:]+=pressure[:-k]*gain
    a*=np.clip(t/.003,0,1)*np.clip((9-t)/1.3,0,1);a-=a.mean();a=np.tanh(a*1.5);a*=.84/max(abs(a))
    wav=OUT/'angel_nuclear_finale.wav'
    with wave.open(str(wav),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(RATE);f.writeframes((a*32767).astype('<i2').tobytes())
    ogg=ASSET/'sounds/angel_nuclear_finale.ogg';subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(wav),'-c:a','libvorbis','-q:a','5',str(ogg)],check=True)
    p=ASSET/'sounds.json';d=json.loads(p.read_text(encoding='utf8'));d['angel_nuclear_finale']=dict(subtitle='subtitles.projectseele.angel_nuclear_finale',sounds=[dict(name='projectseele:angel_nuclear_finale',attenuation_distance=512,stream=False)]);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for code,text in [('zh_cn','使徒核心爆裂，冲击波与持续低频轰鸣'),('en_us','Angel core detonation and rolling pressure wave')]:
        p=ASSET/'lang'/f'{code}.json';d=json.loads(p.read_text(encoding='utf8'));d['subtitles.projectseele.angel_nuclear_finale']=text;p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (OUT/'source.json').write_text(json.dumps(dict(source='Original deterministic procedural synthesis; no sampled show audio',seed=19950929,seconds=9,peak=float(max(abs(a))),sha256=hashlib.sha256(ogg.read_bytes()).hexdigest()),indent=2))
    print('Original finale audio generated and registered in resource definitions')
if __name__=='__main__':main()
