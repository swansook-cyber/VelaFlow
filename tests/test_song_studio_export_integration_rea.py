"""Integration guard: exported Suno files match visible Song Editor values."""
from copy import deepcopy
from pathlib import Path

from core.song_editor_state import build_song_editor_export
from core.suno_export import export_suno_files


def test_suno_export_uses_edited_lyrics_and_style_without_changing_original(tmp_path: Path):
    song = {
        "title": "แค่ส่วนเกิน",
        "manual_title": True,
        "artist": "Vela Moon",
        "idea": "ความรักของคนที่เป็นตัวสำรอง",
        "complete_lyrics": "[Verse 1]\nเนื้อเพลงเก่า",
        "normalized_song_output": "[Verse 1]\nเนื้อเพลงเก่า",
        "music_style_prompt": "old style prompt",
        "selected_hook": {"hook_text": "พอเขากลับมา ฉันก็แค่ส่วนเกิน"},
    }
    original = deepcopy(song)
    latest_lyrics = "[Verse 1]\nครั้งนี้ฉันเลือกเดินต่อ\n[Chorus]\nพอเขากลับมา ฉันก็แค่ส่วนเกิน"
    latest_style = "Thai emotional pop rock, acoustic guitars, 94 BPM"
    export_input = build_song_editor_export(song, latest_lyrics, latest_style)
    result = export_suno_files("เพลงทดสอบ", export_input, base_dir=tmp_path)
    assert result["ok"], result
    data = result["data"]
    assert data["lyrics_only_text"] == latest_lyrics
    assert data["suno_style_only_text"] == latest_style
    assert latest_lyrics in Path(data["lyrics_only"]).read_text(encoding="utf-8")
    assert latest_style in Path(data["suno_style_only"]).read_text(encoding="utf-8")
    assert latest_lyrics in data["suno_full_text"]
    assert latest_style in data["suno_full_text"]
    assert "โปรเจกต์เพลงใหม่" not in data["suno_full_filename"]
    assert song == original
