"""Bounded, request-owned scratch space and session-owned ephemeral downloads."""
from __future__ import annotations

import secrets
import shutil
import tempfile
import threading
import time
from pathlib import Path

from core.stem_mixer import MAX_EXPORT_BYTES, MAX_STEM_BYTES, mix_stems

_RENDERS = threading.BoundedSemaphore(2)


class DownloadStore:
    """Process-local, bounded store. Tokens alone do not confer cross-session access."""

    def __init__(self, *, max_bytes=192 * 1024 * 1024, max_entries=4, ttl=600, clock=time.monotonic):
        self.max_bytes, self.max_entries, self.ttl, self.clock = max_bytes, max_entries, ttl, clock
        self._entries = {}
        self._lock = threading.Lock()

    def _expire(self):
        now = self.clock()
        self._entries = {k: v for k, v in self._entries.items() if now - v[2] < self.ttl}

    def put(self, owner: str, data: bytes) -> str:
        with self._lock:
            self._expire()
            others = {k: v for k, v in self._entries.items() if v[0] != owner}
            if len(others) >= self.max_entries or sum(len(v[1]) for v in others.values()) + len(data) > self.max_bytes:
                raise ValueError("Download capacity is busy. Clear a previous mix or try again later.")
            token = secrets.token_urlsafe(32)
            self._entries = {**others, token: (owner, data, self.clock())}
            return token

    def get(self, owner: str, token: str) -> bytes | None:
        with self._lock:
            self._expire()
            entry = self._entries.get(token)
            return entry[1] if entry and secrets.compare_digest(entry[0], owner) else None

    def discard(self, owner: str):
        with self._lock:
            self._expire()
            self._entries = {k: v for k, v in self._entries.items() if v[0] != owner}


DOWNLOADS = DownloadStore()


def render_uploaded_stems(vocal, instrumental, *, vocal_db=-6, instrumental_db=-6,
                          ffmpeg_path="", max_upload_bytes=MAX_STEM_BYTES, scratch_root=None) -> dict:
    """UI entrypoint: never retain uploads or generated audio on disk after returning.

    Upload buffers are written without making an extra full-size bytes copy. At most two
    requests render concurrently per process; busy callers fail without creating files.
    The caller owns the returned bounded WAV bytes, not a temporary filesystem path.
    """
    limit = min(max_upload_bytes, MAX_STEM_BYTES)
    uploads = (vocal, instrumental)
    if any(u is None or not 0 < u.size <= limit or Path(u.name).suffix.lower() not in {'.wav', '.mp3'}
           for u in uploads):
        return {"ok": False, "error": f"Supply two WAV/MP3 files, each at most {limit // (1024 * 1024)} MB"}
    if not _RENDERS.acquire(blocking=False):
        return {"ok": False, "error": "Two mixes are already processing. Try again shortly."}
    try:
        required = sum(u.size for u in uploads) + MAX_EXPORT_BYTES + 64 * 1024 * 1024
        if shutil.disk_usage(scratch_root or tempfile.gettempdir()).free < required:
            return {"ok": False, "error": "Insufficient temporary disk space for a safe mix"}
        with tempfile.TemporaryDirectory(prefix='velaflow-stem-', dir=scratch_root) as directory:
            folder = Path(directory)
            sources = []
            for index, upload in enumerate(uploads):
                source = folder / f"stem_{index}{Path(upload.name).suffix.lower()}"
                with source.open('wb') as stream:
                    view = upload.getbuffer()
                    try:
                        if len(view) != upload.size or len(view) > limit:
                            return {"ok": False, "error": "Upload size validation failed"}
                        stream.write(view)
                    finally:
                        view.release()
                sources.append(source)
            result = mix_stems(*sources, folder, vocal_db=vocal_db,
                               instrumental_db=instrumental_db, ffmpeg_path=ffmpeg_path)
            if not result.get('ok'):
                return result
            path = Path(result.pop('path'))
            if path.stat().st_size > MAX_EXPORT_BYTES:
                return {"ok": False, "error": "Mix exceeds download size limit"}
            return {**result, 'audio': path.read_bytes()}
    except (OSError, ValueError):
        return {"ok": False, "error": "Temporary audio workspace failed; no download was retained"}
    finally:
        _RENDERS.release()
