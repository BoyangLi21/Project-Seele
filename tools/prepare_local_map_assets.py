#!/usr/bin/env python3
"""Prepare private Tokyo-3/NERV map assets for the Forge 1.20.1 client.

Downloaded inputs remain below external-assets and are never distributed.
This converts the useful structures and stages a separate complete test save;
source archives and existing saves are never modified.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import shutil
from typing import Iterable

import nbtlib
from nbtlib import Compound, File, Int, List, String

from inspect_map_assets import decode_modern_section, iter_chunks, palette_name


ROOT = Path(__file__).resolve().parents[1]
TARGET_DATA_VERSION = 3465
LOCAL_ASSET_DIR = ROOT / "run" / "projectseele-local-maps"
COMMAND_WORLD = (ROOT / "external-assets" / "work" / "maps"
                 / "source_nerv_command" / "Nerv Comand Module")
TOKYO3_WORLD = (ROOT / "external-assets" / "work" / "maps"
                / "source_eva_bilibili" / "EVA")
SKYSCRAPER_SCHEM = (ROOT / "external-assets" / "incoming" / "maps"
                    / "tokyo-3-type-skyscrapper1-converted.schem")
WORLD_TEMPLATE_CANDIDATES = (
    ROOT / "run" / "saves" / "New World",
    ROOT / "run" / "saves" / "New World (38)",
)
STAGED_WORLD = ROOT / "run" / "saves" / "SEELE_TOKYO3_REBUILT"
STAGED_WORLD_SCHEMA = 10

# The download contains two identical command modules. This is the complete
# left-hand copy, determined from six horizontal density slices.
COMMAND_BOUNDS = (1, -61, -33, 56, 15, 95)
COMMAND_PLACEMENT_OFFSET = (-28, -21, -33)
SKYSCRAPER_PLACEMENTS = (
    (-140, 1, -70, "none"),
    (120, 1, -92, "clockwise_90"),
    (112, 1, 82, "clockwise_180"),
)

AIR = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}
COMMAND_BACKGROUND = AIR | {
    "minecraft:bedrock", "minecraft:dirt", "minecraft:grass_block",
}
NAME_DOWNGRADES = {
    "minecraft:andesite_wall": "minecraft:polished_deepslate_wall",
    "minecraft:stripped_pale_oak_log": "minecraft:stripped_birch_log",
    "minecraft:pale_oak_door": "minecraft:birch_door",
    "minecraft:pale_oak_wall_sign": "minecraft:birch_wall_sign",
    "minecraft:pale_oak_sign": "minecraft:birch_sign",
    "minecraft:pale_oak_trapdoor": "minecraft:birch_trapdoor",
    "minecraft:waxed_exposed_copper_trapdoor": "minecraft:iron_trapdoor",
}

State = tuple[str, tuple[tuple[str, str], ...]]


def tag_list(values: Iterable[int]) -> List[Int]:
    return List[Int]([Int(value) for value in values])


def normalise_state(name: str,
                    properties: dict[str, str] | None = None) -> State:
    mapped = NAME_DOWNGRADES.get(name, name)
    values = dict(properties or {})
    if mapped == "minecraft:iron_trapdoor":
        values = {key: value for key, value in values.items()
                  if key in {"facing", "half", "open", "powered",
                             "waterlogged"}}
    return mapped, tuple(sorted(values.items()))


def state_from_palette(entry: Compound) -> State:
    properties = entry.get("Properties", {})
    return normalise_state(
        palette_name(entry),
        {str(key): str(value) for key, value in properties.items()},
    )


def parse_state_text(text: str) -> State:
    if "[" not in text:
        return normalise_state(text)
    name, raw = text[:-1].split("[", 1)
    properties = {}
    if raw:
        for item in raw.split(","):
            key, value = item.split("=", 1)
            properties[key] = value
    return normalise_state(name, properties)


def state_tag(state: State) -> Compound:
    name, properties = state
    result = Compound({"Name": String(name)})
    if properties:
        result["Properties"] = Compound(
            {key: String(value) for key, value in properties})
    return result


def clean_block_entity(value: Compound) -> Compound:
    copied = Compound({str(key): item for key, item in value.items()
                       if str(key) not in {
                           "x", "y", "z", "keepPacked", "components"}})
    if str(copied.get("id", "")) != "minecraft:sign":
        return copied
    for side_name in ("front_text", "back_text"):
        side = copied.get(side_name)
        if not isinstance(side, Compound):
            continue
        messages = []
        for raw in list(side.get("messages", []))[:4]:
            text = str(raw)
            try:
                decoded = json.loads(text)
                if not isinstance(decoded, (dict, list)):
                    raise ValueError
                messages.append(text)
            except (json.JSONDecodeError, ValueError):
                messages.append(json.dumps(
                    {"text": text}, ensure_ascii=False,
                    separators=(",", ":")))
        while len(messages) < 4:
            messages.append('{"text":""}')
        side["messages"] = List[String](
            [String(message) for message in messages])
        side.pop("filtered_messages", None)
    return copied


def save_structure(path: Path, size: tuple[int, int, int],
                   states: list[State], blocks: list[Compound]) -> None:
    root = Compound({
        "DataVersion": Int(TARGET_DATA_VERSION),
        "size": tag_list(size),
        "palette": List[Compound]([state_tag(value) for value in states]),
        "blocks": List[Compound](blocks),
        "entities": List[Compound]([]),
    })
    path.parent.mkdir(parents=True, exist_ok=True)
    File(root).save(path, gzipped=True)


def convert_command_module(output: Path) -> dict:
    if not (COMMAND_WORLD / "level.dat").is_file():
        raise FileNotFoundError(f"NERV command world not found: {COMMAND_WORLD}")
    min_x, min_y, min_z, max_x, max_y, max_z = COMMAND_BOUNDS
    bounds = (min_x // 16, max_x // 16, min_z // 16, max_z // 16)
    size = (max_x - min_x + 1, max_y - min_y + 1, max_z - min_z + 1)
    state_ids: dict[State, int] = {}
    states: list[State] = []
    pending: dict[tuple[int, int, int], tuple[int, Compound | None]] = {}
    block_entities: dict[tuple[int, int, int], Compound] = {}
    downgraded: Counter[str] = Counter()

    chunks = list(iter_chunks(COMMAND_WORLD, bounds))
    for _, _, root in chunks:
        data = root.get("Level", root)
        for value in data.get("block_entities", data.get("TileEntities", [])):
            position = (int(value.get("x", 0)), int(value.get("y", 0)),
                        int(value.get("z", 0)))
            if (min_x <= position[0] <= max_x
                    and min_y <= position[1] <= max_y
                    and min_z <= position[2] <= max_z):
                block_entities[position] = clean_block_entity(value)

    for chunk_x, chunk_z, root in chunks:
        data = root.get("Level", root)
        for section in data.get("sections", data.get("Sections", [])):
            section_y = int(section["Y"])
            if section_y * 16 > max_y or section_y * 16 + 15 < min_y:
                continue
            palette, indices = decode_modern_section(section)
            if not palette:
                continue
            converted = [state_from_palette(entry) for entry in palette]
            for original, mapped in zip(palette, converted):
                old_name = palette_name(original)
                if old_name != mapped[0]:
                    downgraded[f"{old_name}->{mapped[0]}"] += 1
            for index in range(4096):
                x = chunk_x * 16 + (index & 15)
                z = chunk_z * 16 + ((index >> 4) & 15)
                y = section_y * 16 + (index >> 8)
                if not (min_x <= x <= max_x and min_y <= y <= max_y
                        and min_z <= z <= max_z):
                    continue
                state = converted[int(indices[index])]
                if state[0] in COMMAND_BACKGROUND:
                    continue
                state_id = state_ids.get(state)
                if state_id is None:
                    state_id = len(states)
                    state_ids[state] = state_id
                    states.append(state)
                source_position = (x, y, z)
                pending[(x - min_x, y - min_y, z - min_z)] = (
                    state_id, block_entities.get(source_position))

    blocks = []
    for position in sorted(pending, key=lambda value: (value[1],
                                                       value[2], value[0])):
        state_id, block_entity = pending[position]
        value = Compound({"pos": tag_list(position), "state": Int(state_id)})
        if block_entity is not None:
            value["nbt"] = block_entity
        blocks.append(value)
    save_structure(output, size, states, blocks)
    return {
        "path": str(output.resolve()),
        "source": str(COMMAND_WORLD.resolve()),
        "source_bounds": list(COMMAND_BOUNDS),
        "size": list(size),
        "blocks": len(blocks),
        "palette": len(states),
        "block_entities": sum("nbt" in value for value in blocks),
        "placement_offset": list(COMMAND_PLACEMENT_OFFSET),
        "downgrades": dict(sorted(downgraded.items())),
    }


def decode_varints(values: Iterable[int]) -> list[int]:
    decoded = []
    current = 0
    shift = 0
    for raw in values:
        value = int(raw) & 0xFF
        current |= (value & 0x7F) << shift
        if value & 0x80:
            shift += 7
            if shift > 35:
                raise ValueError("Invalid Sponge schematic varint")
        else:
            decoded.append(current)
            current = 0
            shift = 0
    if shift:
        raise ValueError("Truncated Sponge schematic varint")
    return decoded


def convert_schematic(output: Path) -> dict:
    if not SKYSCRAPER_SCHEM.is_file():
        raise FileNotFoundError(f"Tokyo-3 schematic not found: {SKYSCRAPER_SCHEM}")
    loaded = nbtlib.load(SKYSCRAPER_SCHEM, gzipped=True)
    schematic = loaded.get("Schematic", loaded)
    width = int(schematic["Width"])
    height = int(schematic["Height"])
    length = int(schematic["Length"])
    values = decode_varints(schematic["BlockData"])
    expected = width * height * length
    if len(values) != expected:
        raise ValueError(f"Schematic has {len(values)} blocks, expected {expected}")
    by_id = {int(identifier): parse_state_text(str(text))
             for text, identifier in schematic["Palette"].items()}
    state_ids: dict[State, int] = {}
    states: list[State] = []
    blocks = []
    for index, source_id in enumerate(values):
        state = by_id[source_id]
        if state[0] in AIR:
            continue
        x = index % width
        z = (index // width) % length
        y = index // (width * length)
        state_id = state_ids.get(state)
        if state_id is None:
            state_id = len(states)
            state_ids[state] = state_id
            states.append(state)
        blocks.append(Compound({
            "pos": tag_list((x, y, z)),
            "state": Int(state_id),
        }))
    size = (width, height, length)
    save_structure(output, size, states, blocks)
    return {
        "path": str(output.resolve()),
        "source": str(SKYSCRAPER_SCHEM.resolve()),
        "size": list(size),
        "blocks": len(blocks),
        "palette": len(states),
        "placements": [list(value) for value in SKYSCRAPER_PLACEMENTS],
    }


def world_copy_ignore(_directory: str, names: list[str]) -> set[str]:
    ignored = {"session.lock", "playerdata", "stats", "advancements",
               "region", "entities", "poi", "dimensions", "data",
               "datapacks", "DIM-1", "DIM1", "serverconfig"}
    ignored.update(name for name in names if name.startswith("visual_capture"))
    return ignored & set(names)


def world_generator_type(path: Path) -> str:
    level_path = path / "level.dat"
    if not level_path.is_file():
        return ""
    level = nbtlib.load(level_path)
    data = level.get("Data", level)
    return str(data.get("WorldGenSettings", {})
               .get("dimensions", {})
               .get("minecraft:overworld", {})
               .get("generator", {})
               .get("type", ""))


def select_world_template() -> Path:
    candidates = list(WORLD_TEMPLATE_CANDIDATES)
    saves = ROOT / "run" / "saves"
    candidates.extend(sorted(
        (path for path in saves.glob("New World*")
         if path not in candidates),
        key=lambda path: path.name,
    ))
    for path in candidates:
        if world_generator_type(path) == "minecraft:noise":
            return path
    raise FileNotFoundError(
        "A clean normal-noise Minecraft world is required as the local "
        "Project SEELE template; no eligible 'New World' save was found")


def rename_staged_world(path: Path) -> None:
    level_path = path / "level.dat"
    if not level_path.is_file():
        raise FileNotFoundError(f"Template level.dat missing: {level_path}")
    level = nbtlib.load(level_path)
    data = level.get("Data", level)
    data["LevelName"] = String("Project SEELE - Tokyo-3 and GeoFront")
    data["SpawnX"] = Int(0)
    data["SpawnY"] = Int(96)
    data["SpawnZ"] = Int(0)
    data["allowCommands"] = nbtlib.Byte(1)
    data["GameType"] = Int(1)
    data["hardcore"] = nbtlib.Byte(0)
    data["Difficulty"] = nbtlib.Byte(1)
    data["DifficultyLocked"] = nbtlib.Byte(0)
    data["confirmedExperimentalSettings"] = nbtlib.Byte(1)
    data.pop("Player", None)
    level.save(level_path, gzipped=True)


def stage_world() -> dict:
    world_template = select_world_template()
    source_region = TOKYO3_WORLD / "region"
    if not source_region.is_dir():
        raise FileNotFoundError(f"Legacy Tokyo-3 region missing: {TOKYO3_WORLD}")
    if STAGED_WORLD.exists():
        marker = STAGED_WORLD / ".projectseele_local_map.json"
        if marker.is_file():
            existing = json.loads(marker.read_text(encoding="utf-8"))
            if (existing.get("schema") == STAGED_WORLD_SCHEMA
                    and existing.get("shaft_center") == [30, 220]
                    and existing.get("map_version") == 15
                    and existing.get("topology")
                    == "continent_surface_skyweave_sphere_640_v5_buried_noise"
                    and existing.get("template_generator")
                    == "minecraft:noise"):
                return existing
            suffix = f"-backup-schema{existing.get('schema', 'unknown')}"
            backup = STAGED_WORLD.with_name(STAGED_WORLD.name + suffix)
            index = 2
            while backup.exists():
                backup = STAGED_WORLD.with_name(
                    STAGED_WORLD.name + suffix + f"-{index}")
                index += 1
            shutil.move(STAGED_WORLD, backup)
            print(f"Preserved obsolete generated save as {backup}")
        else:
            raise FileExistsError(f"Refusing to replace unmarked save: {STAGED_WORLD}")

    shutil.copytree(world_template, STAGED_WORLD, ignore=world_copy_ignore)
    rename_staged_world(STAGED_WORLD)
    dimension = STAGED_WORLD / "dimensions" / "projectseele" / "geofront"
    target_region = dimension / "region"
    target_region.mkdir(parents=True, exist_ok=True)
    region_files = 0
    total_bytes = 0
    # Start the custom dimension with native overworld-noise chunks. The
    # legacy EVA-X save remains a measured private reference, but copying its
    # flattened 0..255 regions would leave an obsolete half-sphere inside the
    # new full 640-block Skyweave shell.
    marker_data = {
        "schema": STAGED_WORLD_SCHEMA,
        "map_version": 15,
        "world": str(STAGED_WORLD.resolve()),
        "template": str(world_template.resolve()),
        "template_generator": world_generator_type(world_template),
        "tokyo3_source": str(TOKYO3_WORLD.resolve()),
        "dimension": "projectseele:geofront",
        "region_files": region_files,
        "region_bytes": total_bytes,
        "city_anchor": [30, 80, 220],
        "geofront_anchor": [30, -444, 296],
        "shaft_center": [30, 220],
        "topology": "continent_surface_skyweave_sphere_640_v5_buried_noise",
        "deep_fluid_floor": -672,
        "surface_profile": "normal_overworld_noise",
        "city_district_half_size": 208,
        "city_landscape_radius": 360,
        "legacy_world_role": "measured_reference_only",
        "private_local_only": True,
    }
    marker = STAGED_WORLD / ".projectseele_local_map.json"
    marker.write_text(json.dumps(marker_data, indent=2), encoding="utf-8")
    return marker_data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets-only", action="store_true")
    args = parser.parse_args()
    LOCAL_ASSET_DIR.mkdir(parents=True, exist_ok=True)
    command = convert_command_module(LOCAL_ASSET_DIR / "nerv_command_left.nbt")
    skyscraper = convert_schematic(LOCAL_ASSET_DIR / "tokyo3_skyscraper.nbt")
    world = None if args.assets_only else stage_world()
    manifest = {
        "schema": 1,
        "minecraft_target": "1.20.1",
        "data_version": TARGET_DATA_VERSION,
        "private_local_only": True,
        "command_module": command,
        "tokyo3_skyscraper": skyscraper,
        "staged_world": world,
    }
    manifest_path = LOCAL_ASSET_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
