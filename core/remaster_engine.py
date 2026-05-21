from __future__ import annotations

import json
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from core.paths import workflow_project_root
from core.project_io import safe_name
from core.real_clip_pipeline import ensure_parent_dir, find_ffmpeg, probe_media


REMASTER_STYLES = [
    "TikTok Loud",
    "Spotify Balanced",
    "YouTube Clean",
    "Warm Vocal",
    "Cinematic Wide",
    "Emotional Soft",
]


STYLE_FILTERS = {
    "Spotify Balanced": "highpass=f=28,lowpass=f=18500,equalizer=f=3200:t=q:w=1.0:g=0.8,acompressor=threshold=-18dB:ratio=1.7:attack=12:release=160,loudnorm=I=-14:TP=-1.2:LRA=10,alimiter=level_in=1:level_out=0.93:limit=0.93",
    "Spotify Clean": "highpass=f=28,lowpass=f=18500,equalizer=f=3200:t=q:w=1.0:g=0.8,acompressor=threshold=-18dB:ratio=1.7:attack=12:release=160,loudnorm=I=-14:TP=-1.2:LRA=10,alimiter=level_in=1:level_out=0.93:limit=0.93",
    "TikTok Loud": "highpass=f=35,equalizer=f=2500:t=q:w=1.1:g=1.8,equalizer=f=9000:t=q:w=1.1:g=0.8,acompressor=threshold=-16dB:ratio=2.4:attack=8:release=120,loudnorm=I=-10:TP=-1.0:LRA=8,alimiter=level_in=1:level_out=0.92:limit=0.92",
    "YouTube Clean": "highpass=f=30,lowpass=f=19000,equalizer=f=3000:t=q:w=1.0:g=1.1,acompressor=threshold=-18dB:ratio=1.8:attack=10:release=150,loudnorm=I=-13:TP=-1.2:LRA=10,alimiter=level_in=1:level_out=0.93:limit=0.93",
    "Warm Vocal": "highpass=f=32,equalizer=f=180:t=q:w=0.8:g=1.2,equalizer=f=3200:t=q:w=1.0:g=1.8,equalizer=f=7200:t=q:w=1.1:g=0.7,acompressor=threshold=-19dB:ratio=1.6:attack=14:release=170,loudnorm=I=-13:TP=-1.1:LRA=10,alimiter=level_out=0.93:limit=0.93",
    "Cinematic Wide": "highpass=f=25,equalizer=f=120:t=q:w=0.9:g=1.0,equalizer=f=4500:t=q:w=1.1:g=0.7,aecho=0.45:0.35:16:0.10,loudnorm=I=-15:TP=-1.4:LRA=12,alimiter=level_out=0.94:limit=0.94",
    "Bass Boost": "highpass=f=28,bass=g=4:f=95,acompressor=threshold=-18dB:ratio=2.0:attack=10:release=160,loudnorm=I=-12:TP=-1.1:LRA=9,alimiter=limit=0.95",
    "Emotional Soft": "highpass=f=24,equalizer=f=800:t=q:w=1.2:g=-0.8,equalizer=f=4500:t=q:w=1.0:g=0.9,acompressor=threshold=-20dB:ratio=1.4:attack=18:release=220,loudnorm=I=-16:TP=-1.5:LRA=13,alimiter=level_out=0.94:limit=0.94",
    "Soft Emotional": "highpass=f=24,equalizer=f=800:t=q:w=1.2:g=-0.8,equalizer=f=4500:t=q:w=1.0:g=0.8,loudnorm=I=-16:TP=-1.5:LRA=13,alimiter=limit=0.97",
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


def remaster_song_audio(
    source_audio_path: str | Path,
    *,
    project_name: str = "remaster_project",
    remaster_style: str = "Spotify Balanced",
    ffmpeg_path: str = "",
) -> dict[str, Any]:
    source = Path(source_audio_path)
    ffmpeg = ffmpeg_path or find_ffmpeg()
    project_dir = workflow_project_root("song") / safe_name(project_name or "remaster_project")
    output_dir = project_dir / "exports" / "remaster"
    wav_path = output_dir / "mastered_song.wav"
    mp3_path = output_dir / "mastered_preview.mp3"
    report_path = output_dir / "mastering_report.json"
    legacy_report_path = output_dir / "remaster_report.json"
    zip_path = output_dir / "remaster_package.zip"
    converted_path = output_dir / "source_converted.wav"
    output_dir.mkdir(parents=True, exist_ok=True)
    style = remaster_style if remaster_style in STYLE_FILTERS else "Spotify Balanced"

    if not source.is_file():
        return {"ok": False, "message": "Source audio missing", "data": {}, "error": "missing_audio"}
    if not ffmpeg:
        return {"ok": False, "message": "FFmpeg not found", "data": {}, "error": "missing_ffmpeg"}

    source_probe = probe_media(source, ffmpeg_path=ffmpeg)
    convert = _run([ffmpeg, "-y", "-i", str(source), "-vn", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", str(converted_path)])
    if not convert.get("ok"):
        return {"ok": False, "message": "Audio conversion failed", "data": {"command": convert.get("command", [])}, "error": "audio_convert_failed"}

    filters = STYLE_FILTERS[style]
    wav = _run([ffmpeg, "-y", "-i", str(converted_path), "-vn", "-af", filters, "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", str(wav_path)])
    wav_probe = probe_media(wav_path, ffmpeg_path=ffmpeg)
    max_volume = _max_volume_db(ffmpeg, wav_path) if wav_path.is_file() else None
    no_clipping = max_volume is None or max_volume <= 0.0
    if not wav.get("ok") or not wav_probe.get("ok") or not no_clipping:
        report = {
            "ok": False,
            "style": style,
            "source_path": str(source),
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
        return {"ok": False, "message": "Mastered WAV failed validation", "data": {"report_path": str(report_path), "report": report}, "error": "master_wav_failed"}

    mp3 = _run([ffmpeg, "-y", "-i", str(wav_path), "-vn", "-c:a", "libmp3lame", "-b:a", "192k", str(mp3_path)])
    mp3_probe = probe_media(mp3_path, ffmpeg_path=ffmpeg) if mp3_path.is_file() else {"ok": False}
    duration_delta = abs(float(source_probe.get("duration") or 0) - float(wav_probe.get("duration") or 0))
    report = {
        "ok": True,
        "style": style,
        "source_path": str(source),
        "converted_wav": str(converted_path),
        "mastered_wav": str(wav_path),
        "mp3_preview": str(mp3_path) if mp3_path.is_file() else "",
        "source_probe": source_probe,
        "wav_probe": wav_probe,
        "mp3_probe": mp3_probe,
        "duration_matches_original": duration_delta <= 0.25,
        "duration_delta_seconds": round(duration_delta, 3),
        "max_volume_db": max_volume,
        "no_clipping_above_0db": no_clipping,
        "filters": filters,
        "external_api_used": False,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    ensure_parent_dir(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    ensure_parent_dir(legacy_report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in [wav_path, mp3_path, report_path]:
            if path.is_file():
                archive.write(path, path.name)
    return {
        "ok": True,
        "message": "Mastered WAV ready",
        "data": {
            "mastered_wav": str(wav_path),
            "mp3_preview": str(mp3_path) if mp3_path.is_file() and mp3.get("ok") else "",
            "report_path": str(report_path),
            "zip_path": str(zip_path),
            "report": report,
        },
        "error": "",
    }
