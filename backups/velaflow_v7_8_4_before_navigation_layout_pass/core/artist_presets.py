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
DEFAULT_ARTIST_CONFIG = PRESET_DIR / "default_artist.json"
LOCKED_PRESET_IDS = {DEFAULT_ARTIST_ID}
ARTIST_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


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
    "locked": True,
}


def ensure_default_artist_preset() -> Path:
    PRESET_DIR.mkdir(parents=True, exist_ok=True)
    path = PRESET_DIR / f"{DEFAULT_ARTIST_ID}.json"
    if not path.exists():
        path.write_text(json.dumps(VELA_MOON_PRESET, ensure_ascii=False, indent=2), encoding="utf-8")
    if not DEFAULT_ARTIST_CONFIG.exists():
        DEFAULT_ARTIST_CONFIG.write_text(json.dumps({"default_artist_id": DEFAULT_ARTIST_ID}, ensure_ascii=False, indent=2), encoding="utf-8")
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
    item["locked"] = is_locked_artist_preset(item.get("artist_id")) or bool(item.get("locked") and item.get("artist_id") == DEFAULT_ARTIST_ID)
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
    return sorted(load_artist_presets().values(), key=lambda item: (not item.get("is_default"), item.get("artist_name", "")))


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
