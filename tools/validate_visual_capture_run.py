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
EXPECTED = {"unit01": 156, "unit00": 156, "unit02": 156, "mass": 35, "impact": 3}
FAILURE_PATTERNS = (
    r"VISUAL (?:CAPTURE|BATCH|MASS POSE|IMPACT) INVALID",
    r"Strict (?:Visual|Impact) capture refused",
    r"Visual screenshot failed",
    r"Visual capture failed: subject missing",
    r"Visual Lab automation failed",
)


def batch_names() -> set[str]:
    if not CAPTURE_ROOT.exists():
        return set()
    return {path.name for path in CAPTURE_ROOT.iterdir() if path.is_dir()}


def begin(target: str) -> int:
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps({"target": target, "batches": sorted(batch_names())}),
                        encoding="utf-8")
    print(f"Visual capture baseline recorded for {target}")
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
    expected = EXPECTED[target]
    if len(pngs) != expected:
        print(f"VISUAL RUN INVALID: {batch} has {len(pngs)} PNGs; expected {expected}",
              file=sys.stderr)
        return 1
    wrong_prefix = [path.name for path in pngs if not path.name.startswith(target + "_")]
    if wrong_prefix:
        print(f"VISUAL RUN INVALID: unexpected filenames: {wrong_prefix[:3]}", file=sys.stderr)
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
    args = parser.parse_args()
    return begin(args.target) if args.action == "begin" else verify(args.target)


if __name__ == "__main__":
    raise SystemExit(main())
