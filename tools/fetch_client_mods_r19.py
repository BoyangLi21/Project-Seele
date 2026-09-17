"""Pinned exact-terrain renderer and client navigation dependencies."""
import json
import fetch_renderer_mods_r17 as r17

def main():
    r17.base.MODS = [row for row in r17.base.MODS if not row[0].startswith('DistantHorizons')]
    for mod in json.loads((r17.base.ROOT / 'tools/client_navigation_r19.json').read_text()):
        r17.base.MODS.append((mod['filename'], mod['project_id'], mod['version_id'], mod['sha512']))
    r17.base.main()

if __name__ == '__main__':
    main()
