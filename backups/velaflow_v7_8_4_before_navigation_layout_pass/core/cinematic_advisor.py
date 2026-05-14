from __future__ import annotations

from typing import Any, Dict, List

from core.emotional_arc import analyze_emotional_arc
from core.hook_intelligence import analyze_hooks


def build_cinematic_suggestions(project: Dict[str, Any]) -> Dict[str, Any]:
    arc_points = analyze_emotional_arc(project)["data"]["points"]
    hooks = analyze_hooks(project)["data"]["candidates"]
    hook_scene_ids = {item["scene_id"] for item in hooks[:3] if item.get("hook_score", 0) >= 70}
    suggestions: List[Dict[str, Any]] = []
    for point in arc_points:
        scene_id = point["scene_id"]
        if point["section"] == "bridge":
            suggestions.append(_row(scene_id, "motion", "Bridge should reduce motion and hold emotion.", "emotional_push_in"))
        if point["section"] == "final_chorus":
            suggestions.append(_row(scene_id, "motion", "Final chorus should feel bigger with stronger zoom.", "hook_energy_zoom"))
        if scene_id in hook_scene_ids:
            suggestions.append(_row(scene_id, "subtitle", "Hook candidate should use emphasized subtitle styling.", "tiktok_bold"))
        if point["energy"] <= 40:
            suggestions.append(_row(scene_id, "camera", "Low-energy scene should use close-up or slow push-in.", "close-up / slow dolly in"))
        if point["recommended_color"] == "moody":
            suggestions.append(_row(scene_id, "color", "Emotional scene should use moody grade.", "moody"))
    return {"ok": True, "message": "Cinematic suggestions generated offline", "data": {"suggestions": suggestions}, "error": ""}


def apply_cinematic_suggestions(project: Dict[str, Any]) -> Dict[str, Any]:
    storyboard = project.setdefault("mv", {}).setdefault("storyboard", [])
    arc = analyze_emotional_arc(project)["data"]["points"]
    arc_by_id = {item["scene_id"]: item for item in arc}
    changed = []
    for index, scene in enumerate(storyboard):
        scene_id = str(scene.get("scene") or index + 1)
        point = arc_by_id.get(scene_id, {})
        if not point:
            continue
        scene["transition"] = point.get("recommended_transition", scene.get("transition", "fade"))
        scene["camera"] = scene.get("camera") or ("close-up" if point.get("energy", 0) <= 40 else "slow dolly in")
        scene["motion_effect"] = point.get("recommended_motion", scene.get("motion_effect", "cinematic_drift"))
        scene["color_profile"] = point.get("recommended_color", scene.get("color_profile", "film_look"))
        scene["pacing_note"] = scene.get("pacing_note") or point.get("recommended_pacing", "")
        changed.append(scene_id)
    project.setdefault("settings", {})["adaptive_creative_intelligence"] = True
    return {"ok": True, "message": f"Applied cinematic suggestions to {len(changed)} scenes", "data": {"scenes": changed, "project": project}, "error": ""}


def _row(scene_id: str, area: str, message: str, recommendation: str) -> Dict[str, str]:
    return {"scene_id": str(scene_id), "area": area, "message": message, "recommendation": recommendation}
