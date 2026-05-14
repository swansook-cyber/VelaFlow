from __future__ import annotations

from typing import Any, Dict, List

from core.hook_intelligence import analyze_hooks
from core.narrative_arc import analyze_narrative_arc


def analyze_cinematic_beats(project: Dict[str, Any]) -> Dict[str, Any]:
    narrative = {row["scene_id"]: row for row in analyze_narrative_arc(project)["data"]["rows"]}
    hooks = {item["scene_id"]: item for item in analyze_hooks(project)["data"]["candidates"]}
    rows: List[Dict[str, Any]] = []
    storyboard = ((project.get("mv", {}) or {}).get("storyboard", []) or [])
    for index, scene in enumerate(storyboard):
        scene_id = str(scene.get("scene") or index + 1)
        role = narrative.get(scene_id, {}).get("narrative_role", "emotional_transition")
        hook_score = hooks.get(scene_id, {}).get("hook_score", 0)
        rows.append(
            {
                "scene_id": scene_id,
                "emotional_beat": _emotional_beat(role),
                "lyric_beat": _lyric_beat(scene.get("lyric_part") or scene.get("subtitle_text") or "", hook_score),
                "visual_beat": _visual_beat(role, hook_score),
                "sync_action": _sync_action(role, hook_score),
            }
        )
    return {"ok": True, "message": "Cinematic beats analyzed", "data": {"rows": rows}, "error": ""}


def inject_cinematic_beats(project: Dict[str, Any]) -> Dict[str, Any]:
    rows = {row["scene_id"]: row for row in analyze_cinematic_beats(project)["data"]["rows"]}
    changed = []
    for index, scene in enumerate(project.setdefault("mv", {}).setdefault("storyboard", [])):
        scene_id = str(scene.get("scene") or index + 1)
        row = rows.get(scene_id)
        if not row:
            continue
        scene["emotional_beat"] = row["emotional_beat"]
        scene["lyric_beat"] = row["lyric_beat"]
        scene["visual_beat"] = row["visual_beat"]
        scene["beat_sync_note"] = row["sync_action"]
        changed.append(scene_id)
    return {"ok": True, "message": f"Injected cinematic beats into {len(changed)} scenes", "data": {"project": project, "scenes": changed}, "error": ""}


def _emotional_beat(role: str) -> str:
    return {"setup": "withhold", "emotional_transition": "build", "breathing_room": "pause", "emotional_peak": "hit", "climax": "explode", "resolution": "release"}.get(role, "build")


def _lyric_beat(text: str, hook_score: int) -> str:
    if hook_score >= 75:
        return "emphasize hook phrase"
    if len(str(text)) > 80:
        return "split lyric into two beats"
    return "hold lyric as one emotional beat"


def _visual_beat(role: str, hook_score: int) -> str:
    if hook_score >= 75:
        return "push on hook word"
    if role == "breathing_room":
        return "hold still before cut"
    if role == "resolution":
        return "fade after final phrase"
    return "cut on emotional phrase"


def _sync_action(role: str, hook_score: int) -> str:
    if hook_score >= 75:
        return "subtitle glow and zoom should land together"
    if role == "breathing_room":
        return "reduce beat motion and let silence breathe"
    return "align transition to lyric phrase ending"
