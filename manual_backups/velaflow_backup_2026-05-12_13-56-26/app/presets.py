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
_LAST_AI_CONTROLS: Dict[str, Tuple[int, int]] = {}


def list_music_preset_names() -> List[str]:
    return list(MUSIC_PRESETS.keys())


def get_music_preset(name: str | None = None) -> Dict[str, Any]:
    preset = MUSIC_PRESETS.get(name or DEFAULT_MUSIC_PRESET) or MUSIC_PRESETS[DEFAULT_MUSIC_PRESET]
    return asdict(preset)


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
    if manual_weirdness is not None and manual_style_influence is not None:
        return {
            "weirdness": int(manual_weirdness),
            "style_influence": int(manual_style_influence),
            "reason": f"ใช้ค่าที่ผู้ใช้ตั้งเองสำหรับ {name}",
            "weirdness_range": weirdness_range,
            "style_influence_range": style_range,
            "manual": True,
        }
    weirdness = random.randint(*weirdness_range)
    style_influence = random.randint(*style_range)
    last = _LAST_AI_CONTROLS.get(name)
    if last == (weirdness, style_influence):
        weirdness = weirdness_range[0] + ((weirdness - weirdness_range[0] + 1) % (weirdness_range[1] - weirdness_range[0] + 1))
    _LAST_AI_CONTROLS[name] = (weirdness, style_influence)
    return {
        "weirdness": weirdness,
        "style_influence": style_influence,
        "reason": f"ค่าแนะนำจาก Music Preset: {name} เพื่อให้เพลงมีความต่างเล็กน้อยแต่ยังคุมโทนได้",
        "weirdness_range": weirdness_range,
        "style_influence_range": style_range,
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
