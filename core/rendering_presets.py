from __future__ import annotations

from typing import Dict, List


RENDERING_PROVIDER_PRESETS: Dict[str, Dict[str, object]] = {
    "Runway": {
        "provider_name": "Runway",
        "recommended_aspect_ratios": ["16:9", "9:16", "1:1"],
        "recommended_duration": "5s-10s",
        "cinematic_strength": "high",
        "motion_strength": "medium",
        "prompt_style": "cinematic, concise, shot-based image-to-video prompt",
        "notes": "Good general-purpose cinematic and social video workflow target.",
    },
    "Kling": {
        "provider_name": "Kling",
        "recommended_aspect_ratios": ["9:16", "16:9"],
        "recommended_duration": "5s-10s",
        "cinematic_strength": "high",
        "motion_strength": "high",
        "prompt_style": "clear subject action, camera motion, environment, and realism",
        "notes": "Useful for stronger movement and emotionally directed shots.",
    },
    "Veo": {
        "provider_name": "Veo",
        "recommended_aspect_ratios": ["16:9", "9:16"],
        "recommended_duration": "10s-15s",
        "cinematic_strength": "very high",
        "motion_strength": "medium",
        "prompt_style": "director-style scene description with camera, lighting, pacing, and mood",
        "notes": "Prepared as a high-quality cinematic provider target.",
    },
    "PixVerse": {
        "provider_name": "PixVerse",
        "recommended_aspect_ratios": ["9:16", "16:9", "1:1"],
        "recommended_duration": "5s",
        "cinematic_strength": "medium",
        "motion_strength": "high",
        "prompt_style": "short, direct, action-first prompt optimized for social clips",
        "notes": "Good for quick short-form motion concepts.",
    },
    "Pika": {
        "provider_name": "Pika",
        "recommended_aspect_ratios": ["9:16", "1:1", "16:9"],
        "recommended_duration": "5s",
        "cinematic_strength": "medium",
        "motion_strength": "medium",
        "prompt_style": "simple visual prompt with style, subject, and motion direction",
        "notes": "Useful for lightweight creative motion experiments.",
    },
    "Luma": {
        "provider_name": "Luma",
        "recommended_aspect_ratios": ["16:9", "9:16"],
        "recommended_duration": "5s-10s",
        "cinematic_strength": "high",
        "motion_strength": "medium",
        "prompt_style": "realistic camera language with spatial detail and natural motion",
        "notes": "Prepared for realistic cinematic shots and camera movement.",
    },
}

ASPECT_RATIOS = ["9:16", "16:9", "1:1"]
RENDER_DURATIONS = ["5s", "10s", "15s"]
RENDER_QUALITIES = ["Draft", "Standard", "Cinematic"]
MOTION_INTENSITIES = ["Low", "Medium", "High"]

RENDER_PRESET_BUNDLES: Dict[str, Dict[str, object]] = {
    "TikTok Viral": {
        "camera_preset": "TikTok Creator",
        "lighting_preset": "Natural Daylight",
        "motion_preset": "Fast TikTok Cuts",
        "visual_mood": "Viral",
        "aspect_ratio": "9:16",
        "duration": "15s",
        "quality": "Draft",
        "motion_intensity": "High",
        "provider": "PixVerse",
    },
    "Cinematic Sad": {
        "camera_preset": "Slow Push",
        "lighting_preset": "Moody Dark",
        "motion_preset": "Slow Cinematic",
        "visual_mood": "Emotional",
        "aspect_ratio": "16:9",
        "duration": "10s",
        "quality": "Cinematic",
        "motion_intensity": "Medium",
        "provider": "Veo",
    },
    "Luxury Product": {
        "camera_preset": "Close-up",
        "lighting_preset": "Clean Studio",
        "motion_preset": "Smooth Product Showcase",
        "visual_mood": "Luxury",
        "aspect_ratio": "9:16",
        "duration": "10s",
        "quality": "Standard",
        "motion_intensity": "Medium",
        "provider": "Runway",
    },
    "Podcast Dark Office": {
        "camera_preset": "Documentary",
        "lighting_preset": "Office Fluorescent",
        "motion_preset": "Documentary Realism",
        "visual_mood": "Dark Office",
        "aspect_ratio": "9:16",
        "duration": "15s",
        "quality": "Standard",
        "motion_intensity": "Low",
        "provider": "Luma",
    },
    "Cozy Story": {
        "camera_preset": "Cinematic",
        "lighting_preset": "Soft Indoor",
        "motion_preset": "Dreamy",
        "visual_mood": "Cozy",
        "aspect_ratio": "9:16",
        "duration": "15s",
        "quality": "Standard",
        "motion_intensity": "Medium",
        "provider": "Pika",
    },
    "Emotional Dark": {
        "camera_preset": "Slow Push",
        "lighting_preset": "Moody Dark",
        "motion_preset": "Emotional Shaky Cam",
        "visual_mood": "Lonely",
        "aspect_ratio": "9:16",
        "duration": "10s",
        "quality": "Cinematic",
        "motion_intensity": "Medium",
        "provider": "Veo",
    },
    "Podcast Rant": {
        "camera_preset": "Documentary",
        "lighting_preset": "Office Fluorescent",
        "motion_preset": "Documentary Realism",
        "visual_mood": "Dark Office",
        "aspect_ratio": "9:16",
        "duration": "10s",
        "quality": "Draft",
        "motion_intensity": "Medium",
        "provider": "Luma",
    },
    "Realistic Cinematic": {
        "camera_preset": "Cinematic",
        "lighting_preset": "Natural Daylight",
        "motion_preset": "Realistic Cinematic",
        "visual_mood": "Premium",
        "aspect_ratio": "9:16",
        "duration": "10s",
        "quality": "Cinematic",
        "motion_intensity": "Medium",
        "provider": "Runway",
    },
    "Anime MV": {
        "camera_preset": "Cinematic",
        "lighting_preset": "Neon Night",
        "motion_preset": "Dreamy",
        "visual_mood": "Anime Energy",
        "aspect_ratio": "9:16",
        "duration": "10s",
        "quality": "Standard",
        "motion_intensity": "High",
        "provider": "Pika",
    },
    "Fast Affiliate": {
        "camera_preset": "TikTok Creator",
        "lighting_preset": "Clean Studio",
        "motion_preset": "Fast TikTok Cuts",
        "visual_mood": "Affiliate Fast",
        "aspect_ratio": "9:16",
        "duration": "5s",
        "quality": "Draft",
        "motion_intensity": "High",
        "provider": "PixVerse",
    },
    "Meme Chaos": {
        "camera_preset": "TikTok Creator",
        "lighting_preset": "Natural Daylight",
        "motion_preset": "Meme Chaos",
        "visual_mood": "Meme",
        "aspect_ratio": "9:16",
        "duration": "5s",
        "quality": "Draft",
        "motion_intensity": "High",
        "provider": "PixVerse",
    },
}


def list_rendering_providers() -> List[str]:
    return list(RENDERING_PROVIDER_PRESETS)


def get_rendering_provider_preset(provider_name: str | None = None) -> Dict[str, object]:
    return RENDERING_PROVIDER_PRESETS.get(provider_name or "", RENDERING_PROVIDER_PRESETS["Runway"])


def list_render_preset_bundles() -> List[str]:
    return list(RENDER_PRESET_BUNDLES)


def get_render_preset_bundle(bundle_name: str | None = None) -> Dict[str, object]:
    return RENDER_PRESET_BUNDLES.get(bundle_name or "", RENDER_PRESET_BUNDLES["TikTok Viral"])
