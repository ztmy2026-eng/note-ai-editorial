"""タイトルの型の実験(2026-10-13〜10-26): 日付ごとに「短い型」と「2段型」を交互に出し、インプレッションで比べる。

- 短い型: 1文。30字以内(例: 「コンビニの「今日だけならいいか」が、お金を減らす」)
- 2段型: 「メイン。サブ」の2文、または「メイン｜サブ」。24〜44字(例: 「節約しているのに疲れる人へ。無理なく続ける3つの考え方」)
- 日付が奇数日=2段型、偶数日=短い型。期間の外は、これまでどおり30字以内。
背景: analytics/trend_study_2026-10-12.md(人気上位のタイトルは長く、2段が多い。ただし人気の証拠が無いので、自分たちのデータで確かめる)。
"""
from __future__ import annotations

import re
from datetime import date

EXPERIMENT_START = date(2026, 10, 13)
EXPERIMENT_END = date(2026, 10, 26)
SHORT_MAX = 30
TWO_PART_MIN = 24
TWO_PART_MAX = 44
SHORT, TWO_PART = "short", "two_part"
LABELS = {SHORT: "短い型(1文・30字以内)", TWO_PART: "2段型(「メイン。サブ」・24〜44字)"}
_SPLIT = re.compile(r"。(?=.)|[｜|―]")


def style_for(d: date) -> str | None:
    """その日に使う型。実験の期間外は None。"""
    if not (EXPERIMENT_START <= d <= EXPERIMENT_END):
        return None
    return TWO_PART if d.day % 2 else SHORT


def style_of(title: str) -> str:
    """タイトルが、どちらの型の作りか(2文か、「｜」「―」で2つに分かれていれば2段型)。"""
    return TWO_PART if _SPLIT.search(title.strip()) else SHORT


def problem(title: str, d: date) -> str | None:
    """その日の型に合っていなければ、直す点を返す(合っている・期間外なら None)。"""
    want = style_for(d)
    if want is None:
        return None
    n = len(title)
    if want == SHORT:
        if style_of(title) == TWO_PART or n > SHORT_MAX:
            return f"{d.isoformat()}は「{LABELS[SHORT]}」の日です(いまは{n}字。1文にして、{SHORT_MAX}字以内に): {title}"
    else:
        if style_of(title) != TWO_PART or not (TWO_PART_MIN <= n <= TWO_PART_MAX):
            return f"{d.isoformat()}は「{LABELS[TWO_PART]}」の日です(いまは{n}字。「メイン。サブ」の形で{TWO_PART_MIN}〜{TWO_PART_MAX}字に): {title}"
    return None


def rule_text(d: date) -> str:
    want = style_for(d)
    if want is None:
        return (f"{d.isoformat()}: タイトルの型の実験の期間外({EXPERIMENT_START.isoformat()}〜{EXPERIMENT_END.isoformat()})。"
                f"通常のルール(1本のタイトルは{SHORT_MAX}字以内)。")
    lines = [f"{d.isoformat()}: 今日のタイトルの型 = {LABELS[want]}"]
    if want == SHORT:
        lines.append(f"- 1文で{SHORT_MAX}字以内。「。」で2文に分けない。例: コンビニの「今日だけならいいか」が、お金を減らす")
    else:
        lines.append(f"- 「メイン。サブ」の2文(または「メイン｜サブ」)で、合計{TWO_PART_MIN}〜{TWO_PART_MAX}字。メインは悩み・問い・意外な一言、サブは中身(数字を1つ)。")
        lines.append("- 例: 節約しているのに疲れる人へ。無理なく続ける3つの考え方(体験の形にしない。出典のある一般論で書ける題材にする)")
    lines.append("- 予備のタイトル案も、同じ型にする。" + ("見出し画像は、メインを大きく、サブを帯にして入れる(figures.json の title_html と sub)。" if want == TWO_PART else "見出し画像は、タイトルを大きく入れる。"))
    return "\n".join(lines)
