"""Check the current private assets and pinned R39 shader without touching saves."""
from pathlib import Path
import contextlib,hashlib,io,json
from check_runtime_r37 import check as foundation
ROOT=Path(__file__).resolve().parents[1]
def check():
    with contextlib.redirect_stdout(io.StringIO()):foundation()
    marker=json.loads((ROOT/'run/projectseele-local-maps/revision_r39.json').read_text())
    shader=ROOT/'run/shaderpacks'/marker['shader']['filename']
    if marker['protocol']!=44 or hashlib.sha256(shader.read_bytes()).hexdigest()!=marker['shader']['sha256']:raise ValueError('Missing R39 facility shader or runtime marker')
    print('R39 assets ready; protocol 44. Original world retained.')
if __name__=='__main__':check()
