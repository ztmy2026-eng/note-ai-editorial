"""過去記事の数値分析(計算はAIではなくPythonが行う)。

AIが暗算すると間違えるため、集計はここで行い、AI(分析Agent)は結果を読んで「仮説」を立てるだけにする。
サンプル数が少ないうちは「参考程度」と明記し、断定しない。
"""
from __future__ import annotations

import re
from pathlib import Path

from .articles import Article

MIN_N_FOR_TREND = 10  # これ未満は傾向と呼ばず「参考程度」
HYP_LABELS = ("仮説", "根拠(事実)", "信頼度", "検証方法", "状態")
HYP_STATES = ("検証中", "支持", "棄却", "保留")


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def like_rate(a: Article) -> float | None:
    """スキ率=スキ÷PV。どちらかが無い、PVが0なら None。"""
    if a.pv is None or a.likes is None or a.pv == 0:
        return None
    return a.likes / a.pv


def title_features(title: str) -> dict[str, bool]:
    return {
        "タイトルに数字を含む": bool(re.search(r"\d|[０-９]", title)),
        "タイトルが疑問形": bool(re.search(r"[?？]|でしょうか|ですか", title)),
        "タイトルに体験表現(話・感想・記録・失敗)": bool(re.search(r"話|感想|記録|失敗|体験", title)),
        "タイトルが30字以上": len(title) >= 30,
    }


def _group(arts: list[Article]) -> dict:
    rates = [r for r in (like_rate(a) for a in arts) if r is not None]
    return {
        "n": len(arts),
        "avg_impressions": _mean([a.impressions for a in arts if a.impressions is not None]),
        "avg_pv": _mean([a.pv for a in arts if a.pv is not None]),
        "avg_like_rate": _mean(rates),
        "total_revenue": sum(a.revenue for a in arts if a.revenue is not None),
        "total_followers": sum(a.followers_gained for a in arts if a.followers_gained is not None),
    }


def compute_facts(articles: list[Article]) -> dict:
    measured = [a for a in articles if a.has_metrics]
    by_theme: dict[str, list[Article]] = {}
    for a in measured:
        by_theme.setdefault(a.theme or "(未設定)", []).append(a)
    features: dict[str, dict] = {}
    for name in title_features("x"):
        yes = [a for a in measured if title_features(a.title)[name]]
        no = [a for a in measured if not title_features(a.title)[name]]
        features[name] = {"あり": _group(yes), "なし": _group(no)}
    ranked = sorted((a for a in measured if like_rate(a) is not None), key=lambda a: like_rate(a), reverse=True)
    return {
        "total": len(articles),
        "measured": len(measured),
        "unmeasured": len(articles) - len(measured),
        "all_samples": bool(articles) and all(a.is_sample for a in articles),
        "small_sample": len(measured) < MIN_N_FOR_TREND,
        "by_theme": {k: _group(v) for k, v in by_theme.items()},
        "features": features,
        "ranking": [(a.title, like_rate(a), a.pv) for a in ranked],
    }


def _f(v, pct=False) -> str:
    if v is None:
        return "データなし"
    return f"{v * 100:.1f}%" if pct else f"{v:,.0f}"


def render_facts(facts: dict) -> str:
    out = ["# 過去記事の集計(事実)", "", "※ この章はPythonが計算した数字のみ。解釈(仮説)は含まれません。", ""]
    if facts["all_samples"]:
        out += ["> ⚠ **すべて架空のサンプルデータ**です。実際の傾向ではありません。", ""]
    if facts["small_sample"]:
        out += [f"> ⚠ 数値のある記事が{facts['measured']}本のみ(傾向とみなすには{MIN_N_FOR_TREND}本以上が目安)。**参考程度**です。", ""]
    out += [f"- 記事数: {facts['total']}(数値あり {facts['measured']} / データなし {facts['unmeasured']})", "",
            "## テーマ別", "", "| テーマ | n | 平均インプ | 平均PV | 平均スキ率 | 収益合計 | フォロワー増合計 |", "|---|---|---|---|---|---|---|"]
    for k, g in facts["by_theme"].items():
        out.append(f"| {k} | {g['n']} | {_f(g['avg_impressions'])} | {_f(g['avg_pv'])} | {_f(g['avg_like_rate'], True)} | {g['total_revenue']:,} | {g['total_followers']:,} |")
    out += ["", "## タイトルの特徴別(スキ率の平均)", "", "| 特徴 | あり(n) | なし(n) |", "|---|---|---|"]
    for name, g in facts["features"].items():
        y, n = g["あり"], g["なし"]
        out.append(f"| {name} | {_f(y['avg_like_rate'], True)} ({y['n']}) | {_f(n['avg_like_rate'], True)} ({n['n']}) |")
    out += ["", "## スキ率ランキング", ""]
    out += [f"{i}. {t}(スキ率 {_f(r, True)} / PV {_f(pv)})" for i, (t, r, pv) in enumerate(facts["ranking"], 1)] or ["- データなし"]
    return "\n".join(out) + "\n"


def validate_hypotheses(path: Path) -> list[str]:
    """仮説台帳の形式検査。各仮説に根拠(事実)・信頼度・検証方法・状態が必要。"""
    path = Path(path)
    if not path.exists():
        return [f"ファイルがありません: {path.name}"]
    text = path.read_text(encoding="utf-8")
    blocks = re.findall(r"^###\s*H\d+.*?(?=^###\s*H\d+|^##\s|\Z)", text, re.M | re.S)
    if not blocks:
        return ["仮説(### H1 …)が1件もありません"]
    errs = []
    for b in blocks:
        hid = re.match(r"###\s*(H\d+)", b).group(1)
        missing = [lb for lb in HYP_LABELS if lb not in b]
        if missing:
            errs.append(f"{hid}: 項目が足りません: {', '.join(missing)}")
        m = re.search(r"状態\*{0,2}\s*[::]\s*\**\s*(\S+)", b)
        if m and not any(m.group(1).startswith(s) for s in HYP_STATES):
            errs.append(f"{hid}: 状態は {'/'.join(HYP_STATES)} のいずれか")
    return errs
