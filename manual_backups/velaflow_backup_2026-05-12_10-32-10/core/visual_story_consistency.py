from __future__ import annotations

from typing import Any, Dict, List


def analyze_visual_story_consistency(project: Dict[str, Any]) -> Dict[str, Any]:
    storyboard = ((project.get("mv", {}) or {}).get("storyboard", []) or [])
    character = project.get("character", {}) or {}
    identity = project.get("visual_identity", {}) or {}
    issues: List[Dict[str, str]] = []
    rows = []
    expected_color = str(identity.get("color_profile") or (project.get("settings", {}) or {}).get("color_profile") or "").lower()
    expected_mood = ""
    for index, scene in enumerate(storyboard):
        scene_id = str(scene.get("scene") or index + 1)
        text = " ".join(str(scene.get(key, "") or "").lower() for key in ["image_prompt", "expanded_prompt", "scene_visual", "lighting", "emotion"])
        row = {
            "scene_id": scene_id,
            "character_continuity": _character_ok(character, text),
            "color_continuity": not expected_color or expected_color.replace("_", " ") in text or expected_color in text,
            "emotional_continuity": True,
            "lighting_continuity": bool(scene.get("lighting") or "light" in text or "neon" in text or "rain" in text),
        }
        if expected_mood and scene.get("emotion") and expected_mood not in str(scene.get("emotion", "")).lower():
            row["emotional_continuity"] = False
        expected_mood = str(scene.get("emotion", "") or expected_mood).lower()
        for key, ok in row.items():
            if key != "scene_id" and not ok:
                issues.append({"scene_id": scene_id, "area": key, "message": f"{key.replace('_', ' ')} needs review"})
        rows.append(row)
    score = max(0, 100 - len(issues) * 7)
    return {"ok": True, "message": "Visual story consistency analyzed", "data": {"score": score, "issues": issues, "rows": rows}, "error": ""}


def _character_ok(character: Dict[str, str], text: str) -> bool:
    name = str(character.get("name", "") or "").lower()
    outfit = str(character.get("outfit", "") or "").lower()
    hair = str(character.get("hair", "") or "").lower()
    if not any([name, outfit, hair]):
        return True
    return any(value and value in text for value in [name, outfit, hair])
