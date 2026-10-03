import json
from datetime import date

from note_editorial import chief, runs
from conftest import RESEARCH, IDEAS, DRAFT, CRITIQUE, REVISED, SNS, write

D = date(2026, 10, 3)


def test_next_action_follows_the_pipeline(root):
    rid = runs.create_run(root, "ai-work", today=D)
    assert chief.next_action(root, rid) == ("リサーチAgentを実行", False)
    write(root, rid, "01_research.md", RESEARCH)
    runs.complete_step(root, rid, "research")
    assert chief.next_action(root, rid)[0] == "企画Agentを実行"
    write(root, rid, "02_ideas.md", IDEAS)
    runs.complete_step(root, rid, "ideas")
    action, human = chief.next_action(root, rid)
    assert "承認1" in action and human
    runs.approve_idea(root, rid, 1)
    assert chief.next_action(root, rid) == ("ライターAgentを実行", False)


def finish(root, revised=REVISED):
    rid = runs.create_run(root, "ai-work", today=D)
    for step, name, text in (("research", "01_research.md", RESEARCH), ("ideas", "02_ideas.md", IDEAS)):
        write(root, rid, name, text)
        runs.complete_step(root, rid, step)
    runs.approve_idea(root, rid, 1)
    for step, name, text in (("draft", "03_draft.md", DRAFT), ("critique", "04_critique.md", CRITIQUE), ("revised", "05_revised.md", revised)):
        write(root, rid, name, text)
        runs.complete_step(root, rid, step)
    return rid


def test_blockers_are_reported_as_human_work(root):
    rid = finish(root, REVISED.replace("## 情報源", "【要入力:体験】 58.8%(要確認)\n## 情報源", 1))
    action, human = chief.next_action(root, rid)
    assert human and "【要入力】1件" in action and "要確認」1件" in action


def test_full_flow_to_done(root):
    rid = finish(root)
    assert "承認2" in chief.next_action(root, rid)[0]
    runs.approve_publish(root, rid)
    assert chief.next_action(root, rid) == ("SNS Agentを実行", False)
    write(root, rid, "06_sns.md", SNS)
    runs.complete_step(root, rid, "sns")
    assert "承認3" in chief.next_action(root, rid)[0]
    runs.approve_sns(root, rid)
    assert "手動で投稿" in chief.next_action(root, rid)[0]


def test_log_reader_skips_broken_lines(root):
    (root / "logs").mkdir()
    (root / "logs" / "events.jsonl").write_text('{"event":"step_rejected","step":"ideas"}\nこれは壊れた行\n', encoding="utf-8")
    assert chief.quality_signals(chief.read_log(root))["rejected_by_step"] == {"ideas": 1}


def test_briefing_lists_waiting_items_and_suggestions(root):
    finish(root, REVISED.replace("## 情報源", "【要入力:体験】\n## 情報源", 1))
    text = chief.briefing(root, D)
    assert "あなたの確認待ち" in text and "【要入力】1件" in text
    assert "今日の実行数: 1 / 3" in text
    assert "過去記事が1本も読み込めていません" in text


def test_briefing_warns_when_only_samples(root):
    import shutil
    from conftest import REPO
    shutil.copytree(REPO / "data" / "samples", root / "data" / "samples")
    assert "サンプル(架空)のまま" in chief.briefing(root, D)


def test_briefing_with_no_runs_does_not_crash(root):
    assert "なし" in chief.briefing(root, D)


def test_next_theme_balances_by_priority_then_fewest_runs(root):
    assert chief.next_theme(root) == "ai-work"  # 実行ゼロなら最優先テーマ
    runs.create_run(root, "ai-work", today=D)
    assert chief.next_theme(root) == "newcomer"  # 最優先テーマは1回実行済み→次に優先度が高く実行数の少ないもの
