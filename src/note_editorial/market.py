"""他の人の記事(タイトルとスキ数)から、金融・保険・投資・節約の分野の「型」を調べる。

入力は人が集めた data/market/items.csv だけ(プログラムでnoteのページは読まない)。
サンプルが少ないうちは傾向とは言わず、仮説の材料として扱う(MIN_N 未満は『参考程度』)。
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

MIN_N = 30  # この件数未満は「傾向」と呼ばない
TOPICS = {
    "保険": ("保険", "共済", "高額療養"),
    "投資": ("投資", "NISA", "iDeCo", "ideco", "株", "資産形成", "資産運用", "FX", "インデックス"),
    "税・制度": ("税", "控除", "年末調整", "確定申告", "ふるさと納税", "年金", "給付"),
    "節約・家計": ("節約", "家計", "固定費", "ポイ活", "お小遣い", "支出", "貯金", "貯蓄"),
}


def classify(title: str) -> str:
    for topic, words in TOPICS.items():
        if any(w.lower() in title.lower() for w in words):
            return topic
    return "その他のお金"


def features(title: str) -> dict[str, bool]:
    return {
        "数字を含む": bool(re.search(r"\d|[０-９]", title)),
        "【】で始まる": title.startswith("【"),
        "体験・実践の言葉": bool(re.search(r"実体験|やってみた|試した|失敗|体験|記録|ログ|私が|僕が|してみた", title)),
        "疑問形": bool(re.search(r"[?？]|でしょうか|のか", title)),
        "30字以上": len(title) >= 30,
    }


def load_items(path: Path) -> tuple[list[dict], list[str]]:
    items, problems = [], []
    path = Path(path)
    if not path.exists():
        return items, [f"ファイルがありません: {path}"]
    with open(path, encoding="utf-8", newline="") as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            title = (row.get("title") or "").strip()
            try:
                likes = int(str(row.get("likes", "")).replace(",", ""))
                if likes < 0:
                    raise ValueError
            except ValueError:
                problems.append(f"{i}行目: likes は0以上の整数で書いてください")
                continue
            if not title:
                problems.append(f"{i}行目: title が空です")
                continue
            items.append({"title": title, "likes": likes, "topic": (row.get("topic") or "").strip() or classify(title)})
    return items, problems


def _avg(xs: list[int]) -> float | None:
    return sum(xs) / len(xs) if xs else None


def render(items: list[dict]) -> str:
    n = len(items)
    out = ["# 市場データの分析(他の人の記事)", "", "※ 計算はPythonが行った事実のみ。解釈は含まれません。", ""]
    if n < MIN_N:
        out += [f"> ⚠ 記事が{n}件のみ(傾向とみなすには{MIN_N}件以上が目安)。**参考程度**です。投稿からの日数や作者のフォロワー数が違うため、スキ数の単純な比較はできません。", ""]
    if not items:
        return "\n".join(out + ["- データなし", ""])
    out += [f"- 記事数: {n}", "", "## トピック別", "", "| トピック | n | 平均スキ | 最大スキ |", "|---|---|---|---|"]
    for topic in sorted({i["topic"] for i in items}):
        ls = [i["likes"] for i in items if i["topic"] == topic]
        out.append(f"| {topic} | {len(ls)} | {_avg(ls):.1f} | {max(ls)} |")
    out += ["", "## タイトルの特徴別(平均スキ)", "", "| 特徴 | あり(n) | なし(n) |", "|---|---|---|"]
    for name in features("x"):
        yes = [i["likes"] for i in items if features(i["title"])[name]]
        no = [i["likes"] for i in items if not features(i["title"])[name]]
        f = lambda xs: f"{_avg(xs):.1f} ({len(xs)})" if xs else "データなし (0)"
        out.append(f"| {name} | {f(yes)} | {f(no)} |")
    out += ["", "## スキ数の多い順", ""]
    out += [f"{k}. {i['likes']}  {i['title']}({i['topic']})" for k, i in enumerate(sorted(items, key=lambda i: -i["likes"])[:10], 1)]
    return "\n".join(out) + "\n"
