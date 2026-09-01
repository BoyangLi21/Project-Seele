#!/usr/bin/env python3
"""Render the Phase-I non-boxing and reverse-grip review package."""

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
    "eva_mocap_combat_reverse_manual_review_phase_i")
CLIPS = [
    ("nonboxing_palm_left", "非拳击掌根击"),
    ("reverse_knife_backknuckle", "反手粒子刀回削"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--motion-db", required=True, type=Path)
    parser.add_argument("--constraint-report", required=True, type=Path)
    parser.add_argument("--stabilization-report", required=True, type=Path)
    parser.add_argument("--exact-audit", required=True, type=Path)
    parser.add_argument("--contact-audit", required=True, type=Path)
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
    with tempfile.TemporaryDirectory(prefix=".phase_i_concat-",
                                     dir=output) as temporary:
        concat = Path(temporary) / "concat.txt"
        concat.write_text("".join(
            f"file '{video.as_posix().replace(chr(39), chr(39) * 2)}'\n"
            for video in videos), encoding="utf-8")
        combined = output / "00_EVA_NONBOXING_REVERSE_GRIP_PHASE_I_ALL.mp4"
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
        (args.contact_audit, "captured_contact_audit.json"),
    ]
    for source, name in evidence:
        shutil.copy2(source, output / name)
    readme = """# EVA 非拳击／反手刀 Phase I 人工验收包

此前 Phase G 与 Phase H 候选均已人工拒绝，本包不包含旧动作。

- 01：Eyes Japan `syotei` 掌根击；不是 jab、cross、直拳或拳击组合；
- 02：Eyes Japan 单臂 back-knuckle 身体发力，绑定 Tiger 右手反握刀；
- 反手刀骨全程为 authored Euler `[90, 0, 12]`，刀刃沿右前臂向下/向后；
- 刀柄位置全程固定 `[-0.666, 3.507, 4.638]`；
- 骨盆、双腿与支撑脚仍来自完整真人动捕，没有锁死下半身；
- 正式游戏未替换，自动门禁不能视觉批准。

右下角红色 `动作号-帧号` 只表示时间顺序，不是模型、贴图、UI、骨骼或关节标记。请分别判断掌击是否仍像拳击，以及刀是否从准备到回收始终明显反握。
"""
    readme_path = output / "README_人工验收.md"
    readme_path.write_text(readme, encoding="utf-8")
    files = videos + [combined, readme_path] + [
        output / name for _, name in evidence
    ]
    manifest = {
        "schema": 1,
        "phase": "I",
        "result": "ELIGIBLE_FOR_HUMAN_REVIEW_ONLY",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "unarmedVocabulary": "PALM_HEEL_NOT_BOXING",
        "knifeGrip": "REVERSE_RIGHT",
        "reverseGripEulerDegrees": [90.0, 0.0, 12.0],
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
