"""画像の自動作成(AI画像生成は使わない)。

文字入りのカードをHTMLで描き、ブラウザ(Chrome/Edge)のスクリーンショットで画像にする。
- APIキーも追加費用も不要。著作権・肖像権の心配がある「AI生成の人物画像」も使わない。
- 作るもの: note見出し画像(1280x670) / Instagramカルーセル(1080x1350)
- 文言はすべて、承認済みの記事とSNS案から取る(画像のために文章を新しく作らない)。
"""
from __future__ import annotations

import glob
import html
import os
import re
import shutil
import subprocess
from pathlib import Path

from . import artifacts, runs
from .log import log_event

EYECATCH_SIZE = (1280, 670)
SLIDE_SIZE = (1080, 1350)
SLIDE_RE = re.compile(r"^\s*(?:[-*]\s*)?\**\s*(\d+)\s*枚目\s*[::]\s*(.*?)\**\s*$", re.M)

DEFAULTS = {
    "colors": {"background": "#0f2a43", "accent": "#ffb400", "text": "#ffffff", "subtext": "#b8c7d9"},
    "font_family": "'Noto Sans JP','Noto Sans CJK JP','Yu Gothic','Meiryo','IPAGothic',sans-serif",
    "footer": "",
    "browser_path": "",
}


class ImageError(Exception):
    pass


def load_config(root: Path) -> dict:
    path = Path(root) / "config" / "images.yaml"
    user = runs._read_yaml(path) if path.exists() else {}
    cfg = {**DEFAULTS, **{k: v for k, v in user.items() if k != "colors"}}
    cfg["colors"] = {**DEFAULTS["colors"], **(user.get("colors") or {})}
    return cfg


def find_browser(cfg: dict) -> str:
    candidates = [cfg.get("browser_path"), os.environ.get("CHROMIUM_PATH")]
    candidates += glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome")
    candidates += [shutil.which(n) for n in ("google-chrome", "chromium", "chromium-browser", "chrome", "msedge")]
    candidates += [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                   r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                   r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]
    for c in candidates:
        if c and Path(c).exists():
            return str(c)
    raise ImageError("画像を作るブラウザ(Chrome か Edge)が見つかりません。config/images.yaml の browser_path に実行ファイルのパスを書いてください")


def slides_from_sns(sns_text: str) -> list[str]:
    block = artifacts.section(sns_text, "Instagram投稿案") or ""
    found = {int(n): t.replace(artifacts.LINK_TOKEN, "").strip() for n, t in SLIDE_RE.findall(block)}
    found = {n: t for n, t in found.items() if t}  # URLは画像に載せない(投稿時に別途貼る)
    return [found[k] for k in sorted(found)]


def split_title(title: str) -> tuple[str, str]:
    """「。」で主題と補足に分ける(見出し画像で大きさを変えるため)。"""
    main, sep, rest = title.partition("。")
    return (main + sep, rest.strip()) if rest.strip() else (title, "")


def _size_for(text: str, large: int, step: int) -> int:
    n = len(text)
    return large if n <= 14 else large - step if n <= 24 else large - 2 * step if n <= 38 else large - 3 * step


def _page(cfg: dict, w: int, h: int, inner: str) -> str:
    c = cfg["colors"]
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;width:{w}px;height:{h}px;background:{c['background']};color:{c['text']};
font-family:{cfg['font_family']};overflow:hidden}}
.frame{{box-sizing:border-box;width:{w}px;height:{h}px;padding:72px;display:flex;flex-direction:column;justify-content:center;position:relative}}
.bar{{width:120px;height:10px;background:{c['accent']};margin-bottom:40px}}
.main{{font-weight:700;line-height:1.35;word-break:keep-all;overflow-wrap:anywhere}} .sub{{color:{c['subtext']};line-height:1.5;margin-top:28px}}
.num{{position:absolute;top:56px;right:72px;color:{c['accent']};font-size:34px;font-weight:700}}
.foot{{position:absolute;bottom:48px;left:72px;color:{c['subtext']};font-size:28px}}
</style></head><body>{inner}</body></html>"""


_BREAK_AFTER = re.compile(r"([、。,.!?!?:：)）」』】])")
_BREAK_BEFORE = re.compile(r"([(（「『【])")


def _esc(text: str) -> str:
    """HTMLに安全な文字へ変換し、句読点・括弧の位置にだけ改行候補(<wbr>)を入れる(単語の途中で切れにくくする)。"""
    safe = html.escape(text)
    safe = _BREAK_AFTER.sub(r"\1<wbr>", safe)
    safe = _BREAK_BEFORE.sub(r"<wbr>\1", safe)
    return safe.replace("\n", "<br>")


def eyecatch_html(title: str, cfg: dict) -> str:
    main, sub = split_title(title)
    foot = f'<div class="foot">{_esc(cfg["footer"])}</div>' if cfg.get("footer") else ""
    inner = (f'<div class="frame"><div class="bar"></div>'
             f'<div class="main" style="font-size:{_size_for(main, 76, 8)}px">{_esc(main)}</div>'
             + (f'<div class="sub" style="font-size:34px">{_esc(sub)}</div>' if sub else "")
             + f"{foot}</div>")
    return _page(cfg, *EYECATCH_SIZE, inner)


def slide_html(index: int, total: int, text: str, cfg: dict) -> str:
    foot = f'<div class="foot">{_esc(cfg["footer"])}</div>' if cfg.get("footer") else ""
    inner = (f'<div class="frame"><div class="num">{index} / {total}</div><div class="bar"></div>'
             f'<div class="main" style="font-size:{_size_for(text, 84, 9)}px">{_esc(text)}</div>{foot}</div>')
    return _page(cfg, *SLIDE_SIZE, inner)


def render(html_text: str, out: Path, size: tuple[int, int], browser: str, work: Path) -> None:
    work.mkdir(parents=True, exist_ok=True)
    src = work / (out.stem + ".html")
    src.write_text(html_text, encoding="utf-8")
    cmd = [browser, "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
           f"--screenshot={out}", f"--window-size={size[0]},{size[1]}", src.resolve().as_uri()]
    try:
        subprocess.run(cmd, capture_output=True, timeout=90, check=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise ImageError(f"画像の作成に失敗しました({out.name}): {e}") from e
    if not out.exists() or out.stat().st_size == 0:
        raise ImageError(f"画像ができませんでした: {out.name}")
    src.unlink(missing_ok=True)


def png_size(path: Path) -> tuple[int, int]:
    import struct
    head = Path(path).read_bytes()[:24]
    return struct.unpack(">II", head[16:24])


def article_title(text: str) -> str:
    m = re.search(r"^#\s+(.+)$", text, re.M)
    if not m:
        raise ImageError("記事タイトル(# …)が見つかりません")
    return m.group(1).strip()


def make_images(root: Path, run_id: str) -> list[Path]:
    root = Path(root)
    data = runs.read_run(root, run_id)
    if "revised" not in data["steps_done"]:
        raise ImageError("修正版(05_revised.md)が完了してから作ってください")
    rdir = runs.run_path(root, run_id)
    cfg = load_config(root)
    browser = find_browser(cfg)
    out_dir = rdir / "images"
    out_dir.mkdir(exist_ok=True)
    made = []
    title = article_title((rdir / artifacts.FILES["revised"]).read_text(encoding="utf-8"))
    path = out_dir / "note_eyecatch.png"
    render(eyecatch_html(title, cfg), path, EYECATCH_SIZE, browser, out_dir / "_work")
    made.append(path)
    if "sns" in data["steps_done"]:
        slides = slides_from_sns((rdir / artifacts.FILES["sns"]).read_text(encoding="utf-8"))
        for i, text in enumerate(slides, 1):
            path = out_dir / f"instagram_{i:02d}.png"
            render(slide_html(i, len(slides), text, cfg), path, SLIDE_SIZE, browser, out_dir / "_work")
            made.append(path)
    shutil.rmtree(out_dir / "_work", ignore_errors=True)
    log_event(root, "images_made", run_id=run_id, count=len(made))
    return made
