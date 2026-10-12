

def test_cover_icons_and_background_variety(tmp_path):
    from note_editorial import figures
    for icon in ("bolt", "aircon", "phone", "bulb", "flame", "calendar", "receipt", "yen"):
        assert icon in figures.ICONS
    ok = {"type": "cover", "name": "c", "tag": "節約", "title_html": "テスト", "icon": "bolt", "bg": "lemon"}
    assert figures.check_specs([ok]) == []
    assert figures.check_specs([dict(ok, icon="nothing")])
    assert figures.check_specs([dict(ok, bg="red")])
    assert figures.check_specs([dict(ok, bg="#ffe066")]) == []
    html = figures.cover(ok)
    assert "#ffe066" in html and "<svg" in html
    days = []
    for d in range(10, 15):
        specs = [{"type": "cover", "name": "c", "tag": "節約", "title_html": "t"}]
        figures._vary_cover_bg(specs, f"2026-10-{d}_001")
        days.append(specs[0]["bg"])
    assert len(set(days)) == 5


def test_render_all_falls_back_to_cli_without_playwright(tmp_path, monkeypatch):
    import builtins
    from note_editorial import figures
    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name.startswith("playwright"):
            raise ImportError(name)
        return real_import(name, *a, **k)

    called = {}
    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(figures, "render_all_cli", lambda specs, out_dir: called.setdefault("ok", out_dir) or [])
    figures.render_all([{"type": "cover", "name": "c", "tag": "t", "title_html": "x"}], tmp_path)
    assert called["ok"] == tmp_path


def test_cat_mascot_cover_with_sub_and_red_text():
    from note_editorial import figures
    for icon in ("cat", "cat_happy", "cat_worry", "cat_think"):
        assert icon in figures.ICONS
    spec = {"type": "cover", "name": "c", "tag": "節約", "title_html": "疲れる<b>3つ</b>", "sub": "続ける<b>3つ</b>の考え方", "icon": "cat_worry"}
    assert figures.check_specs([spec]) == []
    html = figures.cover(spec)
    assert "#d62f1f" in html and "続ける" in html and "&lt;b&gt;" not in html
    assert 'width="460" height="483"' in html  # 猫は、背景に直接置く(大きめ)


def test_cover_with_photo_embeds_the_file(tmp_path):
    from note_editorial import figures
    img = tmp_path / "cat.jpg"
    img.write_bytes(b"\xff\xd8\xff\xd9")
    spec = {"type": "cover", "name": "c", "tag": "節約", "title_html": "題", "photo": str(img)}
    html = figures.cover(spec)
    assert "data:image/jpeg;base64," in html and "object-fit:cover" in html
    import pytest
    with pytest.raises(figures.FigureError):
        figures.cover(dict(spec, photo=str(tmp_path / "none.jpg")))
