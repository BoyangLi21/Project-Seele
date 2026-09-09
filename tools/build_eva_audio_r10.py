"""Original mono movement/combat sounds: seeded synthesis, never anime recordings."""
import json,math,hashlib,subprocess,wave
from pathlib import Path
import numpy as np
from scipy.signal import butter,sosfilt
ROOT=Path(__file__).resolve().parents[1];ASSET=ROOT/'src/main/resources/assets/projectseele';OUT=ROOT/'artifacts/first_battle_world_r10/audio';RATE=48000
rng=np.random.default_rng(10071995)
def filtered(n,lo,hi):return sosfilt(butter(3,[lo,hi],btype='bandpass',fs=RATE,output='sos'),rng.standard_normal(n))
def envelope(t,start,attack,decay):
    u=np.maximum(0,t-start);return (t>=start)*(1-np.exp(-u/max(attack,1e-5)))*np.exp(-u/decay)
def tone(t,f,decay=1,phase=0):return np.sin(2*np.pi*f*t+phase)*np.exp(-t/decay)
def synth(kind,seconds):
    t=np.arange(round(seconds*RATE))/RATE;n=len(t);a=np.zeros(n)
    if kind.startswith('foot') or kind=='land':
        soil='soil' in kind;heavy=kind=='land'
        a+=(.95 if heavy else .65)*np.sin(2*np.pi*(43*t+12*(1-np.exp(-t*14))))*envelope(t,0,.006,.28 if heavy else .17)
        a+=filtered(n,80,380)*envelope(t,.007,.002,.11)*1.2
        a+=filtered(n,180 if soil else 700,2200 if soil else 6400)*envelope(t,.018,.004,.19 if soil else .08)*(.9 if soil else .55)
        for delay in ([.02,.075,.17,.28,.44] if heavy else [.016,.10,.19]):
            for f in [277,463,811]:a+=.11*tone(np.maximum(0,t-delay),f,.09)*envelope(t,delay,.001,.16)
        if heavy:a+=filtered(n,45,950)*envelope(t,.15,.03,.48)*.45
    elif kind in ('swing','servo'):
        u=t/seconds;frequency=(180+750*u) if kind=='servo' else (950-680*u)
        carrier=np.sin(2*np.pi*np.cumsum(frequency)/RATE)
        a=(filtered(n,110,4200)*.45+carrier*.18)*np.sin(np.pi*u)**1.6
        if kind=='servo':a+=.08*np.sin(2*np.pi*98*t)*np.sin(np.pi*u)
    elif kind in ('impact','armor','knife','core'):
        a+=np.sin(2*np.pi*(61*t+8*(1-np.exp(-t*24))))*envelope(t,0,.002,.17)*.75
        band=(130,1900) if kind=='impact' else (800,10500) if kind=='knife' else (500,7800)
        a+=filtered(n,*band)*envelope(t,.004,.001,.14 if kind!='knife' else .24)
        if kind!='impact':
            for f in [537,883,1439,2331,3767]:a+=tone(t,f,.10 if kind=='core' else .22)*envelope(t,.009,.001,.35)*.10
        if kind=='knife':a+=.22*filtered(n,1700,6200)*(1+.6*np.sin(2*np.pi*82*t))*envelope(t,.06,.015,.22)
    elif kind.startswith('at_'):
        rise=kind=='at_pressure';u=t/seconds
        a+=filtered(n,120,4300)*(.13 if rise else .52)*envelope(t,.01,.06 if rise else .001,.7 if rise else .25)
        for f,gain in [(92,.28),(183,.18),(367,.12),(733,.08),(1469,.05)]:
            phase=2*np.pi*(f*t+(38 if rise else -105)*t*t/seconds)
            a+=gain*np.sin(phase)*np.sin(np.pi*u)**(.6 if rise else 1.3)
        if not rise:a+=filtered(n,2300,13500)*envelope(t,.008,.001,.11)*.8
    elif kind=='roar':
        u=t/seconds;f=82+22*np.sin(np.pi*u)+5*np.sin(2*np.pi*6.7*t);phase=2*np.pi*np.cumsum(f)/RATE
        source=sum(np.sin(phase*k+.18*np.sin(2*np.pi*13*t))/k for k in range(1,20))
        for lo,hi,gain in [(100,300,.7),(420,900,.5),(1150,2200,.32)]:a+=sosfilt(butter(3,[lo,hi],btype='bandpass',fs=RATE,output='sos'),source)*gain
        a+=filtered(n,140,3000)*.32;a*=np.sin(np.pi*u)**.8*(.85+.15*np.sin(2*np.pi*7*t))
    elif kind in ('confirm','warning'):
        for delay in ([0,.14,.28] if kind=='warning' else [0,.075]):
            a+=(tone(np.maximum(0,t-delay),660 if kind=='warning' else 990,.04)+.35*tone(np.maximum(0,t-delay),1320,.03))*envelope(t,delay,.001,.07)
    elif kind=='drive':
        a=sum(.24/i*np.sin(2*np.pi*f*t+.05*np.sin(2*np.pi*3*t)) for i,f in enumerate([38,72,114,190],1));a+=filtered(n,55,310)*.18
    fade=np.minimum(1,np.minimum(t/.008,(seconds-t)/.045));a*=np.maximum(0,fade);a=sosfilt(butter(2,25,btype='highpass',fs=RATE,output='sos'),a);a-=a.mean()
    a*=.63/max(np.max(abs(a)),1e-8);return a.astype(np.float32)
SPECS=[('eva_foot_concrete','foot_concrete',.82,160,'EVA 重步','EVA heavy footstep'),('eva_foot_soil','foot_soil',.88,144,'EVA 踏地','EVA footfall on soil'),
 ('eva_land','land',1.45,192,'EVA 着地','EVA landing'),('eva_servo','servo',.42,64,'机体关节运转','EVA joint drive'),
 ('eva_swing','swing',.42,96,'机体挥击','EVA arm swing'),('eva_impact','impact',.75,160,'机体打击命中','EVA strike impact'),
 ('eva_armor_impact','armor',.9,160,'装甲撞击','Armor impact'),('eva_knife_cut','knife',.8,112,'高振动粒子刀切割','Progressive knife cut'),
 ('eva_core_break','core',1.0,160,'使徒核心破裂','Angel core fracture'),('eva_at_pressure','at_pressure',1.3,160,'AT 力场相互侵蚀','AT fields eroding'),
 ('eva_at_tear','at_tear',1.05,176,'AT 力场撕裂','AT field tearing'),('eva_berserk_roar','roar',2.3,224,'初号机暴走咆哮','Unit-01 berserk roar'),
 ('eva_cockpit_confirm','confirm',.22,16,'操纵确认','Pilot control confirmed'),('eva_cockpit_warning','warning',.52,16,'驾驶警示','Pilot warning'),
 ('eva_drive_loop','drive',2.0,48,'机体驱动低鸣','EVA drive hum')]
def main():
    OUT.mkdir(parents=True,exist_ok=True);(ASSET/'sounds').mkdir(exist_ok=True);report=[]
    manifest=json.loads((ASSET/'sounds.json').read_text(encoding='utf8'));languages={code:json.loads((ASSET/'lang'/f'{code}.json').read_text(encoding='utf8')) for code in ['zh_cn','en_us']}
    montage=[]
    for name,kind,duration,distance,zh,en in SPECS:
        signal=synth(kind,duration);wav=OUT/(name+'.wav')
        with wave.open(str(wav),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(RATE);f.writeframes((signal*32767).astype('<i2').tobytes())
        ogg=ASSET/'sounds'/(name+'.ogg');subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(wav),'-c:a','libvorbis','-q:a','5',str(ogg)],check=True)
        manifest[name]=dict(subtitle='subtitles.projectseele.'+name,sounds=[dict(name='projectseele:'+name,attenuation_distance=distance,stream=False)])
        for code,label in [('zh_cn',zh),('en_us',en)]:languages[code]['subtitles.projectseele.'+name]=label
        report.append(dict(name=name,seconds=duration,channels=1,sample_rate=RATE,peak=float(max(abs(signal))),rms=float(np.sqrt(np.mean(signal**2))),sha256=hashlib.sha256(ogg.read_bytes()).hexdigest(),source='Original seeded additive/noise synthesis; no recordings'))
        montage.extend([signal,np.zeros(RATE//3)])
    (ASSET/'sounds.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    for code,data in languages.items():(ASSET/'lang'/f'{code}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (OUT/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    with wave.open(str(OUT/'sound_review.wav'),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(RATE);f.writeframes((np.concatenate(montage)*32767).astype('<i2').tobytes())
    print('Original sound events',len(report))
if __name__=='__main__':main()
