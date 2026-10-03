from datetime import date

import pytest

from note_editorial import runs
from conftest import RESEARCH, IDEAS, DRAFT, CRITIQUE, REVISED, SNS, write

D = date(2026, 10, 3)


def new(root):
    return runs.create_run(root, "ai-work", today=D)


def test_run_id_and_daily_limit(root):
    ids = [new(root) for _ in range(3)]
    assert ids == ["2026-10-03_001", "2026-10-03_002", "2026-10-03_003"]
    with pytest.raises(runs.RunError, match="上限"):
        new(root)


def test_unknown_or_inactive_theme_rejected(root):
    with pytest.raises(runs.RunError):
        runs.create_run(root, "nope", today=D)


def test_cannot_skip_steps(root):
    rid = new(root)
    with pytest.raises(runs.RunError, match="先に"):
        runs.complete_step(root, rid, "ideas")


def test_invalid_artifact_not_recorded(root):
    rid = new(root)
    write(root, rid, "01_research.md", "ただの文章")
    assert runs.complete_step(root, rid, "research")
    assert runs.read_run(root, rid)["steps_done"] == []


def full_to_ideas(root):
    rid = new(root)
    write(root, rid, "01_research.md", RESEARCH)
    assert runs.complete_step(root, rid, "research") == []
    write(root, rid, "02_ideas.md", IDEAS)
    assert runs.complete_step(root, rid, "ideas") == []
    return rid


def test_writing_requires_idea_approval(root):
    rid = full_to_ideas(root)
    write(root, rid, "03_draft.md", DRAFT)
    with pytest.raises(runs.RunError, match="承認1"):
        runs.complete_step(root, rid, "draft")


def test_idea_number_out_of_range(root):
    rid = full_to_ideas(root)
    with pytest.raises(runs.RunError):
        runs.approve_idea(root, rid, 9)


def finish(root, revised=REVISED):
    rid = full_to_ideas(root)
    runs.approve_idea(root, rid, 1)
    for step, name, text in (("draft", "03_draft.md", DRAFT), ("critique", "04_critique.md", CRITIQUE), ("revised", "05_revised.md", revised)):
        write(root, rid, name, text)
        assert runs.complete_step(root, rid, step) == []
    return rid


def test_full_pipeline_then_publish_approval(root):
    rid = finish(root)
    assert runs.read_run(root, rid)["status"] == "revised_done"
    assert not (root / "runs" / rid / runs.READY_FILE).exists()  # 承認前は公開準備状態にならない
    ready = runs.approve_publish(root, rid)
    assert ready.exists() and runs.read_run(root, rid)["status"] == "publish_approved"


def test_publish_blocked_while_placeholders_remain(root):
    rid = finish(root, REVISED.replace("## 情報源", "【要入力:あなたの体験】\n## 情報源", 1))
    with pytest.raises(runs.RunError, match="要入力"):
        runs.approve_publish(root, rid)
    assert not (root / "runs" / rid / runs.READY_FILE).exists()


def test_publish_requires_revised_step(root):
    rid = full_to_ideas(root)
    with pytest.raises(runs.RunError):
        runs.approve_publish(root, rid)


def test_placeholder_mention_in_revision_log_is_not_counted(root):
    rid = finish(root, REVISED + "- 校正: 【要入力】は残した\n")
    ready = runs.approve_publish(root, rid)
    text = ready.read_text(encoding="utf-8")
    assert "修正履歴" not in text and "【要入力" not in text  # 公開用ファイルに編集メモは入らない


def test_publish_blocked_while_unverified_remains(root):
    rid = finish(root, REVISED.replace("## 情報源", "58.8%(要確認)\n## 情報源", 1))
    with pytest.raises(runs.RunError, match="要確認"):
        runs.approve_publish(root, rid)
    assert not (root / "runs" / rid / runs.READY_FILE).exists()


def test_reopen_archives_and_resets_publish_approval(root):
    rid = finish(root)
    runs.approve_publish(root, rid)
    dest = runs.reopen(root, rid, "draft")
    rdir = root / "runs" / rid
    assert (dest / "05_revised.md").exists() and (dest / runs.READY_FILE).exists()
    assert not (rdir / "03_draft.md").exists()
    d = runs.read_run(root, rid)
    assert d["steps_done"] == ["research", "ideas"] and d["approvals"]["publish"] is None
    assert d["approvals"]["idea"] and d["status"] == "idea_approved" and d["rounds"] == 2


def test_reopen_unfinished_step_rejected(root):
    rid = full_to_ideas(root)
    with pytest.raises(runs.RunError):
        runs.reopen(root, rid, "draft")


def test_sns_needs_publish_approval_then_gates(root):
    rid = finish(root)
    write(root, rid, "06_sns.md", SNS)
    assert runs.complete_step(root, rid, "sns") == []
    with pytest.raises(runs.RunError, match="承認2"):
        runs.approve_sns(root, rid)
    runs.approve_publish(root, rid)
    runs.approve_sns(root, rid)
    d = runs.read_run(root, rid)
    assert d["approvals"]["sns"] and d["status"] == "sns_approved"


def test_sns_approval_blocked_by_unverified(root):
    rid = finish(root)
    write(root, rid, "06_sns.md", SNS.replace("- Threads用の投稿その1です。", "- 58.8%(要確認)"))
    assert runs.complete_step(root, rid, "sns") == []
    runs.approve_publish(root, rid)
    with pytest.raises(runs.RunError, match="要確認"):
        runs.approve_sns(root, rid)


def test_reopen_sns_keeps_publish_approval(root):
    rid = finish(root)
    write(root, rid, "06_sns.md", SNS)
    runs.complete_step(root, rid, "sns")
    runs.approve_publish(root, rid)
    runs.reopen(root, rid, "sns")
    d = runs.read_run(root, rid)
    assert d["approvals"]["publish"] and d["status"] == "publish_approved" and "sns" not in d["steps_done"]


def test_sns_memo_may_mention_markers_but_posts_may_not(root):
    rid = finish(root)
    runs.approve_publish(root, rid)
    write(root, rid, "06_sns.md", SNS.replace("数字は使っていません", "「要確認」「【要入力】」は残っていません"))
    assert runs.complete_step(root, rid, "sns") == []
    runs.approve_sns(root, rid)  # メモ内の言及だけなら通る
    rid2 = finish(root)
    runs.approve_publish(root, rid2)
    write(root, rid2, "06_sns.md", SNS.replace("- Threads用の投稿その1です。", "- 【要入力:ここ】"))
    runs.complete_step(root, rid2, "sns")
    with pytest.raises(runs.RunError, match="要入力"):
        runs.approve_sns(root, rid2)
