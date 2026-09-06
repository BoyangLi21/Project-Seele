"""Stage a fresh TV world, retaining a cold copy of the current playable source."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil

import nbtlib

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'run/saves/SEELE_PYRAMID_TV_PREVIEW_20260905'
TARGET = ROOT / 'run/saves/SEELE_TV_WORLD_PREVIEW_20260906'
OUT = ROOT / 'artifacts/tv_world_preview_20260906'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, required=True)
    args = parser.parse_args()
    if TARGET.exists():
        raise RuntimeError(f'Refusing to replace existing preview: {TARGET}')
    if not (SOURCE / '.projectseele_pyramid_tv_preview.json').is_file():
        raise RuntimeError('Latest TV interior source marker missing')
    OUT.mkdir(parents=True, exist_ok=True)
    backup = ROOT / 'backups' / ('SEELE_TV_SOURCE_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    shutil.copytree(SOURCE, backup)
    manifest = {str(p.relative_to(SOURCE)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in SOURCE.rglob('*') if p.is_file()}
    (OUT / 'source_sha256.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    TARGET.mkdir()
    level = nbtlib.load(SOURCE / 'level.dat')
    data = level['Data']
    data['LevelName'] = nbtlib.String('SEELE - TV World Reconstruction Preview')
    data['WorldGenSettings']['seed'] = nbtlib.Long(args.seed)
    data['RandomSeed'] = nbtlib.Long(args.seed)
    generator = data['WorldGenSettings']['dimensions']['projectseele:geofront']['generator']
    generator['surface_datum'] = nbtlib.Int(80)
    generator['tv_preview'] = nbtlib.Byte(1)
    # The dimension registry is rebuilt from datapacks on load. A level.dat
    # generator tag alone is overwritten by the mod's default dimension.
    pack = TARGET / 'datapacks/tv_world_preview'
    definition = pack / 'data/projectseele/dimension/geofront.json'
    definition.parent.mkdir(parents=True)
    (pack / 'pack.mcmeta').write_text(json.dumps({'pack': {'pack_format': 15,
        'description': 'Private TV world preview: save-local GeoFront generation'}}), encoding='utf-8')
    definition.write_text(json.dumps({'type': 'projectseele:geofront', 'generator': {
        'type': 'projectseele:geofront_bounded', 'settings': 'projectseele:geofront_surface',
        'biome_source': {'type': 'minecraft:fixed', 'biome': 'projectseele:geofront_surface'},
        'candidate_index': 0, 'surface_datum': 80, 'tv_preview': True}}, indent=2), encoding='utf-8')
    dimension_type = json.loads((ROOT / 'src/main/resources/data/projectseele/dimension_type/geofront.json').read_text())
    dimension_type['effects'] = 'projectseele:tv_geofront'
    effects_path = pack / 'data/projectseele/dimension_type/geofront.json'
    effects_path.parent.mkdir(parents=True)
    effects_path.write_text(json.dumps(dimension_type, indent=2), encoding='utf-8')
    biome = json.loads((ROOT / 'src/main/resources/data/projectseele/worldgen/biome/geofront_surface.json').read_text())
    biome['effects']['foliage_color'] = 0x527442
    biome['effects']['grass_color'] = 0x7B9053
    biome_path = pack / 'data/projectseele/worldgen/biome/geofront_surface.json'
    biome_path.parent.mkdir(parents=True)
    biome_path.write_text(json.dumps(biome, indent=2), encoding='utf-8')
    data['DataPacks']['Enabled'].append(nbtlib.String('file/tv_world_preview'))
    data['SpawnX'], data['SpawnY'], data['SpawnZ'] = nbtlib.Int(30), nbtlib.Int(90), nbtlib.Int(296)
    data['GameType'], data['allowCommands'] = nbtlib.Int(1), nbtlib.Byte(1)
    data['Player']['Dimension'] = nbtlib.String('minecraft:overworld')
    data['Player']['Pos'] = nbtlib.List[nbtlib.Double]([30.5, 90.0, 296.5])
    data['Player']['Motion'] = nbtlib.List[nbtlib.Double]([0.0, 0.0, 0.0])
    data['Player']['playerGameType'] = nbtlib.Int(1)
    data['Player'].pop('RootVehicle', None)
    level.save(TARGET / 'level.dat', gzipped=True)
    if (SOURCE / 'serverconfig').is_dir():
        shutil.copytree(SOURCE / 'serverconfig', TARGET / 'serverconfig')
    marker = {'revision': 1, 'source': str(SOURCE), 'source_backup': str(backup),
              'seed': args.seed, 'phase': 'terrain_staging',
              'facility_transform': [0, 0, 0], 'source_chunks_copied': False,
              'legacy_terrain_copied': False, 'handed_off': False}
    (TARGET / '.projectseele_tv_world_preview.json').write_text(json.dumps(marker, indent=2), encoding='utf-8')
    (TARGET / '.projectseele_spatial_preview_read_only.json').write_text(
        json.dumps({'reason': 'Only the explicit TV preview tools may author this world.'}), encoding='utf-8')
    print(json.dumps(marker, indent=2))


if __name__ == '__main__':
    main()
