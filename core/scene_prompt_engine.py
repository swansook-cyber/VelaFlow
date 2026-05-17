from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


PROMPT_STYLES: dict[str, dict[str, str]] = {
    "Emotional": {
        "aesthetic": "cinematic Thai emotional short film, warm low-key lighting, intimate framing",
        "metaphor": "empty room, soft window light, objects left behind",
        "palette": "warm amber and soft shadow",
    },
    "Dark": {
        "aesthetic": "dark urban night, realistic cinematic drama, high contrast shadows",
        "metaphor": "wet street, neon reflection, lonely silhouette",
        "palette": "deep blue, black, muted red",
    },
    "Romantic": {
        "aesthetic": "romantic cinematic realism, soft glow, gentle close-up emotion",
        "metaphor": "two coffee cups, city lights, almost-touching hands",
        "palette": "rose gold, soft cream, warm night lights",
    },
    "TikTok Meme": {
        "aesthetic": "cinematic vertical TikTok meme energy, expressive character reaction, bold composition",
        "metaphor": "oversized reaction face, playful prop, punchline-ready frame",
        "palette": "bright contrast, clean colorful background",
    },
    "Anime Nostalgia": {
        "aesthetic": "anime-inspired nostalgic city evening, emotional slice-of-life frame",
        "metaphor": "train window, school bag, sunset sky, drifting petals",
        "palette": "orange sunset, pastel purple, soft blue",
    },
    "Dreamy": {
        "aesthetic": "dreamy surreal cinematic look, soft focus, floating light particles",
        "metaphor": "mirror reflection, mist, glowing doorway, slow memory feeling",
        "palette": "lavender, pale blue, moonlit silver",
    },
    "Podcast Drama": {
        "aesthetic": "dramatic podcast clip visual, office night realism, documentary close-up",
        "metaphor": "desk lamp, empty office chair, unread messages",
        "palette": "fluorescent office green, shadow, muted gray",
    },
    "Cute Character": {
        "aesthetic": "cute 3D cartoon viral character, expressive face, vertical short-form style",
        "metaphor": "tiny character in an oversized real-life situation",
        "palette": "bright playful colors, clean soft background",
    },
}


EMOTION_KEYWORDS: dict[str, list[str]] = {
    "heartbreak": ["เจ็บ", "เสียใจ", "เลิก", "ลืม", "ร้องไห้", "พอแล้ว", "hurt", "heartbreak"],
    "lonely": ["เหงา", "คนเดียว", "ว่างเปล่า", "คิดถึง", "lonely", "missing"],
    "hope": ["เริ่มใหม่", "เดินต่อ", "หวัง", "ดีขึ้น", "hope", "heal"],
    "anger": ["โกรธ", "พัง", "ไม่ไหว", "toxic", "rant"],
    "love": ["รัก", "แฟน", "หัวใจ", "romantic", "crush"],
    "funny": ["ฮา", "ตลก", "บ่น", "meme", "funny"],
}


STYLE_ALIASES = {
    "emotional_story": "Emotional",
    "viral_meme": "TikTok Meme",
    "cute_character": "Cute Character",
    "podcast_drama": "Podcast Drama",
    "cinematic_mv": "Dreamy",
    "affiliate_sell": "TikTok Meme",
}


def normalize_prompt_style(style: str | None, preset_id: str | None = None) -> str:
    candidate = str(style or "").strip()
    if candidate in PROMPT_STYLES:
        return candidate
    mapped = STYLE_ALIASES.get(str(preset_id or "").strip())
    if mapped:
        return mapped
    lowered = candidate.lower()
    for name in PROMPT_STYLES:
        if name.lower() == lowered:
            return name
    return "Emotional"


def detect_scene_emotion(text: str) -> dict[str, Any]:
    value = str(text or "").lower()
    scores: dict[str, int] = {}
    for emotion, keywords in EMOTION_KEYWORDS.items():
        scores[emotion] = sum(1 for keyword in keywords if keyword.lower() in value)
    primary = max(scores, key=scores.get) if any(scores.values()) else "emotional"
    intensity = min(100, 45 + scores.get(primary, 0) * 18 + min(25, len(value) // 18))
    return {"primary_emotion": primary, "intensity": intensity, "scores": scores}


def _clean_lyric(lyric: str) -> str:
    cleaned = re.sub(r"\[[^\]]+\]", " ", str(lyric or ""))
    cleaned = re.sub(r"\([^)]*\)", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _metaphor_for_emotion(emotion: str, style_config: dict[str, str]) -> str:
    overrides = {
        "heartbreak": "cracked mirror, empty side of the bed, rain sliding on glass",
        "lonely": "one chair under street light, unread chat bubbles, silent night room",
        "hope": "first morning light, open door, slow walk forward",
        "anger": "tight close-up, harsh shadow, phone screen glowing in the dark",
        "love": "soft city lights, hand holding a small keepsake, warm reflection",
        "funny": "oversized everyday object, expressive reaction, playful visual punchline",
    }
    return overrides.get(emotion, style_config["metaphor"])


def build_scene_prompt(
    lyric: str,
    *,
    style: str = "Emotional",
    scene_index: int = 1,
    hook_text: str = "",
    preset_id: str = "",
    mood: str = "",
) -> dict[str, Any]:
    prompt_style = normalize_prompt_style(style, preset_id)
    style_config = PROMPT_STYLES[prompt_style]
    cleaned = _clean_lyric(lyric or hook_text)
    emotion = detect_scene_emotion(" ".join([cleaned, hook_text, mood]))
    metaphor = _metaphor_for_emotion(emotion["primary_emotion"], style_config)
    scene_progression = {
        1: {
            "focus": "opening stop-scroll hook moment",
            "camera": "tight vertical close-up with strong foreground subject",
            "lighting": "clean high-contrast key light, face-safe composition",
            "composition": "centered subject, empty lower third for subtitles",
        },
        2: {
            "focus": "emotional story turn with new angle",
            "camera": "medium side angle with cinematic depth and parallax",
            "lighting": "softer practical light from the opposite side",
            "composition": "subject placed on one third, different room angle from scene 1",
        },
        3: {
            "focus": "strongest ending frame, replay-worthy emotional peak",
            "camera": "dramatic push-in frame with clear silhouette or face priority",
            "lighting": "strong rim light and cinematic contrast for thumbnail quality",
            "composition": "mobile thumbnail readable, high contrast center subject",
        },
    }
    progression = scene_progression.get(scene_index, scene_progression[3])
    cinematic_prompt = (
        f"{style_config['aesthetic']}, {progression['focus']}, visual metaphor: {metaphor}, "
        f"emotion: {emotion['primary_emotion']} intensity {emotion['intensity']}/100, "
        f"{progression['camera']}, {progression['lighting']}, {progression['composition']}, "
        f"vertical 9:16 composition, TikTok-ready framing, subtitle-safe lower third, "
        "consistent visual story across scenes but clearly different framing, "
        f"{style_config['palette']} color palette, realistic depth, high quality, no watermark, no random text"
    )
    return {
        "scene_id": f"scene_{scene_index:02d}",
        "source_lyric": cleaned,
        "prompt_style": prompt_style,
        "emotion": emotion,
        "visual_metaphor": metaphor,
        "camera_language": progression["camera"],
        "lighting_direction": progression["lighting"],
        "composition_note": progression["composition"],
        "cinematic_prompt": cinematic_prompt,
        "tiktok_aesthetic": style_config["aesthetic"],
        "subtitle_safe_note": "Keep important faces and objects away from the lower subtitle area.",
    }


def build_scene_prompts(
    scenes: list[dict[str, Any]],
    *,
    hook_text: str = "",
    style: str = "Emotional",
    preset_id: str = "",
    mood: str = "",
) -> dict[str, Any]:
    prompts: list[dict[str, Any]] = []
    for index, scene in enumerate(scenes or [], start=1):
        lyric = str(scene.get("subtitle") or scene.get("lyric_part") or scene.get("visual_prompt") or hook_text)
        prompt = build_scene_prompt(lyric, style=style, scene_index=index, hook_text=hook_text, preset_id=preset_id, mood=mood)
        prompts.append(prompt)
    return {
        "generated_by": "VelaFlow",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "style": normalize_prompt_style(style, preset_id),
        "hook_text": hook_text,
        "scene_prompts": prompts,
    }


def apply_scene_prompts_to_package(package: dict[str, Any], scene_prompt_plan: dict[str, Any]) -> dict[str, Any]:
    prompts = scene_prompt_plan.get("scene_prompts") or []
    scenes = package.get("scene_sequence") or []
    for scene, prompt in zip(scenes, prompts):
        scene["base_visual_prompt"] = scene.get("visual_prompt", "")
        scene["visual_prompt"] = prompt.get("cinematic_prompt", scene.get("visual_prompt", ""))
        scene["visual_metaphor"] = prompt.get("visual_metaphor", "")
        scene["detected_emotion"] = prompt.get("emotion", {})
    package["scene_prompt_plan"] = scene_prompt_plan
    return package


def save_scene_prompts(scene_prompt_plan: dict[str, Any], output_path: str | Path) -> dict[str, Any]:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(scene_prompt_plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "message": "Scene prompts exported", "data": {"path": str(path)}, "error": ""}
