"""インスタのリール動画(縦長 1080x1920、約20〜30秒、音なし)を、SNS案のInstagramスライドから作る。

- 画面: 1枚目=タイトル+実写のマンチカンの写真(assets/mascot/)、中間=1スライド1メッセージの大きな文字、最後=「詳しくはnoteで」。
- 動き: ゆっくりのズーム+場面のあいだのクロスフェード(ffmpeg)。
- 音: 入れない(曲の権利の問題があるため)。インスタの画面で、流行の音源を選んで付ける。
- 出力: runs/<ID>/reel/reel.mp4、reel/caption.txt(投稿文)、reel/frames/*.png(各場面の画像)。
- 投稿は、あなたが手で行う(システムは、インスタに投稿しない)。
"""
from __future__ import annotations

import base64
import html
import re
import shutil
import subprocess
from pathlib import Path

from . import artifacts, images, runs
from .log import log_event

SIZE = (1080, 1920)
SCENE_SEC = 3.4          # 1場面の長さ(秒)
FADE_SEC = 0.45          # 場面のあいだの重なり(秒)
FPS = 30
PHOTO = "assets/mascot/munchkin_cc0_1.jpg"


class ReelError(Exception):
    pass


def find_ffmpeg() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001 - 入っていなければ、PATHの ffmpeg を探す
        found = shutil.which("ffmpeg")
        if found:
            return found
    raise ReelError("動画をつくる ffmpeg がありません。`python -m pip install imageio-ffmpeg` を実行してください")


def _rich(text: str) -> str:
    return html.escape(text).replace("\n", "<br>")


def _frame_html(cfg: dict, inner: str) -> str:
    c = cfg["colors"]
    w, h = SIZE
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;width:{w}px;height:{h}px;background:{c['background']};color:{c['text']};font-family:{cfg['font_family']};overflow:hidden}}
.f{{box-sizing:border-box;width:{w}px;height:{h}px;position:relative}}
.safe{{position:absolute;left:84px;right:84px;top:300px;bottom:420px;display:flex;flex-direction:column;justify-content:center}}
.main{{font-weight:900;line-height:1.38;line-break:strict;word-break:normal;overflow-wrap:break-word;text-wrap:balance}}
.bar{{width:140px;height:12px;background:{c['accent']};margin-bottom:44px;border-radius:6px}}
.dots{{position:absolute;left:84px;top:220px;display:flex;gap:10px}}
.dots i{{display:block;width:44px;height:10px;border-radius:5px;background:rgba(22,35,63,.2)}}
.dots i.on{{background:{c['accent']}}}
.brand{{position:absolute;left:84px;bottom:470px;font-size:34px;font-weight:700;color:{c['subtext']}}}
.tag{{display:inline-block;align-self:flex-start;background:{c['text']};color:{c['background']};font-weight:700;font-size:40px;padding:10px 28px;border-radius:10px;margin-bottom:36px}}
.photo{{margin-top:44px;width:912px;height:620px;border-radius:40px;border:12px solid #fff;overflow:hidden;box-shadow:0 20px 40px rgba(80,58,0,.35);transform:rotate(-1.5deg);background:#fff}}
.photo img{{width:100%;height:100%;object-fit:cover;display:block}}
</style></head><body><div class="f">{inner}</div></body></html>"""


def _photo_tag(root: Path) -> str:
    f = Path(root) / PHOTO
    if not f.exists():
        return ""
    b64 = base64.b64encode(f.read_bytes()).decode("ascii")
    return f'<div class="photo"><img src="data:image/jpeg;base64,{b64}"></div>'


def scene_frames(root: Path, texts: list[str], cfg: dict) -> list[str]:
    """各場面のHTML。1枚目はタイトル+写真、最後はまとめ、そのあいだは大きな文字。"""
    n = len(texts)
    out = []
    for i, raw in enumerate(texts):
        txt = images.slide_text(raw)
        if i == 0:
            size = 112 if len(txt) <= 22 else 96
            inner = (f'<div class="safe"><div class="tag">節約</div><div class="main" style="font-size:{size}px">{_rich(txt)}</div>{_photo_tag(root)}</div>')
        else:
            longest = max(len(line) for line in txt.splitlines())  # いちばん長い行が、画面の幅(912px)に収まる大きさにする
            size = max(60, min(104, int(912 / (min(longest, 11) + .4))))
            dots = "".join(f'<i class="{"on" if j == i else ""}"></i>' for j in range(1, n))
            inner = (f'<div class="dots">{dots}</div><div class="safe"><div class="bar"></div><div class="main" style="font-size:{size}px">{_rich(txt)}</div></div>'
                     '<div class="brand">人生最適化中の会社員</div>')
        out.append(_frame_html(cfg, inner))
    return out


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, timeout=600, check=False)
    if r.returncode != 0:
        raise ReelError("ffmpeg が失敗しました: " + r.stderr.decode("utf-8", "replace")[-400:])


def build_video(frames: list[Path], out: Path, ffmpeg: str) -> None:
    """各場面の画像を、ゆっくりズームする短い動画にして、クロスフェードでつなぐ。"""
    work = out.parent / "_clips"
    work.mkdir(parents=True, exist_ok=True)
    clips = []
    frames_per_clip = int(SCENE_SEC * FPS)
    w, h = SIZE
    for i, fr in enumerate(frames):
        clip = work / f"c{i:02d}.mp4"
        vf = (f"scale={w * 2}:{h * 2},zoompan=z='min(zoom+0.0007,1.07)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames_per_clip}:s={w}x{h}:fps={FPS},"
              "format=yuv420p")
        _run([ffmpeg, "-y", "-loglevel", "error", "-loop", "1", "-i", str(fr), "-vf", vf, "-t", f"{SCENE_SEC}", "-r", str(FPS),
              "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", str(clip)])
        clips.append(clip)
    if len(clips) == 1:
        shutil.copy(clips[0], out)
    else:
        cmd = [ffmpeg, "-y", "-loglevel", "error"]
        for c in clips:
            cmd += ["-i", str(c)]
        parts, last, offset = [], "[0:v]", 0.0
        for i in range(1, len(clips)):
            offset += SCENE_SEC - FADE_SEC
            label = f"[v{i}]"
            parts.append(f"{last}[{i}:v]xfade=transition=fade:duration={FADE_SEC}:offset={offset:.2f}{label}")
            last = label
        cmd += ["-filter_complex", ";".join(parts), "-map", last, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", "-r", str(FPS), str(out)]
        _run(cmd)
    shutil.rmtree(work, ignore_errors=True)


def caption_of(sns_text: str) -> str:
    return (artifacts.section(sns_text, "Instagramキャプション") or "").strip()


def make_reel(root: Path, run_id: str) -> dict:
    root = Path(root)
    data = runs.read_run(root, run_id)
    if "sns" not in data["steps_done"]:
        raise ReelError("SNS案(06_sns.md)が完了してから作ってください")
    rdir = runs.run_path(root, run_id)
    sns = (rdir / artifacts.FILES["sns"]).read_text(encoding="utf-8")
    texts = images.slides_from_sns(sns)
    if len(texts) < 3:
        raise ReelError("Instagramのスライド(「N枚目:」)が3枚以上必要です")
    cfg = images.load_config(root)
    browser = images.find_browser(cfg)
    ffmpeg = find_ffmpeg()
    out_dir = rdir / "reel"
    fdir = out_dir / "frames"
    fdir.mkdir(parents=True, exist_ok=True)
    frames = []
    for i, page in enumerate(scene_frames(root, texts, cfg), 1):
        fr = fdir / f"scene_{i:02d}.png"
        images.render(page, fr, SIZE, browser, out_dir / "_work")
        frames.append(fr)
    shutil.rmtree(out_dir / "_work", ignore_errors=True)
    mp4 = out_dir / "reel.mp4"
    build_video(frames, mp4, ffmpeg)
    cap = caption_of(sns)
    (out_dir / "caption.txt").write_text(cap + "\n", encoding="utf-8")
    seconds = round(len(frames) * SCENE_SEC - (len(frames) - 1) * FADE_SEC, 1)
    log_event(root, "reel_made", run_id=run_id, scenes=len(frames), seconds=seconds)
    return {"video": mp4, "caption": out_dir / "caption.txt", "scenes": len(frames), "seconds": seconds}
