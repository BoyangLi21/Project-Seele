#!/usr/bin/env python3
"""Cache the expensive private EVA asset conversion used by the desktop launcher."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAMP = ROOT / ".Codex" / "local-runtime-cache.json"
GENERATOR_GLOBS = (
    "tools/make_smod_*.py",
    "tools/make_tiger_*.py",
    "tools/make_eud_*.py",
    "tools/make_lilith_model_pack.py",
    "tools/make_downloaded_*.py",
    "tools/make_entry_plug_model.py",
    "tools/make_kantrophe_positron_pack.py",
    "tools/make_original_*.py",
    "tools/make_ultraman_*.py",
    "tools/eva_finger_axis_repair.py",
    "tools/eva_locomotion_*.json",
    "tools/export_accepted_locomotion_to_gecko.py",
    "tools/validate_local_eva_pack.py",
)
SOURCE_ROOTS = (
    ROOT / "external-assets" / "incoming",
    ROOT / "external-assets" / "work" / "positron_rifle_export",
    ROOT / "external-assets" / "work" / "pallet-rifle-oni",
)
SOURCE_FILES = (
    ROOT / "evaaddon1-0.zip",
    ROOT / "eud-1.1.0-forge-1.20.1.jar",
)
REQUIRED_OUTPUTS = (
    "mesh/eva_unit00.mesh.json",
    "mesh/eva_unit01.mesh.json",
    "mesh/eva_unit02.mesh.json",
    "mesh/mass_production_eva.mesh.json",
    "mesh/entry_plug.mesh.json",
    "mesh/entry_plug_unit00.mesh.json",
    "mesh/entry_plug_unit01.mesh.json",
    "mesh/entry_plug_unit02.mesh.json",
    "mesh/progressive_knife.mesh.json",
    "mesh/longinus_lance.mesh.json",
    "mesh/positron_cannon.mesh.json",
    "mesh/eva_pallet_smg.mesh.json",
    "mesh/eva_n2_device.mesh.json",
    "mesh/ultraman_avatar.mesh.json",
    "geo/ultraman_avatar.geo.json",
    "animations/ultraman_avatar.animation.json",
    "textures/entity/ultraman_avatar.png",
    "textures/entity/eva_unit01.png",
)
OUTPUT_ROOT = (ROOT / "run" / "resourcepacks" / "eva_real_model"
               / "assets" / "projectseele")


def iter_inputs() -> list[Path]:
    paths: set[Path] = set()
    for pattern in GENERATOR_GLOBS:
        paths.update(path for path in ROOT.glob(pattern) if path.is_file())
    paths.update(path for path in SOURCE_FILES if path.is_file())
    for source_root in SOURCE_ROOTS:
        if not source_root.is_dir():
            continue
        paths.update(path for path in source_root.rglob("*") if path.is_file())
    return sorted(paths, key=lambda path: path.as_posix().lower())


def signature() -> str:
    digest = hashlib.sha256()
    for path in iter_inputs():
        stat = path.stat()
        try:
            relative = path.relative_to(ROOT).as_posix()
        except ValueError:
            relative = path.as_posix()
        digest.update(relative.encode("utf-8", "surrogatepass"))
        digest.update(b"\0")
        digest.update(str(stat.st_size).encode("ascii"))
        digest.update(b"\0")
        digest.update(str(stat.st_mtime_ns).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def outputs_present() -> bool:
    pack_meta = OUTPUT_ROOT.parents[1] / "pack.mcmeta"
    return pack_meta.is_file() and all(
        (OUTPUT_ROOT / relative).is_file() for relative in REQUIRED_OUTPUTS)


def current() -> bool:
    if not outputs_present() or not STAMP.is_file():
        return False
    try:
        value = json.loads(STAMP.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return value.get("schema") == 1 and value.get("signature") == signature()


def mark() -> None:
    if not outputs_present():
        raise SystemExit("Cannot mark local runtime cache: required outputs are missing")
    STAMP.parent.mkdir(parents=True, exist_ok=True)
    STAMP.write_text(json.dumps({
        "schema": 1,
        "signature": signature(),
        "private_local_only": True,
    }, indent=2), encoding="utf-8")
    print("Local EVA runtime cache marked current")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("check", "mark"))
    args = parser.parse_args()
    if args.action == "mark":
        mark()
        return 0
    if current():
        print("Local EVA runtime cache is current")
        return 0
    print("Local EVA runtime cache requires refresh")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
