from __future__ import annotations

from typing import Any, Dict, List

from core.camera_language import recommend_camera_language
from core.scene_rhythm import analyze_scene_rhythm
from core.shot_intelligence import recommend_shot_types


def build_director_notes(project: Dict[str, Any]) -> Dict[str, Any]:
    shots = {item["scene_id"]: item for item in recommend_shot_types(project)["data"]["shots"]}
    camera = {item["scene_id"]: item for item in recommend_camera_language(project)["data"]["camera"]}
    rhythm = {item["scene_id"]: item for item in analyze_scene_rhythm(project)["data"]["rows"]}
    storyboard = ((project.get("mv", {}) or {}).get("storyboard", []) or [])
    notes: List[Dict[str, str]] = []
    for index, scene in enumerate(storyboard):
        scene_id = str(scene.get("scene") or index + 1)
        text = " ".join(str(scene.get(key, "") or "").lower() for key in ["section", "emotion", "pacing_note", "lyric_part"])
        note = _note_text(scene_id, text, shots.get(scene_id, {}), camera.get(scene_id, {}), rhythm.get(scene_id, {}))
        notes.append(
            {
                "scene_id": scene_id,
                "director_note": note,
                "prompt_injection": f"Director note: {note}",
                "motion_injection": camera.get(scene_id, {}).get("motion_hint", ""),
                "subtitle_injection": "emphasize hook line" if any(w in text for w in ["hook", "chorus"]) else "keep subtitle restrained",
                "render_injection": rhythm.get(scene_id, {}).get("cut_density", "medium"),
            }
        )
    return {"ok": True, "message": "Director notes generated", "data": {"notes": notes}, "error": ""}


def inject_director_notes(project: Dict[str, Any]) -> Dict[str, Any]:
    notes = {item["scene_id"]: item for item in build_director_notes(project)["data"]["notes"]}
    changed = []
    for index, scene in enumerate(project.setdefault("mv", {}).setdefault("storyboard", [])):
        scene_id = str(scene.get("scene") or index + 1)
        note = notes.get(scene_id)
        if not note:
            continue
        scene["director_note"] = note["director_note"]
        scene["prompt_director_note"] = note["prompt_injection"]
        scene["motion_director_note"] = note["motion_injection"]
        scene["subtitle_director_note"] = note["subtitle_injection"]
        scene["render_director_note"] = note["render_injection"]
        changed.append(scene_id)
    return {"ok": True, "message": f"Injected director notes into {len(changed)} scenes", "data": {"project": project, "scenes": changed}, "error": ""}


def _note_text(scene_id: str, text: str, shot: Dict[str, str], camera: Dict[str, str], rhythm: Dict[str, str]) -> str:
    if "bridge" in text:
        mood = "Bridge should feel empty and emotionally suspended."
    elif "final chorus" in text:
        mood = "Final chorus should explode emotionally without losing character focus."
    elif any(w in text for w in ["sad", "lonely", "เหงา"]):
        mood = f"Scene {scene_id} should feel isolated and intimate."
    elif any(w in text for w in ["hook", "chorus"]):
        mood = f"Scene {scene_id} should feel immediate and memorable."
    else:
        mood = f"Scene {scene_id} should keep the story clear and cinematic."
    return f"{mood} Use {shot.get('shot_type', 'medium')} framing with {camera.get('camera_language', 'emotional drift')} and {rhythm.get('cut_density', 'medium')} rhythm."
