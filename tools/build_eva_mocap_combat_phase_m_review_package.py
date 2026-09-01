#!/usr/bin/env python3
"""Render and package Phase M: new ordinary, locked forward, short reverse."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from build_eva_mocap_combat_review_package import (
    DEFAULT_BLENDER, VIEWS, digest, encode, make_panels, render_view, run,
)


REPO = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPO / (
    "artifacts/motion_research/eva_mocap_combat_phase_m_manual_review")
CLIPS = [
    ("eva_anime_body_drive", "新普通攻击：动漫式全身前冲重击"),
    ("eva_locked_knife_stab_twist_forward", "已通过并锁定：正手刺入扭转"),
    ("eva_short_knife_stab_twist_reverse", "新短反手刀：核心刺入扭转"),
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
    with tempfile.TemporaryDirectory(prefix=".phase_m_concat-",
                                     dir=output) as temporary:
        concat = Path(temporary) / "concat.txt"
        concat.write_text("".join(
            f"file '{video.as_posix().replace(chr(39), chr(39) * 2)}'\n"
            for video in videos), encoding="utf-8")
        combined = output / "00_EVA_PHASE_M_ALL.mp4"
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
    readme = """# EVA Phase M 人工验收包

Phase L 的正手刀已人工通过，本包逐帧保持完全相同；其帧数据 SHA-256 为
`414427cf77b59c25912f9fb1821dfa480c5e0be14a88d4969c945e8ff64acbbb`。

- 01：全新 Rapa Motion 60 FPS 动漫真人捕捉核心。单臂先行、骨盆前推、
  躯干跟进；不含 Phase-L 双臂扑砸；
- 02：锁定正手刀，仅用于确认包内没有回归；
- 03：独立 take 2 的短反手核心，去掉长等待段，最终 2.08 秒；
- 反手刀全程 blade/forearm dot 为负，未使用逐帧硬锁；
- 正式游戏动作未替换，自动门禁不构成视觉批准。

右下红色 `动作号-帧号` 只表示时间顺序。人工重点只需判断 01 是否适合作为
普通攻击，以及 03 的节奏是否足够短；02 已锁定，不必重新挑动作。
"""
    readme_path = output / "README_人工验收.md"
    readme_path.write_text(readme, encoding="utf-8")
    files = videos + [combined, readme_path] + [
        output / name for _, name in evidence
    ]
    manifest = {
        "schema": 1,
        "phase": "M",
        "result": "ELIGIBLE_FOR_HUMAN_REVIEW_ONLY",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "forwardKnifeStatus": "HUMAN_APPROVED_AND_HASH_LOCKED",
        "forwardKnifeFramesSha256": (
            "414427cf77b59c25912f9fb1821dfa480c5e0be14a88d4969c945e8ff64acbbb"),
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
