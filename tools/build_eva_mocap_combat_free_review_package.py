#!/usr/bin/env python3
"""Render and package the free Rokoko Phase-K combat candidates."""

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
    "eva_mocap_combat_free_manual_review_phase_k")
CLIPS = [
    ("free_mutant_claw_right", "Rokoko 右臂前冲爪击"),
    ("free_forward_knife_combo", "保留：用户识别正手粒子刀"),
    ("free_reverse_knife_combo", "新增：几何约束反手粒子刀"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--motion-db", required=True, type=Path)
    parser.add_argument("--constraint-report", required=True, type=Path)
    parser.add_argument("--stabilization-report", required=True, type=Path)
    parser.add_argument("--exact-audit", required=True, type=Path)
    parser.add_argument("--grip-audit", required=True, type=Path)
    parser.add_argument("--reverse-solve-report", required=True, type=Path)
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
    with tempfile.TemporaryDirectory(prefix=".phase_k_concat-",
                                     dir=output) as temporary:
        concat = Path(temporary) / "concat.txt"
        concat.write_text("".join(
            f"file '{video.as_posix().replace(chr(39), chr(39) * 2)}'\n"
            for video in videos), encoding="utf-8")
        combined = output / (
            "00_EVA_FREE_CLAW_FORWARD_REVERSE_PHASE_K_ALL.mp4")
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
        (args.reverse_solve_report, "reverse_grip_geometry_solve.json"),
    ]
    for source, name in evidence:
        shutil.copy2(source, output / name)
    readme = """# EVA 免费真人动捕战斗 Phase K 人工验收包

Phase J 开放掌已人工拒绝，本包不再包含该动作。

- 01：Rokoko `MutantClaws` 第 778–792 帧；单次右臂前冲爪击，
  是上半身主导攻击，不是 boxing、掌炮或踹击；
- 02：保留 Phase J 刀动作，并按用户观察纠正标记为正手；
- 03：同一真人刀动作的新增反手版本。刀刃方向由最终几何逐帧约束为
  从手腕指向肘部，blade/forearm dot 全程约 `-1.0`；
- 三条均来自 Rokoko 官方免费真人捕捉，保留骨盆、双腿和支撑脚；
- 反手求解只写刀骨旋转，不写身体关节，也不移动握点；
- 正式游戏动作没有替换，自动门禁只给人工审查资格。

右下角红色 `动作号-帧号` 只表示时间顺序，不是模型、贴图、UI、
骨骼或关节标记。请分别判断爪击是否适合作为普通攻击，以及 02/03 是否
能清楚区分正手与反手。
"""
    readme_path = output / "README_人工验收.md"
    readme_path.write_text(readme, encoding="utf-8")
    files = videos + [combined, readme_path] + [
        output / name for _, name in evidence
    ]
    manifest = {
        "schema": 1,
        "phase": "K",
        "result": "ELIGIBLE_FOR_HUMAN_REVIEW_ONLY",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "unarmedVocabulary": "RIGHT_CLAW_UPPER_BODY_NOT_BOXING_NOT_KICK",
        "knifeGrip": "USER_IDENTIFIED_FORWARD_PLUS_GEOMETRY_SOLVED_REVERSE",
        "reverseGripBladeForearmDot": -1.0,
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
