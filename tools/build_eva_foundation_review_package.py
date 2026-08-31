#!/usr/bin/env python3
"""Build numbered multi-view MP4s from a passed Phase-F game capture."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from audit_eva_foundation_capture import (
    CONTRACT, REPO, audit_capture, latest_batch, load_json)


DEFAULT_ROOT = (REPO / "artifacts/motion_research/"
                "eva_foundation_manual_review_phase_f")
VIEW_LABELS = {
    "front_close": "FRONT / 正面",
    "side_close": "SIDE / 侧面",
    "back_close": "BACK / 背面",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (Path("C:/Windows/Fonts/msyhbd.ttc"),
                 Path("C:/Windows/Fonts/msyh.ttc"),
                 Path("C:/Windows/Fonts/arialbd.ttf")):
        if path.is_file():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def overlay_label(draw: ImageDraw.ImageDraw, xy: tuple[int, int],
                  text: str, selected_font, anchor: str = "la",
                  fill=(255, 255, 255)) -> None:
    bounds = draw.textbbox(xy, text, font=selected_font, anchor=anchor,
                           stroke_width=1)
    padding = 8
    draw.rounded_rectangle((bounds[0] - padding, bounds[1] - padding,
                            bounds[2] + padding, bounds[3] + padding),
                           radius=6, fill=(0, 0, 0, 176))
    draw.text(xy, text, font=selected_font, anchor=anchor, fill=fill,
              stroke_width=1, stroke_fill=(0, 0, 0))


def make_panel(batch: Path, action: dict, views: list[str], frame: int,
               output: Path) -> None:
    tiles = []
    for view in views:
        source = batch / action["pose"] / view / f"frame_{frame:04d}.png"
        with Image.open(source) as opened:
            tiles.append(opened.convert("RGB").resize(
                (640, 360), Image.Resampling.LANCZOS))
    panel = Image.new("RGB", (640 * len(tiles), 360), (0, 0, 0))
    for index, tile in enumerate(tiles):
        panel.paste(tile, (index * 640, 0))
    draw = ImageDraw.Draw(panel, "RGBA")
    title_font = font(24)
    view_font = font(19)
    number_font = font(38)
    overlay_label(draw, (18, 18),
                  f"{action['order']:02d}  {action['label']}", title_font)
    for index, view in enumerate(views):
        overlay_label(draw, (index * 640 + 320, 18), VIEW_LABELS[view],
                      view_font, anchor="ma")
    locator = f"{action['order']:02d}-{frame:03d}"
    draw.text((panel.width - 18, panel.height - 14), locator,
              font=number_font, anchor="rs", fill=(255, 28, 28),
              stroke_width=4, stroke_fill=(0, 0, 0))
    panel.save(output, format="PNG", compress_level=2)


def run(command: list[str]) -> None:
    completed = subprocess.run(command, cwd=REPO, text=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    if completed.returncode != 0:
        raise RuntimeError("command failed:\n" + " ".join(command)
                           + "\n" + completed.stdout[-8000:])


def encode_action(ffmpeg: str, frames: Path, fps: int,
                  output: Path) -> None:
    run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
         "-framerate", str(fps), "-i", str(frames / "frame_%04d.png"),
         "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)])


def log_evidence() -> str:
    latest = REPO / "run/logs/latest.log"
    if not latest.is_file():
        return "latest.log missing\n"
    selected = []
    for line in latest.read_text(encoding="utf-8", errors="replace").splitlines():
        lower = line.lower()
        if ("project seele initialized" in lower
                or "foundation review" in lower
                or "foundation audit" in lower
                or "manifold inner body" in lower
                or "motion-lab melee" in lower
                or "live jump accepted" in lower
                or "base animation selection" in lower
                or (("error" in lower or "fatal" in lower)
                    and "projectseele" in lower)):
            selected.append(line)
    return "\n".join(selected) + "\n"


def build(batch: Path, output: Path) -> tuple[Path, Path]:
    contract = load_json(CONTRACT)
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "phase_f_gate_report.json"
    source_report = batch / "phase_f_gate_report.json"
    report = load_json(source_report) if source_report.is_file() else None
    valid_cached_report = (report is not None
                           and report.get("batch") == batch.name
                           and report.get("result")
                           == "ELIGIBLE_FOR_HUMAN_REVIEW_ONLY"
                           and report.get("contractSha256")
                           == digest(CONTRACT)
                           and report.get("frames")
                           == sum(1 for line in (batch / "frame_audit.jsonl")
                                  .read_text(encoding="utf-8").splitlines()
                                  if line.strip())
                           and report.get("frames")
                           == len(list(batch.rglob("frame_*.png"))))
    if valid_cached_report:
        shutil.copy2(source_report, report_path)
    else:
        report = audit_capture(batch, report_path)
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required to build the review package")
    fps = int(contract["captureFps"])
    videos = []
    with tempfile.TemporaryDirectory(prefix=".phase_f_frames-",
                                     dir=output) as temporary:
        temporary_root = Path(temporary)
        for action in contract["actions"]:
            action_frames = temporary_root / f"{action['order']:02d}"
            action_frames.mkdir()
            for frame in range(1, int(action["framesPerView"]) + 1):
                make_panel(batch, action, contract["views"], frame,
                           action_frames / f"frame_{frame:04d}.png")
            video = output / f"{action['order']:02d}_{action['pose']}.mp4"
            encode_action(ffmpeg, action_frames, fps, video)
            videos.append(video)
        concat = temporary_root / "concat.txt"
        concat.write_text("".join(
            f"file '{video.as_posix().replace(chr(39), chr(39)*2)}'\n"
            for video in videos), encoding="utf-8")
        combined = output / "00_EVA_FOUNDATION_PHASE_F_ALL_ACTIONS.mp4"
        run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
             "-f", "concat", "-safe", "0", "-i", str(concat),
             "-c", "copy", "-movflags", "+faststart", str(combined)])

    (output / "runtime_log_evidence.txt").write_text(
        log_evidence(), encoding="utf-8")
    readme = """# EVA 六基础动作 Phase F 人工验收包

这不是“已视觉批准”的交付，而是已通过自动形变门禁、等待人眼裁决的候选包。
画面来自实际 Minecraft 游戏 framebuffer；走、跑、跳、徒手攻击和粒子刀攻击均走正式驾驶输入/服务端动作入口。三栏依次为正面、侧面、背面。
其中 jump + landing 已因旧 land 的手—胫穿透进入 `CANDIDATE_HASH_CHANGED`；只有人工接受后才可晋升，其他五段仍是冻结基线的实机重放。

## 红色编号

右下角红色 `动作号-帧号` 只表示审查时间顺序：数字小的更早、数字大的更晚。它不是模型几何、贴图、游戏 UI，也不是骨骼或关节标记。反馈问题时请直接引用编号，例如 `05-014`。

## 请人工判断

1. 重量、发力顺序和轮廓是否像 EVA，而不是放大的人类或扭曲木偶；
2. 待机、走、跑是否有清晰区别，步态是否稳定；
3. 跳跃是否包含蓄力、离地、空中、落地和恢复，且无闪回；
4. 徒手攻击是否有预备、提交、随动和回收，双臂不异常张开；
5. 粒子刀是否始终可靠握在手里，头部、手指和刀轨迹无明显错误；
6. 任一角度是否出现装甲断裂、穿胸、反肘/反膝、漂浮部件或动作结束卡顿。

请按动作回复“接受”或“拒绝”，拒绝时附红色编号和现象。自动报告只能给出 `ELIGIBLE_FOR_HUMAN_REVIEW_ONLY`，不能替代你的视觉批准。
"""
    (output / "README_人工验收.md").write_text(readme, encoding="utf-8")
    files = videos + [combined, report_path,
                      output / "runtime_log_evidence.txt",
                      output / "README_人工验收.md"]
    manifest = {
        "schema": 1,
        "phase": "F",
        "result": report["result"],
        "captureBatch": batch.name,
        "captureDirectory": str(batch),
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "fps": fps,
        "resolution": [1920, 360],
        "views": contract["views"],
        "actions": contract["actions"],
        "redNumberMeaning": contract["manualReview"]["redNumberMeaning"],
        "automaticGateReport": report,
        "files": [{"name": path.name, "bytes": path.stat().st_size,
                   "sha256": digest(path)} for path in files],
        "visuallyApproved": False,
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False,
                                        indent=2) + "\n", encoding="utf-8")
    archive = output.parent / f"{output.name}.zip"
    if archive.exists():
        archive.unlink()
    shutil.make_archive(str(archive.with_suffix("")), "zip",
                        root_dir=output.parent, base_dir=output.name)
    return combined, archive


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    batch = args.batch if args.batch else latest_batch()
    output = args.output if args.output else DEFAULT_ROOT / batch.name
    combined, archive = build(batch.resolve(), output.resolve())
    print(f"EVA Phase-F manual review package ready: {output.resolve()}")
    print(f"combined={combined} archive={archive}")


if __name__ == "__main__":
    main()
