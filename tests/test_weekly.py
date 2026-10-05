from datetime import date, timedelta

import pytest
import yaml

from note_editorial import artifacts, chief, figures, runs, weekly

W = date(2026, 10, 5)


def plan(root, n=7, ai_day=5, **over):
    items = []
    for i in range(n):
        d = (W + timedelta(days=i)).isoformat()
        items.append({
            "date": d, "theme": "ai-work" if i == ai_day else "saving-insurance", "ai": i == ai_day,
            "title": f"テーマ{i}、最初に見る3つ",
            "alt_titles": ["予備1", "予備2"], "aim": "狙い", "failures": ["a", "b", "c"],
            "figures": ["見出し画像", "fig1"], "affiliate": "",
        })
    data = {"week_start": W.isoformat(), "approved": False, "items": items, **over}
    d = root / "plans" / W.isoformat()
    d.mkdir(parents=True, exist_ok=True)
    (d / "plan.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return data


def test_week_start_is_monday():
    assert weekly.week_start(date(2026, 10, 11)) == W
    assert weekly.week_start(W) == W


def test_valid_plan_passes(root):
    plan(root)
    assert weekly.validate_plan(root, W) == []


def test_plan_problems_detected(root):
    plan(root, n=6, ai_day=99)
    probs = " ".join(weekly.validate_plan(root, W))
    assert "7本" in probs and "AI" in probs


def test_missing_plan(root):
    assert "ありません" in weekly.validate_plan(root, W)[0]


def test_bad_theme_and_title(root):
    data = plan(root)
    data["items"][0]["theme"] = "nope"
    data["items"][1]["title"] = "とても長いタイトルは読まれにくいので、この長さは受け付けない決まりにしてあります。さらに続けます"
    (root / "plans" / W.isoformat() / "plan.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    probs = " ".join(weekly.validate_plan(root, W))
    assert "nope" in probs and "字以内" in probs


def test_attach_to_run_copies_plan_draft_and_images(root):
    data = plan(root)
    pdir = root / "plans" / W.isoformat()
    (pdir / "drafts").mkdir()
    (pdir / "drafts" / "x.md").write_text("# 下書き\n", encoding="utf-8")
    (pdir / "images").mkdir()
    (pdir / "images" / "2026-10-07_cover.png").write_bytes(b"png")
    (pdir / "images" / "2026-10-08_cover.png").write_bytes(b"png")
    data["items"][2]["draft"] = "drafts/x.md"
    (pdir / "plan.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    found = weekly.item_for(root, date(2026, 10, 7))
    assert found and found[1]["date"] == "2026-10-07"
    rid = runs.create_run(root, found[1]["theme"], today=date(2026, 10, 7))
    weekly.attach_to_run(root, rid, *found)
    rdir = root / "runs" / rid
    assert "テーマ2" in (rdir / "00_plan.md").read_text(encoding="utf-8")
    assert (rdir / "00_plan_draft.md").exists()
    assert [p.name for p in (rdir / "images" / "plan").iterdir()] == ["2026-10-07_cover.png"]
    assert runs.read_run(root, rid)["plan"]["date"] == "2026-10-07"


def test_no_item_outside_plan(root):
    plan(root)
    assert weekly.item_for(root, date(2026, 10, 12)) is None


def test_experience_slot_blocks_publish_approval_until_filled(root):
    """体験の欄(【要入力:僕自身の失敗】)が残っている間は、承認2が止まる(自動モードでも同じ)。"""
    from note_editorial import runs
    from conftest import RESEARCH, IDEAS, DRAFT, CRITIQUE, REVISED, write
    rid = runs.create_run(root, "ai-work")
    for step, name, text in (("research", "01_research.md", RESEARCH), ("ideas", "02_ideas.md", IDEAS)):
        write(root, rid, name, text)
        runs.complete_step(root, rid, step)
    runs.approve_idea(root, rid, 1)
    slot = REVISED.replace("## 情報源", "## 僕自身の失敗\n【要入力:僕自身の失敗(年末調整について)】\n## 情報源", 1)
    for step, name, text in (("draft", "03_draft.md", DRAFT), ("critique", "04_critique.md", CRITIQUE), ("revised", "05_revised.md", slot)):
        write(root, rid, name, text)
        assert runs.complete_step(root, rid, step) == []
    import pytest
    with pytest.raises(runs.RunError, match="要入力"):
        runs.approve_publish(root, rid)
    write(root, rid, "05_revised.md", REVISED.replace("## 情報源", "## 僕自身の失敗\n(あなたが書いた体験)\n## 情報源", 1))
    runs.approve_publish(root, rid)  # 埋めたら通る
    assert (root / "runs" / rid / runs.READY_FILE).exists()


def test_briefing_shows_weekly_plan(root):
    plan(root)
    text = chief.briefing(root, date(2026, 10, 6))
    assert "週次企画" in text and "未承認" in text and "テーマ1" in text


def test_figure_spec_check():
    assert figures.check_specs([]) != []
    ok = [{"type": "bar", "name": "fig1_x", "title": "t", "labels": ["a", "b"], "series": [{"name": "s", "values": [1, 2]}]}]
    assert figures.check_specs(ok) == []
    bad = [{"type": "bar", "name": "../x", "title": "t", "labels": ["a"], "series": [{"name": "s", "values": [1, 2]}]}]
    probs = " ".join(figures.check_specs(bad))
    assert "name" in probs and "値の数" in probs


def test_make_figures_requires_spec(root):
    rid = runs.create_run(root, "ai-work", today=W)
    with pytest.raises(figures.FigureError, match="figures.json"):
        figures.make_figures(root, rid)


def test_old_long_title_type_is_no_longer_required(root):
    data = plan(root)
    data["items"][0]["title"] = "節約の始め方、まず見る3つ"
    (root / "plans" / W.isoformat() / "plan.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    assert weekly.validate_plan(root, W) == []


def test_long_alt_title_is_also_rejected(root):
    data = plan(root)
    data["items"][2]["alt_titles"] = ["短い案", "あ" * (weekly.TITLE_MAX + 1)]
    (root / "plans" / W.isoformat() / "plan.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    assert "3本目" in " ".join(weekly.validate_plan(root, W))
