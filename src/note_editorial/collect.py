"""noteの通知メールから反応の数値を集める(メールを読む部分はClaude Code側のGmail連携が担当)。

役割分担:
  Claude Code(Gmail連携) … 通知メールを検索して、日付と本文の断片をJSONにまとめる(リポジトリの外の一時ファイル)
  このモジュール(Python) … 断片から「記事タイトル」と「スキの数」を取り出して集計し、数値だけを記録する
個人情報への配慮: スキ・フォローしてくれた人の名前やプロフィールは**記録しない**(記事ごとの数・日ごとの数だけ)。
注意: メールのスキ数は「その時点の累計」と思われるが、取り消しで減ることがある。最新の値を採用し、確定値はダッシュボードで確認する。
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from . import articles, learn, limits, runs
from .log import log_event

LIKE_RE = re.compile(r"作品が読者に届いています！\s*(?P<title>.+?)\s+見出し画像\s+(?P<a>\S+)\s+(?P=a)\s+(?P<n>\d+)\s+スキしてくれた人")


def parse_like_snippet(snippet: str) -> tuple[str, int] | None:
    """スキ通知の本文の断片 → (記事タイトル, その時点のスキ数)。読み取れなければ None。"""
    m = LIKE_RE.search(snippet or "")
    return (m.group("title").strip(), int(m.group("n"))) if m else None


def aggregate_likes(records: list[dict]) -> tuple[dict[str, dict], list[str]]:
    """{タイトル: {"likes": 最新の値, "events": 通知の数}} と、読めなかった件の一覧。"""
    by_title: dict[str, list[tuple[str, int]]] = {}
    problems = []
    for r in records:
        parsed = parse_like_snippet(r.get("snippet", ""))
        if parsed is None:
            problems.append(f"読み取れない通知: {r.get('date', '?')}")
            continue
        by_title.setdefault(parsed[0], []).append((r.get("date", ""), parsed[1]))
    out = {}
    for title, rows in by_title.items():
        rows.sort()  # 日付の古い順(ISO形式なので文字列順でよい)
        out[title] = {"likes": rows[-1][1], "events": len(rows), "last": rows[-1][0]}
    return out, problems


def follows_by_day(timestamps: list[str], tz) -> dict[str, int]:
    days: dict[str, int] = {}
    for ts in timestamps:
        day = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(tz).date().isoformat()
        days[day] = days.get(day, 0) + 1
    return days


def _stub_path(root: Path, title: str) -> Path:
    h = hashlib.sha1(title.encode("utf-8")).hexdigest()[:8]
    return Path(root) / "data" / "past_articles" / f"email_{h}.md"


def _find_by_title(root: Path, title: str) -> Path | None:
    for p in sorted((Path(root) / "data" / "past_articles").glob("*.md")):
        try:
            meta, _ = articles._split_front_matter(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if str(meta.get("title", "")).strip() == title:
            return p
    return None


def apply_likes(root: Path, likes: dict[str, dict]) -> list[str]:
    """集計したスキ数を data/past_articles/ に反映する。無い記事は『メール由来の記録(本文なし)』として作る。"""
    root = Path(root)
    today = limits.today_local(root)
    notes = []
    for title, info in likes.items():
        path = _find_by_title(root, title)
        if path is None:
            path = _stub_path(root, title)
            path.parent.mkdir(parents=True, exist_ok=True)
            meta = {"title": title, "url": "", "published": None, "theme": "", "impressions": None, "pv": None, "likes": None,
                    "revenue": None, "followers_gained": None, "cta": "", "sample": False, "source": "email"}
            path.write_text(learn._dump(meta, "(本文は未登録です。通知メールから作った記録です。本文を `data/past_articles/` に貼ると分析に使えます)"), encoding="utf-8")
            notes.append(f"新規(メール由来): {title}")
        meta, body = articles._split_front_matter(path.read_text(encoding="utf-8"))
        if str(meta.get("likes_source", "")).startswith(learn.MANUAL):
            notes.append(f"手入力を優先して更新しない: {title}")
            continue
        meta["likes"] = info["likes"]
        meta["likes_source"] = "email(最新の通知の値。取り消しで減ることがある推定値)"
        meta["metrics_updated"] = today
        path.write_text(learn._dump(meta, body), encoding="utf-8")
        notes.append(f"スキ {info['likes']}: {title}")
    return notes


def write_followers(root: Path, days: dict[str, int]) -> Path:
    """日ごとの新規フォロー数を analytics/followers.csv に保存(同じ日は上書き=何度実行しても重複しない)。"""
    path = Path(root) / "analytics" / "followers.csv"
    path.parent.mkdir(exist_ok=True)
    current: dict[str, int] = {}
    if path.exists():
        with open(path, encoding="utf-8", newline="") as f:
            current = {r["date"]: int(r["new_followers"]) for r in csv.DictReader(f)}
    current.update(days)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "new_followers"])
        for d in sorted(current):
            w.writerow([d, current[d]])
    return path


def collect(root: Path, data_file: Path) -> list[str]:
    root = Path(root)
    try:
        raw = json.loads(Path(data_file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise runs.RunError(f"収集データを読めません: {e}") from e
    likes, problems = aggregate_likes(raw.get("likes", []))
    out = apply_likes(root, likes)
    days = follows_by_day(raw.get("follows", []), limits._tz(limits.load(root)))
    if days:
        write_followers(root, days)
        out.append(f"新規フォロー: {sum(days.values())}件({len(days)}日分)→ analytics/followers.csv")
    out += [f"[注意] {p}" for p in problems]
    log_event(root, "metrics_collected", articles=len(likes), follow_days=len(days), unreadable=len(problems))
    return out
