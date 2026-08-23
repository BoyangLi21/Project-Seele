#!/usr/bin/env python3
"""Migrate the static cyan rescue shell to non-ticking transparent weave."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_geofront_cavern import scan
import migrate_s00_geofront_sky_shell as palette_migration


SOURCE = "minecraft:cyan_terracotta"
TARGET = "projectseele:geofront_skyweave"
EXPECTED = 1_834_340


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", type=Path, required=True)
    parser.add_argument("--backup-root", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    save = args.save.resolve()
    before, _ = scan(save, "projectseele:geofront")
    source_count = int(before["shellBlocks"].get(SOURCE, 0))
    print(f"proposal source={SOURCE} target={TARGET} blocks={source_count}")
    if source_count != EXPECTED:
        raise RuntimeError(
            f"shell precondition changed: expected {EXPECTED}, got {source_count}")
    if not args.apply:
        return

    palette_migration.SOURCE_BLOCK = SOURCE
    palette_migration.REPLACEMENT_BLOCK = TARGET
    result = palette_migration.migrate(save, args.backup_root.resolve())
    backup = Path(str(result["backup"]))
    after, _ = scan(save, "projectseele:geofront")
    cyan = int(after["shellBlocks"].get(SOURCE, 0))
    weave = int(after["shellBlocks"].get(TARGET, 0))
    if cyan != 0 or weave != EXPECTED:
        region_dir = save / "dimensions/projectseele/geofront/region"
        for path in backup.glob("r.*.*.mca"):
            shutil.copy2(path, region_dir / path.name)
        raise RuntimeError(
            f"migration read-back failed cyan={cyan} weave={weave}")

    result.update({
        "status": "APPLIED_AND_FULL_CAVERN_RESCAN_VERIFIED",
        "expectedShellBlocks": EXPECTED,
        "verifiedSourceRemaining": cyan,
        "verifiedTargetBlocks": weave,
    })
    receipt = backup / "static-weave-receipt.json"
    receipt.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    print(f"verified sourceRemaining={cyan} targetBlocks={weave}")
    print(f"backup={backup}")


if __name__ == "__main__":
    main()
