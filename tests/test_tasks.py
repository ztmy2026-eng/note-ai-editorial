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


PNG_1X1 = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000002000001e221bc330000000049454e44ae426082")


def test_export_image_docs_follow_the_article_order_and_group(root):
    import base64
    rid = finish(root, REVISED.replace("# ", "# 題\n\n【画像:cover.png】\n\n本文【画像:fig2_b.png】と【画像:fig1_a.png】\n\n# ", 1))
    img = root / "runs" / rid / "images"
    (img / "figures").mkdir(parents=True)
    for name in ("cover.png", "fig1_a.png", "fig2_b.png"):
        (img / "figures" / name).write_bytes(PNG_1X1)
    (img / "note_eyecatch.png").write_bytes(PNG_1X1)
    for n in (1, 2):
        (img / f"instagram_0{n}.png").write_bytes(PNG_1X1)
    (root / "runs" / rid / "figures.json").write_text('[{"type":"bar","name":"fig1_a","title":"図の題A"}]', encoding="utf-8")
    docs = tasks.export_image_docs(root, rid)
    assert [d["file"] for d in docs] == ["cover.png", "fig2_b.png", "fig1_a.png", "note_eyecatch.png", "instagram_01.png", "instagram_02.png"]
    assert [d["group"] for d in docs] == ["note", "note", "note", "other", "instagram", "instagram"]
    assert docs[0]["label"] == "見出し画像" and docs[1]["label"] == "図1" and docs[2]["label"] == "図2：図の題A"
    assert docs[0]["id"] == f"{rid}__cover" and docs[0]["width"] == 1 and docs[0]["mime"] == "image/png"
    assert base64.b64decode(docs[0]["data"]) == PNG_1X1


def test_export_image_docs_is_empty_without_images(root):
    assert tasks.export_image_docs(root, finish(root)) == []


def test_export_image_docs_match_names_with_or_without_the_date_prefix(root):
    rid = finish(root, REVISED.replace("# ", "# 題\n\n【画像:2026-10-08_cover.png】\n\n# ", 1))
    (root / "runs" / rid / "images" / "figures").mkdir(parents=True)
    (root / "runs" / rid / "images" / "figures" / "cover.png").write_bytes(PNG_1X1)
    assert [d["file"] for d in tasks.export_image_docs(root, rid)] == ["cover.png"]
