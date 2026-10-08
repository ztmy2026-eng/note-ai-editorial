from note_editorial import articles


def test_sample_articles_load(root):
    res = articles.load_articles(__import__("pathlib").Path(__file__).parent.parent / "data" / "samples")
    assert len(res.articles) == 5 and not res.problems
    assert all(a.is_sample for a in res.articles)


def test_missing_metrics_are_none_not_error(tmp_path):
    (tmp_path / "a.md").write_text('---\ntitle: "T"\npublished: 2026-01-01\n---\n本文', encoding="utf-8")
    res = articles.load_articles(tmp_path)
    assert not res.problems
    a = res.articles[0]
    assert a.pv is None and not a.has_metrics


def test_bad_file_does_not_stop_others(tmp_path):
    (tmp_path / "ok.md").write_text('---\ntitle: "T"\n---\nx', encoding="utf-8")
    (tmp_path / "bad.md").write_text("front matterなし", encoding="utf-8")
    (tmp_path / "bad2.md").write_text('---\ntitle: "T"\npv: abc\n---\nx', encoding="utf-8")
    res = articles.load_articles(tmp_path)
    assert len(res.articles) == 1 and len(res.problems) == 2


def test_missing_folder_reports_problem(tmp_path):
    assert articles.load_articles(tmp_path / "none").problems


def test_quoted_date_string_is_accepted_for_published(tmp_path):
    (tmp_path / "a.md").write_text("---\ntitle: t\npublished: '2026-10-07'\npv: 3\n---\n本文", encoding="utf-8")
    res = articles.load_articles(tmp_path)
    assert not res.problems and str(res.articles[0].published) == "2026-10-07"

    (tmp_path / "b.md").write_text("---\ntitle: u\npublished: '2026-13-40'\n---\n本文", encoding="utf-8")
    assert articles.load_articles(tmp_path).problems
