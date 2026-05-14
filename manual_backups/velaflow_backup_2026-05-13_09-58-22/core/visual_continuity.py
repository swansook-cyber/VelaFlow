from __future__ import annotations

from typing import Any, Dict, List


def analyze_visual_continuity(project: Dict[str, Any]) -> Dict[str, Any]:
    storyboard = ((project.get("mv", {}) or {}).get("storyboard", []) or [])
    settings = project.get("settings", {}) or {}
    identity = project.get("visual_identity", {}) or {}
    target_color = settings.get("color_profile") or identity.get("color_profile") or ""
    target_motion = settings.get("motion_style") or identity.get("motion_style") or ""
    target_subtitle = settings.get("subtitle_style") or identity.get("subtitle_style") or ""
    issues: List[Dict[str, Any]] = []
    rows = []
    for index, scene in enumerate(storyboard):
        scene_id = str(scene.get("scene") or index + 1)
        color_text = " ".join(str(scene.get(key, "") or "").lower() for key in ["lighting", "color_profile", "scene_visual", "image_prompt"])
        motion_text = " ".join(str(scene.get(key, "") or "").lower() for key in ["camera", "camera_motion", "pacing_note"])
        subtitle_style = scene.get("subtitle_style", "")
        row = {
            "scene_id": scene_id,
            "color_match": _matches(target_color, color_text),
            "motion_match": _matches(target_motion, motion_text) or not target_motion,
            "subtitle_match": not subtitle_style or not target_subtitle or subtitle_style == target_subtitle,
            "mood": scene.get("emotion", ""),
        }
        rows.append(row)
        if target_color and not row["color_match"]:
            issues.append({"scene_id": scene_id, "area": "color", "message": f"Scene may not match color profile {target_color}"})
        if target_motion and not row["motion_match"]:
            issues.append({"scene_id": scene_id, "area": "motion", "message": f"Scene camera note may not match motion style {target_motion}"})
        if not row["subtitle_match"]:
            issues.append({"scene_id": scene_id, "area": "subtitle", "message": f"Subtitle style differs from project style {target_subtitle}"})
    score = max(0, 100 - len(issues) * 8)
    return {"ok": True, "message": "Visual continuity analyzed offline", "data": {"score": score, "target_color": target_color, "target_motion": target_motion, "target_subtitle": target_subtitle, "issues": issues, "rows": rows}, "error": ""}


def _matches(target: str, text: str) -> bool:
    if not target:
        return True
    normalized = target.lower().replace("_", " ")
    return normalized in text or any(part in text for part in normalized.split() if len(part) > 3)
