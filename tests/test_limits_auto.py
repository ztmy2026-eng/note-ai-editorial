import pytest

from note_editorial import auto, limits, runs
from note_editorial.log import log_event
from conftest import RESEARCH, IDEAS, DRAFT, CRITIQUE, REVISED, SNS, write, set_limits


def to_revised(root, revised=REVISED):
    rid = runs.create_run(root, "ai-work")
    for step, name, text in (("research", "01_research.md", RESEARCH), ("ideas", "02_ideas.md", IDEAS)):
        write(root, rid, name, text)
        runs.complete_step(root, rid, step)
    return rid


def finish(root, revised=REVISED):
    rid = to_revised(root)
    runs.approve_idea(root, rid, 1)
    for step, name, text in (("draft", "03_draft.md", DRAFT), ("critique", "04_critique.md", CRITIQUE), ("revised", "05_revised.md", revised)):
        write(root, rid, name, text)
        runs.complete_step(root, rid, step)
    return rid


def test_step_limit_blocks_new_run(root):
    set_limits(root, max_agent_steps_per_day=2)
    log_event(root, "step_done", run_id="x", step="research")
    runs.create_run(root, "ai-work")  # 1/2 → まだ作れる
    log_event(root, "step_done", run_id="x", step="ideas")
    with pytest.raises(runs.RunError, match="Agent作業数"):
        runs.create_run(root, "ai-work")


def test_ready_queue_limit_and_mark_posted(root):
    set_limits(root, max_ready_queue=1)
    rid = finish(root)
    runs.approve_publish(root, rid)
    assert limits.ready_queue(root) == [rid]
    with pytest.raises(runs.RunError, match="未投稿"):
        runs.create_run(root, "ai-work")
    runs.mark_posted(root, rid, url="https://note.com/x/n/abc")
    assert limits.ready_queue(root) == []
    runs.create_run(root, "ai-work")  # 投稿済みにしたので再び作れる


def test_mark_posted_requires_publish_approval(root):
    rid = finish(root)
    with pytest.raises(runs.RunError, match="公開承認"):
        runs.mark_posted(root, rid)


def test_auto_approve_disabled_by_default_in_tests(root):
    rid = to_revised(root)
    with pytest.raises(runs.RunError, match="無効"):
        auto.auto_approve(root, rid)


def test_auto_approve_full_flow_records_auto(root):
    set_limits(root, auto_approve="true")
    rid = to_revised(root)
    assert auto.auto_approve(root, rid)[0].startswith("【承認1】")
    for step, name, text in (("draft", "03_draft.md", DRAFT), ("critique", "04_critique.md", CRITIQUE), ("revised", "05_revised.md", REVISED)):
        write(root, rid, name, text)
        runs.complete_step(root, rid, step)
    assert any("承認2" in m for m in auto.auto_approve(root, rid))
    write(root, rid, "06_sns.md", SNS)
    runs.complete_step(root, rid, "sns")
    assert any("承認3" in m for m in auto.auto_approve(root, rid))
    d = runs.read_run(root, rid)
    assert d["approvals"]["idea"]["by"] == d["approvals"]["publish"]["by"] == d["approvals"]["sns"]["by"] == "auto"


def test_auto_approve_still_stopped_by_validators(root):
    set_limits(root, auto_approve="true")
    rid = to_revised(root)
    auto.auto_approve(root, rid)
    for step, name, text in (("draft", "03_draft.md", DRAFT), ("critique", "04_critique.md", CRITIQUE),
                             ("revised", "05_revised.md", REVISED.replace("## 情報源", "【要入力:体験】\n## 情報源", 1))):
        write(root, rid, name, text)
        runs.complete_step(root, rid, step)
    msgs = auto.auto_approve(root, rid)
    assert msgs[-1].startswith("停止") and "要入力" in msgs[-1]
    assert not (root / "runs" / rid / runs.READY_FILE).exists()


def test_recommended_candidate_parse():
    assert auto.recommended_candidate("## おすすめ\n候補3 — 理由\n") == 3
    assert auto.recommended_candidate("## おすすめ\n理由のみ\n") is None


def test_check_limits_does_not_count_the_run_in_progress(root, capsys):
    from note_editorial import cli
    set_limits(root, max_runs_per_day=1)
    assert cli.main(["--root", str(root), "check-limits", "--new-run"]) == 0  # まだ1本も作っていない
    runs.create_run(root, "ai-work")
    assert cli.main(["--root", str(root), "check-limits"]) == 0   # 作業中の続きは止めない
    assert cli.main(["--root", str(root), "check-limits", "--new-run"]) == 1  # 新しい実行は作れない
    with pytest.raises(runs.RunError, match="上限"):
        runs.create_run(root, "ai-work")


def test_continuing_work_is_not_blocked_by_ready_queue(root):
    from note_editorial import cli
    set_limits(root, max_ready_queue=1)
    rid = finish(root)
    runs.approve_publish(root, rid)  # この記事自身が在庫1/1になる
    assert cli.main(["--root", str(root), "check-limits"]) == 0              # 続き(SNSなど)は止めない
    assert cli.main(["--root", str(root), "check-limits", "--new-run"]) == 1  # 新しい記事は始めない


def test_skipped_run_leaves_the_ready_queue(root):
    rid = finish(root)
    runs.approve_publish(root, rid)
    assert limits.ready_queue(root) == [rid]
    runs.mark_skipped(root, rid, "投稿しない")
    assert limits.ready_queue(root) == []
    with pytest.raises(runs.RunError):
        runs.mark_skipped(root, "no-such-run")  # 存在しない実行はエラー
