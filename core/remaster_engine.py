from __future__ import annotations

import json
import math
import shutil
import subprocess
import zipfile
from array import array
from datetime import datetime
from pathlib import Path
from typing import Any

from core.file_naming import build_asset_export_filename, ensure_unique_path, sanitize_filename
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
REMASTER_RECOMMENDATION_MODES = ["Auto Recommended", "Manual", "Custom / Advanced"]

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


def _confidence_label(score: int) -> str:
    if score >= 76:
        return "High"
    if score >= 55:
        return "Medium"
    return "Low"


def recommend_remaster_preset_from_metadata(metadata: dict[str, Any] | str | None) -> dict[str, Any]:
    if isinstance(metadata, dict):
        text = " ".join(str(value) for value in metadata.values() if isinstance(value, (str, int, float, list, tuple, dict))).lower()
    else:
        text = str(metadata or "").lower()
    groups = {
        "Loud Modern": ["cheer", "stadium", "crowd", "chant", "high energy", "ตะโกน", "เชียร์", "สนาม", "พลัง", "มันส์"],
        "Modern Pop": ["edm", "trap", "dance", "808", "sub bass", "heavy bass", "electronic", "club", "เบสหนัก", "แดนซ์"],
        "Pop Rock": ["rock", "live band", "guitar", "strong snare", "drum kit", "pop rock", "ร็อก", "กีตาร์", "วงดนตรี"],
        "Vocal Focus": ["podcast", "narration", "spoken", "voice", "speech", "talk", "พอดแคสต์", "เล่าเรื่อง", "พูด", "บรรยาย"],
        "Warm Acoustic": ["ballad", "soft vocal", "acoustic", "emotional", "piano", "warm", "อะคูสติก", "อบอุ่น", "บัลลาด", "เศร้า"],
    }
    scores: dict[str, int] = {}
    reasons: dict[str, list[str]] = {}
    for preset, keywords in groups.items():
        matched = [keyword for keyword in keywords if keyword in text]
        scores[preset] = len(matched)
        reasons[preset] = matched
    best_preset = max(scores, key=lambda key: scores[key]) if scores else "Streaming Balanced"
    if scores.get(best_preset, 0) <= 0:
        best_preset = "Streaming Balanced"
    confidence_score = min(92, 42 + scores.get(best_preset, 0) * 17)
    reason_lines = [f"Project metadata contains: {', '.join(reasons.get(best_preset, [])[:5])}"] if reasons.get(best_preset) else ["Project metadata is mixed or limited; balanced preset is safest."]
    return {
        "source": "project_metadata",
        "recommended_preset": best_preset,
        "selected_preset": best_preset,
        "confidence": _confidence_label(confidence_score),
        "confidence_score": confidence_score,
        "reasons": reason_lines,
        "metrics": {"metadata_keyword_matches": scores, "matched_keywords": reasons.get(best_preset, [])},
        "analyzed_at": datetime.now().isoformat(timespec="seconds"),
    }


def _decode_analysis_pcm(path: Path, ffmpeg: str, *, sample_rate: int = 8000, max_duration: float = 360.0) -> dict[str, Any]:
    args = [ffmpeg, "-v", "error", "-i", str(path), "-map", "0:a:0", "-t", f"{max_duration:.3f}", "-ac", "1", "-ar", str(sample_rate), "-f", "s16le", "-"]
    try:
        proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    except Exception as exc:
        return {"ok": False, "error": "decode_failed", "message": str(exc), "command": args}
    if proc.returncode != 0 or not proc.stdout:
        return {"ok": False, "error": "decode_failed", "message": (proc.stderr or b"Audio analysis failed").decode("utf-8", errors="replace")[:600], "command": args}
    samples = array("h")
    samples.frombytes(proc.stdout)
    return {"ok": bool(samples), "samples": samples, "sample_rate": sample_rate, "command": args}


def analyze_audio_for_remaster_recommendation(source_audio_path: str | Path, *, ffmpeg_path: str = "", max_upload_mb: int = 200) -> dict[str, Any]:
    source = Path(source_audio_path)
    validation = validate_remaster_input(source, max_upload_mb=max_upload_mb)
    if not validation.get("ok"):
        return {"ok": False, "message": validation.get("message", "Invalid audio"), "error": validation.get("error", "invalid_audio")}
    ffmpeg = ffmpeg_path or find_ffmpeg()
    if not ffmpeg:
        return {"ok": False, "message": "FFmpeg not found", "error": "missing_ffmpeg"}
    probe = probe_media(source, ffmpeg_path=ffmpeg)
    if not probe.get("ok") or not probe.get("has_audio", True):
        return {"ok": False, "message": "Invalid or corrupt audio file", "error": "invalid_audio", "data": {"probe": probe}}
    decoded = _decode_analysis_pcm(source, ffmpeg)
    if not decoded.get("ok"):
        return {"ok": False, "message": decoded.get("message", "Audio analysis failed"), "error": decoded.get("error", "analysis_failed")}
    samples = decoded["samples"]
    normalized = [sample / 32768.0 for sample in samples]
    duration = float(probe.get("duration") or (len(samples) / float(decoded["sample_rate"])))
    rms = math.sqrt(sum(value * value for value in normalized) / max(1, len(normalized)))
    peak = max(abs(value) for value in normalized) if normalized else 0.0
    silent = sum(1 for value in normalized if abs(value) < 0.01) / max(1, len(normalized))
    diffs = [abs(normalized[idx] - normalized[idx - 1]) for idx in range(1, len(normalized))]
    transient_density = min(1.0, (sum(1 for value in diffs if value > 0.12) / max(1, len(diffs))) * 8)
    zero_cross = sum(1 for idx in range(1, len(normalized)) if (normalized[idx] >= 0) != (normalized[idx - 1] >= 0)) / max(1, len(normalized))
    crest_factor = peak / max(rms, 0.0001)
    bass_energy = max(0.0, min(1.0, rms * (1.6 - min(1.2, zero_cross * 18))))
    high_energy = max(0.0, min(1.0, rms * min(1.8, zero_cross * 22)))
    mid_energy = max(0.0, min(1.0, rms * (1.2 - abs(zero_cross - 0.055) * 5)))
    dynamic_range = max(0.0, min(1.0, crest_factor / 12.0))
    clipping_risk = peak > 0.985
    metrics = {
        "duration": round(duration, 3),
        "integrated_loudness": "estimated/unavailable",
        "peak": round(peak, 4),
        "dynamic_range": round(dynamic_range, 4),
        "rms_energy": round(rms, 4),
        "bass_energy": round(bass_energy, 4),
        "mid_energy": round(mid_energy, 4),
        "high_energy": round(high_energy, 4),
        "transient_density": round(transient_density, 4),
        "silence_ratio": round(silent, 4),
        "stereo_information": "available from source probe" if int(probe.get("channels") or 1) > 1 else "mono or unavailable",
        "vocal_range_presence": round(mid_energy, 4),
        "crest_factor": round(crest_factor, 3),
        "clipping_risk": bool(clipping_risk),
    }
    reasons: list[str] = []
    preset = "Streaming Balanced"
    score = 48
    if rms < 0.03 or silent > 0.65:
        preset, score = "Streaming Balanced", 42
        reasons.append("Low-confidence input: quiet or silence-heavy audio; balanced preset is safest.")
    elif mid_energy > bass_energy * 1.25 and transient_density < 0.28 and silent > 0.18:
        preset, score = "Vocal Focus", 70
        reasons += ["Dominant speech/vocal range", "Moderate pauses", "Lower sub-bass content"]
    elif bass_energy > mid_energy * 1.18 and rms > 0.12 and high_energy > 0.08:
        preset, score = "Modern Pop", 78
        reasons += ["Dense low-frequency content", "Consistent loudness", "Bright modern profile"]
    elif transient_density > 0.32 and mid_energy >= bass_energy * 0.85:
        preset, score = "Pop Rock", 73
        reasons += ["Strong transient density", "Midrange energy suggests guitars/drums", "Wider dynamics than dense EDM"]
    elif rms > 0.16 and transient_density > 0.2 and silent < 0.18:
        preset, score = "Loud Modern", 80
        reasons += ["High overall energy", "Low silence ratio", "Suitable for loud social playback"]
    elif mid_energy > bass_energy and dynamic_range > 0.45:
        preset, score = "Warm Acoustic", 68
        reasons += ["Moderate loudness", "Vocal/acoustic-friendly midrange", "Softer dynamic profile"]
    else:
        reasons.append("Audio characteristics are mixed; balanced preset is safest.")
    recommendation = {
        "source": "audio_analysis",
        "recommended_preset": preset,
        "selected_preset": preset,
        "confidence": _confidence_label(score),
        "confidence_score": score,
        "reasons": reasons,
        "metrics": metrics,
        "analyzed_at": datetime.now().isoformat(timespec="seconds"),
    }
    return {"ok": True, "data": recommendation, "error": ""}


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
    recommendation = report.get("remaster_recommendation") or {}
    if recommendation:
        lines += [
            "",
            "Preset Recommendation:",
            f"Input source: {recommendation.get('input_source', '')}",
            f"Recommendation source: {recommendation.get('source', '')}",
            f"Recommended preset: {recommendation.get('recommended_preset', '')}",
            f"Confidence: {recommendation.get('confidence', '')}",
            f"User-selected preset: {recommendation.get('selected_preset', report.get('selected_preset', ''))}",
            f"Recommendation overridden: {'Yes' if recommendation.get('overridden') else 'No'}",
            "Why this preset:",
            *[f"- {reason}" for reason in recommendation.get("reasons", [])],
        ]
    return "\n".join(lines)


def remaster_song_audio(
    source_audio_path: str | Path,
    *,
    project_name: str = "remaster_project",
    remaster_style: str = "Streaming Balanced",
    ffmpeg_path: str = "",
    max_upload_mb: int = 200,
    recommendation_data: dict[str, Any] | None = None,
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
    wav_path = output_dir / build_asset_export_filename(project_name, source.name, "Master", "wav")
    mp3_path = output_dir / build_asset_export_filename(project_name, source.name, "Master", "mp3")
    report_path = reports_dir / build_asset_export_filename(project_name, source.name, "Remaster_Report", "json")
    report_txt_path = reports_dir / build_asset_export_filename(project_name, source.name, "Remaster_Report", "txt")
    legacy_report_path = reports_dir / "mastering_report.json"
    zip_path = ensure_unique_path(base_dir / build_asset_export_filename(project_name, source.name, "Remaster_Package", "zip"))
    converted_path = output_dir / "source_converted_48k_24bit.wav"
    style = _normalize_style(remaster_style)
    style_config = STYLE_FILTERS[style]
    recommendation = dict(recommendation_data or {})
    if recommendation:
        recommendation["selected_preset"] = style
        recommendation["overridden"] = bool(recommendation.get("recommended_preset") and recommendation.get("recommended_preset") != style)
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
            "export_name": project_name,
            "source_path": str(source_copy),
            "mastered_wav": str(wav_path),
            "source_probe": source_probe,
            "wav_probe": wav_probe,
            "max_volume_db": max_volume,
            "no_clipping_above_0db": no_clipping,
            "remaster_recommendation": recommendation,
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
        "export_name": project_name,
        "input_format": input_validation.get("format"),
        "input_sample_rate": source_probe.get("sample_rate", "unknown"),
        "input_duration": source_probe.get("duration", 0),
        "input_channels": source_probe.get("channels", "unknown"),
        "input_loudness": "estimated/unavailable",
        "input_peak_level": max_volume if max_volume is not None else "estimated/unavailable",
        "selected_preset": style,
        "remaster_recommendation": recommendation,
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
            "export_name": project_name,
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
