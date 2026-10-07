from datetime import date

from note_editorial import runs, tasks
from test_chief import finish
from conftest import REVISED, SNS, write

D = date(2026, 10, 3)


def test_blank_run_is_listed_with_its_blanks(root):
    rid = finish(root, REVISED.replace("## 情報源", "【要入力:僕自身の失敗(書類について)】\n## 情報源", 1))
    out = tasks.export_tasks(root, D)
    (t,) = out["tasks"]
    assert t["id"] == rid and t["needs_human"]
    assert t["blanks"] == ["僕自身の失敗(書類について)"]
    assert t["note_ready"] is False and t["title"]
    assert out["limits"]["runs"][1] == 3


def test_ready_run_gives_note_text_and_sns_posts(root):
    rid = finish(root)
    write(root, rid, "06_sns.md", SNS)
    runs.complete_step(root, rid, "sns")
    runs.approve_publish(root, rid)
    runs.approve_sns(root, rid)
    (t,) = tasks.export_tasks(root, D)["tasks"]
    assert t["note_ready"] is True and t["blanks"] == []
    assert t["note_body"].strip()
    assert len(t["x_posts"]) == 3 and len(t["threads_posts"]) == 2
    assert "投稿" in t["next_action"] and "auto-approve" not in t["next_action"] and t["needs_human"] is True


def test_posted_and_skipped_runs_are_not_listed(root):
    a, b = finish(root), finish(root)
    runs.mark_skipped(root, a, "test")
    assert [t["id"] for t in tasks.export_tasks(root, D)["tasks"]] == [b]


def test_threads_posts_keep_multiple_lines():
    block = "\n- 一件目\n続きの行\n\n- 二件目\n"
    assert tasks._split_posts(block) == ["一件目\n続きの行", "二件目"]


def test_split_posts_removes_source_indentation():
    assert tasks._split_posts("- 一行目\n  二行目\n  ・箇条書き") == ["一行目\n二行目\n・箇条書き"]

def test_run_waiting_for_approval_2_is_shown_as_waiting_even_in_auto_mode(root):
    from conftest import set_limits
    set_limits(root, auto_approve="true")
    rid = finish(root)
    (t,) = tasks.export_tasks(root, D)["tasks"]
    assert t["id"] == rid and t["needs_human"] is True and "承認2" in t["next_action"]
    assert t["note_ready"] is False and t["blanks"] == []

