from __future__ import annotations

from datetime import datetime
from typing import Any


CHARACTER_STYLES = [
    "Pixar-style 3D",
    "Cute cartoon",
    "Semi-realistic",
    "Anime",
    "Photorealistic",
]

SCENE_BACKGROUNDS = [
    "Rural Thai house",
    "Studio background",
    "Village road",
    "School yard",
    "Stage",
    "Product promo scene",
]

USE_CASES = [
    "Dancing reel",
    "Lip sync music video",
    "Product affiliate clip",
    "Story short",
    "YouTube Shorts character",
]

PLATFORMS = [
    "Kling",
    "Veo",
    "Runway",
    "Hailuo",
    "PixVerse",
    "Midjourney / Flux image prompt",
]

REQUIRED_CHARACTER_STUDIO_SECTIONS = [
    "Character Bible",
    "Master Character Prompt",
    "Image Generation Prompt",
    "Image-to-Video Prompt",
    "Lip Sync Prompt",
    "TikTok / Reels Prompt",
    "Negative Prompt",
    "Consistency Lock Prompt",
    "Caption ideas",
    "Hashtags",
]

# Backward-friendly alias for early internal callers.
REQUIRED_CHARACTER_SECTIONS = REQUIRED_CHARACTER_STUDIO_SECTIONS

DEFAULT_CHARACTER_STUDIO_INPUTS = {
    "character_name": "น้องมินต์",
    "age_range": "4 years old / little girl character",
    "gender_presentation": "female presentation",
    "country_culture": "Thai rural warmth",
    "face_description": "cute round face, adorable smile, soft cheeks",
    "hair_style": "short black bob haircut",
    "eye_style": "big round brown eyes",
    "skin_tone": "light tan skin",
    "outfit": "mint green sweatshirt, brown jogger pants",
    "shoes_accessories": "white sneakers",
    "character_style": "Pixar-style 3D",
    "scene_background": "Rural Thai house",
    "use_case": "Dancing reel",
    "platform": "Kling",
}

# Backward-friendly alias for early internal callers.
DEFAULT_CHARACTER_INPUTS = DEFAULT_CHARACTER_STUDIO_INPUTS


def _clean(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _identity_line(data: dict[str, Any]) -> str:
    return (
        f"{_clean(data.get('character_name'), 'Unnamed character')}, "
        f"{_clean(data.get('age_range'), 'young character')}, "
        f"{_clean(data.get('gender_presentation'), 'friendly presentation')}, "
        f"{_clean(data.get('country_culture'), 'Thai-inspired culture')}, "
        f"{_clean(data.get('face_description'), 'memorable face')}, "
        f"{_clean(data.get('hair_style'), 'consistent hairstyle')}, "
        f"{_clean(data.get('eye_style'), 'expressive eyes')}, "
        f"{_clean(data.get('skin_tone'), 'natural skin tone')}, "
        f"wearing {_clean(data.get('outfit'), 'signature outfit')} with "
        f"{_clean(data.get('shoes_accessories'), 'simple accessories')}."
    )


def _consistency_lock() -> str:
    return "\n".join(
        [
            "Keep the exact same character identity.",
            "Same face, same hairstyle, same outfit, same proportions.",
            "Preserve character design across all shots.",
            "Full body visible.",
            "Camera fixed unless otherwise specified.",
        ]
    )


def generate_character_prompt_pack(**kwargs: Any) -> dict[str, Any]:
    data = dict(DEFAULT_CHARACTER_STUDIO_INPUTS)
    data.update({key: value for key, value in kwargs.items() if value is not None})

    identity = _identity_line(data)
    style = _clean(data.get("character_style"), "Pixar-style 3D")
    background = _clean(data.get("scene_background"), "Studio background")
    use_case = _clean(data.get("use_case"), "Dancing reel")
    platform = _clean(data.get("platform"), "Kling")
    consistency = _consistency_lock()

    character_bible = "\n".join(
        [
            f"Name: {_clean(data.get('character_name'), 'Unnamed character')}",
            f"Age / Type: {_clean(data.get('age_range'), 'young character')}",
            f"Gender / Presentation: {_clean(data.get('gender_presentation'), 'friendly presentation')}",
            f"Country / Culture Style: {_clean(data.get('country_culture'), 'Thai-inspired culture')}",
            f"Face: {_clean(data.get('face_description'), 'memorable face')}",
            f"Hair: {_clean(data.get('hair_style'), 'consistent hairstyle')}",
            f"Eyes: {_clean(data.get('eye_style'), 'expressive eyes')}",
            f"Skin Tone: {_clean(data.get('skin_tone'), 'natural skin tone')}",
            f"Outfit: {_clean(data.get('outfit'), 'signature outfit')}",
            f"Shoes / Accessories: {_clean(data.get('shoes_accessories'), 'simple accessories')}",
            f"Character Style: {style}",
            f"Default Background: {background}",
            f"Primary Use Case: {use_case}",
            f"Target Platform: {platform}",
        ]
    )

    master_prompt = (
        f"{identity} {style} reusable character design, clean readable silhouette, "
        f"friendly expressive body language, vertical short-form video ready, {background}. "
        f"{consistency}"
    )
    image_prompt = (
        f"Create one full-body character reference image of {identity} Visual style: {style}. "
        f"Background: {background}. Neutral standing pose, clear front view, clean soft lighting, "
        f"no text, no logo, no watermark. {consistency}"
    )
    image_to_video = (
        f"{platform} image-to-video prompt: Animate this same character in {background}. "
        f"Use natural small body movement for {use_case}, gentle facial expression changes, "
        f"stable identity, clean vertical 9:16 framing, no scene cuts, no text on screen. {consistency}"
    )
    lip_sync = (
        f"Lip sync prompt: Same character performs a short Thai music line with natural mouth movement, "
        f"cute expressive timing, small hand gestures, full body visible, stable framing, {background}. "
        f"No subtitles inside generated video. {consistency}"
    )
    reels_prompt = (
        f"TikTok/Reels prompt: Same character does a simple {use_case.lower()} moment in {background}. "
        f"The first second is expressive, movement is easy to follow, vertical 9:16, clean composition, "
        f"no captions inside generated video. {consistency}"
    )
    negative_prompt = (
        "different face, different hairstyle, different outfit, different body proportions, cropped body, "
        "extra fingers, distorted hands, text, subtitles, logos, watermark, UI overlay, flicker, "
        "identity drift, blurry face, scary expression, split screen, collage"
    )
    captions = "\n".join(
        [
            "ตัวละครนี้น่ารักเกินต้าน",
            "เก็บไว้ใช้ทำคลิปต่อได้เลย",
            "ใครอยากเห็นเวอร์ชันเต้นบ้าง?",
            "คาแรกเตอร์นี้เหมาะกับเพลงไหน?",
        ]
    )
    hashtags = "#VelaFlow #CharacterStudio #AICharacter #KlingAI #Veo #Runway #PixVerse #TikTokCreator #AIReels"

    sections = {
        "Character Bible": character_bible,
        "Master Character Prompt": master_prompt,
        "Image Generation Prompt": image_prompt,
        "Image-to-Video Prompt": image_to_video,
        "Lip Sync Prompt": lip_sync,
        "TikTok / Reels Prompt": reels_prompt,
        "Negative Prompt": negative_prompt,
        "Consistency Lock Prompt": consistency,
        "Caption ideas": captions,
        "Hashtags": hashtags,
    }
    return {
        "ok": True,
        "inputs": data,
        "sections": sections,
        "outputs": sections,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }


def character_prompt_pack_to_text(pack: dict[str, Any]) -> str:
    sections = pack.get("sections") or pack.get("outputs") or {}
    parts = ["VELAFLOW CHARACTER STUDIO PACK", f"Generated: {pack.get('generated_at', '')}"]
    for section in REQUIRED_CHARACTER_STUDIO_SECTIONS:
        parts.append(f"====================\n{section}\n====================\n{sections.get(section, '')}")
    return "\n\n".join(parts).strip() + "\n"
