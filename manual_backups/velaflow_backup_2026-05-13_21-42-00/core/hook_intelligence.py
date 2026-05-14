from __future__ import annotations

import re
from typing import Any, Dict, List

from core.scene_scoring import score_project_scenes


def analyze_hooks(project: Dict[str, Any], limit: int = 8) -> Dict[str, Any]:
    storyboard = ((project.get("mv", {}) or {}).get("storyboard", []) or [])
    candidates: List[Dict[str, Any]] = []
    scene_scores = {item["scene_id"]: item for item in score_project_scenes(project)}
    for index, scene in enumerate(storyboard):
        scene_id = str(scene.get("scene") or index + 1)
        text = scene.get("subtitle_text") or scene.get("lyric_part") or ""
        for line in _lines(text):
            score = _hook_score(line, scene, scene_scores.get(scene_id, {}))
            candidates.append(
                {
                    "scene_id": scene_id,
                    "text": line,
                    "hook_score": score,
                    "subtitle_emphasis": _emphasis(line, score),
                    "shorts_ready": score >= 70,
                    "recommended_motion": "hook_energy_zoom" if score >= 75 else "emotional_push_in",
                    "recommended_subtitle": "tiktok_bold" if score >= 70 else "cinematic",
                }
            )
    candidates = sorted(candidates, key=lambda item: item["hook_score"], reverse=True)[: max(1, int(limit or 8))]
    return {"ok": True, "message": "Hook intelligence analyzed offline", "data": {"candidates": candidates}, "error": ""}


def _lines(text: str) -> List[str]:
    parts = [part.strip() for part in re.split(r"[\n\r]+|[.!?]", str(text or "")) if part.strip()]
    return parts or ([str(text).strip()] if str(text).strip() else [])


def _hook_score(line: str, scene: Dict[str, Any], score: Dict[str, Any]) -> int:
    text = " ".join([line, str(scene.get("emotion", "")), str(scene.get("pacing_note", "")), str(scene.get("section", ""))]).lower()
    value = 25 + min(25, len(line.strip()) // 3)
    value += 18 if any(word in text for word in ["hook", "chorus", "final chorus", "drop"]) else 0
    value += 12 if any(word in text for word in ["รัก", "คิดถึง", "เจ็บ", "เหงา", "ใจ", "คืน"]) else 0
    value += 12 if any(word in text for word in ["love", "miss", "heart", "lonely", "cry", "viral"]) else 0
    value += int(score.get("hook_potential", 0) * 0.25)
    return max(0, min(100, value))


def _emphasis(line: str, score: int) -> str:
    if score >= 80:
        return "bold center punch-in"
    if len(line) > 70:
        return "split into two subtitle beats"
    if score >= 65:
        return "highlight final phrase"
    return "soft bottom subtitle"
