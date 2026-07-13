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
    saved_data = read("src/main/java/com/projectseele/event/ThirdImpactSavedData.java")
    packet = read("src/main/java/com/projectseele/network/ClientboundThirdImpactPacket.java")
    network = read("src/main/java/com/projectseele/network/SeeleNetwork.java")
    game_events = read("src/main/java/com/projectseele/GameEvents.java")
    entity = read("src/main/java/com/projectseele/entity/EvaUnit01Entity.java")
    mass_entity = read("src/main/java/com/projectseele/entity/MassProductionEvaEntity.java")
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
    orientation_match = re.search(
        r'TABLEAU_ORIENTATION\s*=\s*"([^"]+)"\s*;', layout)
    semantic_indices = {
        name: int(match.group(1)) if (match := re.search(
            rf"\b{name}\s*=\s*(\d+)\s*;", layout)) else -1
        for name in ("KETER", "TIFERET", "MALKUTH")
    }
    ys = [y for _, y in nodes]
    inverted = len(nodes) == 10 \
        and orientation_match is not None \
        and orientation_match.group(1) == "EOE_INVERTED" \
        and semantic_indices == {"KETER": 0, "TIFERET": 5, "MALKUTH": 9} \
        and nodes[semantic_indices["KETER"]][1] == min(ys) \
        and nodes[semantic_indices["MALKUTH"]][1] == max(ys)
    gate.require(
        "tree.eoe_inverted_semantics",
        inverted,
        "orientation=EOE_INVERTED; semantic Keter=nadir and Malkuth=crown",
    )
    tiferet_centre = inverted \
        and nodes[semantic_indices["TIFERET"]][0] == 0.0 \
        and abs(nodes[semantic_indices["TIFERET"]][1]
                - (min(ys) + max(ys)) * 0.5) < 1.0e-6
    gate.require(
        "tree.tiferet_centre",
        tiferet_centre,
        "Tiferet remains at the geometric centre while the semantic Tree is inverted",
    )

    names = quoted_values(java_initializer(client_fx, "SEPHIRA_NAMES"))
    hebrew = quoted_values(java_initializer(client_fx, "SEPHIRA_HEBREW"))
    numerals = quoted_values(java_initializer(client_fx, "SEPHIRA_NUMERALS"))
    divine_names = quoted_values(java_initializer(client_fx, "SEPHIRA_DIVINE_NAMES"))
    archangels = quoted_values(java_initializer(client_fx, "SEPHIRA_ARCHANGELS"))
    choirs = quoted_values(java_initializer(client_fx, "SEPHIRA_CHOIRS"))
    letters = quoted_values(java_initializer(client_fx, "PATH_LETTERS"))
    path_numerals = quoted_values(java_initializer(client_fx, "PATH_NUMERALS"))
    expected_names = [
        "KETER", "CHOKMAH", "BINAH", "CHESED", "GEVURAH",
        "TIFERET", "NETZACH", "HOD", "YESOD", "MALKUTH",
    ]
    expected_hebrew = [
        r"\u05DB\u05EA\u05E8", r"\u05D7\u05DB\u05DE\u05D4", r"\u05D1\u05D9\u05E0\u05D4",
        r"\u05D7\u05E1\u05D3", r"\u05D2\u05D1\u05D5\u05E8\u05D4", r"\u05EA\u05E4\u05D0\u05E8\u05EA",
        r"\u05E0\u05E6\u05D7", r"\u05D4\u05D5\u05D3", r"\u05D9\u05E1\u05D5\u05D3", r"\u05DE\u05DC\u05DB\u05D5\u05EA",
    ]
    gate.require(
        "tree.semantic_label_mapping",
        names == expected_names and hebrew == expected_hebrew,
        "indices 0..9 retain Keter..Malkuth in Latin and Hebrew despite inverted coordinates",
    )
    gate.require("tree.latin_catalog", len(names) == 10,
                 f"latin={len(names)}/10 retained for reports only")
    gate.require("tree.hebrew_labels", len(hebrew) == 10, f"hebrew={len(hebrew)}/10")
    gate.require(
        "tree.hebrew_numerals",
        numerals == [r"\u05D0", r"\u05D1", r"\u05D2", r"\u05D3", r"\u05D4",
                     r"\u05D5", r"\u05D6", r"\u05D7", r"\u05D8", r"\u05D9"],
        f"numerals={len(numerals)}/10 in canonical order",
    )
    gate.require(
        "tree.hebrew_divine_names",
        len(divine_names) == 10 and all(divine_names),
        f"divineNames={len(divine_names)}/10",
    )
    gate.require(
        "tree.hebrew_correspondence_density",
        len(archangels) == 10 and len(choirs) == 10
        and all(archangels) and all(choirs),
        f"archangels={len(archangels)}/10 choirs={len(choirs)}/10",
    )
    gate.require(
        "tree.path_letters",
        len(letters) == 22 and len(set(letters)) == 22,
        f"letters={len(letters)}/22 unique={len(set(letters))}",
    )
    expected_path_numerals = [
        r"\u05D9\u05F4\u05D0", r"\u05D9\u05F4\u05D1", r"\u05D9\u05F4\u05D2",
        r"\u05D9\u05F4\u05D3", r"\u05D8\u05F4\u05D6", r"\u05D8\u05F4\u05D5",
        r"\u05D9\u05F4\u05D7", r"\u05D9\u05F4\u05D6", r"\u05D9\u05F4\u05D8",
        r"\u05DB\u05F3", r"\u05DB\u05F4\u05D0", r"\u05DB\u05F4\u05D1",
        r"\u05DB\u05F4\u05D2", r"\u05DB\u05F4\u05D3", r"\u05DB\u05F4\u05D5",
        r"\u05DB\u05F4\u05D4", r"\u05DB\u05F4\u05D6", r"\u05DB\u05F4\u05D7",
        r"\u05DC\u05F3", r"\u05DB\u05F4\u05D8", r"\u05DC\u05F4\u05D0",
        r"\u05DC\u05F4\u05D1",
    ]
    gate.require(
        "tree.path_numeral_mapping",
        path_numerals == expected_path_numerals,
        f"pathNumerals={len(path_numerals)}/22 ordered with the 11..32 path catalogue",
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

    label_start = client_fx.index("void renderLabels(")
    label_end = client_fx.index("private static String displayHebrew", label_start)
    label_block = client_fx[label_start:label_end]
    no_horizon_row = all(token not in client_fx for token in (
        "HORIZON", "AETERNITATIS", "TITLE_X",
        r"\u05E2\u05E5 \u05D4\u05D7\u05D9\u05D9\u05DD",
        r"\u05E2\u05E9\u05E8 \u05D4\u05E1\u05E4\u05D9\u05E8\u05D5\u05EA",
    )) and "SEPHIRA_NAMES[i]" not in label_block
    gate.require(
        "tree.no_detached_title_or_horizon_row",
        no_horizon_row,
        "the EoE diagram has no detached custom title or HORIZON AETERNITATIS row",
    )

    rotated_labels = all(token in client_fx for token in (
        "LABEL_ROTATION_DEGREES = 180.0F",
        "Axis.ZP.rotationDegrees(",
        "LABEL_ROTATION_DEGREES));",
    ))
    gate.require(
        "tree.label_rotation_180",
        rotated_labels,
        "all node/path text shares the complete diagram's 180-degree EoE rotation",
    )

    dense_internal = all(token in client_fx for token in (
        "NODE_TICK_COUNT = 12", "for (int tick = 0; tick < NODE_TICK_COUNT; tick++)",
        "drawDiagramLabel", "SEPHIRA_HEBREW[i]", "SEPHIRA_DIVINE_NAMES[i]",
        "SEPHIRA_ARCHANGELS[i]", "SEPHIRA_CHOIRS[i]",
        "PATH_NUMERALS[i]", "Font.DisplayMode.NORMAL", "DIAGRAM_TEXT_Z = -7.4F",
        "EXTERNAL_NAME_SCALE = 0.40F", "EXTERNAL_CHOIR_SCALE = 0.20F",
    ))
    gate.require(
        "tree.dense_internal_marks",
        dense_internal,
        "12 radial marks per circle plus 124 compact Hebrew correspondence/path inscriptions",
    )

    thin_geometry = all(fragment in client_fx for fragment in (
        ".mul(0.72F)", "0.38F, 0.38F", "0.12F, 0.12F",
        "radius, 0.56F", "radius * 0.72F, 0.18F", "float s = 1.05F",
    ))
    gate.require(
        "tree.subordinate_red_geometry",
        thin_geometry,
        "paths/rings and Tiferet glory remain thinner than the ritual EVA silhouettes",
    )

    facing_source = all(fragment in layout for fragment in (
        "return -(float) Math.toDegrees(yawRad)",
        "return new Vec3(Math.sin(yawRad), 0.0D, Math.cos(yawRad))",
    )) and all(fragment in director for fragment in (
        "TreeOfLifeLayout.frontFacingYawDegrees(impact.yaw)",
        "faceFront(mass, formationYaw)",
        "entity.yBodyRot = yaw", "entity.yHeadRot = yaw",
    ))
    sample_alignment = all(
        abs((-math.sin(math.radians(-math.degrees(yaw)))) - math.sin(yaw)) < 1.0e-6
        and abs(math.cos(math.radians(-math.degrees(yaw))) - math.cos(yaw)) < 1.0e-6
        for yaw in (-2.4, -0.75, 0.0, 0.8, 2.7)
    )
    gate.require(
        "tree.single_front_plane",
        facing_source and sample_alignment,
        "Minecraft entity forward vector matches the Tree front normal for sampled yaws",
    )

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
    persistence = all(token in saved_data for token in (
        "extends SavedData", "projectseele_third_impact", "DATA_VERSION = 2",
        "OriginX", "OriginY", "OriginZ", "Vessels", "Map<Integer, UUID>",
        "Outcome", "OUTCOME_ACCEPTED", "OUTCOME_REJECTED",
    )) and all(token in director for token in (
        "ensureRestored(level)", "reconcileRestoredImpact", "formationChunksLoaded",
        "persist(impact)", "removePersisted(impact)", "if (!impact.persistent)",
        "chunkSettleTicks", "discardOwnedVessels", "ensureVesselForNode",
        "ForgeChunkManager.forceChunk", "acquireFormationTickets",
        "releaseFormationTickets",
    )) and all(token in mass_entity for token in (
        "SeeleImpactId", "SeeleImpactNode", "assignRitualOwner",
        "isRitualOwnedBy", "hasRitualOwner",
    ))
    gate.require("impact.saved_timeline", persistence,
                 "versioned per-dimension timeline restores node-indexed vessels")
    resync = all(token in packet for token in (
        "eventId", "buf.readUUID()", "buf.writeUUID(this.eventId)",
        "initialTreeAge", "buf.readVarInt()", "buf.writeVarInt(this.initialTreeAge)",
    )) and 'PROTOCOL_VERSION = "4"' in network \
        and all(token in game_events for token in (
            "PlayerLoggedInEvent", "PlayerChangedDimensionEvent", "PlayerRespawnEvent",
            "ThirdImpactDirector.syncTo(player)",
        )) and "PacketDistributor.DIMENSION" in director \
        and "tree.eventId.equals(packet.eventId)" in client_fx \
        and "Math.max(tree.age" in client_fx
    gate.require("impact.client_resync", resync,
                 "protocol-v4 event-id sync resumes Tree age without replacement")


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
    game_events = read("src/main/java/com/projectseele/GameEvents.java")
    client = read("src/main/java/com/projectseele/client/ClientForgeEvents.java")
    renderer = read("src/main/java/com/projectseele/client/render/EvaUnit01Renderer.java")
    network = read("src/main/java/com/projectseele/network/SeeleNetwork.java")
    entry_packet = read("src/main/java/com/projectseele/network/ServerboundEntryPlugPacket.java")
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
    # Bed is origin-30, EVA base origin-29, gantry standing Y origin-3.
    relative_entry_height = (-3) - (-29)
    high_entry = gantry_y == -4 and min_height <= relative_entry_height <= max_height \
        and "bed.getY() + 27.0D" in command
    gate.require(
        "silo.high_entry",
        high_entry,
        f"gantryY={gantry_y} relativeEntry={relative_entry_height} allowed={min_height:g}..{max_height:g}",
    )
    ladder = (
        "for (int y = -26; y <= -3; y++)" in builder
        and "LadderBlock.FACING, Direction.NORTH" in builder
        and "for (int y = 4; y <= 27; y++)" in command
        and "ladderContinuous" in command
    )
    gate.require("silo.gantry_access", ladder, "all 24 ladder blocks are runtime-audited")

    rear_entry = all(token in entity for token in (
        "SILO_ENTRY_MIN_REAR_DOT", "SILO_ENTRY_MIN_DISTANCE", "SILO_ENTRY_MAX_DISTANCE",
        "this.getForward().multiply(-1.0D, 0.0D, -1.0D).normalize()",
        "rearDot < SILO_ENTRY_MIN_REAR_DOT",
    ))
    gate.require("silo.rear_entry_gate", rear_entry,
                 "high entry requires the rear-side distance and facing cone")
    plug_interaction = all(token in entity for token in (
        "ENTRY_PLUG_HEIGHT_00", "ENTRY_PLUG_HEIGHT_01", "ENTRY_PLUG_HEIGHT_02",
        "getEntryPlugSocketPosition", "isEntryPlugTargeted", "tryEnterFromPlug",
        "DATA_ENTRY_PLUG_INSERTED", "SILO_BAY_YAW",
    )) and all(token in client for token in (
        "findEntryPlugTarget", "ServerboundEntryPlugPacket",
    )) and "ServerboundEntryPlugPacket.class" in network \
        and "eva.tryEnterFromPlug(sender)" in entry_packet
    gate.require("silo.entry_plug_interaction", plug_interaction,
                 "aimed dorsal socket works beyond the coarse entity AABB and is revalidated server-side")
    persistent_plug_visual = all(token in renderer for token in (
        "animatable.getActivationTicks() > 0",
        "|| animatable.isEntryPlugInserted()",
        'setWeaponVisibility(model, "entry_plug", activating)',
        'setWeaponVisibility(model, "plug_hatch_l", activating)',
        'setWeaponVisibility(model, "plug_hatch_r", activating)',
    ))
    gate.require(
        "silo.persistent_entry_plug_visual",
        persistent_plug_visual,
        "the inserted plug and both hatch leaves remain visible after the insertion animation",
    )
    entry_start = entity.find("public InteractionResult tryEnterFromPlug(Player player, boolean requireAim)")
    entry_end = entity.find("private void alignForSiloBoarding", entry_start)
    entry_body = entity[entry_start:entry_end] if entry_start >= 0 and entry_end > entry_start else ""
    clear_path_at = entry_body.find("hasClearEntryPlugPath(player)")
    align_at = entry_body.find("alignForSiloBoarding(launchBed)")
    mount_at = entry_body.find("player.startRiding(this, true)")
    authorization_order = 0 <= clear_path_at < align_at < mount_at
    gate.require("silo.authorize_before_alignment", authorization_order,
                 "visible pose is used for every entry gate before the silo may align or mount the EVA")
    client_entry_filter = all(token in client for token in (
        "hasClearEntryPlugPath(player, unit)", "ClipContext.Block.COLLIDER",
        "lastEntryPlugRequestTick", "lastEntryPlugRequestTick != player.tickCount",
    ))
    gate.require("silo.client_entry_filter", client_entry_filter,
                 "blocked sockets do not swallow use input and main/offhand emit one packet per tick")
    socket_heights = [number(entity, name) for name in (
        "ENTRY_PLUG_HEIGHT_00", "ENTRY_PLUG_HEIGHT_01", "ENTRY_PLUG_HEIGHT_02")]
    socket_geometry = all(26.8 < value < 27.1 for value in socket_heights) \
        and max(socket_heights) - min(socket_heights) < 0.01 \
        and abs(number(entity, "ENTRY_PLUG_REAR_OFFSET") - 1.25) < 1.0e-6
    gate.require("silo.variant_entry_sockets", socket_geometry,
                 f"runtimeHeights={socket_heights} rearOffset={number(entity, 'ENTRY_PLUG_REAR_OFFSET'):g}")
    bed_envelope = all(token in entity for token in (
        "for (int x = -5; x <= 5; x++)", "for (int z = -5; z <= 5; z++)",
        "launchBedClaimedByAnother", "launch_bed_occupied",
    ))
    gate.require("silo.bed_envelope_lock", bed_envelope,
                 "shifted EVA remains caged and one active EVA owns each lodestone")

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
    freeze_and_easing = all(token in entity for token in (
        "enforceLaunchLock()", "this.isCrucified() || this.isPilotControlLocked()",
        "public void travel(Vec3 input)", "public boolean isPushable()",
        "LAUNCH_PASSENGER_RESTORE_GRACE_TICKS",
        "progress * progress * (3.0F - 2.0F * progress)",
    ))
    gate.require("silo.freeze_and_deterministic_ascent", freeze_and_easing,
                 "activation is position/yaw/input locked and ascent follows a persisted smoothstep clock")
    reset_start = entity.find("private void resetLaunchSequence()")
    reset_end = entity.find("@Override\n    public void die", reset_start)
    reset_body = entity[reset_start:reset_end] if reset_start >= 0 and reset_end > reset_start else ""
    abandoned_cleanup = all(token in reset_body for token in (
        "boolean abandoned = this.getControllingPassenger() == null",
        "if (abandoned)", "DATA_ACTIVATION_TICKS, 0", "DATA_ENTRY_PLUG_INSERTED, false",
    ))
    gate.require("silo.abandoned_entry_cleanup", abandoned_cleanup,
                 "passenger-restore timeout clears the inserted plug and activation overlay")
    moving_carrier = all(token in entity for token in (
        "SeeleLaunchCarrierY", "updateMovingCarrier()", "setMovingCarrierLayer",
        "for (int x = -5; x <= 5; x++)", "for (int z = -5; z <= 5; z++)",
        "NERV carrier progress", "this.setSurfaceCarrier(true)",
        "recoverMovingCarrier", "serverLevel.setBlock(block, desired, 2)",
        "hasMovingCarrierSignature", "exact 11x11 carrier signature",
    ))
    gate.require("silo.moving_carrier", moving_carrier,
                 "persisted 11x11 carrier follows the EVA and closes on abort")
    travel_interlock = all(token in game_events for token in (
        "EntityTravelToDimensionEvent", "eva.isLaunchSequenceActive()",
        "event.setCanceled(true)",
    )) and "protected void removePassenger" in entity \
        and "if (this.isLaunchSequenceActive())" in entity
    gate.require("silo.travel_interlock", travel_interlock,
                 "forced dismount safely rolls back; dimension travel cannot bypass launch lock")
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
        "/seele silo audit" in doc and "clearShafts=3" in doc
        and "11×11" in doc and "背部扇区" in doc
        and "LAUNCH_CLEAR" in doc and "18 tick" in doc and "0.9" in doc,
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
