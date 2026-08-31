#!/usr/bin/env python3
"""Render and package the isolated Phase-G mocap combat candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


REPO = Path(__file__).resolve().parent.parent
DEFAULT_BLENDER = REPO / (
    "external-assets/tools/blender-3.6.0-portable/"
    "blender-3.6.0-windows-x64/blender.exe")
DEFAULT_OUTPUT = REPO / (
    "artifacts/motion_research/"
    "eva_mocap_combat_manual_review_phase_g")
CLIPS = [
    ("mocap_unarmed_left", "真人动捕徒手左击"),
    ("mocap_unarmed_right", "真人动捕徒手右击"),
    ("mocap_knife_light", "真人动捕粒子刀轻击"),
    ("mocap_knife_heavy", "真人动捕粒子刀重击"),
]
VIEWS = [
    ("front", "FRONT / 正面"),
    ("side", "SIDE / 侧面"),
    ("back", "BACK / 背面"),
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (Path("C:/Windows/Fonts/msyhbd.ttc"),
                 Path("C:/Windows/Fonts/msyh.ttc"),
                 Path("C:/Windows/Fonts/arialbd.ttf")):
        if path.is_file():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def run(command: list[str]) -> str:
    result = subprocess.run(
        command, cwd=REPO, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    if result.returncode != 0:
        raise RuntimeError("command failed:\n" + " ".join(command)
                           + "\n" + result.stdout[-12000:])
    return result.stdout


def render_view(blender: Path, blend: Path, motion_db: Path,
                clip: str, view: str, root: Path) -> None:
    output = root / clip / f"{view}.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    run([
        str(blender), str(blend), "--background", "--python",
        str(REPO / "tools/render_eva_motion_lab_review.py"), "--",
        "--motion-db", str(motion_db), "--clip", clip,
        "--output", str(output), "--fps", "30", "--frame-step", "2",
        "--width", "640", "--height", "360", "--view", view,
    ])


def overlay_label(draw: ImageDraw.ImageDraw, xy: tuple[int, int],
                  value: str, selected_font, anchor: str = "la") -> None:
    bounds = draw.textbbox(xy, value, font=selected_font, anchor=anchor,
                           stroke_width=1)
    padding = 7
    draw.rounded_rectangle((bounds[0] - padding, bounds[1] - padding,
                            bounds[2] + padding, bounds[3] + padding),
                           radius=6, fill=(0, 0, 0, 176))
    draw.text(xy, value, font=selected_font, anchor=anchor,
              fill=(255, 255, 255), stroke_width=1,
              stroke_fill=(0, 0, 0))


def make_panels(render_root: Path, clip: str, label: str, order: int,
                output: Path) -> tuple[Path, int]:
    view_frames = []
    for view, _ in VIEWS:
        directory = render_root / clip / f"{view}_frames"
        frames = sorted(directory.glob("frame_*.png"))
        if not frames:
            raise RuntimeError(f"render produced no frames: {directory}")
        view_frames.append(frames)
    count = min(len(frames) for frames in view_frames)
    frame_root = output / f".{clip}_panels"
    frame_root.mkdir(parents=True, exist_ok=True)
    title_font = font(24)
    view_font = font(19)
    number_font = font(38)
    for index in range(count):
        panel = Image.new("RGB", (1920, 360), (0, 0, 0))
        for column, frames in enumerate(view_frames):
            with Image.open(frames[index]) as opened:
                tile = opened.convert("RGB").resize(
                    (640, 360), Image.Resampling.LANCZOS)
            panel.paste(tile, (column * 640, 0))
        draw = ImageDraw.Draw(panel, "RGBA")
        overlay_label(draw, (18, 18), f"{order:02d}  {label}", title_font)
        for column, (_, view_label) in enumerate(VIEWS):
            overlay_label(draw, (column * 640 + 320, 18), view_label,
                          view_font, anchor="ma")
        locator = f"{order:02d}-{index + 1:03d}"
        draw.text((panel.width - 18, panel.height - 14), locator,
                  font=number_font, anchor="rs", fill=(255, 28, 28),
                  stroke_width=4, stroke_fill=(0, 0, 0))
        panel.save(frame_root / f"frame_{index + 1:04d}.png",
                   format="PNG", compress_level=2)
    return frame_root, count


def encode(ffmpeg: str, frames: Path, output: Path) -> None:
    run([
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-framerate", "30", "-i", str(frames / "frame_%04d.png"),
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output),
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blend", required=True, type=Path)
    parser.add_argument("--motion-db", required=True, type=Path)
    parser.add_argument("--constraint-report", required=True, type=Path)
    parser.add_argument("--exact-audit", required=True, type=Path)
    parser.add_argument("--blender", type=Path, default=DEFAULT_BLENDER)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--skip-render", action="store_true")
    args = parser.parse_args()
    batch = datetime.now().strftime("%Y%m%d-%H%M%S")
    output = (args.output.resolve() if args.output else
              (DEFAULT_OUTPUT / batch).resolve())
    output.mkdir(parents=True, exist_ok=True)
    render_root = output / "render"
    if not args.skip_render:
        jobs = [
            (clip, view) for clip, _ in CLIPS for view, _ in VIEWS
        ]
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
    with tempfile.TemporaryDirectory(prefix=".phase_g_concat-",
                                     dir=output) as temporary:
        concat = Path(temporary) / "concat.txt"
        concat.write_text("".join(
            f"file '{video.as_posix().replace(chr(39), chr(39) * 2)}'\n"
            for video in videos), encoding="utf-8")
        combined = output / "00_EVA_MOCAP_COMBAT_PHASE_G_ALL.mp4"
        run([
            ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(concat),
            "-c", "copy", "-movflags", "+faststart", str(combined),
        ])
    for panels in panel_roots:
        shutil.rmtree(panels)
    if render_root.parent != output:
        raise RuntimeError("refusing to remove render frames outside package")
    if render_root.is_dir():
        shutil.rmtree(render_root)
    shutil.copy2(args.constraint_report, output / "constraint_gate.json")
    shutil.copy2(args.exact_audit, output / "exact_tiger_3d_audit.json")
    readme = """# EVA 真人动捕战斗 Phase G 人工验收包

这四条都是隔离候选，正式游戏的徒手和粒子刀动作没有被替换。

- 01/02：CMU Subject 144 的真人左拳、右拳序列；
- 03/04：CMU Subject 02 trial 08 的真人 swordplay 轻击、重击；
- 真人数据负责胸廓、肩臂、头部时序和主手轨迹；
- 已人工通过的正式 idle 负责唯一骨盆/双腿支撑姿势；
- Tiger 关节幅度、双脚支撑、连续原生拇指和静态握姿由约束层负责；
- 自动门禁只能给出 ELIGIBLE_FOR_HUMAN_REVIEW_ONLY。

右下角红色 `动作号-帧号` 只表示先后顺序：数字越小越早。它不是模型几何、贴图、游戏 UI、骨骼或关节标记。反馈时请引用例如 `03-018`。

请重点判断：上身是否仍过僵、出手前后是否有清晰意图、双臂轮廓是否自然、刀是否始终被握住、刀轨迹是否可信、手指是否外翻、首尾是否无闪回，以及整体是否像 EVA。接受候选不等于允许自动替换 live；晋升仍需你的明确指令。
"""
    (output / "README_人工验收.md").write_text(
        readme, encoding="utf-8")
    files = videos + [combined, output / "constraint_gate.json",
                      output / "exact_tiger_3d_audit.json",
                      output / "README_人工验收.md"]
    manifest = {
        "schema": 1,
        "phase": "G",
        "result": "ELIGIBLE_FOR_HUMAN_REVIEW_ONLY",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "liveGameplayChanged": False,
        "motionDatabase": str(args.motion_db.resolve()),
        "motionDatabaseSha256": digest(args.motion_db),
        "exactBlend": str(args.blend.resolve()),
        "fps": 30,
        "resolution": [1920, 360],
        "views": [view for view, _ in VIEWS],
        "clips": [{"order": order, "name": clip, "label": label,
                   "frames": counts[clip]}
                  for order, (clip, label) in enumerate(CLIPS, 1)],
        "redNumberMeaning": (
            "ACTION_ORDER-FRAME_ORDER; chronological locator only; not "
            "geometry, texture, UI, bone, or joint marker"),
        "visuallyApproved": False,
        "files": [{"name": path.name, "bytes": path.stat().st_size,
                   "sha256": digest(path)} for path in files],
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
