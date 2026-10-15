"""Regression checks for release metadata and export naming."""
from core.song_title_engine import is_placeholder_song_title
from core.suno_export import (
    build_release_package_data,
    resolve_export_txt_filename,
    resolve_lyrics_download_filename,
)


def test_placeholder_project_name_does_not_become_release_title():
    song = {
        "title": "โปรเจกต์เพลงใหม่",
        "idea": "ตัวสำรองที่ถูกลืมเมื่อคนรักเก่ากลับมา",
        "selected_hook": {"hook_text": "พอเขากลับมา ฉันก็แค่ส่วนเกิน"},
        "complete_lyrics": "[Chorus]\nพอเขากลับมา ฉันก็แค่ส่วนเกิน",
    }
    release = build_release_package_data(song, "โปรเจกต์เพลงใหม่")
    title = release["song_metadata"]["song_title"]
    assert title
    assert not is_placeholder_song_title(title)
    assert "โปรเจกต์เพลงใหม่" not in resolve_export_txt_filename(song, "โปรเจกต์เพลงใหม่")
    assert "โปรเจกต์เพลงใหม่" not in resolve_lyrics_download_filename(song, "โปรเจกต์เพลงใหม่")


def test_user_approved_real_title_is_preserved():
    song = {"title": "แค่ส่วนเกิน", "manual_title": True, "idea": "เพลงเศร้า"}
    release = build_release_package_data(song, "โปรเจกต์เพลงใหม่")
    assert release["song_metadata"]["song_title"] == "แค่ส่วนเกิน"
