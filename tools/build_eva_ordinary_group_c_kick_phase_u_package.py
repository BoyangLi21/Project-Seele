#!/usr/bin/env python3
"""Render the selected 2x group C and Phase-U kick review package."""

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
    run,
)


REPO = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPO / (
    "artifacts/motion_research/eva_ordinary_group_c_kick_phase_u_review"
)
ITEMS = (
    {
        "clip": "ordinary_group_c",
        "label": "已选普通攻击 C（2.0× 速度确认）",
        "source": "ordinary",
        "frame_step": 4,
    },
    {
        "clip": "kick_group_side_left",
        "label": "踹击 K1：左侧踹",
        "source": "kick",
        "frame_step": 2,
    },
    {
        "clip": "kick_group_front_right",
        "label": "踹击 K2：右前踹",
        "source": "kick",
        "frame_step": 2,
    },
    {
        "clip": "kick_group_snap_right",
        "label": "踹击 K3：右弹踢",
        "source": "kick",
        "frame_step": 2,
    },
)


def render_view(blender: Path, blend: Path, motion_db: Path,
                clip: str, view: str, root: Path, frame_step: int) -> None:
    output = root / clip / f"{view}.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    run([
        str(blender), str(blend), "--background", "--python",
        str(REPO / "tools/render_eva_motion_lab_review.py"), "--",
        "--motion-db", str(motion_db), "--clip", clip,
        "--output", str(output), "--fps", "30",
        "--frame-step", str(frame_step), "--width", "640",
        "--height", "360", "--view", view,
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ordinary-blend", required=True, type=Path)
    parser.add_argument("--ordinary-db", required=True, type=Path)
    parser.add_argument("--ordinary-live-db", required=True, type=Path)
    parser.add_argument("--ordinary-runtime-gate", required=True, type=Path)
    parser.add_argument("--kick-blend", required=True, type=Path)
    parser.add_argument("--kick-db", required=True, type=Path)
    parser.add_argument("--kick-manifest", required=True, type=Path)
    parser.add_argument("--kick-source-ranking", required=True, type=Path)
    parser.add_argument("--kick-build-gate", required=True, type=Path)
    parser.add_argument("--kick-support-gate", required=True, type=Path)
    parser.add_argument("--kick-exact-audit", required=True, type=Path)
    parser.add_argument("--kick-generic-audit", required=True, type=Path)
    parser.add_argument("--blender", type=Path, default=DEFAULT_BLENDER)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    batch = datetime.now().strftime("%Y%m%d-%H%M%S")
    output = (args.output.resolve() if args.output else
              (DEFAULT_OUTPUT / batch).resolve())
    output.mkdir(parents=True, exist_ok=True)
    render_root = output / "render"
    sources = {
        "ordinary": (args.ordinary_blend.resolve(),
                     args.ordinary_db.resolve()),
        "kick": (args.kick_blend.resolve(), args.kick_db.resolve()),
    }
    jobs = [(item, view) for item in ITEMS for view, _ in VIEWS]
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        for item, view in jobs:
            blend, database = sources[item["source"]]
            futures.append(executor.submit(
                render_view, args.blender.resolve(), blend, database,
                item["clip"], view, render_root, item["frame_step"],
            ))
        for future in futures:
            future.result()

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required")
    videos = []
    counts = {}
    panel_roots = []
    for order, item in enumerate(ITEMS, 1):
        panels, count = make_panels(
            render_root, item["clip"], item["label"], order, output
        )
        panel_roots.append(panels)
        video = output / f"{order:02d}_{item['clip']}.mp4"
        encode(ffmpeg, panels, video)
        videos.append(video)
        counts[item["clip"]] = count
    with tempfile.TemporaryDirectory(prefix=".phase_u_concat-",
                                     dir=output) as temporary:
        concat = Path(temporary) / "concat.txt"
        concat.write_text("".join(
            f"file '{video.as_posix().replace(chr(39), chr(39) * 2)}'\n"
            for video in videos
        ), encoding="utf-8")
        combined = output / "00_EVA_GROUP_C_2X_AND_KICK_PHASE_U_ALL.mp4"
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

    evidence = (
        (args.ordinary_live_db, "ordinary_group_c_live_resource.json"),
        (args.ordinary_runtime_gate, "ordinary_group_c_runtime_gate.json"),
        (args.kick_db, "kick_review_resource.json"),
        (args.kick_manifest, "kick_selection_definition.json"),
        (args.kick_source_ranking, "kick_source_ranking.json"),
        (args.kick_build_gate, "kick_build_gate.json"),
        (args.kick_support_gate, "kick_support_root_gate.json"),
        (args.kick_exact_audit, "kick_exact_tiger_fullbody_audit.json"),
        (args.kick_generic_audit, "kick_exact_tiger_generic_audit.json"),
    )
    for source, name in evidence:
        shutil.copy2(source, output / name)

    readme = """# EVA 普通攻击 C 2.0×／踹击 Phase U 人工验收包

`01` 是已经由你选中的普通攻击第三组，只用于确认按要求提升到 `2.0×` 后的
节奏；正式左键已使用同一批逐帧姿势，三段之间没有站姿重置。

`02–04` 是新找的免费真人 Karate 捕捉踹击组，来源均为 G1 Moves／MOVIN
TRACIN（CC BY 4.0）：左侧踹、右前踹、右弹踢。它们没有接入正式游戏，仍需
你从三条中选择、组合或全部拒绝。自动审计只证明模型没有穿地、支撑脚漂移、
反膝和断链等结构错误，不代表动作已经获得视觉批准。

右下红色编号格式为 `动作号-帧号`：数字只表示视频里的先后顺序，便于反馈
例如 `03-018`；它不是模型、贴图、UI、骨骼、命中点或关节标记。
"""
    readme_path = output / "README_人工验收.md"
    readme_path.write_text(readme, encoding="utf-8")
    files = videos + [combined, readme_path] + [
        output / name for _, name in evidence
    ]
    manifest = {
        "schema": 1,
        "phase": "U",
        "result": "KICK_GROUP_ELIGIBLE_FOR_HUMAN_REVIEW_ONLY",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "ordinaryAttack": {
            "selected": "ordinary_group_c",
            "playbackSpeedMultiplier": 2.0,
            "liveGameplayChanged": True,
            "renderFrameStepAt60Hz": 4,
        },
        "kick": {
            "source": "G1 Moves MOVIN TRACIN",
            "license": "CC BY 4.0",
            "liveGameplayChanged": False,
            "humanReviewRequired": True,
        },
        "fps": 30,
        "resolution": [1920, 360],
        "views": [view for view, _ in VIEWS],
        "clips": [{
            "order": order,
            "name": item["clip"],
            "label": item["label"],
            "frames": counts[item["clip"]],
            "frameStep": item["frame_step"],
        } for order, item in enumerate(ITEMS, 1)],
        "redNumberMeaning": (
            "ACTION_ORDER-FRAME_ORDER; chronological locator only; not "
            "geometry, texture, UI, bone, hit, or joint marker"
        ),
        "kickVisuallyApproved": False,
        "files": [{
            "name": path.name,
            "bytes": path.stat().st_size,
            "sha256": digest(path),
        } for path in files],
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    archive = output.parent / f"{output.name}.zip"
    if archive.exists():
        archive.unlink()
    shutil.make_archive(
        str(archive.with_suffix("")), "zip",
        root_dir=output.parent, base_dir=output.name,
    )
    print(json.dumps({
        "output": str(output),
        "combined": str(combined),
        "archive": str(archive),
        "frames": counts,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
