import json
from datetime import timezone, timedelta

import pytest

from note_editorial import articles, collect, runs
from conftest import write

JST = timezone(timedelta(hours=9))


def snip(title, n, name="誰か"):
    return f"note {name}さんがスキしました！ 作品が読者に届いています！ {title} 見出し画像 地道(チドウ)編集部 地道(チドウ)編集部 {n} スキしてくれた人 {name} {name} プロフィール"


def test_parse_title_and_count_without_liker_info():
    assert collect.parse_like_snippet(snip("節約とご褒美のあいだ。味玉100円に学ぶ", 5)) == ("節約とご褒美のあいだ。味玉100円に学ぶ", 5)
    assert collect.parse_like_snippet("関係ないメール") is None


def test_aggregate_uses_latest_value_even_if_count_dropped():
    recs = [{"date": "2026-09-15T16:56:55Z", "snippet": snip("A", 2)}, {"date": "2026-09-16T01:27:08Z", "snippet": snip("A", 1)},
            {"date": "2026-09-14T00:00:00Z", "snippet": snip("B", 3)}, {"date": "x", "snippet": "壊れた"}]
    agg, problems = collect.aggregate_likes(recs)
    assert agg["A"]["likes"] == 1 and agg["A"]["events"] == 2 and agg["B"]["likes"] == 3 and len(problems) == 1


def test_follows_grouped_by_jst_day():
    days = collect.follows_by_day(["2026-10-03T22:51:09Z", "2026-10-04T01:08:00Z", "2026-10-03T13:41:10Z"], JST)
    assert days == {"2026-10-04": 2, "2026-10-03": 1}


def test_collect_end_to_end_creates_stub_updates_and_is_idempotent(root, tmp_path):
    data = tmp_path / "raw.json"
    data.write_text(json.dumps({"likes": [{"date": "2026-10-04T00:40:22Z", "snippet": snip("記事X", 3, "山田")}],
                                "follows": ["2026-10-04T01:08:00Z"]}, ensure_ascii=False), encoding="utf-8")
    collect.collect(root, data)
    collect.collect(root, data)  # 2回目も重複しない
    arts = articles.load_articles(root / "data" / "past_articles").articles
    assert len(arts) == 1 and arts[0].likes == 3 and arts[0].title == "記事X"
    text = (root / "data" / "past_articles" / arts[0].path.name).read_text(encoding="utf-8")
    assert "山田" not in text  # スキした人の名前は記録しない
    assert (root / "analytics" / "followers.csv").read_text(encoding="utf-8").count("2026-10-04") == 1


def test_collect_updates_existing_article_by_title_and_keeps_other_fields(root, tmp_path):
    d = root / "data" / "past_articles"
    d.mkdir(parents=True)
    (d / "a.md").write_text('---\ntitle: 記事X\nurl: https://note.com/x\npv: 50\n---\n本文\n', encoding="utf-8")
    data = tmp_path / "raw.json"
    data.write_text(json.dumps({"likes": [{"date": "2026-10-04T00:40:22Z", "snippet": snip("記事X", 4)}]}, ensure_ascii=False), encoding="utf-8")
    collect.collect(root, data)
    a = articles.load_articles(d).articles[0]
    assert (a.pv, a.likes, a.url) == (50, 4, "https://note.com/x") and "本文" in a.body


def test_collect_bad_file_is_a_clear_error(root, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    with pytest.raises(runs.RunError):
        collect.collect(root, bad)
