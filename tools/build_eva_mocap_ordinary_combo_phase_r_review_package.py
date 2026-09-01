#!/usr/bin/env python3
"""Render and package the Phase-R overhand EVA ordinary combo review."""

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
    "artifacts/motion_research/eva_mocap_ordinary_combo_phase_r_manual_review")
CLIP = "ordinary_combo_hold_demo"
LABEL = "EVA 普通连击：右过顶砸 → 左过顶砸 → 右重砸（红色仅命中反应）"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--attacker-db", required=True, type=Path)
    parser.add_argument("--target-db", required=True, type=Path)
    parser.add_argument("--attacker-manifest", required=True, type=Path)
    parser.add_argument("--target-manifest", required=True, type=Path)
    parser.add_argument("--attacker-stage-gate", required=True, type=Path)
    parser.add_argument("--target-stage-gate", required=True, type=Path)
    parser.add_argument("--compose-gate", required=True, type=Path)
    parser.add_argument("--target-timeline-gate", required=True, type=Path)
    parser.add_argument("--attacker-stabilization", required=True, type=Path)
    parser.add_argument("--target-stabilization", required=True, type=Path)
    parser.add_argument("--attacker-exact-audit", required=True, type=Path)
    parser.add_argument("--target-exact-audit", required=True, type=Path)
    parser.add_argument("--paired-exact-audit", required=True, type=Path)
    parser.add_argument("--impact-ranking", required=True, type=Path)
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
            args.attacker_db.resolve(),
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
    video = output / "00_EVA_ORDINARY_COMBO_PHASE_R.mp4"
    encode(ffmpeg, panels, video)
    shutil.rmtree(panels)
    if render_root.parent != output:
        raise RuntimeError("refusing to remove render frames outside package")
    shutil.rmtree(render_root)

    evidence = [
        (args.attacker_manifest, "attacker_stage_definition.json"),
        (args.target_manifest, "target_reaction_definition.json"),
        (args.attacker_stage_gate, "attacker_stage_gate.json"),
        (args.target_stage_gate, "target_stage_gate.json"),
        (args.compose_gate, "buffered_combo_compose_gate.json"),
        (args.target_timeline_gate, "target_reaction_timeline_gate.json"),
        (args.attacker_stabilization,
         "attacker_root_contact_stabilization.json"),
        (args.target_stabilization,
         "target_root_contact_stabilization.json"),
        (args.attacker_exact_audit, "attacker_exact_tiger_audit.json"),
        (args.target_exact_audit, "target_exact_tiger_audit.json"),
        (args.paired_exact_audit, "paired_exact_hit_audit.json"),
        (args.impact_ranking, "source_impact_ranking.json"),
    ]
    for source, name in evidence:
        shutil.copy2(source, output / name)

    readme = """# EVA 普通攻击连击 Phase R 人工验收包

Phase Q 已人工认可并锁定为命中后的推动／钳制互动，不计入普通攻击。本包只验收
新的击打本体：

1. 右单臂过顶斜砸；
2. 左侧镜像过顶斜砸；
3. 右侧更重的过顶收尾砸；
4. 持续输入后直接进入下一轮，不回站姿。

三击的全身动力链取自 Rokoko 免费体育真人动捕的棒球投手独立 takes：后脚支撑、
骨盆先转、胸肩延迟、单臂向前下方释放。它不是拳击、掌击、Lariat 或推动。
红色 Tiger 只在服务端确认的六个命中时刻播放 Haley Tuffles 真人受击／后退
反应；落空时正式游戏不得生成红色反应，也不得进入 Phase Q 钳制互动。

- 两轮 365×60 FPS，6.07 秒；
- 五个连击边界最大旋转步长不超过约 4.96°，全片最大约 15.08°；
- 攻击者、目标与双体命中精确门禁均为 0 failures；
- 六次预期命中在 Tiger 上的距离覆盖率为 100%；
- Phase Q 互动只保留为命中后的可选分支，不混进本视频作为一击；
- 正式游戏尚未替换，粒子刀左键正手／右键短反手继续锁定。

右下红色 `01-帧号` 只表示时间顺序。第二轮约从 `01-093` 开始，应重点检查
`01-085`--`01-102`：三击循环是否连续；以及六个命中附近是否真的像 EVA
用长臂和全身重量砸中大型目标，而不是人在投球或普通格斗。
"""
    readme_path = output / "README_人工验收.md"
    readme_path.write_text(readme, encoding="utf-8")

    files = [video, readme_path] + [output / name for _, name in evidence]
    manifest = {
        "schema": 1,
        "phase": "R",
        "result": "ELIGIBLE_FOR_HUMAN_REVIEW_ONLY",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "liveGameplayChanged": False,
        "inputContract": "BUFFERED_REPEATED_LEFT_CLICK_STRIKE_COMBO",
        "targetReactionTrigger": "SERVER_CONFIRMED_HIT_ONLY",
        "phaseQInteractionStatus": "LOCKED_OPTIONAL_POST_HIT_BRANCH",
        "targetProxy": "SOLID_RED_TIGER_NOT_FINAL_ENEMY_ART",
        "standResetBetweenStages": False,
        "reviewCycles": 2,
        "stageOrder": [
            "RIGHT_OVERHAND_DIAGONAL_STRIKE",
            "LEFT_OVERHAND_DIAGONAL_STRIKE_MIRRORED_CAPTURE",
            "RIGHT_HEAVY_OVERHAND_FINISHER",
        ],
        "knifeBindingsLocked": {
            "leftClick": "FORWARD_STAB_TWIST",
            "rightClick": "SHORT_REVERSE_STAB_TWIST",
        },
        "attackerDatabase": str(args.attacker_db.resolve()),
        "attackerDatabaseSha256": digest(args.attacker_db),
        "targetDatabase": str(args.target_db.resolve()),
        "targetDatabaseSha256": digest(args.target_db),
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
