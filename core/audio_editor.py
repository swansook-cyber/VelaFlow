from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from core.file_naming import ensure_unique_path, sanitize_filename
from core.paths import ROOT
from core.project_io import safe_name
from core.real_clip_pipeline import find_ffmpeg, probe_media


AUDIO_EDITOR_CUT_MODES = ["Lossless Quick Cut", "Precise Cut"]
AUDIO_EDITOR_FADE_OPTIONS = {
    "Off": 0.0,
    "0.1 second": 0.1,
    "0.25 second": 0.25,
    "0.5 second": 0.5,
    "1.0 second": 1.0,
}
HOOK_DURATION_PRESETS = {
    "Custom": 0.0,
    "TikTok 15 seconds": 15.0,
    "TikTok 30 seconds": 30.0,
    "Reels 15 seconds": 15.0,
    "Shorts 30 seconds": 30.0,
}


def format_timecode(seconds: float) -> str:
    total_ms = max(0, int(round(float(seconds or 0) * 1000)))
    minutes, rem_ms = divmod(total_ms, 60_000)
    secs, millis = divmod(rem_ms, 1000)
    return f"{minutes:02d}:{secs:02d}.{millis:03d}"


def build_audio_editor_project_id(original_name: str) -> str:
    stem = sanitize_filename(Path(original_name).stem or "audio_editor")
    return safe_name(f"{stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")


def validate_audio_editor_input(path: str | Path, *, mime_type: str = "", max_upload_mb: int = 200) -> dict[str, Any]:
    source = Path(path)
    ext = source.suffix.lower().lstrip(".")
    if not source.is_file():
        return {"ok": False, "error": "missing_audio", "message": "Audio file missing"}
    if ext not in {"mp3", "wav"}:
        return {"ok": False, "error": "unsupported_format", "message": "Audio Editor V1 supports MP3 input; WAV is accepted only for compatibility."}
    if mime_type and not any(token in mime_type.lower() for token in ["audio", "mpeg", "mp3", "wav", "wave", "octet-stream"]):
        return {"ok": False, "error": "unsupported_mime", "message": "Unsupported audio MIME type"}
    size_mb = source.stat().st_size / (1024 * 1024)
    if size_mb > max_upload_mb:
        return {"ok": False, "error": "file_too_large", "message": f"Audio exceeds the {max_upload_mb} MB upload limit"}
    return {"ok": True, "error": "", "message": "", "format": ext, "size_mb": round(size_mb, 3)}


def validate_audio_selection(start: float, end: float, source_duration: float, *, minimum_seconds: float = 1.0) -> dict[str, Any]:
    try:
        start_value = float(start)
        end_value = float(end)
        duration_value = float(source_duration)
    except (TypeError, ValueError):
        return {"ok": False, "error": "invalid_selection", "message": "Start, end, and duration must be numeric"}
    if duration_value <= 0:
        return {"ok": False, "error": "invalid_source_duration", "message": "Audio duration is unavailable"}
    if start_value < 0:
        return {"ok": False, "error": "start_before_zero", "message": "Start time cannot be negative"}
    if end_value > duration_value:
        return {"ok": False, "error": "end_beyond_duration", "message": "End time is beyond the source duration"}
    if start_value >= end_value:
        return {"ok": False, "error": "start_after_end", "message": "Start time must be before end time"}
    if end_value - start_value < minimum_seconds:
        return {"ok": False, "error": "selection_too_short", "message": f"Selection must be at least {minimum_seconds:.1f} second"}
    return {"ok": True, "error": "", "message": "", "selection_duration": round(end_value - start_value, 3)}


def effective_cut_mode(source_path: str | Path, cut_mode: str, fade_in: float = 0.0, fade_out: float = 0.0) -> tuple[str, list[str]]:
    warnings: list[str] = []
    mode = cut_mode if cut_mode in AUDIO_EDITOR_CUT_MODES else "Lossless Quick Cut"
    if fade_in > 0 or fade_out > 0:
        mode = "Precise Cut"
        warnings.append("Fade enabled: re-encoding required.")
    if Path(source_path).suffix.lower() != ".mp3" and mode == "Lossless Quick Cut":
        mode = "Precise Cut"
        warnings.append("WAV input requires MP3 encoding for Audio Editor V1 output.")
    return mode, warnings


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
) -> list[str]:
    duration = max(0.0, float(end_time) - float(start_time))
    source = str(source_path)
    output = str(output_path)
    mode, _warnings = effective_cut_mode(source_path, cut_mode, fade_in, fade_out)
    base = [ffmpeg, "-y", "-ss", f"{float(start_time):.3f}", "-i", source, "-t", f"{duration:.3f}", "-map", "0:a:0", "-map_metadata", "0"]
    if mode == "Lossless Quick Cut":
        return [*base, "-c:a", "copy", output]
    args = [*base, "-c:a", "libmp3lame", "-b:a", "320k", "-minrate", "320k", "-maxrate", "320k", "-write_xing", "0"]
    if channels and int(channels) != 1:
        args += ["-ac", "2"]
    if sample_rate in {32000, 44100, 48000}:
        args += ["-ar", str(sample_rate)]
    filters: list[str] = []
    if fade_in > 0:
        filters.append(f"afade=t=in:st=0:d={float(fade_in):.3f}")
    if fade_out > 0:
        fade_start = max(0.0, duration - float(fade_out))
        filters.append(f"afade=t=out:st={fade_start:.3f}:d={float(fade_out):.3f}")
    if filters:
        args += ["-af", ",".join(filters)]
    return [*args, output]


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


def _report_text(report: dict[str, Any]) -> str:
    rows = [
        "VELAFLOW AUDIO EDIT REPORT",
        "",
        f"Original filename: {report.get('original_filename', '')}",
        f"Input duration: {report.get('input_duration', 0)}",
        f"Input format: {report.get('input_format', '')}",
        f"Input codec: {report.get('input_codec', '')}",
        f"Input bitrate: {report.get('input_bitrate', '')}",
        f"Input sample rate: {report.get('input_sample_rate', '')}",
        f"Selected start: {report.get('selected_start', '')}",
        f"Selected end: {report.get('selected_end', '')}",
        f"Selection duration: {report.get('selection_duration', '')}",
        f"Cut mode: {report.get('cut_mode', '')}",
        f"Fade In: {report.get('fade_in', '')}",
        f"Fade Out: {report.get('fade_out', '')}",
        f"Output filename: {report.get('output_filename', '')}",
        f"Output codec: {report.get('output_codec', '')}",
        f"Output bitrate: {report.get('output_bitrate', '')}",
        f"Re-encoded: {'Yes' if report.get('reencoded') else 'No'}",
        f"Processing date and time: {report.get('processing_date_time', '')}",
        "Warnings: " + (", ".join(report.get("warnings", [])) if report.get("warnings") else "None"),
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
    safe_stem = sanitize_filename(output_name or f"{source.stem}_hook")
    output_path = ensure_unique_path(output_dir / f"{safe_stem}.mp3")
    mode, warnings = effective_cut_mode(source, cut_mode, fade_in, fade_out)
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
    )
    result = _run(command, timeout=180)
    if not result.get("ok") or not output_path.is_file():
        error_text = result.get("output", "audio_edit_failed")
        error = "libmp3lame_unavailable" if "libmp3lame" in error_text.lower() and "unknown encoder" in error_text.lower() else "audio_edit_failed"
        return {"ok": False, "message": error_text[:600], "data": {"command": command}, "error": error}
    output_probe = probe_media(output_path, ffmpeg_path=ffmpeg)
    report = {
        "ok": True,
        "project_id": project_id,
        "original_filename": source.name,
        "input_duration": probe.get("duration", 0),
        "input_format": validation.get("format", ""),
        "input_codec": probe.get("audio_codec", ""),
        "input_bitrate": probe.get("audio_bit_rate", ""),
        "input_sample_rate": probe.get("sample_rate", ""),
        "input_channels": probe.get("channels", ""),
        "selected_start": float(start_time),
        "selected_end": float(end_time),
        "selection_duration": selection.get("selection_duration", 0),
        "cut_mode": mode,
        "fade_in": float(fade_in),
        "fade_out": float(fade_out),
        "output_filename": output_path.name,
        "output_codec": output_probe.get("audio_codec", "mp3"),
        "output_bitrate": "source stream copy" if mode == "Lossless Quick Cut" else "320 kbps CBR",
        "output_sample_rate": output_probe.get("sample_rate", ""),
        "output_channels": output_probe.get("channels", ""),
        "reencoded": mode != "Lossless Quick Cut",
        "ffmpeg_command": command,
        "processing_date_time": datetime.now().isoformat(timespec="seconds"),
        "warnings": warnings,
        "preview": preview,
    }
    report_path = reports_dir / "edit_report.json"
    report_txt_path = reports_dir / "edit_report.txt"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report_txt_path.write_text(_report_text(report), encoding="utf-8")
    zip_path = ensure_unique_path(base_dir / f"{safe_stem}_audio_edit_package.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in [source_copy, output_path, report_path, report_txt_path]:
            if file_path.is_file():
                archive.write(file_path, str(file_path.relative_to(base_dir)))
    return {
        "ok": True,
        "message": "Hook MP3 ready",
        "data": {
            "project_id": project_id,
            "original_audio": str(source_copy),
            "hook_mp3": str(output_path),
            "output_mp3": str(output_path),
            "report_path": str(report_path),
            "report_txt_path": str(report_txt_path),
            "zip_path": str(zip_path),
            "report": report,
        },
        "error": "",
    }
