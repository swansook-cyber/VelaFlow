from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List


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
    ),
}

DEFAULT_MUSIC_PRESET = "VelaFlow Default"


def list_music_preset_names() -> List[str]:
    return list(MUSIC_PRESETS.keys())


def get_music_preset(name: str | None = None) -> Dict[str, str]:
    preset = MUSIC_PRESETS.get(name or DEFAULT_MUSIC_PRESET) or MUSIC_PRESETS[DEFAULT_MUSIC_PRESET]
    return asdict(preset)


def music_preset_prompt(preset: Dict[str, str]) -> str:
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
