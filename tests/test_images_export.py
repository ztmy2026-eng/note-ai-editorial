import shutil

import pytest

from note_editorial import export, images, runs
from conftest import REPO, SNS

SNS_SLIDES = SNS.replace("1枚目: タイトル / 2枚目: チェック表", "1枚目: 表紙の言葉\n2枚目: 確認表 <b>&\n3枚目: 詳しくは記事へ【記事URL】")


def test_slides_parsed_in_order_and_url_token_removed():
    slides = images.slides_from_sns(SNS_SLIDES)
    assert slides == ["表紙の言葉", "確認表 <b>&", "詳しくは記事へ"]


def test_no_slides_when_format_differs():
    assert images.slides_from_sns(SNS.replace("1枚目: タイトル / 2枚目: チェック表", "表紙とチェック表")) == []  # 「N枚目:」の行が無ければ空


def test_html_escapes_text_and_applies_colors():
    cfg = images.load_config(REPO)
    page = images.slide_html(1, 3, "確認表 <b>&", cfg)
    assert "&lt;b&gt;&amp;" in page and "<b>" not in page.split("<body>")[1]
    assert cfg["colors"]["accent"] in page


def test_title_split_and_font_shrinks():
    assert images.split_title("議事録とメールを任せる前に。入力前の注意と表") == ("議事録とメールを任せる前に。", "入力前の注意と表")
    assert images.split_title("短いタイトル") == ("短いタイトル", "")
    assert images._size_for("あ" * 10, 76, 8) > images._size_for("あ" * 40, 76, 8)


def test_config_override_merges(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "images.yaml").write_text("colors:\n  accent: '#ff0000'\nfooter: '@me'\n", encoding="utf-8")
    cfg = images.load_config(tmp_path)
    assert cfg["colors"]["accent"] == "#ff0000" and cfg["colors"]["background"] == "#0f2a43" and cfg["footer"] == "@me"


def test_missing_browser_gives_clear_error(monkeypatch):
    monkeypatch.setattr(images.glob, "glob", lambda *_: [])
    monkeypatch.setattr(images.shutil, "which", lambda *_: None)
    monkeypatch.setattr(images.Path, "exists", lambda self: False)
    with pytest.raises(images.ImageError, match="browser_path"):
        images.find_browser({"browser_path": ""})


def test_render_makes_png_of_expected_size(tmp_path):
    try:
        browser = images.find_browser(images.load_config(REPO))
    except images.ImageError:
        pytest.skip("ブラウザが無い環境")
    cfg = images.load_config(REPO)
    out = tmp_path / "e.png"
    images.render(images.eyecatch_html("議事録とメールをAIに任せる前に。入力前の注意と表", cfg), out, images.EYECATCH_SIZE, browser, tmp_path / "w")
    assert images.png_size(out) == images.EYECATCH_SIZE


READY = "# 題名です。補足\n\n本文です。\n\n## 見出し\n中身\n\n## 情報源\n- 外部の情報源は使用していません(筆者の体験のみ)\n"


def test_split_note_drops_only_the_no_source_line():
    title, body = export.split_note(READY)
    assert title == "題名です。補足" and "情報源" not in body and "## 見出し" in body
    title, body = export.split_note(READY.replace("外部の情報源は使用していません(筆者の体験のみ)", "https://example.com/a"))
    assert "情報源" in body and "https://example.com/a" in body


def test_export_requires_publish_approval(root):
    rid = runs.create_run(root, "ai-work")
    with pytest.raises(runs.RunError, match="承認2"):
        export.export_note(root, rid)


def test_wbr_inserted_only_at_punctuation_and_text_stays_escaped():
    out = images._esc("確認表<b>、次の項目(重要)")
    assert "&lt;b&gt;" in out and "、<wbr>" in out and "<wbr>(" in out and ")<wbr>" in out
    assert "<b>" not in out
