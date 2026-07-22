#!/usr/bin/env python3
"""Apply the stable manual-test profile without lowering EVA mesh quality."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OPTIONS = ROOT / "run" / "options.txt"
PROFILE = {
    "renderDistance": "10",
    "simulationDistance": "6",
    "particles": "1",
    "biomeBlendRadius": "0",
    "syncChunkWrites": "false",
    "entityDistanceScaling": "0.8",
    "mipmapLevels": "2",
}


def main() -> None:
    OPTIONS.parent.mkdir(parents=True, exist_ok=True)
    lines = OPTIONS.read_text(encoding="utf-8").splitlines() \
        if OPTIONS.exists() else []
    found: set[str] = set()
    updated: list[str] = []
    for line in lines:
        key, separator, _ = line.partition(":")
        if separator and key in PROFILE:
            updated.append(f"{key}:{PROFILE[key]}")
            found.add(key)
        else:
            updated.append(line)
    for key, value in PROFILE.items():
        if key not in found:
            updated.append(f"{key}:{value}")
    OPTIONS.write_text("\n".join(updated) + "\n", encoding="utf-8")
    print("SEELE manual performance profile: client heap 6G (launcher), "
          "render 10, simulation 6, entity range 80%, decreased particles, "
          "async chunk writes; EVA meshes unchanged.")


if __name__ == "__main__":
    main()
