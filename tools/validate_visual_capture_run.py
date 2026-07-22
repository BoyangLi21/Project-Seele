#!/usr/bin/env python3
"""Fail a Visual Lab launcher run when its PNG batch or log is incomplete."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


REPO = Path(__file__).resolve().parent.parent
CAPTURE_ROOT = REPO / "run/screenshots/projectseele_visual"
LATEST_LOG = REPO / "run/logs/latest.log"
SNAPSHOT = REPO / "run/.projectseele_visual_before.json"
# Twenty-eight frozen Unit poses x thirteen cameras. Locomotion regression now
# includes run/jump/fall/crouch-walk/crawl instead of certifying only idle and
# one walk contact frame; the final rifle pose also proves the local weapon
# derivative and its shared first-/third-person skeleton.
EXPECTED = {
    "unit01": 364, "unit00": 364, "unit02": 364,
    "mass": 35, "tokyo3": 4, "tokyo3_retraction": 4, "geofront": 13,
    "geofront_sortie": 5,
    "silo": 6, "impact": 3,
}
VIEWS_PER_POSE = {"unit01": 13, "unit00": 13, "unit02": 13, "mass": 7}
FAILURE_PATTERNS = (
    r"VISUAL (?:CAPTURE|BATCH|MASS POSE|IMPACT) INVALID",
    r"Strict (?:Visual|Impact) capture refused",
    r"Visual screenshot failed",
    r"Visual capture failed: subject missing",
    r"VISUAL SILO (?:CAPTURE|AUTOMATION) INVALID",
    r"Launch-silo visual screenshot failed",
    r"VISUAL TOKYO3 INVALID",
    r"Strict Tokyo-3 capture refused",
    r"Tokyo-3 visual screenshot failed",
    r"VISUAL TOKYO3 RETRACTION INVALID",
    r"Tokyo-3 retraction visual screenshot failed",
    r"VISUAL GEOFRONT INVALID",
    r"GeoFront visual screenshot failed",
    r"VISUAL GEOFRONT SORTIE INVALID",
    r"GeoFront sortie visual screenshot failed",
    r"Visual Lab automation failed",
)
SILO_STAGES = (
    "gantry_rear_socket", "plug_descent_external", "plug_descent_cockpit",
    "hatch_locked", "ascent_mid", "surface_clear",
)
TOKYO3_RETRACTION_STAGES = (
    "deployed", "mid_descent", "fully_retracted", "restored",
)
GEOFRONT_SORTIE_STAGES = (
    "three_units_ready", "entry_plug_locked", "live_pilot_sensor", "ascent_mid",
    "tokyo3_surface_arrival",
)
GEOFRONT_VIEWS = (
    "cavern_overview", "natural_lake", "forest_canopy",
    "nerv_pyramid", "nerv_operations",
    "nerv_support_gallery", "nerv_briefing_room",
    "nerv_medical_support", "nerv_pressure_vestibule",
    "central_dogma_descent", "terminal_dogma", "lcl_lake", "lift_terminals",
)


def batch_names() -> set[str]:
    if not CAPTURE_ROOT.exists():
        return set()
    return {path.name for path in CAPTURE_ROOT.iterdir() if path.is_dir()}


def normalise_poses(value: str | None) -> list[str]:
    return [pose.strip() for pose in (value or "").split(",") if pose.strip()]


def begin(target: str, poses: list[str]) -> int:
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps({
        "target": target,
        "poses": poses,
        "batches": sorted(batch_names()),
    }),
                        encoding="utf-8")
    suffix = f" ({', '.join(poses)})" if poses else ""
    print(f"Visual capture baseline recorded for {target}{suffix}")
    return 0


def verify(target: str) -> int:
    try:
        before = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError) as exc:
        print(f"VISUAL RUN INVALID: capture baseline is unavailable: {exc}", file=sys.stderr)
        return 1
    if before.get("target") != target:
        print("VISUAL RUN INVALID: capture baseline target changed", file=sys.stderr)
        return 1
    fresh = sorted(batch_names() - set(before.get("batches", [])))
    if len(fresh) != 1:
        print(f"VISUAL RUN INVALID: expected one new batch for {target}, found {fresh}",
              file=sys.stderr)
        return 1
    batch = CAPTURE_ROOT / fresh[0]
    pngs = sorted(batch.glob("*.png"))
    poses = [str(value) for value in before.get("poses", [])]
    expected = (len(poses) * VIEWS_PER_POSE[target]
                if poses and target in VIEWS_PER_POSE else EXPECTED[target])
    if len(pngs) != expected:
        print(f"VISUAL RUN INVALID: {batch} has {len(pngs)} PNGs; expected {expected}",
              file=sys.stderr)
        return 1
    wrong_prefix = [path.name for path in pngs if not path.name.startswith(target + "_")]
    if wrong_prefix:
        print(f"VISUAL RUN INVALID: unexpected filenames: {wrong_prefix[:3]}", file=sys.stderr)
        return 1
    if target == "silo":
        missing = [stage for stage in SILO_STAGES
                   if not any(path.name.endswith(f"_{stage}.png") for path in pngs)]
        if missing:
            print(f"VISUAL RUN INVALID: silo stages missing: {missing}", file=sys.stderr)
            return 1
    if target == "tokyo3_retraction":
        missing = [stage for stage in TOKYO3_RETRACTION_STAGES
                   if not any(path.name.endswith(f"_{stage}.png") for path in pngs)]
        if missing:
            print(f"VISUAL RUN INVALID: Tokyo-3 retraction stages missing: {missing}",
                  file=sys.stderr)
            return 1
    if target == "geofront_sortie":
        missing = [stage for stage in GEOFRONT_SORTIE_STAGES
                   if not any(path.name.endswith(f"_{stage}.png") for path in pngs)]
        if missing:
            print(f"VISUAL RUN INVALID: GeoFront sortie stages missing: {missing}",
                  file=sys.stderr)
            return 1
    if target == "geofront":
        missing = [view for view in GEOFRONT_VIEWS
                   if not any(path.name.endswith(f"_{view}.png") for path in pngs)]
        if missing:
            print(f"VISUAL RUN INVALID: GeoFront views missing: {missing}",
                  file=sys.stderr)
            return 1
    try:
        log = LATEST_LOG.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"VISUAL RUN INVALID: cannot read latest.log: {exc}", file=sys.stderr)
        return 1
    failures = [pattern for pattern in FAILURE_PATTERNS
                if re.search(pattern, log, flags=re.IGNORECASE)]
    if failures:
        print(f"VISUAL RUN INVALID: latest.log matched {failures}", file=sys.stderr)
        return 1
    if "Visual Lab screenshots complete; closing unattended client" not in log:
        print("VISUAL RUN INVALID: unattended client completion marker is missing",
              file=sys.stderr)
        return 1
    SNAPSHOT.unlink(missing_ok=True)
    print(f"Visual capture verified: {target}, {len(pngs)} PNGs -> {batch}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("begin", "verify"))
    parser.add_argument("target", choices=tuple(EXPECTED))
    parser.add_argument("--poses",
                        help="comma-separated targeted capture list; begin records its exact PNG count")
    args = parser.parse_args()
    poses = normalise_poses(args.poses)
    if poses and args.target in {
            "impact", "silo", "tokyo3", "tokyo3_retraction", "geofront",
            "geofront_sortie"}:
        parser.error(f"{args.target} capture has fixed stages and does not accept --poses")
    return begin(args.target, poses) if args.action == "begin" else verify(args.target)


if __name__ == "__main__":
    raise SystemExit(main())
