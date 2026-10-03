from note_editorial import artifacts as a
from conftest import RESEARCH, IDEAS, DRAFT, CRITIQUE, REVISED, SNS


def check(step, text, tmp_path, run_dir=None):
    p = tmp_path / "x.md"
    p.write_text(text, encoding="utf-8")
    return a.validate(step, p, run_dir)


def test_good_artifacts_pass(tmp_path):
    for step, text in (("research", RESEARCH), ("ideas", IDEAS), ("draft", DRAFT), ("critique", CRITIQUE)):
        assert check(step, text, tmp_path) == [], step


def test_research_fact_without_source_rejected(tmp_path):
    bad = RESEARCH.replace("- 例の事実A [S1]", "- 出典のない事実")
    assert any("出典番号" in e for e in check("research", bad, tmp_path))


def test_research_needs_three_dated_urls(tmp_path):
    bad = RESEARCH.replace("| 公開日:2026-01-03 | 取得日:2026-10-03", "")
    assert any("3件未満" in e for e in check("research", bad, tmp_path))


def test_ideas_need_experiment_slot(tmp_path):
    assert any("実験枠" in e for e in check("ideas", IDEAS.replace("【実験枠】", ""), tmp_path))


def test_ideas_need_five(tmp_path):
    assert any("5件未満" in e for e in check("ideas", IDEAS.replace("### 候補5", "### x5"), tmp_path))


def test_praise_only_critique_rejected(tmp_path):
    praise = "# 批評\n## 総合評価\nとても良い記事です。スコア:95/100\n"
    errs = check("critique", praise, tmp_path)
    assert any("問題点" in e for e in errs)


def test_revised_must_address_every_problem(tmp_path):
    (tmp_path / a.FILES["critique"]).write_text(CRITIQUE, encoding="utf-8")
    assert check("revised", REVISED, tmp_path, tmp_path) == []
    missing = REVISED.replace("- 問題3: 表記統一", "")
    assert any("問題3" in e for e in check("revised", missing, tmp_path, tmp_path))


def test_good_sns_passes(tmp_path):
    assert check("sns", SNS, tmp_path) == []


def test_sns_x_post_over_limit_rejected(tmp_path):
    long = SNS.replace("- チェック表を記事で配っています 【記事URL】", "- " + "あ" * 141)
    assert any("140字" in e for e in check("sns", long, tmp_path))


def test_sns_needs_confirmation_memo(tmp_path):
    assert any("確認メモ" in e for e in check("sns", SNS.replace("## 確認メモ", "## 別の章"), tmp_path))


def test_sns_must_not_cite_unverified_source(tmp_path):
    (tmp_path / a.FILES["revised"]).write_text(REVISED.replace("## 情報源", "58.8%(要確認)\n## 情報源", 1), encoding="utf-8")
    bad = SNS.replace("- チェック表を記事で配っています 【記事URL】", "- 総務省の白書によると… 【記事URL】")
    assert any("白書" in e or "総務省" in e for e in check("sns", bad, tmp_path, tmp_path))
    assert check("sns", SNS, tmp_path, tmp_path) == []
    # 要確認が残っていない記事なら、出典に触れてよい
    (tmp_path / a.FILES["revised"]).write_text(REVISED, encoding="utf-8")
    assert check("sns", bad, tmp_path, tmp_path) == []
