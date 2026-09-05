from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
import re

from core.artist_presets import get_artist_preset
from core.file_naming import build_export_filename, build_lyrics_download_filename, ensure_unique_path
from core.instrument_tag_normalizer import normalize_lyrics_tags
from core.project_io import safe_name
from core.paths import resolve_project_folder
from core.song_structure_intelligence import export_structure_plan_files
from core.song_title_engine import is_placeholder_song_title, resolve_song_title
from core.version import build_label


ROOT = Path(__file__).resolve().parents[1]

HASHTAG_CANONICAL_LABELS = {
    "r&b": "RnB",
    "city pop": "CityPop",
    "pop rock": "PopRock",
    "hip-hop": "HipHop",
    "hip hop": "HipHop",
    "lo-fi pop": "LofiPop",
    "lofi pop": "LofiPop",
    "neo soul": "NeoSoul",
    "alternative rock": "AlternativeRock",
}

RELEASE_MOOD_FAMILIES = {
    "uplifting": {
        "aliases": ("ให้กำลังใจ", "ฮึกเหิม", "หวังใหม่", "inspirational", "hopeful", "positive", "uplifting"),
        "caption": "บางครั้งเพลงหนึ่งก็ช่วยเตือนให้เราเชื่อในตัวเองอีกครั้ง ✨",
        "description": "เพลงที่ส่งต่อกำลังใจและพาอารมณ์ค่อย ๆ ยกขึ้นอย่างจริงใจ",
        "hashtags": ("เพลงให้กำลังใจ", "พลังบวก", "ฮีลใจ", "กำลังใจ"),
        "shorts": ("เก็บท่อนนี้ไว้ฟังในวันที่ต้องการกำลังใจ", "ส่งเพลงนี้ให้ตัวเองในวันที่เหนื่อย"),
        "keyword": "uplifting song",
    },
    "bright": {
        "aliases": ("สดใส", "มีพลัง", "energetic", "bright", "cheerful", "feel good", "feel-good"),
        "caption": "เปิดเพลงนี้แล้วออกไปใช้ชีวิตให้เต็มที่กัน 🌤️",
        "description": "เพลงโทนสดใสที่เติมพลังและชวนออกไปใช้ชีวิตให้เต็มที่",
        "hashtags": ("เพลงสดใส", "ฟีลกู๊ด", "พลังบวก", "เพลงอารมณ์ดี"),
        "shorts": ("ท่อนนี้เหมาะกับวันที่อยากออกไปใช้ชีวิต", "เปิดท่อนนี้รับพลังดี ๆ ของวันนี้"),
        "keyword": "feel-good song",
    },
    "sad": {
        "aliases": ("อกหัก", "เศร้า", "heartbreak", "heartbroken", "sad", "broken"),
        "caption": "บางครั้งท่อนเดียวก็พูดแทนทั้งใจได้ 💔",
        "description": "เพลงที่ถ่ายทอดความเศร้าและพื้นที่ว่างหลังความสัมพันธ์อย่างตรงไปตรงมา",
        "hashtags": ("เพลงเศร้า", "เพลงอกหัก", "อกหัก", "แคปชั่นเศร้า"),
        "shorts": ("เก็บท่อนนี้ไว้ฟังในวันที่ใจยังเจ็บ", "บางความรู้สึกพูดออกมาได้ผ่านเพลงนี้"),
        "keyword": "sad emotional song",
    },
    "romantic": {
        "aliases": ("โรแมนติก", "อบอุ่น", "romantic", "warm", "รัก", "love"),
        "caption": "บางความรู้สึกไม่ต้องพูดเยอะ เพลงนี้ก็เล่าแทนได้ ❤️",
        "description": "เพลงรักโทนอุ่นที่เล่าความสัมพันธ์อย่างเป็นธรรมชาติและใกล้ตัว",
        "hashtags": ("เพลงรัก", "เพลงโรแมนติก", "เพลงอบอุ่น", "ความรัก"),
        "shorts": ("ส่งท่อนนี้ให้คนที่ทำให้วันธรรมดาอบอุ่นขึ้น", "เพลงนี้เหมาะกับความรู้สึกที่อยากบอกใครสักคน"),
        "keyword": "romantic song",
    },
    "lonely": {
        "aliases": ("เหงากลางคืน", "เหงา", "lonely", "late-night", "late night", "night"),
        "caption": "บางคืนเราไม่ได้ต้องการคำตอบ แค่อยากมีเพลงอยู่เป็นเพื่อน 🌙",
        "description": "เพลงบรรยากาศกลางคืนที่เล่าความเงียบและความคิดซึ่งดังขึ้นเมื่ออยู่คนเดียว",
        "hashtags": ("เพลงกลางคืน", "เพลงเหงา", "ฟังตอนกลางคืน", "NightVibes"),
        "shorts": ("เก็บท่อนนี้ไว้ฟังในคืนที่ความเงียบดังเป็นพิเศษ", "ท่อนสำหรับคืนที่ยังไม่อยากปิดไฟนอน"),
        "keyword": "late-night reflective song",
    },
    "nostalgic": {
        "aliases": ("คิดถึง", "nostalgic", "bittersweet", "longing", "reflective"),
        "caption": "บางเพลงพาเรากลับไปหาช่วงเวลาที่ไม่เคยหายไปจากใจ 💙",
        "description": "เพลงโทนคิดถึงที่ย้อนมองความทรงจำอย่างอ่อนโยน โดยไม่สรุปว่าเป็นความอกหัก",
        "hashtags": ("เพลงคิดถึง", "ความทรงจำ", "เพลงฟังสบาย", "คิดถึง"),
        "shorts": ("เก็บท่อนนี้ไว้ฟังตอนนึกถึงช่วงเวลาดี ๆ", "ท่อนนี้พากลับไปหาความทรงจำบางอย่าง"),
        "keyword": "nostalgic song",
    },
    "neutral": {
        "aliases": (),
        "caption": "ท่อนนี้อาจเล่าเรื่องที่คุณกำลังรู้สึกอยู่พอดี 🎧",
        "description": "เพลงที่เล่าเรื่องและอารมณ์อย่างชัดเจนผ่านท่อนร้องที่จดจำง่าย",
        "hashtags": ("เพลงเพราะ", "เพลงใหม่", "ฟังเพลง", "ThaiMusic"),
        "shorts": ("ถ้าท่อนนี้ตรงใจ ลองฟังให้จบ", "เก็บท่อนนี้ไว้ในเพลย์ลิสต์ของคุณ"),
        "keyword": "Thai song",
    },
}


def _project_folder(project_name: str, base_dir: str | Path | None = None) -> Path:
    if base_dir:
        return Path(base_dir) / safe_name(project_name or "project")
    return resolve_project_folder(project_name or "project", "song")


def _selected_hook(song: Dict[str, Any]) -> Dict[str, Any]:
    hook = song.get("selected_hook")
    if isinstance(hook, dict):
        return hook
    return {"hook_text": song.get("selected_hook_text") or str(hook or "")}


def _setting_value(settings: Dict[str, Any], key: str) -> Any:
    value = settings.get(key, "")
    if isinstance(value, str):
        return value
    return str(value)


def normalize_hashtag(value: str) -> str:
    raw = re.sub(r"\s+", " ", str(value or "").strip().lstrip("#")).strip()
    canonical = HASHTAG_CANONICAL_LABELS.get(raw.casefold(), raw)
    text = re.sub(r"[^\wก-๙]+", "", canonical, flags=re.UNICODE)
    return f"#{text}" if text else ""


def resolve_release_mood_family(mood: str) -> str:
    value = " ".join(str(mood or "").casefold().replace("_", " ").split())
    for family in ("sad", "uplifting", "bright", "romantic", "lonely", "nostalgic"):
        if any(alias.casefold() in value for alias in RELEASE_MOOD_FAMILIES[family]["aliases"]):
            return family
    return "neutral"


def _mood_aware_release_copy(*, title: str, artist: str, genre: str, mood: str, hook_text: str) -> Dict[str, Any]:
    family_name = resolve_release_mood_family(mood)
    family = RELEASE_MOOD_FAMILIES[family_name]
    primary_mood = str(mood or "emotional").split(",")[0].strip() or "emotional"
    tags: list[str] = []
    for tag in (
        "เพลงไทย",
        "เพลงใหม่",
        genre.split("/")[0],
        "ThaiMusic",
        "Tpop",
        "เพลงเพราะ",
        "TikTokเพลงไทย",
        "Shorts",
        "Reels",
        *family["hashtags"],
        artist,
        title,
        primary_mood,
        "VelaFlow",
    ):
        cleaned = normalize_hashtag(tag)
        if cleaned and cleaned not in tags:
            tags.append(cleaned)
        if len(tags) >= 20:
            break
    seo_caption = f"{hook_text} - เพลงใหม่จาก {artist} โทน {primary_mood} {family['description']}"
    youtube_description = "\n".join([
        f"{title} - {artist}",
        "",
        str(family["description"]),
        "",
        "Credit:",
        f"Artist / Creator: {artist}",
        "Creative workflow: VelaFlow",
        "",
        "ฟังแล้วคอมเมนต์ท่อนที่ตรงใจที่สุดไว้ได้เลย",
        "",
        " ".join(tags[:15]),
    ])
    shorts = [
        hook_text,
        str(family["shorts"][0]),
        f"{title} - ท่อนที่อยากให้เธอได้ยิน",
        "บางเพลงดังในใจ ก่อนดังในฟีด",
        str(family["shorts"][1]),
    ]
    return {
        "family": family_name,
        "seo_caption": seo_caption,
        "tiktok_caption": f"{hook_text}\n\n{family['caption']}\n{' '.join(tags[:8])}",
        "youtube_description": youtube_description,
        "hashtags": tags,
        "shorts_hooks": shorts,
        "keyword": str(family["keyword"]),
    }


def _song_title(song: Dict[str, Any], project_name: str = "") -> str:
    return resolve_song_title({**(song or {}), "idea": song.get("idea") or song.get("song_idea") or project_name}, project_name)


def _canonical_export_title(song: Dict[str, Any], project_name: str = "") -> str:
    if any(not _is_placeholder_title(song.get(key)) for key in ("title", "song_title", "generated_title")):
        return _song_title(song, project_name)
    if not _is_placeholder_title(project_name):
        return str(project_name).strip()
    if str(song.get("idea") or song.get("song_idea") or "").strip():
        return _song_title(song, project_name)
    return ""


def safe_txt_filename(song_title: str | None, suffix: str) -> str:
    return build_export_filename(song_title or "Untitled Song", "Vela_Moon", suffix, "txt")


def _is_placeholder_title(value: str | None) -> bool:
    return is_placeholder_song_title(value)
    normalized = str(value or "").strip().lower()
    return normalized in {"", "untitled song", "project", "current session", "เพลงใหม่ของฉัน"}


def extract_song_title_from_export_text(export_text: str) -> str:
    text = export_text or ""
    inline_match = re.search(r"^Song title:\s*(.+?)\s*$", text, re.IGNORECASE | re.MULTILINE)
    if inline_match:
        return inline_match.group(1).strip()
    block_match = re.search(r"^Song Title:\s*\n(.+?)\s*$", text, re.IGNORECASE | re.MULTILINE)
    if block_match:
        return block_match.group(1).strip()
    return ""


def resolve_export_txt_filename(
    song: Dict[str, Any],
    project_name: str = "",
    workflow_mode: str = "Full Pipeline",
    export_text: str = "",
) -> str:
    suffix = "Suno_Export"
    artist = _artist_name(song)
    candidates = [_canonical_export_title(song, project_name), extract_song_title_from_export_text(export_text)]
    for candidate in candidates:
        if not _is_placeholder_title(candidate):
            return build_export_filename(str(candidate), artist, suffix, "txt")
    return build_export_filename("Untitled Song", artist, suffix, "txt")


def resolve_lyrics_download_filename(song: Dict[str, Any], project_name: str = "") -> str:
    artist = _artist_name(song)
    candidates = [_canonical_export_title(song, project_name)]
    for candidate in candidates:
        if not _is_placeholder_title(candidate):
            return build_lyrics_download_filename(str(candidate), artist)
    return build_lyrics_download_filename(None, artist)


def export_txt_filename(song: Dict[str, Any], project_name: str = "", workflow_mode: str = "Full Pipeline") -> str:
    return resolve_export_txt_filename(song, project_name, workflow_mode)


def _artist_name(song: Dict[str, Any]) -> str:
    artist = song.get("artist") or song.get("artist_name") or ""
    if artist:
        return str(artist)
    preset = get_artist_preset(song.get("artist_preset", "vela_moon"))
    return str(preset.get("artist_name") or "VelaFlow Artist")


def _canonical_lyrics(song: Dict[str, Any], preset: Dict[str, Any]) -> str:
    source = song.get("normalized_song_output") or song.get("complete_lyrics", "")
    return normalize_lyrics_tags(str(source or ""), preset)


def build_release_package_data(song: Dict[str, Any], project_name: str = "") -> Dict[str, Any]:
    preset = get_artist_preset(song.get("artist_preset", "vela_moon"))
    music_preset = song.get("music_preset_data") or {}
    hook = _selected_hook(song)
    title = _song_title(song, project_name)
    artist = _artist_name(song)
    genre = str(music_preset.get("genre") or preset.get("genre") or "Modern Pop / Pop Rock")
    mood = str(music_preset.get("mood") or song.get("mood") or "emotional, cinematic, relatable")
    vocal_style = str(music_preset.get("vocal_style") or preset.get("vocal_style") or "clear emotional vocal")
    hook_text = str(hook.get("hook_text") or title)
    release_copy = _mood_aware_release_copy(title=title, artist=artist, genre=genre, mood=mood, hook_text=hook_text)
    keywords = [
        title,
        artist,
        genre,
        mood,
        vocal_style,
        hook_text,
        "Thai music",
        release_copy["keyword"],
        "VelaFlow",
    ]
    visual_concept = (
        f"cinematic emotional realistic artwork for a Thai song titled '{title}' by '{artist}', "
        f"mood: {mood}, genre: {genre}, intimate lighting, high quality, no watermark, no logo, "
        "no random text, text on image only includes song title and artist name"
    )
    cover_prompts = {
        "1:1": f"Square 1:1 Spotify and DistroKid cover, {visual_concept}",
        "16:9": f"16:9 YouTube thumbnail, cinematic emotional composition, {visual_concept}",
        "9:16": f"9:16 TikTok Reels Shorts cover, vertical cinematic framing, {visual_concept}",
        "Square Album Cover 1:1": f"Square album cover 1:1 for Spotify, DistroKid, and streaming platforms, {visual_concept}",
        "No Text / DistroKid Safe": (
            f"Square 1:1 distribution-safe album cover artwork for '{title}' by '{artist}', "
            f"mood: {mood}, genre: {genre}, cinematic emotional realistic style, high quality, "
            "no text, no typography, no watermark, no logo, no random letters"
        ),
        "Spotify Canvas / Short Visual Loop": (
            f"Spotify Canvas and short visual loop concept for '{title}' by '{artist}', "
            f"mood: {mood}, genre: {genre}, subtle cinematic motion, emotional realistic scene, "
            "loopable vertical visual, no watermark, no logo, no random text"
        ),
    }
    metadata = {
        "song_title": title,
        "artist_name": artist,
        "genre": genre,
        "mood": mood,
        "vocal_style": vocal_style,
        "keywords": keywords,
    }
    return {
        "song_metadata": metadata,
        "seo_caption": release_copy["seo_caption"],
        "tiktok_caption": release_copy["tiktok_caption"],
        "youtube_description": release_copy["youtube_description"],
        "hashtags": release_copy["hashtags"][:20],
        "shorts_hooks": release_copy["shorts_hooks"][:5],
        "cover_art_prompts": cover_prompts,
        "canvas_prompt": cover_prompts["Spotify Canvas / Short Visual Loop"],
        "release_assets": [
            "suno_full_package.txt",
            export_txt_filename(song, project_name, song.get("workflow_mode", "Full Pipeline")),
            "SEO caption",
            "TikTok caption",
            "YouTube description",
            "hashtags",
            "shorts hooks",
            "cover art prompts",
            "Spotify Canvas prompt",
        ],
    }


def _minimal_suno_package(song: Dict[str, Any], project_name: str, lyrics: str, hook: Dict[str, Any], settings: Dict[str, Any], preset: Dict[str, Any]) -> str:
    return "\n".join([
        "--------------------------------",
        "Song Title:",
        str(song.get("title") or project_name or "Untitled Song"),
        "",
        "Artist Preset:",
        str(song.get("artist_preset") or preset.get("artist_id", "vela_moon")),
        "",
        "Music Style Prompt:",
        str(song.get("music_style_prompt", "")),
        "",
        "Weirdness:",
        str(song.get("weirdness") or _setting_value(settings, "weirdness")),
        "",
        "Style Influence:",
        str(song.get("style_influence") or _setting_value(settings, "style_influence")),
        "",
        "--------------------------------",
        "Complete Lyrics with Tags",
        "--------------------------------",
        "",
        lyrics,
        "",
        "--------------------------------",
        "Hook Information",
        "--------------------------------",
        "",
        "Selected Hook:",
        str(hook.get("hook_text", "")),
        "",
        "Hook Scores:",
        f"- Emotional: {hook.get('emotional_score', '')}",
        f"- Catchy: {hook.get('catchy_score', '')}",
        f"- TikTok: {hook.get('tiktok_potential', '')}",
        "",
        "--------------------------------",
        "Generated By",
        "--------------------------------",
        build_label(),
        "",
    ])


def build_suno_full_package(song: Dict[str, Any], project_name: str = "", workflow_mode: str = "Full Pipeline") -> str:
    preset = get_artist_preset(song.get("artist_preset", "vela_moon"))
    hook = _selected_hook(song)
    settings = song.get("advanced_settings", {}) or {}
    lyrics = _canonical_lyrics(song, preset)
    if workflow_mode == "Song Studio Only":
        return _minimal_suno_package(song, project_name, lyrics, hook, settings, preset)
    release = build_release_package_data(song, project_name)
    metadata = release["song_metadata"]
    structure_plan = song.get("song_structure_plan") or {}
    structure_summary: list[str] = []
    if structure_plan:
        energy_curve = ", ".join(
            f"{item.get('section')} {item.get('energy')}"
            for item in structure_plan.get("energy_curve", []) or []
        )
        section_order = ", ".join(structure_plan.get("recommended_section_order", []) or [])
        structure_summary = [
            "",
            "--------------------------------",
            "Song Structure Summary",
            "--------------------------------",
            "",
            "Preset:",
            str(structure_plan.get("preset_name", "")),
            "",
            "Emotional Arc:",
            str(structure_plan.get("emotional_arc", "")),
            "",
            "Energy Curve:",
            energy_curve,
            "",
            "Section Order:",
            section_order,
        ]
    return "\n".join([
        "====================",
        "SONG METADATA",
        "====================",
        "",
        f"Song title: {metadata.get('song_title', '')}",
        f"Artist name: {metadata.get('artist_name', '')}",
        f"Genre: {metadata.get('genre', '')}",
        f"Mood: {metadata.get('mood', '')}",
        f"Vocal style: {metadata.get('vocal_style', '')}",
        f"Keywords: {', '.join(metadata.get('keywords', []))}",
        "",
        "Artist Preset:",
        str(song.get("artist_preset") or preset.get("artist_id", "vela_moon")),
        "",
        "Music Preset:",
        str(song.get("music_preset", "")),
        "",
        "Music Style Prompt:",
        str(song.get("music_style_prompt", "")),
        "",
        "Weirdness:",
        str(song.get("weirdness") or _setting_value(settings, "weirdness")),
        "",
        "Style Influence:",
        str(song.get("style_influence") or _setting_value(settings, "style_influence")),
        "",
        "====================",
        "LYRICS",
        "====================",
        "",
        lyrics,
        "",
        "====================",
        "SEO CAPTION",
        "====================",
        "",
        release["seo_caption"],
        "",
        "====================",
        "TIKTOK CAPTION",
        "====================",
        "",
        release["tiktok_caption"],
        "",
        "====================",
        "YOUTUBE DESCRIPTION",
        "====================",
        "",
        release["youtube_description"],
        "",
        "====================",
        "HASHTAGS",
        "====================",
        "",
        " ".join(release["hashtags"]),
        "",
        "====================",
        "SHORTS HOOKS",
        "====================",
        "",
        *[f"- {item}" for item in release["shorts_hooks"]],
        "",
        "Selected Hook:",
        str(hook.get("hook_text", "")),
        "",
        "Hook Scores:",
        f"- Emotional: {hook.get('emotional_score', '')}",
        f"- Catchy: {hook.get('catchy_score', '')}",
        f"- TikTok: {hook.get('tiktok_potential', '')}",
        "",
        "====================",
        "COVER ART PROMPTS",
        "====================",
        "",
        "[Square Album Cover 1:1]",
        release["cover_art_prompts"].get("Square Album Cover 1:1") or release["cover_art_prompts"].get("1:1") or "Cover prompts not generated yet.",
        "",
        "[No Text / DistroKid Safe]",
        release["cover_art_prompts"].get("No Text / DistroKid Safe") or "Cover prompts not generated yet.",
        "",
        "[Spotify Canvas / Short Visual Loop]",
        release["cover_art_prompts"].get("Spotify Canvas / Short Visual Loop") or "Cover prompts not generated yet.",
        "",
        "[16:9]",
        release["cover_art_prompts"].get("16:9") or "Cover prompts not generated yet.",
        "",
        "[9:16]",
        release["cover_art_prompts"].get("9:16") or "Cover prompts not generated yet.",
        "",
        "====================",
        "CANVAS PROMPT",
        "====================",
        "",
        release.get("canvas_prompt") or "Cover prompts not generated yet.",
        "",
        "====================",
        "RELEASE ASSETS",
        "====================",
        "",
        *[f"- {item}" for item in release.get("release_assets", [])],
        *structure_summary,
        "",
        "--------------------------------",
        "Generated By",
        "--------------------------------",
        build_label(),
        "",
    ])


def export_suno_files(
    project_name: str,
    song: Dict[str, Any],
    base_dir: str | Path | None = None,
    workflow_mode: str = "Full Pipeline",
) -> Dict[str, Any]:
    try:
        folder = _project_folder(project_name, base_dir) / "exports"
        folder.mkdir(parents=True, exist_ok=True)
        preset = get_artist_preset(song.get("artist_preset", "vela_moon"))
        lyrics = _canonical_lyrics(song, preset)
        canonical_title = _canonical_export_title(song, project_name)
        lyrics_path = ensure_unique_path(folder / build_export_filename(canonical_title, _artist_name(song), "Lyrics_Only", "txt"))
        full_text = build_suno_full_package(song, project_name, workflow_mode=workflow_mode)
        full_path = ensure_unique_path(folder / resolve_export_txt_filename(song, project_name, workflow_mode, full_text))
        full_path.write_text(full_text, encoding="utf-8")
        lyrics_path.write_text(lyrics, encoding="utf-8")
        release = build_release_package_data(song, project_name)
        export_sections = ["Lyrics", "Style Prompt", "Hook Info"]
        if workflow_mode != "Song Studio Only":
            export_sections += ["SEO Caption", "TikTok Caption", "YouTube Description", "Hashtags", "Cover Prompts", "Shorts Hooks", "Canvas Prompt", "Release Assets"]
        debug = {
            "workflow_mode": workflow_mode,
            "seo_caption_exists": bool(release.get("seo_caption")),
            "hashtags_exists": bool(release.get("hashtags")),
            "cover_prompts_exists": bool(release.get("cover_art_prompts")),
            "export_sections": export_sections,
        }
        (folder / "suno_export_debug.json").write_text(json.dumps(debug, ensure_ascii=False, indent=2), encoding="utf-8")
        structure_export = {}
        if song.get("song_structure_plan"):
            structure_export = export_structure_plan_files(project_name, song.get("song_structure_plan", {}), base_dir).get("data", {})
        return {
            "ok": True,
            "message": "Suno exports created",
            "data": {
                "exports_dir": str(folder),
                "suno_full_package": str(full_path),
                "suno_full_filename": full_path.name,
                "lyrics_only": str(lyrics_path),
                "suno_full_text": full_path.read_text(encoding="utf-8"),
                "lyrics_only_text": lyrics,
                "release_package": release,
                "workflow_mode": workflow_mode,
                "export_sections": export_sections,
                "debug_log": str(folder / "suno_export_debug.json"),
                "seo_caption": release.get("seo_caption", ""),
                "tiktok_caption": release.get("tiktok_caption", ""),
                "youtube_description": release.get("youtube_description", ""),
                "hashtags_text": " ".join(release.get("hashtags", [])),
                "cover_prompts_text": "\n\n".join(
                    f"[{key}]\n{value}" for key, value in release.get("cover_art_prompts", {}).items()
                ),
                "song_structure_plan_json": structure_export.get("json", ""),
                "song_structure_plan_md": structure_export.get("markdown", ""),
            },
            "error": "",
        }
    except Exception as exc:
        return {"ok": False, "message": "Suno export failed", "data": {}, "error": str(exc)}


def _resolved_song_intent(song: Dict[str, Any], preset: Dict[str, Any], music_preset: Dict[str, Any]) -> Dict[str, str]:
    """Resolve downstream metadata from the same authoritative generation intent."""
    resolution = song.get("generation_resolution") if isinstance(song.get("generation_resolution"), dict) else {}
    return {
        "genre": str(resolution.get("resolved_genre") or song.get("genre") or music_preset.get("genre") or preset.get("genre") or "Cinematic Thai Pop"),
        "mood": str(resolution.get("resolved_mood") or song.get("mood") or music_preset.get("mood") or preset.get("mood") or "emotional"),
        "vocal": str(resolution.get("resolved_vocal") or song.get("vocal") or music_preset.get("vocal_style") or preset.get("vocal_style") or "clear emotional vocal"),
        "style_prompt": str(resolution.get("resolved_style_prompt") or song.get("music_style_prompt") or ""),
    }


def build_release_package_data(song: Dict[str, Any], project_name: str = "") -> Dict[str, Any]:
    preset = get_artist_preset(song.get("artist_preset", "vela_moon"))
    music_preset = song.get("music_preset_data") or {}
    hook = _selected_hook(song)
    title = _song_title(song, project_name)
    artist = _artist_name(song)
    intent = _resolved_song_intent(song, preset, music_preset)
    genre = intent["genre"]
    mood = intent["mood"]
    vocal_style = intent["vocal"]
    hook_text = str(hook.get("hook_text") or song.get("selected_hook_text") or title).strip()
    release_copy = _mood_aware_release_copy(title=title, artist=artist, genre=genre, mood=mood, hook_text=hook_text)
    keywords = [title, artist, genre, mood, vocal_style, hook_text, "Thai music", release_copy["keyword"], "TikTok hook", "VelaFlow"]
    visual_seed = str(song.get("visual_concept") or hook_text or title)
    visual_concept = (
        f"cinematic emotional Thai pop artwork for '{title}' by '{artist}', "
        f"mood: {mood}, genre: {genre}, same character continuity, same emotional tone, "
        "same warm cinematic lighting palette, connected mini-movie atmosphere, premium realistic artwork, "
        "high emotional realism, no watermark, no logo, no random text, "
        "text on image must include only song title and artist name, "
        f"visual story seed: {visual_seed}"
    )
    cover_prompts = {
        "1:1": (
            "cinematic emotional Thai pop album cover, square 1:1 Spotify and DistroKid artwork, "
            f"{visual_concept}, center composition, premium streaming cover"
        ),
        "9:16": (
            "vertical cinematic emotional TikTok cover frame, close-up emotional subject, strong hook energy, "
            f"{visual_concept}, mobile-first framing, subtitle-safe negative space"
        ),
        "16:9": (
            "cinematic wide YouTube thumbnail, dramatic emotional room, movie-like composition, high contrast, "
            f"{visual_concept}, strong readable focal point"
        ),
        "Square Album Cover 1:1": (
            "cinematic emotional Thai pop album cover, square 1:1 Spotify and DistroKid artwork, "
            f"{visual_concept}, center composition, premium streaming cover"
        ),
        "No Text / DistroKid Safe": (
            f"distribution-safe square 1:1 album cover for '{title}' by '{artist}', same emotional tone, "
            "same lighting palette, cinematic realistic artwork, no text, no typography, no watermark, no logo, no random letters"
        ),
        "Spotify Canvas / Short Visual Loop": (
            f"Spotify Canvas short visual loop for '{title}' by '{artist}', same character continuity, "
            f"genre: {genre}, mood: {mood}, same emotional lighting palette, subtle cinematic motion, "
            "loopable vertical scene, no watermark, no logo, no random text"
        ),
    }
    return {
        "song_metadata": {
            "song_title": title,
            "artist_name": artist,
            "genre": genre,
            "mood": mood,
            "vocal_style": vocal_style,
            "keywords": keywords,
        },
        "seo_caption": release_copy["seo_caption"],
        "tiktok_caption": release_copy["tiktok_caption"],
        "youtube_description": release_copy["youtube_description"],
        "hashtags": release_copy["hashtags"][:20],
        "shorts_hooks": release_copy["shorts_hooks"][:5],
        "cover_art_prompts": cover_prompts,
        "canvas_prompt": cover_prompts["Spotify Canvas / Short Visual Loop"],
        "release_assets": [
            "suno_export.txt",
            "tiktok_caption.txt",
            "youtube_caption.txt",
            "hashtags.txt",
            "cover_prompt_1x1.txt",
            "cover_prompt_9x16.txt",
            "cover_prompt_16x9.txt",
            "thumbnail.jpg",
            "upload_checklist.txt",
        ],
    }


def _creator_song_structure(lyrics: str, hook: Dict[str, Any]) -> str:
    hook_text = str(hook.get("hook_text") or "").strip()
    cleaned = str(lyrics or "").strip()
    lines = ["[SONG STRUCTURE]", ""]
    if hook_text:
        lines += ["[HOOK]", hook_text, ""]
    if cleaned:
        lines.append(cleaned)
    else:
        lines += ["[VERSE]", "", "[PRE-CHORUS]", "", "[CHORUS]", ""]
    return "\n".join(lines).strip()


def _creator_negative_style_prompt() -> str:
    return "\n".join([
        "avoid noisy mix",
        "avoid weak vocal",
        "avoid low-energy chorus",
        "avoid muddy instruments",
        "avoid random genre changes",
        "avoid unclear emotional focus",
    ])


def _minimal_suno_package(song: Dict[str, Any], project_name: str, lyrics: str, hook: Dict[str, Any], settings: Dict[str, Any], preset: Dict[str, Any]) -> str:
    release = build_release_package_data(song, project_name)
    metadata = release["song_metadata"]
    style_prompt = str(song.get("music_style_prompt") or preset.get("default_music_style_prompt") or "").strip()
    return "\n".join([
        "-----------------------------------",
        str(metadata.get("song_title") or project_name or "Untitled Song"),
        str(metadata.get("artist_name") or _artist_name(song)),
        f"MOOD: {metadata.get('mood', '')}",
        f"STYLE: {metadata.get('genre', '')}",
        f"VOCAL: {metadata.get('vocal_style', '')}",
        "LANGUAGE: Thai lyrics with English-only production tags",
        "-----------------------------------",
        "",
        "Complete Lyrics with Tags",
        "",
        _creator_song_structure(lyrics, hook),
        "",
        "-----------------------------------",
        "STYLE PROMPT FOR SUNO",
        "-----------------------------------",
        "",
        style_prompt,
        "",
        f"Weirdness: {song.get('weirdness') or _setting_value(settings, 'weirdness')}",
        f"Style Influence: {song.get('style_influence') or _setting_value(settings, 'style_influence')}",
        "",
        "-----------------------------------",
        "OPTIONAL NEGATIVE STYLE",
        "-----------------------------------",
        "",
        _creator_negative_style_prompt(),
        "",
        "-----------------------------------",
        "HOOK INFORMATION",
        "-----------------------------------",
        "",
        "Hook Information",
        f"Selected Hook: {hook.get('hook_text', '')}",
        f"Emotional: {hook.get('emotional_score', '')}",
        f"Catchy: {hook.get('catchy_score', '')}",
        f"TikTok: {hook.get('tiktok_potential', '')}",
        "",
        "-----------------------------------",
        "Generated By",
        "-----------------------------------",
        build_label(),
        "",
    ])


def build_suno_full_package(song: Dict[str, Any], project_name: str = "", workflow_mode: str = "Full Pipeline") -> str:
    preset = get_artist_preset(song.get("artist_preset", "vela_moon"))
    hook = _selected_hook(song)
    settings = song.get("advanced_settings", {}) or {}
    lyrics = _canonical_lyrics(song, preset)
    release = build_release_package_data(song, project_name)
    metadata = release["song_metadata"]
    base = _minimal_suno_package(song, project_name, lyrics, hook, settings, preset)
    structure_plan = song.get("song_structure_plan") or {}
    structure_summary: list[str] = []
    if structure_plan:
        energy_curve = ", ".join(
            f"{item.get('section')} {item.get('energy')}"
            for item in structure_plan.get("energy_curve", []) or []
        )
        section_order = ", ".join(structure_plan.get("recommended_section_order", []) or [])
        structure_summary = [
            "Song Structure Summary",
            f"Preset: {structure_plan.get('preset_name', '')}",
            f"Emotional Arc: {structure_plan.get('emotional_arc', '')}",
            f"Energy Curve: {energy_curve}",
            f"Section Order: {section_order}",
            "",
        ]
    return "\n".join([
        base,
        "",
        "Hook Scores:",
        f"- Emotional: {hook.get('emotional_score', '')}",
        f"- Catchy: {hook.get('catchy_score', '')}",
        f"- TikTok: {hook.get('tiktok_potential', '')}",
        "",
        *structure_summary,
        "====================",
        "CREATOR RELEASE PACKAGE",
        "====================",
        "",
        "SONG METADATA",
        "",
        "====================",
        "SONG METADATA",
        f"Song title: {metadata.get('song_title', '')}",
        f"Artist name: {metadata.get('artist_name', '')}",
        f"Genre: {metadata.get('genre', '')}",
        f"Mood: {metadata.get('mood', '')}",
        f"Vocal style: {metadata.get('vocal_style', '')}",
        f"Keywords: {', '.join(metadata.get('keywords', []))}",
        "",
        "====================",
        "LYRICS",
        "====================",
        "",
        lyrics,
        "",
        "====================",
        "SEO CAPTION",
        "====================",
        "",
        release["seo_caption"],
        "",
        "====================",
        "TIKTOK CAPTION",
        "====================",
        "",
        "TIKTOK CAPTION",
        release["tiktok_caption"],
        "",
        "====================",
        "YOUTUBE DESCRIPTION",
        "====================",
        "",
        "YOUTUBE CAPTION",
        release["youtube_description"],
        "",
        "====================",
        "HASHTAGS",
        "====================",
        "",
        "HASHTAGS",
        " ".join(release["hashtags"]),
        "",
        "====================",
        "SHORTS HOOKS",
        "====================",
        "",
        "SHORTS HOOKS",
        *[f"- {item}" for item in release["shorts_hooks"]],
        "",
        "====================",
        "COVER ART PROMPTS",
        "====================",
        "",
        "COVER PROMPTS",
        "",
        "[1:1 COVER PROMPT]",
        release["cover_art_prompts"].get("1:1", "Cover prompts not generated yet."),
        "",
        "[9:16 TIKTOK COVER]",
        release["cover_art_prompts"].get("9:16", "Cover prompts not generated yet."),
        "",
        "[16:9 YOUTUBE THUMBNAIL]",
        release["cover_art_prompts"].get("16:9", "Cover prompts not generated yet."),
        "",
        "[Square Album Cover 1:1]",
        release["cover_art_prompts"].get("Square Album Cover 1:1", "Cover prompts not generated yet."),
        "",
        "[No Text / DistroKid Safe]",
        release["cover_art_prompts"].get("No Text / DistroKid Safe", "Cover prompts not generated yet."),
        "",
        "[Spotify Canvas / Short Visual Loop]",
        release["cover_art_prompts"].get("Spotify Canvas / Short Visual Loop", "Cover prompts not generated yet."),
        "",
        "====================",
        "CANVAS PROMPT",
        "====================",
        "",
        release.get("canvas_prompt") or "Cover prompts not generated yet.",
        "",
        "====================",
        "RELEASE ASSETS",
        "====================",
        "",
        "RELEASE ASSETS",
        *[f"- {item}" for item in release.get("release_assets", [])],
        "",
    ])


def export_suno_files(
    project_name: str,
    song: Dict[str, Any],
    base_dir: str | Path | None = None,
    workflow_mode: str = "Full Pipeline",
) -> Dict[str, Any]:
    try:
        folder = _project_folder(project_name, base_dir) / "exports"
        folder.mkdir(parents=True, exist_ok=True)
        preset = get_artist_preset(song.get("artist_preset", "vela_moon"))
        lyrics = _canonical_lyrics(song, preset)
        canonical_title = _canonical_export_title(song, project_name)
        lyrics_path = ensure_unique_path(folder / build_export_filename(canonical_title, _artist_name(song), "Lyrics_Only", "txt"))
        full_text = build_suno_full_package(song, project_name, workflow_mode=workflow_mode)
        full_path = ensure_unique_path(folder / resolve_export_txt_filename(song, project_name, workflow_mode, full_text))
        full_path.write_text(full_text, encoding="utf-8-sig")
        lyrics_path.write_text(lyrics, encoding="utf-8")
        release = build_release_package_data(song, project_name)
        export_sections = ["Lyrics", "Style Prompt", "Hook Info", "TikTok Caption", "YouTube Caption", "Hashtags", "Cover Prompts", "Release Assets"]
        debug = {
            "workflow_mode": workflow_mode,
            "seo_caption_exists": bool(release.get("seo_caption")),
            "hashtags_exists": bool(release.get("hashtags")),
            "cover_prompts_exists": bool(release.get("cover_art_prompts")),
            "export_sections": export_sections,
        }
        (folder / "suno_export_debug.json").write_text(json.dumps(debug, ensure_ascii=False, indent=2), encoding="utf-8")
        structure_export = {}
        if song.get("song_structure_plan"):
            structure_export = export_structure_plan_files(project_name, song.get("song_structure_plan", {}), base_dir).get("data", {})
        return {
            "ok": True,
            "message": "Suno exports created",
            "data": {
                "exports_dir": str(folder),
                "suno_full_package": str(full_path),
                "suno_full_filename": full_path.name,
                "lyrics_only": str(lyrics_path),
                "lyrics_download_filename": resolve_lyrics_download_filename(song, project_name),
                "suno_full_text": full_path.read_text(encoding="utf-8-sig"),
                "lyrics_only_text": lyrics,
                "release_package": release,
                "workflow_mode": workflow_mode,
                "export_sections": export_sections,
                "debug_log": str(folder / "suno_export_debug.json"),
                "seo_caption": release.get("seo_caption", ""),
                "tiktok_caption": release.get("tiktok_caption", ""),
                "youtube_description": release.get("youtube_description", ""),
                "hashtags_text": " ".join(release.get("hashtags", [])),
                "cover_prompts_text": "\n\n".join(f"[{key}]\n{value}" for key, value in release.get("cover_art_prompts", {}).items()),
                "song_structure_plan_json": structure_export.get("json", ""),
                "song_structure_plan_md": structure_export.get("markdown", ""),
            },
            "error": "",
        }
    except Exception as exc:
        return {"ok": False, "message": "Suno export failed", "data": {}, "error": str(exc)}


def export_creator_final_assets(
    project_name: str,
    song: Dict[str, Any],
    final_dir: str | Path,
    workflow_mode: str = "Full Pipeline",
) -> Dict[str, Any]:
    try:
        folder = Path(final_dir)
        folder.mkdir(parents=True, exist_ok=True)
        release = build_release_package_data(song, project_name)
        cover_prompts = release.get("cover_art_prompts", {}) or {}
        files = {
            "suno_export.txt": build_suno_full_package(song, project_name, workflow_mode=workflow_mode),
            "tiktok_caption.txt": release.get("tiktok_caption", ""),
            "youtube_caption.txt": release.get("youtube_description", ""),
            "hashtags.txt": " ".join(release.get("hashtags", [])),
            "cover_prompt_1x1.txt": cover_prompts.get("1:1") or cover_prompts.get("Square Album Cover 1:1") or "",
            "cover_prompt_9x16.txt": cover_prompts.get("9:16") or "",
            "cover_prompt_16x9.txt": cover_prompts.get("16:9") or "",
            "thumbnail_prompt.txt": cover_prompts.get("9:16") or cover_prompts.get("16:9") or "",
            "upload_checklist.txt": "\n".join([
                "[ ] Review final_hook_clip.mp4 on mobile",
                "[ ] Check Thai subtitles are readable",
                "[ ] Copy TikTok caption",
                "[ ] Copy YouTube caption",
                "[ ] Copy hashtags",
                "[ ] Review cover prompt before generating artwork",
                "[ ] Review AI outputs before publishing",
            ]),
        }
        written: Dict[str, str] = {}
        for filename, content in files.items():
            path = folder / filename
            path.write_text(str(content).strip() + "\n", encoding="utf-8-sig")
            written[filename] = str(path)
        manifest_path = folder / "creator_export_manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "generated_by": build_label(),
                    "project_name": project_name,
                    "workflow_mode": workflow_mode,
                    "files": written,
                    "release_package": release,
                    "api_keys_exported": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return {"ok": True, "message": "Creator final assets exported", "data": {"final_dir": str(folder), "files": written, "manifest": str(manifest_path), "release_package": release}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Creator final asset export failed", "data": {}, "error": str(exc)}
