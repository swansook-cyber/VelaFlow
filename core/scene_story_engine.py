from __future__ import annotations

from datetime import datetime
from typing import Any

from core.visual_presets import normalize_visual_settings


SCENE_STRUCTURES = {
    "music": ["Opening Hook", "Emotional Image", "Lyric Punchline"],
    "music_mv": ["Opening Hook", "Emotional Image", "Lyric Punchline"],
    "seller": ["Hook", "Pain Point", "Product Proof", "CTA"],
    "podcast": ["Emotional Opening", "Relatable Beat", "Quote Moment"],
    "viral_clips": ["Fast Hook", "Context Beat", "Viral Punchline"],
    "hook_clip": ["Fast Hook", "Story Beat", "Payoff"],
}

CLIP_MODES = ["Fast Hook", "Viral Clip", "Story Clip"]


def _duration_for_count(total_duration: int, count: int) -> list[float]:
    count = max(1, count)
    base = round(total_duration / count, 2)
    durations = [base for _ in range(count)]
    durations[-1] = round(max(0.5, total_duration - sum(durations[:-1])), 2)
    return durations


def build_scene_sequence(
    *,
    workflow_type: str,
    hook_text: str,
    visual_settings: dict[str, Any] | None = None,
    clip_mode: str = "Fast Hook",
    duration_seconds: int = 8,
    source_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    visual = normalize_visual_settings(visual_settings)
    workflow_key = workflow_type if workflow_type in SCENE_STRUCTURES else "hook_clip"
    beats = SCENE_STRUCTURES[workflow_key]
    if clip_mode == "Fast Hook":
        beats = beats[:3]
    elif clip_mode == "Story Clip" and len(beats) < 4:
        beats = beats + ["Closing Feeling"]
    durations = _duration_for_count(max(5, min(60, int(duration_seconds or 8))), len(beats))
    context = source_context or {}
    scenes: list[dict[str, Any]] = []
    for index, beat in enumerate(beats, start=1):
        subtitle = hook_text if index == 1 else str(context.get("subtitle") or hook_text)
        pacing = "fast attention cut" if clip_mode in {"Fast Hook", "Viral Clip"} else "short emotional story beat"
        transition = "snap cut" if index == 1 else "quick blur cut" if clip_mode == "Viral Clip" else "soft cut"
        scenes.append(
            {
                "scene_id": f"scene_{index:02d}",
                "beat": beat,
                "subtitle": subtitle[:90],
                "visual_prompt": (
                    f"{beat}, {hook_text}, vertical 9:16 short-form scene, "
                    f"{visual['visual_mood_description']}, {visual['camera_description']}, "
                    f"{visual['lighting_description']}, realistic creator-ready visual"
                ),
                "camera_direction": visual["camera_description"],
                "lighting": visual["lighting_description"],
                "motion": visual["motion_description"],
                "pacing": pacing,
                "transition": transition,
                "duration": durations[index - 1],
                "render_provider_metadata": {
                    "aspect_ratio": "9:16",
                    "duration": f"{durations[index - 1]}s",
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                },
            }
        )
    return scenes


def build_subtitle_timing(scenes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    timeline = []
    current = 0.0
    for scene in scenes:
        duration = float(scene.get("duration", 2.0) or 2.0)
        timeline.append(
            {
                "scene_id": scene.get("scene_id", ""),
                "start": round(current, 2),
                "end": round(current + duration, 2),
                "subtitle": scene.get("subtitle", ""),
            }
        )
        current += duration
    return timeline
