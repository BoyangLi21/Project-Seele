"""Sample-based combat foley. No oscillator, noise generator or invented roar.

Source recordings are fetched separately and retained with their source pages.
The EVA-labelled community roar is installed only in the local audition pack;
no claim is made that the uploader grants rights to an anime master recording.
"""
from pathlib import Path
import json,subprocess,hashlib
import numpy as np
from scipy.signal import butter,sosfilt,resample_poly,find_peaks
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'artifacts/combat_direction_r34/research';OUT=ROOT/'artifacts/combat_direction_r34/audio';ASSET=ROOT/'src/main/resources/assets/projectseele';RATE=48000

def load(name):
    raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(SRC/(name+'.mp3')),'-ar',str(RATE),'-ac','1','-f','f32le','-'])
    return np.frombuffer(raw,dtype='<f4').copy()
def level(a,peak=.85):
    a=np.asarray(a,float);a-=a.mean();return a*peak/max(.001,np.max(abs(a)))
def pitch(a,factor):return resample_poly(a,1000,round(1000*factor))
def mix(*layers):
    a=np.zeros(max(len(x)+round(at*RATE) for x,at,gain in layers))
    for x,at,gain in layers:a[round(at*RATE):round(at*RATE)+len(x)]+=x*gain
    return a
def write(name,a):
    a=level(a,.89);a[:min(80,len(a))]*=np.linspace(0,1,min(80,len(a)));n=min(round(.045*RATE),len(a));a[-n:]*=np.linspace(1,0,n)
    out=ASSET/'sounds'/(name+'.ogg');subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar',str(RATE),'-ac','1','-i','-','-c:a','libvorbis','-q:a','6',str(out)],input=a.astype('<f4').tobytes(),check=True)
    return {'file':str(out.relative_to(ROOT)),'seconds':len(a)/RATE,'peak':float(abs(a).max()),'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}

def main():
    OUT.mkdir(parents=True,exist_ok=True);report=[];defs=json.loads((ASSET/'sounds.json').read_text(encoding='utf8'))
    punch=load('punch_qubodup');whoosh=load('whoosh');metal=load('heavy_metal');concrete=load('metal_concrete')
    # Separate actual hits in the original sequence; don't manufacture a
    # succession of identical impacts with random pitch on every footstep.
    envelope=np.sqrt(np.mean(concrete[:len(concrete)//480*480].reshape(-1,480)**2,axis=1));peaks,_=find_peaks(envelope,distance=90,prominence=max(envelope)*.20)
    peaks=sorted(peaks,key=lambda i:envelope[i],reverse=True)[:4];impacts=[]
    for i in sorted(peaks):
        at=max(0,i*480-720);impacts.append(concrete[at:min(len(concrete),at+round(.75*RATE))])
    if len(impacts)<3:raise RuntimeError('Recorded concrete source does not contain enough distinct impacts')
    events={}
    for i in range(4):
        hard=level(pitch(impacts[i%len(impacts)],.70+i*.035));body=level(pitch(punch,.59+i*.025));shell=level(pitch(metal,.80+i*.04))[:round(.95*RATE)]
        a=mix((body,0,.80),(hard,.012,.62),(sosfilt(butter(2,450,fs=RATE,output='sos'),shell),.025,.48))
        name=f'eva_contact_r34_{i}';report.append(write(name,a));events.setdefault('eva_impact',[]).append(name)
    for i in range(3):
        hit=level(pitch(impacts[i],.53+i*.035));ring=sosfilt(butter(2,750,fs=RATE,output='sos'),level(pitch(metal,.63+i*.025)))
        name=f'eva_step_r34_{i}';report.append(write(name,mix((hit,0,.9),(ring[:round(.9*RATE)],.018,.3))));events.setdefault('eva_foot_concrete',[]).append(name)
    for i in range(2):
        a=pitch(whoosh,.70+i*.08);start=int(np.argmax(abs(a)));a=a[max(0,start-round(.17*RATE)):start+round(.30*RATE)]
        name=f'eva_sweep_r34_{i}';report.append(write(name,a));events.setdefault('eva_swing',[]).append(name)
    for event,names in events.items():
        defs[event]['sounds']=[{'name':'projectseele:'+n,'attenuation_distance':384} for n in names]
    for event,base in [('eva_armor_impact','eva_impact'),('eva_at_pressure','eva_impact'),('eva_land','eva_foot_concrete'),('eva_foot_soil','eva_foot_concrete')]:
        defs[event]['sounds']=copy=[dict(s) for s in defs[base]['sounds']]
        for sound in copy:sound['pitch']=.85 if event=='eva_land' else .95
    (ASSET/'sounds.json').write_text(json.dumps(defs,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    sources=[{'author':'qubodup','url':'https://freesound.org/people/qubodup/sounds/482134/','file':'punch_qubodup.mp3'}, {'author':'qubodup','url':'https://freesound.org/people/qubodup/sounds/60013/','file':'whoosh.mp3'}, {'author':'rifualk','url':'https://freesound.org/people/rifualk/sounds/613466/','file':'metal_concrete.mp3'}, {'author':'magnuswaker','url':'https://freesound.org/s/614063/','file':'heavy_metal.mp3'}]
    for s in sources:s.update(license='CC0 1.0',sha256=hashlib.sha256((SRC/s['file']).read_bytes()).hexdigest())
    pack=OUT/'eva_roar_r34';dest=pack/'assets/projectseele';(dest/'sounds').mkdir(parents=True,exist_ok=True)
    (pack/'pack.mcmeta').write_text(json.dumps({'pack':{'pack_format':15,'description':'R34 EVA roar - sourced community clip, local audition'}}))
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(SRC/'roar_toddyn.mp3'),'-ac','1','-af','afade=t=in:d=0.008,afade=t=out:st=5.08:d=0.18,alimiter=limit=0.89:level=false','-c:a','libvorbis','-q:a','6',str(dest/'sounds/eva_roar_sourced_r34.ogg')],check=True)
    (dest/'sounds.json').write_text(json.dumps({'eva_berserk_roar':{'replace':True,'subtitle':'subtitles.projectseele.eva_berserk_roar','sounds':[{'name':'projectseele:eva_roar_sourced_r34','attenuation_distance':512}]}}))
    roar={'url':'https://tuna.voicemod.net/sound/46e80a30-57f0-4b20-8788-9c4e4d44da35','uploader':'TODDYN','title':'Eva Unit 01 Roar','duration':5.28,'license':'No redistribution license verified; local user-requested audition only','authenticity':'EVA-labelled community extract; TV/Japanese master version unverified','processing':'Mono conversion and short fade only; no synthesized substitute','sha256':hashlib.sha256((SRC/'roar_toddyn.mp3').read_bytes()).hexdigest()}
    (OUT/'sources.json').write_text(json.dumps({'recordings':sources,'outputs':report,'local_roar':roar,'auditory_review':'Audio input is unavailable to this agent; no subjective listening approval claimed.'},indent=2))
    print('Recorded combat cues:',len(report),'local roar pack:',pack)
if __name__=='__main__':main()
