import shutil
from pathlib import Path

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
    assert cfg["colors"]["accent"] == "#ff0000" and cfg["colors"]["background"] == "#ffd43b" and cfg["footer"] == "@me"


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


def test_clean_url_drops_tracking_params_and_rejects_non_urls():
    assert export.clean_url("https://note.com/a/n/nabc?sub_rt=share_pb") == "https://note.com/a/n/nabc"
    with pytest.raises(runs.RunError):
        export.clean_url("note.com/a")


def test_fill_url_keeps_original_and_replaces_token(root):
    from conftest import RESEARCH, IDEAS, DRAFT, CRITIQUE, REVISED, write
    rid = runs.create_run(root, "ai-work")
    (root / "runs" / rid / "06_sns.md").write_text(SNS, encoding="utf-8")
    out = export.fill_article_url(root, rid, "https://note.com/a/n/nabc?x=1")
    assert "https://note.com/a/n/nabc" in out.read_text(encoding="utf-8") and "【記事URL】" not in out.read_text(encoding="utf-8")
    assert "【記事URL】" in (root / "runs" / rid / "06_sns.md").read_text(encoding="utf-8")  # 承認済みの原本は変えない

def test_render_passes_an_absolute_screenshot_path(tmp_path, monkeypatch):
    """相対パスで渡すと、ブラウザが自分の作業フォルダに保存してしまい、画像ができたのに見つからなくなる(Windowsで起きた)。"""
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        out = next(c for c in cmd if c.startswith("--screenshot=")).split("=", 1)[1]
        Path(out).write_bytes(b"png")

    monkeypatch.setattr(images.subprocess, "run", fake_run)
    monkeypatch.chdir(tmp_path)
    images.render("<p>x</p>", Path("rel/out.png"), (10, 10), "browser", Path("rel/_work"))
    shot = next(c for c in seen["cmd"] if c.startswith("--screenshot=")).split("=", 1)[1]
    assert Path(shot).is_absolute()


def test_slash_line_breaks_in_slides_become_newlines_but_plain_slashes_stay():
    assert images.slide_text("見える形にしたいのは2つ。/寄った回数と、") == "見える形にしたいのは2つ。\n寄った回数と、"
    assert images.slide_text("コツ1 数える / コツ2 聞く") == "コツ1 数える\nコツ2 聞く"
    assert images.slide_text("AI/家計の話") == "AI/家計の話"

def test_slides_can_be_written_over_several_lines():
    text = "## Instagram投稿案\n1枚目\n表紙の言葉\nもう1行\n\n2枚目: 1行で書く形も読める\n\n3枚目\n詳しくは記事へ【記事URL】\n## Instagramキャプション\n本文\n"
    assert images.slides_from_sns(text) == ["表紙の言葉\nもう1行", "1行で書く形も読める", "詳しくは記事へ"]

