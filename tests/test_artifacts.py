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


def test_article_without_external_sources_needs_explicit_note(tmp_path):
    no_url = DRAFT.replace("- https://example.com/1", "- 筆者の体験のみ")
    assert any("URL" in e for e in check("draft", no_url, tmp_path))
    ok = DRAFT.replace("- https://example.com/1", "- 外部の情報源は使用していません(筆者の体験と架空例のみ)")
    assert check("draft", ok, tmp_path) == []

def test_internal_chapters_are_not_public_and_not_counted(tmp_path):
    text = "# 題名\n本文です。\n【要入力:僕の失敗】\n## 情報源\n- https://example.com\n## 執筆メモ(公開前に削除する章)\n- 体験は【要入力】のまま。(要確認)の数字は無い\n## 修正履歴\n- 問題1: 【要入力】を残した\n"
    pub = a.publishable_text(text)
    assert "執筆メモ" not in pub and "修正履歴" not in pub and "情報源" in pub
    f = tmp_path / "r.md"
    f.write_text(text, encoding="utf-8")
    assert a.count_placeholders(f) == 1 and a.count_unverified(f) == 0


def test_title_minutes_must_fit_the_body_length():
    tail = "\n## 情報源\n- https://example.com\n## 執筆メモ\nメモ\n## 修正履歴\n- 問題1\n"
    ok = "# 【5分で読める】題\n" + "あ" * 2400 + tail
    assert not [e for e in a._revised(ok, None) if "分」とある" in e]
    long = "# 【3分でわかる】題\n" + "あ" * 2400 + tail
    assert [e for e in a._revised(long, None) if "「3分」とある" in e]
    plain = "# ふつうの題\n" + "あ" * 4000 + tail
    assert not [e for e in a._revised(plain, None) if "分」とある" in e]
