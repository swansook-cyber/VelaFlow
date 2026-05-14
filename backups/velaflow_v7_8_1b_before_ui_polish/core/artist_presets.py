from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
PRESET_DIR = ROOT / "config" / "artist_presets"
DEFAULT_ARTIST_ID = "vela_moon"


VELA_MOON_PRESET: Dict[str, Any] = {
    "artist_id": "vela_moon",
    "artist_name": "Vela Moon",
    "brand_style": "emotional easy-listening Thai pop rock",
    "default_language": "Thai lyrics",
    "music_prompt_language": "English only",
    "instrument_tags_language": "English only",
    "genre": "mid-tempo pop rock, easy listening",
    "vocal_style": "smooth emotional male vocal, warm tone, relaxed but heartfelt delivery",
    "main_instruments": [
        "clean electric guitar",
        "acoustic guitar strumming",
        "warm bass",
        "soft drum kit",
    ],
    "supporting_instruments": [
        "light rhodes piano",
        "soft synth pad",
        "tambourine",
        "melodic electric guitar solo",
    ],
    "atmosphere_elements": [
        "relaxed emotional atmosphere",
        "catchy melody",
        "full band arrangement",
        "complete song structure",
    ],
    "default_music_style_prompt": (
        "mid-tempo pop rock, easy listening, clean electric guitar, acoustic strumming, "
        "warm bass, soft drum kit, light rhodes piano, smooth male vocal, relaxed but emotional, "
        "catchy melody, full band arrangement, complete song structure"
    ),
    "suno_advanced_settings": {
        "weirdness": 10,
        "style_influence": 65,
        "reason_th": (
            "เพลงแนว Pop Rock ฟังสบาย ต้องการโครงสร้างที่คุ้นหูและเมโลดี้ที่ตลาดเข้าถึงง่าย "
            "การตั้ง Weirdness ต่ำจะทำให้เพลงไม่หลุดกรอบ และ Style Influence ระดับกลางค่อนสูง"
            "จะช่วยคุมดนตรีให้เป็น Pop Rock ที่ไม่หนักจนกลายเป็น Hard Rock"
        ),
    },
    "song_structure": [
        "Intro",
        "Verse 1",
        "Pre-Chorus",
        "Chorus",
        "Post-Chorus",
        "Verse 2",
        "Pre-Chorus",
        "Chorus",
        "Bridge",
        "Guitar Solo",
        "Final Chorus",
        "Outro",
    ],
    "writing_rules": [
        "Thai lyrics must sound natural and conversational",
        "Hook must be short, emotional, catchy, and caption-friendly",
        "Avoid overly poetic or unnatural Thai words",
        "Chorus should be easy to sing after 1-2 listens",
        "Final Chorus must feel bigger than previous chorus",
        "Do not make the song feel like a short demo",
    ],
    "section_instrument_tags": {
        "Intro": "acoustic guitar strumming, soft rhodes piano, relaxed mid-tempo beat",
        "Verse 1": "clean electric guitar picking, warm bass, smooth male vocal",
        "Pre-Chorus": "drum pattern builds up slightly, light synth pad",
        "Chorus": "full band drops in, catchy pop rock groove, tambourine added",
        "Post-Chorus": "melodic electric guitar solo, easy listening vibe",
        "Verse 2": "bass and drum focus, rhythmic acoustic strumming",
        "Bridge": "music strips down, rhodes piano and vocal focus, emotional build up",
        "Guitar Solo": "melodic and expressive pop-rock guitar solo, driving rhythm",
        "Final Chorus": "maximum energy, full band, brighter vocal delivery, expanded emotion",
        "Outro": "fading out with acoustic guitar and soft piano, lingering clean guitar note",
    },
    "mv_identity": {
        "render_profile": "Cinematic",
        "subtitle_style": "cinematic",
        "color_profile": "warm / lonely night / film look",
        "camera_language": ["slow push in", "emotional drift", "soft handheld", "cinematic close-up"],
        "visual_mood": "emotional, relatable, cinematic but accessible",
    },
    "marketing_identity": {
        "tone": "emotional, relatable, caption-friendly",
        "target_platforms": ["YouTube", "TikTok", "Facebook", "Shorts"],
        "hook_style": "short Thai phrase that feels like real life",
    },
}


def ensure_default_artist_preset() -> Path:
    PRESET_DIR.mkdir(parents=True, exist_ok=True)
    path = PRESET_DIR / f"{DEFAULT_ARTIST_ID}.json"
    if not path.exists():
        path.write_text(json.dumps(VELA_MOON_PRESET, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def validate_artist_preset(preset: Dict[str, Any]) -> Dict[str, Any]:
    required = ["artist_id", "artist_name", "default_music_style_prompt", "section_instrument_tags"]
    missing = [key for key in required if not preset.get(key)]
    return {"ok": not missing, "message": "valid" if not missing else "missing required preset fields", "data": {"missing": missing}, "error": ""}


def load_artist_presets() -> Dict[str, Dict[str, Any]]:
    ensure_default_artist_preset()
    presets: Dict[str, Dict[str, Any]] = {}
    for path in PRESET_DIR.glob("*.json"):
        try:
            preset = json.loads(path.read_text(encoding="utf-8"))
            validation = validate_artist_preset(preset)
            if validation.get("ok"):
                presets[preset["artist_id"]] = preset
        except Exception:
            continue
    if DEFAULT_ARTIST_ID not in presets:
        presets[DEFAULT_ARTIST_ID] = dict(VELA_MOON_PRESET)
    return presets


def get_artist_preset(artist_id: str | None = None) -> Dict[str, Any]:
    presets = load_artist_presets()
    return presets.get(artist_id or DEFAULT_ARTIST_ID) or presets[DEFAULT_ARTIST_ID]


def list_artist_presets() -> List[Dict[str, Any]]:
    return sorted(load_artist_presets().values(), key=lambda item: item.get("artist_name", ""))


def save_artist_preset(preset: Dict[str, Any]) -> Dict[str, Any]:
    validation = validate_artist_preset(preset)
    if not validation.get("ok"):
        return {"ok": False, "message": validation.get("message", "Invalid preset"), "data": validation.get("data", {}), "error": "invalid_artist_preset"}
    PRESET_DIR.mkdir(parents=True, exist_ok=True)
    artist_id = preset.get("artist_id", DEFAULT_ARTIST_ID)
    path = PRESET_DIR / f"{artist_id}.json"
    path.write_text(json.dumps(preset, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "message": "Artist preset saved", "data": {"path": str(path), "preset": preset}, "error": ""}
