from __future__ import annotations

import json
import hashlib
import math
import shutil
import subprocess
import uuid
import zipfile
from array import array
from datetime import datetime
from pathlib import Path
from typing import Any

from core.file_naming import build_asset_export_filename, ensure_unique_path, export_name_base, make_safe_filename, sanitize_filename
from core.paths import ROOT
from core.project_io import safe_name
from core.real_clip_pipeline import find_ffmpeg, probe_media


AUDIO_EDITOR_CUT_MODES = ["Lossless Quick Cut", "Precise Cut"]
SUPPORTED_AUDIO_EDITOR_FORMATS = {"mp3", "wav"}
AUDIO_EDITOR_FADE_OPTIONS = {
    "Off": 0.0,
    "0.1 second": 0.1,
    "0.25 second": 0.25,
    "0.5 second": 0.5,
    "1.0 second": 1.0,
}
HOOK_DURATION_PRESETS = {
    "15 seconds": 15.0,
    "30 seconds": 30.0,
    "45 seconds": 45.0,
    "60 seconds": 60.0,
    "Custom": 0.0,
}
HOOK_ANALYSIS_DURATIONS = [30.0, 15.0]
HOOK_ANALYSIS_STEP_SECONDS = 2.0
WAVEFORM_TARGET_POINTS = 1600
MIN_AUDIO_SELECTION_SECONDS = 0.1
CUT_BOUNDARY_SMOOTHING_SECONDS = 0.008
SELECTION_PREVIEW_CACHE_LIMIT = 24
SELECTION_PREVIEW_PROCESSING_VERSION = "3"
PHRASE_COMPLETION_LOOKAHEAD_SECONDS = 10.0
PHRASE_STABLE_BOUNDARY_SECONDS = 0.5
SMART_HOOK_TYPES = {
    "Short Hook": {"soft_range": (15.0, 25.0), "suffix": "ShortHook"},
    "Best Hook": {"soft_range": (25.0, 45.0), "suffix": "BestHook"},
    "Extended Hook": {"soft_range": (40.0, 70.0), "suffix": "ExtendedHook"},
    "Full Chorus": {"soft_range": (25.0, 75.0), "suffix": "FullChorus"},
}
JOIN_CROSSFADE_DURATIONS = (1.0, 2.0, 3.0, 5.0)
JOIN_MAX_NEW_TRACKS = 8
JOIN_DEFAULT_TRANSITION = {"enabled": False, "duration": 2.0}


def build_join_project_scope(project_identity: str) -> str:
    identity = str(project_identity or "audio_joiner").strip() or "audio_joiner"
    return hashlib.sha1(identity.encode("utf-8", errors="replace")).hexdigest()[:12]


def create_join_track_instance(source: dict[str, Any], *, track_id: str = "") -> dict[str, Any]:
    """Create an independently editable track while retaining shared source identity."""
    resolved = dict(source or {})
    source_id = str(resolved.get("source_id") or resolved.get("upload_id") or resolved.get("path") or "")
    resolved["source_id"] = source_id
    resolved["track_id"] = str(track_id or f"join-{uuid.uuid4().hex}")
    return resolved


def join_pair_id(left_track: dict[str, Any], right_track: dict[str, Any]) -> str:
    left = str(left_track.get("track_id") or left_track.get("upload_id") or left_track.get("path") or "")
    right = str(right_track.get("track_id") or right_track.get("upload_id") or right_track.get("path") or "")
    return f"{left}|{right}"


def reorder_join_tracks(tracks: list[dict[str, Any]], ordered_track_ids: list[str]) -> dict[str, Any]:
    current = [str(track.get("track_id") or "") for track in tracks]
    requested = [str(track_id or "") for track_id in ordered_track_ids]
    if not current or len(requested) != len(current) or len(set(requested)) != len(requested) or set(requested) != set(current):
        return {"ok": False, "tracks": [dict(track) for track in tracks], "error": "invalid_track_order"}
    by_id = {str(track.get("track_id")): dict(track) for track in tracks}
    return {"ok": True, "tracks": [by_id[track_id] for track_id in requested], "error": ""}


def reconcile_join_pair_settings(
    tracks: list[dict[str, Any]], pair_settings: dict[str, dict[str, Any]] | None,
) -> dict[str, Any]:
    stored = pair_settings or {}
    active: dict[str, dict[str, Any]] = {}
    crossfades: list[dict[str, Any]] = []
    for index in range(max(0, len(tracks) - 1)):
        pair_id = join_pair_id(tracks[index], tracks[index + 1])
        raw = dict(stored.get(pair_id) or JOIN_DEFAULT_TRANSITION)
        duration = float(raw.get("duration") or 2.0)
        if duration not in JOIN_CROSSFADE_DURATIONS:
            duration = 2.0
        resolved = {"enabled": bool(raw.get("enabled", False)), "duration": duration}
        active[pair_id] = resolved
        crossfades.append(dict(resolved))
    return {"pair_settings": active, "crossfades": crossfades}


def calculate_join_total_duration(tracks: list[dict[str, Any]], crossfades: list[dict[str, Any]] | None = None) -> float:
    total = 0.0
    for track in tracks:
        source_duration = max(0.0, float(track.get("duration") or 0.0))
        start = max(0.0, float(track.get("start") or 0.0))
        end = min(source_duration, float(track.get("end") or source_duration))
        total += max(0.0, end - start)
    for transition in crossfades or []:
        if transition.get("enabled"):
            total -= max(0.0, float(transition.get("duration") or 0.0))
    return round(max(0.0, total), 3)


def build_join_transition_preview_tracks(
    left_track: dict[str, Any], right_track: dict[str, Any], *, context_seconds: float = 5.0,
) -> list[dict[str, Any]]:
    context = max(1.0, min(8.0, float(context_seconds or 5.0)))
    left = dict(left_track)
    right = dict(right_track)
    left_start = max(0.0, float(left.get("start") or 0.0))
    left_end = min(float(left.get("duration") or 0.0), float(left.get("end") or left.get("duration") or 0.0))
    right_start = max(0.0, float(right.get("start") or 0.0))
    right_end = min(float(right.get("duration") or 0.0), float(right.get("end") or right.get("duration") or 0.0))
    left.update({"start": round(max(left_start, left_end - context), 3), "end": round(left_end, 3)})
    right.update({"start": round(right_start, 3), "end": round(min(right_end, right_start + context), 3)})
    return [left, right]


def build_upload_identity(original_filename: str, payload: bytes) -> dict[str, Any]:
    """Build a stable upload identity from the original name and uploaded bytes."""
    content = bytes(payload or b"")
    filename = str(original_filename or "audio").strip()
    content_digest = hashlib.sha256(content).hexdigest()
    identity_digest = hashlib.sha256()
    identity_digest.update(filename.encode("utf-8", errors="replace"))
    identity_digest.update(b"\0")
    identity_digest.update(str(len(content)).encode("ascii"))
    identity_digest.update(b"\0")
    identity_digest.update(content_digest.encode("ascii"))
    return {
        "upload_id": identity_digest.hexdigest(),
        "original_filename": filename,
        "size_bytes": len(content),
        "content_digest": content_digest,
    }


def save_uploaded_audio_once(
    destination: str | Path,
    *,
    original_filename: str,
    payload: bytes,
    previous_upload_id: str = "",
) -> dict[str, Any]:
    """Write an upload only when its stable content identity has changed."""
    output = Path(destination)
    identity = build_upload_identity(original_filename, payload)
    unchanged = bool(previous_upload_id and previous_upload_id == identity["upload_id"] and output.is_file())
    if not unchanged:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(bytes(payload or b""))
    return {
        "ok": True,
        "path": str(output),
        **identity,
        "source_changed": not unchanged,
        "saved": not unchanged,
        "save_count": 1 if not unchanged else 0,
    }


def _source_signature(path: Path, trusted_identity: dict[str, Any] | None = None) -> dict[str, Any]:
    stat = path.stat()
    trusted = trusted_identity or {}
    upload_id = str(trusted.get("upload_id") or "").strip()
    stored_digest = str(trusted.get("content_digest") or trusted.get("sha256") or "").strip()
    stored_size = int(trusted.get("size_bytes") or trusted.get("size") or 0)
    if upload_id and stored_digest and stored_size == stat.st_size:
        return {
            "path": str(path.resolve()),
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "upload_id": upload_id,
            "sha256": stored_digest,
            "identity_source": "trusted_upload",
        }
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(path.resolve()), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns, "sha256": digest.hexdigest(), "identity_source": "disk_hash"}


def build_source_signature(path: str | Path, trusted_identity: dict[str, Any] | None = None) -> dict[str, Any]:
    return _source_signature(Path(path), trusted_identity=trusted_identity)


def cached_probe_media(
    path: str | Path,
    cache: dict[str, Any],
    *,
    source_identity: str,
    ffmpeg_path: str = "",
    probe_func: Any | None = None,
    max_entries: int = 24,
) -> dict[str, Any]:
    """Cache FFprobe metadata in a caller-owned, session-local mapping."""
    source = Path(path)
    identity = str(source_identity or "").strip()
    if not identity:
        signature = _source_signature(source)
        identity = str(signature.get("sha256") or "")
    cache_key = f"{source.resolve()}|{identity}|{ffmpeg_path or 'auto'}"
    cached = cache.get(cache_key)
    if isinstance(cached, dict):
        return {**cached, "cache_status": "hit"}
    probe = (probe_func or probe_media)(source, ffmpeg_path=ffmpeg_path)
    result = {**dict(probe or {}), "cache_status": "miss"}
    while len(cache) >= max(1, int(max_entries or 1)):
        cache.pop(next(iter(cache)))
    cache[cache_key] = dict(result)
    return result


def reset_source_dependent_state(workflow_state: dict[str, Any], session_state: dict[str, Any], workflow: str) -> None:
    """Reset only state that belongs to a changed audio source."""
    normalized = str(workflow or "").strip().lower()
    if normalized == "audio_editor":
        for key in (
            "hook_analysis",
            "rough_selection",
            "smart_refined_hook",
            "smart_override_status",
            "hook_quality",
            "hook_quality_source_id",
            "preview_result",
            "waveform",
            "last_result",
            "last_ok",
            "last_error",
            "start_time",
            "end_time",
        ):
            workflow_state.pop(key, None)
        for key in (
            "audio_editor_selection_source_id",
            "audio_editor_selection_start",
            "audio_editor_selection_end",
        ):
            session_state.pop(key, None)
        preview_prefixes = ("audio_editor_",)
    else:
        for key in ("last_result", "last_ok", "last_error", "active_master", "preview_diagnostics"):
            workflow_state.pop(key, None)
        recommendation = workflow_state.get("remaster_recommendation") or {}
        if recommendation.get("source") == "audio_analysis":
            workflow_state.pop("remaster_recommendation", None)
        preview_prefixes = ("remaster_original", "remaster_mastered", "remaster_ab_")
    preview_cache = session_state.get("remaster_preview_bytes_cache")
    if isinstance(preview_cache, dict):
        for key in list(preview_cache):
            if str(key).startswith(preview_prefixes):
                preview_cache.pop(key, None)


def format_timecode(seconds: float) -> str:
    total_ms = max(0, int(round(float(seconds or 0) * 1000)))
    minutes, rem_ms = divmod(total_ms, 60_000)
    secs, millis = divmod(rem_ms, 1000)
    return f"{minutes:02d}:{secs:02d}.{millis:03d}"


def parse_time_input(value: str | float | int) -> float:
    if isinstance(value, (int, float)):
        seconds = float(value)
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError("time cannot be negative")
        return seconds
    text = str(value or "").strip()
    if not text:
        raise ValueError("time is empty")
    if ":" not in text:
        seconds = float(text)
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError("time cannot be negative")
        return seconds
    parts = text.split(":")
    if len(parts) != 2:
        raise ValueError("time must be MM:SS or seconds")
    minutes = int(parts[0])
    seconds = float(parts[1])
    if minutes < 0 or not math.isfinite(seconds) or seconds < 0 or seconds >= 60:
        raise ValueError("invalid MM:SS value")
    return minutes * 60 + seconds


def clamp_audio_selection(start: float, end: float, duration: float, *, min_gap: float = 0.1) -> dict[str, float]:
    source_duration = max(0.0, float(duration or 0.0))
    gap = max(0.001, float(min_gap or 0.1))
    if source_duration <= gap:
        return {"start": 0.0, "end": source_duration, "duration": source_duration}
    clean_start = max(0.0, min(source_duration - gap, float(start or 0.0)))
    clean_end = max(clean_start + gap, min(source_duration, float(end or 0.0)))
    if clean_end > source_duration:
        clean_end = source_duration
        clean_start = max(0.0, clean_end - gap)
    return {"start": round(clean_start, 3), "end": round(clean_end, 3), "duration": round(clean_end - clean_start, 3)}


def move_audio_selection_region(start: float, end: float, delta: float, duration: float, *, min_gap: float = 0.1) -> dict[str, float]:
    selection = clamp_audio_selection(start, end, duration, min_gap=min_gap)
    region_duration = selection["duration"]
    source_duration = max(0.0, float(duration or 0.0))
    if source_duration <= region_duration:
        return selection
    next_start = max(0.0, min(source_duration - region_duration, selection["start"] + float(delta or 0.0)))
    return {"start": round(next_start, 3), "end": round(next_start + region_duration, 3), "duration": round(region_duration, 3)}


def build_audio_editor_project_id(original_name: str) -> str:
    stem = sanitize_filename(Path(original_name).stem or "audio_editor")
    return safe_name(f"{stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")


def validate_audio_editor_input(path: str | Path, *, mime_type: str = "", max_upload_mb: int = 200) -> dict[str, Any]:
    source = Path(path)
    ext = source.suffix.lower().lstrip(".")
    if not source.is_file():
        return {"ok": False, "error": "missing_audio", "message": "Audio file missing"}
    if ext not in SUPPORTED_AUDIO_EDITOR_FORMATS:
        return {"ok": False, "error": "unsupported_format", "message": "Audio Editor supports MP3 and WAV input"}
    if mime_type and not any(token in mime_type.lower() for token in ["audio", "mpeg", "mp3", "wav", "wave", "x-wav", "octet-stream"]):
        return {"ok": False, "error": "unsupported_mime", "message": "Unsupported audio MIME type"}
    size_mb = source.stat().st_size / (1024 * 1024)
    if size_mb > max_upload_mb:
        return {"ok": False, "error": "file_too_large", "message": f"Audio exceeds the {max_upload_mb} MB upload limit"}
    return {"ok": True, "error": "", "message": "", "format": ext, "size_mb": round(size_mb, 3)}


def validate_audio_selection(start: float, end: float, source_duration: float, *, minimum_seconds: float = MIN_AUDIO_SELECTION_SECONDS) -> dict[str, Any]:
    try:
        start_value = float(start)
        end_value = float(end)
        duration_value = float(source_duration)
    except (TypeError, ValueError):
        return {"ok": False, "error": "invalid_selection", "message": "Start, end, and duration must be numeric"}
    if not all(math.isfinite(value) for value in (start_value, end_value, duration_value)):
        return {"ok": False, "error": "invalid_selection", "message": "Start, end, and duration must be finite numbers"}
    if duration_value <= 0:
        return {"ok": False, "error": "invalid_source_duration", "message": "Audio duration is unavailable"}
    if start_value < 0:
        return {"ok": False, "error": "start_before_zero", "message": "Start time cannot be negative"}
    if end_value > duration_value:
        return {"ok": False, "error": "end_beyond_duration", "message": "End time is beyond the source duration"}
    if start_value >= end_value:
        return {"ok": False, "error": "start_after_end", "message": "Start time must be before end time"}
    if end_value - start_value + 1e-9 < minimum_seconds:
        return {"ok": False, "error": "selection_too_short", "message": f"Selection must be at least {minimum_seconds:.1f} second"}
    return {"ok": True, "error": "", "message": "", "selection_duration": round(end_value - start_value, 3)}


def effective_cut_mode(source_path: str | Path, cut_mode: str, fade_in: float = 0.0, fade_out: float = 0.0) -> tuple[str, list[str]]:
    warnings: list[str] = []
    mode = cut_mode if cut_mode in AUDIO_EDITOR_CUT_MODES else "Lossless Quick Cut"
    if fade_in > 0 or fade_out > 0:
        mode = "Precise Cut"
        warnings.append("Fade enabled: re-encoding required.")
    return mode, warnings


def resolve_audio_fades(duration: float, fade_in: float = 0.0, fade_out: float = 0.0) -> tuple[float, float]:
    """Clamp requested fades to the selected range without changing its bounds."""
    selected_duration = max(0.0, float(duration or 0.0))
    requested_in = max(0.0, float(fade_in or 0.0))
    requested_out = max(0.0, float(fade_out or 0.0))
    if selected_duration <= 0:
        return 0.0, 0.0
    if requested_in and requested_out:
        maximum = selected_duration / 2.0
        return min(requested_in, maximum), min(requested_out, maximum)
    return min(requested_in, selected_duration), min(requested_out, selected_duration)


def build_audio_preview_cache_key(
    source_audio_path: str | Path,
    *,
    start_time: float,
    end_time: float,
    fade_in: float = 0.0,
    fade_out: float = 0.0,
    output_format: str = "mp3",
    caller_key: str = "",
) -> str:
    """Build a source-aware preview identity so stale ranges cannot be reused."""
    source = Path(source_audio_path)
    try:
        stat = source.stat()
        source_identity = f"{source.resolve()}|{stat.st_size}|{stat.st_mtime_ns}"
    except OSError:
        source_identity = str(source.resolve())
    payload = "|".join(
        [
            SELECTION_PREVIEW_PROCESSING_VERSION,
            source_identity,
            f"{float(start_time):.3f}",
            f"{float(end_time):.3f}",
            f"{float(fade_in):.3f}",
            f"{float(fade_out):.3f}",
            str(output_format or "mp3").lower(),
            str(caller_key or ""),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8", errors="replace")).hexdigest()


def _prune_selection_preview_cache(preview_dir: Path, *, keep: Path | None = None, limit: int = SELECTION_PREVIEW_CACHE_LIMIT) -> None:
    """Bound generated preview artifacts while leaving user exports untouched."""
    try:
        candidates = sorted(
            (path for path in preview_dir.glob("selection_*.mp3") if path.is_file() and path != keep),
            key=lambda path: path.stat().st_mtime_ns,
            reverse=True,
        )
        for stale in candidates[max(0, int(limit) - (1 if keep else 0)) :]:
            stale.unlink(missing_ok=True)
    except OSError:
        return


def build_audio_cut_command(
    ffmpeg: str,
    source_path: str | Path,
    output_path: str | Path,
    *,
    start_time: float,
    end_time: float,
    cut_mode: str,
    fade_in: float = 0.0,
    fade_out: float = 0.0,
    sample_rate: int = 0,
    channels: int = 2,
    output_format: str = "mp3",
) -> list[str]:
    duration = max(0.0, float(end_time) - float(start_time))
    source = str(source_path)
    output = str(output_path)
    mode, _warnings = effective_cut_mode(source_path, cut_mode, fade_in, fade_out)
    export_format = str(output_format or "mp3").lower()
    if mode == "Lossless Quick Cut":
        base = [ffmpeg, "-y", "-ss", f"{float(start_time):.3f}", "-i", source, "-t", f"{duration:.3f}", "-map", "0:a:0", "-map_metadata", "0"]
    else:
        base = [ffmpeg, "-y", "-i", source, "-map", "0:a:0", "-map_metadata", "0"]
    resolved_fade_in, resolved_fade_out = resolve_audio_fades(duration, fade_in, fade_out)
    smoothing = CUT_BOUNDARY_SMOOTHING_SECONDS if mode == "Precise Cut" and resolved_fade_in <= 0 and resolved_fade_out <= 0 else 0.0
    if export_format == "wav":
        if mode == "Lossless Quick Cut" and resolved_fade_in <= 0 and resolved_fade_out <= 0:
            return [*base, "-c:a", "pcm_s24le", output]
        args = [*base, "-c:a", "pcm_s24le"]
        filters: list[str] = [f"atrim=start={float(start_time):.3f}:duration={duration:.3f}", "asetpts=PTS-STARTPTS"]
        if resolved_fade_in > 0:
            filters.append(f"afade=t=in:st=0:d={resolved_fade_in:.3f}")
        if resolved_fade_out > 0:
            fade_start = max(0.0, duration - resolved_fade_out)
            filters.append(f"afade=t=out:st={fade_start:.3f}:d={resolved_fade_out:.3f}")
        if smoothing:
            filters.extend(
                [
                    f"afade=t=in:st=0:d={smoothing:.3f}",
                    f"afade=t=out:st={max(0.0, duration - smoothing):.3f}:d={smoothing:.3f}",
                ]
            )
        args += ["-af", ",".join(filters)]
        if sample_rate in {32000, 44100, 48000}:
            args += ["-ar", str(sample_rate)]
        if channels:
            args += ["-ac", str(max(1, min(2, int(channels))))]
        return [*args, output]
    if mode == "Lossless Quick Cut" and str(source_path).lower().endswith(".mp3"):
        return [*base, "-c:a", "copy", output]
    args = [*base, "-c:a", "libmp3lame", "-b:a", "320k", "-minrate", "320k", "-maxrate", "320k"]
    if channels and int(channels) != 1:
        args += ["-ac", "2"]
    if sample_rate in {32000, 44100, 48000}:
        args += ["-ar", str(sample_rate)]
    filters: list[str] = [f"atrim=start={float(start_time):.3f}:duration={duration:.3f}", "asetpts=PTS-STARTPTS"]
    if resolved_fade_in > 0:
        filters.append(f"afade=t=in:st=0:d={resolved_fade_in:.3f}")
    if resolved_fade_out > 0:
        fade_start = max(0.0, duration - resolved_fade_out)
        filters.append(f"afade=t=out:st={fade_start:.3f}:d={resolved_fade_out:.3f}")
    if smoothing:
        filters.extend(
            [
                f"afade=t=in:st=0:d={smoothing:.3f}",
                f"afade=t=out:st={max(0.0, duration - smoothing):.3f}:d={smoothing:.3f}",
            ]
        )
    args += ["-af", ",".join(filters)]
    return [*args, output]


def create_audio_selection_preview(
    source_audio_path: str | Path,
    *,
    start_time: float,
    end_time: float,
    cache_key: str,
    fade_in: float = 0.0,
    fade_out: float = 0.0,
    ffmpeg_path: str = "",
) -> dict[str, Any]:
    """Create a cached MP3 preview using the same cut/fade command as export."""
    source = Path(source_audio_path)
    ffmpeg = ffmpeg_path or find_ffmpeg()
    if not source.is_file():
        return {"ok": False, "error": "missing_audio", "message": "Audio file missing"}
    if not ffmpeg:
        return {"ok": False, "error": "missing_ffmpeg", "message": "FFmpeg not found"}
    probe = probe_media(source, ffmpeg_path=ffmpeg)
    if not probe.get("ok") or not probe.get("has_audio"):
        return {"ok": False, "error": "invalid_audio", "message": "Invalid or corrupt audio file"}
    selection = validate_audio_selection(start_time, end_time, float(probe.get("duration") or 0))
    if not selection.get("ok"):
        return {"ok": False, "error": selection.get("error", "invalid_selection"), "message": selection.get("message", "Invalid selection")}

    preview_dir = ROOT / "exports" / "audio_editor" / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    resolved_cache_key = build_audio_preview_cache_key(
        source,
        start_time=start_time,
        end_time=end_time,
        fade_in=fade_in,
        fade_out=fade_out,
        output_format="mp3",
        caller_key=cache_key,
    )
    digest = resolved_cache_key[:20]
    preview_path = preview_dir / f"selection_{digest}.mp3"
    if preview_path.is_file() and preview_path.stat().st_size > 0:
        _prune_selection_preview_cache(preview_dir, keep=preview_path)
        return {"ok": True, "path": str(preview_path), "cache_status": "hit", "cache_key": resolved_cache_key, "command": []}

    command = build_audio_cut_command(
        ffmpeg,
        source,
        preview_path,
        start_time=start_time,
        end_time=end_time,
        cut_mode="Precise Cut",
        fade_in=fade_in,
        fade_out=fade_out,
        sample_rate=int(probe.get("sample_rate") or 0),
        channels=int(probe.get("channels") or 2),
        output_format="mp3",
    )
    result = _run(command, timeout=180)
    if not result.get("ok") or not preview_path.is_file() or preview_path.stat().st_size <= 0:
        preview_path.unlink(missing_ok=True)
        return {
            "ok": False,
            "error": "preview_failed",
            "message": str(result.get("output") or "Selection preview failed")[:600],
            "command": command,
        }
    _prune_selection_preview_cache(preview_dir, keep=preview_path)
    return {"ok": True, "path": str(preview_path), "cache_status": "miss", "cache_key": resolved_cache_key, "command": command}


def _run(args: list[str], timeout: int = 180) -> dict[str, Any]:
    try:
        proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return {"ok": proc.returncode == 0, "returncode": proc.returncode, "output": proc.stdout or "", "command": args}
    except subprocess.TimeoutExpired as exc:
        return {"ok": False, "returncode": -1, "output": f"timeout: {exc}", "command": args}
    except FileNotFoundError as exc:
        return {"ok": False, "returncode": -1, "output": f"missing_ffmpeg: {exc}", "command": args}
    except Exception as exc:
        return {"ok": False, "returncode": -1, "output": str(exc), "command": args}


def _decode_pcm_mono(source_audio_path: str | Path, *, ffmpeg_path: str = "", sample_rate: int = 8000, max_duration: float = 480.0, timeout: int = 120) -> dict[str, Any]:
    ffmpeg = ffmpeg_path or find_ffmpeg()
    if not ffmpeg:
        return {"ok": False, "error": "missing_ffmpeg", "message": "FFmpeg not found"}
    source = Path(source_audio_path)
    args = [ffmpeg, "-v", "error", "-i", str(source), "-map", "0:a:0", "-t", f"{float(max_duration):.3f}", "-ac", "1", "-ar", str(int(sample_rate)), "-f", "s16le", "-"]
    try:
        proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return {"ok": False, "error": "analysis_timeout", "message": f"Audio analysis timed out: {exc}", "command": args}
    except FileNotFoundError as exc:
        return {"ok": False, "error": "missing_ffmpeg", "message": str(exc), "command": args}
    if proc.returncode != 0 or not proc.stdout:
        return {"ok": False, "error": "decode_failed", "message": (proc.stderr or b"Audio decode failed").decode("utf-8", errors="replace")[:600], "command": args}
    samples = array("h")
    samples.frombytes(proc.stdout)
    if not samples:
        return {"ok": False, "error": "empty_audio", "message": "No audio samples decoded", "command": args}
    return {"ok": True, "data": {"samples": samples, "sample_rate": int(sample_rate), "decoded_duration": len(samples) / float(sample_rate), "command": args}, "error": ""}


def _bucket_samples(samples: array, target_points: int) -> list[float]:
    if not samples:
        return []
    point_count = max(1, min(int(target_points), len(samples)))
    bucket_size = max(1, len(samples) // point_count)
    points: list[float] = []
    for idx in range(0, len(samples), bucket_size):
        chunk = samples[idx : idx + bucket_size]
        if not chunk:
            continue
        peak = max(abs(value) for value in chunk) / 32768.0
        points.append(round(min(1.0, peak), 4))
        if len(points) >= point_count:
            break
    return points


def _frame_features(samples: array, sample_rate: int, frame_seconds: float = 0.5) -> list[dict[str, float]]:
    frame_size = max(1, int(sample_rate * frame_seconds))
    frames: list[dict[str, float]] = []
    for start in range(0, len(samples), frame_size):
        chunk = samples[start : start + frame_size]
        if not chunk:
            continue
        sum_sq = sum((value / 32768.0) ** 2 for value in chunk)
        rms = math.sqrt(sum_sq / len(chunk))
        peak_count = sum(1 for value in chunk if abs(value) > 19660)
        clipped_count = sum(1 for value in chunk if abs(value) > 32100)
        frames.append(
            {
                "time": start / float(sample_rate),
                "duration": len(chunk) / float(sample_rate),
                "rms": rms,
                "peak_density": peak_count / float(len(chunk)),
                "clip_density": clipped_count / float(len(chunk)),
                "silent": 1.0 if rms < 0.012 else 0.0,
            }
        )
    return frames


def _nearest_frame(frames: list[dict[str, float]], time_value: float) -> int:
    if not frames:
        return 0
    return min(range(len(frames)), key=lambda idx: abs(frames[idx]["time"] - time_value))


def _frames_between(frames: list[dict[str, float]], start_time: float, end_time: float) -> list[dict[str, float]]:
    return [frame for frame in frames if float(start_time) <= frame["time"] < float(end_time)]


def _average_frame_value(frames: list[dict[str, float]], key: str, default: float = 0.0) -> float:
    if not frames:
        return float(default)
    return sum(float(frame.get(key, 0.0)) for frame in frames) / float(len(frames))


def _global_activity_floor(frames: list[dict[str, float]]) -> float:
    if not frames:
        return 0.012
    avg = _average_frame_value(frames, "rms")
    return max(0.012, avg * 0.42)


def score_start_boundary(frames: list[dict[str, float]], candidate_time: float) -> dict[str, Any]:
    idx = _nearest_frame(frames, candidate_time)
    before = frames[max(0, idx - 4) : idx]
    after = frames[idx : min(len(frames), idx + 4)]
    current = frames[idx] if frames else {"rms": 0, "peak_density": 0, "clip_density": 0}
    before_energy = sum(frame["rms"] for frame in before) / max(1, len(before))
    after_energy = sum(frame["rms"] for frame in after) / max(1, len(after))
    onset = max(0.0, after_energy - before_energy)
    active_penalty = min(35, int(current["rms"] * 130))
    transient_penalty = min(20, int(current["peak_density"] * 180))
    clipping_penalty = min(20, int(current["clip_density"] * 300))
    score = int(58 + onset * 320 + max(0.0, 0.05 - before_energy) * 220 - active_penalty - transient_penalty - clipping_penalty)
    reasons: list[str] = []
    if before_energy < 0.04:
        reasons.append("Low energy immediately before start")
    if onset > 0.025:
        reasons.append("Clear phrase or section entrance after start")
    if current["clip_density"] <= 0.001:
        reasons.append("No clipped leading transient detected")
    if active_penalty > 18:
        reasons.append("Penalty: start may be inside active sustained sound")
    return {"time": round(candidate_time, 3), "score": max(0, min(100, score)), "reasons": reasons, "before_energy": round(before_energy, 4), "after_energy": round(after_energy, 4)}


def analyze_phrase_completion(frames: list[dict[str, float]], candidate_time: float, *, lookahead_seconds: float = PHRASE_COMPLETION_LOOKAHEAD_SECONDS, stable_seconds: float = PHRASE_STABLE_BOUNDARY_SECONDS) -> dict[str, Any]:
    idx = _nearest_frame(frames, candidate_time)
    duration = (frames[-1]["time"] + frames[-1].get("duration", 0.25)) if frames else 0.0
    before = _frames_between(frames, max(0.0, candidate_time - 2.0), candidate_time)
    boundary_zone = _frames_between(frames, candidate_time, min(duration, candidate_time + max(0.25, stable_seconds)))
    after_short = _frames_between(frames, candidate_time, min(duration, candidate_time + 1.5))
    lookahead = _frames_between(frames, candidate_time, min(duration, candidate_time + lookahead_seconds))
    previous = frames[max(0, idx - 1)] if frames else {"rms": 0.0, "peak_density": 0.0}
    current = frames[idx] if frames else {"rms": 0.0, "peak_density": 0.0}
    before_energy = _average_frame_value(before, "rms", _average_frame_value(frames, "rms"))
    boundary_energy = _average_frame_value(boundary_zone, "rms", current.get("rms", 0.0))
    after_energy = _average_frame_value(after_short, "rms", boundary_energy)
    lookahead_energy = _average_frame_value(lookahead, "rms", after_energy)
    onset_activity_after = _average_frame_value(after_short, "peak_density")
    activity_floor = _global_activity_floor(frames)
    active_threshold = max(activity_floor, before_energy * 0.52)

    stable_boundary_duration = 0.0
    for frame in lookahead:
        if frame["rms"] <= active_threshold and frame["peak_density"] <= 0.02:
            stable_boundary_duration += float(frame.get("duration", 0.25))
            if stable_boundary_duration >= stable_seconds:
                break
        elif stable_boundary_duration > 0:
            break

    immediate_reentry_delay: float | None = None
    for frame in lookahead:
        if frame["time"] < candidate_time + 0.2:
            continue
        if frame["rms"] > max(activity_floor * 1.25, before_energy * 0.62) or frame["peak_density"] > 0.035:
            immediate_reentry_delay = round(max(0.0, frame["time"] - candidate_time), 3)
            break

    sustained_activity = 0.0
    if before_energy > activity_floor:
        sustained_activity = min(100.0, max(0.0, (after_energy / max(before_energy, 0.001)) * 100.0))
    spectral_continuity = min(100.0, max(0.0, 100.0 - abs(before_energy - after_energy) / max(before_energy, 0.001) * 100.0)) if before_energy > activity_floor else 0.0
    section_change_score = max(0.0, min(100.0, abs(before_energy - lookahead_energy) / max(before_energy, 0.001) * 80.0 + stable_boundary_duration * 26.0))
    continuation_penalty = 0.0
    continuation_penalty += max(0.0, min(42.0, sustained_activity * 0.42))
    continuation_penalty += max(0.0, min(24.0, onset_activity_after * 520.0))
    if immediate_reentry_delay is not None:
        continuation_penalty += max(0.0, 32.0 - immediate_reentry_delay * 13.0)
    if stable_boundary_duration < stable_seconds:
        continuation_penalty += 22.0
    if spectral_continuity > 70 and after_energy > activity_floor:
        continuation_penalty += 16.0
    continuation_penalty = max(0.0, min(100.0, continuation_penalty))

    warnings: list[str] = []
    if immediate_reentry_delay is not None and immediate_reentry_delay <= 1.5:
        warnings.append("Active music continues immediately after proposed endpoint")
    if stable_boundary_duration < stable_seconds:
        warnings.append("No stable low-energy boundary zone")
    if sustained_activity >= 58:
        warnings.append("Sustained activity crosses the endpoint")
    if onset_activity_after > 0.035:
        warnings.append("Onset activity remains high after endpoint")

    if continuation_penalty <= 34 and stable_boundary_duration >= stable_seconds and (immediate_reentry_delay is None or immediate_reentry_delay > 1.5):
        result = "PASS"
    elif continuation_penalty <= 72:
        result = "EXTEND"
    else:
        result = "REJECT"
    phrase_score = max(0, min(100, int(100 - continuation_penalty + stable_boundary_duration * 10 + section_change_score * 0.12)))
    return {
        "lookahead_duration": round(min(lookahead_seconds, max(0.0, duration - candidate_time)), 3),
        "continuation_penalty": round(continuation_penalty, 2),
        "sustained_activity_score": round(sustained_activity, 2),
        "stable_boundary_duration": round(stable_boundary_duration, 3),
        "section_change_score": round(section_change_score, 2),
        "spectral_continuity_across_end": round(spectral_continuity, 2),
        "onset_activity_after_end": round(onset_activity_after, 4),
        "energy_before_end": round(before_energy, 4),
        "energy_at_end": round(float(current.get("rms", 0.0)), 4),
        "energy_after_end": round(after_energy, 4),
        "immediate_reentry_delay": immediate_reentry_delay,
        "phrase_completion_result": result,
        "phrase_completion_score": phrase_score,
        "warnings": warnings,
    }


def score_end_boundary(frames: list[dict[str, float]], candidate_time: float) -> dict[str, Any]:
    idx = _nearest_frame(frames, candidate_time)
    before = frames[max(0, idx - 5) : idx]
    after = frames[idx : min(len(frames), idx + 5)]
    current = frames[idx] if frames else {"rms": 0, "peak_density": 0, "clip_density": 0}
    before_energy = sum(frame["rms"] for frame in before) / max(1, len(before))
    after_energy = sum(frame["rms"] for frame in after) / max(1, len(after))
    completion = analyze_phrase_completion(frames, candidate_time)
    local_min_bonus = max(0.0, before_energy - current["rms"]) * 220
    decay_bonus = max(0.0, before_energy - after_energy) * 180
    silence_bonus = max(0.0, 0.035 - after_energy) * 180
    stable_bonus = min(24, int(completion["stable_boundary_duration"] * 38))
    section_bonus = int(completion["section_change_score"] * 0.22)
    active_penalty = min(40, int(current["rms"] * 150))
    rise_penalty = min(30, int(max(0.0, after_energy - before_energy) * 220))
    transient_penalty = min(22, int(current["peak_density"] * 220))
    continuation_penalty = int(completion["continuation_penalty"] * 0.58)
    score = int(52 + local_min_bonus + decay_bonus + silence_bonus + stable_bonus + section_bonus - active_penalty - rise_penalty - transient_penalty - continuation_penalty)
    reasons: list[str] = []
    if current["rms"] < before_energy:
        reasons.append("End aligned near local energy minimum")
    if after_energy < before_energy:
        reasons.append("Phrase decay or reduced activity after boundary")
    if after_energy < 0.04:
        reasons.append("Low-energy tail after end")
    if completion["stable_boundary_duration"] >= PHRASE_STABLE_BOUNDARY_SECONDS:
        reasons.append("Stable low-energy boundary zone")
    if completion["immediate_reentry_delay"] is None:
        reasons.append("No immediate continuation detected")
    if completion["phrase_completion_result"] != "PASS":
        reasons.extend(completion.get("warnings", []))
    if active_penalty > 20:
        reasons.append("Penalty: boundary is still musically active")
    if transient_penalty > 10:
        reasons.append("Penalty: strong transient near cut point")
    return {"time": round(candidate_time, 3), "score": max(0, min(100, score)), "reasons": list(dict.fromkeys(reasons)), "before_energy": round(before_energy, 4), "after_energy": round(after_energy, 4), **completion}


def _search_boundary(frames: list[dict[str, float]], rough_time: float, source_duration: float, *, window: float, boundary_type: str) -> dict[str, Any]:
    start = max(0.0, rough_time - window)
    end = min(source_duration, rough_time + window)
    step = 0.1
    best: dict[str, Any] | None = None
    current = start
    while current <= end + 0.001:
        scored = score_start_boundary(frames, current) if boundary_type == "start" else score_end_boundary(frames, current)
        distance_penalty = min(18, int(abs(current - rough_time) * 2.2))
        scored["score"] = max(0, int(scored["score"]) - distance_penalty)
        if best is None or int(scored["score"]) > int(best["score"]):
            best = scored
        current += step
    return best or {"time": round(rough_time, 3), "score": 0, "reasons": ["Boundary search unavailable"]}


def _absolute_phrase_limit(hook_type: str, rough_start: float, rough_end: float, source_duration: float) -> float:
    soft_range = (SMART_HOOK_TYPES.get(hook_type) or SMART_HOOK_TYPES["Best Hook"])["soft_range"]
    preferred_max = float(soft_range[1])
    rough_duration = max(1.0, float(rough_end) - float(rough_start))
    extra = 18.0 if hook_type != "Full Chorus" else 28.0
    absolute_duration = min(max(preferred_max + extra, rough_duration + 18.0), source_duration * 0.72 if source_duration > 90 else source_duration)
    return min(source_duration, float(rough_start) + max(absolute_duration, rough_duration + 4.0))


def expand_end_to_complete_phrase(frames: list[dict[str, float]], proposed_end: float, source_duration: float, *, hook_type: str = "Best Hook", rough_start: float = 0.0, rough_end: float | None = None, step: float = 0.25) -> dict[str, Any]:
    rough_end_value = float(rough_end if rough_end is not None else proposed_end)
    search_limit = _absolute_phrase_limit(hook_type, rough_start, rough_end_value, source_duration)
    first = score_end_boundary(frames, proposed_end)
    if first.get("phrase_completion_result") == "PASS":
        first["expanded"] = False
        first["seconds_extended_to_complete_phrase"] = 0.0
        return first
    best = first
    current = max(float(proposed_end) + step, float(proposed_end))
    while current <= search_limit + 0.001:
        scored = score_end_boundary(frames, current)
        extension_penalty = min(16, int(max(0.0, current - rough_end_value) * 0.45))
        scored["score"] = max(0, int(scored["score"]) - extension_penalty)
        if scored.get("phrase_completion_result") == "PASS":
            scored["expanded"] = True
            scored["seconds_extended_to_complete_phrase"] = round(max(0.0, current - proposed_end), 3)
            scored["reasons"] = list(dict.fromkeys([*scored.get("reasons", []), f"Extended {current - proposed_end:.1f} seconds to complete the musical phrase"]))
            return scored
        if int(scored.get("phrase_completion_score", 0)) > int(best.get("phrase_completion_score", 0)):
            best = scored
        current += step
    best["expanded"] = bool(float(best.get("time", proposed_end)) > float(proposed_end) + 0.001)
    best["seconds_extended_to_complete_phrase"] = round(max(0.0, float(best.get("time", proposed_end)) - proposed_end), 3)
    best["reasons"] = list(dict.fromkeys([*best.get("reasons", []), "No complete phrase found before safety limit"]))
    if best.get("phrase_completion_result") == "PASS":
        return best
    best["phrase_completion_result"] = "REJECT" if float(best.get("continuation_penalty", 100)) > 72 else "EXTEND"
    return best


def smart_hook_suffix(hook_type: str) -> str:
    return str((SMART_HOOK_TYPES.get(hook_type) or {}).get("suffix") or "Hook")


def refine_musical_hook_boundaries(
    source_audio_path: str | Path,
    *,
    rough_start: float,
    rough_end: float,
    hook_type: str = "Best Hook",
    ffmpeg_path: str = "",
    start_window: float = 3.0,
    end_window: float = 6.0,
    max_upload_mb: int = 200,
) -> dict[str, Any]:
    source = Path(source_audio_path)
    validation = validate_audio_editor_input(source, max_upload_mb=max_upload_mb)
    if not validation.get("ok"):
        return {"ok": False, "message": validation.get("message", "Invalid audio"), "error": validation.get("error", "invalid_audio")}
    ffmpeg = ffmpeg_path or find_ffmpeg()
    if not ffmpeg:
        return {"ok": False, "message": "FFmpeg not found", "error": "missing_ffmpeg"}
    probe = probe_media(source, ffmpeg_path=ffmpeg)
    duration = float(probe.get("duration") or 0)
    selection = validate_audio_selection(rough_start, rough_end, duration)
    if not selection.get("ok"):
        return {"ok": False, "message": selection.get("message", "Invalid selection"), "error": selection.get("error", "invalid_selection")}
    decoded = _decode_pcm_mono(source, ffmpeg_path=ffmpeg, max_duration=min(480.0, duration or 480.0))
    if not decoded.get("ok"):
        return decoded
    frames = _frame_features(decoded["data"]["samples"], int(decoded["data"]["sample_rate"]), frame_seconds=0.25)
    start_boundary = _search_boundary(frames, float(rough_start), duration, window=float(start_window), boundary_type="start")
    initial_end_boundary = _search_boundary(frames, float(rough_end), duration, window=float(end_window), boundary_type="end")
    end_boundary = expand_end_to_complete_phrase(frames, float(initial_end_boundary["time"]), duration, hook_type=hook_type, rough_start=float(rough_start), rough_end=float(rough_end))
    refined_start = max(0.0, min(float(start_boundary["time"]), duration))
    refined_end = max(refined_start + 1.0, min(float(end_boundary["time"]), duration))
    if refined_end <= refined_start:
        refined_start = float(rough_start)
        refined_end = float(rough_end)
    actual_duration = refined_end - refined_start
    phrase_score = int(end_boundary.get("phrase_completion_score", 0))
    continuation_penalty = float(end_boundary.get("continuation_penalty", 100))
    confidence_score = int((int(start_boundary["score"]) * 0.28) + (int(end_boundary["score"]) * 0.24) + (phrase_score * 0.36) + (float(end_boundary.get("section_change_score", 0)) * 0.12) - min(28.0, continuation_penalty * 0.22))
    phrase_result = str(end_boundary.get("phrase_completion_result") or "REJECT")
    if phrase_result != "PASS":
        confidence_score = min(confidence_score, 64 if phrase_result == "EXTEND" else 44)
    soft_range = (SMART_HOOK_TYPES.get(hook_type) or SMART_HOOK_TYPES["Best Hook"])["soft_range"]
    range_note = "Actual duration preserved musical boundary instead of forcing exact length."
    if soft_range[0] <= actual_duration <= soft_range[1]:
        range_note = "Actual duration sits within the soft target range."
    reasons = list(dict.fromkeys([*start_boundary.get("reasons", []), *end_boundary.get("reasons", []), range_note]))
    warnings = list(dict.fromkeys(end_boundary.get("warnings", [])))
    if phrase_result == "PASS":
        reasons.append("Complete musical phrase proxy detected")
    elif phrase_result == "EXTEND":
        warnings.append("Ending remains uncertain; manual adjustment recommended")
    else:
        warnings.append("No reliable complete phrase endpoint found")
    boundary_confidence = "High" if confidence_score >= 76 and phrase_result == "PASS" and continuation_penalty <= 34 else "Medium" if confidence_score >= 55 and phrase_result in {"PASS", "EXTEND"} else "Low"
    return {
        "ok": True,
        "data": {
            "source_audio": str(source),
            "hook_type": hook_type,
            "rough_start": round(float(rough_start), 3),
            "rough_end": round(float(rough_end), 3),
            "initial_candidate_start": round(float(rough_start), 3),
            "initial_candidate_end": round(float(rough_end), 3),
            "expanded_start": round(refined_start, 3),
            "expanded_end": round(refined_end, 3),
            "preferred_duration_range": list(soft_range),
            "refined_start": round(refined_start, 3),
            "refined_end": round(refined_end, 3),
            "actual_duration": round(actual_duration, 3),
            "lookahead_duration": end_boundary.get("lookahead_duration", PHRASE_COMPLETION_LOOKAHEAD_SECONDS),
            "continuation_penalty": end_boundary.get("continuation_penalty", 100),
            "sustained_activity_score": end_boundary.get("sustained_activity_score", 0),
            "stable_boundary_duration": end_boundary.get("stable_boundary_duration", 0),
            "section_change_score": end_boundary.get("section_change_score", 0),
            "phrase_completion_result": phrase_result,
            "phrase_completion_score": phrase_score,
            "seconds_extended_to_complete_phrase": end_boundary.get("seconds_extended_to_complete_phrase", 0.0),
            "boundary_confidence": boundary_confidence,
            "boundary_confidence_score": max(0, min(100, confidence_score)),
            "start_boundary_score": int(start_boundary["score"]),
            "end_boundary_score": int(end_boundary["score"]),
            "start_boundary": start_boundary,
            "initial_end_boundary": initial_end_boundary,
            "end_boundary": end_boundary,
            "reasons": reasons,
            "warnings": warnings,
            "user_override_status": "Smart Refined",
        },
        "error": "",
    }


def evaluate_hook_selection_quality(
    source_audio_path: str | Path,
    *,
    start_time: float,
    end_time: float,
    ffmpeg_path: str = "",
    max_upload_mb: int = 200,
) -> dict[str, Any]:
    """Classify a selected hook using existing PCM and boundary diagnostics."""
    source = Path(source_audio_path)
    validation = validate_audio_editor_input(source, max_upload_mb=max_upload_mb)
    if not validation.get("ok"):
        return {"ok": False, "label": "REVIEW", "findings": [validation.get("message", "Invalid audio")], "diagnostics": {}}
    ffmpeg = ffmpeg_path or find_ffmpeg()
    probe = probe_media(source, ffmpeg_path=ffmpeg) if ffmpeg else {"ok": False}
    duration = float(probe.get("duration") or 0.0)
    selection = validate_audio_selection(start_time, end_time, duration)
    if not ffmpeg or not selection.get("ok"):
        return {"ok": False, "label": "REVIEW", "findings": [selection.get("message", "Analysis unavailable")], "diagnostics": {}}
    decoded = _decode_pcm_mono(source, ffmpeg_path=ffmpeg, max_duration=min(480.0, duration or 480.0))
    if not decoded.get("ok"):
        return {"ok": False, "label": "REVIEW", "findings": [decoded.get("message", "Analysis unavailable")], "diagnostics": {}}
    frames = _frame_features(decoded["data"]["samples"], int(decoded["data"]["sample_rate"]), frame_seconds=0.25)
    selected = _frames_between(frames, start_time, end_time)
    if not selected:
        return {"ok": False, "label": "POOR", "findings": ["Selected range contains no measurable audio."], "diagnostics": {}}
    start = score_start_boundary(frames, start_time)
    end = score_end_boundary(frames, end_time)
    global_rms = _average_frame_value(frames, "rms")
    selected_rms = _average_frame_value(selected, "rms")
    silence_ratio = _average_frame_value(selected, "silent")
    clip_density = _average_frame_value(selected, "clip_density")
    energy_variance = sum((frame["rms"] - selected_rms) ** 2 for frame in selected) / len(selected)
    stability = max(0.0, min(1.0, 1.0 - math.sqrt(energy_variance) / max(selected_rms, 0.001)))
    issues: list[str] = []
    severe = 0
    if int(start.get("score", 0)) < 45:
        issues.append("Start may cut into an active phrase or transient.")
        severe += 1
    elif int(start.get("score", 0)) < 62:
        issues.append("Start boundary is usable but worth a quick listen.")
    phrase_result = str(end.get("phrase_completion_result") or "REJECT")
    if phrase_result == "REJECT":
        issues.append("Music appears to continue immediately after the endpoint.")
        severe += 1
    elif phrase_result == "EXTEND":
        issues.append("Ending may need a little more time to complete the phrase.")
    if clip_density > 0.002:
        issues.append("Possible clipping is present inside the selection.")
        severe += 1
    if silence_ratio > 0.35:
        issues.append("Selection contains a large amount of silence.")
        severe += 1
    elif selected_rms < max(0.012, global_rms * 0.55):
        issues.append("Selection is low-energy compared with the full track.")
    if stability < 0.28:
        issues.append("Energy changes sharply across the selected range.")
    if severe >= 2 or len(issues) >= 5:
        label = "POOR"
    elif issues:
        label = "REVIEW"
    else:
        label = "GOOD"
    return {
        "ok": True,
        "label": label,
        "findings": issues[:4] or ["Start, sustained energy, and phrase ending look usable."],
        "diagnostics": {
            "start_boundary_score": start.get("score"),
            "end_boundary_score": end.get("score"),
            "phrase_completion_result": phrase_result,
            "continuation_penalty": end.get("continuation_penalty"),
            "immediate_reentry_delay": end.get("immediate_reentry_delay"),
            "selected_rms": round(selected_rms, 5),
            "global_rms": round(global_rms, 5),
            "silence_ratio": round(silence_ratio, 4),
            "clip_density": round(clip_density, 6),
            "energy_stability": round(stability, 4),
        },
    }


def generate_waveform_data(
    source_audio_path: str | Path,
    output_json_path: str | Path,
    *,
    ffmpeg_path: str = "",
    target_points: int = WAVEFORM_TARGET_POINTS,
    max_analysis_duration: float = 480.0,
    source_signature: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source = Path(source_audio_path)
    output_json = Path(output_json_path)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    signature = _source_signature(source, trusted_identity=source_signature)
    if output_json.is_file():
        try:
            cached = json.loads(output_json.read_text(encoding="utf-8"))
            if cached.get("source_signature") == signature and 1 <= len(cached.get("points", [])) <= 3000:
                cached["cache_status"] = "hit"
                return {"ok": True, "data": cached, "error": ""}
        except Exception:
            pass
    decoded = _decode_pcm_mono(source, ffmpeg_path=ffmpeg_path, max_duration=max_analysis_duration)
    if not decoded.get("ok"):
        return decoded
    data = decoded["data"]
    points = _bucket_samples(data["samples"], target_points)
    probe = probe_media(source, ffmpeg_path=ffmpeg_path or find_ffmpeg())
    duration = float(probe.get("duration") or data.get("decoded_duration") or 0)
    payload = {
        "source_signature": signature,
        "duration": round(duration, 3),
        "decoded_duration": round(float(data.get("decoded_duration") or 0), 3),
        "points": points,
        "point_count": len(points),
        "method": "ffmpeg pcm s16le mono peak buckets",
        "target_points": int(target_points),
        "max_analysis_duration": float(max_analysis_duration),
        "cache_status": "miss",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "data": payload, "error": ""}


def render_waveform_svg(waveform: dict[str, Any], output_svg_path: str | Path, *, start_time: float = 0.0, end_time: float = 0.0, width: int = 1200, height: int = 220) -> dict[str, Any]:
    points = [float(value) for value in waveform.get("points", []) if isinstance(value, (int, float))]
    duration = float(waveform.get("duration") or 0)
    if not points or duration <= 0:
        return {"ok": False, "error": "missing_waveform", "message": "Waveform points unavailable"}
    output = Path(output_svg_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    baseline = height / 2
    usable_h = height * 0.42
    bar_w = max(1.0, width / max(1, len(points)))
    selected_x = max(0.0, min(width, (float(start_time) / duration) * width))
    selected_w = max(0.0, min(width - selected_x, ((float(end_time) - float(start_time)) / duration) * width))
    bars = []
    for idx, amp in enumerate(points):
        x = idx * bar_w
        h = max(1.0, min(usable_h, amp * usable_h))
        bars.append(f'<rect x="{x:.2f}" y="{baseline - h:.2f}" width="{max(1.0, bar_w * 0.82):.2f}" height="{h * 2:.2f}" rx="1" fill="#5BBEFF" opacity="0.78"/>')
    labels = []
    tick_step = 15.0 if duration <= 180 else 30.0
    tick = 0.0
    while tick <= duration + 0.01:
        x = (tick / duration) * width
        labels.append(f'<line x1="{x:.1f}" y1="{height - 28}" x2="{x:.1f}" y2="{height - 18}" stroke="#8da2b8" stroke-width="1"/>')
        labels.append(f'<text x="{x + 3:.1f}" y="{height - 5}" fill="#b7c5d5" font-size="12" font-family="Arial">{format_timecode(tick)[:5]}</text>')
        tick += tick_step
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="#0f172a"/>
<rect x="{selected_x:.2f}" y="8" width="{selected_w:.2f}" height="{height - 44}" fill="#22c55e" opacity="0.22"/>
{''.join(bars)}
<line x1="{selected_x:.2f}" y1="8" x2="{selected_x:.2f}" y2="{height - 36}" stroke="#f8fafc" stroke-width="2"/>
<line x1="{selected_x + selected_w:.2f}" y1="8" x2="{selected_x + selected_w:.2f}" y2="{height - 36}" stroke="#f8fafc" stroke-width="2"/>
{''.join(labels)}
</svg>'''
    output.write_text(svg, encoding="utf-8")
    return {"ok": True, "data": {"waveform_svg": str(output)}, "error": ""}


def generate_waveform_image(source_audio_path: str | Path, output_path: str | Path, *, ffmpeg_path: str = "") -> dict[str, Any]:
    ffmpeg = ffmpeg_path or find_ffmpeg()
    if not ffmpeg:
        return {"ok": False, "error": "missing_ffmpeg", "message": "FFmpeg not found"}
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    result = _run([ffmpeg, "-y", "-i", str(source_audio_path), "-filter_complex", "aformat=channel_layouts=mono,showwavespic=s=1200x260:colors=5BBEFF", "-frames:v", "1", str(output)], timeout=60)
    if not result.get("ok") or not output.is_file():
        return {"ok": False, "error": "waveform_failed", "message": (result.get("output") or "Waveform generation failed")[:500], "command": result.get("command", [])}
    return {"ok": True, "data": {"waveform_path": str(output), "command": result.get("command", [])}, "error": ""}


def _window_score(frames: list[dict[str, float]], start: float, duration: float, source_duration: float, global_energy: float) -> dict[str, Any]:
    end = start + duration
    selected = [frame for frame in frames if start <= frame["time"] < end]
    if not selected:
        return {"score": 0, "reasons": ["No measurable activity"], "component_scores": {}, "rejection_reasons": ["empty_window"]}
    avg_rms = sum(frame["rms"] for frame in selected) / len(selected)
    peak_density = sum(frame["peak_density"] for frame in selected) / len(selected)
    silence_ratio = sum(frame["silent"] for frame in selected) / len(selected)
    clip_density = sum(frame["clip_density"] for frame in selected) / len(selected)
    variance = sum((frame["rms"] - avg_rms) ** 2 for frame in selected) / len(selected)
    stability = 1.0 - min(1.0, math.sqrt(variance) / max(avg_rms, 0.001))
    before = [frame["rms"] for frame in frames if max(0.0, start - duration) <= frame["time"] < start]
    before_avg = sum(before) / len(before) if before else global_energy
    contrast = max(0.0, avg_rms - before_avg) / max(global_energy, 0.001)
    energy_score = min(100, int((avg_rms / max(global_energy * 1.25, 0.025)) * 72 + min(0.18, peak_density) * 155))
    activity_score = max(0, min(100, int((1.0 - silence_ratio) * 100)))
    contrast_score = max(0, min(100, int(contrast * 80)))
    stability_score = max(0, min(100, int(stability * 100)))
    intro_penalty = 18 if source_duration > 25 and start < 5 else 0
    outro_penalty = 16 if source_duration > 45 and end > source_duration * 0.92 else 0
    clipping_penalty = min(25, int(clip_density * 300))
    score = int(energy_score * 0.34 + activity_score * 0.25 + contrast_score * 0.18 + stability_score * 0.18 + (100 if duration >= 30 else 88) * 0.05)
    score = max(0, min(100, score - intro_penalty - outro_penalty - clipping_penalty))
    reasons: list[str] = []
    rejection_reasons: list[str] = []
    if energy_score >= 65:
        reasons.append("Sustained high-energy section")
    if contrast_score >= 35:
        reasons.append("Clear energy rise into the selected region")
    if activity_score >= 82:
        reasons.append("Low silence ratio")
    if stability_score >= 62:
        reasons.append("Stable audio activity across the window")
    if intro_penalty:
        rejection_reasons.append("intro_penalty")
    if outro_penalty:
        rejection_reasons.append("outro_penalty")
    if clipping_penalty:
        rejection_reasons.append("possible_clipping_penalty")
    if not reasons:
        reasons.append("Moderate audio activity; manual review recommended")
    return {
        "score": score,
        "energy_score": energy_score,
        "vocal_activity_score": activity_score,
        "component_scores": {
            "energy_strength": energy_score,
            "sustained_activity": activity_score,
            "energy_contrast": contrast_score,
            "section_stability": stability_score,
            "silence_ratio": round(silence_ratio, 3),
            "clipping_penalty": clipping_penalty,
            "intro_penalty": intro_penalty,
            "outro_penalty": outro_penalty,
        },
        "reasons": reasons,
        "rejection_reasons": rejection_reasons,
    }


def _overlap_ratio(a: dict[str, Any], b: dict[str, Any]) -> float:
    start = max(float(a["start_time"]), float(b["start_time"]))
    end = min(float(a["end_time"]), float(b["end_time"]))
    overlap = max(0.0, end - start)
    shorter = max(0.001, min(float(a["duration"]), float(b["duration"])))
    return overlap / shorter


def analyze_hook_candidates(
    source_audio_path: str | Path,
    *,
    output_dir: str | Path = "",
    ffmpeg_path: str = "",
    window_sizes: list[float] | None = None,
    step_seconds: float = HOOK_ANALYSIS_STEP_SECONDS,
    max_analysis_duration: float = 480.0,
) -> dict[str, Any]:
    source = Path(source_audio_path)
    validation = validate_audio_editor_input(source)
    if not validation.get("ok"):
        return {"ok": False, "message": validation.get("message", "Invalid audio"), "error": validation.get("error", "invalid_audio")}
    ffmpeg = ffmpeg_path or find_ffmpeg()
    if not ffmpeg:
        return {"ok": False, "message": "FFmpeg not found", "error": "missing_ffmpeg"}
    probe = probe_media(source, ffmpeg_path=ffmpeg)
    if not probe.get("ok") or not probe.get("has_audio"):
        return {"ok": False, "message": "Invalid or corrupt MP3", "error": "invalid_audio"}
    source_duration = float(probe.get("duration") or 0)
    decoded = _decode_pcm_mono(source, ffmpeg_path=ffmpeg, max_duration=min(max_analysis_duration, source_duration or max_analysis_duration))
    if not decoded.get("ok"):
        return decoded
    pcm = decoded["data"]
    frames = _frame_features(pcm["samples"], int(pcm["sample_rate"]))
    if not frames:
        return {"ok": False, "message": "Hook analysis found no usable audio frames", "error": "hook_analysis_failed"}
    global_energy = sum(frame["rms"] for frame in frames) / len(frames)
    candidates: list[dict[str, Any]] = []
    durations = window_sizes or HOOK_ANALYSIS_DURATIONS
    for window in durations:
        if source_duration < 10:
            continue
        duration = min(float(window), source_duration)
        if duration < 10:
            continue
        start_min = 0.0 if source_duration <= 20 else 5.0
        latest_start = max(start_min, min(source_duration - duration, float(pcm["decoded_duration"]) - duration))
        start = start_min
        while start <= latest_start + 0.001:
            scored = _window_score(frames, start, duration, source_duration, global_energy)
            candidates.append(
                {
                    "rank": 0,
                    "start_time": round(start, 3),
                    "end_time": round(start + duration, 3),
                    "duration": round(duration, 3),
                    "confidence_score": int(scored["score"]),
                    "energy_score": int(scored.get("energy_score", 0)),
                    "vocal_activity_score": int(scored.get("vocal_activity_score", 0)),
                    "reason_summary": "; ".join(scored["reasons"]),
                    "component_scores": scored["component_scores"],
                    "rejection_reasons": scored["rejection_reasons"],
                }
            )
            start += max(1.0, float(step_seconds))
    ranked = sorted(candidates, key=lambda item: (item["confidence_score"], item["duration"]), reverse=True)
    rough_deduped: list[dict[str, Any]] = []
    for candidate in ranked:
        if candidate["confidence_score"] < 20:
            continue
        if any(_overlap_ratio(candidate, existing) > 0.45 for existing in rough_deduped):
            continue
        rough_deduped.append(candidate)
        if len(rough_deduped) >= 12:
            break
    refined_candidates: list[dict[str, Any]] = []
    for candidate in rough_deduped:
        hook_type = "Best Hook" if float(candidate.get("duration", 0)) >= 25 else "Short Hook"
        refined = refine_musical_hook_boundaries(
            source,
            rough_start=float(candidate["start_time"]),
            rough_end=float(candidate["end_time"]),
            hook_type=hook_type,
            ffmpeg_path=ffmpeg,
        )
        candidate["hook_type"] = hook_type
        if refined.get("ok"):
            rdata = refined["data"]
            candidate["rough_start"] = candidate["start_time"]
            candidate["rough_end"] = candidate["end_time"]
            candidate["refined_start"] = rdata["refined_start"]
            candidate["refined_end"] = rdata["refined_end"]
            candidate["actual_duration"] = rdata["actual_duration"]
            candidate["boundary_confidence"] = rdata["boundary_confidence"]
            candidate["boundary_confidence_score"] = rdata["boundary_confidence_score"]
            candidate["start_boundary_score"] = rdata["start_boundary_score"]
            candidate["end_boundary_score"] = rdata["end_boundary_score"]
            candidate["boundary_reasons"] = rdata["reasons"]
            candidate["boundary_warnings"] = rdata.get("warnings", [])
            candidate["preferred_duration_range"] = rdata.get("preferred_duration_range", [])
            candidate["lookahead_duration"] = rdata.get("lookahead_duration", PHRASE_COMPLETION_LOOKAHEAD_SECONDS)
            candidate["continuation_penalty"] = rdata.get("continuation_penalty", 100)
            candidate["sustained_activity_score"] = rdata.get("sustained_activity_score", 0)
            candidate["stable_boundary_duration"] = rdata.get("stable_boundary_duration", 0)
            candidate["section_change_score"] = rdata.get("section_change_score", 0)
            candidate["phrase_completion_result"] = rdata.get("phrase_completion_result", "REJECT")
            candidate["phrase_completion_score"] = rdata.get("phrase_completion_score", 0)
            candidate["seconds_extended_to_complete_phrase"] = rdata.get("seconds_extended_to_complete_phrase", 0.0)
            candidate["confidence_score"] = int(rdata.get("boundary_confidence_score", candidate["confidence_score"]))
            candidate["start_time"] = rdata["refined_start"]
            candidate["end_time"] = rdata["refined_end"]
            candidate["duration"] = rdata["actual_duration"]
        if candidate.get("phrase_completion_result") == "REJECT":
            continue
        refined_candidates.append(candidate)
    refined_ranked = sorted(
        refined_candidates,
        key=lambda item: (
            1 if item.get("phrase_completion_result") == "PASS" else 0,
            int(item.get("phrase_completion_score", 0)),
            int(item.get("start_boundary_score", 0)),
            int(item.get("end_boundary_score", 0)),
            int(item.get("energy_score", 0)),
            -abs(float(item.get("actual_duration", item.get("duration", 0))) - 37.0),
        ),
        reverse=True,
    )
    deduped: list[dict[str, Any]] = []
    for candidate in refined_ranked:
        if any(_overlap_ratio(candidate, existing) > 0.45 for existing in deduped):
            continue
        candidate["rank"] = len(deduped) + 1
        deduped.append(candidate)
        if len(deduped) >= 3:
            break
    low_confidence = not deduped or max(item["confidence_score"] for item in deduped) < 55 or not any(item.get("phrase_completion_result") == "PASS" for item in deduped)
    report = {
        "ok": True,
        "source_filename": source.name,
        "source_duration": round(source_duration, 3),
        "analysis_method": "local ffmpeg PCM RMS/peak/silence sliding windows with musical phrase completion proxy",
        "window_sizes": durations,
        "step_seconds": step_seconds,
        "candidate_count": len(deduped),
        "candidates": deduped,
        "low_confidence": low_confidence,
        "message": "No strong hook candidate detected. Manual selection is recommended." if low_confidence else "Hook candidates detected from audio activity.",
        "analysis_timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    if output_dir:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        report_path = out_dir / "hook_analysis.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        report["report_path"] = str(report_path)
    return {"ok": True, "data": report, "error": ""}


def _report_text(report: dict[str, Any]) -> str:
    rows = [
        "VELAFLOW AUDIO EDIT REPORT",
        "",
        f"Original filename: {report.get('original_filename', '')}",
        f"Input duration: {report.get('input_duration', 0)}",
        f"Input format: {report.get('input_format', '')}",
        f"Source format: {report.get('source_format', report.get('input_format', ''))}",
        f"Input codec: {report.get('input_codec', '')}",
        f"Input bitrate: {report.get('input_bitrate', '')}",
        f"Input sample rate: {report.get('input_sample_rate', '')}",
        f"Selected start: {report.get('selected_start', '')}",
        f"Selected end: {report.get('selected_end', '')}",
        f"Selection duration: {report.get('selection_duration', '')}",
        f"Actual output duration: {report.get('actual_output_duration', '')}",
        f"Duration difference (ms): {report.get('duration_difference_ms', '')}",
        f"Cut mode: {report.get('cut_mode', '')}",
        f"Fade In: {report.get('fade_in', '')}",
        f"Fade Out: {report.get('fade_out', '')}",
        f"Effective Fade In: {report.get('effective_fade_in', report.get('fade_in', ''))}",
        f"Effective Fade Out: {report.get('effective_fade_out', report.get('fade_out', ''))}",
        f"Boundary smoothing (ms): {report.get('boundary_smoothing_ms', 0)}",
        f"Output filename: {report.get('output_filename', '')}",
        f"Export format: {report.get('export_format', '')}",
        f"Preview format: {report.get('preview_format', '')}",
        f"Output codec: {report.get('output_codec', '')}",
        f"Output bitrate: {report.get('output_bitrate', '')}",
        f"Re-encoded: {'Yes' if report.get('reencoded') else 'No'}",
        f"Processing date and time: {report.get('processing_date_time', '')}",
        "Warnings: " + (", ".join(report.get("warnings", [])) if report.get("warnings") else "None"),
    ]
    waveform = report.get("waveform") or {}
    if waveform:
        rows += [
            "",
            "Waveform:",
            f"- Points: {waveform.get('point_count', '')}",
            f"- Method: {waveform.get('method', '')}",
            f"- Cache status: {waveform.get('cache_status', '')}",
        ]
    hook_analysis = report.get("smart_hook_finder") or {}
    if hook_analysis:
        rows += [
            "",
            "Smart Hook Finder:",
            f"- Method: {hook_analysis.get('analysis_method', '')}",
            f"- Window sizes: {hook_analysis.get('window_sizes', '')}",
            f"- Candidate count: {hook_analysis.get('candidate_count', '')}",
        ]
    smart_hook = report.get("smart_musical_hook") or {}
    if smart_hook:
        rows += [
            "",
            "Smart Musical Hook:",
            f"- Hook type: {smart_hook.get('hook_type', '')}",
            f"- Rough start: {smart_hook.get('rough_start', '')}",
            f"- Rough end: {smart_hook.get('rough_end', '')}",
            f"- Refined start: {smart_hook.get('refined_start', '')}",
            f"- Refined end: {smart_hook.get('refined_end', '')}",
            f"- Preferred range: {smart_hook.get('preferred_duration_range', '')}",
            f"- Actual duration: {smart_hook.get('actual_duration', '')}",
            f"- Lookahead duration: {smart_hook.get('lookahead_duration', '')}",
            f"- Phrase completion: {smart_hook.get('phrase_completion_result', '')}",
            f"- Continuation penalty: {smart_hook.get('continuation_penalty', '')}",
            f"- Sustained activity score: {smart_hook.get('sustained_activity_score', '')}",
            f"- Stable boundary duration: {smart_hook.get('stable_boundary_duration', '')}",
            f"- Section change score: {smart_hook.get('section_change_score', '')}",
            f"- Seconds extended to complete phrase: {smart_hook.get('seconds_extended_to_complete_phrase', '')}",
            f"- Boundary confidence: {smart_hook.get('boundary_confidence', '')}",
            f"- Start boundary score: {smart_hook.get('start_boundary_score', '')}",
            f"- End boundary score: {smart_hook.get('end_boundary_score', '')}",
            f"- User override status: {smart_hook.get('user_override_status', '')}",
            f"- Export mode: {smart_hook.get('export_mode', report.get('cut_mode', ''))}",
            f"- Fade settings: {smart_hook.get('fade_settings', {'fade_in': report.get('fade_in', 0), 'fade_out': report.get('fade_out', 0)})}",
            "Reasons:",
            *[f"- {reason}" for reason in smart_hook.get("reasons", [])],
        ]
        if smart_hook.get("warnings"):
            rows += [
                "Phrase warnings:",
                *[f"- {warning}" for warning in smart_hook.get("warnings", [])],
            ]
    return "\n".join(rows)


def _batch_report_text(report: dict[str, Any]) -> str:
    rows = [
        "VELAFLOW AUDIO EDIT BATCH REPORT",
        "",
        f"Original filename: {report.get('original_filename', '')}",
        f"Selected start: {report.get('selected_start', '')}",
        f"Selected durations: {', '.join(str(item) for item in report.get('selected_durations', []))}",
        f"Cut mode: {report.get('cut_mode', '')}",
        f"Fade In: {report.get('fade_in', '')}",
        f"Fade Out: {report.get('fade_out', '')}",
        f"Re-encoded: {'Yes' if report.get('reencoded') else 'No'}",
        f"Output bitrate: {report.get('output_bitrate', '')}",
        "",
        "Generated files:",
    ]
    for item in report.get("generated_files", []):
        rows.append(f"- {item.get('filename')} ({item.get('duration')} sec)")
    rows.append("")
    rows.append("Skipped files:")
    skipped = report.get("skipped_files", [])
    if skipped:
        for item in skipped:
            rows.append(f"- {item.get('duration')} sec: {item.get('reason')}")
    else:
        rows.append("- None")
    rows.append("")
    rows.append("Warnings: " + (", ".join(report.get("warnings", [])) if report.get("warnings") else "None"))
    waveform = report.get("waveform") or {}
    if waveform:
        rows += [
            "",
            "Waveform:",
            f"- Points: {waveform.get('point_count', '')}",
            f"- Method: {waveform.get('method', '')}",
            f"- Cache status: {waveform.get('cache_status', '')}",
        ]
    return "\n".join(rows)


def export_audio_selection(
    source_audio_path: str | Path,
    *,
    start_time: float,
    end_time: float,
    project_name: str = "audio_editor",
    output_name: str = "",
    cut_mode: str = "Lossless Quick Cut",
    fade_in: float = 0.0,
    fade_out: float = 0.0,
    ffmpeg_path: str = "",
    max_upload_mb: int = 200,
    preview: bool = False,
    waveform_summary: dict[str, Any] | None = None,
    hook_analysis_summary: dict[str, Any] | None = None,
    smart_hook_data: dict[str, Any] | None = None,
    output_suffix: str = "Hook",
    output_format: str = "mp3",
) -> dict[str, Any]:
    source = Path(source_audio_path)
    ffmpeg = ffmpeg_path or find_ffmpeg()
    validation = validate_audio_editor_input(source, max_upload_mb=max_upload_mb)
    if not validation.get("ok"):
        return {"ok": False, "message": validation.get("message", "Invalid audio"), "data": {"validation": validation}, "error": validation.get("error", "invalid_audio")}
    if not ffmpeg:
        return {
            "ok": False,
            "message": "FFmpeg not found. Install on Debian with: sudo apt-get update && sudo apt-get install -y ffmpeg",
            "data": {"setup_hint": "sudo apt-get update && sudo apt-get install -y ffmpeg"},
            "error": "missing_ffmpeg",
        }
    probe = probe_media(source, ffmpeg_path=ffmpeg)
    if not probe.get("ok") or not probe.get("has_audio"):
        return {"ok": False, "message": "Invalid or corrupt audio file", "data": {"source_probe": probe}, "error": "invalid_audio"}
    selection = validate_audio_selection(start_time, end_time, float(probe.get("duration") or 0))
    if not selection.get("ok"):
        return {"ok": False, "message": selection.get("message", "Invalid selection"), "data": {"selection": selection}, "error": selection.get("error", "invalid_selection")}
    project_id = build_audio_editor_project_id(project_name or source.stem)
    base_dir = ROOT / "exports" / "audio_editor" / project_id
    original_dir = base_dir / "original"
    output_dir = base_dir / "output"
    reports_dir = base_dir / "reports"
    original_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    source_copy = original_dir / f"source.{source.suffix.lower().lstrip('.')}"
    shutil.copy2(source, source_copy)
    safe_stem = export_name_base(output_name, source.name)
    export_format = "wav" if str(output_format or "").lower() == "wav" else "mp3"
    output_path = ensure_unique_path(output_dir / build_asset_export_filename(output_name, source.name, output_suffix or "Hook", export_format))
    mode, warnings = effective_cut_mode(source, cut_mode, fade_in, fade_out)
    if export_format == "mp3" and source.suffix.lower() == ".wav" and mode == "Lossless Quick Cut":
        mode = "Precise Cut"
        warnings.append("WAV to MP3 export requires encoding to 320 kbps MP3.")
    command = build_audio_cut_command(
        ffmpeg,
        source,
        output_path,
        start_time=start_time,
        end_time=end_time,
        cut_mode=mode,
        fade_in=fade_in,
        fade_out=fade_out,
        sample_rate=int(probe.get("sample_rate") or 0),
        channels=int(probe.get("channels") or 2),
        output_format=export_format,
    )
    result = _run(command, timeout=180)
    if not result.get("ok") or not output_path.is_file():
        error_text = result.get("output", "audio_edit_failed")
        error = "libmp3lame_unavailable" if "libmp3lame" in error_text.lower() and "unknown encoder" in error_text.lower() else "audio_edit_failed"
        return {"ok": False, "message": error_text[:600], "data": {"command": command}, "error": error}
    output_probe = probe_media(output_path, ffmpeg_path=ffmpeg)
    if not output_probe.get("ok") or not output_probe.get("has_audio") or float(output_probe.get("duration") or 0) <= 0:
        return {
            "ok": False,
            "message": "Exported audio failed media validation",
            "data": {"command": command, "output_probe": output_probe},
            "error": "invalid_export",
        }
    requested_duration = float(selection.get("selection_duration") or 0.0)
    actual_duration = float(output_probe.get("duration") or 0.0)
    duration_difference_ms = round((actual_duration - requested_duration) * 1000.0, 3)
    resolved_fade_in, resolved_fade_out = resolve_audio_fades(requested_duration, fade_in, fade_out)
    boundary_smoothing = CUT_BOUNDARY_SMOOTHING_SECONDS if mode == "Precise Cut" and resolved_fade_in <= 0 and resolved_fade_out <= 0 else 0.0
    report = {
        "ok": True,
        "project_id": project_id,
        "original_filename": source.name,
        "export_name": safe_stem,
        "input_duration": probe.get("duration", 0),
        "input_format": validation.get("format", ""),
        "input_codec": probe.get("audio_codec", ""),
        "input_bitrate": probe.get("audio_bit_rate", ""),
        "input_sample_rate": probe.get("sample_rate", ""),
        "input_channels": probe.get("channels", ""),
        "source_format": validation.get("format", ""),
        "selected_start": float(start_time),
        "selected_end": float(end_time),
        "selection_duration": selection.get("selection_duration", 0),
        "actual_output_duration": round(actual_duration, 6),
        "duration_difference_ms": duration_difference_ms,
        "cut_mode": mode,
        "fade_in": float(fade_in),
        "fade_out": float(fade_out),
        "effective_fade_in": round(resolved_fade_in, 6),
        "effective_fade_out": round(resolved_fade_out, 6),
        "boundary_smoothing_ms": round(boundary_smoothing * 1000.0, 3),
        "output_filename": output_path.name,
        "output_codec": output_probe.get("audio_codec", export_format),
        "output_bitrate": "source stream copy" if mode == "Lossless Quick Cut" and export_format == "mp3" else "320 kbps CBR" if export_format == "mp3" else "lossless PCM WAV",
        "output_sample_rate": output_probe.get("sample_rate", ""),
        "output_channels": output_probe.get("channels", ""),
        "preview_format": "audio/mpeg",
        "export_format": export_format.upper(),
        "reencoded": bool(mode != "Lossless Quick Cut" or export_format == "wav"),
        "ffmpeg_command": command,
        "processing_date_time": datetime.now().isoformat(timespec="seconds"),
        "warnings": warnings,
        "preview": preview,
        "waveform": waveform_summary or {},
        "smart_hook_finder": hook_analysis_summary or {},
        "smart_musical_hook": smart_hook_data or {},
    }
    report_path = reports_dir / "edit_report.json"
    report_txt_path = reports_dir / "edit_report.txt"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report_txt_path.write_text(_report_text(report), encoding="utf-8")
    zip_path = ensure_unique_path(base_dir / f"{safe_stem}_Audio_Edit_Package.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in [source_copy, output_path, report_path, report_txt_path]:
            if file_path.is_file():
                archive.write(file_path, str(file_path.relative_to(base_dir)))
    return {
        "ok": True,
        "message": f"Hook {export_format.upper()} ready",
        "data": {
            "project_id": project_id,
            "original_audio": str(source_copy),
            "export_name": safe_stem,
            "hook_mp3": str(output_path) if export_format == "mp3" else "",
            "output_mp3": str(output_path) if export_format == "mp3" else "",
            "hook_wav": str(output_path) if export_format == "wav" else "",
            "output_wav": str(output_path) if export_format == "wav" else "",
            "output_audio": str(output_path),
            "output_format": export_format,
            "report_path": str(report_path),
            "report_txt_path": str(report_txt_path),
            "zip_path": str(zip_path),
            "report": report,
        },
        "error": "",
    }


def export_audio_batch(
    source_audio_path: str | Path,
    *,
    start_time: float,
    durations: list[float],
    project_name: str = "audio_editor",
    output_stem: str = "",
    cut_mode: str = "Lossless Quick Cut",
    fade_in: float = 0.0,
    fade_out: float = 0.0,
    ffmpeg_path: str = "",
    max_upload_mb: int = 200,
    waveform_summary: dict[str, Any] | None = None,
    hook_analysis_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source = Path(source_audio_path)
    ffmpeg = ffmpeg_path or find_ffmpeg()
    validation = validate_audio_editor_input(source, max_upload_mb=max_upload_mb)
    if not validation.get("ok"):
        return {"ok": False, "message": validation.get("message", "Invalid audio"), "data": {"validation": validation}, "error": validation.get("error", "invalid_audio")}
    if not ffmpeg:
        return {"ok": False, "message": "FFmpeg not found", "data": {}, "error": "missing_ffmpeg"}
    probe = probe_media(source, ffmpeg_path=ffmpeg)
    if not probe.get("ok") or not probe.get("has_audio"):
        return {"ok": False, "message": "Invalid or corrupt audio file", "data": {"source_probe": probe}, "error": "invalid_audio"}
    source_duration = float(probe.get("duration") or 0)
    project_id = build_audio_editor_project_id(project_name or source.stem)
    base_dir = ROOT / "exports" / "audio_editor" / project_id
    original_dir = base_dir / "original"
    output_dir = base_dir / "output"
    reports_dir = base_dir / "reports"
    original_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    source_copy = original_dir / f"source.{source.suffix.lower().lstrip('.')}"
    shutil.copy2(source, source_copy)
    mode, warnings = effective_cut_mode(source, cut_mode, fade_in, fade_out)
    if source.suffix.lower() == ".wav" and mode == "Lossless Quick Cut":
        mode = "Precise Cut"
        warnings.append("WAV batch export to MP3 requires encoding to 320 kbps MP3.")
    safe_stem = export_name_base(output_stem, source.name)
    generated: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    selected_durations = sorted({float(item) for item in durations if float(item) > 0})
    for duration in selected_durations:
        end_time = float(start_time) + duration
        if end_time > source_duration + 0.001:
            skipped.append({"duration": int(duration), "start_time": float(start_time), "end_time": round(end_time, 3), "reason": "Beyond source duration; not shortened automatically"})
            continue
        filename = f"{safe_stem}_Hook{int(duration)}.mp3"
        output_path = ensure_unique_path(output_dir / filename)
        command = build_audio_cut_command(
            ffmpeg,
            source,
            output_path,
            start_time=float(start_time),
            end_time=end_time,
            cut_mode=mode,
            fade_in=fade_in,
            fade_out=fade_out,
            sample_rate=int(probe.get("sample_rate") or 0),
            channels=int(probe.get("channels") or 2),
        )
        result = _run(command, timeout=180)
        if not result.get("ok") or not output_path.is_file():
            skipped.append({"duration": int(duration), "start_time": float(start_time), "end_time": round(end_time, 3), "reason": (result.get("output") or "Export failed")[:300], "command": command})
            continue
        generated.append({"duration": int(duration), "start_time": float(start_time), "end_time": round(end_time, 3), "filename": output_path.name, "path": str(output_path), "command": command})
    report = {
        "ok": bool(generated),
        "project_id": project_id,
        "original_filename": source.name,
        "export_name": safe_stem,
        "input_duration": source_duration,
        "selected_start": float(start_time),
        "selected_durations": [int(item) for item in selected_durations],
        "generated_files": generated,
        "skipped_files": skipped,
        "cut_mode": mode,
        "fade_in": float(fade_in),
        "fade_out": float(fade_out),
        "reencoded": mode != "Lossless Quick Cut",
        "output_bitrate": "source stream copy" if mode == "Lossless Quick Cut" else "320 kbps CBR",
        "warnings": warnings + (["Some durations were skipped."] if skipped else []),
        "waveform": waveform_summary or {},
        "smart_hook_finder": hook_analysis_summary or {},
        "processing_date_time": datetime.now().isoformat(timespec="seconds"),
    }
    report_path = reports_dir / "batch_edit_report.json"
    report_txt_path = reports_dir / "batch_edit_report.txt"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report_txt_path.write_text(_batch_report_text(report), encoding="utf-8")
    zip_path = ensure_unique_path(base_dir / f"{safe_stem}_Hooks.zip")
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for item in generated:
                file_path = Path(item["path"])
                if file_path.is_file():
                    archive.write(file_path, file_path.name)
            archive.write(report_path, "batch_edit_report.json")
            archive.write(report_txt_path, "batch_edit_report.txt")
    except Exception as exc:
        return {"ok": False, "message": f"ZIP creation failed: {exc}", "data": {"report": report, "report_path": str(report_path)}, "error": "zip_failed"}
    return {
        "ok": bool(generated),
        "message": "Batch hooks exported" if generated else "No batch hooks exported",
        "data": {
            "project_id": project_id,
            "original_audio": str(source_copy),
            "export_name": safe_stem,
            "generated_files": generated,
            "skipped_files": skipped,
            "report": report,
            "report_path": str(report_path),
            "report_txt_path": str(report_txt_path),
            "zip_path": str(zip_path),
        },
        "error": "" if generated else "no_outputs",
    }


def remove_join_track(tracks: list[dict[str, Any]], track_id: str) -> list[dict[str, Any]]:
    return [dict(track) for track in tracks if str(track.get("track_id") or track.get("upload_id") or track.get("path")) != str(track_id)]


def move_join_track(tracks: list[dict[str, Any]], track_id: str, direction: int) -> list[dict[str, Any]]:
    ordered = [dict(track) for track in tracks]
    index = next((idx for idx, track in enumerate(ordered) if str(track.get("track_id") or track.get("upload_id") or track.get("path")) == str(track_id)), -1)
    target = index + (-1 if int(direction) < 0 else 1)
    if index >= 0 and 0 <= target < len(ordered):
        ordered[index], ordered[target] = ordered[target], ordered[index]
    return ordered


def _join_track_identity(track: dict[str, Any]) -> dict[str, Any]:
    source = Path(str(track.get("path") or ""))
    if not source.is_file():
        return {"path": str(source), "missing": True}
    signature = _source_signature(source, trusted_identity=track)
    return {
        "path": str(source.resolve()),
        "sha256": signature.get("sha256"),
        "upload_id": signature.get("upload_id"),
        "size": signature.get("size"),
        "start": round(float(track.get("start") or 0.0), 3),
        "end": round(float(track.get("end") or track.get("duration") or 0.0), 3),
    }


def build_join_arrangement_fingerprint(
    tracks: list[dict[str, Any]],
    *,
    crossfades: list[dict[str, Any]] | None = None,
    fade_in: bool = False,
    fade_out: bool = False,
) -> str:
    payload = {
        "tracks": [_join_track_identity(track) for track in tracks],
        "crossfades": [
            {"enabled": bool(item.get("enabled")), "duration": round(float(item.get("duration") or 0.0), 3)}
            for item in (crossfades or [])
        ],
        "fade_in": bool(fade_in),
        "fade_out": bool(fade_out),
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _validate_join_tracks(tracks: list[dict[str, Any]], ffmpeg: str, max_upload_mb: int) -> dict[str, Any]:
    if len(tracks) < 2:
        return {"ok": False, "error": "not_enough_tracks", "message": "Add at least two MP3 or WAV files."}
    normalized: list[dict[str, Any]] = []
    for index, track in enumerate(tracks):
        source = Path(str(track.get("path") or ""))
        validation = validate_audio_editor_input(source, max_upload_mb=max_upload_mb)
        if not validation.get("ok"):
            return {"ok": False, "error": validation.get("error", "invalid_audio"), "message": f"Track {index + 1}: {validation.get('message', 'invalid audio')}"}
        probe = probe_media(source, ffmpeg_path=ffmpeg)
        duration = float(probe.get("duration") or 0.0)
        if not probe.get("ok") or not probe.get("has_audio") or duration <= 0:
            return {"ok": False, "error": "invalid_audio", "message": f"Track {index + 1}: audio could not be read."}
        start = max(0.0, float(track.get("start") or 0.0))
        end = min(duration, float(track.get("end") or duration))
        if end - start < 0.25:
            return {"ok": False, "error": "invalid_trim", "message": f"Track {index + 1}: trim range is too short."}
        normalized.append({**dict(track), "path": str(source), "start": round(start, 3), "end": round(end, 3), "duration": round(duration, 3), "trimmed_duration": round(end - start, 3), "probe": probe})
    return {"ok": True, "tracks": normalized, "error": "", "message": ""}


def _normalized_crossfades(crossfades: list[dict[str, Any]] | None, tracks: list[dict[str, Any]]) -> dict[str, Any]:
    transitions: list[dict[str, Any]] = []
    for index in range(max(0, len(tracks) - 1)):
        raw = (crossfades or [])[index] if index < len(crossfades or []) else {}
        enabled = bool(raw.get("enabled"))
        duration = float(raw.get("duration") or 2.0) if enabled else 0.0
        if enabled and duration not in JOIN_CROSSFADE_DURATIONS:
            duration = 2.0
        maximum = min(float(tracks[index]["trimmed_duration"]), float(tracks[index + 1]["trimmed_duration"])) - 0.05
        if enabled and (maximum <= 0 or duration > maximum):
            return {"ok": False, "error": "crossfade_too_long", "message": f"Crossfade between tracks {index + 1} and {index + 2} is longer than the trimmed audio."}
        transitions.append({"enabled": enabled, "duration": duration})
    return {"ok": True, "crossfades": transitions, "error": "", "message": ""}


def _build_join_filter(tracks: list[dict[str, Any]], crossfades: list[dict[str, Any]], *, fade_in: bool, fade_out: bool) -> tuple[str, str, float]:
    filters: list[str] = []
    for index, track in enumerate(tracks):
        filters.append(
            f"[{index}:a]atrim=start={float(track['start']):.3f}:end={float(track['end']):.3f},"
            f"asetpts=PTS-STARTPTS,aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[t{index}]"
        )
    current = "t0"
    expected_duration = float(tracks[0]["trimmed_duration"])
    for index in range(1, len(tracks)):
        output_label = f"j{index}"
        transition = crossfades[index - 1]
        if transition.get("enabled"):
            duration = float(transition["duration"])
            filters.append(f"[{current}][t{index}]acrossfade=d={duration:.3f}:c1=qsin:c2=qsin[{output_label}]")
            expected_duration += float(tracks[index]["trimmed_duration"]) - duration
        else:
            filters.append(f"[{current}][t{index}]concat=n=2:v=0:a=1[{output_label}]")
            expected_duration += float(tracks[index]["trimmed_duration"])
        current = output_label
    if fade_in or fade_out:
        fade_filters: list[str] = []
        if fade_in:
            fade_filters.append("afade=t=in:st=0:d=1.000")
        if fade_out:
            fade_filters.append(f"afade=t=out:st={max(0.0, expected_duration - 1.0):.3f}:d=1.000")
        filters.append(f"[{current}]{','.join(fade_filters)}[joined]")
        current = "joined"
    return ";".join(filters), current, round(expected_duration, 3)


def _validate_join_output(path: Path, *, output_format: str, expected_duration: float, ffmpeg: str) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size <= 0:
        return {"ok": False, "error": "missing_output", "message": "Joined output was not created."}
    probe = probe_media(path, ffmpeg_path=ffmpeg)
    codec = str(probe.get("audio_codec") or "").lower()
    codec_ok = codec == "mp3" if output_format == "mp3" else codec.startswith("pcm")
    duration = float(probe.get("duration") or 0.0)
    tolerance = max(0.5, expected_duration * 0.015)
    duration_ok = duration > 0 and abs(duration - expected_duration) <= tolerance
    checks = {"file_nonempty": path.stat().st_size > 0, "probe_ok": bool(probe.get("ok") and probe.get("has_audio")), "codec_ok": codec_ok, "duration_ok": duration_ok}
    return {"ok": all(checks.values()), "error": "" if all(checks.values()) else "output_validation_failed", "message": "" if all(checks.values()) else "Joined output failed codec or duration validation.", "checks": checks, "probe": probe, "duration": duration, "expected_duration": expected_duration, "duration_delta": round(abs(duration - expected_duration), 3)}


def join_audio_tracks(
    tracks: list[dict[str, Any]],
    *,
    crossfades: list[dict[str, Any]] | None = None,
    fade_in: bool = False,
    fade_out: bool = False,
    export_name: str = "Joined Audio",
    output_format: str = "mp3",
    project_name: str = "audio_joiner",
    output_dir: str | Path = "",
    ffmpeg_path: str = "",
    max_upload_mb: int = 200,
    preview: bool = False,
) -> dict[str, Any]:
    ffmpeg = ffmpeg_path or find_ffmpeg()
    if not ffmpeg:
        return {"ok": False, "message": "FFmpeg not found", "data": {}, "error": "missing_ffmpeg"}
    validated = _validate_join_tracks(tracks, ffmpeg, max_upload_mb)
    if not validated.get("ok"):
        return {"ok": False, "message": validated.get("message"), "data": {}, "error": validated.get("error")}
    normalized_tracks = validated["tracks"]
    transitions = _normalized_crossfades(crossfades, normalized_tracks)
    if not transitions.get("ok"):
        return {"ok": False, "message": transitions.get("message"), "data": {}, "error": transitions.get("error")}
    normalized_fades = transitions["crossfades"]
    arrangement_id = build_join_arrangement_fingerprint(normalized_tracks, crossfades=normalized_fades, fade_in=fade_in, fade_out=fade_out)
    export_format = "wav" if str(output_format or "").lower() == "wav" and not preview else "mp3"
    base_dir = Path(output_dir) if output_dir else ROOT / "exports" / "audio_joiner" / safe_name(project_name or "audio_joiner")
    target_dir = base_dir / ("previews" if preview else "output")
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_export_name = make_safe_filename(export_name or "Joined Audio") or "Joined Audio"
    output_path = target_dir / (f"join_preview_{arrangement_id[:16]}.mp3" if preview else f"{safe_export_name}.{export_format}")
    if not preview:
        output_path = ensure_unique_path(output_path)
    filter_complex, output_label, expected_duration = _build_join_filter(normalized_tracks, normalized_fades, fade_in=fade_in, fade_out=fade_out)
    if preview and output_path.is_file():
        cached_validation = _validate_join_output(output_path, output_format="mp3", expected_duration=expected_duration, ffmpeg=ffmpeg)
        if cached_validation.get("ok"):
            return {"ok": True, "message": "Joined preview ready", "data": {"output_audio": str(output_path), "preview_mp3": str(output_path), "output_format": "mp3", "arrangement_fingerprint": arrangement_id, "cache_status": "hit", "expected_duration": expected_duration, "output_duration": cached_validation.get("duration"), "validation": cached_validation}, "error": ""}
    args = [ffmpeg, "-y"]
    for track in normalized_tracks:
        args += ["-i", str(track["path"])]
    args += ["-filter_complex", filter_complex, "-map", f"[{output_label}]", "-vn"]
    if export_format == "mp3":
        args += ["-c:a", "libmp3lame", "-b:a", "320k", "-minrate", "320k", "-maxrate", "320k", "-ar", "48000", "-ac", "2", "-write_xing", "0"]
    else:
        args += ["-c:a", "pcm_s24le", "-ar", "48000", "-ac", "2"]
    args.append(str(output_path))
    result = _run(args, timeout=300)
    if not result.get("ok"):
        output_path.unlink(missing_ok=True)
        return {"ok": False, "message": str(result.get("output") or "Audio join failed")[:600], "data": {"command": args}, "error": "audio_join_failed"}
    output_validation = _validate_join_output(output_path, output_format=export_format, expected_duration=expected_duration, ffmpeg=ffmpeg)
    if not output_validation.get("ok"):
        return {"ok": False, "message": output_validation.get("message"), "data": {"output_audio": str(output_path), "validation": output_validation}, "error": output_validation.get("error")}
    report = {
        "ok": True,
        "track_count": len(normalized_tracks),
        "tracks": [{"filename": Path(track["path"]).name, "start": track["start"], "end": track["end"], "trimmed_duration": track["trimmed_duration"]} for track in normalized_tracks],
        "crossfades": normalized_fades,
        "fade_in": bool(fade_in),
        "fade_out": bool(fade_out),
        "export_name": safe_export_name,
        "output_format": export_format.upper(),
        "output_codec": output_validation.get("probe", {}).get("audio_codec"),
        "output_bitrate": "320 kbps CBR" if export_format == "mp3" else "lossless PCM 24-bit",
        "expected_duration": expected_duration,
        "output_duration": output_validation.get("duration"),
        "arrangement_fingerprint": arrangement_id,
        "processing_mode": "normalized FFmpeg filter_complex",
        "preview": bool(preview),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    report_path = base_dir / "join_report.json"
    if not preview:
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "message": "Joined preview ready" if preview else "Joined audio ready",
        "data": {
            "output_audio": str(output_path),
            "joined_mp3": str(output_path) if export_format == "mp3" else "",
            "joined_wav": str(output_path) if export_format == "wav" else "",
            "preview_mp3": str(output_path) if preview else "",
            "output_format": export_format,
            "export_name": safe_export_name,
            "arrangement_fingerprint": arrangement_id,
            "cache_status": "miss",
            "expected_duration": expected_duration,
            "output_duration": output_validation.get("duration"),
            "validation": output_validation,
            "report": report,
            "report_path": str(report_path) if not preview else "",
        },
        "error": "",
    }


def preview_join_transition(
    left_track: dict[str, Any],
    right_track: dict[str, Any],
    *,
    transition: dict[str, Any] | None = None,
    project_name: str = "audio_joiner",
    output_dir: str | Path = "",
    ffmpeg_path: str = "",
    max_upload_mb: int = 200,
    context_seconds: float = 5.0,
) -> dict[str, Any]:
    preview_tracks = build_join_transition_preview_tracks(left_track, right_track, context_seconds=context_seconds)
    resolved_transition = dict(transition or JOIN_DEFAULT_TRANSITION)
    result = join_audio_tracks(
        preview_tracks,
        crossfades=[resolved_transition],
        fade_in=False,
        fade_out=False,
        project_name=project_name,
        output_dir=output_dir,
        ffmpeg_path=ffmpeg_path,
        max_upload_mb=max_upload_mb,
        preview=True,
    )
    if result.get("ok"):
        result.setdefault("data", {})["transition_pair"] = [
            str(left_track.get("track_id") or ""),
            str(right_track.get("track_id") or ""),
        ]
        result["data"]["context_seconds"] = float(context_seconds)
    return result
