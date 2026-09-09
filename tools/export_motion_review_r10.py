"""Review movies preserve native capture timing and separate the three actionable motion groups."""
import argparse,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/first_battle_world_r10/motion'
def main(batch):
 rows=[json.loads(line) for line in (batch/'poses.jsonl').read_text(encoding='utf8').splitlines()];manifest=[]
 for name,start,end in [('rifle_stances',0,805),('heavy_and_knife',805,999),('walk_run_jump',1000,1399)]:
  frames=[r for r in rows if start<=r['tick']<=end];lines=[]
  for i,r in enumerate(frames):
   image=(batch/f"frame_{r['image']:04d}.png").resolve();assert image.is_file(),image;next_tick=frames[i+1]['tick'] if i+1<len(frames) else end+1
   lines.extend([f"file '{image.as_posix()}'",f"duration {max(1,next_tick-r['tick'])/20:.6f}"])
  lines.append(f"file '{image.as_posix()}'");source=OUT/(name+'.concat.txt');source.write_text('\n'.join(lines)+'\n',encoding='utf8');target=OUT/(name+'_r10.mp4')
  subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(source),'-fps_mode','vfr','-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],check=True)
  probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration,size','-of','json',str(target)]))
  manifest.append(dict(file=str(target),first_tick=frames[0]['tick'],last_tick=frames[-1]['tick'],frames=len(frames),**probe['format']));print(name,probe)
 (OUT/'native_video_manifest.json').write_text(json.dumps(dict(source=str(batch),videos=manifest,timing='Native game ticks / 20, missing captures held; no generated interpolation',audio='silent geometry review'),indent=2),encoding='utf8')
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('batch',type=Path);main(ap.parse_args().batch.resolve())
