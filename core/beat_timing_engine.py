from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any


MOTION_SYNC_SEQUENCE = [
    "beat_zoom",
    "punch_cut",
    "slow_emotional_pan",
    "bass_hit_shake",
    "cinematic_fade_timing",
]

VISUAL_BPM_CONFIDENCE_THRESHOLD = 0.70
VISUAL_RHYTHM_MIN_SCENE_SECONDS = 1.0
VISUAL_RHYTHM_MAX_SNAP_SECONDS = 0.50
VISUAL_RHYTHM_MAX_SNAP_RATIO = 0.15


def _finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and number not in {float("inf"), float("-inf")} else None


def resolve_visual_rhythm(
    audio_intelligence: dict[str, Any] | None,
    *,
    confidence_threshold: float = VISUAL_BPM_CONFIDENCE_THRESHOLD,
) -> dict[str, Any]:
    """Resolve measured tempo without treating generated/design BPM as audio evidence."""
    analysis = audio_intelligence if isinstance(audio_intelligence, dict) else {}
    musical = analysis.get("musical") if isinstance(analysis.get("musical"), dict) else {}
    energy = analysis.get("energy") if isinstance(analysis.get("energy"), dict) else {}
    bpm = _finite_float(musical.get("bpm"))
    confidence = _finite_float(musical.get("bpm_confidence")) or 0.0
    status = str(musical.get("bpm_status") or "unavailable").strip().lower()
    reliable = status == "ok" and bpm is not None and 40.0 <= bpm <= 240.0 and confidence >= confidence_threshold
    profile = energy.get("profile") if energy.get("status") == "ok" and isinstance(energy.get("profile"), list) else []
    return {
        "rhythm_source": "measured_bpm" if reliable else "fallback",
        "measured_bpm": round(bpm, 3) if bpm is not None else None,
        "bpm_confidence": round(confidence, 4),
        "bpm_status": status,
        "confidence_threshold": confidence_threshold,
        "beat_interval_seconds": round(60.0 / bpm, 6) if reliable and bpm else None,
        "energy_profile": profile,
        "tempo_phase_known": False,
    }


def _energy_at(profile: list[dict[str, Any]], time_seconds: float) -> float | None:
    values: list[float] = []
    for point in profile:
        start = _finite_float(point.get("start_sec"))
        end = _finite_float(point.get("end_sec"))
        normalized = _finite_float(point.get("normalized"))
        if start is None or end is None or normalized is None:
            continue
        if start <= time_seconds < end or (time_seconds == end and end == start):
            values.append(max(0.0, min(1.0, normalized)))
    return sum(values) / len(values) if values else None


def _phrase_quantum_beats(energy: float | None) -> tuple[int, str]:
    if energy is not None and energy >= 0.67:
        return 2, "high"
    if energy is not None and energy <= 0.33:
        return 8, "low"
    return 4, "medium"


def create_visual_rhythm_plan(
    target_durations: list[float | int],
    *,
    total_duration: float | int | None,
    audio_intelligence: dict[str, Any] | None,
    confidence_threshold: float = VISUAL_BPM_CONFIDENCE_THRESHOLD,
) -> dict[str, Any]:
    """Snap scene boundaries to tempo-sized phrases while conserving audio duration.

    BPM supplies tempo only. Boundaries are duration-aligned from zero and are not
    represented as detected beats or downbeats.
    """
    started = time.perf_counter()
    rhythm = resolve_visual_rhythm(audio_intelligence, confidence_threshold=confidence_threshold)
    targets = [max(VISUAL_RHYTHM_MIN_SCENE_SECONDS, float(value or 0.0)) for value in target_durations]
    source_duration = _finite_float(total_duration)
    if not targets:
        return {**rhythm, "durations": [], "boundaries": [0.0], "snaps": [], "elapsed_ms": 0.0}
    if rhythm["rhythm_source"] != "measured_bpm" or source_duration is None or source_duration <= 0:
        return {
            **rhythm,
            "durations": [round(value, 3) for value in targets],
            "boundaries": [],
            "snaps": [],
            "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
        }

    minimum_scene_seconds = min(VISUAL_RHYTHM_MIN_SCENE_SECONDS, source_duration / len(targets))
    target_total = sum(targets)
    scaled = [value * source_duration / target_total for value in targets]
    beat_interval = float(rhythm["beat_interval_seconds"])
    profile = rhythm.get("energy_profile") or []
    boundaries = [0.0]
    snaps: list[dict[str, Any]] = []
    cumulative_target = 0.0
    for index, duration in enumerate(scaled[:-1]):
        cumulative_target += duration
        midpoint = boundaries[-1] + duration / 2.0
        energy = _energy_at(profile, midpoint)
        quantum_beats, energy_level = _phrase_quantum_beats(energy)
        quantum_seconds = beat_interval * quantum_beats
        snapped = round(cumulative_target / quantum_seconds) * quantum_seconds
        tolerance = min(VISUAL_RHYTHM_MAX_SNAP_SECONDS, max(0.08, duration * VISUAL_RHYTHM_MAX_SNAP_RATIO))
        remaining = len(scaled) - index - 1
        minimum_boundary = boundaries[-1] + minimum_scene_seconds
        maximum_boundary = source_duration - remaining * minimum_scene_seconds
        use_snap = abs(snapped - cumulative_target) <= tolerance and minimum_boundary <= snapped <= maximum_boundary
        boundary = snapped if use_snap else cumulative_target
        boundary = max(minimum_boundary, min(maximum_boundary, boundary))
        boundaries.append(boundary)
        snaps.append(
            {
                "scene_index": index,
                "target_boundary": round(cumulative_target, 6),
                "resolved_boundary": round(boundary, 6),
                "adjustment_seconds": round(boundary - cumulative_target, 6),
                "max_adjustment_seconds": round(tolerance, 6),
                "phrase_beats": quantum_beats,
                "energy_level": energy_level,
                "snapped": use_snap,
            }
        )
    boundaries.append(source_duration)
    durations = [boundaries[index + 1] - boundaries[index] for index in range(len(targets))]
    return {
        **rhythm,
        "duration_source": "audio_intelligence",
        "duration_seconds": round(source_duration, 6),
        "durations": [round(value, 6) for value in durations],
        "boundaries": [round(value, 6) for value in boundaries],
        "snaps": snaps,
        "max_snap_seconds": VISUAL_RHYTHM_MAX_SNAP_SECONDS,
        "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
    }


def _safe_duration(value: Any, fallback: float = 15.0) -> float:
    try:
        duration = float(value)
    except (TypeError, ValueError):
        duration = fallback
    return max(5.0, min(60.0, duration))


def _duration_from_audio(audio_path: str | Path | None, fallback: float) -> float:
    path = Path(str(audio_path or ""))
    if not path.is_file():
        return fallback
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        if proc.returncode == 0:
            duration = float((proc.stdout or "0").strip() or 0)
            if duration > 1:
                return _safe_duration(duration, fallback)
    except Exception:
        pass
    # Keep this lightweight and cloud-safe. File size gives us enough variation for
    # retention timing without requiring ffprobe in the critical creator flow.
    size_mb = max(0.05, path.stat().st_size / (1024 * 1024))
    estimated = 8.0 + min(22.0, size_mb * 5.5)
    return _safe_duration(estimated, fallback)


def create_beat_timing_plan(
    *,
    audio_path: str | Path | None = None,
    total_duration: float | int | None = 15,
    scene_count: int = 3,
    pace: str = "fast",
    hook_text: str = "",
) -> dict[str, Any]:
    scene_count = max(1, min(8, int(scene_count or 3)))
    duration = _duration_from_audio(audio_path, _safe_duration(total_duration or 15))
    hook_text_value = str(hook_text or "")
    emotional_words = ["เจ็บ", "เหงา", "รัก", "คิดถึง", "ใจ", "hurt", "lonely", "miss", "heart"]
    punch_words = ["หยุด", "พอ", "เดี๋ยว", "จริง", "ต้องดู", "โคตร", "stop", "wait", "why"]
    emotional_intensity = min(100, 40 + sum(10 for word in emotional_words if word.lower() in hook_text_value.lower()) + min(25, len(hook_text_value) // 12))
    punchline_intensity = min(100, 35 + sum(13 for word in punch_words if word.lower() in hook_text_value.lower()) + (20 if len(hook_text_value) <= 80 else 0))
    if pace == "slow":
        weights = [0.36, 0.34, 0.30]
        timing_profile = "emotional_slow_build"
        emotional_curve = ["soft_open", "deep_feeling", "quiet_release"]
    elif pace == "medium":
        weights = [0.28, 0.34, 0.38]
        timing_profile = "balanced_story_hook"
        emotional_curve = ["setup", "turn", "strong_finish"]
    else:
        weights = [0.14, 0.32, 0.54]
        timing_profile = "fast_retention_hook"
        emotional_curve = ["instant_hook", "punchline", "shareable_peak"]
    if emotional_intensity > punchline_intensity + 15:
        weights = [0.30, 0.37, 0.33] if pace != "fast" else [0.22, 0.34, 0.44]
        timing_profile += "_emotional_weighted"
    if scene_count != 3:
        weights = [1 / scene_count for _ in range(scene_count - 1)] + [1 / scene_count]
    beat_interval = 0.75 if pace == "fast" else 1.05 if pace == "medium" else 1.35
    beat_markers = []
    t = 0.35
    while t < duration:
        beat_markers.append(round(t, 2))
        t += beat_interval
    loudness_peaks = [round(max(0.15, duration * ratio), 2) for ratio in (0.08, 0.36, 0.68, 0.88) if duration * ratio < duration]
    scene_timing = []
    cursor = 0.0
    hook_peak_moment = round(max(0.55, min(1.8, duration * 0.12)) if pace == "fast" else max(0.8, duration * (0.58 if pace == "slow" else 0.48)), 2)
    for index, weight in enumerate(weights[:scene_count], start=1):
        if index == scene_count:
            end = duration
        else:
            end = cursor + max(1.4, duration * weight)
        effect = MOTION_SYNC_SEQUENCE[(index - 1) % len(MOTION_SYNC_SEQUENCE)]
        scene_timing.append(
            {
                "scene_id": f"scene_{index:02d}",
                "start": round(cursor, 2),
                "end": round(end, 2),
                "duration": round(max(0.8, end - cursor), 2),
                "motion_sync": effect,
                "transition_trigger": "peak" if index == 1 else "beat" if index < scene_count else "emotional_release",
                "subtitle_emphasis_at": round(cursor + max(0.2, (end - cursor) * 0.28), 2),
                "retention_role": "stop_scroll" if index == 1 else "context_turn" if index < scene_count else "strongest_finish",
                "emotional_curve": emotional_curve[min(index - 1, len(emotional_curve) - 1)],
                "hook_peak": cursor <= hook_peak_moment <= end,
            }
        )
        cursor = end
    return {
        "generated_by": "VelaFlow",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "audio_path": str(audio_path or ""),
        "duration": round(duration, 2),
        "pace": pace,
        "timing_profile": timing_profile,
        "emotional_curve": emotional_curve,
        "hook_peak_moment": hook_peak_moment,
        "hook_quality_inputs": {
            "emotional_intensity": emotional_intensity,
            "punchline_intensity": punchline_intensity,
            "short_readability": max(0, min(100, 100 - max(0, len(hook_text_value) - 80))),
        },
        "hook_text": hook_text,
        "beat_markers": beat_markers,
        "loudness_peaks": loudness_peaks,
        "energy_changes": [
            {"time": marker, "energy": min(100, 48 + index * 9)}
            for index, marker in enumerate(loudness_peaks, start=1)
        ],
        "scene_timing": scene_timing,
        "motion_sync": {
            "beat_zoom": "Use a small zoom on early beat hits.",
            "punch_cut": "Cut hard when the hook line lands.",
            "slow_emotional_pan": "Hold a slower pan during emotional words.",
            "bass_hit_shake": "Add a short shake on loud peaks.",
            "cinematic_fade_timing": "Fade out at the final emotional release.",
        },
    }


def apply_beat_timing_to_package(package: dict[str, Any], timing_plan: dict[str, Any]) -> dict[str, Any]:
    timing_by_scene = {item.get("scene_id"): item for item in timing_plan.get("scene_timing", [])}
    effect_map = {
        "beat_zoom": "hook_energy_zoom",
        "punch_cut": "shake_zoom",
        "slow_emotional_pan": "minimal_pan",
        "bass_hit_shake": "shake",
        "cinematic_fade_timing": "cinematic_fade",
    }
    for scene in package.get("scene_sequence", []) or []:
        scene_id = scene.get("scene_id")
        timing = timing_by_scene.get(scene_id)
        if not timing:
            continue
        scene["duration"] = timing.get("duration", scene.get("duration", 2.5))
        scene["start_time"] = timing.get("start", scene.get("start_time", 0))
        scene["end_time"] = timing.get("end", scene.get("end_time", 0))
        scene["beat_timing"] = timing
        scene["motion_effect"] = effect_map.get(str(timing.get("motion_sync")), scene.get("motion_effect", "slow_zoom"))
        scene["transition"] = timing.get("transition_trigger", scene.get("transition", "beat"))
    package["beat_timing_plan"] = timing_plan
    return package


def save_beat_timing(timing_plan: dict[str, Any], output_path: str | Path) -> dict[str, Any]:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(timing_plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "message": "Beat timing exported", "data": {"path": str(path)}, "error": ""}


def create_affiliate_retention_timing(*, duration: float | int = 20, hook_type: str = "curiosity") -> dict[str, Any]:
    total = _safe_duration(duration, 20)
    first_cut = min(2.2, total * 0.16)
    proof_cut = min(total - 2.0, max(first_cut + 3.5, total * 0.48))
    cta_start = max(proof_cut + 1.0, total * 0.72)
    urgency_bias = 8 if hook_type in {"urgency", "shock", "social_proof"} else 0
    return {
        "generated_by": "VelaFlow",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "workflow": "affiliate",
        "duration": round(total, 2),
        "hook_type": hook_type,
        "first_3_seconds": {
            "pace": "very_fast",
            "cut_at": round(first_cut, 2),
            "subtitle_emphasis": "large pain-point or curiosity phrase",
            "zoom_pulse_at": [0.45, 1.25, round(first_cut, 2)],
        },
        "emotional_beat_timing": [
            {"time": round(first_cut + 0.3, 2), "role": "problem recognition"},
            {"time": round(proof_cut, 2), "role": "product proof"},
            {"time": round(cta_start, 2), "role": "conversion push"},
        ],
        "subtitle_emphasis_timing": [0.35, round(first_cut + 0.25, 2), round(cta_start, 2)],
        "cta_timing": {"start": round(cta_start, 2), "end": round(total, 2), "placement": "final 25 percent"},
        "retention_estimate": min(100, 76 + urgency_bias),
        "conversion_pacing": min(100, 78 + urgency_bias),
    }
