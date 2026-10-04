"""編集長(Editor-in-Chief)=進行管理。AIは使わない普通のプログラム。

やること:各実行の「次の一手」を決める / 承認待ちを集める / 上限と品質シグナルを集計 / 朝のブリーフィングを書く。
毎回AIに判断させるとコストが増えるので、判断ルールはコードに固定してある。
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path

from . import analytics, artifacts, articles, limits, runs

AGENT_FOR_STEP = {
    "research": "リサーチAgent",
    "ideas": "企画Agent",
    "draft": "ライターAgent",
    "critique": "批評Agent",
    "revised": "編集Agent",
    "sns": "SNS Agent",
}


def next_action(root: Path, run_id: str) -> tuple[str, bool]:
    """(次の一手, 人間の作業が必要か) を返す。"""
    d = runs.read_run(root, run_id)
    done, ap = d["steps_done"], d["approvals"]
    if d.get("skipped"):
        return "見送り済み(投稿しない)", False
    auto = limits.load(root)["auto_approve"]
    rdir = runs.run_path(root, run_id)
    for step in ("research", "ideas"):
        if step not in done:
            return f"{AGENT_FOR_STEP[step]}を実行", False
    if not ap["idea"] and auto:
        return f"承認なしモード:`auto-approve {run_id}` でおすすめ企画を採用", False
    if not ap["idea"]:
        return f"【承認1】02_ideas.md を読み、`approve-idea {run_id} <候補番号>` で企画を選ぶ", True
    for step in ("draft", "critique", "revised"):
        if step not in done:
            return f"{AGENT_FOR_STEP[step]}を実行", False
    if not ap["publish"]:
        revised = rdir / artifacts.FILES["revised"]
        ph, uv = artifacts.count_placeholders(revised), artifacts.count_unverified(revised)
        if ph or uv:
            return f"記事の空欄【要入力】{ph}件・「要確認」{uv}件を、あなたが埋める/確認する(その後、編集・批評を再実行)", True
        if auto:
            return f"承認なしモード:`auto-approve {run_id}` で公開準備", False
        return f"【承認2】05_revised.md を読み、問題なければ `approve-publish {run_id}`", True
    if "sns" not in done:
        return "SNS Agentを実行", False
    if not ap.get("sns") and auto:
        return f"承認なしモード:`auto-approve {run_id}` でSNS案を承認", False
    if not ap.get("sns"):
        return f"【承認3】06_sns.md を読み、問題なければ `approve-sns {run_id}`", True
    if d.get("posted"):
        return "投稿済み", False
    if d.get("skipped"):
        return "見送り済み(投稿しない)", False
    return f"完了:note_post/(`export-note`)と 06_sns.md・images/ を使って、noteとSNSへ手動で投稿。投稿したら `mark-posted {run_id} --url <記事URL>`", True


def read_log(root: Path) -> list[dict]:
    path = Path(root) / "logs" / "events.jsonl"
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # 壊れた行は無視(ログ分析のために全体を止めない)
    return events


def quality_signals(events: list[dict]) -> dict:
    return {
        "rejected_by_step": dict(Counter(e.get("step", "?") for e in events if e.get("event") == "step_rejected")),
        "reopened": sum(1 for e in events if e.get("event") == "run_reopened"),
        "limit_hits": sum(1 for e in events if e.get("event") == "run_blocked_by_limit"),
    }


def suggestions(root: Path, signals: dict, art_summary: dict, hyp_problems: list[str] | None) -> list[str]:
    out = []
    if art_summary["count"] == 0:
        out.append("過去記事が1本も読み込めていません。`data/past_articles/` に記事を置いてください(形式は README 参照)")
    elif art_summary["samples"] == art_summary["count"]:
        out.append("過去記事がサンプル(架空)のままです。`data/past_articles/` に実記事とPV・スキを入れると、企画と分析の精度が上がります")
    elif art_summary["without_metrics"]:
        out.append(f"数値(PV・スキ等)が無い記事が{art_summary['without_metrics']}本あります。分かる範囲で追記してください")
    for step, n in signals["rejected_by_step"].items():
        if n >= 2:
            out.append(f"「{step}」の検品不合格が{n}回。指示書(.claude/agents/)の見直し候補です")
    if signals["reopened"] >= 2:
        out.append(f"やり直し(reopen)が{signals['reopened']}回。初回の材料(体験の回答など)を先に集めると手戻りが減ります")
    if signals["limit_hits"]:
        out.append(f"1日の実行上限に{signals['limit_hits']}回達しました。必要なら config/limits.yaml を見直してください")
    if hyp_problems:
        out.append("仮説台帳に形式の問題があります: " + " / ".join(hyp_problems[:2]))
    return out


def briefing(root: Path, today: date | None = None) -> str:
    root = Path(root)
    today = today or date.today()
    loaded, source = articles.load_with_fallback(root)
    art_summary = articles.summarize(loaded.articles)
    signals = quality_signals(read_log(root))
    hyp = root / "analytics" / "hypotheses.md"
    hyp_problems = analytics.validate_hypotheses(hyp) if hyp.exists() else None

    use = limits.usage(root, today)
    stops = limits.reached(root, today)
    lines = [f"# 編集部ブリーフィング {today.isoformat()}", "",
             f"- 承認: {'承認なしモード(自動)。検品は有効、投稿は常に手動' if limits.load(root)['auto_approve'] else '手動承認'}",
             f"- 今日の実行数: {use['runs'][0]} / {use['runs'][1]}、Agent作業数: {use['steps'][0]} / {use['steps'][1]}、"
             f"未投稿の公開準備済み: {use['queue'][0]} / {use['queue'][1]}",
             *([f"- **停止中**: {'; '.join(stops)}"] if stops else []),
             f"- 過去記事: {art_summary['count']}本(数値あり {art_summary['with_metrics']}、"
             f"{'サンプル(架空)' if source == 'samples' else '実データ'})", ""]
    ids = sorted(p.parent.name for p in (root / "runs").glob("*/run.json"))
    waiting, rows = [], []
    for rid in ids:
        d = runs.read_run(root, rid)
        action, human = next_action(root, rid)
        rows.append(f"| {rid} | {d['theme_name']} | {d['status']} | {action} |")
        if human:
            waiting.append(f"- **{rid}**: {action}")
    lines += ["## あなたの確認待ち", ""] + (waiting or ["- なし"]) + ["", "## 実行一覧", ""]
    lines += ["| 実行ID | テーマ | 状態 | 次の一手 |", "|---|---|---|---|"] + (rows or ["| (なし) | | | |"])
    lines += ["", "## 品質・コストのシグナル(ログより)", "",
              f"- 検品不合格: {signals['rejected_by_step'] or 'なし'}",
              f"- やり直し回数: {signals['reopened']} / 上限到達: {signals['limit_hits']}", ""]
    if hyp_problems is None:
        lines += ["## 仮説台帳", "", "- まだありません(分析Agentで作成)", ""]
    else:
        lines += ["## 仮説台帳", "", "- 形式OK" if not hyp_problems else f"- 形式の問題あり: {hyp_problems}", ""]
    sugg = suggestions(root, signals, art_summary, hyp_problems)
    lines += ["## 次に改善すべきこと", ""] + ([f"- {s}" for s in sugg] or ["- 現時点で検知した問題はありません"])
    return "\n".join(lines) + "\n"


def write_briefing(root: Path, today: date | None = None) -> Path:
    today = today or date.today()
    out = Path(root) / "briefing"
    out.mkdir(exist_ok=True)
    path = out / f"{today.isoformat()}.md"
    path.write_text(briefing(root, today), encoding="utf-8")
    return path


def next_theme(root: Path) -> str:
    """次に記事を作るテーマ。有効なテーマのうち、これまでの実行数が最も少ないもの(同数なら優先度が高い方)。

    優先度の高いテーマが多めになるよう、実行数が同じなら priority 順。偏りすぎを防ぐため単純な「実行数の少ない順」を基本にする。
    """
    root = Path(root)
    themes = [t for t in runs.load_themes(root) if t.get("active", True)]
    if not themes:
        raise runs.RunError("有効なテーマがありません(config/themes.yaml)")
    counts = Counter()
    for p in (root / "runs").glob("*/run.json"):
        try:
            counts[json.loads(p.read_text(encoding="utf-8")).get("theme")] += 1
        except json.JSONDecodeError:
            continue
    return min(themes, key=lambda t: (counts[t["id"]], t.get("priority", 99)))["id"]
