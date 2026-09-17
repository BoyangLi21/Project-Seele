"""Encode actual client frames with their recorded filesystem timing."""
from pathlib import Path
import json,subprocess

ROOT=Path(__file__).resolve().parents[1];SOURCE=ROOT/'artifacts/world_repair_r19/un_terrain_1789599062527';OUT=ROOT/'artifacts/world_repair_r19/media'
NAMES={0:'Street props',1:'Walking up steps',2:'Running downhill',3:'Running over slabs',4:'Crouched steps',5:'Prone passage',6:'Moving jump',7:'Diagonal curbs',8:'Prone incline',9:'Continuous stance changes'}

def main():
    OUT.mkdir(parents=True,exist_ok=True);clips=[];records=[]
    for index,name in NAMES.items():
        frames=sorted((SOURCE/f'clip_{index}').glob('*.jpg'))
        if len(frames)<2:continue
        listing=OUT/f'frames_{index}.txt';rows=[];times=[p.stat().st_mtime_ns/1e9 for p in frames];duration=0.
        for i,frame in enumerate(frames):
            dt=max(.025,min(.5,times[i+1]-times[i])) if i+1<len(frames) else .05
            rows.extend(["file '"+frame.as_posix()+"'",'duration '+str(dt)]);duration+=dt
        rows.append("file '"+frames[-1].as_posix()+"'");listing.write_text('\n'.join(rows)+'\n')
        clip=OUT/f'un00_{index:02d}.mp4';label=OUT/f'label_{index}.txt';label.write_text(f'{index+1:02d}  {name}',encoding='utf8')
        # Forward-slash paths and escaped drive colon are filter syntax, not
        # shell interpolation; subprocess receives an exact argument array.
        text_path=label.as_posix().replace(':',r'\:')
        vf="fps=20,drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf':textfile='"+text_path+"':fontcolor=white:fontsize=24:x=24:y=20:box=1:boxcolor=black@0.6:boxborderw=10"
        subprocess.run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(listing),'-vf',vf,'-c:v','libx264','-preset','fast','-crf','25','-maxrate','1500k','-bufsize','3M','-pix_fmt','yuv420p','-movflags','+faststart',str(clip)],check=True)
        clips.append(clip);records.append(dict(case=index,label=name,source_frames=len(frames),measured_duration=duration,file=str(clip)))
    concat=OUT/'un00_clips.txt';concat.write_text('\n'.join("file '"+p.as_posix()+"'" for p in clips)+'\n')
    final=OUT/'EVA-UN-00_native_motion_R19.mp4';subprocess.run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(concat),'-c','copy','-movflags','+faststart',str(final)],check=True)
    (OUT/'motion_video.json').write_text(json.dumps({'file':str(final),'bytes':final.stat().st_size,'source':'Native Minecraft framebuffer captures; no synthesized movement','timing':'Frame-file completion timestamps; pauses clipped at 0.5 s','clips':records},indent=2))
    print(final,final.stat().st_size)

if __name__=='__main__':main()
