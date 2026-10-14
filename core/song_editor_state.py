from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any


EDITOR_DRAFT_KEY = "creator_editor_draft"


def _lyrics(song: dict[str, Any]) -> str:
    return str(song.get("normalized_song_output") or song.get("complete_lyrics") or "")


def _style_prompt(song: dict[str, Any]) -> str:
    return str(song.get("music_style_prompt") or song.get("style_prompt") or "")


def resolve_song_editor_values(song: dict[str, Any]) -> dict[str, str]:
    """Return recoverable editor values without changing canonical song data."""
    draft = song.get(EDITOR_DRAFT_KEY)
    if isinstance(draft, dict):
        return {
            "lyrics": str(draft.get("lyrics", _lyrics(song))),
            "style_prompt": str(draft.get("style_prompt", _style_prompt(song))),
        }
    return {"lyrics": _lyrics(song), "style_prompt": _style_prompt(song)}


def song_editor_dirty_fields(song: dict[str, Any], lyrics: str, style_prompt: str) -> list[str]:
    dirty: list[str] = []
    if str(lyrics) != _lyrics(song):
        dirty.append("lyrics")
    if str(style_prompt) != _style_prompt(song):
        dirty.append("style_prompt")
    return dirty


def stage_song_editor_draft(song: dict[str, Any], lyrics: str, style_prompt: str) -> dict[str, Any]:
    """Store a reload-safe draft while leaving saved/exported fields untouched."""
    updated = deepcopy(song)
    dirty_fields = song_editor_dirty_fields(updated, lyrics, style_prompt)
    if dirty_fields:
        updated[EDITOR_DRAFT_KEY] = {
            "lyrics": str(lyrics),
            "style_prompt": str(style_prompt),
            "dirty_fields": dirty_fields,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
    else:
        updated.pop(EDITOR_DRAFT_KEY, None)
    return updated


def commit_song_editor_values(song: dict[str, Any], lyrics: str, style_prompt: str) -> dict[str, Any]:
    """Promote editor values to canonical song fields while preserving metadata."""
    updated = deepcopy(song)
    updated["complete_lyrics"] = str(lyrics)
    updated["normalized_song_output"] = str(lyrics)
    updated["music_style_prompt"] = str(style_prompt)
    if "style_prompt" in updated:
        updated["style_prompt"] = str(style_prompt)
    updated.pop(EDITOR_DRAFT_KEY, None)
    return updated


def build_song_editor_export(song: dict[str, Any], lyrics: str, style_prompt: str) -> dict[str, Any]:
    """Build export input from visible editor state without mutating the caller."""
    return commit_song_editor_values(song, lyrics, style_prompt)
