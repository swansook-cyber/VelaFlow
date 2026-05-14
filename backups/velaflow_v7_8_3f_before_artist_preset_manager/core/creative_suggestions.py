from __future__ import annotations

from typing import Any, Dict, List

from core.quality_control import quality_rows
from core.scene_scoring import score_project_scenes


def build_creative_suggestions(project: Dict[str, Any]) -> Dict[str, Any]:
    suggestions: List[Dict[str, Any]] = []
    rows = quality_rows(project)
    scores = {item["scene_id"]: item for item in score_project_scenes(project)}
    settings = project.get("settings", {}) or {}
    color_profile = settings.get("color_profile") or (project.get("visual_identity", {}) or {}).get("color_profile", "")

    for row in rows:
        scene_id = row["scene_id"]
        score = scores.get(scene_id, row)
        if row.get("subtitle_too_long"):
            suggestions.append(_suggest(scene_id, "subtitle", "Subtitle is long; split into shorter caption chunks.", "shorten_subtitle"))
        if score.get("hook_potential", 0) >= 75 and score.get("recommended_motion") != "hook_energy_zoom":
            suggestions.append(_suggest(scene_id, "motion", "Hook scene can use stronger zoom or beat-aware movement.", "use_hook_energy_zoom"))
        if score.get("emotional_impact", 0) >= 75 and score.get("hook_potential", 0) < 70:
            suggestions.append(_suggest(scene_id, "motion", "Emotional scene should stay smoother; avoid fast TikTok motion.", "use_emotional_push_in"))
        if row.get("quality_score", 0) < 55:
            suggestions.append(_suggest(scene_id, "asset", "Scene quality is weak; regenerate or reuse a stronger approved visual.", "regenerate_or_reuse"))
        scene_color = str(row.get("color", "") or "").lower()
        if color_profile and scene_color and color_profile.lower().replace("_", " ") not in scene_color:
            suggestions.append(_suggest(scene_id, "color", "Scene color note may not match the project color profile.", "review_color_profile"))
        if not row.get("has_prompt"):
            suggestions.append(_suggest(scene_id, "prompt", "Scene has no image prompt; reuse a scene preset or write a prompt before generation.", "add_prompt"))

    if not suggestions:
        suggestions.append(
            {
                "scene_id": "",
                "area": "project",
                "message": "No urgent creative issues found. Project is ready for draft preview.",
                "action": "render_draft",
                "severity": "INFO",
            }
        )
    return {"ok": True, "message": "Creative suggestions generated offline", "data": {"suggestions": suggestions}, "error": ""}


def _suggest(scene_id: str, area: str, message: str, action: str, severity: str = "WARN") -> Dict[str, str]:
    return {"scene_id": str(scene_id), "area": area, "message": message, "action": action, "severity": severity}
