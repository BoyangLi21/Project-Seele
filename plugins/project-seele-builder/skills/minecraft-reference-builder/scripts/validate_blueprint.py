#!/usr/bin/env python3
"""Validate the evidence and geometry gates for a reference-build blueprint."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse


CONFIDENCE = {"verified", "cross-checked", "inferred"}


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read valid JSON: {exc}"]
    if not isinstance(payload, dict):
        return ["root must be an object"]

    if payload.get("schemaVersion") != 1:
        fail(errors, "schemaVersion must be 1")
    if not nonempty_string(payload.get("slug")):
        fail(errors, "slug must be a non-empty string")

    target = payload.get("target")
    if not isinstance(target, dict):
        fail(errors, "target must be an object")
    else:
        for key in ("name", "version", "scalePolicy"):
            if not nonempty_string(target.get(key)):
                fail(errors, f"target.{key} must be a non-empty string")

    sources = payload.get("sources")
    covered_views: set[str] = set()
    distinct_hosts: set[str] = set()
    if not isinstance(sources, list) or len(sources) < 3:
        fail(errors, "sources must contain at least three entries")
    else:
        for index, source in enumerate(sources):
            label = f"sources[{index}]"
            if not isinstance(source, dict):
                fail(errors, f"{label} must be an object")
                continue
            url = source.get("url")
            parsed = urlparse(url) if nonempty_string(url) else None
            if parsed is None or parsed.scheme not in {"http", "https"} or not parsed.netloc:
                fail(errors, f"{label}.url must be an HTTP(S) page URL")
            else:
                distinct_hosts.add(parsed.netloc.lower())
            views = source.get("views")
            if not isinstance(views, list) or not views or not all(nonempty_string(v) for v in views):
                fail(errors, f"{label}.views must be a non-empty string array")
            else:
                covered_views.update(v.lower() for v in views)
            establishes = source.get("establishes")
            if not isinstance(establishes, list) or not establishes:
                fail(errors, f"{label}.establishes must be a non-empty array")
            if source.get("confidence") not in CONFIDENCE:
                fail(errors, f"{label}.confidence must be one of {sorted(CONFIDENCE)}")
    if len(distinct_hosts) < 2:
        fail(errors, "sources must cover at least two distinct hosts")
    if not any("exterior" in view or view in {"front", "side", "rear", "aerial", "front-three-quarter"} for view in covered_views):
        fail(errors, "sources must cover an exterior view")

    dimensions = payload.get("dimensions")
    if not isinstance(dimensions, dict):
        fail(errors, "dimensions must be an object")
    else:
        for key in ("length", "width", "height"):
            value = dimensions.get(key)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                fail(errors, f"dimensions.{key} must be a positive integer")

    frame = payload.get("coordinateFrame")
    if not isinstance(frame, dict):
        fail(errors, "coordinateFrame must be an object")
    else:
        for key in ("originMeaning", "forward", "entranceSide"):
            if not nonempty_string(frame.get(key)):
                fail(errors, f"coordinateFrame.{key} must be a non-empty string")

    palette = payload.get("palette")
    if not isinstance(palette, dict) or not palette:
        fail(errors, "palette must be a non-empty object")
    elif not all(nonempty_string(k) and nonempty_string(v) for k, v in palette.items()):
        fail(errors, "palette keys and values must be non-empty strings")

    for key in ("signatureFeatures", "rooms", "batches", "acceptanceViews", "uncertainties"):
        if not isinstance(payload.get(key), list):
            fail(errors, f"{key} must be an array")
    if isinstance(payload.get("signatureFeatures"), list) and not payload["signatureFeatures"]:
        fail(errors, "signatureFeatures must not be empty")
    if isinstance(payload.get("rooms"), list) and not payload["rooms"]:
        fail(errors, "rooms must not be empty")
    if isinstance(payload.get("batches"), list) and not payload["batches"]:
        fail(errors, "batches must not be empty")
    if isinstance(payload.get("acceptanceViews"), list) and len(payload["acceptanceViews"]) < 3:
        fail(errors, "acceptanceViews must contain at least three views")

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_blueprint.py <blueprint.json>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    errors = validate(path)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"OK: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
