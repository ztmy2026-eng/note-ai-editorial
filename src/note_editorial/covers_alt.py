"""見出し画像の、スライドっぽくない別デザイン(2026-11-05 持ち主の指示:パワポ風をやめ、絵・イラストで)。
cover の style に書く: scene(イラストの場面)| burst(マンガの集中線と大きな数字)| memo(ノートとふせん)| poster(暗い地に光る大きな数字)
どれも 1280x670。文字は少なく、絵を大きく。数字(big)は、記事で確認済みのものだけを書く。"""
from __future__ import annotations

import html
import math
import re

NAVY = "#16233f"


def _title(s, em_css, b_css="color:#d62f1f"):
    t = s["title_html"]
    return t.replace("<em>", f'<span style="{em_css}">').replace("</em>", "</span>").replace("<b>", f'<span style="{b_css}">').replace("</b>", "</span>")


def _plain(t):
    return re.sub(r"<[^>]+>", "", t)


def _big(s):
    if s.get("big"):
        return str(s["big"])
    m = re.search(r"<b>(.*?)</b>", s["title_html"])
    return _plain(m.group(1)) if m else ""


def _scale(ill, w, h):
    return ill.replace('width="400" height="420"', f'width="{w}" height="{h}"')


def _sparkles(pts, color="#fff"):
    out = ""
    for x, y, r in pts:
        d = f"M{x},{y-r} Q{x},{y} {x+r},{y} Q{x},{y} {x},{y+r} Q{x},{y} {x-r},{y} Q{x},{y} {x},{y-r}Z"
        out += f'<path d="{d}" fill="{color}"/>'
    return f'<svg style="position:absolute;left:0;top:0" width="1280" height="670">{out}</svg>'


def _coins(pts):
    out = ""
    for x, y, r in pts:
        out += (f'<circle cx="{x}" cy="{y}" r="{r}" fill="#ffc233" stroke="#b97a00" stroke-width="5"/>'
                f'<circle cx="{x}" cy="{y}" r="{r*0.66}" fill="none" stroke="#b97a00" stroke-width="3"/>'
                f'<text x="{x}" y="{y+r*0.3}" font-size="{r*0.9}" font-weight="900" text-anchor="middle" fill="#b97a00">¥</text>')
    return f'<svg style="position:absolute;left:0;top:0" width="1280" height="670">{out}</svg>'


def scene(s, ill):
    """空と丸い雲、地面。大きな絵と、ふきだしのタイトル。"""
    title = _title(s, "background:linear-gradient(transparent 58%,#ffe066 58%);font-style:normal")
    clouds = ('<svg style="position:absolute;left:0;top:0" width="1280" height="670">'
              '<g fill="#fff" opacity=".9"><ellipse cx="980" cy="110" rx="110" ry="34"/><ellipse cx="1050" cy="92" rx="70" ry="38"/>'
              '<ellipse cx="170" cy="600" rx="0" ry="0"/><ellipse cx="1180" cy="250" rx="70" ry="22"/></g>'
              '<path d="M0,560 Q320,500 640,560 T1280,540 L1280,670 L0,670Z" fill="#7fd1a0"/>'
              '<path d="M0,610 Q380,560 760,615 T1280,600 L1280,670 L0,670Z" fill="#5bbd86"/></svg>')
    return f"""<div class="fig" id="t" style="width:1280px;height:670px;padding:0;position:relative;overflow:hidden;background:linear-gradient(#8fd3ff,#d9f1ff);color:{NAVY}">
{clouds}{_sparkles([(820,150,22),(1190,420,18),(700,420,14)],"#fff")}
<div style="position:absolute;right:30px;top:100px;width:520px;height:546px;filter:drop-shadow(0 18px 18px rgba(20,60,100,.3))">{_scale(ill,520,546)}</div>
<div style="position:absolute;left:50px;top:90px;width:740px;background:#fff;border:6px solid {NAVY};border-radius:44px;padding:36px 40px 40px;box-shadow:10px 12px 0 rgba(22,35,63,.25)">
<div style="font-size:{s.get('size',46)}px;font-weight:900;line-height:1.4">{title}</div></div>
<svg style="position:absolute;left:520px;top:352px" width="120" height="90"><path d="M10,0 L110,0 L40,80Z" fill="#fff" stroke="{NAVY}" stroke-width="6" stroke-linejoin="round"/><path d="M16,-4 L104,-4 L100,4 L20,4Z" fill="#fff"/></svg>
<div style="position:absolute;left:64px;bottom:30px;font-size:24px;font-weight:700;color:{NAVY};background:#ffffffcc;padding:4px 16px;border-radius:20px">人生最適化中の会社員</div></div>"""


def burst(s, ill):
    """マンガ風。集中線とドット、ギザギザの吹き出しに大きな数字。"""
    big = _big(s)
    cx, cy = 960, 340
    rays = ""
    for i in range(36):
        a0 = i * 10 * math.pi / 180
        a1 = (i * 10 + 4.5) * math.pi / 180
        R = 1000
        rays += f'<path d="M{cx},{cy} L{cx+R*math.cos(a0):.0f},{cy+R*math.sin(a0):.0f} L{cx+R*math.cos(a1):.0f},{cy+R*math.sin(a1):.0f}Z" fill="#fff" opacity=".55"/>'
    pts = []
    for i in range(32):
        r = 270 if i % 2 == 0 else 205
        a = i * math.pi / 16
        pts.append(f"{cx+r*math.cos(a):.0f},{cy+r*math.sin(a):.0f}")
    star = f'<polygon points="{" ".join(pts)}" fill="#e8372a" stroke="{NAVY}" stroke-width="8" stroke-linejoin="round"/>'
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="5" fill="#ff9d1c" opacity=".55"/>' for x in range(20, 1280, 40) for y in range(20, 670, 40) if x < 380 and y > 380)
    title = _title(s, f"background:{NAVY};color:#ffe066;font-style:normal;padding:0 .1em;border-radius:6px;-webkit-box-decoration-break:clone;box-decoration-break:clone", "color:#e8372a")
    bigsize = 110 if len(big) <= 5 else 70 if len(big) <= 8 else 56
    return f"""<div class="fig" id="t" style="width:1280px;height:670px;padding:0;position:relative;overflow:hidden;background:#ffd43b;color:{NAVY}">
<svg style="position:absolute;left:0;top:0" width="1280" height="670">{rays}{dots}{star}</svg>
<div style="position:absolute;left:{cx-210}px;top:{cy-80}px;width:420px;text-align:center;transform:rotate(-6deg);font-weight:900;color:#fff;line-height:1.05;text-shadow:-4px -4px 0 {NAVY},4px -4px 0 {NAVY},-4px 4px 0 {NAVY},4px 4px 0 {NAVY},0 6px 0 {NAVY}">
<div style="font-size:{bigsize}px">{html.escape(big)}</div><div style="font-size:44px;margin-top:6px;color:#ffe066">{html.escape(s.get('bigsub',''))}</div></div>
<div style="position:absolute;left:34px;top:60px;width:610px;background:#fff;border:6px solid {NAVY};border-radius:18px;padding:26px 32px;transform:rotate(-2deg);box-shadow:9px 10px 0 {NAVY}">
<div style="font-size:{s.get('size',42)}px;font-weight:900;line-height:1.4">{title}</div></div>
<div style="position:absolute;left:60px;bottom:24px;width:230px;height:231px;transform:rotate(-4deg)"><div style="width:400px;height:420px;transform:scale(.55);transform-origin:0 0">{ill}</div></div>
<div style="position:absolute;right:30px;bottom:22px;font-size:24px;font-weight:700">人生最適化中の会社員</div></div>"""


def memo(s, ill):
    """机の上のノート。マスキングテープ、マーカー、ふせん、鉛筆。"""
    big = _big(s)
    title = _title(s, "background:linear-gradient(transparent 52%,#ffe066 52%);font-style:normal", "color:#d62f1f;background:linear-gradient(transparent 60%,#ffd1cb 60%)")
    lines = "".join(f'<div style="position:absolute;left:0;right:0;top:{y}px;height:2px;background:#cfe0f4"></div>' for y in range(60, 520, 54))
    return f"""<div class="fig" id="t" style="width:1280px;height:670px;padding:0;position:relative;overflow:hidden;background:#d9b384;
background-image:repeating-linear-gradient(90deg,rgba(120,70,20,.07) 0 3px,transparent 3px 46px);color:{NAVY}">
<div style="position:absolute;left:70px;top:44px;width:830px;height:540px;background:#fffdf5;border-radius:10px;transform:rotate(-1.6deg);box-shadow:0 16px 28px rgba(70,40,10,.38);overflow:hidden">
{lines}<div style="position:absolute;left:68px;top:0;bottom:0;width:3px;background:#f0a0a0"></div>
<div style="position:absolute;left:100px;top:34px;width:700px"><div style="font-size:23px;font-weight:700;color:#6b7280;margin-bottom:6px">メモ:{html.escape(s['tag'])}</div>
<div style="font-size:{s.get('size',60)}px;font-weight:900;line-height:1.55">{title}</div></div></div>
<div style="position:absolute;left:330px;top:18px;width:200px;height:50px;background:rgba(255,120,120,.7);transform:rotate(-4deg)"></div>
<div style="position:absolute;right:48px;top:70px;width:340px;height:340px;background:#ffe45c;transform:rotate(4deg);box-shadow:0 12px 20px rgba(70,40,10,.35);padding:22px 20px;text-align:center">
<div style="font-size:26px;font-weight:900">{html.escape(s.get('bigsub','ポイント'))}</div>
<div style="font-size:{86 if len(big)<=6 else 60}px;font-weight:900;color:#d62f1f;line-height:1.1;margin-top:34px">{html.escape(big)}</div></div>
<div style="position:absolute;right:70px;bottom:36px;width:300px;height:315px;transform:rotate(-6deg);filter:drop-shadow(0 10px 12px rgba(70,40,10,.4))">{_scale(ill,300,315)}</div>
<svg style="position:absolute;left:560px;bottom:20px" width="360" height="60"><g transform="rotate(-6 180 30)"><rect x="10" y="20" width="270" height="22" rx="4" fill="#f5a623" stroke="{NAVY}" stroke-width="3"/><polygon points="280,20 340,31 280,42" fill="#f3d9b1" stroke="{NAVY}" stroke-width="3"/><polygon points="322,28 340,31 322,34" fill="{NAVY}"/><rect x="10" y="20" width="36" height="22" rx="4" fill="#e88"/></g></svg>
</div>"""


def poster(s, ill):
    """夜空のような濃い紺に、光る絵と大きな数字(映画ポスター風)。"""
    big = _big(s)
    title = _title(s, "color:#ffd43b;font-style:normal", "color:#ffd43b")
    stars = "".join(f'<circle cx="{(i*197)%1280}" cy="{(i*113)%670}" r="{1.5+(i%3)}" fill="#fff" opacity="{.4+(i%4)*.15}"/>' for i in range(60))
    return f"""<div class="fig" id="t" style="width:1280px;height:670px;padding:0;position:relative;overflow:hidden;background:radial-gradient(circle at 76% 48%,#2f4a8a 0%,#16233f 55%,#0b1226 100%);color:#fff">
<svg style="position:absolute;left:0;top:0" width="1280" height="670">{stars}<circle cx="960" cy="330" r="250" fill="#ffd43b" opacity=".13"/><circle cx="960" cy="330" r="180" fill="#ffd43b" opacity=".16"/></svg>
{_coins([(700,120,26),(1210,150,22),(1150,560,30),(640,590,20)])}
<div style="position:absolute;right:90px;top:90px;width:460px;height:483px;filter:drop-shadow(0 0 40px rgba(255,212,59,.6))">{_scale(ill,460,483)}</div>
<div style="position:absolute;left:64px;top:60px;font-size:26px;font-weight:700;letter-spacing:.2em;color:#ffd43b">{html.escape(s['tag'])}</div>
<div style="position:absolute;left:64px;top:118px;width:640px;font-size:{s.get('size',52)}px;font-weight:900;line-height:1.38">{title}</div>
<div style="position:absolute;left:64px;bottom:60px;font-size:{150 if len(big)<=5 else 110 if len(big)<=8 else 80}px;font-weight:900;color:#ffd43b;line-height:1;text-shadow:0 0 30px rgba(255,212,59,.55)">{html.escape(big)}</div>
<div style="position:absolute;left:64px;bottom:22px;font-size:22px;color:#9fb0d0">人生最適化中の会社員</div></div>"""


def _vis_len(text):
    return sum(0.58 if ord(c) < 0x2000 else 1.0 for c in text)


def pachi(s, ill):
    """パチンコ演出風(2026-11-09 持ち主の参考画像のような、派手なデザイン)。人物は使わない。
    紫〜ピンクの光る背景・キラキラ・太い縁取りの金色/ピンクの特大文字・金貨。参考画像の人物・配置・形はそのまま真似しない。"""
    raw = s["title_html"]
    lines = [x for x in re.split(r"<br\s*/?>", raw) if _plain(x).strip()]
    has_b = [("<b>" in x) for x in lines]
    if not any(has_b):
        has_b[-1] = True
    plain = [_plain(x).strip() for x in lines]
    W, H = 760, 520
    sizes = [min(120, W / max(_vis_len(x), 1)) for x in plain]
    tot = sum(sizes) * 1.18
    k = min(1.0, H / tot)
    sizes = [max(40, int(z * k)) for z in sizes]
    top = 96 + max(0, int((H - sum(sizes) * 1.2) / 2))
    rows = ""
    for x, z, pink in zip(plain, sizes, has_b):
        grad = "linear-gradient(#fff6a8 0%,#ffd21f 45%,#ff9a00 100%)" if not pink else "linear-gradient(#ffd6fb 0%,#ff5ce1 45%,#c2189f 100%)"
        glow = "0 0 22px #ffb300" if not pink else "0 0 26px #ff2bd6"
        rows += (f'<div style="position:relative;line-height:1.16;margin:0 0 2px 0;font-size:{z}px;font-weight:900;white-space:nowrap;letter-spacing:.01em">'
                 f'<span style="-webkit-text-stroke:{max(12, z // 6)}px #14000f;color:#14000f;text-shadow:{glow}">{html.escape(x)}</span>'
                 f'<span style="position:absolute;left:0;top:0;background:{grad};-webkit-background-clip:text;background-clip:text;color:transparent;'
                 f'-webkit-text-stroke:2px #fff7;filter:drop-shadow(0 3px 0 #0006)">{html.escape(x)}</span></div>')
    # キラキラ(決まった配置)
    sp = []
    import random
    rnd = random.Random(7)
    for i in range(46):
        sp.append((rnd.randint(10, 1270), rnd.randint(10, 660), rnd.choice([6, 8, 10, 14, 20, 28])))
    stars = _sparkles(sp, "#fff")
    bokeh = "".join(f'<circle cx="{rnd.randint(0,1280)}" cy="{rnd.randint(0,670)}" r="{rnd.randint(10,46)}" fill="#ffffff" opacity="{rnd.choice([.06,.09,.12])}"/>' for _ in range(22))
    coins = _coins([(1010, 150, 70), (1150, 300, 56), (930, 420, 62), (1090, 470, 84), (1200, 590, 44), (860, 580, 40)])
    tag = (f'<div style="position:absolute;left:44px;top:36px;background:#ff3fd1;color:#fff;font-weight:900;font-size:26px;padding:6px 22px;'
           f'border-radius:30px;border:4px solid #14000f;box-shadow:0 0 18px #ff3fd1">{html.escape(s["tag"])}</div>')
    return f"""<div class="fig" id="t" style="width:1280px;height:670px;padding:0;position:relative;overflow:hidden;color:#fff;
background:radial-gradient(circle at 72% 42%,#ff58dc 0%,#b0179f 30%,#58087a 62%,#1c0430 100%)">
<svg style="position:absolute;left:0;top:0" width="1280" height="670">{bokeh}</svg>
{stars}{coins}{tag}
<div style="position:absolute;left:44px;top:{top}px;transform:rotate(-3deg);transform-origin:0 0">{rows}</div>
<div style="position:absolute;right:24px;bottom:16px;font-size:22px;font-weight:700;color:#ffd7f7;text-shadow:0 0 8px #14000f">人生最適化中の会社員</div></div>"""


# ---- 2026-11-09: 落ち着いた上質なデザイン。フォントは毎回変える(fonts.py)。斜め配置・太い縁取り・どぎつい色はやめる ----
THEMES = {
    "mincho": dict(font="mincho", bg="linear-gradient(135deg,#f7f0e1,#efe4cc)", ink="#14213d", accent="#b8321f", sub="#6b5b3e", frame="#14213d"),
    "maru": dict(font="maru", bg="linear-gradient(135deg,#e6f6ef,#d3eee3)", ink="#0e3b3a", accent="#e8590c", sub="#3d6b66", frame="#0e3b3a"),
    "dela": dict(font="dela", bg="#ffd23f", ink="#141414", accent="#141414", sub="#141414", frame="#141414"),
    "antique": dict(font="antique", bg="radial-gradient(circle at 70% 35%,#1d3557,#0c1626 70%)", ink="#f3e7c8", accent="#e9c46a", sub="#bda66a", frame="#c9a94f"),
}


def _plain_lines(s):
    lines = [x for x in re.split(r"<br\s*/?>", s["title_html"]) if _plain(x).strip()]
    return lines


def premium(s, ill, theme):
    from .fonts import font_css
    th = THEMES[theme]
    lines = _plain_lines(s)
    hot = [("<b>" in x or "<em>" in x) for x in lines]
    if not any(hot):
        hot[-1] = True
    plain = [_plain(x).strip() for x in lines]
    css, family = font_css(th["font"], "".join(plain) + s["tag"] + "人生最適化中の会社員")
    W, H = 640, 370
    sizes = [min(104, W / max(_vis_len(x), 1)) for x in plain]
    k = min(1.0, H / (sum(sizes) * 1.3))
    sizes = [max(38, int(z * k)) for z in sizes]
    rows = ""
    for x, z, h in zip(plain, sizes, hot):
        if theme == "dela":
            st = f"background:{th['ink']};color:{th['bg']};padding:.02em .18em;display:inline-block;" if h else f"color:{th['ink']};"
        elif theme == "maru":
            st = (f"color:{th['ink']};background:linear-gradient(transparent 58%,#ffd43b 58%);" if h else f"color:{th['ink']};")
        else:
            st = f"color:{th['accent']};" if h else f"color:{th['ink']};"
        bigger = int(z * 1.12) if h else z
        rows += f'<div style="font-size:{bigger}px;line-height:1.26;letter-spacing:.03em;white-space:nowrap"><span style="{st}">{html.escape(x)}</span></div>'
    if theme == "antique":
        frame = (f'<div style="position:absolute;inset:26px;border:1.5px solid {th["frame"]}"></div>'
                 f'<div style="position:absolute;inset:36px;border:1px solid {th["frame"]}88"></div>')
    elif theme == "mincho":
        frame = (f'<div style="position:absolute;inset:28px;border:2px solid {th["frame"]}"></div>')
    elif theme == "dela":
        frame = ""
    else:
        frame = ""
    if theme == "maru":
        deco = ('<div style="position:absolute;right:-90px;top:-110px;width:470px;height:470px;border-radius:50%;background:#ffffff88"></div>'
                '<div style="position:absolute;left:-120px;bottom:-160px;width:420px;height:420px;border-radius:50%;background:#ffffff66"></div>')
    else:
        deco = ""
    if theme == "dela":
        iconbox = f'<div style="position:absolute;right:70px;top:150px;width:360px;height:360px;border-radius:50%;background:{th["ink"]};overflow:hidden;box-shadow:12px 12px 0 #ffffff99"><div style="transform:scale(.72);transform-origin:50% 50%;margin:20px 0 0 14px">{ill}</div></div>'
    elif theme == "antique":
        iconbox = f'<div style="position:absolute;right:92px;top:160px;width:340px;height:340px;border-radius:50%;border:2px solid {th["frame"]};background:#ffffff0d;overflow:hidden"><div style="transform:scale(.7);transform-origin:50% 50%;margin:30px 0 0 14px">{ill}</div></div>'
    elif theme == "mincho":
        iconbox = f'<div style="position:absolute;right:96px;top:170px;width:320px;height:320px;border-radius:50%;background:{th["ink"]};overflow:hidden"><div style="transform:scale(.68);transform-origin:50% 50%;margin:34px 0 0 14px">{ill}</div></div>'
    else:
        iconbox = f'<div style="position:absolute;right:84px;top:160px;width:340px;height:340px;border-radius:44px;background:#fff;box-shadow:0 18px 40px rgba(14,59,58,.18);overflow:hidden"><div style="background:{th["ink"]};width:100%;height:100%;padding:34px 0 0 14px;box-sizing:border-box"><div style="transform:scale(.7);transform-origin:50% 50%">{ill}</div></div></div>'
    tag_bg = {"mincho": th["ink"], "maru": th["ink"], "dela": th["ink"], "antique": "transparent"}[theme]
    tag_col = {"mincho": "#f7f0e1", "maru": "#fff", "dela": th["bg"], "antique": th["accent"]}[theme]
    tag_border = f"1.5px solid {th['accent']}" if theme == "antique" else "none"
    tag = (f'<div style="display:inline-block;background:{tag_bg};color:{tag_col};border:{tag_border};font-size:25px;letter-spacing:.14em;'
           f'padding:7px 22px;border-radius:{30 if theme=="maru" else 2}px">{html.escape(s["tag"])}</div>')
    return f"""{css}<div class="fig" id="t" style="width:1280px;height:670px;padding:0;position:relative;overflow:hidden;background:{th['bg']};color:{th['ink']};font-family:{family}">
{deco}{frame}{iconbox}
<div style="position:absolute;left:78px;top:70px">{tag}</div>
<div style="position:absolute;left:78px;top:150px">{rows}</div>
<div style="position:absolute;left:78px;bottom:54px;font-size:22px;letter-spacing:.12em;color:{th['sub']}">人生最適化中の会社員</div></div>"""


def mincho(s, ill):
    return premium(s, ill, "mincho")


def maru(s, ill):
    return premium(s, ill, "maru")


def dela(s, ill):
    return premium(s, ill, "dela")


def antique(s, ill):
    return premium(s, ill, "antique")


# ---- 2026-11-09: 自然の背景(夜空・青空・海・森)。noteでは表紙が小さいので、文字は大きく太く。絵は、SVGフィルターで描いたCG(写真ではない) ----
def _noise(rnd, n):
    return [rnd.random() for _ in range(n)]


def _scene_night(rnd):
    stars = ""
    for _ in range(260):
        x, y = rnd.randint(0, 1280), rnd.randint(0, 520)
        r = rnd.choice([.6, .8, 1, 1, 1.3, 1.6])
        stars += f'<circle cx="{x}" cy="{y}" r="{r}" fill="#fff" opacity="{rnd.uniform(.35,.95):.2f}"/>'
    bright = ""
    for _ in range(14):
        x, y = rnd.randint(40, 1240), rnd.randint(20, 420)
        bright += f'<circle cx="{x}" cy="{y}" r="2.2" fill="#fff"/><circle cx="{x}" cy="{y}" r="7" fill="#cfe3ff" opacity=".25"/>'
    pts, x, y = [], 0, 600
    for i in range(0, 1300, 20):
        y = max(560, min(640, y + rnd.randint(-14, 14)))
        pts.append(f"{i},{y}")
    mount = "0,670 " + " ".join(pts) + " 1280,670"
    return f"""<defs>
<linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#01030a"/><stop offset=".55" stop-color="#071634"/><stop offset=".9" stop-color="#1b3868"/><stop offset="1" stop-color="#2b4a7e"/></linearGradient>
<filter id="mw" x="-20%" y="-20%" width="140%" height="140%"><feTurbulence type="fractalNoise" baseFrequency=".006 .018" numOctaves="5" seed="4" result="n"/>
<feColorMatrix in="n" type="matrix" values="0 0 0 0 .78  0 0 0 0 .86  0 0 0 0 1  0 0 0 2.6 -.95"/><feGaussianBlur stdDeviation="3"/></filter>
<linearGradient id="band" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity="1"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<mask id="bm"><rect x="-200" y="-100" width="1700" height="900" fill="url(#band)" transform="rotate(-24 640 335)"/></mask>
<radialGradient id="glow" cx=".72" cy="1" r=".6"><stop offset="0" stop-color="#6f8fd6" stop-opacity=".55"/><stop offset="1" stop-color="#6f8fd6" stop-opacity="0"/></radialGradient></defs>
<rect width="1280" height="670" fill="url(#g)"/>
<rect width="1280" height="670" filter="url(#mw)" mask="url(#bm)" opacity=".85"/>
<rect width="1280" height="670" fill="url(#glow)"/>{stars}{bright}
<polygon points="{mount}" fill="#02050c"/>"""


def _scene_sky(rnd):
    return """<defs>
<linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0b5cc4"/><stop offset=".55" stop-color="#3e92e0"/><stop offset="1" stop-color="#bfe3fb"/></linearGradient>
<filter id="c1" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".007 .012" numOctaves="6" seed="11" result="n"/>
<feColorMatrix in="n" type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 6 -2.6"/><feGaussianBlur stdDeviation="1.4"/></filter>
<filter id="c2" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".011 .02" numOctaves="6" seed="23" result="n"/>
<feColorMatrix in="n" type="matrix" values="0 0 0 0 .93  0 0 0 0 .96  0 0 0 0 1  0 0 0 5 -2.3"/><feGaussianBlur stdDeviation="1"/></filter>
<linearGradient id="m" x1="0" y1="0" x2="0" y2="1"><stop offset=".25" stop-color="#fff" stop-opacity="0"/><stop offset=".7" stop-color="#fff" stop-opacity="1"/></linearGradient>
<mask id="mk"><rect width="1280" height="670" fill="url(#m)"/></mask>
<radialGradient id="sun" cx=".85" cy=".1" r=".5"><stop offset="0" stop-color="#fff" stop-opacity=".55"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient></defs>
<rect width="1280" height="670" fill="url(#g)"/><rect width="1280" height="670" fill="url(#sun)"/>
<rect width="1280" height="670" filter="url(#c2)" mask="url(#mk)" opacity=".75"/>
<rect width="1280" height="670" filter="url(#c1)" mask="url(#mk)" opacity=".95"/>"""


def _scene_sea(rnd):
    return """<defs>
<linearGradient id="sk" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2a3f7a"/><stop offset=".45" stop-color="#e0719a"/><stop offset=".8" stop-color="#ffb877"/><stop offset="1" stop-color="#ffe0a8"/></linearGradient>
<linearGradient id="sea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#d98a73"/><stop offset=".12" stop-color="#4a5f8e"/><stop offset=".6" stop-color="#16345f"/><stop offset="1" stop-color="#0a1c38"/></linearGradient>
<filter id="w" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".004 .09" numOctaves="4" seed="9" result="n"/>
<feColorMatrix in="n" type="matrix" values="0 0 0 0 1  0 0 0 0 .86  0 0 0 0 .72  0 0 0 3.2 -1.55"/></filter>
<filter id="w2" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".002 .05" numOctaves="3" seed="5" result="n"/>
<feColorMatrix in="n" type="matrix" values="0 0 0 0 .05  0 0 0 0 .12  0 0 0 0 .25  0 0 0 2.4 -.9"/></filter>
<radialGradient id="sun" cx=".66" cy=".53" r=".42"><stop offset="0" stop-color="#fff6d6" stop-opacity="1"/><stop offset=".12" stop-color="#ffd58a" stop-opacity=".85"/><stop offset="1" stop-color="#ff9a5a" stop-opacity="0"/></radialGradient>
<linearGradient id="col" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffe9b8" stop-opacity=".9"/><stop offset="1" stop-color="#ffe9b8" stop-opacity="0"/></linearGradient>
<mask id="cm"><rect x="760" y="360" width="170" height="310" fill="url(#col)"/></mask>
<filter id="blur"><feGaussianBlur stdDeviation="2.5"/></filter></defs>
<rect width="1280" height="670" fill="url(#sk)"/><rect width="1280" height="670" fill="url(#sun)"/>
<rect y="355" width="1280" height="315" fill="url(#sea)"/>
<rect y="355" width="1280" height="315" filter="url(#w2)" opacity=".8"/>
<rect y="355" width="1280" height="315" filter="url(#w)" mask="url(#cm)" opacity=".95"/>
<rect y="353" width="1280" height="4" fill="#fff3d0" opacity=".55" filter="url(#blur)"/>"""


def _scene_forest(rnd):
    def tree(x, base, h, w, color):
        pts = [f"{x},{base}"]
        tiers = 6
        left, right = [], []
        for k in range(tiers):
            yy = base - h * (k + 1) / tiers
            ww = w * (1 - k / tiers) * rnd.uniform(.9, 1.1)
            left.append((x - ww / 2, yy + h / tiers * .55))
            left.append((x - ww * .28, yy))
            right.append((x + ww * .28, yy))
            right.append((x + ww / 2, yy + h / tiers * .55))
        poly = [(x - w / 2, base)] + left + [(x, base - h)] + list(reversed(right)) + [(x + w / 2, base)]
        return f'<polygon points="{" ".join(f"{a:.0f},{b:.0f}" for a, b in poly)}" fill="{color}"/>'
    def layer(base, h, w, color, step, blur):
        out, x = "", -30
        while x < 1320:
            out += tree(x + rnd.randint(-12, 12), base + rnd.randint(-10, 10), h * rnd.uniform(.6, 1.15), w * rnd.uniform(.8, 1.2), color)
            x += step * rnd.uniform(.7, 1.25)
        return f'<g filter="url(#bl{blur})">{out}</g>'
    far = layer(470, 190, 70, "#8fb0a6", 46, 3)
    mid = layer(540, 280, 100, "#4f7b6d", 62, 2)
    near = layer(620, 400, 150, "#244a3f", 90, 1)
    front = layer(720, 560, 220, "#0c2822", 150, 0)
    return f"""<defs>
<linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9cc9bd"/><stop offset=".55" stop-color="#d4e9dc"/><stop offset="1" stop-color="#f1efd0"/></linearGradient>
<linearGradient id="fog1" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#eaf4e6" stop-opacity="0"/><stop offset="1" stop-color="#eaf4e6" stop-opacity=".8"/></linearGradient>
<linearGradient id="ray" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fffbe0" stop-opacity=".75"/><stop offset="1" stop-color="#fffbe0" stop-opacity="0"/></linearGradient>
<filter id="b"><feGaussianBlur stdDeviation="10"/></filter>
<filter id="bl3"><feGaussianBlur stdDeviation="3.2"/></filter><filter id="bl2"><feGaussianBlur stdDeviation="1.6"/></filter><filter id="bl1"><feGaussianBlur stdDeviation=".8"/></filter><filter id="bl0"><feGaussianBlur stdDeviation="0"/></filter></defs>
<rect width="1280" height="670" fill="url(#g)"/>
<g filter="url(#b)"><polygon points="760,-20 900,-20 560,670 330,670" fill="url(#ray)"/><polygon points="980,-20 1070,-20 840,670 700,670" fill="url(#ray)" opacity=".7"/></g>
{far}<rect y="330" width="1280" height="340" fill="url(#fog1)"/>{mid}<rect y="400" width="1280" height="270" fill="url(#fog1)" opacity=".75"/>{near}<rect y="500" width="1280" height="170" fill="url(#fog1)" opacity=".35"/>{front}"""


SCENES = {"night": _scene_night, "sky": _scene_sky, "sea": _scene_sea, "forest": _scene_forest}
FONT_ROT = ["dela", "maru", "rocknroll", "reggae", "mochiy", "potta"]  # ポップで力強い書体だけ(明朝・古風は「高貴すぎる」ので使わない)


def nature(s, ill, scene):
    import random
    from .fonts import font_css
    rnd = random.Random(sum(ord(c) for c in s["title_html"]))
    svg = SCENES[scene](rnd)
    key = s.get("font") or FONT_ROT[sum(ord(c) for c in s["title_html"]) % len(FONT_ROT)]
    lines = [x for x in re.split(r"<br\s*/?>", s["title_html"]) if _plain(x).strip()]
    hot = [("<b>" in x or "<em>" in x) for x in lines]
    if not any(hot):
        hot[-1] = True
    plain = [_plain(x).strip() for x in lines]
    css, family = font_css(key, "".join(plain) + s["tag"] + "人生最適化中の会社員")
    W, H = 1120, 470
    sizes = [min(150, W / max(_vis_len(x), 1)) for x in plain]
    k = min(1.0, H / (sum(sizes) * 1.22))
    sizes = [max(52, int(z * k)) for z in sizes]
    thick = {"dela": 0, "maru": 1.6, "rocknroll": 1.6, "reggae": 0.8, "mochiy": 1.2, "potta": 1.0}.get(key, 1.2)
    rows = ""
    for x, z, h in zip(plain, sizes, hot):
        col = "#ffe27a" if h else "#ffffff"
        rows += (f'<div style="font-size:{z}px;line-height:1.2;white-space:nowrap;color:{col};letter-spacing:.02em;'
                 f'-webkit-text-stroke:{thick}px {col};text-shadow:0 3px 22px rgba(0,0,0,.55),0 1px 3px rgba(0,0,0,.7)">{html.escape(x)}</div>')
    shade = ('<div style="position:absolute;inset:0;background:linear-gradient(90deg,rgba(0,0,0,.42),rgba(0,0,0,.1) 70%,rgba(0,0,0,0))"></div>')
    tag = (f'<div style="position:absolute;left:70px;top:46px;font-size:30px;letter-spacing:.16em;color:#fff;text-shadow:0 2px 10px rgba(0,0,0,.6);'
           f'border-bottom:3px solid #ffe27a;padding-bottom:6px">{html.escape(s["tag"])}</div>')
    top = 120 + max(0, int((H - sum(sizes) * 1.22) / 2))
    return f"""{css}<div class="fig" id="t" style="width:1280px;height:670px;padding:0;position:relative;overflow:hidden;background:#000;font-family:{family}">
<svg style="position:absolute;left:0;top:0" width="1280" height="670" viewBox="0 0 1280 670">{svg}<filter id="grain"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="3"/><feColorMatrix type="matrix" values="0 0 0 0 .5  0 0 0 0 .5  0 0 0 0 .5  0 0 0 .5 -.12"/></filter><rect width="1280" height="670" filter="url(#grain)" opacity=".5"/></svg>{shade}{tag}
<div style="position:absolute;left:70px;top:{top}px">{rows}</div>
<div style="position:absolute;right:30px;bottom:18px;font-size:20px;letter-spacing:.1em;color:#fff;opacity:.85;text-shadow:0 1px 6px rgba(0,0,0,.7)">人生最適化中の会社員</div></div>"""


def night(s, ill):
    return nature(s, ill, "night")


def sky(s, ill):
    return nature(s, ill, "sky")


def sea(s, ill):
    return nature(s, ill, "sea")


def forest(s, ill):
    return nature(s, ill, "forest")


STYLES = {"scene": scene, "burst": burst, "memo": memo, "poster": poster, "pachi": pachi, "mincho": mincho, "maru": maru, "dela": dela, "antique": antique, "night": night, "sky": sky, "sea": sea, "forest": forest}
