from __future__ import annotations

from typing import Any, Dict, List


CAMERA_LANGUAGE = {
    "slow push in": "slow dolly toward the subject, emotional pressure rising",
    "emotional drift": "gentle floating motion with subtle side drift",
    "static tension": "locked camera, subject holds frame, emotional restraint",
    "whip transition": "fast lateral camera energy for a hard emotional cut",
    "floating cinematic motion": "smooth stabilized glide with dreamy movement",
    "handheld intimacy": "soft handheld micro movement for vulnerability",
}


def recommend_camera_language(project: Dict[str, Any]) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    storyboard = ((project.get("mv", {}) or {}).get("storyboard", []) or [])
    for index, scene in enumerate(storyboard):
        scene_id = str(scene.get("scene") or index + 1)
        text = " ".join(str(scene.get(key, "") or "").lower() for key in ["emotion", "section", "pacing_note", "camera", "lyric_part"])
        language = _select(text)
        rows.append({"scene_id": scene_id, "camera_language": language, "description": CAMERA_LANGUAGE[language], "motion_hint": _motion_hint(language)})
    return {"ok": True, "message": "Camera language recommendations created", "data": {"camera": rows}, "error": ""}


def apply_camera_language(project: Dict[str, Any]) -> Dict[str, Any]:
    camera = {item["scene_id"]: item for item in recommend_camera_language(project)["data"]["camera"]}
    changed = []
    for index, scene in enumerate(project.setdefault("mv", {}).setdefault("storyboard", [])):
        scene_id = str(scene.get("scene") or index + 1)
        item = camera.get(scene_id)
        if not item:
            continue
        scene["camera_language"] = item["camera_language"]
        scene["camera"] = scene.get("camera") or item["camera_language"]
        scene["motion_effect"] = scene.get("motion_effect") or item["motion_hint"]
        changed.append(scene_id)
    return {"ok": True, "message": f"Applied camera language to {len(changed)} scenes", "data": {"project": project, "scenes": changed}, "error": ""}


def _select(text: str) -> str:
    if any(word in text for word in ["hook", "chorus", "final chorus", "energy"]):
        return "whip transition"
    if any(word in text for word in ["sad", "cry", "miss", "lonely", "เจ็บ", "คิดถึง"]):
        return "slow push in"
    if "bridge" in text or "empty" in text:
        return "static tension"
    if "dream" in text or "memory" in text:
        return "floating cinematic motion"
    if "raw" in text or "handheld" in text:
        return "handheld intimacy"
    return "emotional drift"


def _motion_hint(language: str) -> str:
    return {
        "slow push in": "emotional_push_in",
        "emotional drift": "cinematic_drift",
        "static tension": "still",
        "whip transition": "hook_energy_zoom",
        "floating cinematic motion": "cinematic_drift",
        "handheld intimacy": "handheld_soft",
    }.get(language, "cinematic_drift")
