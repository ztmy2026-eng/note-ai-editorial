"""記事の本文用の図と見出し画像(週次方針 config/weekly_policy.md の仕様)を作る。

runs/<実行ID>/figures.json(図のリスト)を読み、runs/<実行ID>/images/figures/<name>.png に書き出す。
- 種類: cover(見出し画像 1280x670)/ bar(数字比較)/ timeline(流れ・スケジュール)/ checklist(確認事項の表)
- 書き方: HTMLで組み、Playwright の Chromium(device_scale_factor=2)で要素をスクリーンショットする。
- 数字は出典か計算スクリプトの結果だけを使う(このモジュールは渡された値をそのまま描くだけ)。

figures.json の例:
[
  {"type": "cover", "name": "cover", "tag": "年末調整", "title_html": "…「<em>出し忘れ</em>」5つ", "icon": "doc"},
  {"type": "bar", "name": "fig1_xxx", "title": "…", "sub": "…", "unit": "万円", "labels": ["A", "B"],
   "series": [{"name": "2026年", "values": [104, 67]}], "note": "前提・出典"},
  {"type": "timeline", "name": "fig2_xxx", "title": "…", "items": [{"date": "10月", "label": "…", "desc": "…", "hl": false}]},
  {"type": "checklist", "name": "fig3_xxx", "title": "…", "columns": ["…"], "widths": [300, 500, 352], "rows": [["…"]]}
]
cover の icon: cat(白いマンチカン。普通)|cat_happy(笑顔)|cat_worry(困り顔)|cat_think(考える)|house|yen|chart|doc|shield|robot|briefcase|cart|bolt(電気)|aircon(エアコン)|phone(スマホ・通信)|bulb(照明)|flame(ガス)|calendar(年払い・更新日)|receipt(明細・家計)(または illust_html で自作)。
cover の photo: 写真のファイル(例: assets/mascot/munchkin_cc0_1.jpg。ライセンスが明確なものだけ。assets/mascot/README.md)。猫の絵(icon: cat…)のかわりに、実写を右に置く。
cover の title_html: <em>…</em>=紺の地に黄の文字、<b>…</b>=赤い文字。sub=タイトルの下の白い帯(2段型タイトルのサブ)。
cover の bg(背景の黄色系): sun|lemon|amber|honey|cream、または「#ffd43b」形式の色。書かなければ、実行の日付で毎日変わる(同じ色が続かない)。
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

from . import runs
from .log import log_event

SPEC_FILE = "figures.json"
NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,60}$")


class FigureError(Exception):
    pass


FONT='"Noto Sans CJK JP", sans-serif'
BASE=f"""<style>*{{box-sizing:border-box;margin:0;padding:0}}body{{font-family:{FONT};background:#fff}}
.fig{{width:1280px;background:#fcfcfb;color:#1d2433;padding:56px 64px 48px}}
.fig h1{{font-size:38px;font-weight:700;line-height:1.35}} .fig .sub{{font-size:22px;color:#5a6272;margin-top:10px;line-height:1.5}}
.note{{font-size:18px;color:#6b7280;margin-top:28px;line-height:1.6;border-top:1px solid #e5e7eb;padding-top:16px}}
.brand{{font-size:16px;color:#9aa1ad;text-align:right;margin-top:12px}}</style>"""
ICONS={
'house':'<div style="position:absolute;left:90px;top:170px;width:220px;height:170px;background:#fff;border-radius:6px"></div><div style="position:absolute;left:60px;top:60px;width:0;height:0;border-left:140px solid transparent;border-right:140px solid transparent;border-bottom:120px solid #eda100"></div><div style="position:absolute;left:175px;top:250px;width:50px;height:90px;background:#16233f;border-radius:4px 4px 0 0"></div><div style="position:absolute;left:115px;top:200px;width:40px;height:40px;background:#9fc3f0;border-radius:3px"></div><div style="position:absolute;left:245px;top:200px;width:40px;height:40px;background:#9fc3f0;border-radius:3px"></div><div style="position:absolute;left:260px;top:20px;font-size:64px;font-weight:900;color:#fff">%</div>',
'yen':'<div style="position:absolute;left:70px;top:60px;width:260px;height:260px;border-radius:50%;background:#eda100;display:flex;align-items:center;justify-content:center;font-size:150px;font-weight:900;color:#16233f">¥</div><div style="position:absolute;left:250px;top:250px;width:110px;height:110px;border-radius:50%;background:#fff;display:flex;align-items:center;justify-content:center;font-size:62px;font-weight:900;color:#16233f">¥</div>',
'chart':'<div style="position:absolute;left:50px;top:340px;width:300px;height:4px;background:#fff"></div>'+''.join(f'<div style="position:absolute;left:{70+i*70}px;top:{340-h}px;width:46px;height:{h}px;background:{c};border-radius:4px 4px 0 0"></div>' for i,(h,c) in enumerate([(80,"#86b6ef"),(140,"#5a98e2"),(200,"#2a78d6"),(270,"#eda100")])),
'doc':'<div style="position:absolute;left:90px;top:40px;width:220px;height:300px;background:#fff;border-radius:8px"></div>'+''.join(f'<div style="position:absolute;left:120px;top:{90+i*44}px;width:{160 if i%2 else 120}px;height:12px;background:#c9d3e3;border-radius:6px"></div>' for i in range(5))+'<div style="position:absolute;left:230px;top:240px;width:120px;height:120px;border-radius:50%;background:#eda100;display:flex;align-items:center;justify-content:center;font-size:70px;font-weight:900;color:#16233f">✓</div>',
'shield':'<div style="position:absolute;left:90px;top:40px;width:220px;height:280px;background:#eda100;border-radius:20px 20px 110px 110px;display:flex;align-items:center;justify-content:center;font-size:110px;font-weight:900;color:#16233f">+</div><div style="position:absolute;left:250px;top:250px;width:100px;height:100px;border-radius:50%;background:#fff;display:flex;align-items:center;justify-content:center;font-size:56px;font-weight:900;color:#16233f">¥</div>',
'robot':'<div style="position:absolute;left:190px;top:30px;width:20px;height:50px;background:#fff"></div><div style="position:absolute;left:180px;top:15px;width:40px;height:40px;border-radius:50%;background:#eda100"></div><div style="position:absolute;left:70px;top:80px;width:260px;height:200px;background:#fff;border-radius:30px"></div><div style="position:absolute;left:125px;top:145px;width:44px;height:44px;border-radius:50%;background:#16233f"></div><div style="position:absolute;left:231px;top:145px;width:44px;height:44px;border-radius:50%;background:#16233f"></div><div style="position:absolute;left:150px;top:225px;width:100px;height:14px;border-radius:7px;background:#eda100"></div><div style="position:absolute;left:230px;top:280px;width:120px;height:80px;border-radius:12px;background:#eda100;display:flex;align-items:center;justify-content:center;font-size:44px;font-weight:900;color:#16233f">¥</div>',
'briefcase':'<div style="position:absolute;left:150px;top:70px;width:100px;height:60px;border:16px solid #fff;border-bottom:none;border-radius:16px 16px 0 0"></div><div style="position:absolute;left:60px;top:125px;width:280px;height:190px;background:#eda100;border-radius:16px"></div><div style="position:absolute;left:60px;top:200px;width:280px;height:8px;background:#16233f"></div><div style="position:absolute;left:180px;top:185px;width:40px;height:40px;background:#fff;border-radius:6px"></div><div style="position:absolute;left:280px;top:270px;font-size:80px;font-weight:900;color:#fff">→</div>',
'cart':'<div style="position:absolute;left:60px;top:90px;width:260px;height:150px;background:#eda100;border-radius:8px 8px 30px 30px"></div><div style="position:absolute;left:20px;top:70px;width:60px;height:14px;background:#fff;border-radius:7px"></div><div style="position:absolute;left:100px;top:270px;width:50px;height:50px;border-radius:50%;background:#fff"></div><div style="position:absolute;left:240px;top:270px;width:50px;height:50px;border-radius:50%;background:#fff"></div><div style="position:absolute;left:250px;top:10px;font-size:90px;font-weight:900;color:#fff">↑</div>',
}
def _svg(inner):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 420" width="400" height="420">{inner}</svg>'
A='#eda100';W='#fff';N='#16233f';L='#9fc3f0'
ICONS.update({
'bolt':_svg(f'<polygon points="235,40 105,245 190,245 160,385 300,165 212,165" fill="{A}"/><polygon points="235,40 105,245 190,245 212,165" fill="{W}" opacity=".25"/><circle cx="90" cy="95" r="10" fill="{W}"/><circle cx="320" cy="285" r="14" fill="{W}"/><circle cx="330" cy="95" r="7" fill="{L}"/>'),
'aircon':_svg(f'<rect x="40" y="90" width="320" height="130" rx="26" fill="{W}"/><rect x="62" y="186" width="276" height="16" rx="8" fill="{N}" opacity=".85"/><rect x="62" y="186" width="276" height="16" rx="8" fill="{A}" opacity=".0"/><circle cx="82" cy="130" r="9" fill="{A}"/><rect x="110" y="122" width="90" height="16" rx="8" fill="{L}"/>'+''.join(f'<path d="M{x} 250 q26 30 0 62 q-26 32 0 62" fill="none" stroke="{L}" stroke-width="14" stroke-linecap="round"/>' for x in (110,200,290))),
'phone':_svg(f'<rect x="115" y="40" width="170" height="340" rx="32" fill="{W}"/><rect x="133" y="82" width="134" height="236" rx="10" fill="{L}"/><circle cx="200" cy="350" r="12" fill="{N}" opacity=".5"/><circle cx="200" cy="190" r="52" fill="{A}"/><text x="200" y="212" text-anchor="middle" font-size="68" font-weight="900" fill="{N}" font-family="sans-serif">¥</text><rect x="160" y="60" width="80" height="8" rx="4" fill="{N}" opacity=".5"/>'),
'bulb':_svg(f'<circle cx="200" cy="170" r="105" fill="{A}"/><circle cx="165" cy="135" r="30" fill="{W}" opacity=".35"/><rect x="152" y="268" width="96" height="22" rx="8" fill="{W}"/><rect x="162" y="298" width="76" height="22" rx="8" fill="{W}"/><rect x="178" y="328" width="44" height="20" rx="10" fill="{W}"/>'+''.join(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{W}" stroke-width="12" stroke-linecap="round"/>' for x1,y1,x2,y2 in [(200,40,200,14),(70,60,50,40),(330,60,350,40),(45,170,15,170),(355,170,385,170)])),
'flame':_svg(f'<path d="M205 35 C215 110 310 150 310 250 C310 330 260 385 200 385 C140 385 90 335 90 255 C90 200 130 170 150 120 C170 150 175 160 190 165 C195 120 190 75 205 35 Z" fill="{A}"/><path d="M200 210 C215 250 262 270 262 320 C262 355 235 380 200 380 C165 380 140 355 140 322 C140 285 185 262 200 210 Z" fill="{W}"/>'),
'calendar':_svg(f'<rect x="65" y="75" width="270" height="280" rx="24" fill="{W}"/><rect x="65" y="75" width="270" height="78" rx="24" fill="{A}"/><rect x="65" y="125" width="270" height="28" fill="{A}"/><rect x="118" y="45" width="22" height="64" rx="11" fill="{L}"/><rect x="260" y="45" width="22" height="64" rx="11" fill="{L}"/>'+''.join(f'<rect x="{95+c*60}" y="{185+r*55}" width="36" height="30" rx="6" fill="{L if (r,c)!=(1,2) else A}"/>' for r in range(3) for c in range(4))),
'receipt':_svg(f'<polygon points="95,40 305,40 305,380 275,360 245,380 215,360 185,380 155,360 125,380 95,360" fill="{W}"/>'+''.join(f'<rect x="130" y="{95+i*45}" width="{140 if i%2==0 else 100}" height="14" rx="7" fill="#c9d3e3"/>' for i in range(4))+f'<circle cx="255" cy="300" r="42" fill="{A}"/><text x="255" y="322" text-anchor="middle" font-size="58" font-weight="900" fill="{N}" font-family="sans-serif">¥</text>'),
})
def _cat(expr='normal'):
    """白とグレーのぶちのマンチカンの子猫(マスコット)。写真を参考に、毛の1本1本の筆づかい・やわらかい陰影・つやのある青い目で、リアルに描く(SVG。AI画像生成ではない)。
    expr: normal|happy|worry|think"""
    import math
    import random
    rnd = random.Random(7)

    def inside_ellipse(x, y, cx, cy, rx, ry):
        return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1

    # --- ぶち(グレー)の範囲: 写真の子と同じ、頭の左右・背中・しっぽがグレー、顔の真ん中と胸・足は白 ---
    def gray_at(x, y):
        if inside_ellipse(x, y, 140, 185, 108, 92):  # 頭
            blaze = abs(x - 140) < (10 + max(0, 190 - y) * .10) and y < 215
            side = inside_ellipse(x, y, 78, 150, 52, 62) or inside_ellipse(x, y, 205, 150, 48, 60)
            return side and not blaze
        if y < 200 and x > 335:  # しっぽ
            return True
        return inside_ellipse(x, y, 285, 262, 62, 30) or inside_ellipse(x, y, 240, 330, 40, 22)

    W = ["#ffffff", "#fbf8f4", "#f3eee7", "#e9e2d8", "#dcd3c7"]
    G = ["#a8a29b", "#97918a", "#b9b3ab", "#847e77", "#c8c2ba"]

    def strokes(sampler, n, dirf, ln, wd, jitter=.5):
        """色ごとに、短い線(毛)をまとめて1つのpathにする。"""
        groups = {}
        for _ in range(n):
            x, y = sampler()
            dx, dy = dirf(x, y)
            a = math.atan2(dy, dx) + rnd.uniform(-jitter, jitter)
            k = ln * (.55 + .9 * rnd.random())
            gray = gray_at(x, y)
            pal = G if gray else W
            col = pal[min(len(pal) - 1, int(rnd.random() ** 1.6 * len(pal)))]
            ex, ey = x + math.cos(a) * k, y + math.sin(a) * k
            cx_, cy_ = (x + ex) / 2 + rnd.uniform(-1.5, 1.5), (y + ey) / 2 + rnd.uniform(-1.5, 1.5)
            groups.setdefault(col, []).append(f"M{x:.1f} {y:.1f}Q{cx_:.1f} {cy_:.1f} {ex:.1f} {ey:.1f}")
        return ''.join(f'<path d="{"".join(v)}" fill="none" stroke="{c}" stroke-width="{wd}" stroke-linecap="round" stroke-opacity=".8"/>' for c, v in groups.items())

    def in_ell(cx, cy, rx, ry):
        def f():
            while True:
                x, y = cx + rx * rnd.uniform(-1, 1), cy + ry * rnd.uniform(-1, 1)
                if inside_ellipse(x, y, cx, cy, rx, ry):
                    return x, y
        return f

    defs = ('<defs>'
            '<filter id="fur" x="-10%" y="-10%" width="120%" height="120%"><feTurbulence type="fractalNoise" baseFrequency="0.6" numOctaves="2" seed="5" result="n"/>'
            '<feDisplacementMap in="SourceGraphic" in2="n" scale="6" xChannelSelector="R" yChannelSelector="G"/></filter>'
            '<filter id="b6" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="6"/></filter>'
            '<filter id="b3" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="3"/></filter>'
            '<filter id="b1" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="1.2"/></filter>'
            '<filter id="drop" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="5" stdDeviation="5" flood-color="#5e4500" flood-opacity=".32"/></filter>'
            '<radialGradient id="fw" cx="40%" cy="32%" r="80%"><stop offset="0" stop-color="#ffffff"/><stop offset=".65" stop-color="#f7f3ee"/><stop offset="1" stop-color="#ddd5ca"/></radialGradient>'
            '<radialGradient id="iris" cx="48%" cy="36%" r="64%"><stop offset="0" stop-color="#7fa6d6"/><stop offset=".45" stop-color="#44689c"/><stop offset="1" stop-color="#16294a"/></radialGradient>'
            '<clipPath id="ch"><ellipse cx="140" cy="185" rx="108" ry="92"/></clipPath>'
            '<clipPath id="cbd"><ellipse cx="245" cy="300" rx="125" ry="70"/></clipPath>'
            '</defs>')
    P = []
    P.append('<ellipse cx="225" cy="410" rx="165" ry="11" fill="#4d3a00" opacity=".28" filter="url(#b3)"/>')
    # 体・しっぽ・足・胸の土台(白)
    base = ['<path d="M338 290 C374 282 396 226 384 138 C380 112 352 114 350 140 C352 196 346 240 322 262 Z" fill="#8f8982"/>',
            '<ellipse cx="330" cy="368" rx="34" ry="23" fill="url(#fw)"/>',
            '<ellipse cx="245" cy="300" rx="125" ry="70" fill="url(#fw)"/>',
            '<ellipse cx="215" cy="372" rx="34" ry="22" fill="url(#fw)"/>',
            '<ellipse cx="160" cy="288" rx="78" ry="46" fill="url(#fw)"/>',
            '<ellipse cx="146" cy="372" rx="40" ry="23" fill="url(#fw)"/>']
    P.append('<g filter="url(#drop)"><g filter="url(#fur)">' + ''.join(base) + '</g></g>')
    # 体のぶち・陰影
    P.append('<g clip-path="url(#cbd)">'
             '<ellipse cx="285" cy="262" rx="64" ry="30" fill="#8f8982" opacity=".9" filter="url(#b6)"/>'
             '<ellipse cx="240" cy="330" rx="40" ry="22" fill="#a09a93" opacity=".8" filter="url(#b6)"/>'
             '<ellipse cx="260" cy="365" rx="140" ry="40" fill="#b5ada2" opacity=".6" filter="url(#b6)"/>'
             '<ellipse cx="300" cy="258" rx="60" ry="14" fill="#fff" opacity=".35" filter="url(#b3)"/></g>')
    # 毛(体・しっぽ・足・胸)
    P.append(strokes(in_ell(245, 300, 125, 70), 700, lambda x, y: (1, .25 + (y - 300) / 90), 9, 1.1, .4))
    P.append(strokes(lambda: (rnd.uniform(334, 390), rnd.uniform(118, 286)), 260, lambda x, y: (.15, -1), 14, 1.1, .35))
    P.append(strokes(in_ell(160, 288, 78, 46), 320, lambda x, y: (0, 1), 12, 1.1, .5))
    P.append(strokes(in_ell(146, 372, 40, 23), 70, lambda x, y: (-.2, 1), 8, 1.1, .5) + strokes(in_ell(215, 372, 34, 22), 60, lambda x, y: (0, 1), 8, 1.1, .5) + strokes(in_ell(330, 368, 34, 23), 60, lambda x, y: (0, 1), 8, 1.1, .5))
    P.append('<path d="M126 376 v8 M142 379 v8 M160 378 v8 M205 376 v8 M221 376 v8 M318 372 v8 M334 372 v8" stroke="#e8b9bd" stroke-width="3.2" stroke-linecap="round"/>')
    # 首輪(ブランドの赤い首輪。細め)
    P.append('<path d="M76 262 Q140 308 204 262" fill="none" stroke="#a8281b" stroke-width="11" stroke-linecap="round"/><path d="M78 260 Q140 303 202 260" fill="none" stroke="#dd4a38" stroke-width="4" stroke-linecap="round"/>'
             '<circle cx="140" cy="296" r="11" fill="#e6a41d" stroke="#9a6400" stroke-width="2"/><path d="M134 296 h12" stroke="#7d5200" stroke-width="2.5"/><circle cx="136" cy="291" r="3" fill="#fff" opacity=".8"/>')
    # 耳
    ears = ['<path d="M50 138 L40 66 Q80 70 116 100 Z" fill="url(#fw)"/>', '<path d="M232 130 L248 62 Q210 68 172 100 Z" fill="url(#fw)"/>']
    P.append('<g filter="url(#drop)"><g filter="url(#fur)">' + ''.join(ears) + '</g></g>')
    P.append('<path d="M54 126 L47 82 Q76 86 100 106 Z" fill="#a39d96" opacity=".85" filter="url(#b1)"/><path d="M60 124 L55 92 Q76 95 92 108 Z" fill="#f4b8bf" filter="url(#b1)"/>'
             '<path d="M228 120 L242 78 Q214 84 186 104 Z" fill="#a39d96" opacity=".85" filter="url(#b1)"/><path d="M224 118 L235 88 Q214 93 196 106 Z" fill="#f4b8bf" filter="url(#b1)"/>')
    P.append(strokes(lambda: (rnd.uniform(48, 112), rnd.uniform(78, 118)), 60, lambda x, y: (-.3, -1), 8, 1, .4) + strokes(lambda: (rnd.uniform(178, 240), rnd.uniform(74, 116)), 60, lambda x, y: (.3, -1), 8, 1, .4))
    # 頭
    P.append('<g filter="url(#drop)"><g filter="url(#fur)"><ellipse cx="140" cy="185" rx="108" ry="92" fill="url(#fw)"/></g></g>')
    P.append('<g clip-path="url(#ch)">'
             '<ellipse cx="68" cy="140" rx="56" ry="70" fill="#8f8982" opacity=".92" filter="url(#b6)"/>'
             '<ellipse cx="212" cy="140" rx="52" ry="68" fill="#8f8982" opacity=".92" filter="url(#b6)"/>'
             '<path d="M128 70 L152 70 L146 205 L134 205 Z" fill="#ffffff" filter="url(#b3)"/>'
             '<ellipse cx="140" cy="268" rx="104" ry="42" fill="#cfc7bb" opacity=".55" filter="url(#b6)"/>'
             '<ellipse cx="140" cy="236" rx="40" ry="28" fill="#fff" filter="url(#b3)"/></g>')
    # 頭の毛: 鼻の周りから放射状に
    P.append(strokes(in_ell(140, 185, 108, 92), 1500, lambda x, y: (x - 140, y - 222), 8, 1.0, .3))
    # 目もと(涙やけ風のクリーム色)
    P.append('<path d="M96 206 Q92 226 100 240 M184 206 Q190 226 182 240" fill="none" stroke="#e9cfa6" stroke-width="5" stroke-linecap="round" opacity=".55" filter="url(#b1)"/>')
    # 目
    ey = 190
    if expr == 'happy':
        P.append(f'<path d="M72 {ey + 4} Q98 {ey - 26} 124 {ey + 4} M156 {ey + 4} Q182 {ey - 26} 208 {ey + 4}" fill="none" stroke="#2a3550" stroke-width="6.5" stroke-linecap="round"/>')
    else:
        dy = -4 if expr == 'think' else 0
        for cx in (98, 182):
            P.append(f'<ellipse cx="{cx}" cy="{ey}" rx="24" ry="25" fill="#2b2f3c" opacity=".35" filter="url(#b1)"/>'
                     f'<ellipse cx="{cx}" cy="{ey}" rx="22.5" ry="23.5" fill="#f3f0ec"/>'
                     f'<circle cx="{cx}" cy="{ey + dy}" r="20" fill="url(#iris)" stroke="#142238" stroke-width="2.4"/>'
                     f'<circle cx="{cx}" cy="{ey + dy + 1}" r="10.5" fill="#070b14"/>'
                     f'<path d="M{cx - 18} {ey + dy + 6} Q{cx} {ey + dy + 22} {cx + 18} {ey + dy + 6}" fill="none" stroke="#9cc0ea" stroke-width="2" opacity=".6"/>'
                     f'<circle cx="{cx - 8}" cy="{ey + dy - 9}" r="6.5" fill="#fff"/><circle cx="{cx + 8}" cy="{ey + dy + 8}" r="3" fill="#fff" opacity=".85"/>'
                     f'<path d="M{cx - 24} {ey - 6} Q{cx} {ey - 32} {cx + 24} {ey - 6}" fill="none" stroke="#6f6a64" stroke-width="2.4" stroke-linecap="round" opacity=".75"/>')
    if expr == 'worry':
        P.append('<path d="M70 158 Q98 142 122 154 M210 158 Q182 142 158 154" fill="none" stroke="#c9c2b8" stroke-width="3.5" stroke-linecap="round"/>'
                 '<path d="M262 112 Q277 140 262 152 Q247 140 262 112 Z" fill="#a9cdf2" stroke="#6c9bd0" stroke-width="2.5" stroke-linejoin="round"/>')
    if expr == 'think':
        P.append('<path d="M156 154 Q180 142 206 150" fill="none" stroke="#c9c2b8" stroke-width="3.5" stroke-linecap="round"/>'
                 '<text x="252" y="108" font-size="70" font-weight="900" fill="#2a3550" font-family="sans-serif">?</text>')
    # 鼻・口・ひげ
    P.append('<path d="M129 222 Q140 216 151 222 Q148 234 140 237 Q132 234 129 222 Z" fill="#f0909f" stroke="#cf6a7e" stroke-width="1.6" stroke-linejoin="round"/>'
             '<ellipse cx="136" cy="222" rx="4" ry="2" fill="#fff" opacity=".7"/>'
             '<path d="M140 237 V247 M140 247 Q129 259 116 249 M140 247 Q151 259 164 249" fill="none" stroke="#b9737f" stroke-width="2.4" stroke-linecap="round"/>')
    wh = 'M84 236 Q52 226 12 228 M84 244 Q50 248 10 258 M196 236 Q228 226 268 228 M196 244 Q230 248 270 258'
    P.append(f'<path d="{wh}" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round"/><path d="{wh}" fill="none" stroke="#c9c1b6" stroke-width=".8" stroke-linecap="round" opacity=".8"/>')
    return _svg(defs + ''.join(P))
ICONS.update({'cat':_cat('normal'),'cat_happy':_cat('happy'),'cat_worry':_cat('worry'),'cat_think':_cat('think')})
# 同系色(黄色〜山吹色)の背景。濃い紺の文字がどれでも読める明るさ。bg に名前か「#ffd43b」形式の色を書く
BG_NAMES={'sun':'#ffd43b','lemon':'#ffe066','amber':'#ffc233','honey':'#ffcf4d','cream':'#ffe98a'}
BG_ORDER=['sun','lemon','amber','honey','cream']
HEX_RE=re.compile(r'^#[0-9a-fA-F]{6}$')
def _bg(s):
    v=str(s.get('bg') or 'sun')
    return BG_NAMES.get(v) or (v if HEX_RE.match(v) else BG_NAMES['sun'])
EM_OPEN='<span style="background:#16233f;color:{bg};font-style:normal;padding:0 .12em;border-radius:6px;-webkit-box-decoration-break:clone;box-decoration-break:clone">'
def _photo_card(path):
    """写真を、白い縁と影のついた、角の丸いカードにして返す(HTML)。写真は、ファイルの中に埋め込む。"""
    import base64
    from pathlib import Path as _P
    f = _P(path)
    if not f.exists():
        raise FigureError(f"写真が見つかりません: {path}")
    mime = "image/png" if f.suffix.lower() == ".png" else "image/jpeg"
    b64 = base64.b64encode(f.read_bytes()).decode("ascii")
    return ('<div style="position:absolute;right:44px;top:92px;width:560px;height:474px;border-radius:30px;border:9px solid #fff;overflow:hidden;'
            'box-shadow:0 14px 30px rgba(80,58,0,.35);transform:rotate(1.6deg);background:#fff">'
            f'<img src="data:{mime};base64,{b64}" style="width:100%;height:100%;object-fit:cover;display:block"></div>')
def _rich(text):
    """文字は安全に変換し、<b>…</b>(赤い文字)だけ使えるようにする。"""
    return html.escape(text).replace('&lt;b&gt;','<span style="color:#d62f1f">').replace('&lt;/b&gt;','</span>')
def cover(s):
    ill=s.get('illust_html') or ICONS.get(s.get('icon','yen'))
    bg=_bg(s)
    cat=str(s.get('icon','')).startswith('cat')
    title=s['title_html'].replace('<em>',EM_OPEN.format(bg=bg)).replace('</em>','</span>').replace('<b>','<span style="color:#d62f1f">').replace('</b>','</span>')
    sub=(f'<div style="display:inline-block;margin-top:26px;background:#fff;color:#16233f;font-size:{s.get("sub_size",30)}px;font-weight:900;'
         f'padding:12px 28px;border-radius:44px;border:4px solid #16233f">{_rich(s["sub"])}</div>') if s.get('sub') else ''
    photo = s.get('photo')
    if photo:  # 実写の写真(ライセンスが明確なもの。assets/mascot/README.md)を、右に丸い角のカードで置く
        pic = _photo_card(photo)
    elif cat:  # 白いマンチカン(マスコット)は、背景に直接置く
        big = ill.replace('width="400" height="420"', 'width="460" height="483"')
        pic = f'<div style="position:absolute;right:24px;top:120px;width:460px;height:483px">{big}</div>'
    else:
        pic = f'<div style="position:absolute;right:40px;top:130px;width:400px;height:420px;background:#16233f;border-radius:36px;overflow:hidden">{ill}</div>'
    return f"""<div class="fig" id="t" style="width:1280px;height:670px;background:{bg};padding:0;position:relative;overflow:hidden;color:#16233f">
<div style="position:absolute;left:64px;top:56px;background:#16233f;color:{bg};font-weight:700;font-size:26px;padding:8px 22px;border-radius:6px">{html.escape(s['tag'])}</div>
<div style="position:absolute;left:64px;top:140px;width:{600 if photo else 720 if cat else 700}px">
<div style="text-wrap:balance;font-size:{s.get('size',(56 if photo else 62) if (cat or photo) else 54)}px;font-weight:900;line-height:1.32;letter-spacing:.01em">{title}</div>{sub}</div>
<div style="position:absolute;left:64px;bottom:48px;font-size:24px;font-weight:700;color:#3b4a63">人生最適化中の会社員</div>
{pic}</div>"""
def bar(s):
    labels=s['labels'];ser=s['series'];n=len(ser)
    allv=[v for x in ser for v in x['values']];mx=max(allv)*1.15
    H=420;W=1152;gw=W/len(labels);bw=min(110,(gw*0.7)/n)
    cols=['#2a78d6'] if n==1 else (['#86b6ef','#2a78d6'] if n==2 else ['#b9d4f5','#86b6ef','#2a78d6'][:n])
    fmt=s.get('fmt','{:,}')
    parts=[]
    for g in range(5):
        y=H-H*g/4
        parts.append(f'<div style="position:absolute;left:0;top:{y}px;width:{W}px;height:1px;background:#eceef1"></div>')
    for i,l in enumerate(labels):
        x0=i*gw+(gw-bw*n-8*(n-1))/2
        for j,x in enumerate(ser):
            v=x['values'][i];h=H*v/mx;x1=x0+j*(bw+8)
            parts.append(f'<div style="position:absolute;left:{x1}px;top:{H-h}px;width:{bw}px;height:{h}px;background:{cols[j]};border-radius:4px 4px 0 0"></div>')
            parts.append(f'<div style="position:absolute;left:{x1-30}px;top:{H-h-34}px;width:{bw+60}px;text-align:center;font-size:21px;font-weight:700">{fmt.format(v)}{s.get("unit","")}</div>')
        parts.append(f'<div style="position:absolute;left:{i*gw}px;top:{H+14}px;width:{gw}px;text-align:center;font-size:21px;line-height:1.35">{l}</div>')
    leg=''
    if n>1: leg='<div style="display:flex;gap:28px;margin-top:22px;font-size:20px">'+''.join(f'<span><span style="display:inline-block;width:18px;height:18px;background:{cols[j]};border-radius:3px;vertical-align:-2px;margin-right:8px"></span>{html.escape(x["name"])}</span>' for j,x in enumerate(ser))+'</div>'
    return f"""<div class="fig" id="t"><h1>{s['title']}</h1><div class="sub">{s.get('sub','')}</div>{leg}
<div style="position:relative;height:{H+80}px;margin-top:40px">{''.join(parts)}</div>
{f'<div class="note">{s["note"]}</div>' if s.get('note') else ''}<div class="brand">人生最適化中の会社員</div></div>"""
def timeline(s):
    it=s['items']
    rows=''.join(f"""<div style="display:flex;gap:28px;position:relative;padding-bottom:30px">
<div style="width:200px;flex:none;text-align:right;font-size:24px;font-weight:700;color:{'#c47f00' if x.get('hl') else '#2a78d6'};padding-top:2px">{x['date']}</div>
<div style="width:28px;flex:none;position:relative"><div style="width:22px;height:22px;border-radius:50%;background:{'#eda100' if x.get('hl') else '#2a78d6'};margin-top:6px;margin-left:3px;position:relative;z-index:1"></div>{'' if k==len(it)-1 else '<div style="position:absolute;left:12px;top:20px;bottom:-36px;width:4px;background:#d6e4f5"></div>'}</div>
<div style="flex:1"><div style="font-size:26px;font-weight:700;line-height:1.4">{x['label']}</div><div style="font-size:21px;color:#4b5363;margin-top:6px;line-height:1.55">{x.get('desc','')}</div></div></div>""" for k,x in enumerate(it))
    return f"""<div class="fig" id="t"><h1>{s['title']}</h1><div class="sub">{s.get('sub','')}</div><div style="margin-top:40px">{rows}</div>
{f'<div class="note">{s["note"]}</div>' if s.get('note') else ''}<div class="brand">人生最適化中の会社員</div></div>"""
def checklist(s):
    cols = s['columns']; w = s.get('widths')
    box = ('<span style="display:inline-block;width:22px;height:22px;border:3px solid #2a78d6;'
           'border-radius:4px;vertical-align:-3px;margin-right:12px"></span>') if s.get("boxes", True) else ""
    th = ''.join(f'<th style="text-align:left;padding:16px 18px;background:#16233f;color:#fff;font-size:22px;'
                 f'{"width:" + str(w[i]) + "px;" if w else ""}">{c}</th>' for i, c in enumerate(cols))
    tr = ''
    for r, row in enumerate(s['rows']):
        bg = '#ffffff' if r % 2 == 0 else '#f3f5f8'
        tds = ''
        for i, c in enumerate(row):
            bold = "font-weight:700;" if i == 0 else ""
            lead = box if i == 0 else ""
            tds += (f'<td style="padding:16px 18px;font-size:21px;line-height:1.5;vertical-align:top;'
                    f'border-bottom:1px solid #e3e6eb;{bold}">{lead}{c}</td>')
        tr += f'<tr style="background:{bg}">{tds}</tr>'
    note = f'<div class="note">{s["note"]}</div>' if s.get('note') else ''
    return (f'<div class="fig" id="t"><h1>{s["title"]}</h1><div class="sub">{s.get("sub", "")}</div>'
            f'<table style="width:100%;border-collapse:collapse;margin-top:34px;table-layout:fixed;border-radius:6px;overflow:hidden">'
            f'<tr>{th}</tr>{tr}</table>{note}<div class="brand">人生最適化中の会社員</div></div>')


R = {'cover':cover,'bar':bar,'timeline':timeline,'checklist':checklist}


def _launch(p):
    """Playwright 標準のブラウザで起動し、無い/版が合わない場合は、すでにある Chrome・Chromium を指定して起動する。
    (ブラウザを新しく入れ直さない。探し方は images.find_browser と同じ)"""
    try:
        return p.chromium.launch()
    except Exception as first:
        from . import images
        try:
            return p.chromium.launch(executable_path=images.find_browser(images.load_config(Path("."))))
        except Exception as second:
            raise FigureError(f"図を描くブラウザを起動できません: {str(first).splitlines()[0][:120]} / {second}") from second


def _page_html(s: dict, script: str = "") -> str:
    return '<html><head><meta charset="utf-8">' + BASE + '</head><body>' + R[s["type"]](s) + script + '</body></html>'


_MEASURE = ('<script>window.addEventListener("load",function(){var d=document.createElement("pre");'
            'd.textContent="HEIGHT="+document.getElementById("t").offsetHeight;document.body.appendChild(d);});</script>')


def render_all_cli(specs: list[dict], out_dir: Path) -> list[Path]:
    """Playwright が無い環境(クラウドなど)用。画像づくりと同じ、Chrome/Edge の命令だけで描く(追加の導入が要らない)。
    高さは、先にページを読み込んで測る(--dump-dom)。"""
    import subprocess
    from . import images
    browser = images.find_browser(images.load_config(Path(".")))
    out_dir.mkdir(parents=True, exist_ok=True)
    work = out_dir / "_work"
    work.mkdir(exist_ok=True)
    base = [browser, "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars"]
    made = []
    try:
        for s in specs:
            out = out_dir / f"{s['name']}.png"
            measure = work / f"{s['name']}_m.html"
            measure.write_text(_page_html(s, _MEASURE), encoding="utf-8")
            try:
                dom = subprocess.run(base + ["--virtual-time-budget=3000", "--dump-dom", measure.resolve().as_uri()],
                                     capture_output=True, timeout=90, check=False).stdout.decode("utf-8", "replace")
            except (OSError, subprocess.TimeoutExpired) as e:
                raise FigureError(f"図の高さを測れませんでした({s['name']}): {e}") from e
            m = re.search(r"HEIGHT=(\d+)", dom)
            if not m:
                raise FigureError(f"図の高さを測れませんでした({s['name']})")
            src = work / f"{s['name']}.html"
            src.write_text(_page_html(s), encoding="utf-8")
            out.unlink(missing_ok=True)
            cmd = base + ["--force-device-scale-factor=2", f"--screenshot={out.resolve()}",
                          f"--window-size=1280,{int(m.group(1))}", src.resolve().as_uri()]
            try:
                subprocess.run(cmd, capture_output=True, timeout=90, check=False)
            except (OSError, subprocess.TimeoutExpired) as e:
                raise FigureError(f"図の作成に失敗しました({s['name']}): {e}") from e
            if not out.exists() or out.stat().st_size == 0:
                raise FigureError(f"図ができませんでした: {s['name']}")
            made.append(out)
    finally:
        for f in work.glob("*"):
            f.unlink(missing_ok=True)
        work.rmdir()
    return made


def render_all(specs: list[dict], out_dir: Path) -> list[Path]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return render_all_cli(specs, out_dir)  # Playwright が無ければ、Chrome/Edge の命令だけで描く
    out_dir.mkdir(parents=True, exist_ok=True)
    made = []
    with sync_playwright() as p:
        b = _launch(p)
        try:
            pg = b.new_page(viewport={"width": 1280, "height": 800}, device_scale_factor=2)
            for s in specs:
                out = out_dir / f"{s['name']}.png"
                pg.set_content('<html><head><meta charset="utf-8">' + BASE + '</head><body>' + R[s["type"]](s) + '</body></html>')
                pg.wait_for_timeout(150)
                pg.locator("#t").screenshot(path=str(out))
                made.append(out)
        finally:
            b.close()
    return made


def check_specs(specs) -> list[str]:
    if not isinstance(specs, list) or not specs:
        return ["figures.json は図のリスト(1つ以上)にしてください"]
    problems = []
    names = set()
    for n, s in enumerate(specs, 1):
        if not isinstance(s, dict) or s.get("type") not in R:
            problems.append(f"{n}個目: type は {', '.join(R)} のどれか")
            continue
        name = str(s.get("name", ""))
        if not NAME_RE.match(name):
            problems.append(f"{n}個目: name は英数字・_・- だけ(拡張子なし)")
        if name in names:
            problems.append(f"{n}個目: name '{name}' が重複")
        names.add(name)
        need = {"cover": ("tag", "title_html"), "bar": ("title", "labels", "series"),
                "timeline": ("title", "items"), "checklist": ("title", "columns", "rows")}[s["type"]]
        for k in need:
            if not s.get(k):
                problems.append(f"{n}個目({name}): {k} が空")
        if s["type"] == "cover":
            if s.get("icon") and s["icon"] not in ICONS and not s.get("illust_html"):
                problems.append(f"{n}個目({name}): icon '{s['icon']}' は {'|'.join(ICONS)} のどれか")
            if s.get("bg") and s["bg"] not in BG_NAMES and not HEX_RE.match(str(s["bg"])):
                problems.append(f"{n}個目({name}): bg は {'|'.join(BG_NAMES)} か「#ffd43b」形式の色")
        if s["type"] == "bar" and s.get("labels") and s.get("series"):
            for ser in s["series"]:
                if len(ser.get("values", [])) != len(s["labels"]):
                    problems.append(f"{n}個目({name}): 値の数がラベルの数と合いません")
    return problems


def _vary_cover_bg(specs, run_id):
    """cover に bg が無ければ、実行ID の日付から黄色系の背景を選ぶ(毎日、見た目が変わる)。"""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", run_id)
    if not m:
        return
    import datetime
    day = datetime.date(int(m[1]), int(m[2]), int(m[3])).toordinal()
    photos = sorted(Path("assets/mascot").glob("*.jpg"))
    for s in specs:
        if s.get("type") == "cover" and not s.get("bg"):
            s["bg"] = BG_ORDER[day % len(BG_ORDER)]
        if s.get("type") == "cover" and s.get("photo") == "auto" and photos:  # 猫の写真を、日付で毎日かえる(同じ写真が続かない)
            s["photo"] = str(photos[day % len(photos)])


def make_figures(root: Path, run_id: str) -> list[Path]:
    rdir = runs.run_path(Path(root), run_id)
    spec_path = rdir / SPEC_FILE
    if not spec_path.exists():
        raise FigureError(f"{SPEC_FILE} がありません(runs/{run_id}/{SPEC_FILE} に図の仕様を書いてください)")
    try:
        specs = json.loads(spec_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise FigureError(f"{SPEC_FILE} が壊れています: {e}") from e
    problems = check_specs(specs)
    if problems:
        raise FigureError("図の仕様に問題があります: " + " / ".join(problems))
    _vary_cover_bg(specs, run_id)
    made = render_all(specs, rdir / "images" / "figures")
    log_event(Path(root), "figures_made", run_id=run_id, count=len(made))
    return made
