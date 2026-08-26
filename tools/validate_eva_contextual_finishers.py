#!/usr/bin/env python3
"""Validate target-specific EVA finisher interaction-graph contracts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    document = json.loads(args.input.read_text(encoding="utf-8"))
    finishers = document.get("finishers", {})
    failures = []
    warnings = []
    priorities = []
    stage_ids = set()
    for finisher_id, finisher in finishers.items():
        for field in ("priority", "participants", "entry_requirements",
                      "stages", "source_basis", "target_rig_pending"):
            if field not in finisher:
                failures.append(f"{finisher_id}:missing_{field}")
        priorities.append(finisher.get("priority"))
        if len(finisher.get("participants", [])) < 2:
            failures.append(f"{finisher_id}:fewer_than_two_participants")
        if not finisher.get("entry_requirements"):
            failures.append(f"{finisher_id}:no_entry_requirements")
        stages = finisher.get("stages", [])
        if len(stages) < 2:
            failures.append(f"{finisher_id}:fewer_than_two_stages")
        for stage_index, stage in enumerate(stages):
            stage_id = stage.get("id")
            if not stage_id:
                failures.append(
                    f"{finisher_id}:stage_{stage_index}:missing_id"
                )
                continue
            qualified = f"{finisher_id}/{stage_id}"
            if qualified in stage_ids:
                failures.append(f"duplicate_stage:{qualified}")
            stage_ids.add(qualified)
            for field in ("attacker_contacts", "target_contacts", "abort"):
                if field not in stage:
                    failures.append(f"{qualified}:missing_{field}")
            if not stage.get("abort"):
                failures.append(f"{qualified}:empty_abort")
        if finisher.get("target_rig_pending"):
            warnings.append(f"{finisher_id}:target_rig_pending")
    if len(priorities) != len(set(priorities)):
        failures.append("finisher_priorities_not_unique")
    if priorities and sorted(priorities) != list(
            range(1, len(priorities) + 1)):
        failures.append("finisher_priorities_not_contiguous")
    if "no official frame" not in document.get("copyright_boundary", ""):
        failures.append("missing_explicit_official_frame_copy_boundary")
    report = {
        "schema": 1,
        "input": str(args.input.resolve()),
        "finisher_count": len(finishers),
        "stage_count": len(stage_ids),
        "backlog_count": len(document.get("backlog", [])),
        "failures": failures,
        "warnings": warnings,
        "passed": not failures,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
