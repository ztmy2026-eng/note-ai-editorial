import pytest

from note_editorial import articles, learn, runs
from conftest import write


def posted_run(root):
    rid = runs.create_run(root, "ai-work")
    d = root / "runs" / rid / "note_post"
    d.mkdir()
    (d / "title.txt").write_text("題名: テスト\n", encoding="utf-8")
    (d / "body.md").write_text("本文です。\n## 見出し\n中身\n", encoding="utf-8")
    data = runs.read_run(root, rid)
    data["approvals"]["publish"] = {"at": "x"}
    runs._save(root, rid, data)
    runs.mark_posted(root, rid, url="https://note.com/a/n/nabc")
    return rid


def test_posted_article_enters_learning_data_without_metrics(root):
    rid = posted_run(root)
    path = learn.add_posted_article(root, rid)
    res = articles.load_articles(root / "data" / "past_articles")
    assert not res.problems and len(res.articles) == 1
    a = res.articles[0]
    assert a.title == "題名: テスト" and a.url == "https://note.com/a/n/nabc" and a.pv is None and not a.is_sample
    assert learn.add_posted_article(root, rid) == path  # 2回目は何もしない


def test_record_metrics_updates_only_given_fields_and_keeps_body(root):
    rid = posted_run(root)
    learn.add_posted_article(root, rid)
    learn.record_metrics(root, rid, pv=120, likes=7)
    learn.record_metrics(root, rid, likes=9)  # pv は変えない
    a = articles.load_articles(root / "data" / "past_articles").articles[0]
    assert (a.pv, a.likes, a.revenue) == (120, 9, None) and "見出し" in a.body


def test_record_metrics_rejects_bad_input(root):
    rid = posted_run(root)
    learn.add_posted_article(root, rid)
    with pytest.raises(runs.RunError):
        learn.record_metrics(root, rid)
    with pytest.raises(runs.RunError):
        learn.record_metrics(root, rid, pv=-1)
    with pytest.raises(runs.RunError, match="past_articles"):
        learn.record_metrics(root, "2000-01-01_001", pv=1)


def test_real_article_replaces_samples_in_loader(root):
    import shutil
    from conftest import REPO
    shutil.copytree(REPO / "data" / "samples", root / "data" / "samples")
    assert articles.load_with_fallback(root)[1] == "samples"
    learn.add_posted_article(root, posted_run(root))
    assert articles.load_with_fallback(root)[1] == "past_articles"


def test_dashboard_edits_import_and_win_over_email(root, tmp_path):
    import json
    from note_editorial import collect
    rid = posted_run(root)
    learn.add_posted_article(root, rid)
    rows = learn.export_metrics(root)["articles"]
    assert rows[0]["id"] == rid and rows[0]["pv"] is None
    # 画面で PV=120, スキ=7 を手入力した
    edited = [{**rows[0], "pv": 120, "likes": 7, "impressions": 900, "src": {"pv": "manual", "likes": "manual", "impressions": "manual"}}]
    notes = learn.import_metrics(root, edited)
    a = articles.load_articles(root / "data" / "past_articles").articles[0]
    assert (a.impressions, a.pv, a.likes) == (900, 120, 7) and notes
    # その後メール収集が「スキ=3」を見つけても、手入力は上書きしない
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps({"likes": [{"date": "2026-10-05T00:00:00Z", "snippet":
        f"作品が読者に届いています！ {a.title} 見出し画像 x x 3 スキしてくれた人"}]}, ensure_ascii=False), encoding="utf-8")
    out = collect.collect(root, raw)
    assert articles.load_articles(root / "data" / "past_articles").articles[0].likes == 7
    assert any("手入力を優先" in line for line in out)


def test_import_ignores_auto_values_negatives_and_unknown_ids(root):
    rid = posted_run(root)
    learn.add_posted_article(root, rid)
    notes = learn.import_metrics(root, [
        {"id": rid, "pv": 5, "src": {"pv": "auto"}},          # 自動の値は取り込まない
        {"id": rid, "likes": -3, "src": {"likes": "manual"}},  # 負の数は無視
        {"id": "nope", "pv": 1, "src": {"pv": "manual"}}])
    a = articles.load_articles(root / "data" / "past_articles").articles[0]
    assert a.pv is None and a.likes is None and any("対応する記事がありません" in n for n in notes)
