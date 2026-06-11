from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class MusicPreset:
    name: str
    description: str
    genre: str
    mood: str
    vocal_style: str
    arrangement: str
    structure_guide: str
    prompt_suffix: str
    weirdness_range: Tuple[int, int]
    style_influence_range: Tuple[int, int]


@dataclass(frozen=True)
class VocalDirectionPreset:
    name: str
    description: str
    vocal_style: str
    delivery: str
    emotional_tone: str


MUSIC_PRESETS: Dict[str, MusicPreset] = {
    "VelaFlow Default": MusicPreset(
        name="VelaFlow Default",
        description="A safe general-purpose preset for polished emotional pop and pop rock releases.",
        genre="Modern Pop / Pop Rock",
        mood="balanced, emotional, clean, radio-friendly",
        vocal_style="clear natural vocal, expressive but not overdramatic",
        arrangement="warm piano, acoustic/electric guitar, bass, drums, light pad",
        structure_guide="Intro, Verse, Pre-Chorus, Chorus, Verse 2, Bridge, Final Chorus, Outro",
        prompt_suffix="Make the song polished, easy to listen to, emotionally clear, and suitable for general release.",
        weirdness_range=(8, 14),
        style_influence_range=(55, 68),
    ),
    "Viral TikTok Hook": MusicPreset(
        name="Viral TikTok Hook",
        description="A short-form focused preset for fast hooks and memorable clip moments.",
        genre="Pop Rock / Alternative Pop / Short-form Viral",
        mood="direct, catchy, emotional, memorable",
        vocal_style="expressive vocal with strong hook delivery",
        arrangement="start quickly, strong rhythm, hook within first 10 seconds, chorus designed for 15-30 second clips",
        structure_guide="Hook Intro, Verse, Pre-Chorus, Big Chorus, Repeat Hook, Outro",
        prompt_suffix="Focus on a catchy first line, fast emotional impact, and a chorus that works well as a TikTok or Shorts clip.",
        weirdness_range=(3, 8),
        style_influence_range=(70, 85),
    ),
    "Story Cinematic": MusicPreset(
        name="Story Cinematic",
        description="A narrative preset for songs that need a cinematic emotional arc.",
        genre="Cinematic Pop / Emotional Storytelling",
        mood="deep, reflective, dramatic, narrative",
        vocal_style="intimate vocal, storytelling delivery, emotional but controlled",
        arrangement="piano, cinematic strings, soft drums, ambient pads, gradual build",
        structure_guide="Cinematic Intro, Verse 1, Verse 2, Pre-Chorus, Chorus, Bridge, Final Chorus, Outro",
        prompt_suffix="Make the song feel like a story, with cinematic emotion and strong narrative flow.",
        weirdness_range=(15, 25),
        style_influence_range=(45, 60),
    ),
}

DEFAULT_MUSIC_PRESET = "VelaFlow Default"
DEFAULT_VOCAL_DIRECTION = "Male Emotional"
_LAST_AI_CONTROLS: Dict[str, Tuple[int, int]] = {}

RECOMMENDED_AI_CONTROLS: Dict[str, Tuple[int, int]] = {
    "Vela Moon Emotional Pop Rock": (12, 68),
    "Thai Sad Pop": (14, 70),
    "Office Burnout": (18, 72),
    "Viral TikTok Hook": (6, 82),
    "Story Cinematic": (22, 58),
    "Indie Acoustic": (16, 64),
    "Dark Podcast Intro": (30, 50),
    "VelaFlow Default": (12, 68),
}

STRICT_COMMERCIAL_PRESETS = {"Vela Moon Emotional Pop Rock", "Thai Sad Pop", "Office Burnout"}
EXPERIMENTAL_MUSIC_PRESETS = {"Story Cinematic", "Dark Podcast Intro"}

VOCAL_DIRECTION_PRESETS: Dict[str, VocalDirectionPreset] = {
    "Male Emotional": VocalDirectionPreset(
        name="Male Emotional",
        description="เสียงผู้ชายอบอุ่น ถ่ายทอดอารมณ์จริงใจ เหมาะกับเพลงรักและเพลงเศร้า",
        vocal_style="warm emotional male vocal",
        delivery="intimate heartfelt delivery",
        emotional_tone="expressive but controlled",
    ),
    "Female Soft": VocalDirectionPreset(
        name="Female Soft",
        description="เสียงผู้หญิงนุ่ม โปร่ง และละมุน เหมาะกับเพลง cinematic หรือเพลงฟังสบาย",
        vocal_style="soft airy female vocal",
        delivery="cinematic emotional tone",
        emotional_tone="gentle phrasing",
    ),
    "Deep Male Cinematic": VocalDirectionPreset(
        name="Deep Male Cinematic",
        description="เสียงผู้ชายโทนลึก เล่าเรื่องเข้มและอบอุ่น เหมาะกับเพลงดราม่า",
        vocal_style="deep male vocal",
        delivery="cinematic storytelling delivery",
        emotional_tone="dark warm resonance",
    ),
    "Female Power Pop": VocalDirectionPreset(
        name="Female Power Pop",
        description="เสียงผู้หญิงพลัง pop ชัดและจำง่าย เหมาะกับเพลง hook เด่น",
        vocal_style="energetic female vocal",
        delivery="modern pop power delivery",
        emotional_tone="catchy expressive tone",
    ),
    "Indie Whisper": VocalDirectionPreset(
        name="Indie Whisper",
        description="เสียงกระซิบใกล้ไมค์ ให้ความรู้สึกอินดี้และเป็นส่วนตัว",
        vocal_style="intimate whisper vocal",
        delivery="indie soft delivery",
        emotional_tone="close mic emotional feeling",
    ),
    "Duo Harmony": VocalDirectionPreset(
        name="Duo Harmony",
        description="เสียงคู่ชายหญิงพร้อมฮาร์โมนี เหมาะกับเพลง duet หรือ chorus ใหญ่",
        vocal_style="male and female harmony vocal",
        delivery="layered emotional chorus",
        emotional_tone="cinematic duet feeling",
    ),
}


def list_music_preset_names() -> List[str]:
    return list(MUSIC_PRESETS.keys())


def get_music_preset(name: str | None = None) -> Dict[str, Any]:
    preset = MUSIC_PRESETS.get(name or DEFAULT_MUSIC_PRESET) or MUSIC_PRESETS[DEFAULT_MUSIC_PRESET]
    return asdict(preset)


def list_vocal_direction_names() -> List[str]:
    return list(VOCAL_DIRECTION_PRESETS.keys())


def get_vocal_direction(name: str | None = None) -> Dict[str, str]:
    preset = VOCAL_DIRECTION_PRESETS.get(name or DEFAULT_VOCAL_DIRECTION) or VOCAL_DIRECTION_PRESETS[DEFAULT_VOCAL_DIRECTION]
    return asdict(preset)


def vocal_direction_prompt(preset: Dict[str, str]) -> str:
    if not preset:
        return ""
    return (
        "\n\nVocal Direction:\n"
        f"- Name: {preset.get('name', '')}\n"
        f"- Vocal Style: {preset.get('vocal_style', '')}\n"
        f"- Delivery: {preset.get('delivery', '')}\n"
        f"- Emotional Tone: {preset.get('emotional_tone', '')}\n"
    )


def _range_for_preset(preset_name: str | None, key: str, fallback: Tuple[int, int]) -> Tuple[int, int]:
    preset = get_music_preset(preset_name)
    values = preset.get(key, fallback)
    try:
        low, high = int(values[0]), int(values[1])
        return min(low, high), max(low, high)
    except Exception:
        return fallback


def get_recommended_ai_controls(
    preset_name: str | None = None,
    manual_weirdness: int | None = None,
    manual_style_influence: int | None = None,
) -> Dict[str, Any]:
    name = preset_name or DEFAULT_MUSIC_PRESET
    weirdness_range = _range_for_preset(name, "weirdness_range", (8, 14))
    style_range = _range_for_preset(name, "style_influence_range", (55, 68))
    recommended_weirdness, recommended_style = RECOMMENDED_AI_CONTROLS.get(
        name,
        (int(sum(weirdness_range) / 2), int(sum(style_range) / 2)),
    )
    max_weirdness = 35 if name in EXPERIMENTAL_MUSIC_PRESETS else (25 if name in STRICT_COMMERCIAL_PRESETS else 35)
    if manual_weirdness is not None and manual_style_influence is not None:
        weirdness = max(0, min(max_weirdness, int(manual_weirdness)))
        style_influence = max(55, min(85, int(manual_style_influence)))
        return {
            "weirdness": weirdness,
            "style_influence": style_influence,
            "reason": f"Manual override for {name}; values clamped for commercial safety.",
            "weirdness_range": weirdness_range,
            "style_influence_range": style_range,
            "mode": "Manual Override",
            "manual": True,
        }
    weirdness = max(0, min(max_weirdness, recommended_weirdness))
    style_influence = max(55, min(85, recommended_style))
    _LAST_AI_CONTROLS[name] = (weirdness, style_influence)
    return {
        "weirdness": weirdness,
        "style_influence": style_influence,
        "reason": f"Auto by preset: safe recommended AI controls for {name}.",
        "weirdness_range": weirdness_range,
        "style_influence_range": style_range,
        "mode": "Auto by preset",
        "manual": False,
    }


def music_preset_prompt(preset: Dict[str, Any]) -> str:
    if not preset:
        return ""
    return (
        "\n\nMusic Preset:\n"
        f"- Name: {preset.get('name', '')}\n"
        f"- Genre: {preset.get('genre', '')}\n"
        f"- Mood: {preset.get('mood', '')}\n"
        f"- Vocal Style: {preset.get('vocal_style', '')}\n"
        f"- Arrangement: {preset.get('arrangement', '')}\n"
        f"- Structure Guide: {preset.get('structure_guide', '')}\n"
        f"- Direction: {preset.get('prompt_suffix', '')}\n"
    )
