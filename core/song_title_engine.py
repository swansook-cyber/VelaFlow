from __future__ import annotations

import re
from typing import Any


PLACEHOLDER_TITLES = {
    "",
    "demo song",
    "untitled song",
    "new song",
    "song only",
    "current session",
    "project",
    "เพลงใหม่ของฉัน",
}


def is_placeholder_song_title(value: str | None) -> bool:
    normalized = re.sub(r"\s+", " ", str(value or "").strip()).lower()
    return normalized in PLACEHOLDER_TITLES or normalized.startswith("demo_song")


def _clean_phrase(value: str) -> str:
    text = re.sub(r"[\[\]{}()\"'“”‘’!?.,:;|/\\]+", " ", str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _first_usable_line(value: str) -> str:
    for raw in str(value or "").replace("\r\n", "\n").splitlines():
        line = _clean_phrase(raw)
        if line and not line.startswith("["):
            return line
    return ""


def _shorten_thai_phrase(text: str) -> str:
    phrase = _clean_phrase(text)
    if not phrase:
        return ""
    replacements = [
        ("ยังลืมแฟนเก่าไม่ได้", "ลืมเธอไม่ได้"),
        ("ลืมแฟนเก่าไม่ได้", "ลืมเธอไม่ได้"),
        ("รักคนที่ไม่กลับมา", "คนที่ไม่กลับมา"),
        ("คิดถึงแฟนเก่า", "คิดถึงเธอ"),
        ("ยังคิดถึงเธออยู่", "ยังคิดถึงเธอ"),
    ]
    compact = re.sub(r"\s+", "", phrase)
    for source, title in replacements:
        if source in compact:
            return title
    if len(phrase.split()) >= 2:
        words = phrase.split()
        return " ".join(words[:5])
    for prefix in ["เพลงเกี่ยวกับ", "เรื่อง", "อยากได้เพลง", "เพลง", "เกี่ยวกับ", "ยัง"]:
        if phrase.startswith(prefix) and len(phrase) > len(prefix) + 2:
            phrase = phrase[len(prefix):].strip()
    if "ที่ไม่กลับมา" in phrase:
        start = phrase.find("คน")
        if start >= 0:
            phrase = phrase[start:]
    if len(phrase) > 18:
        phrase = phrase[:18].strip()
    return phrase


def generate_song_title_from_idea(idea: str = "", hook_text: str = "", lyrics: str = "") -> str:
    """Create a short Thai-first title from idea + hook without needing an API."""
    hook = _first_usable_line(hook_text)
    idea_line = _first_usable_line(idea)
    lyric_line = _first_usable_line(lyrics)
    for candidate in [hook, idea_line, lyric_line]:
        title = _shorten_thai_phrase(candidate)
        if title and not is_placeholder_song_title(title):
            return title
    return "เพลงของฉัน"


def resolve_song_title(song: dict[str, Any], project_name: str = "") -> str:
    manual = str(song.get("title") or song.get("song_title") or "").strip()
    if manual and not is_placeholder_song_title(manual):
        return manual
    generated = generate_song_title_from_idea(
        idea=str(song.get("idea") or song.get("song_idea") or song.get("concept") or project_name or ""),
        hook_text=str((song.get("selected_hook") or {}).get("hook_text") if isinstance(song.get("selected_hook"), dict) else song.get("selected_hook_text") or ""),
        lyrics=str(song.get("normalized_song_output") or song.get("complete_lyrics") or ""),
    )
    return generated
