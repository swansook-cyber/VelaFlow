from __future__ import annotations

from typing import Any, Dict, List

from core.asset_library import search_asset_library


def recommend_reusable_scenes(project: Dict[str, Any], limit: int = 8) -> Dict[str, Any]:
    storyboard = ((project.get("mv", {}) or {}).get("storyboard", []) or [])
    recommendations: List[Dict[str, Any]] = []
    for index, scene in enumerate(storyboard):
        scene_id = str(scene.get("scene") or index + 1)
        query_terms = [
            str(scene.get("emotion", "") or ""),
            str(scene.get("lighting", "") or ""),
            str(scene.get("camera", "") or ""),
        ]
        query = " ".join(term for term in query_terms if term).strip()
        matches = search_asset_library(query=query)[:3] if query else []
        if not matches and scene.get("emotion"):
            matches = search_asset_library(emotion=str(scene.get("emotion")))[:3]
        if matches:
            recommendations.append(
                {
                    "scene_id": scene_id,
                    "scene_visual": scene.get("scene_visual", ""),
                    "emotion": scene.get("emotion", ""),
                    "matches": matches,
                    "recommended_action": "reuse_asset_or_prompt",
                }
            )
    return {
        "ok": True,
        "message": "Scene reuse recommendations created",
        "data": {"recommendations": recommendations[: max(1, int(limit or 8))]},
        "error": "",
    }


def apply_prompt_from_library_item(project: Dict[str, Any], item: Dict[str, Any], scene_id: str) -> Dict[str, Any]:
    prompt = item.get("prompt", "")
    if not prompt:
        return {"ok": False, "message": "Library item has no reusable prompt", "data": {}, "error": "missing_prompt"}
    storyboard = project.setdefault("mv", {}).setdefault("storyboard", [])
    for index, scene in enumerate(storyboard):
        if str(scene.get("scene") or index + 1) == str(scene_id):
            scene["image_prompt"] = prompt
            scene["reused_from_asset"] = item.get("id", "")
            return {"ok": True, "message": "Prompt reused for scene", "data": {"scene_id": str(scene_id)}, "error": ""}
    return {"ok": False, "message": "Scene not found", "data": {}, "error": "missing_scene"}
