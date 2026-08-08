#!/usr/bin/env python3
"""Apply the stable manual-test profile without lowering EVA mesh quality."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OPTIONS = ROOT / "run" / "options.txt"
COMMON_CONFIG = ROOT / "run" / "config" / "projectseele-common.toml"
PROFILE = {
    "renderDistance": "8",
    "simulationDistance": "6",
    "particles": "1",
    "biomeBlendRadius": "0",
    "syncChunkWrites": "false",
    "entityDistanceScaling": "0.8",
    "mipmapLevels": "2",
    "enableVsync": "false",
    "maxFps": "120",
    "fov": "0.0",
    "guiScale": "3",
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

    # Manual R28 review uses the real command-room rise/lower buttons.  An
    # earlier performance rescue profile left this false after GPU selection
    # had already solved the frame-rate problem, making both physical controls
    # look dead even though their server coordinates were correct.
    if COMMON_CONFIG.exists():
        config = COMMON_CONFIG.read_text(encoding="utf-8")
        config = config.replace(
            "\trescueMode = true",
            "\trescueMode = false",
        )
        config = config.replace(
            "\tdynamicTokyo3Retraction = false",
            "\tdynamicTokyo3Retraction = true",
        )
        config = config.replace(
            "\tdynamicLclBlocks = false",
            "\tdynamicLclBlocks = true",
        )
        config = config.replace(
            "\tdynamicBridgeBlocks = false",
            "\tdynamicBridgeBlocks = true",
        )
        COMMON_CONFIG.write_text(config, encoding="utf-8")
    print("SEELE manual performance profile: 1280x720 window, "
          "client heap 6G (launcher), render 8, simulation 6, "
          "VSync off, max FPS 120, FOV 70, GUI 3, "
          "entity range 80%, decreased particles, async chunk writes; "
          "Tokyo-3 motion enabled; EVA meshes unchanged.")


if __name__ == "__main__":
    main()
