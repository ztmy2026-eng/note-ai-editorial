"""投稿した記事を「あなた自身のデータ」として蓄積し、反応の数値を後から入れる。

流れ: mark-posted → data/past_articles/<日付>_<実行ID>.md を作る(数値は空=データなし)
      → record-metrics で PV・スキ・売上・フォロワー増 を追記(手入力でも、メールからの収集結果でも同じ入口を使う)
サンプル(架空)データは、実記事が1本でもあれば使われなくなる(articles.load_with_fallback)。
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml

from . import articles, limits, runs
from .log import log_event

METRIC_KEYS = ("impressions", "pv", "likes", "revenue", "followers_gained")
DASHBOARD_METRICS = ("impressions", "pv", "likes")  # ダッシュボードで編集できる項目
MANUAL = "手入力"


def _dump(meta: dict, body: str) -> str:
    front = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{front}\n---\n{body.strip()}\n"


def find_article_file(root: Path, run_id: str) -> Path | None:
    for p in sorted((Path(root) / "data" / "past_articles").glob("*.md")):
        try:
            meta, _ = articles._split_front_matter(p.read_text(encoding="utf-8"))
        except (ValueError, yaml.YAMLError):
            continue
        if meta.get("run_id") == run_id:
            return p
    return None


def add_posted_article(root: Path, run_id: str) -> Path:
    """投稿済みの記事を data/past_articles/ に登録する。すでにあれば何もしない(数値を消さない)。"""
    root = Path(root)
    existing = find_article_file(root, run_id)
    if existing:
        return existing
    data = runs.read_run(root, run_id)
    if not data.get("posted"):
        raise runs.RunError("投稿済みの記録(mark-posted)がありません")
    rdir = runs.run_path(root, run_id)
    title = (rdir / "note_post" / "title.txt").read_text(encoding="utf-8").strip()
    body = (rdir / "note_post" / "body.md").read_text(encoding="utf-8")
    tz = limits._tz(limits.load(root))
    posted_date = datetime.fromisoformat(data["posted"]["at"]).astimezone(tz).date()
    meta = {"title": title, "url": data["posted"].get("url", ""), "published": posted_date, "theme": data["theme"],
            "impressions": None, "pv": None, "likes": None, "revenue": None, "followers_gained": None,
            "cta": "", "sample": False, "run_id": run_id}
    out_dir = root / "data" / "past_articles"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{posted_date.isoformat()}_{run_id}.md"
    out.write_text(_dump(meta, body), encoding="utf-8")
    log_event(root, "past_article_added", run_id=run_id)
    return out


def record_metrics(root: Path, run_id: str, **values: int | None) -> Path:
    """数値を追記・更新する。指定しなかった項目は変えない。負の数は受け付けない。"""
    root = Path(root)
    path = find_article_file(root, run_id)
    if path is None:
        raise runs.RunError(f"{run_id} は data/past_articles/ にありません(先に mark-posted)")
    updates = {k: v for k, v in values.items() if k in METRIC_KEYS and v is not None}
    if not updates:
        raise runs.RunError("更新する数値がありません(--pv --likes --revenue --followers のどれかを指定)")
    for k, v in updates.items():
        if v < 0:
            raise runs.RunError(f"{k} は0以上にしてください")
    meta, body = articles._split_front_matter(path.read_text(encoding="utf-8"))
    meta.update(updates)
    meta["metrics_updated"] = limits.today_local(root)
    path.write_text(_dump(meta, body), encoding="utf-8")
    log_event(root, "metrics_recorded", run_id=run_id, **updates)
    return path


def article_id(path: Path, meta: dict) -> str:
    """ダッシュボードとの対応に使う記事ID。システムで作った記事は実行ID、メール由来の記録はファイル名。"""
    return str(meta.get("run_id") or Path(path).stem)


def export_metrics(root: Path) -> dict:
    """ダッシュボード(共有データ)に載せる内容。記事ごとの数値と、日ごとの新規フォロー数。"""
    root = Path(root)
    rows = []
    for p in sorted((root / "data" / "past_articles").glob("*.md")):
        try:
            meta, _ = articles._split_front_matter(p.read_text(encoding="utf-8"))
        except (ValueError, yaml.YAMLError):
            continue
        src = {k: ("manual" if str(meta.get(f"{k}_source", "")).startswith(MANUAL) else "auto")
               for k in DASHBOARD_METRICS if meta.get(k) is not None}
        rows.append({"id": article_id(p, meta), "title": str(meta.get("title", "")), "theme": str(meta.get("theme") or ""),
                     "published": str(meta.get("published") or ""), "url": str(meta.get("url") or ""),
                     **{k: meta.get(k) for k in DASHBOARD_METRICS}, "src": src})
    followers = []
    csv_path = root / "analytics" / "followers.csv"
    if csv_path.exists():
        import csv
        with open(csv_path, encoding="utf-8", newline="") as f:
            followers = [{"date": r["date"], "new_followers": int(r["new_followers"])} for r in csv.DictReader(f)]
    return {"articles": rows, "followers": followers}


def import_metrics(root: Path, rows: list[dict]) -> list[str]:
    """ダッシュボードで人が直した数字だけを取り込む(src が manual の項目)。手入力は、メール収集より優先される。"""
    root = Path(root)
    by_id = {}
    for p in sorted((root / "data" / "past_articles").glob("*.md")):
        try:
            meta, _ = articles._split_front_matter(p.read_text(encoding="utf-8"))
        except (ValueError, yaml.YAMLError):
            continue
        by_id[article_id(p, meta)] = p
    notes = []
    for row in rows:
        path = by_id.get(str(row.get("id")))
        if path is None:
            notes.append(f"[注意] 対応する記事がありません: {row.get('id')}")
            continue
        meta, body = articles._split_front_matter(path.read_text(encoding="utf-8"))
        changed = []
        for k in DASHBOARD_METRICS:
            v = row.get(k)
            if (row.get("src") or {}).get(k) != "manual" or isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0:
                continue
            v = int(v)
            if meta.get(k) != v or not str(meta.get(f"{k}_source", "")).startswith(MANUAL):
                meta[k] = v
                meta[f"{k}_source"] = f"{MANUAL}(ダッシュボード)"
                changed.append(f"{k}={v}")
        if changed:
            meta["metrics_updated"] = limits.today_local(root)
            path.write_text(_dump(meta, body), encoding="utf-8")
            notes.append(f"{row.get('title', row['id'])}: " + ", ".join(changed))
    log_event(root, "metrics_imported", updated=len(notes))
    return notes
