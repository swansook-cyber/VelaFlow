from __future__ import annotations

import json
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
        weights = [0.18, 0.30, 0.52]
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
    hook_peak_moment = round(max(0.8, duration * (0.38 if pace == "fast" else 0.58 if pace == "slow" else 0.48)), 2)
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
