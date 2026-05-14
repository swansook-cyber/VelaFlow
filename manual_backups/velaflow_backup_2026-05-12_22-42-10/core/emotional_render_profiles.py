from __future__ import annotations

from typing import Any, Dict, List


EMOTIONAL_RENDER_PROFILES: Dict[str, Dict[str, str]] = {
    "heartbreak": {"render_profile": "Cinematic", "color_grade": "moody", "motion_style": "emotional_push_in", "subtitle_style": "cinematic"},
    "nostalgic": {"render_profile": "Cinematic", "color_grade": "warm", "motion_style": "cinematic_drift", "subtitle_style": "cinematic"},
    "uplifting": {"render_profile": "Standard", "color_grade": "warm", "motion_style": "slow_zoom_out", "subtitle_style": "simple"},
    "lonely night": {"render_profile": "Cinematic", "color_grade": "neon", "motion_style": "slow_zoom_in", "subtitle_style": "cinematic"},
    "emotional explosion": {"render_profile": "TikTok Fast", "color_grade": "film_look", "motion_style": "hook_energy_zoom", "subtitle_style": "tiktok_bold"},
}


def list_emotional_render_profiles() -> List[Dict[str, str]]:
    return [{"name": name, **profile} for name, profile in EMOTIONAL_RENDER_PROFILES.items()]


def recommend_emotional_render_profile(project: Dict[str, Any]) -> Dict[str, Any]:
    text = " ".join(str(value or "") for value in (project.get("song", {}) or {}).values()).lower()
    storyboard_text = " ".join(
        " ".join(str(scene.get(key, "") or "") for key in ["emotion", "lyric_part", "pacing_note"]).lower()
        for scene in ((project.get("mv", {}) or {}).get("storyboard", []) or [])
    )
    combined = f"{text} {storyboard_text}"
    if any(word in combined for word in ["explode", "final chorus", "power", "viral"]):
        name = "emotional explosion"
    elif any(word in combined for word in ["night", "neon", "lonely", "เหงา"]):
        name = "lonely night"
    elif any(word in combined for word in ["hope", "uplift", "ยิ้ม", "เริ่มใหม่"]):
        name = "uplifting"
    elif any(word in combined for word in ["memory", "nostalgic", "คิดถึง"]):
        name = "nostalgic"
    else:
        name = "heartbreak"
    return {"ok": True, "message": "Emotional render profile recommended", "data": {"name": name, "profile": EMOTIONAL_RENDER_PROFILES[name]}, "error": ""}


def apply_emotional_render_profile(project: Dict[str, Any], name: str | None = None) -> Dict[str, Any]:
    if not name:
        name = recommend_emotional_render_profile(project)["data"]["name"]
    profile = EMOTIONAL_RENDER_PROFILES.get(name)
    if not profile:
        return {"ok": False, "message": "Emotional render profile not found", "data": {}, "error": "missing_profile"}
    project.setdefault("settings", {})
    project["settings"]["emotional_render_profile"] = name
    project["settings"]["render_profile"] = profile["render_profile"]
    project["settings"]["color_profile"] = profile["color_grade"]
    project["settings"]["motion_style"] = profile["motion_style"]
    project["settings"]["subtitle_style"] = profile["subtitle_style"]
    return {"ok": True, "message": f"Applied emotional render profile: {name}", "data": {"project": project, "profile": profile}, "error": ""}
