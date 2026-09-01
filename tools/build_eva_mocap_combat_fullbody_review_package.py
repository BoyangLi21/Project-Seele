#!/usr/bin/env python3
"""Render and package the Phase-H captured-full-body combat review."""

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
    "eva_mocap_combat_fullbody_manual_review_phase_h")
CLIPS = [
    ("fullbody_unarmed_left", "全身动捕徒手左击"),
    ("fullbody_unarmed_right", "全身动捕徒手右击"),
    ("fullbody_knife_a", "全身动捕粒子刀 A"),
    ("fullbody_knife_b", "全身动捕粒子刀 B"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--motion-db", required=True, type=Path)
    parser.add_argument("--constraint-report", required=True, type=Path)
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
    with tempfile.TemporaryDirectory(prefix=".phase_h_concat-",
                                     dir=output) as temporary:
        concat = Path(temporary) / "concat.txt"
        concat.write_text("".join(
            f"file '{video.as_posix().replace(chr(39), chr(39) * 2)}'\n"
            for video in videos), encoding="utf-8")
        combined = output / "00_EVA_MOCAP_COMBAT_PHASE_H_FULLBODY_ALL.mp4"
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
        (args.exact_audit, "exact_tiger_3d_audit.json"),
        (args.contact_audit, "captured_contact_audit.json"),
    ]
    for source, name in evidence:
        shutil.copy2(source, output / name)
    readme = """# EVA 全身真人动捕战斗 Phase H 人工验收包

旧 Phase-G 四条已经全部人工拒绝，本包不包含任何旧候选。

- 01/02：Bandai Namco 专业演员的完整左/右拳击片段；
- 03/04：Bandai Namco 专业演员的完整 slash episode；
- 骨盆、双腿、支撑脚、COM、躯干和手臂都来自同一段全身捕捉；
- 没有锁死下半身，没有逐骨复制人体 Euler 轴；
- 26 个可见手指仍使用连续原生拇指的静态握姿；
- 正式游戏动作未替换，自动门禁不能视觉批准。

部分动作包含真实冲步。当前只在隔离预览中显示；若未来人工接受并晋升，冲步必须由服务端 root-motion 推进实体，禁止仅移动渲染骨。

右下角红色 `动作号-帧号` 只表示时间先后，不是模型、贴图、UI、骨骼或关节标记。请直接引用如 `03-041` 反馈。

请重点判断：支撑脚与骨盆是否形成完整发力链、动作是否仍像普通人而不像 EVA、刀轨迹和重量、握持、轮廓、回收，以及是否存在你一眼就能看到的模型错误。四条必须逐条人工接受或拒绝。
"""
    readme_path = output / "README_人工验收.md"
    readme_path.write_text(readme, encoding="utf-8")
    files = videos + [combined, readme_path] + [
        output / name for _, name in evidence
    ]
    manifest = {
        "schema": 1,
        "phase": "H",
        "result": "ELIGIBLE_FOR_HUMAN_REVIEW_ONLY",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "supportMode": "CAPTURED_FULL_BODY",
        "rootAuthority": (
            "REVIEW_LOCAL_ONLY_LIVE_REQUIRES_SERVER_ROOT_MOTION"),
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
