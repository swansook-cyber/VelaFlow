from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from core.artist_presets import get_artist_preset, load_default_artist_id
from core.project_io import safe_name


PROJECT_ROOT = Path(__file__).resolve().parents[1] / "project_data" / "projects"

TOPIC_OPTIONS = [
    "Heartbreak",
    "Secret Crush",
    "Move On",
    "Self Healing",
    "Lonely Night",
    "Life Motivation",
    "Missing Someone",
    "Relationship Confusion",
    "Custom",
]

MOOD_OPTIONS = ["Emotional", "Cinematic", "Uplifting", "Dark", "Nostalgic", "Hopeful", "Lonely", "Regretful"]
MUSIC_DIRECTION_OPTIONS = [
    "Emotional Pop Rock",
    "Acoustic Ballad",
    "Sad Cinematic",
    "TikTok Viral Pop",
    "Night Drive",
    "Indie Pop",
    "Easy Listening Pop Rock",
]
TARGET_PLATFORM_OPTIONS = ["Suno only", "TikTok", "YouTube MV", "Spotify", "Shorts/Reels", "Full Pipeline"]


def _topic_text(topic: str, custom_topic: str = "") -> str:
    return (custom_topic or "").strip() if topic == "Custom" else topic


def suggest_project_name(topic: str, custom_topic: str = "") -> str:
    topic_value = _topic_text(topic, custom_topic) or "New Song"
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    return safe_name(f"{topic_value}_{stamp}")


def generate_creative_direction(
    *,
    topic: str,
    mood: str,
    music_direction: str,
    artist_preset_id: str | None = None,
    target_platform: str = "Full Pipeline",
    custom_topic: str = "",
) -> Dict[str, Any]:
    preset = get_artist_preset(artist_preset_id or load_default_artist_id())
    topic_value = _topic_text(topic, custom_topic) or topic
    topic_lower = topic_value.lower()

    hook_focus = {
        "heartbreak": "short Thai phrase about knowing love is over but the heart still hurts",
        "secret crush": "shy, caption-friendly Thai phrase about loving quietly",
        "move on": "memorable Thai phrase about finally letting go",
        "self healing": "short emotional Thai phrase about choosing yourself",
        "lonely night": "night-time Thai phrase about missing someone in silence",
        "life motivation": "uplifting Thai phrase about standing up again",
        "missing someone": "simple Thai phrase about missing someone every night",
        "relationship confusion": "relatable Thai phrase about unclear love",
    }
    hook_direction = next((value for key, value in hook_focus.items() if key in topic_lower), "short, emotional, caption-friendly Thai phrase that feels like real life")

    if music_direction in {"Emotional Pop Rock", "Easy Listening Pop Rock"}:
        suggested_template = "Emotional Pop Rock"
        render_profile = "Cinematic"
        subtitle_style = "cinematic"
    elif music_direction == "TikTok Viral Pop" or target_platform in {"TikTok", "Shorts/Reels"}:
        suggested_template = "TikTok Viral"
        render_profile = "TikTok Fast"
        subtitle_style = "tiktok"
    elif music_direction == "Night Drive":
        suggested_template = "Night Drive"
        render_profile = "Cinematic"
        subtitle_style = "cinematic"
    elif music_direction == "Acoustic Ballad":
        suggested_template = "Acoustic Heartbreak"
        render_profile = "Cinematic"
        subtitle_style = "cinematic"
    else:
        suggested_template = music_direction
        render_profile = "Cinematic"
        subtitle_style = "cinematic"

    emotional_arc = {
        "Emotional": "hurt -> reflection -> acceptance -> release",
        "Cinematic": "quiet tension -> emotional rise -> visual climax -> soft ending",
        "Uplifting": "doubt -> courage -> hope -> forward motion",
        "Dark": "confusion -> isolation -> confrontation -> unresolved echo",
        "Nostalgic": "memory -> longing -> bittersweet chorus -> gentle fade",
        "Hopeful": "pain -> realization -> self-belief -> open ending",
        "Lonely": "silence -> memory -> ache -> empty night",
        "Regretful": "mistake -> memory -> apology -> acceptance",
    }.get(mood, "emotion rises naturally toward a memorable chorus")

    visual_mood = {
        "Lonely Night": "lonely room, warm street lights, reflective mirror shots",
        "Heartbreak": "empty bedroom, rain window, soft close-up, quiet street",
        "Self Healing": "morning light, walking alone, mirror reflection, open road",
        "Move On": "leaving a room, city lights, slow push in, final warm sunrise",
    }.get(topic_value, "cinematic close-up, relatable room, night street lights, emotional performance shots")

    style_prompt = preset.get("default_music_style_prompt", "")
    platform_angle = {
        "TikTok": "relatable hook line for short captions and repeat viewing",
        "Shorts/Reels": "quick emotional payoff for vertical short-form clips",
        "YouTube MV": "cinematic story angle with clear emotional progression",
        "Spotify": "artist identity and loopable Canvas mood",
        "Suno only": "clean Suno-ready structure and singable chorus",
        "Full Pipeline": "complete song-to-MV workflow with hook and marketing angle",
    }.get(target_platform, "caption-friendly emotional release")

    return {
        "topic": topic_value,
        "mood": mood,
        "music_direction": music_direction,
        "artist_preset": preset.get("artist_id", "vela_moon"),
        "target_platform": target_platform,
        "project_concept": f"A {mood.lower()} {music_direction.lower()} song about {topic_value.lower()} with a clear emotional payoff.",
        "hook_direction": hook_direction,
        "lyric_direction": "natural Thai lyrics, relatable, conversational, not overly poetic",
        "music_style_direction": style_prompt,
        "emotional_arc": emotional_arc,
        "visual_mood": visual_mood,
        "suggested_template": suggested_template,
        "suggested_render_profile": render_profile,
        "suggested_subtitle_style": subtitle_style,
        "suggested_marketing_angle": platform_angle,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def creative_direction_prompt(direction: Dict[str, Any]) -> str:
    if not direction:
        return ""
    return (
        "\n\nCreative Direction:\n"
        f"- Topic: {direction.get('topic', '')}\n"
        f"- Mood: {direction.get('mood', '')}\n"
        f"- Music Direction: {direction.get('music_direction', '')}\n"
        f"- Target Platform: {direction.get('target_platform', '')}\n"
        f"- Project Concept: {direction.get('project_concept', '')}\n"
        f"- Hook Direction: {direction.get('hook_direction', '')}\n"
        f"- Lyric Direction: {direction.get('lyric_direction', '')}\n"
        f"- Music Style Direction: {direction.get('music_style_direction', '')}\n"
        f"- Emotional Arc: {direction.get('emotional_arc', '')}\n"
        f"- Visual Mood: {direction.get('visual_mood', '')}\n"
        f"- Marketing Angle: {direction.get('suggested_marketing_angle', '')}\n"
    )


def save_creative_direction(project_name: str, direction: Dict[str, Any], base_dir: str | Path | None = None) -> Dict[str, Any]:
    try:
        root = Path(base_dir) if base_dir else PROJECT_ROOT
        folder = root / safe_name(project_name or suggest_project_name(direction.get("topic", "New Song")))
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "creative_direction.json"
        path.write_text(json.dumps(direction, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "message": "Creative direction saved", "data": {"path": str(path), "folder": str(folder), "creative_direction": direction}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Save creative direction failed", "data": {}, "error": str(exc)}


def load_creative_direction(project_name: str, base_dir: str | Path | None = None) -> Dict[str, Any]:
    try:
        root = Path(base_dir) if base_dir else PROJECT_ROOT
        path = root / safe_name(project_name or "project") / "creative_direction.json"
        if not path.exists():
            return {"ok": False, "message": "No creative direction found", "data": {}, "error": "missing creative_direction.json"}
        return {"ok": True, "message": "Creative direction loaded", "data": {"creative_direction": json.loads(path.read_text(encoding="utf-8")), "path": str(path)}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Load creative direction failed", "data": {}, "error": str(exc)}
