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
