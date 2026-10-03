"""過去記事の取り込み。

1記事=1つのMarkdownファイル。先頭に「---」で囲んだ情報(front matter)を書く。
数値(PV・スキ・売上など)は空でもよい。空は None(=データなし)として扱い、エラーにしない。
壊れたファイルがあっても全体は止めず、problems に理由を溜めて報告する。
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

NUMERIC_FIELDS = ("pv", "likes", "revenue", "followers_gained")


@dataclass
class Article:
    path: Path
    title: str
    theme: str = ""
    url: str = ""
    published: date | None = None
    pv: int | None = None
    likes: int | None = None
    revenue: int | None = None
    followers_gained: int | None = None
    cta: str = ""
    is_sample: bool = False
    body: str = ""
    char_count: int = 0

    @property
    def has_metrics(self) -> bool:
        return any(getattr(self, f) is not None for f in NUMERIC_FIELDS)


@dataclass
class LoadResult:
    articles: list[Article] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


def _split_front_matter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        raise ValueError("先頭に --- で始まる情報ブロックがありません")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("情報ブロックが --- で閉じられていません")
    meta = yaml.safe_load(parts[1]) or {}
    if not isinstance(meta, dict):
        raise ValueError("情報ブロックの形式が正しくありません")
    return meta, parts[2].strip()


def _to_int(value, name: str) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError(f"{name} は数値で書いてください")
    try:
        number = int(str(value).replace(",", ""))
    except ValueError:
        raise ValueError(f"{name} は数値で書いてください: {value!r}") from None
    if number < 0:
        raise ValueError(f"{name} は0以上にしてください")
    return number


def parse_article(path: Path) -> Article:
    meta, body = _split_front_matter(path.read_text(encoding="utf-8"))
    title = str(meta.get("title") or "").strip()
    if not title:
        raise ValueError("title がありません")
    published = meta.get("published")
    if published in (None, ""):
        published = None
    elif not isinstance(published, date):
        raise ValueError(f"published は YYYY-MM-DD で書いてください: {published!r}")
    return Article(
        path=path,
        title=title,
        theme=str(meta.get("theme") or ""),
        url=str(meta.get("url") or ""),
        published=published,
        cta=str(meta.get("cta") or ""),
        is_sample=bool(meta.get("sample", False)),
        body=body,
        char_count=len(body),
        **{f: _to_int(meta.get(f), f) for f in NUMERIC_FIELDS},
    )


def load_articles(directory: Path) -> LoadResult:
    result = LoadResult()
    directory = Path(directory)
    if not directory.is_dir():
        result.problems.append(f"フォルダが見つかりません: {directory}")
        return result
    for path in sorted(directory.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        try:
            result.articles.append(parse_article(path))
        except (ValueError, yaml.YAMLError, OSError) as e:
            result.problems.append(f"{path.name}: {e}")
    return result


def load_with_fallback(root: Path) -> tuple[LoadResult, str]:
    """実記事(data/past_articles)があればそれを、無ければサンプルを読む。"""
    real = load_articles(Path(root) / "data" / "past_articles")
    if real.articles or real.problems:
        return real, "past_articles"
    return load_articles(Path(root) / "data" / "samples"), "samples"


def summarize(articles: list[Article]) -> dict:
    with_metrics = [a for a in articles if a.has_metrics]
    return {
        "count": len(articles),
        "with_metrics": len(with_metrics),
        "without_metrics": len(articles) - len(with_metrics),
        "samples": sum(a.is_sample for a in articles),
        "by_theme": dict(Counter(a.theme or "(未設定)" for a in articles)),
    }
