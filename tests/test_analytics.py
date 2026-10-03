from datetime import date
from pathlib import Path

from note_editorial import analytics as an
from note_editorial.articles import Article, load_articles

REPO = Path(__file__).resolve().parent.parent


def art(title, pv, likes, theme="ai-work", sample=False):
    return Article(path=Path("x.md"), title=title, theme=theme, pv=pv, likes=likes, is_sample=sample)


def test_like_rate_handles_missing_and_zero():
    assert an.like_rate(art("a", 200, 10)) == 0.05
    assert an.like_rate(art("a", None, 10)) is None
    assert an.like_rate(art("a", 0, 0)) is None


def test_samples_are_flagged_and_unmeasured_excluded():
    arts = load_articles(REPO / "data" / "samples").articles + [art("データなし記事", None, None)]
    facts = an.compute_facts(arts)
    assert facts["measured"] == 5 and facts["unmeasured"] == 1
    assert facts["small_sample"] and not facts["all_samples"]  # 実記事(サンプルでない)が混ざる
    text = an.render_facts(facts)
    assert "参考程度" in text and "ai-work" in text


def test_all_samples_warning():
    facts = an.compute_facts(load_articles(REPO / "data" / "samples").articles)
    assert "架空" in an.render_facts(facts)


def test_empty_articles_do_not_crash():
    assert "データなし" in an.render_facts(an.compute_facts([]))


def test_title_feature_groups():
    facts = an.compute_facts([art("3つのルール", 100, 10), art("ルール", 100, 2)])
    g = facts["features"]["タイトルに数字を含む"]
    assert g["あり"]["n"] == 1 and g["なし"]["n"] == 1
    assert g["あり"]["avg_like_rate"] > g["なし"]["avg_like_rate"]


GOOD = """# 仮説台帳
### H1 体験型タイトルは反応が良い
- **仮説**: 体験型
- **根拠(事実)**: n=2 でスキ率 6.8% vs 5.2%
- **信頼度**: 低(架空データ)
- **検証方法**: 次の2本で比較
- **状態**: 検証中
"""


def test_hypotheses_validation(tmp_path):
    f = tmp_path / "h.md"
    f.write_text(GOOD, encoding="utf-8")
    assert an.validate_hypotheses(f) == []
    f.write_text(GOOD.replace("- **検証方法**: 次の2本で比較\n", ""), encoding="utf-8")
    assert any("検証方法" in e for e in an.validate_hypotheses(f))
    f.write_text(GOOD.replace("検証中", "たぶん正しい"), encoding="utf-8")
    assert any("状態" in e for e in an.validate_hypotheses(f))
    f.write_text("仮説なし", encoding="utf-8")
    assert an.validate_hypotheses(f)
