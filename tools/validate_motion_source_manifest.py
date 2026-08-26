#!/usr/bin/env python3
"""Validate immutable motion-source manifests and all recorded file hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


PUBLIC_LICENSES = {
    "CC BY 4.0",
    "CC BY 3.0 Unported",
    "CC0 1.0",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifests", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strict-release", action="store_true")
    return parser.parse_args()


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def within(root: Path, path: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def validate_file(root: Path, relative: str, expected_size,
                  expected_hash, failures: list[str], label: str) -> None:
    path = (root / relative).resolve()
    if not within(root, path):
        failures.append(f"{label}: path escapes manifest root: {relative}")
        return
    if not path.is_file():
        failures.append(f"{label}: missing file: {relative}")
        return
    if expected_size is None:
        failures.append(f"{label}: missing byte count: {relative}")
    elif path.stat().st_size != int(expected_size):
        failures.append(
            f"{label}: byte count mismatch: {relative} "
            f"expected={expected_size} actual={path.stat().st_size}")
    if not expected_hash:
        failures.append(f"{label}: missing SHA-256: {relative}")
    else:
        actual = digest(path)
        if actual.lower() != str(expected_hash).lower():
            failures.append(
                f"{label}: SHA-256 mismatch: {relative} "
                f"expected={expected_hash} actual={actual}")


def validate_manifest(path: Path, strict_release: bool) -> dict:
    manifest_path = path.resolve()
    root = manifest_path.parent.resolve()
    payload = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    failures: list[str] = []
    warnings: list[str] = []
    for key in ("schema", "source", "official_page", "license",
                "license_url", "retrieved_at_utc", "assets"):
        if not payload.get(key):
            failures.append(f"missing top-level field: {key}")
    if strict_release and payload.get("license") not in PUBLIC_LICENSES:
        failures.append(
            f"license is not approved for public release: "
            f"{payload.get('license')!r}")
    if not isinstance(payload.get("assets"), list) or not payload.get("assets"):
        failures.append("assets must be a non-empty list")
    else:
        for index, asset in enumerate(payload["assets"]):
            label = asset.get("id") or asset.get("file") or f"asset[{index}]"
            relative = asset.get("file") or asset.get("archive")
            if not relative:
                failures.append(f"{label}: missing file/archive path")
                continue
            validate_file(root, relative, asset.get("bytes"),
                          asset.get("sha256"), failures, label)
            extracted = asset.get("extracted_files") or []
            extracted_root = root / "third_party_normalized" / "source_extract"
            if asset.get("id"):
                extracted_root /= str(asset["id"])
            for item in extracted:
                validate_file(
                    extracted_root.resolve(), str(item.get("file", "")),
                    item.get("bytes"), item.get("sha256"), failures,
                    f"{label}/extracted",
                )
            declared_count = asset.get("extracted_file_count")
            if declared_count is not None and int(declared_count) != len(extracted):
                failures.append(
                    f"{label}: extracted file count mismatch: "
                    f"declared={declared_count} listed={len(extracted)}")
    status = str(payload.get("status", ""))
    if "runtime" in status and "not_runtime" not in status:
        warnings.append("manifest status names a runtime asset; verify promotion evidence")
    return {
        "manifest": str(manifest_path),
        "source": payload.get("source"),
        "license": payload.get("license"),
        "asset_count": len(payload.get("assets") or []),
        "passed": not failures,
        "failures": failures,
        "warnings": warnings,
    }


def main() -> None:
    args = parse_args()
    reports = [validate_manifest(path, args.strict_release)
               for path in args.manifests]
    result = {
        "schema": 1,
        "strict_release": args.strict_release,
        "passed": all(report["passed"] for report in reports),
        "manifests": reports,
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
