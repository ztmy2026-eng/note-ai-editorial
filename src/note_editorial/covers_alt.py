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
<div style="position:absolute;left:46px;bottom:26px;width:300px;height:260px;transform:rotate(-4deg)">{_scale(ill,300,315)}</div>
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


STYLES = {"scene": scene, "burst": burst, "memo": memo, "poster": poster}
