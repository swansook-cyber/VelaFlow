from typing import Any, Dict


RENDER_PROFILES: Dict[str, Dict[str, Any]] = {
    "Draft": {
        "description": "Fast preview render",
        "fps": 24,
        "crf": 28,
        "preset": "veryfast",
        "motion_style": "auto",
        "subtitle_mode": "simple",
        "transition_mode": "none",
        "color_grade": "none",
        "beat_sync": False,
        "audio_reactive": False,
        "audio_fade_seconds": 0.6,
        "scale_factor": 0.5,
    },
    "Standard": {
        "description": "Balanced YouTube render",
        "fps": 30,
        "crf": 23,
        "preset": "medium",
        "motion_style": "auto",
        "subtitle_mode": "simple",
        "transition_mode": "fade",
        "color_grade": "film_look",
        "beat_sync": True,
        "audio_reactive": True,
        "audio_fade_seconds": 1.2,
        "scale_factor": 1.0,
    },
    "TikTok Fast": {
        "description": "Fast hook-first vertical render with punchy subtitles and beat-aware motion",
        "fps": 30,
        "crf": 22,
        "preset": "fast",
        "motion_style": "hook_energy_zoom",
        "subtitle_mode": "tiktok_bold",
        "transition_mode": "flash cut",
        "color_grade": "neon",
        "beat_sync": True,
        "audio_reactive": True,
        "audio_fade_seconds": 0.45,
        "scale_factor": 1.0,
    },
    "Cinematic": {
        "description": "Smooth emotional pacing with soft subtitles and a light film look",
        "fps": 30,
        "crf": 18,
        "preset": "slow",
        "motion_style": "cinematic_drift",
        "subtitle_mode": "cinematic",
        "transition_mode": "emotional dip to black",
        "color_grade": "film_look",
        "beat_sync": False,
        "audio_reactive": False,
        "audio_fade_seconds": 2.8,
        "scale_factor": 1.0,
    },
}


def get_render_profile(name: str | None) -> Dict[str, Any]:
    profile_name = name if name in RENDER_PROFILES else "Standard"
    profile = dict(RENDER_PROFILES[profile_name])
    profile["name"] = profile_name
    return profile
