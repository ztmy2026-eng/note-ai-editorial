from pathlib import Path

from note_editorial import images, reels


def test_scene_frames_title_then_text_scenes(tmp_path):
    cfg = images.load_config(tmp_path)
    pages = reels.scene_frames(tmp_path, ["タイトルです", "習慣1\n冷蔵庫を見る。", "詳しくはnoteで。"], cfg)
    assert len(pages) == 3
    assert 'class="tag"' in pages[0] and 'class="dots"' not in pages[0]
    assert pages[1].count('<i class="on">') == 1 and "習慣1" in pages[1]
    assert "1080px" in pages[0]


def test_ffmpeg_missing_message(monkeypatch):
    import builtins
    real = builtins.__import__

    def fake(name, *a, **k):
        if name == "imageio_ffmpeg":
            raise ImportError(name)
        return real(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake)
    monkeypatch.setattr(reels.shutil, "which", lambda n: None)
    import pytest
    with pytest.raises(reels.ReelError):
        reels.find_ffmpeg()
