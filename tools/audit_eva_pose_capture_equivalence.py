#!/usr/bin/env python3
"""Compare final rendered poses across an authority-only migration."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


FIELDS = {
    "finalPosition": 1.0e-7,
    "finalRotationRadians": 1.0e-7,
    "finalScale": 1.0e-7,
    # Gecko's localSpaceMatrix includes render-offset/camera terms and varies
    # slightly between client launches even when final bone channels match.
    "localMatrix": 2.0e-5,
    "modelMatrix": 1.0e-5,
}
RESOURCE_FIELDS = (
    "meshSha256", "geoSha256", "animationSha256", "textureSha256",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    return parser.parse_args()


def read_frame(path: Path) -> tuple[dict, dict]:
    records = [json.loads(line) for line in
               path.read_text(encoding="utf-8").splitlines() if line.strip()]
    frames = [record for record in records if record.get("type") == "frame"]
    if not frames:
        raise SystemExit(f"EVA pose equivalence invalid: no frame in {path}")
    return records[0], frames[0]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("EVA pose equivalence invalid: " + message)


def maximum_delta(baseline: dict, candidate: dict, field: str) -> float:
    result = 0.0
    for name in baseline:
        left = baseline[name][field]
        right = candidate[name][field]
        require(len(left) == len(right), f"{name}.{field} length differs")
        for before, after in zip(left, right):
            require(math.isfinite(before) and math.isfinite(after),
                    f"{name}.{field} contains a non-finite value")
            result = max(result, abs(before - after))
    return result


def main() -> None:
    args = parse_args()
    baseline_header, baseline = read_frame(args.baseline.resolve())
    candidate_header, candidate = read_frame(args.candidate.resolve())
    require(baseline["poseGraph"]["actionToken"] ==
            candidate["poseGraph"]["actionToken"],
            "action tokens differ")
    require(baseline["entity"]["weapon"] == candidate["entity"]["weapon"],
            "weapon states differ")
    require(set(baseline["bones"]) == set(candidate["bones"]),
            "captured bone sets differ")
    for field in RESOURCE_FIELDS:
        require(baseline["resources"].get(field) ==
                candidate["resources"].get(field),
                f"active resource {field} differs")

    deltas = {
        field: maximum_delta(baseline["bones"], candidate["bones"], field)
        for field in FIELDS
    }
    failures = [
        f"{field}={value:.9g}>{FIELDS[field]:.9g}"
        for field, value in deltas.items() if value > FIELDS[field]
    ]
    require(not failures, "; ".join(failures))
    print(json.dumps({
        "verdict": "PASS",
        "baselineMode": baseline_header.get("poseGraphMode"),
        "candidateMode": candidate_header.get("poseGraphMode"),
        "actionToken": candidate["poseGraph"]["actionToken"],
        "bones": len(candidate["bones"]),
        "maximumDeltas": deltas,
        "limits": FIELDS,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
