"""noteのタグのページから、他の人の記事のタイトルとスキ数を、少数だけ集める(2026-11-08 持ち主の指示)。

守ること(note.com/robots.txt と、礼儀):
- 読むのは、タグの一覧ページ(/tag/…)と、記事のページ(/…/n/…)だけ。/api/ と /search は読まない(robots.txtで禁止)。
- 1回に読むのは、タグ数 × 件数 の少数(既定: 6タグ × 12件 = 約80ページ)。1ページごとに2.5秒あけて、順番に読む。
- 身元を隠さない(User-Agent に用途を書く)。429・403・ロボット確認が出たら、すぐやめる(回避しない)。
- 集めるのはタイトルとスキ数だけ(本文・作者名は保存しない)。data/market/items.csv に追記し、analytics/ に順位表を書く。
使い方: python -m note_editorial.market_fetch [--tags 節約,ポイ活] [--per-tag 12]
"""
from __future__ import annotations

import argparse
import csv
import datetime
import html
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = "note-ai-editorial-research/1.0 (personal market research; polite, low volume)"
DELAY = 2.5
DEFAULT_TAGS = ["節約", "ポイ活", "お金", "副業", "家計管理", "電気代"]
ITEMS = Path("data/market/items.csv")


class Stop(Exception):
    pass


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code in (403, 429, 503):
            raise Stop(f"{url} が {e.code} を返したので、ここでやめます(回避しません)")
        raise


def tag_articles(tag: str) -> list[tuple[str, str]]:
    t = _get("https://note.com/tag/" + urllib.parse.quote(tag))
    out, seen = [], set()
    for m in re.finditer(r'title="([^"]+)" href="(https://note\.com/[^"/]+/n/[a-z0-9]+)"', t):
        title, url = html.unescape(m.group(1)), m.group(2)
        if url not in seen:
            seen.add(url)
            out.append((title, url))
    return out


def like_count(url: str) -> int | None:
    t = _get(url)
    m = re.search(r'\\?"noteLikeCount\\?":(\d+)', t) or re.search(r'\\?"likeCount\\?":(\d+)', t)
    return int(m.group(1)) if m else None


def run(tags: list[str], per_tag: int, items: Path = ITEMS, out_dir: Path = Path("analytics")) -> list[dict]:
    today = datetime.date.today().isoformat()
    rows: list[dict] = []
    seen_urls: set[str] = set()
    try:
        for tag in tags:
            arts = tag_articles(tag)
            time.sleep(DELAY)
            n = 0
            for title, url in arts:
                if n >= per_tag:
                    break
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                likes = like_count(url)
                time.sleep(DELAY)
                n += 1
                if likes is not None:
                    rows.append({"title": title, "likes": likes, "tag": tag})
    except Stop as e:
        print("[停止]", e)
    # items.csv に追記(タイトル重複は入れない)
    existing = set()
    if items.exists():
        with items.open(encoding="utf-8", newline="") as f:
            existing = {r["title"] for r in csv.DictReader(f)}
    new = [r for r in rows if r["title"] not in existing]
    if new:
        with items.open("a", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            for r in new:
                w.writerow([r["title"], r["likes"], "", f"noteタグ「{r['tag']}」(自動取得)", today])
    # 順位表
    rows.sort(key=lambda r: -r["likes"])
    out_dir.mkdir(exist_ok=True)
    md = [f"# noteタグの記事のスキ数(自動取得) {today}", "",
          "※ 取得したのは、タグの一覧に出た記事のうち、各タグ先頭から少数。スキ数は見た時点のもの。投稿日・作者のフォロワー数が違うので、単純な比較はできない(参考程度)。", "",
          "| スキ | タイトル | タグ |", "|---|---|---|"]
    md += [f"| {r['likes']} | {r['title'].replace('|', '/')} | {r['tag']} |" for r in rows]
    (out_dir / f"note_tag_likes_{today}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"取得 {len(rows)} 件 / items.csv に追記 {len(new)} 件")
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", default=",".join(DEFAULT_TAGS))
    ap.add_argument("--per-tag", type=int, default=12)
    a = ap.parse_args()
    run([x for x in a.tags.split(",") if x], a.per_tag)
