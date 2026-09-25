"""Check installed R38 code-side assets without modifying a world."""
from pathlib import Path
import contextlib,hashlib,io,json
from check_runtime_r37 import check as foundation
ROOT=Path(__file__).resolve().parents[1]
def check():
    with contextlib.redirect_stdout(io.StringIO()):foundation()
    marker=json.loads((ROOT/'run/projectseele-local-maps/revision_r38.json').read_text())
    shader=ROOT/'run/shaderpacks'/marker['shader']['filename']
    if marker['protocol']!=43 or hashlib.sha256(shader.read_bytes()).hexdigest()!=marker['shader']['sha256']:raise ValueError('Missing reviewed R38 shader or runtime marker')
    print('R38 assets ready; protocol 43. Formal world retained.')
if __name__=='__main__':check()
