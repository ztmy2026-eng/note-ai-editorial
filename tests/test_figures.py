

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
