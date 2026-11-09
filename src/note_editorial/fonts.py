"""見出し画像のための、日本語フォント(2026-11-09 持ち主の指示:毎回フォントを変える。ゴシック一辺倒は安っぽい)。

フォントは、npm の @fontsource/<名前>(オープンフォント。ライセンスOFL)から、必要になったときだけ取ってくる。
取ってきたものは `.fontcache/`(Gitに入れない)に置く。画像に使う文字を含む部分(スライス)だけを、HTMLに埋め込む。
ネットワークが使えない環境では、フォントが無いので、`fallback`(標準のゴシック)になる(画像は作れる)。
"""
from __future__ import annotations

import base64
import re
import subprocess
import tarfile
from pathlib import Path

CACHE = Path(".fontcache")

# key: (npmの名前, CSSのfont-family, 太さ)
PRESETS = {
    "mincho": ("shippori-mincho", "Shippori Mincho", 800),   # 上品な明朝
    "maru": ("zen-maru-gothic", "Zen Maru Gothic", 900),     # やわらかい丸ゴシック
    "dela": ("dela-gothic-one", "Dela Gothic One", 400),     # 太い見出し用(ポップ)
    "antique": ("zen-antique", "Zen Antique", 400),          # 古風・重厚
    "kaisei": ("kaisei-decol", "Kaisei Decol", 700),         # 個性のある書体
    "tegomin": ("new-tegomin", "New Tegomin", 400),          # 手書き風の明朝
    # 2026-11-09 「明朝・古風は高貴すぎる」との指摘。表紙は、親しみのあるポップで力強い書体だけを使う
    "rocknroll": ("rocknroll-one", "RocknRoll One", 400),
    "reggae": ("reggae-one", "Reggae One", 400),
    "mochiy": ("mochiy-pop-one", "Mochiy Pop One", 400),
    "potta": ("potta-one", "Potta One", 400),
}


def _pkg_dir(pkg: str) -> Path | None:
    d = CACHE / pkg / "package"
    if d.exists():
        return d
    CACHE.mkdir(exist_ok=True)
    try:
        r = subprocess.run(["npm", "pack", f"@fontsource/{pkg}", "--pack-destination", str(CACHE)],
                           capture_output=True, text=True, timeout=180)
        tgz = next(CACHE.glob(f"fontsource-{pkg}-*.tgz"), None)
        if not tgz:
            return None
        (CACHE / pkg).mkdir(exist_ok=True)
        with tarfile.open(tgz) as t:
            t.extractall(CACHE / pkg)
        tgz.unlink(missing_ok=True)
    except (OSError, subprocess.TimeoutExpired, tarfile.TarError):
        return None
    return d if d.exists() else None


def _ranges(spec: str):
    for part in spec.split(","):
        part = part.strip().lstrip("Uu+")
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-")
            yield int(a, 16), int(b, 16)
        else:
            yield int(part, 16), int(part, 16)


def font_css(key: str, text: str) -> tuple[str, str]:
    """(埋め込み用の @font-face のCSS, font-family の指定) を返す。取れなければ ("", 標準ゴシック)。"""
    fallback = "'Noto Sans CJK JP','IPAGothic',sans-serif"
    if key not in PRESETS:
        return "", fallback
    pkg, family, weight = PRESETS[key]
    d = _pkg_dir(pkg)
    if d is None:
        return "", fallback
    css_file = d / f"{weight}.css"
    if not css_file.exists():
        return "", fallback
    chars = {ord(c) for c in text} | {ord(c) for c in "0123456789,.:%円万!?"}
    out = []
    for m in re.finditer(r"@font-face\s*\{(.*?)\}", css_file.read_text(encoding="utf-8"), flags=re.S):
        body = m.group(1)
        ur = re.search(r"unicode-range:\s*([^;]+);", body)
        src = re.search(r"url\(\./(files/[^)]+\.woff2)\)", body)
        if not ur or not src:
            continue
        if not any(a <= c <= b for a, b in _ranges(ur.group(1)) for c in chars):
            continue
        data = base64.b64encode((d / src.group(1)).read_bytes()).decode("ascii")
        out.append(f"@font-face{{font-family:'{family}';font-weight:{weight};src:url(data:font/woff2;base64,{data}) format('woff2');unicode-range:{ur.group(1).strip()}}}")
    if not out:
        return "", fallback
    return "<style>" + "".join(out) + "</style>", f"'{family}',{fallback}"
