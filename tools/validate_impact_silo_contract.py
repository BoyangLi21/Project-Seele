#!/usr/bin/env python3
"""Offline structural gate for Third Impact and the NERV launch silo.

This does not replace an in-game screenshot or a Gradle build.  It catches
regressions that can be proven from source data: Tree topology and lettering,
the Unit-01 crucifix state contract, three-bay/high-gantry construction, and
the presence of deterministic runtime audit logs.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def java_initializer(source: str, name: str) -> str:
    match = re.search(rf"\b{re.escape(name)}\b\s*=\s*\{{", source)
    if not match:
        raise ValueError(f"Java initializer not found: {name}")
    start = source.find("{", match.start())
    depth = 0
    for index in range(start, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise ValueError(f"Unclosed Java initializer: {name}")


def quoted_values(initializer: str) -> list[str]:
    return re.findall(r'"((?:\\.|[^"\\])*)"', initializer)


class Gate:
    def __init__(self) -> None:
        self.checks: list[dict[str, object]] = []

    def require(self, label: str, condition: bool, detail: str) -> None:
        self.checks.append({"label": label, "ok": bool(condition), "detail": detail})

    @property
    def valid(self) -> bool:
        return all(bool(check["ok"]) for check in self.checks)


def first_rotation(animation: dict[str, object], bone: str) -> list[float]:
    entry = animation["bones"][bone]["rotation"]
    if isinstance(entry, list):
        return entry
    key = min(entry, key=lambda value: float(value))
    return entry[key]


def validate_tree(gate: Gate) -> None:
    layout = read("src/main/java/com/projectseele/fx/TreeOfLifeLayout.java")
    client_fx = read("src/main/java/com/projectseele/client/fx/ClientFxManager.java")
    director = read("src/main/java/com/projectseele/event/ThirdImpactDirector.java")
    entity = read("src/main/java/com/projectseele/entity/EvaUnit01Entity.java")
    animation_doc = json.loads(read(
        "src/main/resources/assets/projectseele/animations/eva_unit01.animation.json"))

    node_block = java_initializer(layout, "NODES")
    nodes = [
        (float(x), float(y))
        for x, y in re.findall(
            r"\{\s*(-?\d+(?:\.\d+)?)F?\s*,\s*(-?\d+(?:\.\d+)?)F?\s*\}",
            node_block,
        )
    ]
    path_block = java_initializer(layout, "PATHS")
    paths = [
        (int(left), int(right))
        for left, right in re.findall(r"\{\s*(\d+)\s*,\s*(\d+)\s*\}", path_block)
    ]
    gate.require("tree.nodes", len(nodes) == 10, f"nodes={len(nodes)} expected=10")
    gate.require("tree.paths", len(paths) == 22, f"paths={len(paths)} expected=22")
    canonical_edges = {tuple(sorted(edge)) for edge in paths}
    valid_indices = all(0 <= a < len(nodes) and 0 <= b < len(nodes) and a != b
                        for a, b in paths)
    gate.require(
        "tree.path_indices",
        valid_indices and len(canonical_edges) == 22,
        f"validIndices={valid_indices} uniqueUndirected={len(canonical_edges)}",
    )
    visited = {0}
    while True:
        expanded = visited | {
            b if a in visited else a
            for a, b in paths
            if a in visited or b in visited
        }
        if expanded == visited:
            break
        visited = expanded
    gate.require("tree.connected", len(visited) == 10, f"reachable={len(visited)}/10")
    inverted = len(nodes) == 10 and nodes[0][1] == min(y for _, y in nodes) \
        and nodes[9][1] == max(y for _, y in nodes)
    gate.require("tree.inverted", inverted, "Keter=nadir and Malkuth=crown")

    names = quoted_values(java_initializer(client_fx, "SEPHIRA_NAMES"))
    hebrew = quoted_values(java_initializer(client_fx, "SEPHIRA_HEBREW"))
    letters = quoted_values(java_initializer(client_fx, "PATH_LETTERS"))
    gate.require("tree.latin_labels", len(names) == 10, f"latin={len(names)}/10")
    gate.require("tree.hebrew_labels", len(hebrew) == 10, f"hebrew={len(hebrew)}/10")
    gate.require(
        "tree.path_letters",
        len(letters) == 22 and len(set(letters)) == 22,
        f"letters={len(letters)}/22 unique={len(set(letters))}",
    )
    # Golden Dawn edge mapping.  Merely checking 22 unique glyphs previously
    # allowed four swapped pairs to pass while visibly labelling the wrong
    # paths in the ritual tableau.
    expected_path_letters = {
        (0, 1): r"\u05D0", (0, 2): r"\u05D1", (0, 5): r"\u05D2",
        (1, 2): r"\u05D3", (1, 5): r"\u05D4", (1, 3): r"\u05D5",
        (2, 5): r"\u05D6", (2, 4): r"\u05D7", (3, 4): r"\u05D8",
        (3, 5): r"\u05D9", (3, 6): r"\u05DB", (4, 5): r"\u05DC",
        (4, 7): r"\u05DE", (5, 6): r"\u05E0", (5, 8): r"\u05E1",
        (5, 7): r"\u05E2", (6, 7): r"\u05E4", (6, 8): r"\u05E6",
        (6, 9): r"\u05E7", (7, 8): r"\u05E8", (7, 9): r"\u05E9",
        (8, 9): r"\u05EA",
    }
    actual_path_letters = {
        tuple(sorted(edge)): letter for edge, letter in zip(paths, letters)
    }
    mismatched_edges = [
        edge for edge, letter in expected_path_letters.items()
        if actual_path_letters.get(edge) != letter
    ]
    gate.require(
        "tree.path_letter_mapping",
        actual_path_letters == expected_path_letters,
        f"mismatchedEdges={mismatched_edges}",
    )
    pure_red = (
        "0x00FF0000" in client_fx
        and "float pg = 0.0F" in client_fx
        and "float pb = 0.0F" in client_fx
        and "0x00000000" in client_fx
        and "colour, false" in client_fx
        and re.search(
            r"drawPolyRing\([^;]+?1\.0F,\s*0\.0F,\s*0\.0F,", client_fx, re.S
        ) is not None
    )
    gate.require("tree.pure_red_contract", pure_red,
                 "rings, glory and text use RGB 1/0/0 with no label backdrop/shadow")

    animations = animation_doc.get("animations", {})
    crucified = animations.get("animation.eva_unit01.crucified")
    has_cross_bones = isinstance(crucified, dict) and all(
        bone in crucified.get("bones", {}) for bone in ("arm_l", "arm_r", "forearm_l", "forearm_r")
    )
    gate.require("unit01.crucified_animation", has_cross_bones,
                 "crucified animation controls both upper arms and forearms")
    if has_cross_bones:
        left = first_rotation(crucified, "arm_l")
        right = first_rotation(crucified, "arm_r")
        cross_pose = abs(left[2]) >= 80.0 and abs(right[2]) >= 80.0 \
            and math.copysign(1.0, left[2]) != math.copysign(1.0, right[2])
        gate.require(
            "unit01.cross_silhouette",
            cross_pose,
            f"armZ=({left[2]},{right[2]}) expected opposite >=80deg",
        )

    local_animation_path = ROOT / (
        "run/resourcepacks/eva_real_model/assets/projectseele/animations/"
        "eva_unit01.animation.json"
    )
    if local_animation_path.is_file():
        local_doc = json.loads(local_animation_path.read_text(encoding="utf-8"))
        local_cross = local_doc.get("animations", {}).get("animation.eva_unit01.crucified")
        local_ok = isinstance(local_cross, dict) and all(
            bone in local_cross.get("bones", {}) for bone in ("arm_l", "arm_r")
        )
        if local_ok:
            local_left = first_rotation(local_cross, "arm_l")
            local_right = first_rotation(local_cross, "arm_r")
            local_ok = abs(local_left[2]) >= 80.0 and abs(local_right[2]) >= 80.0 \
                and math.copysign(1.0, local_left[2]) != math.copysign(1.0, local_right[2])
        gate.require(
            "unit01.local_pack_cross",
            local_ok,
            "generated eva_real_model pack preserves the arms-out crucified animation",
        )

    base_controller = entity.find('new AnimationController<>(this, "base"')
    crucified_priority = entity.find("if (this.isCrucified())", base_controller)
    visual_switch = entity.find("switch (this.getVisualPose())", base_controller)
    arms_controller = entity.find('new AnimationController<>(this, "arms"')
    arms_stop = entity.find("return PlayState.STOP", arms_controller)
    gate.require(
        "unit01.crucified_priority",
        0 <= base_controller < crucified_priority < visual_switch
        and arms_controller >= 0 and arms_stop > arms_controller,
        "crucified base pose precedes Visual Lab and stops the arms overlay",
    )
    strike_controller = entity.find('new AnimationController<>(this, "strike"')
    strike_end = entity.find("));", strike_controller)
    strike_block = entity[strike_controller:strike_end + 3]
    gate.require(
        "unit01.crucified_strike_gate",
        strike_controller >= 0
        and "this.isCrucified() ? PlayState.STOP" in strike_block
        and ".receiveTriggeredAnimations()" in strike_block,
        "triggered attacks are polled and stopped while Unit-01 is crucified",
    )
    gate.require(
        "unit01.crucified_state_reset",
        all(token in entity for token in (
            "this.entityData.set(DATA_WEAPON, WEAPON_FISTS)",
            "this.entityData.set(DATA_VISUAL_POSE, VISUAL_NORMAL)",
            "this.entityData.set(DATA_CROUCHING, false)",
            "this.entityData.set(DATA_PRONE, false)",
        )),
        "weapons and locomotion states are cleared before the cross pose",
    )
    gate.require(
        "impact.server_audit",
        "Third Impact tableau audit" in director
        and "occupiedOuterNodes" in director
        and "unitAtTiferet" in director,
        "story and preview paths emit structural tableau evidence",
    )


def number(source: str, name: str) -> float:
    match = re.search(
        rf"\b{re.escape(name)}\s*=\s*(-?\d+(?:\.\d+)?)D?\s*;", source
    )
    if not match:
        raise ValueError(f"Numeric Java constant not found: {name}")
    return float(match.group(1))


def validate_silo(gate: Gate) -> None:
    command = read("src/main/java/com/projectseele/visual/LaunchSiloCommands.java")
    builder = read("src/main/java/com/projectseele/item/NervConstructionKitItem.java")
    entity = read("src/main/java/com/projectseele/entity/EvaUnit01Entity.java")
    doc = read("docs/LAUNCH_SILO_TEST.md")

    commands = all(f'Commands.literal("{name}")' in command
                   for name in ("setup", "board", "status", "audit"))
    gate.require("silo.commands", commands, "setup/board/status/audit are registered")
    variants = all(token in builder for token in (
        "ModEntities.EVA_UNIT00.get().create(level)",
        "ModEntities.EVA_UNIT01.get().create(level)",
        "ModEntities.EVA_UNIT02.get().create(level)",
    ))
    gate.require("silo.three_variants", variants, "Unit-00/01/02 each have a launch bay")

    gantry_match = re.search(r"int gantryY\s*=\s*(-?\d+)\s*;", builder)
    min_height = number(entity, "SILO_ENTRY_MIN_HEIGHT")
    max_height = number(entity, "SILO_ENTRY_MAX_HEIGHT")
    gantry_y = int(gantry_match.group(1)) if gantry_match else 999
    # Bed is origin-30, EVA base origin-29, gantry standing Y origin-7.
    relative_entry_height = (-7) - (-29)
    high_entry = gantry_y == -8 and min_height <= relative_entry_height <= max_height \
        and "bed.getY() + 23.0D" in command
    gate.require(
        "silo.high_entry",
        high_entry,
        f"gantryY={gantry_y} relativeEntry={relative_entry_height} allowed={min_height:g}..{max_height:g}",
    )
    ladder = (
        "for (int y = -26; y <= -7; y++)" in builder
        and "LadderBlock.FACING, Direction.NORTH" in builder
        and "bed.offset(0, 4, 13)" in command
        and "bed.offset(0, 23, 13)" in command
    )
    gate.require("silo.gantry_access", ladder, "continuous ladder endpoints are runtime-audited")

    target = number(entity, "LAUNCH_TARGET_ABOVE_BED")
    ascent_ticks = number(entity, "LAUNCH_ASCENT_TICKS")
    launch_contract = (
        target == 32.0
        and ascent_ticks > 0
        and "LAUNCH_LOCKED" in entity
        and "LAUNCH_ASCENT" in entity
        and "LAUNCH_CLEAR" in entity
        and "setSurfaceCarrier(false)" in entity
        and "setSurfaceCarrier(true)" in entity
    )
    gate.require(
        "silo.catapult_state_machine",
        launch_contract,
        f"targetAboveBed={target:g} ascentTicks={ascent_ticks:g} carrier opens/closes",
    )
    log_contract = all(token in entity for token in (
        "NERV launch locked", "NERV launch ascent", "NERV launch surface clear"
    )) and "NERV silo audit" in command
    gate.require("silo.runtime_evidence", log_contract,
                 "structure, lock, ascent and surface-clear logs are present")
    gate.require(
        "silo.audit_geometry",
        all(token in command for token in (
            "units.size() == 3", "validHighGantries == 3", "clearShafts == 3",
            "variants00/01/02", "bed.offset(x, y, z)",
        )),
        "audit gates variants, beds, gantries and 11x11x31 launch corridors",
    )
    gate.require(
        "silo.documentation",
        "/seele silo audit" in doc and "clearShafts=3" in doc,
        "manual test names the structural gate and expected result",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="print machine-readable evidence")
    args = parser.parse_args()
    gate = Gate()
    try:
        validate_tree(gate)
        validate_silo(gate)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        gate.require("validator.execution", False, str(error))

    if args.json:
        print(json.dumps({"valid": gate.valid, "checks": gate.checks}, ensure_ascii=False, indent=2))
    else:
        for check in gate.checks:
            state = "PASS" if check["ok"] else "FAIL"
            print(f"[{state}] {check['label']}: {check['detail']}")
        print(f"Impact/silo contract: {'PASS' if gate.valid else 'FAIL'}")
    return 0 if gate.valid else 1


if __name__ == "__main__":
    sys.exit(main())
