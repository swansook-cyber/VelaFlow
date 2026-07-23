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
from core.real_clip_pipeline import ensure_parent_dir, find_ffmpeg, probe_media


REMASTER_STYLES = [
    "Streaming Balanced",
    "Modern Pop",
    "Pop Rock",
    "Emotional Ballad",
    "Warm Acoustic",
    "Vocal Focus",
    "Cinematic",
    "Loud Modern",
]

LEGACY_STYLE_ALIASES = {
    "Vela Moon Emotional Pop Rock": "Pop Rock",
    "Spotify Pop Loud": "Modern Pop",
    "TikTok Loud Master": "Loud Modern",
    "Warm Vocal": "Vocal Focus",
    "Acoustic Smooth": "Warm Acoustic",
    "Podcast Voice Clean": "Vocal Focus",
    "Spotify Balanced": "Streaming Balanced",
    "Spotify Clean": "Streaming Balanced",
    "TikTok Loud": "Loud Modern",
    "YouTube Clean": "Streaming Balanced",
    "Cinematic Wide": "Cinematic",
    "Bass Boost": "Modern Pop",
    "Emotional Soft": "Emotional Ballad",
    "Soft Emotional": "Emotional Ballad",
}

STYLE_FILTERS: dict[str, dict[str, Any]] = {
    "Streaming Balanced": {
        "filters": "adeclick,highpass=f=28,lowpass=f=18500,equalizer=f=3200:t=q:w=1.0:g=0.8,acompressor=threshold=-18dB:ratio=1.7:attack=12:release=160,loudnorm=I=-14:TP=-1.0:LRA=10,alimiter=level_out=0.93:limit=0.93",
        "target_lufs": "-14 LUFS estimated",
        "true_peak": "-1 dBTP estimated",
        "summary": "clean streaming loudness, gentle EQ, safe limiting",
    },
    "Modern Pop": {
        "filters": "adeclick,highpass=f=30,lowpass=f=18800,equalizer=f=90:t=q:w=0.9:g=0.8,equalizer=f=2800:t=q:w=1.0:g=1.1,acompressor=threshold=-17dB:ratio=1.9:attack=10:release=145,loudnorm=I=-12.5:TP=-1.0:LRA=9,alimiter=level_out=0.93:limit=0.93",
        "target_lufs": "-12.5 LUFS estimated",
        "true_peak": "-1 dBTP estimated",
        "summary": "modern pop loudness with controlled vocal presence",
    },
    "Pop Rock": {
        "filters": "adeclick,highpass=f=30,lowpass=f=18500,equalizer=f=180:t=q:w=0.9:g=0.8,equalizer=f=2800:t=q:w=1.0:g=1.4,equalizer=f=6800:t=q:w=1.1:g=0.6,acompressor=threshold=-18dB:ratio=1.8:attack=10:release=150,loudnorm=I=-13:TP=-1.0:LRA=9,alimiter=level_out=0.93:limit=0.93",
        "target_lufs": "-13 LUFS estimated",
        "true_peak": "-1 dBTP estimated",
        "summary": "guitar-forward pop rock polish with warm vocal focus",
    },
    "Emotional Ballad": {
        "filters": "adeclick,highpass=f=24,lowpass=f=18000,equalizer=f=800:t=q:w=1.2:g=-0.8,equalizer=f=4500:t=q:w=1.0:g=0.9,acompressor=threshold=-20dB:ratio=1.4:attack=18:release=220,loudnorm=I=-15.5:TP=-1.3:LRA=13,alimiter=level_out=0.94:limit=0.94",
        "target_lufs": "-15.5 LUFS estimated",
        "true_peak": "-1.3 dBTP estimated",
        "summary": "soft dynamics for emotional ballads",
    },
    "Warm Acoustic": {
        "filters": "adeclick,highpass=f=26,lowpass=f=18000,equalizer=f=220:t=q:w=0.9:g=0.8,equalizer=f=3500:t=q:w=1.0:g=0.9,acompressor=threshold=-19dB:ratio=1.45:attack=16:release=190,loudnorm=I=-15:TP=-1.2:LRA=12,alimiter=level_out=0.94:limit=0.94",
        "target_lufs": "-15 LUFS estimated",
        "true_peak": "-1.2 dBTP estimated",
        "summary": "warm acoustic tone with light compression",
    },
    "Vocal Focus": {
        "filters": "adeclick,highpass=f=45,lowpass=f=17000,equalizer=f=1800:t=q:w=1.1:g=0.8,equalizer=f=4200:t=q:w=1.0:g=1.4,acompressor=threshold=-19dB:ratio=1.8:attack=10:release=150,loudnorm=I=-14:TP=-1.1:LRA=9,alimiter=level_out=0.93:limit=0.93",
        "target_lufs": "-14 LUFS estimated",
        "true_peak": "-1.1 dBTP estimated",
        "summary": "clearer vocal center and safe loudness",
    },
    "Cinematic": {
        "filters": "adeclick,highpass=f=25,lowpass=f=19000,equalizer=f=120:t=q:w=0.9:g=0.7,equalizer=f=4500:t=q:w=1.1:g=0.5,aecho=0.35:0.25:12:0.06,loudnorm=I=-15:TP=-1.3:LRA=12,alimiter=level_out=0.94:limit=0.94",
        "target_lufs": "-15 LUFS estimated",
        "true_peak": "-1.3 dBTP estimated",
        "summary": "wide cinematic space without aggressive loudness",
    },
    "Loud Modern": {
        "filters": "adeclick,highpass=f=35,lowpass=f=18500,equalizer=f=2500:t=q:w=1.1:g=1.5,equalizer=f=9000:t=q:w=1.1:g=0.7,acompressor=threshold=-16dB:ratio=2.2:attack=8:release=120,loudnorm=I=-11:TP=-1.0:LRA=8,alimiter=level_out=0.92:limit=0.92",
        "target_lufs": "-11 LUFS estimated",
        "true_peak": "-1 dBTP estimated",
        "summary": "louder modern master with clipping protection",
    },
}


def _run(args: list[str], timeout: int = 180) -> dict[str, Any]:
    try:
        proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return {"ok": proc.returncode == 0, "returncode": proc.returncode, "output": proc.stdout or "", "command": args}
    except FileNotFoundError as exc:
        return {"ok": False, "returncode": -1, "output": f"missing_ffmpeg: {exc}", "command": args}
    except Exception as exc:
        return {"ok": False, "returncode": -1, "output": str(exc), "command": args}


def _max_volume_db(ffmpeg: str, path: Path) -> float | None:
    result = _run([ffmpeg, "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"], timeout=120)
    for line in result.get("output", "").splitlines():
        if "max_volume:" in line:
            try:
                return float(line.split("max_volume:", 1)[1].strip().split()[0])
            except Exception:
                return None
    return None


def _normalize_style(style: str) -> str:
    selected = LEGACY_STYLE_ALIASES.get(style, style)
    return selected if selected in STYLE_FILTERS else "Streaming Balanced"


def _source_ext(path: Path) -> str:
    return path.suffix.lower().lstrip(".")


def validate_remaster_input(path: str | Path, *, max_upload_mb: int = 200) -> dict[str, Any]:
    source = Path(path)
    ext = _source_ext(source)
    if not source.is_file():
        return {"ok": False, "error": "missing_audio", "message": "Source audio missing"}
    if ext not in {"mp3", "wav"}:
        return {"ok": False, "error": "unsupported_format", "message": "Only MP3 and WAV are supported in Remaster Studio V1"}
    size_mb = source.stat().st_size / (1024 * 1024)
    if size_mb > max_upload_mb:
        return {"ok": False, "error": "file_too_large", "message": f"Audio exceeds the {max_upload_mb} MB upload limit"}
    return {"ok": True, "error": "", "message": "", "format": ext, "size_mb": round(size_mb, 3)}


def build_remaster_project_id(original_name: str) -> str:
    stem = sanitize_filename(Path(original_name).stem or "remaster")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return safe_name(f"{stem}_{stamp}")


def _report_text(report: dict[str, Any]) -> str:
    lines = [
        "VELAFLOW REMASTER REPORT",
        "",
        f"Original filename: {report.get('original_filename', '')}",
        f"Input format: {report.get('input_format', '')}",
        f"Input sample rate: {report.get('input_sample_rate', 'unknown')}",
        f"Input duration: {report.get('input_duration', 0)}",
        f"Selected preset: {report.get('selected_preset', '')}",
        "",
        "Processing steps applied:",
        *[f"- {step}" for step in report.get("processing_steps_applied", [])],
        "",
        f"Output WAV settings: {report.get('output_wav_settings', {})}",
        f"Output MP3 settings: {report.get('output_mp3_settings', {})}",
        f"Loudness result: {report.get('loudness_result', '')}",
        f"Peak result: {report.get('peak_result', '')}",
        "Warnings: " + (", ".join(report.get("warnings", [])) if report.get("warnings") else "None"),
        f"Processing date/time: {report.get('processing_date_time', '')}",
    ]
    return "\n".join(lines)


def remaster_song_audio(
    source_audio_path: str | Path,
    *,
    project_name: str = "remaster_project",
    remaster_style: str = "Streaming Balanced",
    ffmpeg_path: str = "",
    max_upload_mb: int = 200,
) -> dict[str, Any]:
    source = Path(source_audio_path)
    ffmpeg = ffmpeg_path or find_ffmpeg()
    input_validation = validate_remaster_input(source, max_upload_mb=max_upload_mb)
    if not input_validation.get("ok"):
        return {"ok": False, "message": input_validation.get("message", "Invalid audio"), "data": {"validation": input_validation}, "error": input_validation.get("error", "invalid_audio")}
    if not ffmpeg:
        return {
            "ok": False,
            "message": "FFmpeg not found. Install on Debian with: sudo apt-get update && sudo apt-get install -y ffmpeg",
            "data": {"setup_hint": "sudo apt-get update && sudo apt-get install -y ffmpeg"},
            "error": "missing_ffmpeg",
        }

    project_id = build_remaster_project_id(project_name or source.stem)
    base_dir = ROOT / "exports" / "remaster" / project_id
    original_dir = base_dir / "original"
    output_dir = base_dir / "output"
    reports_dir = base_dir / "reports"
    original_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    source_copy = original_dir / f"source_audio.{_source_ext(source)}"
    shutil.copy2(source, source_copy)
    safe_stem = sanitize_filename(source.stem or project_name or "song")
    wav_path = output_dir / f"{safe_stem}_master.wav"
    mp3_path = output_dir / f"{safe_stem}_master.mp3"
    report_path = reports_dir / "remaster_report.json"
    report_txt_path = reports_dir / "remaster_report.txt"
    legacy_report_path = reports_dir / "mastering_report.json"
    zip_path = ensure_unique_path(base_dir / f"{safe_stem}_remaster_package.zip")
    converted_path = output_dir / "source_converted_48k_24bit.wav"
    style = _normalize_style(remaster_style)
    style_config = STYLE_FILTERS[style]
    source_probe = probe_media(source, ffmpeg_path=ffmpeg)
    if not source_probe.get("ok") or not source_probe.get("has_audio", True):
        return {"ok": False, "message": "Invalid or corrupt audio file", "data": {"source_probe": source_probe}, "error": "invalid_audio"}
    convert = _run([ffmpeg, "-y", "-i", str(source), "-vn", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", str(converted_path)])
    if not convert.get("ok"):
        return {"ok": False, "message": "Audio conversion failed", "data": {"command": convert.get("command", [])}, "error": "audio_convert_failed"}

    filters = style_config["filters"]
    wav = _run([ffmpeg, "-y", "-i", str(converted_path), "-vn", "-af", filters, "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", str(wav_path)])
    wav_probe = probe_media(wav_path, ffmpeg_path=ffmpeg)
    max_volume = _max_volume_db(ffmpeg, wav_path) if wav_path.is_file() else None
    no_clipping = max_volume is None or max_volume <= 0.0
    if not wav.get("ok") or not wav_probe.get("ok") or not no_clipping:
        report = {
            "ok": False,
            "style": style,
            "source_path": str(source_copy),
            "mastered_wav": str(wav_path),
            "source_probe": source_probe,
            "wav_probe": wav_probe,
            "max_volume_db": max_volume,
            "no_clipping_above_0db": no_clipping,
            "error": "master_wav_failed" if wav.get("ok") else wav.get("output", "master_wav_failed")[:1200],
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        ensure_parent_dir(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        ensure_parent_dir(legacy_report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        ensure_parent_dir(report_txt_path).write_text(_report_text(report), encoding="utf-8")
        return {"ok": False, "message": "Mastered WAV failed validation", "data": {"report_path": str(report_path), "report": report}, "error": "master_wav_failed"}

    mp3 = _run([ffmpeg, "-y", "-i", str(wav_path), "-vn", "-c:a", "libmp3lame", "-b:a", "320k", "-minrate", "320k", "-maxrate", "320k", "-write_xing", "0", str(mp3_path)])
    mp3_probe = probe_media(mp3_path, ffmpeg_path=ffmpeg) if mp3_path.is_file() else {"ok": False}
    duration_delta = abs(float(source_probe.get("duration") or 0) - float(wav_probe.get("duration") or 0))
    warnings: list[str] = []
    if max_volume is None:
        warnings.append("Peak level is estimated because exact true-peak measurement is unavailable.")
    if not mp3.get("ok"):
        warnings.append("MP3 export failed.")
    report = {
        "ok": True,
        "project_id": project_id,
        "original_filename": source.name,
        "input_format": input_validation.get("format"),
        "input_sample_rate": source_probe.get("sample_rate", "unknown"),
        "input_duration": source_probe.get("duration", 0),
        "input_channels": source_probe.get("channels", "unknown"),
        "input_loudness": "estimated/unavailable",
        "input_peak_level": max_volume if max_volume is not None else "estimated/unavailable",
        "selected_preset": style,
        "processing_steps_applied": [
            "Input validation",
            "Source copy preserved in original/",
            "48 kHz stereo PCM 24-bit conversion",
            "DC click/pop cleanup where detectable",
            "High-pass filtering",
            "Corrective EQ",
            "Gentle compression",
            "Preset stereo/space enhancement where configured",
            "Loudness normalization",
            "True-peak style limiting",
            "WAV + MP3 export",
        ],
        "output_wav_settings": {"format": "WAV", "codec": "pcm_s24le", "bit_depth": "24-bit", "sample_rate_hz": 48000, "channels": "stereo", "lossless": True},
        "output_mp3_settings": {"format": "MP3", "codec": "libmp3lame", "bitrate": "320 kbps", "mode": "CBR", "channels": "stereo"},
        "loudness_result": style_config.get("target_lufs", "estimated/unavailable"),
        "peak_result": style_config.get("true_peak", "estimated/unavailable") if max_volume is None else f"{max_volume} dB max_volume (true peak estimated)",
        "warnings": warnings,
        "processing_date_time": datetime.now().isoformat(timespec="seconds"),
        "style": style,
        "source_path": str(source_copy),
        "converted_wav": str(converted_path),
        "mastered_wav": str(wav_path),
        "mp3_preview": str(mp3_path) if mp3_path.is_file() else "",
        "mastered_mp3": str(mp3_path) if mp3_path.is_file() else "",
        "source_probe": source_probe,
        "wav_probe": wav_probe,
        "mp3_probe": mp3_probe,
        "duration_matches_original": duration_delta <= 0.25,
        "duration_delta_seconds": round(duration_delta, 3),
        "max_volume_db": max_volume,
        "no_clipping_above_0db": no_clipping,
        "filters": filters,
        "preset_summary": style_config.get("summary", ""),
        "external_api_used": False,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    ensure_parent_dir(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    ensure_parent_dir(legacy_report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    ensure_parent_dir(report_txt_path).write_text(_report_text(report), encoding="utf-8")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in [source_copy, wav_path, mp3_path, report_path, report_txt_path]:
            if path.is_file():
                archive.write(path, str(path.relative_to(base_dir)))
    return {
        "ok": True,
        "message": "Remaster ready",
        "data": {
            "project_id": project_id,
            "original_audio": str(source_copy),
            "mastered_wav": str(wav_path),
            "mp3_preview": str(mp3_path) if mp3_path.is_file() and mp3.get("ok") else "",
            "mastered_mp3": str(mp3_path) if mp3_path.is_file() and mp3.get("ok") else "",
            "report_path": str(report_path),
            "report_txt_path": str(report_txt_path),
            "zip_path": str(zip_path),
            "report": report,
        },
        "error": "",
    }
