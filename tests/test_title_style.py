from datetime import date

from note_editorial import analytics, artifacts, title_style as ts


def test_style_alternates_by_day_and_is_none_outside():
    assert ts.style_for(date(2026, 10, 12)) is None
    assert ts.style_for(date(2026, 10, 13)) == ts.TWO_PART
    assert ts.style_for(date(2026, 10, 14)) == ts.SHORT
    assert ts.style_for(date(2026, 10, 26)) == ts.SHORT
    assert ts.style_for(date(2026, 10, 27)) is None


def test_style_of_and_problem():
    short = "コンビニの「今日だけならいいか」が、お金を減らす"
    two = "節約しているのに疲れる人へ。無理なく続ける3つの考え方"
    assert ts.style_of(short) == ts.SHORT
    assert ts.style_of(two) == ts.TWO_PART
    assert ts.style_of("節約しているのに疲れる人へ。") == ts.SHORT  # 末尾の「。」だけは2段ではない
    assert ts.problem(short, date(2026, 10, 14)) is None
    assert ts.problem(two, date(2026, 10, 13)) is None
    assert ts.problem(two, date(2026, 10, 14))      # 偶数日(短い型)に2段は不可
    assert ts.problem(short, date(2026, 10, 13))    # 奇数日に短い型は不可
    assert ts.problem("あ" * 31, date(2026, 10, 14))
    assert ts.problem(two, date(2026, 10, 1)) is None  # 期間外


def test_revised_check_uses_run_date(tmp_path):
    run = tmp_path / "2026-10-14_001"
    run.mkdir()
    body = "# 節約しているのに疲れる人へ。無理なく続ける3つの考え方\n\n本文\n"
    errs = artifacts._revised(body, run)
    assert any("短い型" in e for e in errs)


def test_analytics_has_title_style_groups():
    facts = analytics.compute_facts([])
    assert set(facts["title_styles"]) == {"短い型(1文)", "2段型(2文・「｜」)"}
    assert "タイトルの型別" in analytics.render_facts(facts)
