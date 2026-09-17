"""Migrate the default test profile away from LOD meshes without losing user settings."""
from pathlib import Path
import datetime, json, shutil

ROOT = Path(__file__).resolve().parents[1]

def ensure_local(game):
    game = Path(game).resolve()
    marker = game / 'config/projectseele-rendering-r19.json'
    if marker.exists() and json.loads(marker.read_text()).get('profile_revision',0)>=3:
        return
    backup = ROOT / 'artifacts/world_repair_r19/client_backup' / datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup.mkdir(parents=True)
    options = game / 'options.txt'
    if options.exists():
        shutil.copy2(options, backup / 'options.txt')
    lines = options.read_text(encoding='utf8').splitlines() if options.exists() else []
    changes = {'renderDistance':'24', 'simulationDistance':'8',
        'key_gui.xaero_new_waypoint':'key.keyboard.n',
        'key_gui.xaero_enlarge_map':'key.keyboard.backslash',
        'key_gui.xaero_zoom_in':'key.keyboard.right.bracket',
        'key_gui.xaero_zoom_out':'key.keyboard.left.bracket',
        'key_gui.xaero_toggle_manual_cave_mode':'key.keyboard.f8',
        'key_gui.xaero_open_settings':'key.keyboard.unknown'}
    seen = set()
    result = []
    for line in lines:
        key, sep, value = line.partition(':')
        result.append(key + ':' + changes[key] if sep and key in changes else line)
        seen.add(key)
    result.extend(k + ':' + v for k,v in changes.items() if k not in seen)
    options.write_text('\n'.join(result)+'\n', encoding='utf8')
    hud=game/'config/xaerohud.txt'
    if hud.exists():
        shutil.copy2(hud,backup/hud.name)
        lines=hud.read_text(encoding='utf8').splitlines()
        hud.write_text('\n'.join(line.replace('fromRight=false','fromRight=true') if 'id=xaerominimap:minimap;' in line else line for line in lines)+'\n',encoding='utf8')
    # A manually installed copy would still be loaded despite the Gradle flag.
    # Move only named LOD / retained-chunk mods, retaining a reversible backup.
    retired=[]
    mods=game/'mods'
    if mods.is_dir():
        for path in mods.glob('*.jar'):
            if path.name.lower().startswith(('distanthorizons','farsight','cupboard')):
                target=backup/path.name
                shutil.move(str(path),str(target));retired.append(path.name)
    marker.parent.mkdir(parents=True,exist_ok=True)
    marker.write_text(json.dumps({'profile_revision':3,'terrain':'full blocks','render_distance':24,
        'simulation_distance':8,'lod_enabled':False,'backup':str(backup),'retired_mods':retired},indent=2),encoding='utf8')

if __name__ == '__main__':
    ensure_local(ROOT/'run')
