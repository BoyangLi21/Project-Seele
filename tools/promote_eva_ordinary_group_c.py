#!/usr/bin/env python3
"""Promote the human-selected Phase T group C into the live attack database."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO_ROOT / (
    "src/main/resources/assets/projectseele/motion/"
    "eva_mocap_ordinary_combo_phase_t_selection_v1.json"
)
DEFAULT_OUTPUT = REPO_ROOT / (
    "src/main/resources/assets/projectseele/motion/"
    "eva_ordinary_attack_group_c_v1.json"
)
PLAYBACK_SPEED = 2.0
STAGES = (
    {
        "name": "ordinary_attack_group_c_stage_1",
        "source_clip": "group_c_right_drive",
        "frame_range": (0, 44),
        "contact_frame": 20,
        "buffer_window": (25, 44),
    },
    {
        "name": "ordinary_attack_group_c_stage_2",
        "source_clip": "group_c_left_double",
        "frame_range": (45, 107),
        "contact_frame": 93,
        "buffer_window": (98, 107),
    },
    {
        "name": "ordinary_attack_group_c_stage_3",
        "source_clip": "group_c_right_finish",
        "frame_range": (108, 140),
        "contact_frame": 125,
        "buffer_window": (130, 140),
    },
)
SELECTED_SOURCE_IDS = {
    "g1_moves_m17_frames_1036_1081",
    "g1_moves_m17_frames_1221_1285",
    "g1_moves_m17_frames_1498_1532_mirrored",
}


def compact_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--do-not-update-selection",
        action="store_true",
        help="Leave the Phase T selection metadata untouched.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selection = json.loads(args.source.read_text(encoding="utf-8"))
    if selection.get("schema") != 2:
        raise RuntimeError("Phase T selection must use motion schema 2")
    sample_rate = float(selection.get("sample_rate", 0.0))
    if sample_rate != 60.0:
        raise RuntimeError(f"expected 60 Hz Phase T source, got {sample_rate}")
    source_clip = selection.get("clips", {}).get("ordinary_group_c")
    if source_clip is None:
        raise RuntimeError("ordinary_group_c is missing from Phase T selection")
    source_frames = source_clip.get("frames", [])
    if len(source_frames) < 141:
        raise RuntimeError("ordinary_group_c does not contain its first full cycle")

    source_bones = list(selection.get("bones", []))
    if not source_bones or source_bones[-1] != "knife":
        raise RuntimeError("expected Phase T's hidden knife channel as final bone")
    live_bones = source_bones[:-1]
    live_clips: dict[str, object] = {}
    stage_contracts: list[dict[str, object]] = []
    total_frames = 0

    for index, spec in enumerate(STAGES):
        first, last = spec["frame_range"]
        frames = json.loads(json.dumps(source_frames[first : last + 1]))
        for frame in frames:
            rotations = frame.get("rotation_wxyz", [])
            if len(rotations) != len(source_bones):
                raise RuntimeError(
                    f"source bone/frame mismatch in {spec['name']}"
                )
            frame["rotation_wxyz"] = rotations[:-1]

        local_contact = int(spec["contact_frame"]) - first
        buffer_first, buffer_last = spec["buffer_window"]
        local_buffer = [buffer_first - first, buffer_last - first]
        authored_duration = (len(frames) - 1) / sample_rate
        runtime_duration = authored_duration / PLAYBACK_SPEED
        contact_seconds = local_contact / sample_rate / PLAYBACK_SPEED
        contact_tick = max(1, round(contact_seconds * 20.0))
        frame_hash = hashlib.sha256(compact_bytes(frames)).hexdigest()

        live_clips[spec["name"]] = {
            "duration_seconds": round(authored_duration, 7),
            "runtime_duration_seconds": round(runtime_duration, 7),
            "playback_speed_multiplier": PLAYBACK_SPEED,
            "loop": False,
            "role": "live_buffered_left_click_combo_stage",
            "kind": spec["source_clip"],
            "support_mode": "CAPTURED_FULL_BODY_WITH_INERTIAL_TRANSITIONS",
            "grip": "CURLED_FOREARM_CONTACT",
            "source_frame_range": [first, last],
            "contact_frame": local_contact,
            "buffer_window": local_buffer,
            "frame_sha256": frame_hash,
            "frames": frames,
        }
        stage_contracts.append(
            {
                "stage": index,
                "clip": spec["name"],
                "frames": len(frames),
                "runtime_duration_seconds": round(runtime_duration, 7),
                "contact_frame": local_contact,
                "contact_seconds": round(contact_seconds, 7),
                "contact_tick_20hz": contact_tick,
                "buffer_window": local_buffer,
            }
        )
        total_frames += len(frames)

    selected_sources = [
        source
        for source in selection.get("sources", [])
        if source.get("id") in SELECTED_SOURCE_IDS
    ]
    if {source.get("id") for source in selected_sources} != SELECTED_SOURCE_IDS:
        raise RuntimeError("one or more selected G1 Moves source records are missing")

    live = {
        "schema": 2,
        "coordinate_system": selection["coordinate_system"],
        "quaternion_order": selection["quaternion_order"],
        "sample_rate": sample_rate,
        "preview_only": False,
        "live_gameplay_replacement": True,
        "human_review": {
            "status": "HUMAN_SELECTED_FOR_LIVE_GAMEPLAY",
            "selected": "ordinary_group_c",
            "requested_playback_speed_multiplier": PLAYBACK_SPEED,
            "date": "2026-09-01",
        },
        "authority": "human_selected_group_c_visual_pose_only",
        "root_authority": "SERVER_ENTITY_XZ_YAW_CAPTURED_ROOT_Y_ONLY",
        "sources": selected_sources,
        "bones": live_bones,
        "gameplay_contract": {
            "input": "repeated_left_click",
            "stage_order": [stage["clip"] for stage in stage_contracts],
            "advance_rule": "server_buffered_next_click",
            "playback_speed_multiplier": PLAYBACK_SPEED,
            "damage_authority": "server_contact_tick",
            "world_root_authority": "server_entity",
            "stand_reset_between_stages": False,
            "stages": stage_contracts,
        },
        "clips": live_clips,
        "provenance": {
            "selection_resource": str(args.source.relative_to(REPO_ROOT)).replace(
                "\\", "/"
            ),
            "selection_clip": "ordinary_group_c",
            "selection_first_cycle_frames": [0, 140],
            "total_live_frames": total_frames,
            "source_clip_sha256": hashlib.sha256(
                compact_bytes(source_clip)
            ).hexdigest(),
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(live, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    if not args.do_not_update_selection:
        selection["human_review"] = {
            "status": "HUMAN_SELECTED_GROUP_C",
            "selected": "ordinary_group_c",
            "requested_playback_speed_multiplier": PLAYBACK_SPEED,
            "date": "2026-09-01",
        }
        contract = selection.get("selection_contract", {})
        contract["chooseExactlyOneOrRejectAll"] = False
        contract["selectedGroup"] = "ordinary_group_c"
        contract["liveGameplayChanged"] = True
        contract["liveResource"] = str(args.output.relative_to(REPO_ROOT)).replace(
            "\\", "/"
        )
        contract["livePlaybackSpeedMultiplier"] = PLAYBACK_SPEED
        selection["selection_contract"] = contract
        args.source.write_text(
            json.dumps(selection, ensure_ascii=False, separators=(",", ":"))
            + "\n",
            encoding="utf-8",
        )

    print(
        f"promoted ordinary_group_c: clips={len(live_clips)} "
        f"bones={len(live_bones)} frames={total_frames} "
        f"speed={PLAYBACK_SPEED:.1f}x output={args.output}"
    )


if __name__ == "__main__":
    main()
