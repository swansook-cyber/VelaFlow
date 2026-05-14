from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from core.emotional_arc import analyze_emotional_arc
from core.hook_intelligence import analyze_hooks


def build_creative_timeline(project: Dict[str, Any]) -> Dict[str, Any]:
    storyboard = ((project.get("mv", {}) or {}).get("storyboard", []) or [])
    arc_points = {item["scene_id"]: item for item in analyze_emotional_arc(project)["data"]["points"]}
    hooks = analyze_hooks(project)["data"]["candidates"]
    hook_by_scene = {}
    for hook in hooks:
        hook_by_scene.setdefault(hook["scene_id"], hook)
    rows: List[Dict[str, Any]] = []
    start = 0.0
    for index, scene in enumerate(storyboard):
        scene_id = str(scene.get("scene") or index + 1)
        duration = float(scene.get("duration_seconds") or 5)
        arc = arc_points.get(scene_id, {})
        hook = hook_by_scene.get(scene_id, {})
        rows.append(
            {
                "scene_id": scene_id,
                "start_time": round(start, 3),
                "duration_seconds": duration,
                "end_time": round(start + duration, 3),
                "lyrics": scene.get("subtitle_text") or scene.get("lyric_part", ""),
                "emotion": scene.get("emotion", ""),
                "energy": arc.get("energy", 0),
                "beat": "dense" if arc.get("energy", 0) >= 75 else "soft",
                "motion": arc.get("recommended_motion", scene.get("motion_effect", "")),
                "subtitle": hook.get("subtitle_emphasis", scene.get("subtitle_style", "")),
                "transition": arc.get("recommended_transition", scene.get("transition", "")),
                "color": arc.get("recommended_color", scene.get("color_profile", "")),
                "hook_score": hook.get("hook_score", 0),
            }
        )
        start += duration
    return {"ok": True, "message": "Creative timeline built", "data": {"total_duration_seconds": round(start, 3), "items": rows}, "error": ""}


def export_creative_timeline(project: Dict[str, Any], output_dir: str | Path) -> Dict[str, Any]:
    import json

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    data = build_creative_timeline(project)["data"]
    path = output / "creative_timeline.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "message": "Creative timeline exported", "data": {"path": str(path)}, "error": ""}
