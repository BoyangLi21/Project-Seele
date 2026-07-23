"""Print visual sanity metrics for one or more captured PNG files."""

from pathlib import Path
import sys

from png_scene_quality import invalid_scene_pngs, png_scene_metrics


def main() -> int:
    paths = [Path(value) for value in sys.argv[1:]]
    if not paths:
        print("usage: check_png_quality.py <png> [<png> ...]", file=sys.stderr)
        return 2
    invalid = set(invalid_scene_pngs(paths))
    for path in paths:
        dark, texture, colours = png_scene_metrics(path)
        print(f"{path}: dark={dark:.3f} texture={texture:.3f} colours={colours}")
    if invalid:
        print("INVALID VISUAL EVIDENCE:", file=sys.stderr)
        for reason in sorted(invalid):
            print(f"- {reason}", file=sys.stderr)
        return 1
    print("Visual evidence sanity check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
