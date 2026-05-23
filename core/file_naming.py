from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


INVALID_FILENAME_CHARS = r'\\/:*?"<>|'


def sanitize_filename(text: str | None) -> str:
    cleaned = str(text or "").strip()
    cleaned = re.sub(f"[{re.escape(INVALID_FILENAME_CHARS)}]+", "", cleaned)
    cleaned = re.sub(r"\s+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("._ ")
    return cleaned or "Untitled_Song"


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
    title = sanitize_filename(song_title)
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
