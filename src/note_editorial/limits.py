"""1日あたりの上限(コスト・暴走の防止)。

- max_runs_per_day        : 1日に作れる「実行(記事1本分)」の数
- max_agent_steps_per_day : 1日に完了できるAgent作業の数(1ステップ=Agent1回分の目安。コストの代わりの物差し)
- max_ready_queue         : 「公開準備済みなのに、まだ投稿していない記事」がこの数に達したら止まる(読み切れない在庫を作らない)
上限に達したら、新しい作業を始めない。
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import yaml

DEFAULTS = {
    "max_runs_per_day": 3,
    "max_agent_steps_per_day": 30,
    "max_ready_queue": 3,
    "auto_approve": False,
    "timezone": "Asia/Tokyo",
}


def load(root: Path) -> dict:
    path = Path(root) / "config" / "limits.yaml"
    try:
        user = yaml.safe_load(path.read_text(encoding="utf-8")) or {} if path.exists() else {}
    except (OSError, yaml.YAMLError):
        user = {}
    return {**DEFAULTS, **user}


def _tz(cfg: dict):
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(str(cfg["timezone"]))
    except Exception:  # tzdata が無い等。システムの時刻で代用
        return None


def today_local(root: Path) -> date:
    return datetime.now(_tz(load(root))).date()


def _events(root: Path) -> list[dict]:
    path = Path(root) / "logs" / "events.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _local_date(iso: str, tz) -> date | None:
    try:
        return datetime.fromisoformat(iso).astimezone(tz).date()
    except (ValueError, TypeError):
        return None


def ready_queue(root: Path) -> list[str]:
    """公開承認済みで、まだ「投稿済み」の記録も「見送り」の記録もない実行ID。"""
    ids = []
    for p in sorted((Path(root) / "runs").glob("*/run.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if d.get("approvals", {}).get("publish") and not d.get("posted") and not d.get("skipped"):
            ids.append(d["run_id"])
    return ids


def usage(root: Path, today: date | None = None) -> dict:
    cfg = load(root)
    tz = _tz(cfg)
    today = today or datetime.now(tz).date()
    runs_dir = Path(root) / "runs"
    runs_today = len([p for p in runs_dir.glob(f"{today.isoformat()}_*") if p.is_dir()]) if runs_dir.exists() else 0
    steps_today = sum(1 for e in _events(root) if e.get("event") == "step_done" and _local_date(e.get("time", ""), tz) == today)
    return {"runs": (runs_today, int(cfg["max_runs_per_day"])),
            "steps": (steps_today, int(cfg["max_agent_steps_per_day"])),
            "queue": (len(ready_queue(root)), int(cfg["max_ready_queue"]))}


LABELS = {"runs": "今日の実行数", "steps": "今日のAgent作業数", "queue": "未投稿の公開準備済み記事"}


def reached(root: Path, today: date | None = None, new_run: bool = True) -> list[str]:
    """上限に達している理由の一覧。

    new_run=True : 新しい実行を作り始める前の確認。実行数・Agent作業数・未投稿の在庫の全てを見る。
    new_run=False: すでに作り始めた実行の続きの確認。見るのはAgent作業数だけ。
                   (作業中の記事自身が「今日の実行数」や「未投稿の在庫」に入っているため、続きの作業を止めてはいけない)
    """
    keys = None if new_run else {"steps"}
    return [f"{LABELS[k]}が上限に達しています({used}/{cap})"
            for k, (used, cap) in usage(root, today).items()
            if used >= cap and (keys is None or k in keys)]
