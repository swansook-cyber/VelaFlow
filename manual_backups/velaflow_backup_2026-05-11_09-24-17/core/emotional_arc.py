from __future__ import annotations

from typing import Any, Dict, List


LOW_WORDS = {"intro", "verse", "lonely", "sad", "quiet", "soft", "miss", "regret", "night"}
RISE_WORDS = {"pre-chorus", "build", "rising", "hope", "drum", "tension"}
HIGH_WORDS = {"chorus", "hook", "final chorus", "climax", "drop", "power", "energy", "viral"}
ENDING_WORDS = {"outro", "ending", "fade", "goodbye", "accept", "release"}


def analyze_emotional_arc(project: Dict[str, Any]) -> Dict[str, Any]:
    storyboard = ((project.get("mv", {}) or {}).get("storyboard", []) or [])
    points: List[Dict[str, Any]] = []
    for index, scene in enumerate(storyboard):
        text = _scene_text(scene)
        energy = _score_energy(text, index, len(storyboard))
        section = _section(text)
        points.append(
            {
                "scene_id": str(scene.get("scene") or index + 1),
                "section": section,
                "energy": energy,
                "mood": scene.get("emotion", ""),
                "recommended_pacing": _pacing(section, energy),
                "recommended_transition": _transition(section, energy),
                "recommended_color": _color(text, section),
                "recommended_motion": _motion(section, energy, text),
            }
        )
    if not points:
        points = [{"scene_id": "1", "section": "intro", "energy": 25, "mood": "neutral", "recommended_pacing": "slow", "recommended_transition": "fade", "recommended_color": "film_look", "recommended_motion": "slow_zoom_in"}]
    climax = max(points, key=lambda item: item["energy"])
    ending = points[-1]
    return {
        "ok": True,
        "message": "Emotional arc analyzed offline",
        "data": {
            "intro_mood": points[0]["mood"] or points[0]["section"],
            "emotional_rise": _rise_shape(points),
            "climax_scene": climax["scene_id"],
            "climax_energy": climax["energy"],
            "ending_tone": ending["mood"] or ending["section"],
            "points": points,
        },
        "error": "",
    }


def _scene_text(scene: Dict[str, Any]) -> str:
    keys = ["section", "lyric_part", "subtitle_text", "emotion", "camera", "pacing_note", "transition", "scene_visual"]
    return " ".join(str(scene.get(key, "") or "").lower() for key in keys)


def _score_energy(text: str, index: int, total: int) -> int:
    score = 25 + min(20, index * 4)
    score += sum(6 for word in LOW_WORDS if word in text)
    score += sum(12 for word in RISE_WORDS if word in text)
    score += sum(18 for word in HIGH_WORDS if word in text)
    score -= 10 if any(word in text for word in ENDING_WORDS) else 0
    if total and index >= total - 2 and "chorus" in text:
        score += 15
    return max(0, min(100, score))


def _section(text: str) -> str:
    if "final chorus" in text:
        return "final_chorus"
    if "chorus" in text or "hook" in text:
        return "hook"
    if "bridge" in text:
        return "bridge"
    if "intro" in text:
        return "intro"
    if "outro" in text or "ending" in text:
        return "outro"
    if "pre-chorus" in text:
        return "rise"
    if "verse" in text:
        return "verse"
    return "scene"


def _pacing(section: str, energy: int) -> str:
    if section in {"hook", "final_chorus"} or energy >= 80:
        return "fast expressive cuts"
    if section == "bridge":
        return "slow emotional hold"
    if energy <= 40:
        return "slow breathing pace"
    return "medium cinematic pace"


def _transition(section: str, energy: int) -> str:
    if section in {"hook", "final_chorus"} or energy >= 80:
        return "flash cut"
    if section == "bridge":
        return "emotional dip to black"
    if energy <= 45:
        return "blur dissolve"
    return "fade"


def _color(text: str, section: str) -> str:
    if any(word in text for word in ["night", "neon", "city", "viral"]):
        return "neon"
    if any(word in text for word in ["sad", "lonely", "cry", "miss", "bridge"]):
        return "moody"
    if section in {"hook", "final_chorus"}:
        return "film_look"
    return "film_look"


def _motion(section: str, energy: int, text: str) -> str:
    if section in {"hook", "final_chorus"} or energy >= 82:
        return "hook_energy_zoom"
    if "handheld" in text:
        return "handheld_soft"
    if any(word in text for word in ["close", "cry", "lonely", "miss", "emotional"]):
        return "emotional_push_in"
    if energy <= 40:
        return "slow_zoom_in"
    return "cinematic_drift"


def _rise_shape(points: List[Dict[str, Any]]) -> str:
    if len(points) < 2:
        return "single scene"
    first = points[0]["energy"]
    peak = max(item["energy"] for item in points)
    last = points[-1]["energy"]
    if peak - first >= 35 and last >= peak - 15:
        return "rising to strong ending"
    if peak - first >= 35:
        return "rising then release"
    if peak < 60:
        return "low restrained arc"
    return "balanced wave"
