"""Record the selected speaker's WASAPI loopback while the native review runs.

No microphone capture, driver changes, or synthetic replacement soundtrack.
"""
from contextlib import contextmanager
import json,time,threading,wave
from pathlib import Path
import numpy as np

@contextmanager
def capture(path,start_log=None,marker='R31 COMBAT phase=WARM'):
    if path is None:yield;return
    import soundcard as sc
    path=Path(path).resolve()
    if path.exists():raise FileExistsError(path)
    path.parent.mkdir(parents=True,exist_ok=True);stop=threading.Event();ready=threading.Event();errors=[];meta={};rate=48000;began=time.time()
    def worker():
        try:
            if start_log is not None:
                log=Path(start_log)
                while not stop.is_set():
                    if log.exists() and log.stat().st_mtime>=began:
                        with log.open('rb') as stream:
                            stream.seek(max(0,log.stat().st_size-24000))
                            if marker.encode() in stream.read():break
                    stop.wait(.10)
                if stop.is_set():raise RuntimeError('Game never reached the audio capture marker')
            speaker=sc.default_speaker();loop=sc.get_microphone(speaker.id,include_loopback=True)
            with wave.open(str(path),'wb') as out,loop.recorder(samplerate=rate,channels=2,blocksize=960) as source:
                out.setnchannels(2);out.setsampwidth(2);out.setframerate(rate);frames=0;peak=0
                while not stop.is_set():
                    data=source.record(numframes=960)
                    if not frames:
                        meta.update(start_epoch_seconds=time.time()-len(data)/rate,sample_rate=rate,channels=2,source='Windows WASAPI selected-speaker loopback',alignment='System epoch timestamps; 20 ms capture blocks plus endpoint buffering',start_marker=marker if start_log else None);ready.set()
                    frames+=len(data);peak=max(peak,float(abs(data).max()));out.writeframesraw((np.clip(data,-1,1)*32767).astype('<i2').tobytes())
                meta.update(frames=frames,seconds=frames/rate,peak=peak,end_epoch_seconds=time.time())
            path.with_suffix('.capture.json').write_text(json.dumps(meta,indent=2))
        except BaseException as error:errors.append(error);ready.set()
    thread=threading.Thread(target=worker,daemon=True);thread.start()
    if start_log is None:
        if not ready.wait(8):raise RuntimeError('WASAPI capture did not initialize')
        if errors:raise errors[0]
    try:yield
    finally:
        stop.set();thread.join(5)
        if thread.is_alive():raise RuntimeError('WASAPI recorder did not close')
        if errors:raise errors[0]
