#!/usr/bin/env python3
"""Render and package four Phase-T ordinary-combo groups for selection."""

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
    "artifacts/motion_research/eva_mocap_ordinary_combo_phase_t_selection")
CLIPS = [
    ("ordinary_group_a", "A：右下砸 → 左横扫 → 右前冲击"),
    ("ordinary_group_b", "B：Power Burst 左右爆发组"),
    ("ordinary_group_c", "C：Double Strike 双击＋下砸收尾"),
    ("ordinary_group_d", "D：Attack Karate 前压＋爆发＋下击"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--motion-db", required=True, type=Path)
    parser.add_argument("--selection-manifest", required=True, type=Path)
    parser.add_argument("--stage-gate", required=True, type=Path)
    parser.add_argument("--compose-gate", action="append", required=True,
                        type=Path)
    parser.add_argument("--stabilization-report", required=True, type=Path)
    parser.add_argument("--exact-audit", required=True, type=Path)
    parser.add_argument("--generic-exact-audit", required=True, type=Path)
    parser.add_argument("--source-ranking", action="append", required=True,
                        type=Path)
    parser.add_argument("--blender", type=Path, default=DEFAULT_BLENDER)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if len(args.compose_gate) != len(CLIPS):
        raise RuntimeError("one compose gate is required for every group")

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
    with tempfile.TemporaryDirectory(prefix=".phase_t_concat-",
                                     dir=output) as temporary:
        concat = Path(temporary) / "concat.txt"
        concat.write_text("".join(
            f"file '{video.as_posix().replace(chr(39), chr(39) * 2)}'\n"
            for video in videos), encoding="utf-8")
        combined = output / "00_EVA_ORDINARY_PHASE_T_ALL.mp4"
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
        (args.selection_manifest, "selection_definition.json"),
        (args.stage_gate, "stage_constraint_gate.json"),
        (args.stabilization_report, "root_contact_stabilization.json"),
        (args.exact_audit, "exact_tiger_fullbody_audit.json"),
        (args.generic_exact_audit, "exact_tiger_generic_audit.json"),
    ]
    evidence.extend((path, f"group_{chr(65 + index)}_compose_gate.json")
                    for index, path in enumerate(args.compose_gate))
    evidence.extend((path, f"source_ranking_{index + 1:02d}.json")
                    for index, path in enumerate(args.source_ranking))
    for source, name in evidence:
        shutil.copy2(source, output / name)

    readme = """# EVA 普通攻击 Phase T 四组选片包

本包只显示 Unit-01 攻击本体，不显示红色目标或 Phase Q 互动，避免同一受击效果
干扰四组之间的公平比较。选中一组后，再接已认可的命中反应／推移分支。

- A：混合三条原生攻击，右下砸、左横扫、右前冲击；
- B：同一 Power Burst 系列，节奏最快、左右爆发最集中；
- C：Double Strike 系列，第二击更长，第三击短促下砸；
- D：Attack Karate 系列，前压距离最大，随后左爆发和右下击。

四组全部来自 G1 Moves 的 MOVIN TRACIN 真人捕捉，CC BY 4.0；没有体育动作、
拳击、掌击、Lariat 或推动。每组都展示两轮持续左键，阶段间和循环边界不经过
站姿。自动门禁只能排除结构错误，不能替你判断哪组像 EVA。

右下红色编号格式仍是 `组号-帧号`。请回复：`选 A/B/C/D`、组合修改意见，
或`全部不行`。粒子刀左键正手／右键短反手保持锁定；正式游戏未替换。
"""
    readme_path = output / "README_人工选片.md"
    readme_path.write_text(readme, encoding="utf-8")

    files = videos + [combined, readme_path] + [
        output / name for _, name in evidence
    ]
    manifest = {
        "schema": 1,
        "phase": "T",
        "result": "FOUR_GROUPS_ELIGIBLE_FOR_HUMAN_SELECTION_ONLY",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "liveGameplayChanged": False,
        "targetReactionShown": False,
        "targetReactionReason": "isolate attacker motion for fair selection",
        "phaseQInteractionStatus": "LOCKED_OPTIONAL_POST_HIT_BRANCH",
        "motionDatabase": str(args.motion_db.resolve()),
        "motionDatabaseSha256": digest(args.motion_db),
        "exactBlend": str(args.blend.resolve()),
        "fps": 30,
        "resolution": [1920, 360],
        "views": [view for view, _ in VIEWS],
        "groups": [{
            "order": order,
            "id": chr(64 + order),
            "name": clip,
            "label": label,
            "frames": counts[clip],
            "selected": None,
        } for order, (clip, label) in enumerate(CLIPS, 1)],
        "redNumberMeaning": (
            "GROUP_ORDER-FRAME_ORDER; chronological locator only; not "
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
        "frames": counts,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
