#!/usr/bin/env python3
"""Render and package the Phase-Q target-contact EVA combo review."""

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
    "artifacts/motion_research/eva_mocap_contact_combo_phase_q_manual_review")
CLIP = "eva_contact_combo_hold_demo"
LABEL = "EVA 接触连击：压入 → 双肩钳制 → 推移（红色为目标代理）"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--attacker-db", required=True, type=Path)
    parser.add_argument("--target-db", required=True, type=Path)
    parser.add_argument("--stage-manifest", required=True, type=Path)
    parser.add_argument("--stage-gate", required=True, type=Path)
    parser.add_argument("--compose-gate", required=True, type=Path)
    parser.add_argument("--attacker-stabilization", required=True, type=Path)
    parser.add_argument("--target-stabilization", required=True, type=Path)
    parser.add_argument("--attacker-exact-audit", required=True, type=Path)
    parser.add_argument("--target-exact-audit", required=True, type=Path)
    parser.add_argument("--paired-exact-audit", required=True, type=Path)
    parser.add_argument("--paired-source-audit", required=True, type=Path)
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
    video = output / "00_EVA_CONTACT_COMBO_PHASE_Q.mp4"
    encode(ffmpeg, panels, video)
    shutil.rmtree(panels)
    if render_root.parent != output:
        raise RuntimeError("refusing to remove render frames outside package")
    shutil.rmtree(render_root)

    evidence = [
        (args.stage_manifest, "stage_definition.json"),
        (args.stage_gate, "stage_constraint_gate.json"),
        (args.compose_gate, "paired_combo_compose_gate.json"),
        (args.attacker_stabilization,
         "attacker_root_contact_stabilization.json"),
        (args.target_stabilization,
         "target_root_contact_stabilization.json"),
        (args.attacker_exact_audit, "attacker_exact_tiger_audit.json"),
        (args.target_exact_audit, "target_exact_tiger_audit.json"),
        (args.paired_exact_audit, "paired_exact_contact_audit.json"),
        (args.paired_source_audit, "paired_source_contact_audit.json"),
    ]
    for source, name in evidence:
        shutil.copy2(source, output / name)

    readme = """# EVA 普通攻击接触连击 Phase Q 人工验收包

Phase P 的单人拨砸/Lariat 已整套人工判退，本包不复用那些动作。新路线来自
CMU `22_05 + 23_05` 同步双人真人动捕：紫色 Unit-01 是攻击者，纯红色 EVA
只是目标反应代理，不是最终敌人美术。

持续左键按同一段真实接触表演分成三次提交：

1. 大步压入并建立第一次肩部接触；
2. 双手钳住肩部，身体继续驱动；
3. 第二次接触、推移与失衡随动。

视频连续展示两轮来暴露循环边界，但正式游戏每一段都必须收到新的左键缓冲才
推进；未命中目标时只能走压入刹停，不能凭空播放钳制和推移。它不再是普通人
对空气挥拳，而是目标存在时的 EVA 式近身接触链。

- 215 个 60 FPS 采样，3.57 秒；循环边界最大旋转步长攻击者约 2.91°；
- 攻击者、目标和双体精确 Tiger 审计均为 0 failures；
- 目标反应位移约 0.156 H，攻击者压入约 0.216 H；
- Tiger 手到目标肩部最小距离约 0.022 H；
- 正式游戏尚未替换，粒子刀左键正手／右键反手继续锁定。

右下红色 `01-帧号` 只表示时间顺序。第二轮约从 `01-055` 开始，应重点检查
`01-048`--`01-062`：是否仍然连续、有重量、像 EVA 与大型目标缠斗，而不是
两个普通人摔跤或两个模型无意义重叠。
"""
    readme_path = output / "README_人工验收.md"
    readme_path.write_text(readme, encoding="utf-8")

    files = [video, readme_path] + [output / name for _, name in evidence]
    manifest = {
        "schema": 1,
        "phase": "Q",
        "result": "ELIGIBLE_FOR_HUMAN_REVIEW_ONLY",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "liveGameplayChanged": False,
        "inputContract": "BUFFERED_REPEATED_LEFT_CLICK_TARGET_CONTACT_BRANCH",
        "targetRequired": True,
        "targetProxy": "SOLID_RED_TIGER_NOT_FINAL_ENEMY_ART",
        "standResetBetweenStages": False,
        "reviewCycles": 2,
        "stageOrder": [
            "BODY_ENTRY_AND_FIRST_SHOULDER_CONTACT",
            "TWO_HAND_CLAMP_AND_BODY_DRIVE",
            "SECOND_CONTACT_AND_SHOVE_FOLLOW_THROUGH",
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
