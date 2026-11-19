"""キャラ解説型のショート動画(縦長 1080x1920)を、台本(JSON)から作る。

- 画面: クリーム色の背景・上に緑の帯・番号つきの見出し・中央に数字のカード・左下に猫の博士(オリジナルの絵)・字幕の吹き出し。
  (参考にした動画のキャラ・名前・配色の細部は、まねない。猫の博士は、このシステムのオリジナル)
- 台本: runs/<ID>/reel_cat/script.json  {"channel":..., "scenes":[{"step","head","chips","card","sub","say"}...], "credit":...}
  すべての数字は、記事(05_revised.md)で確認済みのものだけを使う。
- 声: VOICEVOX(ずんだもん。PCに入っていれば自動)→ なければ音なし。声を入れたときは、投稿文に「VOICEVOX:ずんだもん」を足す。
- 出力: runs/<ID>/reel_cat/reel.mp4 / caption.txt / narration.txt / frames/
- 投稿は、あなたが手で行う。
"""
from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

from . import images, reels, runs
from .log import log_event

SIZE = reels.SIZE

CAT_SVG = """<svg viewBox="0 0 420 520" xmlns="http://www.w3.org/2000/svg">
<path d="M60 330 Q60 290 120 285 L300 285 Q360 290 360 330 L380 520 L40 520 Z" fill="#ffffff" stroke="#c9ccd3" stroke-width="4"/>
<path d="M175 288 L210 360 L245 288 Z" fill="#7bc89a"/>
<path d="M190 288 L210 330 L230 288 Z" fill="#2f8f5b"/>
<ellipse cx="210" cy="190" rx="140" ry="122" fill="#aeb8c8"/>
<polygon points="86,120 98,28 172,84" fill="#aeb8c8"/><polygon points="106,100 108,56 146,88" fill="#f4b6c0"/>
<polygon points="334,120 322,28 248,84" fill="#aeb8c8"/><polygon points="314,100 312,56 274,88" fill="#f4b6c0"/>
<path d="M190 82 L196 112 M210 78 L210 112 M230 82 L224 112" stroke="#8793a8" stroke-width="9" stroke-linecap="round"/>
<ellipse cx="210" cy="232" rx="82" ry="62" fill="#e6ebf3"/>
<circle cx="150" cy="190" r="44" fill="#ffffff" fill-opacity=".75" stroke="#4a3b2a" stroke-width="9"/>
<circle cx="270" cy="190" r="44" fill="#ffffff" fill-opacity=".75" stroke="#4a3b2a" stroke-width="9"/>
<path d="M194 188 Q210 176 226 188" stroke="#4a3b2a" stroke-width="9" fill="none"/>
<circle cx="152" cy="194" r="13" fill="#2a2118"/><circle cx="268" cy="194" r="13" fill="#2a2118"/>
<circle cx="157" cy="188" r="4.5" fill="#fff"/><circle cx="273" cy="188" r="4.5" fill="#fff"/>
<path d="M198 226 L222 226 L210 242 Z" fill="#f08aa0"/>
<path d="M210 242 L210 254 M210 254 Q196 272 180 262 M210 254 Q224 272 240 262" stroke="#4a3b2a" stroke-width="6" fill="none" stroke-linecap="round"/>
<path d="M120 236 L58 226 M120 250 L56 256 M300 236 L362 226 M300 250 L364 256" stroke="#8793a8" stroke-width="5" stroke-linecap="round"/>
<ellipse cx="114" cy="262" rx="20" ry="12" fill="#f4b6c0" fill-opacity=".7"/><ellipse cx="306" cy="262" rx="20" ry="12" fill="#f4b6c0" fill-opacity=".7"/>
</svg>"""


class CharReelError(Exception):
    pass


def _frame(cfg: dict, sc: dict, channel: str) -> str:
    w, h = SIZE
    step = html.escape(sc.get("step", ""))
    head = html.escape(sc.get("head", "")).replace("\n", "<br>")
    chips = "".join(f'<span class="chip{" hl" if i == len(sc.get("chips", [])) - 1 else ""}">{html.escape(c)}</span>' for i, c in enumerate(sc.get("chips", [])))
    card_lines = "".join(f"<div>{html.escape(l).replace('[[', '<b>').replace(']]', '</b>')}</div>" for l in sc.get("card", []))
    sub = html.escape(sc.get("sub", "")).replace("\n", "<br>")
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;width:{w}px;height:{h}px;overflow:hidden;background:#fff6e1;font-family:{cfg['font_family']};color:#2b2a26}}
.f{{position:relative;width:{w}px;height:{h}px}}
.band{{position:absolute;left:0;right:0;top:150px;height:96px;background:#d9efdc;display:flex;align-items:center;justify-content:center;font-size:42px;font-weight:900;color:#2c6e49;letter-spacing:.06em}}
.step{{position:absolute;left:72px;right:72px;top:300px;background:#fff;border:6px solid #3a9d6a;border-radius:28px;padding:34px 40px;font-size:64px;font-weight:900;line-height:1.3;box-shadow:0 8px 0 #bfe3cb}}
.chips{{position:absolute;left:72px;right:72px;top:560px;display:flex;flex-wrap:wrap;gap:14px}}
.chip{{background:#fff;border:4px solid #d6c9a8;border-radius:16px;padding:10px 20px;font-size:38px;font-weight:700}}
.chip.hl{{background:#ffd98a;border-color:#e0a63b}}
.card{{position:absolute;left:72px;right:72px;top:{"740" if sc.get("chips") else "620"}px;min-height:{"300" if sc.get("chips") else "420"}px;background:#fff;border-radius:36px;border:6px solid #e8dcc0;padding:28px 40px;font-size:{"62" if sc.get("chips") else "70"}px;font-weight:900;line-height:1.45;display:flex;flex-direction:column;justify-content:center;text-align:center}}
.card b{{color:#d4442e;font-size:1.3em}}
.cat{{position:absolute;left:30px;bottom:300px;width:420px;height:520px}}
.bubble{{position:absolute;left:470px;right:48px;bottom:420px;background:#fff;border:6px solid #2b2a26;border-radius:36px;padding:30px 34px;font-size:56px;font-weight:900;line-height:1.38;text-wrap:balance}}
.bubble:before{{content:"";position:absolute;left:-30px;bottom:70px;border:22px solid transparent;border-right:34px solid #2b2a26;border-left:0}}
.brand{{position:absolute;right:48px;bottom:330px;font-size:30px;font-weight:700;color:#7a7360}}
</style></head><body><div class="f">
<div class="band">{html.escape(channel)}</div>
{f'<div class="step">{step}</div>' if step else ''}
{f'<div class="chips">{chips}</div>' if chips else ''}
{f'<div class="card">{card_lines}</div>' if card_lines else ''}
<div class="cat">{CAT_SVG}</div>
{f'<div class="bubble">{sub}</div>' if sub else ''}
</div></body></html>"""


def make_char_reel(root: Path, run_id: str, voice: str = "auto") -> dict:
    root = Path(root)
    rdir = runs.run_path(root, run_id)
    out_dir = rdir / "reel_cat"
    script = out_dir / "script.json"
    if not script.exists():
        raise CharReelError(f"台本がありません: {script}")
    data = json.loads(script.read_text(encoding="utf-8"))
    scenes = data["scenes"]
    cfg = images.load_config(root)
    browser = images.find_browser(cfg)
    ffmpeg = reels.find_ffmpeg()
    fdir = out_dir / "frames"
    fdir.mkdir(parents=True, exist_ok=True)
    frames = []
    for i, sc in enumerate(scenes, 1):
        fr = fdir / f"scene_{i:02d}.png"
        images.render(_frame(cfg, sc, data.get("channel", "ねこ博士のお金ノート")), fr, SIZE, browser, out_dir / "_work")
        frames.append(fr)
    shutil.rmtree(out_dir / "_work", ignore_errors=True)
    narr = [sc.get("say") or reels.narration_text(sc.get("sub", "")) for sc in scenes]
    (out_dir / "narration.txt").write_text("\n".join(f"{i}. {t}" for i, t in enumerate(narr, 1)) + "\n", encoding="utf-8")
    voices, used = None, "none"
    if voice in ("auto", "voicevox") and reels.voicevox_ready():
        voices = reels.synthesize_voicevox(narr, out_dir / "_voice")
        used = "voicevox"
    elif voice == "voicevox":
        raise CharReelError("VOICEVOX のエンジンが見つかりません(PCで、VOICEVOX を起動してから実行してください)")
    durations = reels.scene_durations([reels.wav_seconds(v) for v in voices] if voices else None, len(frames))
    mp4 = out_dir / "reel.mp4"
    reels.build_video(frames, mp4, ffmpeg, durations, voices)
    shutil.rmtree(out_dir / "_voice", ignore_errors=True)
    cap = data.get("caption", "").rstrip()
    if data.get("credit"):
        cap += "\n\n" + data["credit"]
    if used == "voicevox":
        cap += f"\n\nVOICEVOX:{reels.VOICEVOX_NAME}"
    (out_dir / "caption.txt").write_text(cap.strip() + "\n", encoding="utf-8")
    seconds = round(sum(durations) - (len(frames) - 1) * reels.FADE_SEC, 1)
    log_event(root, "char_reel_made", run_id=run_id, scenes=len(frames), seconds=seconds, voice=used)
    return {"video": mp4, "caption": out_dir / "caption.txt", "narration": out_dir / "narration.txt", "scenes": len(frames), "seconds": seconds, "voice": used}
