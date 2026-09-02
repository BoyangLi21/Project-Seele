#!/usr/bin/env python3
"""Promote the human-selected Phase-U K1 side kick into a live resource."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO / (
    "src/main/resources/assets/projectseele/motion/"
    "eva_mocap_kick_phase_u_review_v1.json"
)
DEFAULT_OUTPUT = REPO / (
    "src/main/resources/assets/projectseele/motion/"
    "eva_kick_side_left_v1.json"
)
SOURCE_CLIP = "kick_group_side_left"
LIVE_CLIP = "kick_side_left"
PLAYBACK_SPEED = 1.5
CONTACT_FRAME = 48


def compact(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    review = json.loads(args.source.read_text(encoding="utf-8"))
    if review.get("schema") != 2 or float(review.get("sample_rate", 0)) != 60.0:
        raise RuntimeError("Phase-U kick review must be schema 2 at 60 Hz")
    source_bones = list(review.get("bones", []))
    if not source_bones or source_bones[-1] != "knife":
        raise RuntimeError("expected hidden knife as final review bone")
    source_clip = review.get("clips", {}).get(SOURCE_CLIP)
    if source_clip is None:
        raise RuntimeError(f"missing selected kick clip {SOURCE_CLIP}")
    frames = json.loads(json.dumps(source_clip["frames"]))
    for frame in frames:
        rotations = frame.get("rotation_wxyz", [])
        if len(rotations) != len(source_bones):
            raise RuntimeError("kick review bone/frame mismatch")
        frame["rotation_wxyz"] = rotations[:-1]
    authored_duration = (len(frames) - 1) / 60.0
    runtime_duration = authored_duration / PLAYBACK_SPEED
    contact_seconds = CONTACT_FRAME / 60.0 / PLAYBACK_SPEED
    contact_tick = max(1, round(contact_seconds * 20.0))
    selected_source = next(
        source for source in review.get("sources", [])
        if source.get("id") == source_clip.get("source_id")
    )
    output = {
        "schema": 2,
        "coordinate_system": review["coordinate_system"],
        "quaternion_order": review["quaternion_order"],
        "sample_rate": 60.0,
        "preview_only": False,
        "live_gameplay_replacement": True,
        "human_review": {
            "status": "HUMAN_SELECTED_FOR_LIVE_GAMEPLAY",
            "selected": "K1_SIDE_LEFT",
            "requested_playback_speed_multiplier": PLAYBACK_SPEED,
            "date": "2026-09-02",
        },
        "authority": "human_selected_k1_side_kick_visual_pose_only",
        "root_authority": "SERVER_ENTITY_XZ_YAW_CAPTURED_ROOT_Y_ONLY",
        "sources": [selected_source],
        "bones": source_bones[:-1],
        "gameplay_contract": {
            "input": "key_b_existing_stomp_action",
            "playback_speed_multiplier": PLAYBACK_SPEED,
            "damage_authority": "server_contact_tick",
            "contact_frame": CONTACT_FRAME,
            "contact_seconds": round(contact_seconds, 7),
            "contact_tick_20hz": contact_tick,
            "damage": 50.0,
            "cooldown_ticks": 50,
            "damage_and_cooldown_changed": False,
            "world_root_authority": "server_entity",
            "ordinary_attack_bidirectional_buffer": True,
        },
        "clips": {
            LIVE_CLIP: {
                "duration_seconds": round(authored_duration, 7),
                "runtime_duration_seconds": round(runtime_duration, 7),
                "playback_speed_multiplier": PLAYBACK_SPEED,
                "loop": False,
                "role": "live_side_kick_key_b",
                "kind": "g1_kick_side_left",
                "support_mode": source_clip["support_mode"],
                "contact_authority": source_clip["contact_authority"],
                "grip": source_clip["grip"],
                "contact_frame": CONTACT_FRAME,
                "frame_sha256": hashlib.sha256(compact(frames)).hexdigest(),
                "frames": frames,
            }
        },
        "root_contact_stabilization": review.get(
            "root_contact_stabilization"),
        "exact_grounding": review.get("exact_grounding"),
        "provenance": {
            "review_resource": str(args.source.relative_to(REPO)).replace(
                "\\", "/"),
            "review_clip": SOURCE_CLIP,
            "review_clip_sha256": hashlib.sha256(
                compact(source_clip)).hexdigest(),
            "total_live_frames": len(frames),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(
        f"promoted K1 side kick: clips=1 bones={len(source_bones) - 1} "
        f"frames={len(frames)} speed={PLAYBACK_SPEED:.1f}x "
        f"contactTick={contact_tick} output={args.output}"
    )


if __name__ == "__main__":
    main()
