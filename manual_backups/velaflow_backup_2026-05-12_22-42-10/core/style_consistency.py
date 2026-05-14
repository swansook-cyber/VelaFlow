from __future__ import annotations

from typing import Any, Dict, List


def build_style_consistency_report(project: Dict[str, Any]) -> Dict[str, Any]:
    identity = project.get("visual_identity", {}) or {}
    storyboard = ((project.get("mv", {}) or {}).get("storyboard", []) or [])
    missing: List[str] = []
    if not identity.get("color_profile"):
        missing.append("color profile")
    if not identity.get("motion_style"):
        missing.append("motion style")
    if not identity.get("prompt_rules"):
        missing.append("prompt rules")
    weak_scenes = []
    for index, scene in enumerate(storyboard):
        prompt = " ".join(str(scene.get(key, "") or "") for key in ["image_prompt", "expanded_prompt", "scene_visual", "lighting"])
        if identity.get("color_profile") and identity["color_profile"].replace("_", " ") not in prompt.lower():
            weak_scenes.append(str(scene.get("scene") or index + 1))
    score = max(0, 100 - len(missing) * 20 - len(weak_scenes) * 5)
    return {
        "ok": score >= 70,
        "message": "Style consistency checked",
        "data": {
            "score": score,
            "missing_identity_fields": missing,
            "scenes_needing_style_review": weak_scenes,
            "visual_identity": identity,
        },
        "error": "",
    }
