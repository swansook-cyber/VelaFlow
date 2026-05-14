from __future__ import annotations

from typing import Any, Dict, List


def analyze_narrative_arc(project: Dict[str, Any]) -> Dict[str, Any]:
    storyboard = ((project.get("mv", {}) or {}).get("storyboard", []) or [])
    total = max(1, len(storyboard))
    rows: List[Dict[str, Any]] = []
    for index, scene in enumerate(storyboard):
        scene_id = str(scene.get("scene") or index + 1)
        text = _text(scene)
        position = index / max(1, total - 1)
        role = classify_scene_role(scene, index, total)
        tension = _tension(text, position, role)
        rows.append(
            {
                "scene_id": scene_id,
                "position": round(position, 3),
                "narrative_role": role,
                "tension": tension,
                "story_function": _story_function(role),
                "recommended_transition": _transition(role),
                "recommended_motion": _motion(role),
                "recommended_color": _color(role, text),
            }
        )
    if not rows:
        rows = [{"scene_id": "1", "position": 0, "narrative_role": "setup", "tension": 20, "story_function": "establish the emotional world", "recommended_transition": "fade", "recommended_motion": "slow_zoom_in", "recommended_color": "film_look"}]
    peak = max(rows, key=lambda item: item["tension"])
    return {
        "ok": True,
        "message": "Narrative arc analyzed offline",
        "data": {
            "beginning": rows[0]["scene_id"],
            "tension_scene": next((row["scene_id"] for row in rows if row["narrative_role"] == "emotional_transition"), rows[0]["scene_id"]),
            "emotional_peak": peak["scene_id"],
            "release": next((row["scene_id"] for row in rows if row["narrative_role"] == "resolution"), rows[-1]["scene_id"]),
            "ending": rows[-1]["scene_id"],
            "rows": rows,
        },
        "error": "",
    }


def classify_scene_role(scene: Dict[str, Any], index: int, total: int) -> str:
    text = _text(scene)
    if index == 0 or "intro" in text:
        return "setup"
    if "final chorus" in text or "climax" in text:
        return "climax"
    if "chorus" in text or "hook" in text:
        return "emotional_peak" if index >= total // 2 else "emotional_transition"
    if "bridge" in text or "empty" in text:
        return "breathing_room"
    if index >= total - 1 or "outro" in text or "ending" in text:
        return "resolution"
    if any(word in text for word in ["build", "pre-chorus", "tension", "hope"]):
        return "emotional_transition"
    return "emotional_transition" if index < total - 2 else "resolution"


def _text(scene: Dict[str, Any]) -> str:
    return " ".join(str(scene.get(key, "") or "").lower() for key in ["section", "emotion", "lyric_part", "subtitle_text", "pacing_note", "scene_visual"])


def _tension(text: str, position: float, role: str) -> int:
    base = 20 + int(position * 35)
    base += {"setup": 0, "emotional_transition": 22, "breathing_room": 8, "emotional_peak": 35, "climax": 45, "resolution": -5}.get(role, 10)
    base += 12 if any(word in text for word in ["cry", "เจ็บ", "miss", "lonely", "regret", "heart"]) else 0
    return max(0, min(100, base))


def _story_function(role: str) -> str:
    return {
        "setup": "establish the emotional world",
        "emotional_transition": "move the character from restraint toward confession",
        "emotional_peak": "make the hook emotionally memorable",
        "climax": "release the strongest feeling of the song",
        "breathing_room": "let the audience sit inside the silence",
        "resolution": "land the final emotional meaning",
    }.get(role, "support the story flow")


def _transition(role: str) -> str:
    return {"setup": "fade", "breathing_room": "emotional dip to black", "climax": "flash cut", "emotional_peak": "flash cut", "resolution": "blur dissolve"}.get(role, "fade")


def _motion(role: str) -> str:
    return {"setup": "slow_zoom_in", "breathing_room": "still", "climax": "hook_energy_zoom", "emotional_peak": "emotional_push_in", "resolution": "slow_zoom_out"}.get(role, "cinematic_drift")


def _color(role: str, text: str) -> str:
    if any(word in text for word in ["night", "neon"]):
        return "neon"
    return {"breathing_room": "moody", "climax": "film_look", "emotional_peak": "film_look", "resolution": "warm"}.get(role, "film_look")
