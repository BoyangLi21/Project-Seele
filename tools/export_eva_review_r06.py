"""Encode native screenshots with their game-tick durations, preserving dropped-frame timing."""
import argparse,json,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/motion_review_r06'
def main(batch):
    rows=[json.loads(line) for line in (batch/'poses.jsonl').read_text(encoding='utf-8').splitlines()]
    recipes=[('eva_r06_rifle_stances',0,805,'R06 | Unit-01 | Walk - kneel - prone - stand'),
             ('eva_r06_heavy_knife',805,999,'R06 | Unit-01 | Unarmed heavy - knife'),
             ('eva_r06_three_units',0,2999,'R06 | Native gameplay | Unit-01 / Unit-00 / Unit-02')]
    manifest=[]
    for name,start,end,title in recipes:
        frames=[r for r in rows if start<=r['tick']<=end];lines=[]
        for i,r in enumerate(frames):
            file=(batch/f"frame_{r['image']:04d}.png").resolve()
            if not file.is_file():raise FileNotFoundError(file)
            next_tick=frames[i+1]['tick'] if i+1<len(frames) else end+1
            lines.extend([f"file '{file.as_posix()}'",f"duration {max(1,next_tick-r['tick'])/20:.6f}"])
        lines.append(f"file '{file.as_posix()}'")
        source=OUT/(name+'.concat.txt');source.write_text('\n'.join(lines)+'\n',encoding='utf-8')
        label=OUT/(name+'.title.txt');label.write_text(title,encoding='utf-8')
        # The filter uses relative, ASCII paths to avoid Windows drive-colon escaping.
        overlay=f"drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf':textfile='artifacts/motion_review_r06/{name}.title.txt':x=24:y=22:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=10"
        target=OUT/(name+'.mp4')
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(source),
                        '-vf',overlay,'-r','20','-c:v','libx264','-preset','fast','-crf','22','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],cwd=ROOT,check=True)
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration,size','-of','json',str(target)]))
        manifest.append(dict(file=str(target),source_frames=len(frames),first_tick=frames[0]['tick'],last_tick=frames[-1]['tick'],timing='game ticks / 20; missing captures held, no motion interpolation',**probe['format']))
        print(name,probe['format'],flush=True)
    (OUT/'video_manifest.json').write_text(json.dumps(dict(batch=str(batch),videos=manifest),indent=2),encoding='utf-8')
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('batch',type=Path);main(ap.parse_args().batch.resolve())
