#!/usr/bin/env python3
"""Validate the continuous EVA combat action-graph contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", required=True, type=Path)
    parser.add_argument("--fragments", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    graph = json.loads(args.graph.read_text(encoding="utf-8"))
    fragment_doc = json.loads(args.fragments.read_text(encoding="utf-8"))
    fragments = {row["id"]: row for row in fragment_doc["fragments"]}
    nodes = graph["nodes"]
    failures = []
    warnings = []
    for node_id, node in nodes.items():
        for field in ("domain", "effectors", "support", "redirectible_phase",
                      "commit_phase", "contact_phase", "recovery_phase",
                      "miss_outcome", "hit_outcome"):
            if field not in node:
                failures.append(f"{node_id}:missing_{field}")
        fragment = node.get("source_fragment")
        if fragment is not None and fragment not in fragments:
            failures.append(f"{node_id}:unknown_fragment:{fragment}")
        if (fragment is not None and fragment in fragments
                and fragments[fragment].get("source") is None):
            warnings.append(
                f"{node_id}:fragment_source_pending:{fragment}"
            )
        if fragment is not None and fragment in fragments:
            fragment_status = str(fragments[fragment].get("status", ""))
            if ("blocked" in fragment_status
                    or "rejected" in fragment_status):
                warnings.append(
                    f"{node_id}:fragment_not_promotable:{fragment}:"
                    f"{fragment_status}"
                )
        if fragment is None:
            warnings.append(f"{node_id}:project_authored_source_pending")
        for phase_name in ("redirectible_phase", "commit_phase",
                           "contact_phase", "recovery_phase"):
            phase = node.get(phase_name)
            if not isinstance(phase, list) or len(phase) != 2:
                continue
            if not (0.0 <= phase[0] <= phase[1] <= 1.0):
                failures.append(f"{node_id}:{phase_name}_outside_0_1")
        if not node.get("miss_outcome"):
            failures.append(f"{node_id}:missing_miss_outcome")
    for index, edge in enumerate(graph["edges"]):
        if edge.get("from") not in nodes:
            failures.append(f"edge_{index}:unknown_from")
        if edge.get("to") not in nodes:
            failures.append(f"edge_{index}:unknown_to")
        if not edge.get("when"):
            failures.append(f"edge_{index}:missing_condition")
    for required in ("target_contact", "ground_contact",
                     "environment_contact", "no_contact"):
        if not graph.get("pounce_resolvers", {}).get(required):
            failures.append(f"pounce:missing_{required}_resolver")
    payload = {
        "schema": 1,
        "graph": str(args.graph.resolve()),
        "node_count": len(nodes),
        "edge_count": len(graph["edges"]),
        "failures": failures,
        "warnings": warnings,
        "passed": not failures,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
