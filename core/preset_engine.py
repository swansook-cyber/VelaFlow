from __future__ import annotations

from copy import deepcopy
from typing import Any


PRESETS: dict[str, dict[str, Any]] = {
    "viral_meme": {
        "label": "🔥 Viral Meme",
        "motion_style": "shake_zoom",
        "subtitle_style": "bold_fast",
        "transition_style": "hard_cut",
        "voice_style": "energetic",
        "pace": "fast",
        "aspect_ratio": "9:16",
        "hook_style": "aggressive",
        "default_duration": 15,
        "description": "Fast, loud, punchy TikTok/Reels hook clip.",
    },
    "emotional_story": {
        "label": "💔 Emotional Story",
        "motion_style": "slow_cinematic",
        "subtitle_style": "soft_fade",
        "transition_style": "cinematic_fade",
        "voice_style": "calm_narrator",
        "pace": "slow",
        "aspect_ratio": "9:16",
        "hook_style": "emotional",
        "default_duration": 30,
        "description": "Soft emotional short story with cinematic movement.",
    },
    "affiliate_sell": {
        "label": "🛍 Affiliate Fast Sell",
        "motion_style": "product_focus",
        "subtitle_style": "cta_bold",
        "transition_style": "fast_cut",
        "voice_style": "sales",
        "pace": "fast",
        "aspect_ratio": "9:16",
        "hook_style": "conversion",
        "default_duration": 20,
        "description": "Product-focused hook clip built for fast conversion.",
    },
    "podcast_drama": {
        "label": "🎙 Podcast Drama",
        "motion_style": "minimal_pan",
        "subtitle_style": "caption_heavy",
        "transition_style": "dark_fade",
        "voice_style": "narrator",
        "pace": "medium",
        "aspect_ratio": "16:9",
        "hook_style": "storytelling",
        "default_duration": 45,
        "description": "Dramatic spoken-story clip with heavy captions.",
    },
    "cute_character": {
        "label": "🐱 Cute Character",
        "motion_style": "bounce",
        "subtitle_style": "cute_pop",
        "transition_style": "cartoon_pop",
        "voice_style": "cute",
        "pace": "fun",
        "aspect_ratio": "9:16",
        "hook_style": "funny",
        "default_duration": 15,
        "description": "Cute viral character clip with playful motion.",
        "image_style": "cute 3D cartoon, colorful, expressive face, TikTok viral, Facebook meme style, consistent character",
        "examples": ["กล้วยพูดได้", "แมวรีวิวของ", "หัวใจบ่นเรื่องความรัก", "สมองเถียงกับหัวใจ", "ไข่ดาวร้องไห้", "ทุเรียนสายดาร์ก"],
    },
    "cinematic_mv": {
        "label": "🎬 Cinematic MV",
        "motion_style": "cinematic_mv",
        "subtitle_style": "minimal",
        "transition_style": "film_fade",
        "voice_style": "music",
        "pace": "dynamic",
        "aspect_ratio": "16:9",
        "hook_style": "music_video",
        "default_duration": 60,
        "description": "Music-video style cinematic hook with dynamic pacing.",
    },
}


def list_presets() -> list[dict[str, Any]]:
    return [{"preset_id": preset_id, **deepcopy(preset)} for preset_id, preset in PRESETS.items()]


def get_preset(preset_id: str | None = None) -> dict[str, Any]:
    key = str(preset_id or "viral_meme").strip()
    preset = PRESETS.get(key) or PRESETS["viral_meme"]
    return {"preset_id": key if key in PRESETS else "viral_meme", **deepcopy(preset)}


def apply_preset_to_project(project: dict[str, Any], preset_id: str) -> dict[str, Any]:
    preset = get_preset(preset_id)
    project.setdefault("hook_clip_studio", {})["creator_outcome_preset"] = preset
    if preset["preset_id"] == "cute_character":
        project.setdefault("image_lab", {})["defaults"] = {
            "style": "colorful cute 3D cartoon",
            "character_consistency": True,
            "prompt_suffix": preset.get("image_style", ""),
        }
    return project


def preset_to_visual_settings(preset: dict[str, Any]) -> dict[str, str]:
    motion_style = str(preset.get("motion_style", "shake_zoom"))
    mood = {
        "slow_cinematic": "Emotional",
        "minimal_pan": "Dark Office",
        "cinematic_mv": "Emotional",
        "product_focus": "Premium",
        "bounce": "Viral",
    }.get(motion_style, "Viral")
    camera = {
        "slow_cinematic": "Slow Push",
        "minimal_pan": "Documentary",
        "cinematic_mv": "Cinematic",
        "product_focus": "Close-up",
        "bounce": "TikTok Creator",
    }.get(motion_style, "TikTok Creator")
    lighting = {
        "slow_cinematic": "Moody Dark",
        "minimal_pan": "Office Fluorescent",
        "cinematic_mv": "Neon Night",
        "product_focus": "Clean Studio",
        "bounce": "Natural Daylight",
    }.get(motion_style, "Natural Daylight")
    motion = {
        "slow_cinematic": "Slow Cinematic",
        "minimal_pan": "Documentary Realism",
        "cinematic_mv": "Slow Cinematic",
        "product_focus": "Smooth Product Showcase",
        "bounce": "Fast TikTok Cuts",
    }.get(motion_style, "Fast TikTok Cuts")
    return {"camera_preset": camera, "lighting_preset": lighting, "motion_preset": motion, "visual_mood": mood}


def preset_to_render_settings(preset: dict[str, Any]) -> dict[str, str]:
    return {
        "provider": "Local FFmpeg",
        "aspect_ratio": str(preset.get("aspect_ratio") or "9:16"),
        "duration": f"{int(preset.get('default_duration') or 15)}s",
        "quality": "Draft",
        "motion_intensity": "High" if preset.get("pace") in {"fast", "fun", "dynamic"} else "Medium",
        "bundle_name": str(preset.get("label") or preset.get("preset_id") or "Creator Outcome Preset"),
    }
