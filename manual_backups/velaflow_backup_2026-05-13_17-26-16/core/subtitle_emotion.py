from __future__ import annotations

from typing import Any, Dict, List

from core.hook_intelligence import analyze_hooks
from core.performance_emotion import map_performance_emotions


def map_dynamic_subtitle_emotion(project: Dict[str, Any]) -> Dict[str, Any]:
    performance = {row["scene_id"]: row for row in map_performance_emotions(project)["data"]["rows"]}
    hooks = {row["scene_id"]: row for row in analyze_hooks(project)["data"]["candidates"]}
    rows: List[Dict[str, str]] = []
    storyboard = ((project.get("mv", {}) or {}).get("storyboard", []) or [])
    for index, scene in enumerate(storyboard):
        scene_id = str(scene.get("scene") or index + 1)
        perf = performance.get(scene_id, {}).get("performance_emotion", "")
        hook_score = hooks.get(scene_id, {}).get("hook_score", 0)
        style = _style(perf, hook_score)
        rows.append({"scene_id": scene_id, "subtitle_emotion_style": style, "reason": _reason(style), "ass_hint": _ass_hint(style)})
    return {"ok": True, "message": "Dynamic subtitle emotion mapped", "data": {"rows": rows}, "error": ""}


def inject_dynamic_subtitle_emotion(project: Dict[str, Any]) -> Dict[str, Any]:
    rows = {row["scene_id"]: row for row in map_dynamic_subtitle_emotion(project)["data"]["rows"]}
    changed = []
    for index, scene in enumerate(project.setdefault("mv", {}).setdefault("storyboard", [])):
        scene_id = str(scene.get("scene") or index + 1)
        row = rows.get(scene_id)
        if row:
            scene["subtitle_emotion_style"] = row["subtitle_emotion_style"]
            scene["subtitle_ass_hint"] = row["ass_hint"]
            changed.append(scene_id)
    return {"ok": True, "message": f"Injected subtitle emotion into {len(changed)} scenes", "data": {"project": project, "scenes": changed}, "error": ""}


def _style(performance: str, hook_score: int) -> str:
    if hook_score >= 80:
        return "hook glow"
    if performance == "emotional explosion":
        return "large chorus"
    if performance == "silent regret":
        return "whisper"
    if performance == "hopeful ending":
        return "soft warm"
    return "restrained"


def _reason(style: str) -> str:
    return {"hook glow": "hook line should pop visually", "large chorus": "chorus should feel bigger", "whisper": "bridge should fade down", "soft warm": "ending should feel gentle", "restrained": "keep emotion controlled"}.get(style, "")


def _ass_hint(style: str) -> str:
    return {"hook glow": "bold glow, slight scale punch", "large chorus": "larger type, strong fade in", "whisper": "smaller type, lower opacity feel", "soft warm": "warm tone, soft fade", "restrained": "simple bottom subtitle"}.get(style, "simple")
