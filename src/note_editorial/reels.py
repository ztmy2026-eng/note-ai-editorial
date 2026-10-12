"""インスタのリール動画(縦長 1080x1920、約25〜40秒)を、SNS案のInstagramスライドから作る。

- 画面: 1枚目=タイトル+実写のマンチカンの写真(assets/mascot/)、中間=1スライド1メッセージの大きな文字、最後=「詳しくはnoteで」。
- 動き: ゆっくりのズーム+場面のあいだのクロスフェード(ffmpeg)。
- 声: 各場面の文字を、読み上げの声(ナレーション)にして重ねる。既定は Windows の日本語の声(Microsoft Haruka。パソコンに入っている音声。追加の費用・権利の問題なし)。
  声が使えない環境(クラウドなど)では、音なしの動画になる。曲(BGM)は入れない(権利のため)。インスタの画面で付ける。
- 出力: runs/<ID>/reel/reel.mp4、reel/caption.txt(投稿文)、reel/narration.txt(読み上げの原稿)、reel/frames/*.png(各場面の画像)。
- 投稿は、あなたが手で行う(システムは、インスタに投稿しない)。
"""
from __future__ import annotations

import base64
import html
import re
import shutil
import subprocess
import wave
from pathlib import Path

from . import artifacts, images, runs
from .log import log_event

SIZE = (1080, 1920)
SCENE_SEC = 3.4          # 1場面の最短の長さ(秒)。声が長ければ、声に合わせて伸ばす
VOICE_PAD = 0.9          # 声が終わってから、次の場面までの間(秒)
FADE_SEC = 0.45          # 場面のあいだの重なり(秒)
FPS = 30
PHOTO = "assets/mascot/munchkin_cc0_1.jpg"
SAPI_VOICE = "Microsoft Haruka Desktop"


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


# ---------------------------------------------------------------- 声(ナレーション)
def narration_text(raw: str) -> str:
    """スライドの文字を、読み上げ用の原稿にする(改行は間にする。記号・かっこは読まない)。"""
    parts = []
    for line in images.slide_text(raw).splitlines():
        line = line.strip()
        if not line:
            continue
        parts.append(line if line[-1] in "。!?!?、" else line + "。")
    s = " ".join(parts)
    s = re.sub(r"[【】「」『』]", "", s)
    s = s.replace("(例です)", "。例です。")
    return s.strip()


def sapi_available() -> bool:
    return shutil.which("powershell") is not None and shutil.which("powershell.exe") is not None and _sapi_has_voice()


def _sapi_has_voice() -> bool:
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "Add-Type -AssemblyName System.Speech;(New-Object System.Speech.Synthesis.SpeechSynthesizer).GetInstalledVoices()|%{$_.VoiceInfo.Name}"],
                           capture_output=True, timeout=60, check=False)
        return SAPI_VOICE in r.stdout.decode("utf-8", "replace") or SAPI_VOICE in r.stdout.decode("cp932", "replace")
    except (OSError, subprocess.TimeoutExpired):
        return False


def synthesize_sapi(texts: list[str], out_dir: Path, rate: int = 2) -> list[Path]:
    """Windows の日本語の声で、場面ごとに wav を作る。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    jobs = []
    for i, t in enumerate(texts, 1):
        txt = out_dir / f"voice_{i:02d}.txt"
        txt.write_text(t, encoding="utf-8")
        jobs.append((txt, out_dir / f"voice_{i:02d}.wav"))
    ps = out_dir / "speak.ps1"
    lines = ["Add-Type -AssemblyName System.Speech", "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer",
             f"$s.SelectVoice('{SAPI_VOICE}')", f"$s.Rate = {int(rate)}"]
    for txt, wav in jobs:
        lines += [f"$t = Get-Content -Raw -Encoding UTF8 -LiteralPath '{txt.resolve()}'", f"$s.SetOutputToWaveFile('{wav.resolve()}')", "$s.Speak($t)", "$s.SetOutputToNull()"]
    ps.write_text("\n".join(lines), encoding="utf-8-sig")
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps)], capture_output=True, timeout=300, check=False)
    if r.returncode != 0 or not all(w.exists() and w.stat().st_size > 0 for _, w in jobs):
        raise ReelError("声(読み上げ)を作れませんでした: " + r.stderr.decode("utf-8", "replace")[-300:])
    return [w for _, w in jobs]


def wav_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def scene_durations(voice_secs: list[float] | None, n: int) -> list[float]:
    """各場面の長さ。声があれば、声の長さ+間(最短 SCENE_SEC)。"""
    if not voice_secs:
        return [SCENE_SEC] * n
    return [max(SCENE_SEC, v + VOICE_PAD + FADE_SEC) for v in voice_secs]


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, timeout=900, check=False)
    if r.returncode != 0:
        raise ReelError("ffmpeg が失敗しました: " + r.stderr.decode("utf-8", "replace")[-400:])


def build_video(frames: list[Path], out: Path, ffmpeg: str, durations: list[float], voices: list[Path] | None = None) -> None:
    """各場面の画像を、ゆっくりズームする動画にして、クロスフェードでつなぎ、声(あれば)を場面の頭に合わせて重ねる。"""
    work = out.parent / "_clips"
    work.mkdir(parents=True, exist_ok=True)
    w, h = SIZE
    clips = []
    for i, (fr, dur) in enumerate(zip(frames, durations)):
        clip = work / f"c{i:02d}.mp4"
        vf = (f"scale={w * 2}:{h * 2},zoompan=z='min(zoom+0.0007,1.07)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(dur * FPS)}:s={w}x{h}:fps={FPS},"
              "format=yuv420p")
        _run([ffmpeg, "-y", "-loglevel", "error", "-loop", "1", "-i", str(fr), "-vf", vf, "-t", f"{dur:.2f}", "-r", str(FPS),
              "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", str(clip)])
        clips.append(clip)
    cmd = [ffmpeg, "-y", "-loglevel", "error"]
    for c in clips:
        cmd += ["-i", str(c)]
    for v in voices or []:
        cmd += ["-i", str(v)]
    parts, last = [], "[0:v]"
    starts = [0.0]                                   # 各場面が、画面にはっきり出る時刻
    offset = 0.0
    for i in range(1, len(clips)):
        offset += durations[i - 1] - FADE_SEC
        parts.append(f"{last}[{i}:v]xfade=transition=fade:duration={FADE_SEC}:offset={offset:.2f}[v{i}]")
        last = f"[v{i}]"
        starts.append(offset + FADE_SEC)
    maps = ["-map", last if len(clips) > 1 else "[0:v]"]
    if len(clips) == 1:
        parts = ["[0:v]null[v0]"]
        maps = ["-map", "[v0]"]
    if voices:
        labels = []
        for k, st in enumerate(starts):
            ms = int((st + 0.25) * 1000)
            parts.append(f"[{len(clips) + k}:a]adelay={ms}|{ms},aformat=sample_rates=44100:channel_layouts=stereo[a{k}]")
            labels.append(f"[a{k}]")
        parts.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0:duration=longest[aout]")
        maps += ["-map", "[aout]", "-c:a", "aac", "-b:a", "160k"]
    cmd += ["-filter_complex", ";".join(parts), *maps, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", "-r", str(FPS), str(out)]
    _run(cmd)
    shutil.rmtree(work, ignore_errors=True)


def caption_of(sns_text: str) -> str:
    return (artifacts.section(sns_text, "Instagramキャプション") or "").strip()


def make_reel(root: Path, run_id: str, voice: str = "auto") -> dict:
    """voice: auto(声が使えれば声つき)| sapi(Windowsの声)| none(音なし)"""
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
    narr = [narration_text(t) for t in texts]
    (out_dir / "narration.txt").write_text("\n".join(f"{i}. {t}" for i, t in enumerate(narr, 1)) + "\n", encoding="utf-8")
    voices, used = None, "none"
    if voice in ("auto", "sapi"):
        if sapi_available():
            voices = synthesize_sapi(narr, out_dir / "_voice")
            used = "sapi"
        elif voice == "sapi":
            raise ReelError(f"声({SAPI_VOICE})が、このパソコンにありません")
    durations = scene_durations([wav_seconds(v) for v in voices] if voices else None, len(frames))
    mp4 = out_dir / "reel.mp4"
    build_video(frames, mp4, ffmpeg, durations, voices)
    shutil.rmtree(out_dir / "_voice", ignore_errors=True)
    cap = caption_of(sns)
    (out_dir / "caption.txt").write_text(cap + "\n", encoding="utf-8")
    seconds = round(sum(durations) - (len(frames) - 1) * FADE_SEC, 1)
    log_event(root, "reel_made", run_id=run_id, scenes=len(frames), seconds=seconds, voice=used)
    return {"video": mp4, "caption": out_dir / "caption.txt", "narration": out_dir / "narration.txt", "scenes": len(frames), "seconds": seconds, "voice": used}
