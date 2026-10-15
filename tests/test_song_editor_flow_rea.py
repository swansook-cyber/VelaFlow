"""REA regression tests for editing, recovery, save and Suno export handoff."""
from copy import deepcopy

from core.song_editor_state import (
    EDITOR_DRAFT_KEY,
    build_song_editor_export,
    commit_song_editor_values,
    resolve_song_editor_values,
    song_editor_dirty_fields,
    stage_song_editor_draft,
)


def test_draft_survives_reload_without_overwriting_canonical_song():
    original = {
        "title": "แค่ส่วนเกิน",
        "selected_hook": {"hook_text": "พอเขากลับมา ฉันก็แค่ส่วนเกิน"},
        "complete_lyrics": "old lyrics",
        "normalized_song_output": "old lyrics",
        "music_style_prompt": "Pop Rock",
    }
    snapshot = deepcopy(original)
    staged = stage_song_editor_draft(original, "edited lyrics", "Soft Rock")
    assert original == snapshot
    assert staged["complete_lyrics"] == "old lyrics"
    assert staged["music_style_prompt"] == "Pop Rock"
    assert resolve_song_editor_values(staged) == {
        "lyrics": "edited lyrics",
        "style_prompt": "Soft Rock",
    }
    assert set(staged[EDITOR_DRAFT_KEY]["dirty_fields"]) == {"lyrics", "style_prompt"}


def test_save_commits_visible_values_and_clears_recovery_draft():
    original = {"complete_lyrics": "old", "music_style_prompt": "Pop", "manual_title": True}
    staged = stage_song_editor_draft(original, "new", "Rock")
    saved = commit_song_editor_values(staged, "new", "Rock")
    assert saved["complete_lyrics"] == "new"
    assert saved["normalized_song_output"] == "new"
    assert saved["music_style_prompt"] == "Rock"
    assert saved["manual_title"] is True
    assert EDITOR_DRAFT_KEY not in saved
    assert song_editor_dirty_fields(saved, "new", "Rock") == []


def test_export_uses_visible_unsaved_edits_without_mutating_song():
    song = {
        "title": "แค่ส่วนเกิน",
        "complete_lyrics": "saved",
        "normalized_song_output": "saved",
        "music_style_prompt": "Pop Rock",
    }
    snapshot = deepcopy(song)
    exported = build_song_editor_export(song, "unsaved visible lyric", "Acoustic")
    assert exported["complete_lyrics"] == "unsaved visible lyric"
    assert exported["normalized_song_output"] == "unsaved visible lyric"
    assert exported["music_style_prompt"] == "Acoustic"
    assert song == snapshot


def test_reverting_edits_clears_draft():
    song = {"complete_lyrics": "original", "music_style_prompt": "Rock"}
    changed = stage_song_editor_draft(song, "change", "Rock")
    reverted = stage_song_editor_draft(changed, "original", "Rock")
    assert EDITOR_DRAFT_KEY not in reverted
    assert resolve_song_editor_values(reverted)["lyrics"] == "original"
