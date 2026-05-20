from __future__ import annotations

import json
import math
import re
import subprocess
from pathlib import Path
from typing import Any

from core.real_clip_pipeline import ensure_parent_dir, find_ffmpeg, probe_media, trim_audio_clip


def _parse_volumedetect(stderr: str) -> float:
    match = re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", stderr or "")
    if not match:
        return -99.0
    return float(match.group(1))


def detect_hook_section(
    audio_path: str | Path,
    *,
    output_dir: str | Path,
    quota_saving_mode: bool = True,
    min_hook_duration: float | None = None,
    max_hook_duration: float | None = None,
    ffmpeg_path: str = "",
) -> dict[str, Any]:
    source = Path(audio_path)
    debug_dir = Path(output_dir)
    report_path = ensure_parent_dir(debug_dir / "hook_detection_report.json")
    report: dict[str, Any] = {
        "audio_path": str(source),
        "quota_saving_mode": bool(quota_saving_mode),
        "veo_called": False,
        "segments": [],
        "ok": False,
        "error": "",
    }
    if not source.is_file():
        report["error"] = "missing_audio"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": False, "message": "Audio file missing", "data": {"report_path": str(report_path)}, "error": "missing_audio"}
    ffmpeg = ffmpeg_path or find_ffmpeg()
    if not ffmpeg:
        report["error"] = "missing_ffmpeg"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": False, "message": "FFmpeg not found", "data": {"report_path": str(report_path)}, "error": "missing_ffmpeg"}
    duration = float(probe_media(source, ffmpeg_path=ffmpeg).get("duration") or 0.0)
    if duration <= 0:
        report["error"] = "audio_duration_unavailable"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": False, "message": "Audio duration unavailable", "data": {"report_path": str(report_path)}, "error": "audio_duration_unavailable"}

    min_duration = float(min_hook_duration if min_hook_duration is not None else (8.0 if quota_saving_mode else 15.0))
    max_duration = float(max_hook_duration if max_hook_duration is not None else (8.0 if quota_saving_mode else 24.0))
    target_duration = 8.0 if quota_saving_mode else min(max_duration, max(min_duration, duration * 0.22))
    target_duration = min(target_duration, max(min_duration, duration))
    target_duration = max(min_duration, min(max_duration, target_duration))
    target_duration = min(target_duration, duration)

    intro_guard = min(max(8.0, duration * 0.18), max(0.0, duration - target_duration))
    search_start = intro_guard
    search_end = max(search_start, duration - target_duration)
    step = 4.0 if quota_saving_mode else 3.0
    candidates = []
    cursor = search_start
    while cursor <= search_end + 0.1:
        candidates.append(round(cursor, 2))
        cursor += step
    if not candidates:
        candidates = [max(0.0, duration * 0.35)]

    best: dict[str, Any] = {"start": candidates[0], "mean_volume": -99.0}
    for candidate in candidates:
        proc = subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-ss",
                f"{candidate:.3f}",
                "-t",
                f"{target_duration:.3f}",
                "-i",
                str(source),
                "-af",
                "volumedetect",
                "-f",
                "null",
                "-",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=45,
        )
        mean_volume = _parse_volumedetect(proc.stderr)
        segment = {"start": round(candidate, 2), "end": round(min(duration, candidate + target_duration), 2), "mean_volume_db": mean_volume}
        report["segments"].append(segment)
        if mean_volume > float(best.get("mean_volume", -99.0)):
            best = {"start": candidate, "mean_volume": mean_volume}

    start = max(0.0, min(float(best["start"]), max(0.0, duration - target_duration)))
    end = min(duration, start + target_duration)
    hook_duration = max(1.0, end - start)
    confidence = int(max(45, min(92, 62 + (float(best.get("mean_volume", -99.0)) + 30) * 1.4)))
    reason = (
        "Quota-saving mode selected the strongest local energy window after the intro/verse zone."
        if quota_saving_mode
        else "Selected a high-energy chorus-like window after the intro/verse zone using local loudness analysis."
    )
    data = {
        "hook_start_time": round(start, 2),
        "hook_end_time": round(end, 2),
        "hook_duration": round(hook_duration, 2),
        "confidence": confidence,
        "confidence_score": confidence,
        "reason": reason,
        "detection_reason": reason,
        "energy_profile_summary": f"Scanned {len(report['segments'])} candidate windows; strongest mean volume {float(best.get('mean_volume', -99.0)):.1f} dB.",
        "suggested_use": "Use as full hook section for creator package exports and external video tools.",
        "audio_duration": round(duration, 2),
        "quota_saving_mode": bool(quota_saving_mode),
        "report_path": str(report_path),
    }
    report.update(data)
    report["ok"] = True
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "message": "Hook detected", "data": data, "error": ""}


def apply_detected_hook_audio(
    audio_path: str | Path,
    output_path: str | Path,
    detection: dict[str, Any],
    *,
    ffmpeg_path: str = "",
) -> dict[str, Any]:
    return trim_audio_clip(
        audio_path,
        output_path,
        start_time=float(detection.get("hook_start_time") or 0.0),
        end_time=float(detection.get("hook_end_time") or 0.0),
        ffmpeg_path=ffmpeg_path,
    )
