"""Additional integration coverage for filenames, UTF-8 and repeat exports."""
from pathlib import Path

from core.song_editor_state import build_song_editor_export
from core.suno_export import export_suno_files


def _song():
    return {
        "title": "แค่ส่วนเกิน",
        "manual_title": True,
        "artist": "Vela Moon",
        "idea": "ตัวสำรองที่ถูกลืม",
        "complete_lyrics": "[Chorus]\nพอเขากลับมา ฉันก็แค่ส่วนเกิน",
        "normalized_song_output": "[Chorus]\nพอเขากลับมา ฉันก็แค่ส่วนเกิน",
        "music_style_prompt": "Thai Pop Rock",
    }


def test_repeated_exports_do_not_overwrite_previous_files(tmp_path: Path):
    first = export_suno_files("เพลงทดสอบ", _song(), base_dir=tmp_path)
    assert first["ok"], first
    second = export_suno_files("เพลงทดสอบ", _song(), base_dir=tmp_path)
    assert second["ok"], second
    for key in ("lyrics_only", "suno_full_package", "suno_style_only"):
        first_path = Path(first["data"][key])
        second_path = Path(second["data"][key])
        assert first_path != second_path, key
        assert first_path.exists() and second_path.exists(), key


def test_thai_utf8_lyrics_and_suno_full_text_are_readable(tmp_path: Path):
    lyrics = "[Verse 1]\nคำว่าใจไม่ใช่ของเล่น\n[Chorus]\nฉันไม่ใช่ตัวสำรอง"
    song = build_song_editor_export(_song(), lyrics, "Thai emotional rock")
    result = export_suno_files("โปรเจกต์เพลงใหม่", song, base_dir=tmp_path)
    assert result["ok"], result
    data = result["data"]
    assert Path(data["lyrics_only"]).read_text(encoding="utf-8") == lyrics
    assert lyrics in Path(data["suno_full_package"]).read_text(encoding="utf-8-sig")
    assert "โปรเจกต์เพลงใหม่" not in data["suno_full_filename"]
