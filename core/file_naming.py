from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from core.song_title_engine import is_placeholder_song_title


INVALID_FILENAME_CHARS = r'\\/:*?"<>|'


def sanitize_filename(text: str | None) -> str:
    cleaned = str(text or "").strip()
    cleaned = re.sub(f"[{re.escape(INVALID_FILENAME_CHARS)}]+", "", cleaned)
    cleaned = re.sub(r"\s+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("._ ")
    return cleaned or "Untitled_Song"


def make_safe_filename(name: str | None) -> str:
    cleaned = str(name or "").strip()
    cleaned = re.sub(f"[{re.escape(INVALID_FILENAME_CHARS)}]+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = cleaned.rstrip(". ")
    return (cleaned or "Untitled")[:120].rstrip(". ") or "Untitled"


def export_name_base(song_title: str | None = None, original_filename: str | None = None) -> str:
    title = "" if is_placeholder_song_title(song_title) else str(song_title or "").strip()
    if title:
        return make_safe_filename(title)
    original = Path(str(original_filename or "")).stem.strip()
    if original:
        return make_safe_filename(original)
    return "Untitled"


def build_asset_export_filename(song_title: str | None, original_filename: str | None, suffix: str, ext: str) -> str:
    base = export_name_base(song_title, original_filename)
    clean_suffix = make_safe_filename(suffix).replace(" ", "_")
    clean_ext = str(ext or "").lstrip(".") or "txt"
    return f"{base}_{clean_suffix}.{clean_ext}"


def _normalize_type(export_type: str | None) -> str:
    value = sanitize_filename(export_type or "Export")
    aliases = {
        "song_only": "Lyrics_Only",
        "full_pipeline": "Suno_Export",
        "suno": "Suno_Export",
        "lyrics": "Lyrics_Only",
        "creator_package": "Creator_Package",
        "release_package": "Release_Package",
        "remaster_package": "Remaster_Package",
        "affiliate_package": "Affiliate_Package",
    }
    return aliases.get(value.lower(), value)


def build_export_filename(song_title: str | None, artist_name: str | None, export_type: str | None, ext: str | None) -> str:
    title = sanitize_filename("Untitled Song" if is_placeholder_song_title(song_title) else song_title)
    artist = sanitize_filename(artist_name or "Vela_Moon")
    kind = _normalize_type(export_type)
    suffix = str(ext or "").lstrip(".") or "txt"
    return f"{title}_{artist}_{kind}.{suffix}"


def ensure_unique_path(path: str | Path) -> Path:
    target = Path(path)
    if not target.exists():
        return target
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return target.with_name(f"{target.stem}_{timestamp}{target.suffix}")
