from __future__ import annotations

from typing import Any, Dict, List


def analyze_scene_rhythm(project: Dict[str, Any]) -> Dict[str, Any]:
    storyboard = ((project.get("mv", {}) or {}).get("storyboard", []) or [])
    rows: List[Dict[str, Any]] = []
    fast = 0
    slow = 0
    for index, scene in enumerate(storyboard):
        duration = float(scene.get("duration_seconds") or 5)
        text = " ".join(str(scene.get(key, "") or "").lower() for key in ["section", "emotion", "pacing_note", "transition"])
        density = _cut_density(duration, text)
        fast += 1 if density == "fast" else 0
        slow += 1 if density == "slow" else 0
        rows.append(
            {
                "scene_id": str(scene.get("scene") or index + 1),
                "duration_seconds": duration,
                "cut_density": density,
                "pacing_balance": _balance(density, text),
                "chorus_intensity": _chorus_intensity(text),
                "breathing_room": "needs more hold" if density == "fast" and any(w in text for w in ["sad", "bridge", "lonely"]) else "ok",
            }
        )
    overall = "too fast" if fast > slow + 3 else "too slow" if slow > fast + 4 else "balanced"
    return {"ok": True, "message": "Scene rhythm analyzed", "data": {"overall": overall, "rows": rows}, "error": ""}


def _cut_density(duration: float, text: str) -> str:
    if duration <= 3 or any(word in text for word in ["hook", "chorus", "fast", "beat"]):
        return "fast"
    if duration >= 7 or any(word in text for word in ["bridge", "outro", "slow", "empty"]):
        return "slow"
    return "medium"


def _balance(density: str, text: str) -> str:
    if density == "fast" and any(word in text for word in ["hook", "chorus"]):
        return "good intensity"
    if density == "slow" and any(word in text for word in ["bridge", "sad", "lonely"]):
        return "good breathing room"
    if density == "fast":
        return "watch for emotional rush"
    if density == "slow":
        return "watch for drag"
    return "balanced"


def _chorus_intensity(text: str) -> str:
    if "final chorus" in text:
        return "maximum"
    if "chorus" in text or "hook" in text:
        return "high"
    return "normal"
