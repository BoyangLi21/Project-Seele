"""Encode the native framebuffer sequence with its recorded server-tick timing."""
import argparse
import json
from pathlib import Path
import subprocess


def export(batch, output, first, last, speed=1):
    rows = [json.loads(line) for line in (batch / 'poses.jsonl').read_text(encoding='utf-8').splitlines()]
    selected = [row for row in rows if first <= row['tick'] <= last]
    if not selected:
        raise ValueError('No frames in requested interval')
    timeline = output.with_suffix('.ffconcat')
    entries = ['ffconcat version 1.0']
    for index, row in enumerate(selected):
        image = batch / f"frame_{row['image']:04d}.png"
        if not image.is_file():
            raise FileNotFoundError(image)
        next_tick = selected[index + 1]['tick'] if index + 1 < len(selected) else row['tick'] + 1
        escaped = image.resolve().as_posix().replace("'", "'\\''")
        entries += [f"file '{escaped}'", f"duration {(next_tick-row['tick'])/20/speed:.8f}"]
    entries.append(entries[-2])
    timeline.write_text('\n'.join(entries) + '\n', encoding='utf-8')
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'warning', '-y',
                    '-f', 'concat', '-safe', '0', '-i', str(timeline),
                    '-vf', 'fps=30', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19',
                    '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(output)], check=True)
    print(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('batch', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--first', type=int, default=0)
    parser.add_argument('--last', type=int, default=649)
    parser.add_argument('--speed', type=float, default=1)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    export(args.batch, args.output, args.first, args.last, args.speed)
