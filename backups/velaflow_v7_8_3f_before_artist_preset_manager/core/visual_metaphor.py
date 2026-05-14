from __future__ import annotations

from typing import Any, Dict, List


METAPHORS = {
    "restrained sadness": ["rain on window", "empty road", "dim reflection"],
    "emotional explosion": ["neon flare", "wide open street", "burning stage light"],
    "silent regret": ["mirror reflection", "shadow on wall", "unmade bed"],
    "hopeful ending": ["morning light", "open sky", "warm doorway"],
    "lonely night": ["neon street", "closed shop", "wet pavement"],
}


def suggest_visual_metaphors(project: Dict[str, Any]) -> Dict[str, Any]:
    rows: List[Dict[str, str]] = []
    storyboard = ((project.get("mv", {}) or {}).get("storyboard", []) or [])
    for index, scene in enumerate(storyboard):
        scene_id = str(scene.get("scene") or index + 1)
        emotion = str(scene.get("performance_emotion") or scene.get("emotion") or "").lower()
        key = _key(emotion)
        rows.append(
            {
                "scene_id": scene_id,
                "emotion": emotion,
                "metaphors": ", ".join(METAPHORS[key]),
                "prompt_injection": f"visual metaphors: {', '.join(METAPHORS[key])}",
            }
        )
    return {"ok": True, "message": "Visual metaphors suggested", "data": {"rows": rows}, "error": ""}


def inject_visual_metaphors(project: Dict[str, Any]) -> Dict[str, Any]:
    rows = {row["scene_id"]: row for row in suggest_visual_metaphors(project)["data"]["rows"]}
    changed = []
    for index, scene in enumerate(project.setdefault("mv", {}).setdefault("storyboard", [])):
        scene_id = str(scene.get("scene") or index + 1)
        row = rows.get(scene_id)
        if not row:
            continue
        scene["visual_metaphor"] = row["metaphors"]
        prompt = scene.get("image_prompt") or scene.get("expanded_prompt") or ""
        if row["prompt_injection"] not in prompt:
            scene["image_prompt"] = f"{prompt}, {row['prompt_injection']}".strip(", ")
        changed.append(scene_id)
    return {"ok": True, "message": f"Injected visual metaphors into {len(changed)} scenes", "data": {"project": project, "scenes": changed}, "error": ""}


def _key(emotion: str) -> str:
    if any(word in emotion for word in ["explosion", "climax", "chorus"]):
        return "emotional explosion"
    if any(word in emotion for word in ["regret", "silent", "bridge"]):
        return "silent regret"
    if any(word in emotion for word in ["hope", "ending", "warm"]):
        return "hopeful ending"
    if any(word in emotion for word in ["night", "lonely", "เหงา"]):
        return "lonely night"
    return "restrained sadness"
