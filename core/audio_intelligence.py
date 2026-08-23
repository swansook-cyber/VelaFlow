from __future__ import annotations

import hashlib
import json
import math
import subprocess
import time
from array import array
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from core.audio_bpm import BPM_METHOD, estimate_bpm
from core.audio_editor import build_source_signature
from core.paths import ROOT
from core.project_io import atomic_write_json
from core.real_clip_pipeline import find_ffmpeg, probe_media


SCHEMA_VERSION = 3
ANALYZER_VERSION = "audio-intelligence-v1-bpm-experimental"
SUPPORTED_DEPTHS = {"fast", "deep"}
DEFAULT_CACHE_ROOT = ROOT / "outputs" / "cache" / "audio_intelligence"
PCM_ANALYSIS_SAMPLE_RATE = 8000
ENERGY_WINDOW_SEC = 1.0
ENERGY_PROFILE_MAX_POINTS = 600
SILENCE_WINDOW_SEC = 0.1
SILENCE_THRESHOLD_DBFS = -50.0
MINIMUM_ACTIVE_SEC = 0.2
MINIMUM_INTERNAL_SILENCE_SEC = 2.0
MAX_INTERNAL_SILENCE_REGIONS = 24

ProbeFunction = Callable[..., dict[str, Any]]
LoudnessRunner = Callable[[Path, str], dict[str, Any]]
PcmRunner = Callable[[Path, str], dict[str, Any]]


def _utc_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _safe_context(source_context: dict[str, Any] | None) -> dict[str, str]:
    context = source_context if isinstance(source_context, dict) else {}
    return {
        "kind": str(context.get("kind") or context.get("source_type") or "file").strip() or "file",
        "project_id": str(context.get("project_id") or context.get("project_identity") or "").strip(),
        "path_role": str(context.get("path_role") or context.get("role") or "source").strip() or "source",
        "upload_id": str(context.get("upload_id") or "").strip(),
        "content_digest": str(context.get("content_digest") or context.get("sha256") or "").strip().lower(),
    }


def _empty_result(path: Path, context: dict[str, str]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis_depth": "fast",
        "completed_capabilities": [],
        "source": {
            "source_id": "",
            "kind": context["kind"],
            "project_id": context["project_id"],
            "path_role": context["path_role"],
            "path": str(path),
            "sha256": "",
            "size_bytes": 0,
            "mtime_ns": None,
        },
        "metadata": {
            "duration_sec": None,
            "codec": None,
            "bitrate_bps": None,
            "sample_rate_hz": None,
            "channels": None,
            "method": None,
            "status": "unknown",
        },
        "loudness": {
            "integrated_lufs": None,
            "true_peak_dbtp": None,
            "lra_lu": None,
            "units": {"integrated_lufs": "LUFS", "true_peak_dbtp": "dBTP", "lra_lu": "LU"},
            "method": None,
            "status": "unknown",
        },
        "energy": {
            "profile": [],
            "window_sec": ENERGY_WINDOW_SEC,
            "normalization": "silence_floor_to_active_p90_dbfs",
            "method": "pcm_rms_windows",
            "status": "unknown",
        },
        "silence": {
            "leading_sec": None,
            "trailing_sec": None,
            "internal_regions": [],
            "threshold_dbfs": SILENCE_THRESHOLD_DBFS,
            "minimum_active_sec": MINIMUM_ACTIVE_SEC,
            "minimum_internal_sec": MINIMUM_INTERNAL_SILENCE_SEC,
            "method": "pcm_window_activity",
            "status": "unknown",
        },
        "musical": {
            "bpm": None,
            "bpm_confidence": None,
            "bpm_method": None,
            "bpm_status": "unknown",
        },
        "cache": {
            "hit": False,
            "analyzer_version": ANALYZER_VERSION,
            "created_at": None,
        },
        "performance": {"elapsed_ms": None, "ffprobe_runs": 0, "ffmpeg_runs": 0, "ffmpeg_loudness_runs": 0, "pcm_analysis_runs": 0, "bpm_decode_runs": 0, "bpm_elapsed_ms": 0.0},
        "warnings": [],
        "errors": [],
    }


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _identity_locator(path: Path, context: dict[str, str]) -> str:
    payload = {
        "kind": context["kind"],
        "project_id": context["project_id"],
        "path_role": context["path_role"],
        "path": str(path.resolve()),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _identity_index_path(cache_root: Path, locator: str) -> Path:
    return cache_root / "_identities" / f"{locator}.json"


def _trusted_identity_from_context(context: dict[str, str], size: int) -> dict[str, Any] | None:
    digest = context["content_digest"]
    if context["upload_id"] and len(digest) == 64:
        return {
            "upload_id": context["upload_id"],
            "content_digest": digest,
            "size_bytes": size,
        }
    return None


def _resolve_source_identity(path: Path, context: dict[str, str], cache_root: Path) -> dict[str, Any]:
    stat = path.stat()
    trusted = _trusted_identity_from_context(context, stat.st_size)
    locator = _identity_locator(path, context)
    index_path = _identity_index_path(cache_root, locator)
    if trusted is None:
        indexed = _read_json(index_path)
        if (
            indexed
            and indexed.get("path") == str(path.resolve())
            and int(indexed.get("size_bytes") or -1) == stat.st_size
            and int(indexed.get("mtime_ns") or -1) == stat.st_mtime_ns
            and len(str(indexed.get("sha256") or "")) == 64
        ):
            trusted = {
                "upload_id": f"managed:{locator}",
                "content_digest": str(indexed["sha256"]),
                "size_bytes": stat.st_size,
            }

    signature = build_source_signature(path, trusted_identity=trusted)
    digest = str(signature.get("sha256") or "")
    if trusted is None:
        atomic_write_json(
            index_path,
            {
                "path": str(path.resolve()),
                "size_bytes": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "sha256": digest,
                "updated_at": _utc_now(),
            },
        )

    if context["upload_id"] and context["content_digest"]:
        identity_material = {
            "kind": context["kind"],
            "project_id": context["project_id"],
            "path_role": context["path_role"],
            "upload_id": context["upload_id"],
            "sha256": digest,
            "size_bytes": stat.st_size,
        }
    else:
        identity_material = {
            "kind": context["kind"],
            "project_id": context["project_id"],
            "path_role": context["path_role"],
            "path": str(path.resolve()),
            "sha256": digest,
            "size_bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
        }
    encoded = json.dumps(identity_material, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "source_id": hashlib.sha256(encoded).hexdigest(),
        "sha256": digest,
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "identity_source": signature.get("identity_source", ""),
    }


def _cache_path(cache_root: Path, source_id: str) -> Path:
    return cache_root / f"{source_id}.json"


def _valid_cache(payload: dict[str, Any] | None, source_id: str, depth: str) -> bool:
    if not payload:
        return False
    if payload.get("schema_version") != SCHEMA_VERSION:
        return False
    if (payload.get("cache") or {}).get("analyzer_version") != ANALYZER_VERSION:
        return False
    if (payload.get("source") or {}).get("source_id") != source_id:
        return False
    capabilities = set(payload.get("completed_capabilities") or [])
    if "metadata" not in capabilities:
        return False
    return depth == "fast" or {"loudness", "energy", "silence", "musical"}.issubset(capabilities)


def _nullable_number(value: Any) -> float | None:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def parse_loudnorm_output(output: str) -> dict[str, Any]:
    """Parse the final loudnorm JSON object without accepting NaN or infinity."""
    decoder = json.JSONDecoder()
    candidates: list[dict[str, Any]] = []
    text = str(output or "")
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and any(key in payload for key in ("input_i", "input_tp", "input_lra")):
            candidates.append(payload)
    if not candidates:
        return {"integrated_lufs": None, "true_peak_dbtp": None, "lra_lu": None, "found": False}
    payload = candidates[-1]
    return {
        "integrated_lufs": _nullable_number(payload.get("input_i")),
        "true_peak_dbtp": _nullable_number(payload.get("input_tp")),
        "lra_lu": _nullable_number(payload.get("input_lra")),
        "found": True,
    }


def _run_loudnorm_analysis(path: Path, ffmpeg_path: str) -> dict[str, Any]:
    ffmpeg = ffmpeg_path or find_ffmpeg()
    if not ffmpeg:
        return {"ok": False, "output": "", "error": "missing_ffmpeg"}
    command = [
        ffmpeg,
        "-hide_banner",
        "-nostats",
        "-i",
        str(path),
        "-map",
        "0:a:0",
        "-af",
        "loudnorm=I=-14:TP=-1:LRA=11:print_format=json",
        "-f",
        "null",
        "-",
    ]
    try:
        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "output": "", "error": "loudness_timeout", "command": command}
    except (FileNotFoundError, OSError) as exc:
        return {"ok": False, "output": "", "error": f"loudness_process_failed:{exc}", "command": command}
    output = "\n".join(part for part in (process.stdout, process.stderr) if part)
    return {
        "ok": process.returncode == 0,
        "output": output,
        "error": "" if process.returncode == 0 else f"ffmpeg_loudness_exit_{process.returncode}",
        "command": command,
    }


def _run_pcm_analysis(path: Path, ffmpeg_path: str) -> dict[str, Any]:
    """Decode one bounded-rate mono PCM stream for all signal-level metrics."""
    ffmpeg = ffmpeg_path or find_ffmpeg()
    if not ffmpeg:
        return {"ok": False, "samples": array("h"), "sample_rate": PCM_ANALYSIS_SAMPLE_RATE, "error": "missing_ffmpeg"}
    command = [
        ffmpeg,
        "-hide_banner",
        "-nostats",
        "-v",
        "error",
        "-i",
        str(path),
        "-map",
        "0:a:0",
        "-ac",
        "1",
        "-ar",
        str(PCM_ANALYSIS_SAMPLE_RATE),
        "-c:a",
        "pcm_s16le",
        "-f",
        "s16le",
        "-",
    ]
    try:
        process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
    except subprocess.TimeoutExpired:
        return {"ok": False, "samples": array("h"), "sample_rate": PCM_ANALYSIS_SAMPLE_RATE, "error": "pcm_analysis_timeout", "command": command}
    except (FileNotFoundError, OSError) as exc:
        return {"ok": False, "samples": array("h"), "sample_rate": PCM_ANALYSIS_SAMPLE_RATE, "error": f"pcm_analysis_failed:{exc}", "command": command}
    samples = array("h")
    if process.returncode == 0 and process.stdout:
        samples.frombytes(process.stdout)
    return {
        "ok": process.returncode == 0 and bool(samples),
        "samples": samples,
        "sample_rate": PCM_ANALYSIS_SAMPLE_RATE,
        "error": "" if process.returncode == 0 and samples else f"pcm_analysis_exit_{process.returncode}" if process.returncode else "empty_pcm_analysis",
        "command": command,
    }


def _rms_dbfs(mean_square: float) -> float:
    if mean_square <= 0.0:
        return -120.0
    return max(-120.0, 10.0 * math.log10(mean_square))


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = max(0.0, min(1.0, percentile)) * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _activity_runs(flags: list[bool], target: bool) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for index, value in enumerate(flags + [not target]):
        if value == target and start is None:
            start = index
        elif value != target and start is not None:
            runs.append((start, index))
            start = None
    return runs


def _analyze_pcm_signal(samples: array, sample_rate: int, duration_sec: float | None) -> dict[str, Any]:
    decoded_duration = len(samples) / float(sample_rate) if sample_rate > 0 else 0.0
    duration = min(float(duration_sec), decoded_duration) if duration_sec and duration_sec > 0 else decoded_duration
    if not samples or duration <= 0:
        return {"ok": False, "error": "empty_pcm_analysis"}

    activity_window_samples = max(1, int(round(SILENCE_WINDOW_SEC * sample_rate)))
    activity_frames: list[dict[str, float]] = []
    sample_limit = min(len(samples), max(1, int(math.ceil(duration * sample_rate))))
    for start in range(0, sample_limit, activity_window_samples):
        end = min(sample_limit, start + activity_window_samples)
        if end <= start:
            continue
        sum_square = 0.0
        for value in samples[start:end]:
            normalized = value / 32768.0
            sum_square += normalized * normalized
        mean_square = sum_square / (end - start)
        activity_frames.append(
            {
                "start_sec": start / sample_rate,
                "end_sec": min(duration, end / sample_rate),
                "mean_square": mean_square,
                "rms_dbfs": _rms_dbfs(mean_square),
            }
        )
    if not activity_frames:
        return {"ok": False, "error": "empty_pcm_windows"}

    profile_window_sec = max(ENERGY_WINDOW_SEC, math.ceil((duration / ENERGY_PROFILE_MAX_POINTS) / SILENCE_WINDOW_SEC) * SILENCE_WINDOW_SEC)
    profile_group_size = max(1, int(round(profile_window_sec / SILENCE_WINDOW_SEC)))
    raw_profile: list[dict[str, float]] = []
    for start in range(0, len(activity_frames), profile_group_size):
        group = activity_frames[start : start + profile_group_size]
        total_duration = sum(max(0.0, item["end_sec"] - item["start_sec"]) for item in group)
        if total_duration <= 0:
            continue
        mean_square = sum(item["mean_square"] * max(0.0, item["end_sec"] - item["start_sec"]) for item in group) / total_duration
        raw_profile.append(
            {
                "start_sec": group[0]["start_sec"],
                "end_sec": min(duration, group[-1]["end_sec"]),
                "rms_dbfs": _rms_dbfs(mean_square),
            }
        )

    active_profile_db = [item["rms_dbfs"] for item in raw_profile if item["rms_dbfs"] > SILENCE_THRESHOLD_DBFS]
    robust_upper_db = _percentile(active_profile_db, 0.90)
    for item in raw_profile:
        if robust_upper_db is None or item["rms_dbfs"] <= SILENCE_THRESHOLD_DBFS:
            normalized_energy = 0.0
        else:
            scale = max(6.0, robust_upper_db - SILENCE_THRESHOLD_DBFS)
            normalized_energy = max(0.0, min(1.0, (item["rms_dbfs"] - SILENCE_THRESHOLD_DBFS) / scale))
        item["start_sec"] = round(item["start_sec"], 3)
        item["end_sec"] = round(min(duration, item["end_sec"]), 3)
        item["rms_dbfs"] = round(item["rms_dbfs"], 2)
        item["normalized"] = round(normalized_energy, 4)

    raw_active = [item["rms_dbfs"] > SILENCE_THRESHOLD_DBFS for item in activity_frames]
    minimum_active_windows = max(1, int(math.ceil(MINIMUM_ACTIVE_SEC / SILENCE_WINDOW_SEC)))
    qualified_active = [False] * len(raw_active)
    for start, end in _activity_runs(raw_active, True):
        if end - start >= minimum_active_windows:
            for index in range(start, end):
                qualified_active[index] = True

    active_indexes = [index for index, active in enumerate(qualified_active) if active]
    if not active_indexes:
        leading_sec = duration
        trailing_sec = duration
        internal_regions: list[dict[str, float]] = []
    else:
        first_active = active_indexes[0]
        last_active = active_indexes[-1]
        leading_sec = activity_frames[first_active]["start_sec"]
        trailing_sec = max(0.0, duration - activity_frames[last_active]["end_sec"])
        minimum_internal_windows = max(1, int(math.ceil(MINIMUM_INTERNAL_SILENCE_SEC / SILENCE_WINDOW_SEC)))
        internal_regions = []
        internal_flags = [not value for value in qualified_active]
        for start, end in _activity_runs(internal_flags, True):
            if start <= first_active or end - 1 >= last_active or end - start < minimum_internal_windows:
                continue
            region_start = activity_frames[start]["start_sec"]
            region_end = min(duration, activity_frames[end - 1]["end_sec"])
            internal_regions.append(
                {
                    "start_sec": round(region_start, 3),
                    "end_sec": round(region_end, 3),
                    "duration_sec": round(max(0.0, region_end - region_start), 3),
                }
            )
            if len(internal_regions) >= MAX_INTERNAL_SILENCE_REGIONS:
                break

    return {
        "ok": True,
        "energy": {
            "profile": raw_profile[:ENERGY_PROFILE_MAX_POINTS],
            "window_sec": round(profile_window_sec, 3),
            "normalization": "linear dBFS scaling from -50 dBFS silence floor to active-window 90th percentile; clipped to 0..1",
            "method": "pcm_rms_windows",
            "status": "ok",
        },
        "silence": {
            "leading_sec": round(min(duration, leading_sec), 3),
            "trailing_sec": round(min(duration, trailing_sec), 3),
            "internal_regions": internal_regions,
            "threshold_dbfs": SILENCE_THRESHOLD_DBFS,
            "minimum_active_sec": MINIMUM_ACTIVE_SEC,
            "minimum_internal_sec": MINIMUM_INTERNAL_SILENCE_SEC,
            "method": "pcm_window_activity",
            "status": "ok",
        },
    }


def _apply_signal_analysis(result: dict[str, Any], run: dict[str, Any]) -> bool:
    if not run.get("ok"):
        result["errors"].append(str(run.get("error") or "pcm_analysis_failed"))
        result["warnings"].append("Energy and silence analysis were unavailable; values remain unknown.")
        return False
    signal = _analyze_pcm_signal(
        run.get("samples") or array("h"),
        int(run.get("sample_rate") or PCM_ANALYSIS_SAMPLE_RATE),
        (result.get("metadata") or {}).get("duration_sec"),
    )
    if not signal.get("ok"):
        result["errors"].append(str(signal.get("error") or "pcm_signal_analysis_failed"))
        result["warnings"].append("Energy and silence analysis were unavailable; values remain unknown.")
        return False
    result["energy"] = signal["energy"]
    result["silence"] = signal["silence"]
    result["completed_capabilities"].extend(["energy", "silence"])
    return True


def _apply_bpm_analysis(result: dict[str, Any], run: dict[str, Any]) -> None:
    musical = result["musical"]
    musical.update({"bpm": None, "bpm_confidence": 0.0, "bpm_method": BPM_METHOD, "bpm_status": "unavailable"})
    samples = run.get("samples")
    if not run.get("ok") or samples is None or len(samples) == 0:
        musical["bpm_reason"] = str(run.get("error") or "pcm_analysis_unavailable")
        result["completed_capabilities"].append("musical")
        return
    measured = estimate_bpm(samples, int(run.get("sample_rate") or PCM_ANALYSIS_SAMPLE_RATE))
    for key in (
        "bpm",
        "bpm_confidence",
        "bpm_method",
        "bpm_status",
        "bpm_reason",
        "onset_count",
        "segment_consistency",
        "half_double_ambiguity",
    ):
        if key in measured:
            musical[key] = measured[key]
    result["performance"]["bpm_elapsed_ms"] = float(measured.get("bpm_elapsed_ms") or 0.0)
    if musical["bpm_status"] == "error":
        result["warnings"].append(f"Experimental BPM analysis failed: {musical.get('bpm_reason') or 'unknown_error'}")
    result["completed_capabilities"].append("musical")


def _apply_probe(result: dict[str, Any], probe: dict[str, Any]) -> None:
    metadata = result["metadata"]
    if not probe.get("ok") or not probe.get("has_audio", True):
        metadata["method"] = "ffprobe"
        metadata["status"] = "unknown"
        result["errors"].append(str(probe.get("error") or "audio_probe_failed"))
        return
    metadata.update(
        {
            "duration_sec": _nullable_number(probe.get("duration")),
            "codec": str(probe.get("audio_codec") or "") or None,
            "bitrate_bps": int(probe.get("audio_bit_rate") or 0) or None,
            "sample_rate_hz": int(probe.get("sample_rate") or 0) or None,
            "channels": int(probe.get("channels") or 0) or None,
            "method": "ffprobe",
        }
    )
    required_values = (metadata["duration_sec"], metadata["codec"], metadata["sample_rate_hz"], metadata["channels"])
    metadata["status"] = "measured" if all(value is not None for value in required_values) else "partial"
    if metadata["status"] == "partial":
        result["warnings"].append("Some FFprobe metadata fields were unavailable and remain null.")
    result["completed_capabilities"].append("metadata")


def _apply_loudness(result: dict[str, Any], run: dict[str, Any]) -> bool:
    loudness = result["loudness"]
    loudness["method"] = "ffmpeg_loudnorm"
    if not run.get("ok"):
        result["errors"].append(str(run.get("error") or "ffmpeg_loudness_failed"))
        result["warnings"].append("Loudness analysis was unavailable; values remain null.")
        return False
    parsed = parse_loudnorm_output(str(run.get("output") or ""))
    loudness.update({key: parsed[key] for key in ("integrated_lufs", "true_peak_dbtp", "lra_lu")})
    available = sum(loudness[key] is not None for key in ("integrated_lufs", "true_peak_dbtp", "lra_lu"))
    loudness["status"] = "measured" if available == 3 else "partial" if available else "unknown"
    if not parsed["found"]:
        result["warnings"].append("FFmpeg returned no readable loudnorm JSON; values remain null.")
        return False
    elif available < 3:
        missing = [key for key in ("integrated_lufs", "true_peak_dbtp", "lra_lu") if loudness[key] is None]
        result["warnings"].append("Unavailable loudness fields: " + ", ".join(missing))
    result["completed_capabilities"].append("loudness")
    return True


def analyze_audio_source(
    path: str | Path,
    source_context: dict[str, Any] | None = None,
    depth: str = "fast",
    *,
    cache_root: str | Path | None = None,
    ffmpeg_path: str = "",
    _probe_func: ProbeFunction | None = None,
    _loudness_runner: LoudnessRunner | None = None,
    _pcm_runner: PcmRunner | None = None,
) -> dict[str, Any]:
    """Return versioned source facts, preserving unknown values as null."""
    started = time.perf_counter()
    requested_depth = str(depth or "fast").strip().lower()
    if requested_depth not in SUPPORTED_DEPTHS:
        raise ValueError("depth must be 'fast' or 'deep'")
    source = Path(path)
    context = _safe_context(source_context)
    result = _empty_result(source, context)
    result["analysis_depth"] = requested_depth
    if not source.is_file():
        result["errors"].append("missing_source")
        result["performance"]["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 3)
        return result

    resolved_cache_root = Path(cache_root) if cache_root is not None else DEFAULT_CACHE_ROOT
    try:
        identity = _resolve_source_identity(source, context, resolved_cache_root)
    except (OSError, ValueError) as exc:
        result["errors"].append(f"source_identity_failed:{exc}")
        result["performance"]["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 3)
        return result
    result["source"].update(identity)
    result["source"]["path"] = str(source.resolve())
    cache_path = _cache_path(resolved_cache_root, identity["source_id"])
    cached = _read_json(cache_path)
    if _valid_cache(cached, identity["source_id"], requested_depth):
        cached["cache"]["hit"] = True
        cached["performance"] = {
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
            "ffprobe_runs": 0,
            "ffmpeg_runs": 0,
            "ffmpeg_loudness_runs": 0,
            "pcm_analysis_runs": 0,
            "bpm_decode_runs": 0,
            "bpm_elapsed_ms": 0.0,
        }
        return cached

    if _valid_cache(cached, identity["source_id"], "fast"):
        result = cached
        result["cache"]["hit"] = False
        result["analysis_depth"] = requested_depth
        result["performance"] = {"elapsed_ms": None, "ffprobe_runs": 0, "ffmpeg_runs": 0, "ffmpeg_loudness_runs": 0, "pcm_analysis_runs": 0, "bpm_decode_runs": 0, "bpm_elapsed_ms": 0.0}
    else:
        probe_function = _probe_func or probe_media
        probe = probe_function(source, ffmpeg_path=ffmpeg_path)
        result["performance"]["ffprobe_runs"] = 2
        _apply_probe(result, dict(probe or {}))

    if requested_depth == "deep" and "metadata" in result["completed_capabilities"]:
        runner = _loudness_runner or _run_loudnorm_analysis
        loudness_run = runner(source, ffmpeg_path)
        result["performance"]["ffmpeg_runs"] += 1
        result["performance"]["ffmpeg_loudness_runs"] += 1
        _apply_loudness(result, dict(loudness_run or {}))
        pcm_runner = _pcm_runner or _run_pcm_analysis
        pcm_run = pcm_runner(source, ffmpeg_path)
        result["performance"]["pcm_analysis_runs"] += 1
        _apply_signal_analysis(result, dict(pcm_run or {}))
        _apply_bpm_analysis(result, dict(pcm_run or {}))

    deep_capabilities = {"loudness", "energy", "silence", "musical"}
    result["analysis_depth"] = "deep" if deep_capabilities.issubset(set(result["completed_capabilities"])) else "fast"
    result["cache"].update({"hit": False, "analyzer_version": ANALYZER_VERSION, "created_at": _utc_now()})
    result["performance"]["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 3)
    try:
        atomic_write_json(cache_path, result)
    except OSError as exc:
        result["warnings"].append(f"Audio Intelligence cache write failed: {exc}")
    return result
