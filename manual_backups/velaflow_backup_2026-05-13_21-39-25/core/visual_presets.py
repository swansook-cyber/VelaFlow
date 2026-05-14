from __future__ import annotations


CAMERA_PRESETS = {
    "Handheld": "natural handheld camera, human and intimate movement",
    "Cinematic": "cinematic camera language, composed framing, film-like movement",
    "Slow Push": "slow push-in camera move toward the subject",
    "Close-up": "emotional close-up framing with shallow depth of field",
    "Wide Establishing": "wide establishing shot that clearly shows location and atmosphere",
    "Drone": "smooth aerial or high-angle establishing movement",
    "Documentary": "observational documentary camera, realistic and grounded",
    "TikTok Creator": "vertical creator-style camera, close and direct to audience",
}

LIGHTING_PRESETS = {
    "Soft Indoor": "soft indoor practical lighting, gentle shadows",
    "Sunset Golden Hour": "warm golden hour sunset light",
    "Neon Night": "neon night lighting with colorful reflections",
    "Moody Dark": "low-key moody lighting with cinematic contrast",
    "Clean Studio": "clean studio lighting, bright and controlled",
    "Office Fluorescent": "office fluorescent lighting, realistic work environment",
    "Natural Daylight": "natural daylight, clean realistic ambience",
}

MOTION_PRESETS = {
    "Slow Cinematic": "slow cinematic pacing with smooth motion",
    "Fast TikTok Cuts": "fast TikTok-style cuts with punchy pacing",
    "Dreamy": "dreamy floating movement with soft transitions",
    "Emotional Shaky Cam": "soft emotional shaky cam, intimate and human",
    "Documentary Realism": "realistic documentary motion with natural imperfections",
    "Smooth Product Showcase": "smooth product showcase motion with clean detail shots",
}

VISUAL_MOOD_PRESETS = {
    "Emotional": "emotional, heartfelt, relatable atmosphere",
    "Lonely": "lonely, quiet, reflective visual mood",
    "Energetic": "energetic, bright, fast-moving mood",
    "Premium": "premium, polished, high-quality visual mood",
    "Viral": "viral, attention-grabbing, high-retention visual mood",
    "Dark Office": "dark office mood, tired corporate realism",
    "Cozy": "cozy, warm, friendly atmosphere",
    "Luxury": "luxury, elegant, refined visual mood",
}


DEFAULT_VISUAL_SETTINGS = {
    "camera_preset": "Cinematic",
    "lighting_preset": "Soft Indoor",
    "motion_preset": "Slow Cinematic",
    "visual_mood": "Emotional",
}


def list_camera_presets() -> list[str]:
    return list(CAMERA_PRESETS)


def list_lighting_presets() -> list[str]:
    return list(LIGHTING_PRESETS)


def list_motion_presets() -> list[str]:
    return list(MOTION_PRESETS)


def list_visual_mood_presets() -> list[str]:
    return list(VISUAL_MOOD_PRESETS)


def normalize_visual_settings(settings: dict | None = None) -> dict:
    data = {**DEFAULT_VISUAL_SETTINGS, **(settings or {})}
    if data.get("camera_preset") not in CAMERA_PRESETS:
        data["camera_preset"] = DEFAULT_VISUAL_SETTINGS["camera_preset"]
    if data.get("lighting_preset") not in LIGHTING_PRESETS:
        data["lighting_preset"] = DEFAULT_VISUAL_SETTINGS["lighting_preset"]
    if data.get("motion_preset") not in MOTION_PRESETS:
        data["motion_preset"] = DEFAULT_VISUAL_SETTINGS["motion_preset"]
    if data.get("visual_mood") not in VISUAL_MOOD_PRESETS:
        data["visual_mood"] = DEFAULT_VISUAL_SETTINGS["visual_mood"]
    data["camera_description"] = CAMERA_PRESETS[data["camera_preset"]]
    data["lighting_description"] = LIGHTING_PRESETS[data["lighting_preset"]]
    data["motion_description"] = MOTION_PRESETS[data["motion_preset"]]
    data["visual_mood_description"] = VISUAL_MOOD_PRESETS[data["visual_mood"]]
    return data
