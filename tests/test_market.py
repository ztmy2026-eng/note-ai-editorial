from note_editorial import market


def test_classify_and_features():
    assert market.classify("医療保険の見直し") == "保険"
    assert market.classify("NISAを始めた") == "投資"
    assert market.classify("天気の話") == "その他のお金"
    f = market.features("【実体験】節約で月3万")
    assert f["数字を含む"] and f["【】で始まる"] and f["体験・実践の言葉"] and not f["疑問形"]


def test_load_reports_bad_rows_and_keeps_good(tmp_path):
    p = tmp_path / "i.csv"
    p.write_text("title,likes,topic,source,observed\nA保険,5,,x,d\nB,abc,,x,d\n,3,,x,d\nC投資,-1,,x,d\n", encoding="utf-8")
    items, problems = market.load_items(p)
    assert [i["title"] for i in items] == ["A保険"] and len(problems) == 3


def test_small_sample_is_flagged_and_empty_is_safe(tmp_path):
    assert "参考程度" in market.render([{"title": "t", "likes": 1, "topic": "投資"}])
    assert "データなし" in market.render([])
    assert market.load_items(tmp_path / "none.csv")[1]
