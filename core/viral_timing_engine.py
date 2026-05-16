from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _density(text: str, duration: float) -> float:
    compact = "".join(str(text or "").split())
    return round(len(compact) / max(0.5, duration), 2)


def create_viral_timing_plan(
    hook_package: dict[str, Any],
    *,
    target_duration: int | float | None = None,
    preset_id: str = "",
) -> dict[str, Any]:
    scenes = hook_package.get("scene_sequence") or (hook_package.get("scene_package") or {}).get("scenes") or []
    subtitle_timing = hook_package.get("subtitle_timing") or []
    total_duration = _float(target_duration, 0.0) or sum(_float(scene.get("duration"), 0.0) for scene in scenes) or 8.0
    first_scene = scenes[0] if scenes else {}
    first_three_seconds = {
        "goal": "stop scroll quickly",
        "opening_line": hook_package.get("hook_text") or first_scene.get("subtitle", ""),
        "recommended_action": "show hook subtitle immediately, start motion within 0.3s",
    }
    scene_plan = []
    current = 0.0
    for index, scene in enumerate(scenes, start=1):
        duration = max(0.8, _float(scene.get("duration"), total_duration / max(1, len(scenes))))
        subtitle = str(scene.get("subtitle") or "")
        scene_plan.append(
            {
                "scene_id": scene.get("scene_id") or f"scene_{index:02d}",
                "start": round(current, 2),
                "end": round(current + duration, 2),
                "duration": round(duration, 2),
                "subtitle_density": _density(subtitle, duration),
                "motion_cue": scene.get("motion_effect") or scene.get("motion") or "slow zoom",
                "cut_timing": "hard cut" if index == 1 else scene.get("transition", "quick cut"),
                "retention_note": "hook punch" if index == 1 else "keep visual change obvious",
            }
        )
        current += duration
    subtitle_density = [_density(item.get("subtitle") or item.get("text") or "", _float(item.get("end"), 1) - _float(item.get("start"), 0)) for item in subtitle_timing]
    average_density = round(sum(subtitle_density) / max(1, len(subtitle_density)), 2)
    speed = "fast" if total_duration <= 15 else "medium" if total_duration <= 30 else "slow"
    plan = {
        "generated_by": "VelaFlow",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "preset_id": preset_id,
        "total_duration": round(total_duration, 2),
        "hook_speed": speed,
        "first_3_seconds": first_three_seconds,
        "scene_count": len(scenes),
        "scene_timing": scene_plan,
        "subtitle_density": {
            "average_chars_per_second": average_density,
            "recommendation": "shorten subtitle lines" if average_density > 13 else "density ok",
        },
        "zoom_cut_timing": [
            {"time": 0.0, "action": "start zoom or shake"},
            {"time": min(2.8, total_duration / 3), "action": "first visual change"},
            {"time": max(0.0, total_duration - 2.0), "action": "final punchline or CTA"},
        ],
        "emotional_punchline_timing": {
            "recommended_time": round(max(1.5, total_duration * 0.66), 2),
            "note": "place the most emotional subtitle near the final third",
        },
    }
    return plan


def save_viral_timing_plan(plan: dict[str, Any], output_path: str | Path) -> dict[str, Any]:
    try:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "message": "Viral timing plan saved", "data": {"path": str(path), "plan": plan}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Viral timing plan save failed", "data": {}, "error": str(exc)}
