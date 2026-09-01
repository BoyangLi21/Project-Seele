#!/usr/bin/env python3
"""Render and package the Phase-P buffered ordinary-combo review."""

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
    "artifacts/motion_research/eva_mocap_ordinary_combo_phase_p_manual_review")
CLIP = "ordinary_combo_hold_demo"
LABEL = "持续左键两轮：右前臂 → 左前臂 → 重横砸"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--motion-db", required=True, type=Path)
    parser.add_argument("--stage-manifest", required=True, type=Path)
    parser.add_argument("--stage-gate", required=True, type=Path)
    parser.add_argument("--compose-gate", required=True, type=Path)
    parser.add_argument("--stabilization-report", required=True, type=Path)
    parser.add_argument("--exact-audit", required=True, type=Path)
    parser.add_argument("--generic-exact-audit", required=True, type=Path)
    parser.add_argument("--impact-ranking", required=True, type=Path)
    parser.add_argument("--mirror-report", required=True, type=Path)
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
    video = output / "00_EVA_ORDINARY_COMBO_PHASE_P.mp4"
    encode(ffmpeg, panels, video)
    shutil.rmtree(panels)
    if render_root.parent != output:
        raise RuntimeError("refusing to remove render frames outside package")
    shutil.rmtree(render_root)

    evidence = [
        (args.stage_manifest, "stage_definition.json"),
        (args.stage_gate, "stage_constraint_gate.json"),
        (args.compose_gate, "buffered_combo_compose_gate.json"),
        (args.stabilization_report, "root_contact_stabilization.json"),
        (args.exact_audit, "exact_tiger_fullbody_audit.json"),
        (args.generic_exact_audit, "exact_tiger_generic_audit.json"),
        (args.impact_ranking, "captured_impact_ranking.json"),
        (args.mirror_report, "left_stage_mirror_report.json"),
        (args.source_license, "SOURCE_README.txt"),
    ]
    for source, name in evidence:
        shutil.copy2(source, output / name)

    readme = """# EVA 普通攻击 Phase P 持续左键连击验收包

视频把“持续输入左键”演示为两轮连续循环：

1. 右前臂短拨砸；
2. 左前臂镜像短拨砸；
3. 右前臂重横砸；
4. 直接从第三击随动姿势进入下一轮第一击。

三击均来自 Haley Tuffles 的 iPiSoft 真人动捕；左击是实拍右击的矢状面镜像，
不是程序生成动作。每个阶段只在输入缓冲中收到下一次左键时推进；视频为了验收
连续性而假定输入始终存在，并不代表正式游戏会一键自动播完六击。松开左键时，
正式状态机必须从当前姿势自然回收，不得回站姿闪一下。

- 阶段间使用 12 帧姿态惯性消除，不插入站姿；
- 最大阶段边界旋转步长约 5.69°，全片最大约 18.64°；
- 精确 Tiger 全身与通用 3D 门禁均为 1 clip / 0 failures；
- 正式游戏尚未替换，粒子刀左键正手／右键反手继续保持锁定。

右下红色 `01-帧号` 只表示时间顺序。请重点看第三击结束进入第二轮第一击时，
是否仍像同一场连续打斗，以及三击整体是否具有 EVA 的冲击、重量和危险感。
"""
    readme_path = output / "README_人工验收.md"
    readme_path.write_text(readme, encoding="utf-8")

    files = [video, readme_path] + [output / name for _, name in evidence]
    manifest = {
        "schema": 1,
        "phase": "P",
        "result": "ELIGIBLE_FOR_HUMAN_REVIEW_ONLY",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "liveGameplayChanged": False,
        "inputContract": "BUFFERED_REPEATED_LEFT_CLICK",
        "standResetBetweenStages": False,
        "reviewCycles": 2,
        "stageOrder": [
            "RIGHT_FOREARM_BACKHAND",
            "LEFT_FOREARM_BACKHAND_MIRRORED_CAPTURE",
            "RIGHT_FOREARM_LARIAT_HEAVY",
        ],
        "knifeBindingsLocked": {
            "leftClick": "FORWARD_STAB_TWIST",
            "rightClick": "SHORT_REVERSE_STAB_TWIST",
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
        "video": str(video),
        "archive": str(archive),
        "frames": frame_count,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
