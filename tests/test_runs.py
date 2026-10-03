from datetime import date

import pytest

from note_editorial import runs
from conftest import RESEARCH, IDEAS, DRAFT, CRITIQUE, REVISED, write

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
    rid = finish(root, REVISED + "\n【要入力:あなたの体験】\n")
    with pytest.raises(runs.RunError, match="要入力"):
        runs.approve_publish(root, rid)
    assert not (root / "runs" / rid / runs.READY_FILE).exists()


def test_publish_requires_revised_step(root):
    rid = full_to_ideas(root)
    with pytest.raises(runs.RunError):
        runs.approve_publish(root, rid)
