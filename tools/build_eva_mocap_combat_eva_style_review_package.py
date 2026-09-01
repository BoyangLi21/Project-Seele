#!/usr/bin/env python3
"""Render and package the Phase-L EVA-style free mocap candidates."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from build_eva_mocap_combat_review_package import (
    DEFAULT_BLENDER,
    VIEWS,
    digest,
    encode,
    make_panels,
    render_view,
    run,
)


REPO = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPO / (
    "artifacts/motion_research/"
    "eva_mocap_combat_eva_style_manual_review_phase_l")
CLIPS = [
    ("eva_style_maul_lunge", "EVA 式双臂扑进下砸"),
    ("eva_style_knife_stab_twist_forward", "新正手刀：刺入后扭转"),
    ("eva_style_knife_stab_twist_reverse", "新反手刀：冰锥刺入后扭转"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--motion-db", required=True, type=Path)
    parser.add_argument("--constraint-report", required=True, type=Path)
    parser.add_argument("--stabilization-report", required=True, type=Path)
    parser.add_argument("--exact-audit", required=True, type=Path)
    parser.add_argument("--grip-audit", required=True, type=Path)
    parser.add_argument("--blender", type=Path, default=DEFAULT_BLENDER)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    batch = datetime.now().strftime("%Y%m%d-%H%M%S")
    output = (args.output.resolve() if args.output else
              (DEFAULT_OUTPUT / batch).resolve())
    output.mkdir(parents=True, exist_ok=True)
    render_root = output / "render"
    jobs = [(clip, view) for clip, _ in CLIPS for view, _ in VIEWS]
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(
            render_view, args.blender.resolve(), args.blend.resolve(),
            args.motion_db.resolve(), clip, view, render_root)
            for clip, view in jobs]
        for future in futures:
            future.result()

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required")
    videos = []
    counts = {}
    panel_roots = []
    for order, (clip, label) in enumerate(CLIPS, 1):
        panels, count = make_panels(
            render_root, clip, label, order, output)
        panel_roots.append(panels)
        video = output / f"{order:02d}_{clip}.mp4"
        encode(ffmpeg, panels, video)
        videos.append(video)
        counts[clip] = count
    with tempfile.TemporaryDirectory(prefix=".phase_l_concat-",
                                     dir=output) as temporary:
        concat = Path(temporary) / "concat.txt"
        concat.write_text("".join(
            f"file '{video.as_posix().replace(chr(39), chr(39) * 2)}'\n"
            for video in videos), encoding="utf-8")
        combined = output / "00_EVA_STYLE_PHASE_L_ALL.mp4"
        run([
            ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(concat),
            "-c", "copy", "-movflags", "+faststart", str(combined),
        ])
    for panels in panel_roots:
        shutil.rmtree(panels)
    if render_root.parent != output:
        raise RuntimeError("refusing to remove render frames outside package")
    shutil.rmtree(render_root)

    evidence = [
        (args.constraint_report, "constraint_gate.json"),
        (args.stabilization_report, "root_contact_stabilization.json"),
        (args.exact_audit, "exact_tiger_3d_audit.json"),
        (args.grip_audit, "knife_grip_geometry_audit.json"),
    ]
    for source, name in evidence:
        shutil.copy2(source, output / name)
    readme = """# EVA 原作动作语言 Phase L 人工验收包

Phase K 三条已全部人工拒绝，本包没有复用其中任何动作。

- 01：Rokoko `ZombieAttack_Walking` 的双臂扑进下砸段；目标是躯干和
  骨盆先行、双臂随后砸落，不是拳击、掌炮或单手爪击；
- 02：Eric Jacobus `stabTwist Knife` take 1，新正手刺入、停顿、扭转、拔出；
- 03：独立 take 2，新反手冰锥式刺入、扭转、回收；
- 两个刀动作不是旧 `KnifeFight` 的重定向或换角度版本；
- 正手 blade/forearm dot 中位数 `+0.3063`，反手为 `-0.4763`，
  两者全程符号相反且没有逐帧硬锁刀骨；
- 正式游戏动作未替换，自动门禁不能视觉批准。

右下角红色 `动作号-帧号` 只表示时间顺序。请重点判断整体轮廓、巨大惯性、
躯干先行和刀刺入后的停顿/扭转是否更接近 EVA 原作的战斗语言。
"""
    readme_path = output / "README_人工验收.md"
    readme_path.write_text(readme, encoding="utf-8")
    files = videos + [combined, readme_path] + [
        output / name for _, name in evidence
    ]
    manifest = {
        "schema": 1,
        "phase": "L",
        "result": "ELIGIBLE_FOR_HUMAN_REVIEW_ONLY",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "combatLanguage": "TORSO_LED_MAUL_AND_COMMITTED_STAB_TWIST",
        "supportMode": "CAPTURED_FULL_BODY",
        "liveGameplayChanged": False,
        "motionDatabase": str(args.motion_db.resolve()),
        "motionDatabaseSha256": digest(args.motion_db),
        "fps": 30,
        "resolution": [1920, 360],
        "views": [view for view, _ in VIEWS],
        "clips": [{
            "order": order, "name": clip, "label": label,
            "frames": counts[clip],
        } for order, (clip, label) in enumerate(CLIPS, 1)],
        "redNumberMeaning": (
            "ACTION_ORDER-FRAME_ORDER; chronological locator only; not "
            "geometry, texture, UI, bone, or joint marker"),
        "visuallyApproved": False,
        "files": [{
            "name": path.name, "bytes": path.stat().st_size,
            "sha256": digest(path),
        } for path in files],
    }
    (output / "manifest.json").write_text(json.dumps(
        manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    archive = output.parent / f"{output.name}.zip"
    if archive.exists():
        archive.unlink()
    shutil.make_archive(str(archive.with_suffix("")), "zip",
                        root_dir=output.parent, base_dir=output.name)
    print(json.dumps({
        "output": str(output), "combined": str(combined),
        "archive": str(archive), "frames": counts,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
