"""Encode the real framebuffer sequence at its recorded wall-clock timing, without invented frames."""
from pathlib import Path
import argparse,json,math,shutil,subprocess

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('folder',type=Path)
    args=parser.parse_args()
    folder=args.folder.resolve(strict=True)
    if not folder.is_relative_to((ROOT/'artifacts/facility_r31').resolve()):
        raise ValueError('Use an R31 native recording folder')
    source=json.loads((folder/'client_evidence.json').read_text(encoding='utf8'))
    if source.get('server_failure'):raise ValueError('The native sequence ended in a failed case')
    frames=source['frames']
    if len(frames)<120:raise ValueError('Run the native fixture with --video before exporting')
    rows=[]
    for index,frame in enumerate(frames):
        path=(folder/frame['file']).resolve(strict=True)
        if path.parent!=folder or not path.name.startswith('contact_') or path.suffix!='.jpg':
            raise ValueError('Unexpected frame path')
        if index+1<len(frames):duration=frames[index+1]['render_elapsed_seconds']-frame['render_elapsed_seconds']
        else:duration=1/24
        if not math.isfinite(duration) or duration<=0:raise ValueError('Invalid native capture timing')
        rows.extend(["file '"+path.name+"'",f'duration {duration:.9f}'])
    rows.append("file '"+(folder/frames[-1]['file']).name+"'")
    manifest=folder/'native_video.ffconcat'
    manifest.write_text('ffconcat version 1.0\n'+'\n'.join(rows)+'\n',encoding='utf8')
    output=folder/'R31_native_combat_silent.mp4'
    if output.exists():raise FileExistsError('Do not replace an earlier exported recording')
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg:raise FileNotFoundError('ffmpeg')
    subprocess.run([ffmpeg,'-hide_banner','-loglevel','warning','-n','-f','concat','-safe','1',
                    '-i',str(manifest),'-an','-c:v','libx264','-preset','medium','-crf','21',
                    '-pix_fmt','yuv420p','-fps_mode','vfr','-movflags','+faststart',str(output)],check=True)
    metadata={'output':str(output),'source_frames':len(frames),'timing':'recorded_render_wall_clock',
              'audio':False,'interpolated_frames':False,'scene':'isolated_native_combat_fixture',
              'bytes':output.stat().st_size}
    (folder/'video_provenance.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(metadata,ensure_ascii=False))

if __name__=='__main__':main()
