#!/usr/bin/env python3
"""Render and package the isolated Phase-O EVA forearm-impact candidate."""

from __future__ import annotations

import argparse
import json
import shutil
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
)


REPO = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPO / (
    "artifacts/motion_research/eva_mocap_ordinary_phase_o_manual_review")
CLIP = "eva_forearm_lariat"
LABEL = "新普通攻击：肩胯带动的右前臂横砸"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--motion-db", required=True, type=Path)
    parser.add_argument("--candidate-manifest", required=True, type=Path)
    parser.add_argument("--constraint-report", required=True, type=Path)
    parser.add_argument("--stabilization-report", required=True, type=Path)
    parser.add_argument("--exact-audit", required=True, type=Path)
    parser.add_argument("--generic-exact-audit", required=True, type=Path)
    parser.add_argument("--impact-ranking", required=True, type=Path)
    parser.add_argument("--source-metadata", required=True, type=Path)
    parser.add_argument("--source-window", required=True, type=Path)
    parser.add_argument("--source-license", required=True, type=Path)
    parser.add_argument("--blender", type=Path, default=DEFAULT_BLENDER)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    batch = datetime.now().strftime("%Y%m%d-%H%M%S")
    output = (args.output.resolve() if args.output else
              (DEFAULT_OUTPUT / batch).resolve())
    output.mkdir(parents=True, exist_ok=True)
    render_root = output / "render"
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(
            render_view,
            args.blender.resolve(),
            args.blend.resolve(),
            args.motion_db.resolve(),
            CLIP,
            view,
            render_root,
        ) for view, _ in VIEWS]
        for future in futures:
            future.result()

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required")
    panels, frame_count = make_panels(
        render_root, CLIP, LABEL, 1, output)
    candidate_video = output / f"01_{CLIP}.mp4"
    encode(ffmpeg, panels, candidate_video)
    combined = output / "00_EVA_ORDINARY_PHASE_O.mp4"
    shutil.copy2(candidate_video, combined)
    shutil.rmtree(panels)
    if render_root.parent != output:
        raise RuntimeError("refusing to remove render frames outside package")
    shutil.rmtree(render_root)

    evidence = [
        (args.candidate_manifest, "candidate_definition.json"),
        (args.constraint_report, "constraint_gate.json"),
        (args.stabilization_report, "root_contact_stabilization.json"),
        (args.exact_audit, "exact_tiger_fullbody_audit.json"),
        (args.generic_exact_audit, "exact_tiger_generic_audit.json"),
        (args.impact_ranking, "captured_impact_ranking.json"),
        (args.source_metadata, "source_capture_metadata.json"),
        (args.source_window, "source_window.json"),
        (args.source_license, "SOURCE_README.txt"),
    ]
    for source, name in evidence:
        shutil.copy2(source, output / name)

    readme = """# EVA 普通攻击 Phase O 人工验收包

本包只包含一条全新的普通攻击。Phase M 已通过的粒子刀仍锁定为左键正手、
右键短反手，本阶段没有修改或重新渲染它们。

- 来源是 Haley Tuffles 通过 iPiSoft 实拍、在 Blender 清理的免费真人动捕；
- 取完整 `ArmsLariat` 的有效帧 13--40，做右前臂横砸；
- 后脚/骨盆先驱动，胸肩延迟，右臂高速横扫，支撑与挥后制动保留；
- 不是拳击、掌击、爪击、双臂下砸或纯向前冲刺；
- 最终 70 个 60 FPS 采样，时长 1.15 秒；
- 结束保持真人捕捉的随动姿势，没有插入站姿重置。正式运行时若晋升，
  下一击或移动必须从该结束姿势接续；
- 自动门禁只能给出 ELIGIBLE_FOR_HUMAN_REVIEW_ONLY，不能批准 EVA 审美。

源筛选指标：主臂峰值约 6.63 H/s，峰后速度下降约 84.7%，骨盆与胸肩角速度
合计约 648°/s，接触窗口存在脚底支撑。右下红色 `01-帧号` 仅表示时间先后，
不是模型、骨骼或命中标记。本轮只需判断这一条是否终于具有 EVA 普通攻击的
冲击与重量。
"""
    readme_path = output / "README_人工验收.md"
    readme_path.write_text(readme, encoding="utf-8")

    files = [candidate_video, combined, readme_path] + [
        output / name for _, name in evidence
    ]
    manifest = {
        "schema": 1,
        "phase": "O",
        "result": "ELIGIBLE_FOR_HUMAN_REVIEW_ONLY",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "liveGameplayChanged": False,
        "endingPosePolicy": "PRESERVE_CAPTURED_FOLLOW_THROUGH",
        "knifeBindingsLocked": {
            "leftClick": "FORWARD_STAB_TWIST",
            "rightClick": "SHORT_REVERSE_STAB_TWIST",
        },
        "knifeFramesSha256": {
            "leftClick": (
                "414427cf77b59c25912f9fb1821dfa480c5e0be14a88d4969c945e8ff64acbbb"),
            "rightClick": (
                "19e7d2a37b46574620df1d55e0ce02d6c0373c02c778740beccece6c8dfe4ae9"),
        },
        "motionDatabase": str(args.motion_db.resolve()),
        "motionDatabaseSha256": digest(args.motion_db),
        "exactBlend": str(args.blend.resolve()),
        "fps": 30,
        "resolution": [1920, 360],
        "views": [view for view, _ in VIEWS],
        "clips": [{
            "order": 1,
            "name": CLIP,
            "label": LABEL,
            "frames": frame_count,
        }],
        "redNumberMeaning": (
            "ACTION_ORDER-FRAME_ORDER; chronological locator only; not "
            "geometry, texture, UI, bone, hit, or joint marker"),
        "visuallyApproved": False,
        "files": [{
            "name": path.name,
            "bytes": path.stat().st_size,
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
        "output": str(output),
        "combined": str(combined),
        "archive": str(archive),
        "frames": frame_count,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
