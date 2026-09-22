"""Original brief radio identification, using standard neural Mandarin voices."""
from pathlib import Path
import asyncio,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/facility_r30/mission_audio';ASSET=ROOT/'src/main/resources/assets/projectseele'
sys.path.insert(0,str(ROOT/'.Codex/audio-runtime'))
import edge_tts
LINES=[('pa_signal_r30','发现异常反应。','zh-CN-XiaoyiNeural','+5%',1.68),('pa_blue_r30','波形蓝色，是使徒。','zh-CN-XiaoyiNeural','+15%',1.68),('pa_alert_r30','全员进入第一战斗配置。','zh-CN-XiaoxiaoNeural','+0%',4.5)]
def duration(p):return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(p)]))
def convert(source,target,filters):subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(source),'-af',filters,'-ar','48000','-ac','1','-c:a','libvorbis','-q:a','5',str(target)],check=True)
async def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for name,text,voice,rate,limit in LINES:
        mp3=OUT/(name+'.mp3')
        if not mp3.exists():await edge_tts.Communicate(text,voice,rate=rate,pitch='-1Hz').save(str(mp3))
        trim='silenceremove=start_periods=1:start_threshold=-48dB:start_silence=0.02,areverse,silenceremove=start_periods=1:start_threshold=-48dB:start_silence=0.03,areverse'
        draft=OUT/(name+'_trim.ogg');convert(mp3,draft,trim)
        speed=max(1,duration(draft)/(limit-.05));assert speed<=1.4,(name,speed)
        target=OUT/(name+'.ogg');convert(draft,target,f'atempo={speed},highpass=f=100,lowpass=f=8500,loudnorm=I=-18:TP=-2:LRA=8');assert duration(target)<=limit
        print(name,round(duration(target),3),'seconds',flush=True)
    events_path=ASSET/'sounds.json';events=json.loads(events_path.read_text(encoding='utf8'));rows=[]
    for name,text,voice,rate,limit in LINES:
        source=OUT/(name+'.ogg');target=ASSET/'sounds'/(name+'.ogg');target.write_bytes(source.read_bytes())
        events[name]={'subtitle':'subtitles.projectseele.'+name,'sounds':[{'name':'projectseele:'+name,'attenuation_distance':160}]}
        rows.append({'name':name,'text':text,'voice':voice,'seconds':duration(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source':'Original project wording; standard Microsoft neural synthesis through the existing edge-tts runtime. No TV recording or actor voice imitation.','reference':'https://learn.microsoft.com/azure/ai-services/speech-service/language-support?tabs=tts'})
    events_path.write_text(json.dumps(events,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for code in ('zh_cn','en_us'):
        p=ASSET/'lang'/(code+'.json');data=json.loads(p.read_text(encoding='utf8'))
        for name,text,_,_,_ in LINES:data['subtitles.projectseele.'+name]=text if code=='zh_cn' else {'pa_signal_r30':'Abnormal signal detected.','pa_blue_r30':'Pattern blue. Angel confirmed.','pa_alert_r30':'All personnel, combat stations.'}[name]
        p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (OUT/'sources.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
if __name__=='__main__':asyncio.run(main())
