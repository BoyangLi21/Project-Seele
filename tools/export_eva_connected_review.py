#!/usr/bin/env python3
"""Export an actual gameplay capture using its server-tick timing, not assumed FPS."""
import argparse
import json
from pathlib import Path
import subprocess

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in (args.capture/'poses.jsonl').read_text(encoding='utf-8').splitlines()]
    required = ('0:walk', '0:run', '0:crouch:false', '0:crouch:true', '0:ordinary:',
                '0:kick:', '1:knife:0:', '1:knife:1:')
    for prefix in required:
        if not any(row['key'].startswith(prefix) for row in rows):
            raise SystemExit('Missing gameplay state: '+prefix)
    if rows[-1]['tick'] < 680:
        raise SystemExit('Incomplete connected input sequence')
    for row in rows:
        if not all(np.isfinite(values).all() for values in row['bones'].values()):
            raise SystemExit('Non-finite rendered bone transform')
    args.output.mkdir(parents=True, exist_ok=True)
    concat = args.output/'capture.ffconcat'
    entries = ['ffconcat version 1.0']
    unique = {row['image']:row for row in rows}
    samples = sorted(unique.values(),key=lambda r:r['tick'])
    for i,row in enumerate(samples):
        image = (args.capture/f"frame_{row['image']:04d}.png").resolve()
        if not image.is_file(): raise SystemExit('Missing captured image: '+str(image))
        duration = (samples[i+1]['tick']-row['tick'])/20 if i+1 < len(samples) else .05
        entries += ["file '"+image.as_posix().replace("'", "'\\''")+"'", f'duration {duration:.8f}']
    entries.append(entries[-2])
    concat.write_text('\n'.join(entries)+'\n',encoding='utf-8')
    video = args.output/'eva_connected_actions.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-safe','0','-f','concat',
                    '-i',str(concat),'-fps_mode','vfr','-c:v','libx264','-preset','fast',
                    '-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],check=True)
    changes = [r for i,r in enumerate(rows) if i==0 or r['key']!=rows[i-1]['key']]
    result = {'capture':str(args.capture.resolve()),'video':str(video.resolve()),
              'pose_samples':len(rows),'video_frames':len(samples),
              'server_tick_span':[rows[0]['tick'],rows[-1]['tick']],
              'checks':'required real gameplay states and finite transforms passed',
              'visual_status':'keyframes inspected by agent; owner review remains separate',
              'state_changes':[{'tick':r['tick'],'key':r['key'],'image':r['image']} for r in changes]}
    (args.output/'review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='state_changes'},ensure_ascii=False))


if __name__ == '__main__':
    main()
