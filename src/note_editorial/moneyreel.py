"""「お金の積み上げ」型のアニメ動画(縦長 1080x1920)を、台本(JSON)から作る。

見た目: 濃紺の背景に、金色に光る札束のブロック。上にタイトル、下に字幕の箱、左上に小さな分類タグ。
(参考にした動画の、画面の雰囲気だけを取り入れた。文章・数字・名前は、まねない。数字は、記事で確認済みのものだけを使う)

場面の種類:
- compare: 札束の高さで、いくつかの金額を並べて比べる。{"type":"compare","title","items":[{"label","value","hl":true}],"unit":"円","sub","say"}
- deduct : 全体の札束から、引かれる分が持ち上がって横に出ていき、残りが分かる。
           {"type":"deduct","title","total","total_label","parts":[{"label","amount"}],"remain_label","sub","say"}
- card   : 文字だけの場面(まとめ・注意書き)。{"type":"card","title","lines":[...],"sub","say"}

台本の場所: runs/<ID>/reel_money/script.json
出力: runs/<ID>/reel_money/reel.mp4 / caption.txt / narration.txt
声: VOICEVOX(ずんだもん。PCに入っていれば自動)。なければ音なし。曲(BGM)は入れない。
投稿は、あなたが手で行う。
"""
from __future__ import annotations

import html
import json
import math
import shutil
import subprocess
from pathlib import Path

from . import images, reels, runs
from .log import log_event

W, H = reels.SIZE
FPS = 30
BG_TOP, BG_BOT = (10, 14, 28), (22, 24, 40)
GOLD = (233, 170, 70)
GOLD_DK = (158, 104, 30)
GOLD_LT = (255, 214, 130)
SIDE = (118, 76, 22)
GROUND_Y = 1330


class MoneyReelError(Exception):
    pass


# ------------------------------------------------------------------ 文字(Chromeで透明PNGにする)
def _text_png(browser: str, work: Path, name: str, body: str, size: tuple[int, int], font: str) -> Path:
    work.mkdir(parents=True, exist_ok=True)
    out = work / f"{name}.png"
    if out.exists():
        return out
    src = work / f"{name}.html"
    src.write_text(f"""<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;background:transparent;width:{size[0]}px;height:{size[1]}px;overflow:hidden;font-family:{font};color:#fff}}
{body.split('<!--body-->')[0]}</style></head><body>{body.split('<!--body-->')[1]}</body></html>""", encoding="utf-8")
    cmd = [browser, "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--default-background-color=00000000",
           f"--screenshot={out.resolve()}", f"--window-size={size[0]},{size[1]}", src.resolve().as_uri()]
    subprocess.run(cmd, capture_output=True, timeout=120, check=False)
    if not out.exists():
        raise MoneyReelError("文字の画像を作れませんでした(ブラウザが見つかりません)")
    return out


def _fmt_yen(v: int, unit: str = "円") -> str:
    if v >= 10000 and v % 1000 == 0 and unit == "万":
        return f"{v / 10000:g}万円"
    return f"{v:,}円"


def _label(browser, work, key, text, size_px, color="#fff", big=None, w=520):
    """数字ラベル。textの[[...]]を、金色の大きい字にする。"""
    t = html.escape(text).replace("[[", f'<b style="color:#ffc857;font-size:{big or int(size_px * 1.35)}px">').replace("]]", "</b>")
    body = (f"<!--body--><div style=\"width:{w}px;text-align:center;font-weight:900;font-size:{size_px}px;line-height:1.25;color:{color};"
            f"text-shadow:0 0 18px rgba(0,0,0,.7)\">{t}</div>")
    from PIL import Image
    p = _text_png(browser, work, key, body.replace("<!--body-->", "<!--body-->"), (w, int(size_px * 2.4)), "'Noto Sans CJK JP','IPAGothic',sans-serif")
    return Image.open(p).convert("RGBA")


# ------------------------------------------------------------------ 描画
def _bg():
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * t) for i in range(3)))
    # 床の格子(奥に向かって細くなる)
    for k in range(-14, 15):
        x0 = W / 2 + k * 70
        x1 = W / 2 + k * 190
        d.line([(x0, GROUND_Y - 30), (x1, H)], fill=(60, 52, 40), width=2)
    for j in range(8):
        y = GROUND_Y - 30 + (j ** 1.7) * 28
        d.line([(0, y), (W, y)], fill=(60, 52, 40), width=2)
    return img.convert("RGBA")


def _poly(d, pts, fill, outline=None, width=0):
    d.polygon(pts, fill=fill)
    if outline:
        d.line(pts + [pts[0]], fill=outline, width=width)


def draw_stack(layer, cx: float, base_y: float, w: int, h: float, alpha: float = 1.0, dashed: bool = False, hl: bool = False):
    """金色の札束の箱。cx=中心、base_y=底、w=幅、h=高さ。"""
    from PIL import ImageDraw
    if h < 2:
        return
    dx, dy = int(w * 0.34), int(w * 0.17)
    x0, x1 = cx - w / 2 - dx / 2, cx + w / 2 - dx / 2
    top = base_y - h
    d = ImageDraw.Draw(layer, "RGBA")
    a = int(255 * alpha)
    if dashed:
        pts = [(x0, top), (x1, top), (x1, base_y), (x0, base_y)]
        for i in range(4):
            (ax, ay), (bx, by) = pts[i], pts[(i + 1) % 4]
            n = int(max(abs(bx - ax), abs(by - ay)) // 22)
            for k in range(0, n, 2):
                s, e = k / max(n, 1), min((k + 1) / max(n, 1), 1)
                d.line([(ax + (bx - ax) * s, ay + (by - ay) * s), (ax + (bx - ax) * e, ay + (by - ay) * e)], fill=(255, 255, 255, int(a * .55)), width=3)
        return
    front = [(x0, top), (x1, top), (x1, base_y), (x0, base_y)]
    right = [(x1, top), (x1 + dx, top - dy), (x1 + dx, base_y - dy), (x1, base_y)]
    topf = [(x0, top), (x0 + dx, top - dy), (x1 + dx, top - dy), (x1, top)]
    _poly(d, front, GOLD + (a,), GOLD_LT + (a,), 3)
    _poly(d, right, SIDE + (a,), GOLD_DK + (a,), 3)
    _poly(d, topf, GOLD_LT + (a,), (255, 236, 190, a), 3)
    # 札の層の線
    step = max(10, int(w * 0.05))
    y = base_y - step
    while y > top + 4:
        d.line([(x0 + 2, y), (x1 - 2, y)], fill=(140, 92, 24, int(a * .55)), width=2)
        d.line([(x1, y), (x1 + dx, y - dy)], fill=(80, 50, 14, int(a * .6)), width=2)
        y -= step
    # 帯(白い紙の帯)
    for frac in (0.22, 0.62):
        yy = base_y - h * frac
        if h * frac > 30:
            bh = max(26, int(w * 0.16))
            d.rectangle([x0 + w * .30, yy - bh, x0 + w * .70, yy], fill=(236, 232, 222, a), outline=(180, 170, 150, a), width=2)
    if hl:
        d.line(front + [front[0]], fill=(255, 235, 170, a), width=6)


def _glow(base, layer, strength=1.0, radius=14):
    from PIL import Image, ImageFilter
    small = layer.resize((W // 2, H // 2))
    g = small.filter(ImageFilter.GaussianBlur(radius / 2))
    g = g.resize((W, H))
    if strength != 1.0:
        a = g.getchannel("A").point(lambda v: min(255, int(v * strength)))
        g.putalpha(a)
    base.alpha_composite(g)
    base.alpha_composite(layer)


def _ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


# ------------------------------------------------------------------ 場面ごとの動き
class Ctx:
    def __init__(self, browser: str, work: Path, channel: str, tag: str):
        self.browser, self.work, self.channel, self.tag = browser, work, channel, tag
        self.bg = _bg()
        self.top_tag = _label(browser, work, "tag", tag, 30, "#ffc857", big=30, w=300)
        self.ch = _label(browser, work, "channel", channel, 30, "#9aa3b8", big=30, w=400)

    def base(self):
        im = self.bg.copy()
        im.alpha_composite(self.top_tag, (60, 120))
        im.alpha_composite(self.ch, (W - 460, 120))
        return im


def _caption_box(ctx: Ctx, key: str, text: str):
    from PIL import Image
    t = html.escape(text).replace("\n", "<br>")
    body = (f"<!--body--><div style=\"box-sizing:border-box;width:900px;padding:34px 44px;border-radius:30px;background:rgba(20,26,48,.92);"
            f"border:3px solid rgba(255,200,87,.35);font-size:56px;font-weight:900;line-height:1.4;text-align:left\">{t}</div>")
    p = _text_png(ctx.browser, ctx.work, key, body, (900, 420), "'Noto Sans CJK JP','IPAGothic',sans-serif")
    im = Image.open(p).convert("RGBA")
    bbox = im.getchannel("A").getbbox()
    return im.crop(bbox) if bbox else im


def _title(ctx: Ctx, key: str, text: str):
    from PIL import Image
    t = html.escape(text).replace("\n", "<br>")
    body = (f"<!--body--><div style=\"width:960px;text-align:center;font-size:76px;font-weight:900;line-height:1.3;"
            f"text-shadow:0 0 22px rgba(0,0,0,.75)\">{t}</div>")
    p = _text_png(ctx.browser, ctx.work, key, body, (960, 330), "'Noto Sans CJK JP','IPAGothic',sans-serif")
    return Image.open(p).convert("RGBA")


def scene_frames_compare(ctx: Ctx, sc: dict, idx: int, seconds: float):
    from PIL import Image
    items = sc["items"]
    n = len(items)
    vmax = max(i["value"] for i in items)
    hmax = 620
    w = 215 if n <= 3 else 170
    cxs = [120 + (W - 240) * (k + 0.5) / n for k in range(n)]
    title = _title(ctx, f"s{idx}_title", sc["title"])
    cap = _caption_box(ctx, f"s{idx}_cap", sc.get("sub", "")) if sc.get("sub") else None
    names = [_label(ctx.browser, ctx.work, f"s{idx}_n{k}", it["label"], 38, "#e8ecf8", w=int(W / n)) for k, it in enumerate(items)]
    vals = [_label(ctx.browser, ctx.work, f"s{idx}_v{k}", f"[[{it['value']:,}]]円", 40, "#fff", big=58, w=int(W / n)) for k, it in enumerate(items)]
    nframes = int(seconds * FPS)
    for f in range(nframes):
        t = f / FPS
        im = ctx.base()
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for k, it in enumerate(items):
            g = _ease((t - 0.3 - k * 0.25) / 1.3)
            draw_stack(layer, cxs[k], GROUND_Y, w, hmax * it["value"] / vmax * g, hl=bool(it.get("hl")))
        _glow(im, layer, strength=1.2)
        im.alpha_composite(title, ((W - 960) // 2, 250))
        for k, it in enumerate(items):
            hh = hmax * it["value"] / vmax
            im.alpha_composite(names[k], (int(cxs[k] - W / n / 2), GROUND_Y + 60))
            if t > 0.3 + k * 0.25 + 1.2:
                a = _ease((t - (0.3 + k * 0.25 + 1.2)) / 0.4)
                v = vals[k].copy()
                v.putalpha(v.getchannel("A").point(lambda x, a=a: int(x * a)))
                im.alpha_composite(v, (int(cxs[k] - W / n / 2), int(GROUND_Y - hh - 160)))
        if cap is not None:
            im.alpha_composite(cap, ((W - cap.width) // 2, 1560))
        yield im


def scene_frames_deduct(ctx: Ctx, sc: dict, idx: int, seconds: float):
    from PIL import Image
    total = sc["total"]
    parts = sc["parts"]
    remain = total - sum(p["amount"] for p in parts)
    hmax, w = 620, 300
    cx_main, cx_side = 330, 790
    title = _title(ctx, f"s{idx}_title", sc["title"])
    cap = _caption_box(ctx, f"s{idx}_cap", sc.get("sub", "")) if sc.get("sub") else None
    lab_total = _label(ctx.browser, ctx.work, f"s{idx}_tot", sc.get("total_label", f"[[{total:,}]]円"), 40, w=420)
    lab_rem = _label(ctx.browser, ctx.work, f"s{idx}_rem", sc.get("remain_label", f"残り [[{remain:,}]]円"), 40, w=460)
    plabs = [_label(ctx.browser, ctx.work, f"s{idx}_p{k}", f"{p['label']}\n[[{p['amount']:,}]]円".replace("\n", "<br>"), 36, w=380) for k, p in enumerate(parts)]
    for k, p in enumerate(parts):  # 改行(<br>)を含むので、エスケープを避けて作り直す
        t = f"{html.escape(p['label'])}<br><b style=\"color:#ffc857;font-size:50px\">{p['amount']:,}円</b>"
        body = (f"<!--body--><div style=\"width:380px;text-align:center;font-weight:900;font-size:36px;line-height:1.3;"
                f"text-shadow:0 0 18px rgba(0,0,0,.7)\">{t}</div>")
        plabs[k] = Image.open(_text_png(ctx.browser, ctx.work, f"s{idx}_pp{k}", body, (380, 150), "'Noto Sans CJK JP','IPAGothic',sans-serif")).convert("RGBA")
    nframes = int(seconds * FPS)
    t_grow = 1.2
    seg = max(1.4, (seconds - t_grow - 1.0) / max(len(parts), 1))
    for f in range(nframes):
        t = f / FPS
        im = ctx.base()
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        g = _ease((t - 0.2) / t_grow)
        full_h = hmax * g
        draw_stack(layer, cx_main, GROUND_Y, w, full_h, dashed=True)           # もとの大きさの枠
        taken = 0
        side_h = 0.0
        for k, p in enumerate(parts):
            t0 = t_grow + 0.2 + k * seg
            prog = _ease((t - t0) / (seg * 0.6))
            ph = hmax * p["amount"] / total
            if prog > 0:
                taken += p["amount"]
                start_y = GROUND_Y - hmax * (total - taken) / total        # 取り分の底(もとの束の中での位置)
                end_y = GROUND_Y - side_h                                   # 横の列での底
                sx = cx_main + (cx_side - cx_main) * prog
                by = start_y + (end_y - start_y) * prog - 150 * math.sin(math.pi * prog)
                draw_stack(layer, sx, by, int(w * 0.8), ph)
            side_h += ph
        remain_h = hmax * (total - taken) / total * g if taken else full_h
        draw_stack(layer, cx_main, GROUND_Y, w, remain_h, hl=True)
        _glow(im, layer, strength=1.2)
        im.alpha_composite(title, ((W - 960) // 2, 250))
        if t > 0.2 + t_grow:
            im.alpha_composite(lab_total, (cx_main - 210, int(GROUND_Y - hmax - 150)))
        yy = GROUND_Y - 200
        for k, p in enumerate(parts):
            t0 = t_grow + 0.2 + k * seg
            if t > t0 + seg * 0.6:
                im.alpha_composite(plabs[k], (cx_side - 190, int(yy - 150 * k - 160)))
        if t > t_grow + 0.2 + len(parts) * seg:
            im.alpha_composite(lab_rem, (cx_main - 230, GROUND_Y + 70))
        if cap is not None:
            im.alpha_composite(cap, ((W - cap.width) // 2, 1560))
        yield im


def scene_frames_card(ctx: Ctx, sc: dict, idx: int, seconds: float):
    title = _title(ctx, f"s{idx}_title", sc["title"])
    lines = "".join(f"<div>{html.escape(l).replace('[[', '<b>').replace(']]', '</b>')}</div>" for l in sc.get("lines", []))
    body = (f"<!--body--><style>b{{color:#ffc857}}</style><div style=\"width:900px;text-align:center;font-weight:900;font-size:64px;line-height:1.6\">{lines}</div>")
    from PIL import Image
    txt = Image.open(_text_png(ctx.browser, ctx.work, f"s{idx}_lines", body, (900, 900), "'Noto Sans CJK JP','IPAGothic',sans-serif")).convert("RGBA")
    cap = _caption_box(ctx, f"s{idx}_cap", sc.get("sub", "")) if sc.get("sub") else None
    for f in range(int(seconds * FPS)):
        t = f / FPS
        im = ctx.base()
        im.alpha_composite(title, ((W - 960) // 2, 300))
        a = _ease(t / 0.5)
        tt = txt.copy()
        tt.putalpha(tt.getchannel("A").point(lambda x: int(x * a)))
        im.alpha_composite(tt, ((W - 900) // 2, 640))
        if cap is not None:
            im.alpha_composite(cap, ((W - cap.width) // 2, 1560))
        yield im


KINDS = {"compare": scene_frames_compare, "deduct": scene_frames_deduct, "card": scene_frames_card}


# ------------------------------------------------------------------ 全体
def make_money_reel(root: Path, run_id: str, voice: str = "auto", scene_seconds: float = 5.2) -> dict:
    root = Path(root)
    rdir = runs.run_path(root, run_id)
    out_dir = rdir / "reel_money"
    script = out_dir / "script.json"
    if not script.exists():
        raise MoneyReelError(f"台本がありません: {script}")
    data = json.loads(script.read_text(encoding="utf-8"))
    scenes = data["scenes"]
    cfg = images.load_config(root)
    browser = images.find_browser(cfg)
    ffmpeg = reels.find_ffmpeg()
    work = out_dir / "_work"
    narr = [sc.get("say", "") or reels.narration_text(sc.get("sub", "")) for sc in scenes]
    (out_dir / "narration.txt").write_text("\n".join(f"{i}. {t}" for i, t in enumerate(narr, 1)) + "\n", encoding="utf-8")
    voices, used = None, "none"
    if voice in ("auto", "voicevox") and reels.voicevox_ready():
        voices = reels.synthesize_voicevox(narr, out_dir / "_voice")
        used = "voicevox"
    elif voice == "voicevox":
        raise MoneyReelError("VOICEVOX のエンジンが見つかりません(PCで VOICEVOX を起動してから実行してください)")
    durs = [max(scene_seconds, reels.wav_seconds(v) + 1.0) for v in voices] if voices else [float(sc.get("seconds", scene_seconds)) for sc in scenes]
    ctx = Ctx(browser, work, data.get("channel", "お金のしくみ"), data.get("tag", "動くお金"))
    fdir = work / "frames"
    if fdir.exists():
        shutil.rmtree(fdir)
    fdir.mkdir(parents=True)
    n = 0
    for i, (sc, sec) in enumerate(zip(scenes, durs)):
        fn = KINDS.get(sc.get("type"))
        if fn is None:
            raise MoneyReelError(f"場面の種類が分かりません: {sc.get('type')}")
        for im in fn(ctx, sc, i, sec):
            im.convert("RGB").save(fdir / f"{n:05d}.png", compress_level=1)
            n += 1
    mp4 = out_dir / "reel.mp4"
    silent = out_dir / "_silent.mp4"
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(fdir / "%05d.png"), "-c:v", "libx264",
                    "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(silent)], check=True, timeout=1800)
    if voices:
        starts, acc = [], 0.0
        for d in durs:
            starts.append(acc)
            acc += d
        cmd = [ffmpeg, "-y", "-loglevel", "error", "-i", str(silent)]
        for v in voices:
            cmd += ["-i", str(v)]
        parts = [f"[{k + 1}:a]adelay={int((st + 0.4) * 1000)}|{int((st + 0.4) * 1000)},aformat=sample_rates=44100:channel_layouts=stereo[a{k}]" for k, st in enumerate(starts)]
        parts.append("".join(f"[a{k}]" for k in range(len(voices))) + f"amix=inputs={len(voices)}:normalize=0:duration=longest[aout]")
        cmd += ["-filter_complex", ";".join(parts), "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", str(mp4)]
        subprocess.run(cmd, check=True, timeout=900)
        silent.unlink(missing_ok=True)
    else:
        silent.replace(mp4)
    shutil.rmtree(work, ignore_errors=True)
    shutil.rmtree(out_dir / "_voice", ignore_errors=True)
    cap = data.get("caption", "").rstrip()
    if data.get("credit"):
        cap += "\n\n" + data["credit"]
    if used == "voicevox":
        cap += f"\n\nVOICEVOX:{reels.VOICEVOX_NAME}"
    (out_dir / "caption.txt").write_text(cap.strip() + "\n", encoding="utf-8")
    seconds = round(sum(durs), 1)
    log_event(root, "money_reel_made", run_id=run_id, scenes=len(scenes), seconds=seconds, voice=used)
    return {"video": mp4, "caption": out_dir / "caption.txt", "narration": out_dir / "narration.txt", "scenes": len(scenes), "seconds": seconds, "voice": used}
