#!/usr/bin/env python3
"""Promote audited 3D motion candidates into semantic runtime slots."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--candidates", required=True, type=Path)
    parser.add_argument("--database-audit", required=True, type=Path)
    parser.add_argument("--exact-audit", required=True, type=Path)
    parser.add_argument("--mapping", action="append", default=[])
    parser.add_argument("--allow-new", action="store_true")
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base = json.loads(args.base.read_text(encoding="utf-8"))
    candidates = json.loads(args.candidates.read_text(encoding="utf-8"))
    database_audit = json.loads(args.database_audit.read_text(encoding="utf-8"))
    exact_audit = json.loads(args.exact_audit.read_text(encoding="utf-8"))
    candidate_hash = hashlib.sha256(args.candidates.read_bytes()).hexdigest()
    if database_audit.get("failure_count") != 0:
        raise SystemExit("candidate database audit is not green")
    if exact_audit.get("failure_count") != 0:
        raise SystemExit("candidate exact-mesh audit is not green")
    if database_audit.get("motion_db_sha256") != candidate_hash:
        raise SystemExit("candidate database audit hash is stale")
    if exact_audit.get("motion_db_sha256") != candidate_hash:
        raise SystemExit("candidate exact-mesh audit hash is stale")
    if base["bones"] != candidates["bones"]:
        raise SystemExit("candidate/runtime bone order mismatch")
    mappings = {}
    for item in args.mapping:
        if "=" not in item:
            raise SystemExit(f"invalid mapping {item!r}; expected slot=clip")
        slot, candidate = item.split("=", 1)
        if slot not in base["clips"] and not args.allow_new:
            raise SystemExit(f"unknown runtime slot {slot}")
        if candidate not in candidates["clips"]:
            raise SystemExit(f"unknown candidate clip {candidate}")
        mappings[slot] = candidate
    if not mappings:
        raise SystemExit("at least one --mapping is required")
    for slot, candidate in mappings.items():
        promoted = copy.deepcopy(candidates["clips"][candidate])
        promoted["role"] = (base["clips"][slot].get("role", "locomotion")
                            if slot in base["clips"] else
                            promoted.get("role", "motion"))
        promoted["promoted_from"] = candidate
        base["clips"][slot] = promoted
    known_sources = {source.get("name") for source in base.get("sources", [])}
    for source in candidates.get("sources", []):
        if source.get("name") not in known_sources:
            base.setdefault("sources", []).append(copy.deepcopy(source))
    base.setdefault("promotions", {}).update(mappings)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(base, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(
        f"EVA motion promotion: {len(mappings)} slots "
        f"output={args.output}"
    )


if __name__ == "__main__":
    main()
