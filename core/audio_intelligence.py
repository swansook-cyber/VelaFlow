from __future__ import annotations

import hashlib
import json
import math
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from core.audio_editor import build_source_signature
from core.paths import ROOT
from core.project_io import atomic_write_json
from core.real_clip_pipeline import find_ffmpeg, probe_media


SCHEMA_VERSION = 1
ANALYZER_VERSION = "audio-intelligence-v1"
SUPPORTED_DEPTHS = {"fast", "deep"}
DEFAULT_CACHE_ROOT = ROOT / "outputs" / "cache" / "audio_intelligence"

ProbeFunction = Callable[..., dict[str, Any]]
LoudnessRunner = Callable[[Path, str], dict[str, Any]]


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
        "cache": {
            "hit": False,
            "analyzer_version": ANALYZER_VERSION,
            "created_at": None,
        },
        "performance": {"elapsed_ms": None, "ffprobe_runs": 0, "ffmpeg_runs": 0},
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
    return depth == "fast" or "loudness" in capabilities


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
        }
        return cached

    if _valid_cache(cached, identity["source_id"], "fast"):
        result = cached
        result["cache"]["hit"] = False
        result["analysis_depth"] = requested_depth
        result["performance"] = {"elapsed_ms": None, "ffprobe_runs": 0, "ffmpeg_runs": 0}
    else:
        probe_function = _probe_func or probe_media
        probe = probe_function(source, ffmpeg_path=ffmpeg_path)
        result["performance"]["ffprobe_runs"] = 2
        _apply_probe(result, dict(probe or {}))

    if requested_depth == "deep" and "metadata" in result["completed_capabilities"]:
        runner = _loudness_runner or _run_loudnorm_analysis
        loudness_run = runner(source, ffmpeg_path)
        result["performance"]["ffmpeg_runs"] += 1
        _apply_loudness(result, dict(loudness_run or {}))

    result["analysis_depth"] = "deep" if "loudness" in result["completed_capabilities"] else "fast"
    result["cache"].update({"hit": False, "analyzer_version": ANALYZER_VERSION, "created_at": _utc_now()})
    result["performance"]["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 3)
    try:
        atomic_write_json(cache_path, result)
    except OSError as exc:
        result["warnings"].append(f"Audio Intelligence cache write failed: {exc}")
    return result
