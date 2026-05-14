from __future__ import annotations

from typing import Any, Dict, List

from core.narrative_arc import analyze_narrative_arc


def map_performance_emotions(project: Dict[str, Any]) -> Dict[str, Any]:
    narrative = {row["scene_id"]: row for row in analyze_narrative_arc(project)["data"]["rows"]}
    rows: List[Dict[str, Any]] = []
    storyboard = ((project.get("mv", {}) or {}).get("storyboard", []) or [])
    for index, scene in enumerate(storyboard):
        scene_id = str(scene.get("scene") or index + 1)
        text = " ".join(str(scene.get(key, "") or "").lower() for key in ["emotion", "lyric_part", "pacing_note", "section"])
        role = narrative.get(scene_id, {}).get("narrative_role", "emotional_transition")
        performance = _performance(text, role)
        rows.append(
            {
                "scene_id": scene_id,
                "performance_emotion": performance,
                "subtitle_emotion": _subtitle(performance),
                "motion_emotion": _motion(performance),
                "color_emotion": _color(performance),
                "prompt_emotion": _prompt(performance),
            }
        )
    return {"ok": True, "message": "Performance emotion mapped", "data": {"rows": rows}, "error": ""}


def inject_performance_emotions(project: Dict[str, Any]) -> Dict[str, Any]:
    rows = {row["scene_id"]: row for row in map_performance_emotions(project)["data"]["rows"]}
    changed = []
    for index, scene in enumerate(project.setdefault("mv", {}).setdefault("storyboard", [])):
        scene_id = str(scene.get("scene") or index + 1)
        row = rows.get(scene_id)
        if not row:
            continue
        scene["performance_emotion"] = row["performance_emotion"]
        scene["subtitle_emotion_style"] = row["subtitle_emotion"]
        scene["motion_emotion"] = row["motion_emotion"]
        scene["color_emotion"] = row["color_emotion"]
        scene["prompt_emotion_note"] = row["prompt_emotion"]
        changed.append(scene_id)
    return {"ok": True, "message": f"Injected performance emotion into {len(changed)} scenes", "data": {"project": project, "scenes": changed}, "error": ""}


def _performance(text: str, role: str) -> str:
    if role in {"climax", "emotional_peak"} or any(word in text for word in ["final chorus", "explode", "power"]):
        return "emotional explosion"
    if "bridge" in text or role == "breathing_room":
        return "silent regret"
    if any(word in text for word in ["hope", "accept", "ending", "outro"]):
        return "hopeful ending"
    if any(word in text for word in ["sad", "lonely", "miss", "เจ็บ", "เหงา"]):
        return "restrained sadness"
    return "restrained sadness"


def _subtitle(performance: str) -> str:
    return {"emotional explosion": "large chorus emphasis", "silent regret": "whisper subtitle style", "hopeful ending": "soft warm subtitle", "restrained sadness": "small restrained subtitle"}.get(performance, "cinematic")


def _motion(performance: str) -> str:
    return {"emotional explosion": "hook_energy_zoom", "silent regret": "still", "hopeful ending": "slow_zoom_out", "restrained sadness": "emotional_push_in"}.get(performance, "cinematic_drift")


def _color(performance: str) -> str:
    return {"emotional explosion": "film_look", "silent regret": "moody", "hopeful ending": "warm", "restrained sadness": "moody"}.get(performance, "film_look")


def _prompt(performance: str) -> str:
    return f"performance direction: {performance}, natural Thai music video acting, emotionally believable"
