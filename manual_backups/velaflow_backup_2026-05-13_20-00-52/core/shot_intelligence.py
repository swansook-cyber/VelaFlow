from __future__ import annotations

from typing import Any, Dict, List


def recommend_shot_types(project: Dict[str, Any]) -> Dict[str, Any]:
    storyboard = ((project.get("mv", {}) or {}).get("storyboard", []) or [])
    rows: List[Dict[str, Any]] = []
    for index, scene in enumerate(storyboard):
        scene_id = str(scene.get("scene") or index + 1)
        text = _text(scene)
        shot = _shot_type(text)
        rows.append(
            {
                "scene_id": scene_id,
                "shot_type": shot,
                "reason": _reason(shot),
                "prompt_phrase": f"{shot} shot, {scene.get('scene_visual', '')}".strip(", "),
            }
        )
    return {"ok": True, "message": "Shot type recommendations created", "data": {"shots": rows}, "error": ""}


def apply_shot_types(project: Dict[str, Any]) -> Dict[str, Any]:
    shots = {item["scene_id"]: item for item in recommend_shot_types(project)["data"]["shots"]}
    changed = []
    for index, scene in enumerate(project.setdefault("mv", {}).setdefault("storyboard", [])):
        scene_id = str(scene.get("scene") or index + 1)
        shot = shots.get(scene_id)
        if not shot:
            continue
        scene["shot_type"] = shot["shot_type"]
        scene["director_shot_note"] = shot["reason"]
        changed.append(scene_id)
    return {"ok": True, "message": f"Applied shot intelligence to {len(changed)} scenes", "data": {"project": project, "scenes": changed}, "error": ""}


def _text(scene: Dict[str, Any]) -> str:
    return " ".join(str(scene.get(key, "") or "").lower() for key in ["emotion", "camera", "pacing_note", "section", "lyric_part", "scene_visual"])


def _shot_type(text: str) -> str:
    if any(word in text for word in ["isolated", "lonely", "alone", "เหงา", "คิดถึง"]):
        return "wide"
    if any(word in text for word in ["cry", "sad", "emotional", "เจ็บ", "ใจ"]):
        return "close-up"
    if "bridge" in text or "empty" in text:
        return "silhouette"
    if any(word in text for word in ["argument", "memory", "lover", "behind"]):
        return "over-shoulder"
    if any(word in text for word in ["raw", "run", "panic", "handheld"]):
        return "handheld"
    if any(word in text for word in ["chorus", "hook", "final chorus"]):
        return "medium"
    return "medium"


def _reason(shot: str) -> str:
    return {
        "close-up": "Use facial detail to carry emotional weight.",
        "medium": "Balance performance energy with character presence.",
        "wide": "Show isolation and emotional distance.",
        "over-shoulder": "Add memory, relationship, or point-of-view tension.",
        "silhouette": "Reduce detail and make the scene feel symbolic.",
        "handheld": "Add raw instability and immediacy.",
    }.get(shot, "Balanced cinematic coverage.")
