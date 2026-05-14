from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List

from core.instrument_tag_normalizer import contains_thai

ROOT = Path(__file__).resolve().parents[1]
PRESET_DIR = ROOT / "config" / "artist_presets"
DEFAULT_ARTIST_ID = "vela_moon"
PUBLIC_DEFAULT_ARTIST_ID = "emotional_pop"
DEFAULT_ARTIST_CONFIG = PRESET_DIR / "default_artist.json"
GENERAL_CREATOR_CATEGORY = "General Creator Presets"
VELA_MOON_CATEGORY = "Vela Moon Signature"
PUBLIC_BETA_PRESET_IDS = {
    "emotional_pop",
    "cinematic_story",
    "viral_tiktok",
    "indie_soft",
    "acoustic_heartfelt",
    "dark_emotional",
    "motivational",
    "cozy_chill",
    "vela_moon",
    "vela_moon_emotional",
    "vela_moon_dark_night",
    "vela_moon_lonely_pop",
    "vela_moon_cinematic_sad",
}
LOCKED_PRESET_IDS = set(PUBLIC_BETA_PRESET_IDS)
ARTIST_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


VELA_MOON_PRESET: Dict[str, Any] = {
    "artist_id": "vela_moon",
    "artist_name": "Vela Moon",
    "category": VELA_MOON_CATEGORY,
    "description": "Original compatibility preset for existing Vela Moon projects.",
    "mood": "warm, emotional, relatable",
    "vocal_feeling": "smooth emotional male vocal",
    "pacing": "mid-tempo, easy-listening, complete song structure",
    "instrumentation_style": "clean electric guitar, acoustic strumming, warm bass, soft drum kit",
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
    "locked": True,
}


def _preset(
    artist_id: str,
    artist_name: str,
    category: str,
    description: str,
    mood: str,
    vocal_feeling: str,
    pacing: str,
    instrumentation_style: str,
    genre: str,
    style_prompt: str,
    section_tags: Dict[str, str],
    *,
    weirdness: int = 12,
    style_influence: int = 62,
    visual_mood: str = "cinematic, emotional, accessible",
    hook_style: str = "short, catchy, caption-friendly Thai hook",
) -> Dict[str, Any]:
    instruments = [item.strip() for item in instrumentation_style.split(",") if item.strip()]
    return {
        "artist_id": artist_id,
        "artist_name": artist_name,
        "category": category,
        "description": description,
        "mood": mood,
        "vocal_feeling": vocal_feeling,
        "pacing": pacing,
        "instrumentation_style": instrumentation_style,
        "brand_style": f"{mood}, {genre}",
        "default_language": "Thai lyrics",
        "music_prompt_language": "English only",
        "instrument_tags_language": "English only",
        "genre": genre,
        "vocal_style": vocal_feeling,
        "main_instruments": instruments[:4] or ["piano", "guitar", "bass", "drums"],
        "supporting_instruments": instruments[4:] or ["soft pad", "light percussion"],
        "atmosphere_elements": [mood, pacing, "complete song structure"],
        "default_music_style_prompt": style_prompt,
        "lyric_style": "natural conversational Thai lyrics, clear emotional story, not overly poetic",
        "hook_style": hook_style,
        "suno_advanced_settings": {
            "weirdness": weirdness,
            "style_influence": style_influence,
            "reason_th": "Public beta preset values are controlled and safe for consistent creator output.",
        },
        "song_structure": ["Intro", "Verse 1", "Pre-Chorus", "Chorus", "Verse 2", "Bridge", "Final Chorus", "Outro"],
        "writing_rules": [
            "Thai lyrics must sound natural and conversational",
            "Hook must be short, emotional, catchy, and caption-friendly",
            "Do not reference real artists or copyrighted artist styles",
            "Instrument and production tags inside parentheses must be English only",
            "Final Chorus should feel stronger than previous chorus",
        ],
        "section_instrument_tags": section_tags,
        "mv_identity": {
            "render_profile": "Cinematic",
            "subtitle_style": "cinematic",
            "color_profile": visual_mood,
            "camera_language": ["slow push in", "emotional close-up", "soft handheld", "cinematic drift"],
            "visual_mood": visual_mood,
        },
        "marketing_identity": {
            "tone": "relatable, creator-friendly, emotional",
            "target_platforms": ["YouTube", "TikTok", "Facebook", "Shorts"],
            "hook_style": hook_style,
        },
        "locked": True,
    }


def _public_beta_presets() -> Dict[str, Dict[str, Any]]:
    base_tags = {
        "Intro": "soft piano and ambient pad, emotional opening",
        "Verse 1": "gentle guitar, warm bass, intimate vocal",
        "Pre-Chorus": "drums build softly, rising emotional tension",
        "Chorus": "full pop arrangement, catchy drums, wide guitars",
        "Verse 2": "rhythmic guitar and bass, steady groove",
        "Bridge": "stripped-down piano, emotional pause",
        "Final Chorus": "bigger drums, layered backing vocals, expanded emotion",
        "Outro": "soft fade out, lingering piano and guitar",
    }
    presets = {
        "emotional_pop": _preset(
            "emotional_pop",
            "Emotional Pop",
            GENERAL_CREATOR_CATEGORY,
            "Balanced public preset for emotional Thai pop songs.",
            "warm, emotional, clean",
            "clear natural vocal, expressive but controlled",
            "mid-tempo, radio-friendly, smooth emotional rise",
            "warm piano, clean electric guitar, acoustic guitar, bass, soft drums, light pad",
            "modern Thai pop, pop rock",
            "modern Thai emotional pop, warm piano, clean electric guitar, acoustic strumming, smooth vocal, catchy chorus, polished radio-friendly arrangement",
            base_tags,
        ),
        "cinematic_story": _preset(
            "cinematic_story",
            "Cinematic Story",
            GENERAL_CREATOR_CATEGORY,
            "Story-driven preset for emotional narrative songs.",
            "deep, reflective, cinematic",
            "intimate storytelling vocal, emotional but controlled",
            "slow build, strong bridge, big final chorus",
            "piano, cinematic strings, soft drums, ambient pads, warm bass",
            "cinematic pop, emotional storytelling",
            "cinematic emotional pop, intimate vocal, piano, soft strings, ambient pads, gradual build, strong narrative flow",
            {**base_tags, "Bridge": "minimal piano and strings, dramatic emotional reflection"},
            weirdness=18,
            style_influence=55,
            visual_mood="cinematic, reflective, story-focused",
        ),
        "viral_tiktok": _preset(
            "viral_tiktok",
            "Viral TikTok",
            GENERAL_CREATOR_CATEGORY,
            "Fast hook-first preset for short-form-ready songs.",
            "direct, catchy, emotional",
            "expressive vocal with strong hook delivery",
            "quick start, hook within first 10 seconds, punchy chorus",
            "punchy drums, bright guitars, bass, synth hook, claps",
            "pop rock, alternative pop, short-form viral",
            "hook-first pop rock, fast emotional impact, punchy drums, bright guitar hook, strong chorus for 15-30 second clips",
            {**base_tags, "Intro": "instant hook intro, punchy drums, bright guitar motif", "Chorus": "big catchy chorus, strong rhythm, subtitle-friendly hook"},
            weirdness=6,
            style_influence=78,
            visual_mood="viral, energetic, vertical short-form",
        ),
        "indie_soft": _preset(
            "indie_soft",
            "Indie Soft",
            GENERAL_CREATOR_CATEGORY,
            "Soft indie preset for intimate creator songs.",
            "gentle, honest, intimate",
            "soft close-mic vocal, understated emotion",
            "laid-back, airy, minimal but complete",
            "clean guitar, soft drums, warm bass, mellow keys, ambient texture",
            "indie pop, soft pop",
            "soft indie pop, close-mic vocal, clean guitar, mellow keys, warm bass, airy ambient texture, honest emotional delivery",
            {**base_tags, "Chorus": "soft indie chorus, gentle drums, warm guitar layers"},
            weirdness=16,
            style_influence=50,
            visual_mood="soft, intimate, cozy room",
        ),
        "acoustic_heartfelt": _preset(
            "acoustic_heartfelt",
            "Acoustic Heartfelt",
            GENERAL_CREATOR_CATEGORY,
            "Acoustic-first preset for heartfelt Thai lyrics.",
            "heartfelt, simple, sincere",
            "natural vocal, close and sincere delivery",
            "gentle verses, memorable chorus, organic ending",
            "acoustic guitar, warm piano, light percussion, soft bass, subtle strings",
            "acoustic pop, heartfelt ballad",
            "heartfelt acoustic pop, acoustic guitar strumming, warm piano, light percussion, sincere vocal, memorable chorus, organic full song",
            {**base_tags, "Intro": "acoustic guitar fingerpicking, warm piano, intimate atmosphere", "Final Chorus": "full acoustic band, emotional vocal lift, subtle strings"},
            weirdness=10,
            style_influence=66,
            visual_mood="warm, human, heartfelt",
        ),
        "dark_emotional": _preset(
            "dark_emotional",
            "Dark Emotional",
            GENERAL_CREATOR_CATEGORY,
            "Moody preset for darker heartbreak and night themes.",
            "dark, lonely, intense",
            "deep emotional vocal, restrained but heavy feeling",
            "slow tension, darker chorus, dramatic final release",
            "dark piano, muted electric guitar, deep bass, cinematic drums, low pad",
            "dark pop, emotional pop rock",
            "dark emotional pop rock, moody piano, muted electric guitar, deep bass, cinematic drums, low ambient pad, restrained intense vocal",
            {**base_tags, "Intro": "dark piano, low ambient pad, tense atmosphere", "Chorus": "dark full band chorus, deep bass, cinematic drums"},
            weirdness=20,
            style_influence=58,
            visual_mood="dark night, lonely, moody cinematic",
        ),
        "motivational": _preset(
            "motivational",
            "Motivational",
            GENERAL_CREATOR_CATEGORY,
            "Uplifting preset for self-belief and life motivation songs.",
            "hopeful, uplifting, determined",
            "clear inspiring vocal, confident emotional lift",
            "steady rise, anthem chorus, bright final chorus",
            "bright piano, electric guitar, driving drums, warm bass, uplifting pads",
            "uplifting pop rock, motivational pop",
            "uplifting Thai pop rock, bright piano, driving drums, warm bass, inspiring vocal, anthem chorus, hopeful final chorus",
            {**base_tags, "Chorus": "anthem pop rock chorus, driving drums, bright guitars", "Final Chorus": "maximum uplifting energy, layered vocals, wide guitars"},
            weirdness=9,
            style_influence=70,
            visual_mood="hopeful, bright, forward motion",
        ),
        "cozy_chill": _preset(
            "cozy_chill",
            "Cozy Chill",
            GENERAL_CREATOR_CATEGORY,
            "Relaxed preset for warm, easy-listening creator songs.",
            "cozy, relaxed, comforting",
            "soft warm vocal, relaxed delivery",
            "easy groove, gentle hook, calm ending",
            "rhodes piano, soft guitar, warm bass, light drums, mellow pad",
            "chill pop, easy listening",
            "cozy chill pop, rhodes piano, soft guitar, warm bass, light drums, mellow pad, relaxed warm vocal, easy-listening hook",
            {**base_tags, "Intro": "soft rhodes piano, mellow pad, relaxed groove", "Chorus": "cozy chill chorus, light drums, warm bass"},
            weirdness=13,
            style_influence=60,
            visual_mood="cozy, warm indoor, soft light",
        ),
    }
    presets["vela_moon_emotional"] = _preset(
        "vela_moon_emotional", "Vela Moon Emotional", VELA_MOON_CATEGORY,
        "Signature emotional pop rock identity for Vela Moon-style projects.",
        "relatable heartbreak, warm emotional release", "smooth emotional male vocal, warm tone",
        "mid-tempo, accessible, complete pop rock structure",
        "clean electric guitar, acoustic strumming, warm bass, soft drum kit, rhodes piano",
        "mid-tempo pop rock, easy listening",
        VELA_MOON_PRESET["default_music_style_prompt"], VELA_MOON_PRESET["section_instrument_tags"],
        weirdness=10, style_influence=65, visual_mood="warm lonely night, cinematic but accessible",
    )
    presets["vela_moon_dark_night"] = _preset(
        "vela_moon_dark_night", "Vela Moon Dark Night", VELA_MOON_CATEGORY,
        "Darker night variation for lonely city and regret themes.",
        "lonely night, regretful, cinematic", "smooth male vocal with darker warm resonance",
        "slow-mid tempo, night drive tension, emotional final chorus",
        "clean electric guitar, dark piano, warm bass, soft drums, low synth pad",
        "dark easy-listening pop rock",
        "dark night Thai pop rock, clean electric guitar, dark piano, warm bass, soft drums, low synth pad, smooth emotional male vocal",
        {**VELA_MOON_PRESET["section_instrument_tags"], "Intro": "dark piano, clean guitar delay, lonely night atmosphere"},
        weirdness=14, style_influence=68, visual_mood="lonely night, neon, moody film look",
    )
    presets["vela_moon_lonely_pop"] = _preset(
        "vela_moon_lonely_pop", "Vela Moon Lonely Pop", VELA_MOON_CATEGORY,
        "Melodic lonely-pop variation with accessible hook writing.",
        "lonely but catchy, soft sadness", "smooth emotional male vocal, gentle pop delivery",
        "mid-tempo pop pacing, strong hook, light post-chorus",
        "acoustic guitar, clean electric guitar, warm bass, soft drums, light synth pad",
        "lonely Thai pop rock, easy listening",
        "lonely Thai pop rock, acoustic guitar, clean electric guitar, warm bass, soft drums, light synth pad, catchy emotional melody",
        VELA_MOON_PRESET["section_instrument_tags"],
        weirdness=11, style_influence=70, visual_mood="soft loneliness, warm street lights",
    )
    presets["vela_moon_cinematic_sad"] = _preset(
        "vela_moon_cinematic_sad", "Vela Moon Cinematic Sad", VELA_MOON_CATEGORY,
        "More cinematic sad variation for MV-first emotional songs.",
        "cinematic sadness, reflective, dramatic", "smooth male vocal, cinematic heartfelt delivery",
        "slow build, emotional bridge, big final chorus",
        "piano, clean guitar, warm bass, soft drums, cinematic pad, melodic guitar solo",
        "cinematic sad pop rock",
        "cinematic sad Thai pop rock, piano, clean electric guitar, warm bass, soft drums, cinematic pad, melodic guitar solo, smooth emotional male vocal",
        {**VELA_MOON_PRESET["section_instrument_tags"], "Bridge": "music drops down, piano and cinematic pad, emotional tension"},
        weirdness=16, style_influence=64, visual_mood="cinematic sad, rain, reflective city lights",
    )
    return presets


def ensure_default_artist_preset() -> Path:
    PRESET_DIR.mkdir(parents=True, exist_ok=True)
    for preset_id, preset in _public_beta_presets().items():
        preset_path = PRESET_DIR / f"{preset_id}.json"
        if not preset_path.exists():
            preset_path.write_text(json.dumps(preset, ensure_ascii=False, indent=2), encoding="utf-8")
    path = PRESET_DIR / f"{DEFAULT_ARTIST_ID}.json"
    if not path.exists():
        path.write_text(json.dumps(VELA_MOON_PRESET, ensure_ascii=False, indent=2), encoding="utf-8")
    if not DEFAULT_ARTIST_CONFIG.exists():
        DEFAULT_ARTIST_CONFIG.write_text(json.dumps({"default_artist_id": PUBLIC_DEFAULT_ARTIST_ID}, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _result(ok: bool, message: str, data: Dict[str, Any] | None = None, error: str = "") -> Dict[str, Any]:
    return {"ok": ok, "message": message, "data": data or {}, "error": error}


def sanitize_artist_id(value: str) -> str:
    text = (value or "").strip().lower().replace(" ", "_")
    text = re.sub(r"[^a-z0-9_-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_-")
    return text or "custom_artist"


def is_locked_artist_preset(artist_id: str | None) -> bool:
    return (artist_id or "") in LOCKED_PRESET_IDS


def _with_runtime_flags(preset: Dict[str, Any]) -> Dict[str, Any]:
    item = dict(preset)
    item.setdefault("category", GENERAL_CREATOR_CATEGORY if item.get("artist_id") != DEFAULT_ARTIST_ID else VELA_MOON_CATEGORY)
    item["locked"] = is_locked_artist_preset(item.get("artist_id")) or bool(item.get("locked"))
    item["is_default"] = item.get("artist_id") == _read_default_artist_id()
    item["preset_type"] = "system" if item["locked"] else "custom"
    return item


def _numeric_setting(preset: Dict[str, Any], key: str) -> int | None:
    settings = preset.get("suno_advanced_settings", {}) or {}
    raw = settings.get(key)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _list_has_thai(values: Any) -> List[str]:
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        return []
    return [str(item) for item in values if contains_thai(str(item))]


def _section_tags_with_thai(preset: Dict[str, Any]) -> List[Dict[str, str]]:
    tags = preset.get("section_instrument_tags", {}) or {}
    if not isinstance(tags, dict):
        return [{"section": "section_instrument_tags", "tag": "must be an object"}]
    return [{"section": str(section), "tag": str(tag)} for section, tag in tags.items() if contains_thai(str(tag))]


def validate_artist_preset(preset: Dict[str, Any]) -> Dict[str, Any]:
    required = ["artist_id", "artist_name", "default_music_style_prompt", "vocal_style"]
    missing = [key for key in required if not preset.get(key)]
    artist_id = str(preset.get("artist_id", "")).strip()
    invalid_artist_id = bool(artist_id and not ARTIST_ID_PATTERN.match(artist_id))
    thai_fields = {
        "main_instruments": _list_has_thai(preset.get("main_instruments", [])),
        "supporting_instruments": _list_has_thai(preset.get("supporting_instruments", [])),
        "atmosphere_elements": _list_has_thai(preset.get("atmosphere_elements", [])),
    }
    thai_section_tags = _section_tags_with_thai(preset)
    weirdness = _numeric_setting(preset, "weirdness")
    style_influence = _numeric_setting(preset, "style_influence")
    numeric_errors = []
    if weirdness is None or not 0 <= weirdness <= 100:
        numeric_errors.append("weirdness must be 0-100")
    if style_influence is None or not 0 <= style_influence <= 100:
        numeric_errors.append("style_influence must be 0-100")
    thai_errors = {key: value for key, value in thai_fields.items() if value}
    ok = not missing and not invalid_artist_id and not thai_errors and not thai_section_tags and not numeric_errors
    return _result(
        ok,
        "valid" if ok else "artist preset validation failed",
        {
            "missing": missing,
            "invalid_artist_id": invalid_artist_id,
            "thai_instrument_fields": thai_errors,
            "thai_section_tags": thai_section_tags,
            "numeric_errors": numeric_errors,
        },
        "" if ok else "invalid_artist_preset",
    )


def load_artist_presets() -> Dict[str, Dict[str, Any]]:
    ensure_default_artist_preset()
    presets: Dict[str, Dict[str, Any]] = {}
    for path in PRESET_DIR.glob("*.json"):
        if path.name == DEFAULT_ARTIST_CONFIG.name:
            continue
        try:
            preset = json.loads(path.read_text(encoding="utf-8"))
            validation = validate_artist_preset(preset)
            if validation.get("ok"):
                presets[preset["artist_id"]] = _with_runtime_flags(preset)
        except Exception:
            continue
    if DEFAULT_ARTIST_ID not in presets:
        presets[DEFAULT_ARTIST_ID] = _with_runtime_flags(dict(VELA_MOON_PRESET))
    return presets


def get_artist_preset(artist_id: str | None = None) -> Dict[str, Any]:
    presets = load_artist_presets()
    target_id = artist_id or load_default_artist_id()
    return presets.get(target_id) or presets[DEFAULT_ARTIST_ID]


def list_artist_presets() -> List[Dict[str, Any]]:
    order = {GENERAL_CREATOR_CATEGORY: 0, VELA_MOON_CATEGORY: 1}
    return sorted(
        load_artist_presets().values(),
        key=lambda item: (order.get(item.get("category", ""), 2), not item.get("is_default"), item.get("artist_name", "")),
    )


def artist_preset_categories() -> List[str]:
    presets = load_artist_presets().values()
    categories = []
    for preset in presets:
        category = preset.get("category") or "Custom"
        if category not in categories:
            categories.append(category)
    ordered = [GENERAL_CREATOR_CATEGORY, VELA_MOON_CATEGORY]
    return [item for item in ordered if item in categories] + sorted(item for item in categories if item not in ordered)


def list_artist_presets_by_category(category: str | None = None) -> List[Dict[str, Any]]:
    presets = list_artist_presets()
    if not category:
        return presets
    return [preset for preset in presets if (preset.get("category") or "Custom") == category]


def _read_default_artist_id() -> str:
    ensure_default_artist_preset()
    try:
        data = json.loads(DEFAULT_ARTIST_CONFIG.read_text(encoding="utf-8"))
        return data.get("default_artist_id") or DEFAULT_ARTIST_ID
    except Exception:
        return DEFAULT_ARTIST_ID


def load_default_artist_id() -> str:
    artist_id = _read_default_artist_id()
    if artist_id in load_artist_presets():
        return artist_id
    return DEFAULT_ARTIST_ID


def save_default_artist_id(artist_id: str) -> Dict[str, Any]:
    ensure_default_artist_preset()
    if artist_id not in load_artist_presets():
        return _result(False, "Artist preset not found", {"artist_id": artist_id}, "artist_preset_not_found")
    DEFAULT_ARTIST_CONFIG.write_text(json.dumps({"default_artist_id": artist_id}, ensure_ascii=False, indent=2), encoding="utf-8")
    return _result(True, "Default artist preset saved", {"default_artist_id": artist_id, "path": str(DEFAULT_ARTIST_CONFIG)})


def set_default_artist_preset(artist_id: str) -> Dict[str, Any]:
    return save_default_artist_id(artist_id)


def save_artist_preset(preset: Dict[str, Any], overwrite_locked: bool = False) -> Dict[str, Any]:
    validation = validate_artist_preset(preset)
    if not validation.get("ok"):
        return _result(False, validation.get("message", "Invalid preset"), validation.get("data", {}), "invalid_artist_preset")
    PRESET_DIR.mkdir(parents=True, exist_ok=True)
    artist_id = sanitize_artist_id(str(preset.get("artist_id", DEFAULT_ARTIST_ID)))
    if is_locked_artist_preset(artist_id) and not overwrite_locked:
        return _result(False, "Vela Moon is a locked system preset. Duplicate it to customize.", {"artist_id": artist_id}, "locked_artist_preset")
    preset = dict(preset)
    preset["artist_id"] = artist_id
    preset["locked"] = is_locked_artist_preset(artist_id)
    path = PRESET_DIR / f"{artist_id}.json"
    path.write_text(json.dumps(preset, ensure_ascii=False, indent=2), encoding="utf-8")
    return _result(True, "Artist preset saved", {"path": str(path), "preset": _with_runtime_flags(preset)})


def duplicate_artist_preset(source_artist_id: str, new_artist_id: str, new_artist_name: str | None = None) -> Dict[str, Any]:
    source = get_artist_preset(source_artist_id)
    target_id = sanitize_artist_id(new_artist_id)
    if target_id in load_artist_presets():
        return _result(False, "Artist preset already exists", {"artist_id": target_id}, "artist_preset_exists")
    duplicate = {key: value for key, value in source.items() if key not in {"locked", "is_default", "preset_type"}}
    duplicate["artist_id"] = target_id
    duplicate["artist_name"] = new_artist_name or f"{source.get('artist_name', 'Artist')} Copy"
    duplicate["locked"] = False
    return save_artist_preset(duplicate)


def delete_artist_preset(artist_id: str) -> Dict[str, Any]:
    if is_locked_artist_preset(artist_id):
        return _result(False, "Locked artist presets cannot be deleted", {"artist_id": artist_id}, "locked_artist_preset")
    path = PRESET_DIR / f"{sanitize_artist_id(artist_id)}.json"
    if not path.exists():
        return _result(False, "Artist preset not found", {"artist_id": artist_id}, "artist_preset_not_found")
    backup_dir = PRESET_DIR / "_deleted_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / path.name
    if backup_path.exists():
        backup_path = backup_dir / f"{path.stem}_{len(list(backup_dir.glob(path.stem + '*')))}{path.suffix}"
    shutil.copy2(path, backup_path)
    path.unlink()
    if _read_default_artist_id() == artist_id:
        save_default_artist_id(DEFAULT_ARTIST_ID)
    return _result(True, "Artist preset deleted", {"backup_path": str(backup_path), "artist_id": artist_id})


def export_artist_preset(artist_id: str) -> Dict[str, Any]:
    preset = get_artist_preset(artist_id)
    exportable = {key: value for key, value in preset.items() if key not in {"is_default", "preset_type"}}
    return _result(True, "Artist preset exported", {"preset": exportable, "json": json.dumps(exportable, ensure_ascii=False, indent=2)})


def import_artist_preset(preset: Dict[str, Any], overwrite: bool = False, save_as_copy: bool = False) -> Dict[str, Any]:
    validation = validate_artist_preset(preset)
    if not validation.get("ok"):
        return _result(False, validation.get("message", "Invalid preset"), validation.get("data", {}), "invalid_artist_preset")
    artist_id = sanitize_artist_id(str(preset.get("artist_id", "")))
    existing = load_artist_presets()
    if artist_id in existing:
        if is_locked_artist_preset(artist_id) and not save_as_copy:
            return _result(False, "Cannot overwrite locked Vela Moon preset", {"artist_id": artist_id}, "locked_artist_preset")
        if save_as_copy:
            base = artist_id
            count = 2
            while f"{base}_copy_{count}" in existing:
                count += 1
            preset = dict(preset)
            preset["artist_id"] = f"{base}_copy_{count}"
            preset["artist_name"] = f"{preset.get('artist_name', base)} Copy {count}"
        elif not overwrite:
            return _result(False, "Artist preset already exists", {"artist_id": artist_id}, "artist_preset_exists")
    return save_artist_preset(preset)
