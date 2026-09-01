#!/usr/bin/env python3
"""Render and package the isolated Phase-N ordinary-attack candidate."""

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
    "artifacts/motion_research/eva_mocap_ordinary_phase_n_manual_review")
CLIP = "eva_low_shoulder_drive"
LABEL = "新普通攻击：低肩与骨盆先行的全身前冲重击"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--motion-db", required=True, type=Path)
    parser.add_argument("--candidate-manifest", required=True, type=Path)
    parser.add_argument("--constraint-report", required=True, type=Path)
    parser.add_argument("--stabilization-report", required=True, type=Path)
    parser.add_argument("--exact-audit", required=True, type=Path)
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
    combined = output / "00_EVA_ORDINARY_PHASE_N.mp4"
    shutil.copy2(candidate_video, combined)
    shutil.rmtree(panels)
    if render_root.parent != output:
        raise RuntimeError("refusing to remove render frames outside package")
    shutil.rmtree(render_root)

    evidence = [
        (args.candidate_manifest, "candidate_definition.json"),
        (args.constraint_report, "constraint_gate.json"),
        (args.stabilization_report, "root_contact_stabilization.json"),
        (args.exact_audit, "exact_tiger_3d_audit.json"),
    ]
    for source, name in evidence:
        shutil.copy2(source, output / name)

    readme = """# EVA 普通攻击 Phase N 人工验收包

本包只包含一个全新的普通攻击候选。已通过的两条粒子刀动作没有重新渲染、
没有修改：游戏目标仍是左键正手、右键反手。

- 来源：Rapa Motion 免费 Anime/Mudra 真人动捕包的 Chidori take；
- 使用源帧 352--511，保留骨盆、躯干、肩部和步伐的全身时序；
- 动作意图是低肩与骨盆先前冲，右臂最后打出；
- 不是拳击直拳、掌击、爪击，也不是双臂扑进下砸；
- 最终时长 1.85 秒；正式游戏动作尚未替换；
- 精确 Tiger 场景门禁只能给出 ELIGIBLE_FOR_HUMAN_REVIEW_ONLY，
  不能代替人眼判断是否有 EVA 的感觉。

右下红色 `01-帧号` 只表示时间先后，数字越小越早；它不是模型几何、
贴图、游戏 UI、骨骼或关节标记。此次只需判断这一条普通攻击通过或不通过。
"""
    readme_path = output / "README_人工验收.md"
    readme_path.write_text(readme, encoding="utf-8")

    files = [candidate_video, combined, readme_path] + [
        output / name for _, name in evidence
    ]
    manifest = {
        "schema": 1,
        "phase": "N",
        "result": "ELIGIBLE_FOR_HUMAN_REVIEW_ONLY",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "liveGameplayChanged": False,
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
            "geometry, texture, UI, bone, or joint marker"),
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
