"""週次企画(日曜に作る翌週7本分の企画)と、毎朝の実行をつなぐ。

- plans/<週の開始日(月曜)>/plan.yaml に、日付ごとの企画(テーマ・タイトル案・狙い・失敗パターン・図)を置く。
- 毎朝の daily-run は、今日の日付の企画があれば `new-run --plan` でそれを使って1本作る(無ければ従来どおり next-theme)。
- 企画の中身(方針)は config/weekly_policy.md。週次企画の作り方は .claude/commands/weekly-plan.md。
- このモジュールはAIを使わない。形式の検査と、実行フォルダへの受け渡しだけを行う。
"""
from __future__ import annotations

import shutil
from datetime import date, timedelta
from pathlib import Path

import yaml

from . import runs

PLAN_FILE = "plan.yaml"
REQUIRED = ("date", "theme", "title", "alt_titles", "aim", "failures", "figures")
TITLE_MAX = 30  # タイトルの最大字数(短くてとっつきやすいタイトルにするため。config/weekly_policy.md と合わせる)


def week_start(d: date) -> date:
    """d を含む週の月曜日。"""
    return d - timedelta(days=d.weekday())


def plan_dir(root: Path, start: date) -> Path:
    return Path(root) / "plans" / start.isoformat()


def load_plan(root: Path, start: date) -> dict | None:
    path = plan_dir(root, start) / PLAN_FILE
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise runs.RunError(f"週次企画を読めません({path}): {e}") from e
    return data


def validate_plan(root: Path, start: date) -> list[str]:
    """週次企画の形式検査。問題のリストを返す(空なら合格)。"""
    data = load_plan(root, start)
    if data is None:
        return [f"週次企画がありません: plans/{start.isoformat()}/{PLAN_FILE}"]
    problems = []
    if str(data.get("week_start")) != start.isoformat():
        problems.append(f"week_start が {start.isoformat()} ではありません")
    items = data.get("items") or []
    if len(items) != 7:
        problems.append(f"企画は7本必要です(今は{len(items)}本)")
    themes = {t["id"] for t in runs.load_themes(root) if t.get("active", True)}
    want = {(start + timedelta(days=i)).isoformat() for i in range(7)}
    seen = set()
    ai_count = 0
    for n, it in enumerate(items, 1):
        for key in REQUIRED:
            if not it.get(key):
                problems.append(f"{n}本目: {key} が空です")
        d = str(it.get("date", ""))
        if d not in want:
            problems.append(f"{n}本目: 日付 {d} がこの週(月〜日)の範囲外です")
        if d in seen:
            problems.append(f"{n}本目: 日付 {d} が重複しています")
        seen.add(d)
        if it.get("theme") and it["theme"] not in themes:
            problems.append(f"{n}本目: テーマ '{it['theme']}' は config/themes.yaml に無いか無効です")
        if len(it.get("alt_titles") or []) < 2:
            problems.append(f"{n}本目: 予備のタイトル案が2つありません")
        for t in [str(it.get("title", "")), *[str(a) for a in it.get("alt_titles") or []]]:
            if len(t) > TITLE_MAX:
                problems.append(f"{n}本目: タイトルが{len(t)}字です({TITLE_MAX}字以内に短くしてください): {t}")
        if it.get("ai"):
            ai_count += 1
        draft = it.get("draft")
        if draft and not (plan_dir(root, start) / draft).exists():
            problems.append(f"{n}本目: 下書き {draft} が見つかりません")
    if ai_count < 1:
        problems.append("AIに関する記事(ai: true)が1本もありません")
    return problems


def item_for(root: Path, d: date) -> tuple[dict, dict] | None:
    """(週次企画, その日の企画) を返す。無ければ None。"""
    start = week_start(d)
    data = load_plan(root, start)
    if not data:
        return None
    for it in data.get("items") or []:
        if str(it.get("date")) == d.isoformat():
            return data, it
    return None


def render_item(data: dict, it: dict) -> str:
    """実行フォルダに置く 00_plan.md の中身。"""
    status = "承認済み" if data.get("approved") else "未承認(ユーザー不在のため自動で進める)"
    lines = [
        f"# 今日の企画({it['date']})", "",
        f"- 週次企画: plans/{data.get('week_start')}/(状態: {status})",
        f"- テーマ: {it['theme']}",
        f"- タイトル(本案): {it['title']}",
        *[f"- 予備案{i}: {t}" for i, t in enumerate(it.get("alt_titles") or [], 1)],
        f"- 狙い: {it['aim']}",
        f"- AI記事: {'はい' if it.get('ai') else 'いいえ'}",
        f"- アフィリエイト: {('記事末尾に【リンク任意:' + it['affiliate'] + '】') if it.get('affiliate') else '入れない'}",
        "", "## 失敗パターン(読者層がやりがちなこと。一般的な事例として書く)", "",
        *[f"- {f}" for f in it.get("failures") or []],
        "", "## 入れる図", "",
        *[f"- {f}" for f in it.get("figures") or []],
    ]
    if it.get("notes"):
        lines += ["", "## メモ", "", *[f"- {x}" for x in it["notes"]]]
    if it.get("draft"):
        lines += ["", "## 下書き", "", "- 00_plan_draft.md に週次で作った下書きがある。事実・数字はリサーチで再確認したうえで、これを土台に書いてよい。"]
    lines += ["", "書き方の方針は config/weekly_policy.md に従う(config/editorial_rules.md より優先する点はそちらに明記)。"]
    return "\n".join(lines) + "\n"


def attach_to_run(root: Path, run_id: str, data: dict, it: dict) -> list[Path]:
    """今日の企画を実行フォルダへ渡す(00_plan.md・下書き・週次で作った画像)。"""
    root = Path(root)
    rdir = runs.run_path(root, run_id)
    start = date.fromisoformat(str(data["week_start"]))
    pdir = plan_dir(root, start)
    made = [rdir / "00_plan.md"]
    made[0].write_text(render_item(data, it), encoding="utf-8")
    if it.get("draft"):
        dst = rdir / "00_plan_draft.md"
        shutil.copyfile(pdir / it["draft"], dst)
        made.append(dst)
    imgs = sorted((pdir / "images").glob(f"{it['date']}_*.png")) if (pdir / "images").exists() else []
    if imgs:
        out = rdir / "images" / "plan"
        out.mkdir(parents=True, exist_ok=True)
        for p in imgs:
            shutil.copyfile(p, out / p.name)
            made.append(out / p.name)
    run = runs.read_run(root, run_id)
    run["plan"] = {"week_start": start.isoformat(), "date": str(it["date"]), "title": it["title"],
                   "approved": bool(data.get("approved"))}
    runs._save(root, run_id, run)
    return made
