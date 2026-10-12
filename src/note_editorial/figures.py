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
    """白いマンチカン(マスコット)。写真のような、ふわふわの毛・青い大きな目・短い足・立てたしっぽ。SVGで描く(AI画像生成ではない)。
    expr: normal|happy|worry|think"""
    import math
    import random
    rnd = random.Random(11)

    def tufts(cx, cy, rx, ry, a0, a1, n, ln, col="#d6cec3", op=.75, w=1.5):
        out = []
        for _ in range(n):
            ang = math.radians(a0 + (a1 - a0) * rnd.random())
            x, y = cx + rx * math.cos(ang), cy + ry * math.sin(ang)
            k = ln * (.6 + .8 * rnd.random())
            dx, dy = math.cos(ang) * k + rnd.uniform(-2, 2), math.sin(ang) * k + rnd.uniform(-1, 3)
            out.append(f"M{x - dx * .6:.1f} {y - dy * .6:.1f} Q{x + dx * .1 + rnd.uniform(-3, 3):.1f} {y + dy * .2:.1f} {x + dx:.1f} {y + dy:.1f}")
        return f'<path d="{" ".join(out)}" fill="none" stroke="{col}" stroke-opacity="{op}" stroke-width="{w}" stroke-linecap="round"/>'

    N = '#2a3550'
    defs = ('<defs>'
            '<filter id="fur" x="-10%" y="-10%" width="120%" height="120%"><feTurbulence type="fractalNoise" baseFrequency="0.5" numOctaves="2" seed="4" result="n"/>'
            '<feDisplacementMap in="SourceGraphic" in2="n" scale="8" xChannelSelector="R" yChannelSelector="G"/></filter>'
            '<filter id="soft" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="7"/></filter>'
            '<filter id="soft2" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="2.5"/></filter>'
            '<filter id="drop" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="5" stdDeviation="5" flood-color="#6b4f00" flood-opacity=".30"/></filter>'
            '<radialGradient id="fw" cx="42%" cy="34%" r="78%"><stop offset="0" stop-color="#ffffff"/><stop offset=".6" stop-color="#fcfaf7"/><stop offset="1" stop-color="#e4ddd3"/></radialGradient>'
            '<radialGradient id="iris" cx="46%" cy="38%" r="62%"><stop offset="0" stop-color="#9cc3f0"/><stop offset=".5" stop-color="#5b8ac4"/><stop offset="1" stop-color="#1e3a66"/></radialGradient>'
            '<linearGradient id="ear" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#f6b7bd"/><stop offset="1" stop-color="#f9d4d6"/></linearGradient>'
            '<radialGradient id="bell" cx="40%" cy="35%" r="70%"><stop offset="0" stop-color="#ffe08a"/><stop offset="1" stop-color="#d08a00"/></radialGradient>'
            '<clipPath id="cb"><ellipse cx="232" cy="302" rx="128" ry="66"/></clipPath>'
            '<clipPath id="ch"><ellipse cx="150" cy="187" rx="109" ry="94"/></clipPath>'
            '</defs>')
    P = []
    P.append('<ellipse cx="225" cy="408" rx="160" ry="11" fill="#5a4300" opacity=".25" filter="url(#soft2)"/>')
    # しっぽ・体・足(ふわふわの輪郭)
    body = ['<path d="M336 296 C372 288 394 232 382 156 C378 130 352 132 350 154 C352 208 346 246 320 266 Z" fill="url(#fw)"/>',
            '<ellipse cx="318" cy="370" rx="32" ry="23" fill="url(#fw)"/>',
            '<ellipse cx="232" cy="302" rx="128" ry="66" fill="url(#fw)"/>',
            '<ellipse cx="196" cy="374" rx="33" ry="22" fill="url(#fw)"/>']
    P.append('<g filter="url(#drop)"><g filter="url(#fur)">' + ''.join(body) + '</g></g>')
    # 体の陰影と毛並み
    P.append('<g clip-path="url(#cb)"><ellipse cx="260" cy="350" rx="130" ry="40" fill="#cfc6ba" opacity=".55" filter="url(#soft)"/>'
             '<ellipse cx="300" cy="270" rx="70" ry="22" fill="#ffffff" opacity=".9" filter="url(#soft2)"/></g>')
    P.append(tufts(232, 302, 128, 66, -165, -15, 70, 11) + tufts(318, 370, 32, 23, 150, 400, 14, 6) + tufts(196, 374, 33, 22, 150, 400, 14, 6))
    P.append(tufts(366, 190, 16, 60, -120, 100, 26, 8))
    P.append('<path d="M308 372 v9 M326 372 v9 M186 376 v9 M204 376 v9" stroke="#e7b9bd" stroke-width="3" stroke-linecap="round"/>')
    # 首輪(赤+金の鈴)
    P.append('<path d="M92 270 Q150 316 208 270" fill="none" stroke="#b72a1c" stroke-width="15" stroke-linecap="round"/>'
             '<path d="M94 267 Q150 311 206 267" fill="none" stroke="#e5533f" stroke-width="6" stroke-linecap="round"/>'
             '<circle cx="150" cy="303" r="14" fill="url(#bell)" stroke="#a46a00" stroke-width="2"/><path d="M142 303 h16" stroke="#8a5a00" stroke-width="3"/><circle cx="145" cy="297" r="3.5" fill="#fff" opacity=".8"/>')
    # 耳
    ears = ['<path d="M56 146 L38 58 Q84 66 122 102 Z" fill="url(#fw)"/>', '<path d="M244 146 L262 58 Q216 66 178 102 Z" fill="url(#fw)"/>']
    P.append('<g filter="url(#drop)"><g filter="url(#fur)">' + ''.join(ears) + '</g></g>')
    P.append('<path d="M63 130 L52 82 Q80 88 104 108 Z" fill="url(#ear)" opacity=".95"/><path d="M237 130 L248 82 Q220 88 196 108 Z" fill="url(#ear)" opacity=".95"/>')
    P.append(tufts(80, 112, 30, 30, 200, 290, 10, 7, "#f2d8d8", .9, 1.6) + tufts(220, 112, 30, 30, 250, 340, 10, 7, "#f2d8d8", .9, 1.6))
    # 頭
    P.append('<g filter="url(#drop)"><g filter="url(#fur)"><ellipse cx="150" cy="187" rx="109" ry="94" fill="url(#fw)"/></g></g>')
    P.append('<g clip-path="url(#ch)"><ellipse cx="150" cy="268" rx="110" ry="40" fill="#d9d1c6" opacity=".55" filter="url(#soft)"/>'
             '<ellipse cx="120" cy="120" rx="60" ry="26" fill="#ffffff" filter="url(#soft2)"/></g>')
    P.append(tufts(150, 187, 109, 94, 105, 175, 34, 12) + tufts(150, 187, 109, 94, 5, 75, 34, 12) + tufts(150, 187, 109, 94, 195, 345, 40, 9))
    P.append(tufts(150, 120, 22, 20, 200, 340, 12, 9, "#d6cec3", .6, 1.4))
    # 口もとの毛・ほほ
    P.append('<ellipse cx="150" cy="236" rx="36" ry="24" fill="#ffffff" filter="url(#soft2)"/>'
             '<ellipse cx="68" cy="222" rx="20" ry="11" fill="#f3b6bd" opacity=".45" filter="url(#soft2)"/><ellipse cx="232" cy="222" rx="20" ry="11" fill="#f3b6bd" opacity=".45" filter="url(#soft2)"/>')
    eyes_cy = 190
    if expr == 'happy':
        P.append(f'<path d="M82 {eyes_cy + 4} Q105 {eyes_cy - 24} 128 {eyes_cy + 4} M172 {eyes_cy + 4} Q195 {eyes_cy - 24} 218 {eyes_cy + 4}" fill="none" stroke="{N}" stroke-width="6.5" stroke-linecap="round"/>')
    else:
        dy = -4 if expr == 'think' else 0
        for cx in (105, 195):
            P.append(f'<ellipse cx="{cx}" cy="{eyes_cy}" rx="24" ry="25" fill="#f4f1ee"/>'
                     f'<circle cx="{cx}" cy="{eyes_cy + dy}" r="21" fill="url(#iris)" stroke="#1b2c4a" stroke-width="2.5"/>'
                     f'<circle cx="{cx}" cy="{eyes_cy + dy + 1}" r="10" fill="#0d1526"/>'
                     f'<circle cx="{cx - 8}" cy="{eyes_cy + dy - 9}" r="6.5" fill="#fff"/><circle cx="{cx + 8}" cy="{eyes_cy + dy + 8}" r="3" fill="#fff" opacity=".85"/>'
                     f'<path d="M{cx - 24} {eyes_cy - 8} Q{cx} {eyes_cy - 30} {cx + 24} {eyes_cy - 8}" fill="none" stroke="#8f8a84" stroke-width="2" stroke-linecap="round" opacity=".7"/>')
    if expr == 'worry':
        P.append('<path d="M80 160 Q108 146 130 156 M220 160 Q192 146 170 156" fill="none" stroke="#b9b1a7" stroke-width="3.5" stroke-linecap="round"/>'
                 '<path d="M272 118 Q287 146 272 158 Q257 146 272 118 Z" fill="#a9cdf2" stroke="#6c9bd0" stroke-width="2.5" stroke-linejoin="round"/>')
    if expr == 'think':
        P.append('<path d="M176 156 Q198 146 222 154" fill="none" stroke="#b9b1a7" stroke-width="3.5" stroke-linecap="round"/>'
                 '<text x="262" y="116" font-size="70" font-weight="900" fill="#2a3550" font-family="sans-serif">?</text>')
    # 鼻・口・ひげ
    P.append('<path d="M139 221 Q150 216 161 221 Q158 232 150 235 Q142 232 139 221 Z" fill="#f08c9d" stroke="#d96a80" stroke-width="1.6" stroke-linejoin="round"/>'
             '<ellipse cx="146" cy="222" rx="4" ry="2" fill="#fff" opacity=".7"/>'
             '<path d="M150 235 V245 M150 245 Q139 257 126 247 M150 245 Q161 257 174 247" fill="none" stroke="#b9737f" stroke-width="2.6" stroke-linecap="round"/>'
             '<path d="M92 236 Q60 224 20 224 M92 244 Q58 246 18 256 M208 236 Q240 224 280 224 M208 244 Q242 246 282 256" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" opacity=".95"/>'
             '<path d="M92 236 Q60 224 20 224 M92 244 Q58 246 18 256 M208 236 Q240 224 280 224 M208 244 Q242 246 282 256" fill="none" stroke="#bdb5aa" stroke-width="1" stroke-linecap="round" opacity=".8"/>')
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
    if cat:  # 白いマンチカン(マスコット)は、背景に直接置く
        big = ill.replace('width="400" height="420"', 'width="460" height="483"')
        pic = f'<div style="position:absolute;right:24px;top:120px;width:460px;height:483px">{big}</div>'
    else:
        pic = f'<div style="position:absolute;right:40px;top:130px;width:400px;height:420px;background:#16233f;border-radius:36px;overflow:hidden">{ill}</div>'
    return f"""<div class="fig" id="t" style="width:1280px;height:670px;background:{bg};padding:0;position:relative;overflow:hidden;color:#16233f">
<div style="position:absolute;left:64px;top:56px;background:#16233f;color:{bg};font-weight:700;font-size:26px;padding:8px 22px;border-radius:6px">{html.escape(s['tag'])}</div>
<div style="position:absolute;left:64px;top:140px;width:{720 if cat else 700}px">
<div style="text-wrap:balance;font-size:{s.get('size',62 if cat else 54)}px;font-weight:900;line-height:1.32;letter-spacing:.01em">{title}</div>{sub}</div>
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
    for s in specs:
        if s.get("type") == "cover" and not s.get("bg"):
            s["bg"] = BG_ORDER[day % len(BG_ORDER)]


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
