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
cover の icon: house|yen|chart|doc|shield|robot|briefcase|cart(または illust_html で自作)。
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
def cover(s):
    ill=s.get('illust_html') or ICONS.get(s.get('icon','yen'))
    return f"""<div class="fig" id="t" style="width:1280px;height:670px;background:#16233f;padding:0;position:relative;overflow:hidden;color:#fff">
<div style="position:absolute;left:64px;top:56px;background:#eda100;color:#16233f;font-weight:700;font-size:26px;padding:8px 22px;border-radius:6px">{html.escape(s['tag'])}</div>
<div style="position:absolute;left:64px;top:150px;width:760px;font-size:{s.get('size',54)}px;font-weight:900;line-height:1.38;letter-spacing:.01em">{s['title_html'].replace('<em>','<span style="color:#eda100;font-style:normal">').replace('</em>','</span>')}</div>
<div style="position:absolute;left:64px;bottom:48px;font-size:24px;font-weight:700;color:#cfd6e4">人生最適化中の会社員</div>
<div style="position:absolute;right:60px;top:130px;width:400px;height:420px">{ill}</div></div>"""
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


def render_all(specs: list[dict], out_dir: Path) -> list[Path]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise FigureError("Playwright がありません(pip install playwright)。図は作れませんでした") from e
    out_dir.mkdir(parents=True, exist_ok=True)
    made = []
    with sync_playwright() as p:
        b = p.chromium.launch()
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
        if s["type"] == "bar" and s.get("labels") and s.get("series"):
            for ser in s["series"]:
                if len(ser.get("values", [])) != len(s["labels"]):
                    problems.append(f"{n}個目({name}): 値の数がラベルの数と合いません")
    return problems


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
    made = render_all(specs, rdir / "images" / "figures")
    log_event(Path(root), "figures_made", run_id=run_id, count=len(made))
    return made
