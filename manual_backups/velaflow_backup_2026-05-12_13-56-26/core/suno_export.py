from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
import re

from core.artist_presets import get_artist_preset
from core.instrument_tag_normalizer import normalize_lyrics_tags
from core.project_io import safe_name
from core.song_structure_intelligence import export_structure_plan_files
from core.version import build_label


ROOT = Path(__file__).resolve().parents[1]


def _project_folder(project_name: str, base_dir: str | Path | None = None) -> Path:
    root = Path(base_dir) if base_dir else ROOT / "project_data" / "projects"
    return root / safe_name(project_name or "project")


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


def _clean_hashtag(value: str) -> str:
    text = re.sub(r"[^\wก-๙]+", "", str(value or ""), flags=re.UNICODE)
    return f"#{text}" if text else ""


def _song_title(song: Dict[str, Any], project_name: str = "") -> str:
    return str(song.get("title") or project_name or "Untitled Song")


def safe_txt_filename(song_title: str | None, suffix: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', "", str(song_title or "")).strip()
    cleaned = re.sub(r"\s+", "_", cleaned)
    return f"{cleaned}_{suffix}.txt" if cleaned else "velaflow_export.txt"


def export_txt_filename(song: Dict[str, Any], project_name: str = "", workflow_mode: str = "Full Pipeline") -> str:
    suffix = "song_only" if workflow_mode == "Song Studio Only" else "full_pipeline"
    return safe_txt_filename(_song_title(song, project_name), suffix)


def _artist_name(song: Dict[str, Any]) -> str:
    artist = song.get("artist") or song.get("artist_name") or ""
    if artist:
        return str(artist)
    preset = get_artist_preset(song.get("artist_preset", "vela_moon"))
    return str(preset.get("artist_name") or "VelaFlow Artist")


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
    keywords = [
        title,
        artist,
        genre,
        mood,
        vocal_style,
        hook_text,
        "Thai music",
        "emotional song",
        "VelaFlow",
    ]
    seo_caption = f"{hook_text} - เพลงใหม่จาก {artist} ที่เล่าอารมณ์แบบ {mood.split(',')[0].strip()} ฟังง่ายและจำติดใจ"
    hashtags = []
    for tag in [
        "เพลงไทย",
        "เพลงใหม่",
        "เพลงเศร้า",
        "เพลงรัก",
        "เพลงอกหัก",
        "ThaiMusic",
        "Tpop",
        "PopRock",
        "เพลงเพราะ",
        "เพลงฮิต",
        "TikTokเพลงไทย",
        "Shorts",
        "Reels",
        artist,
        title,
        genre.split("/")[0],
        mood.split(",")[0],
        hook_text,
    ]:
        cleaned = _clean_hashtag(tag)
        if cleaned and cleaned not in hashtags:
            hashtags.append(cleaned)
        if len(hashtags) >= 20:
            break
    youtube_description = "\n".join([
        f"{title} - {artist}",
        "",
        f"{seo_caption}",
        "",
        "Credits:",
        f"Song / Concept: {artist}",
        "Produced with VelaFlow",
        "",
        "Hashtags:",
        " ".join(hashtags[:15]),
    ])
    tiktok_caption = f"{hook_text}\n\n{seo_caption}\n{' '.join(hashtags[:8])}"
    shorts_hooks = [
        hook_text,
        f"ถ้าประโยคนี้ตรงใจ ลองฟังท่อนนี้",
        f"{title} - ท่อนที่อยากให้เธอได้ยิน",
        "บางเพลงไม่ได้ดังเพราะเสียงดัง แต่ดังเพราะมันตรงใจ",
        "เก็บท่อนนี้ไว้ฟังตอนคิดถึงใครบางคน",
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
        "seo_caption": seo_caption,
        "tiktok_caption": tiktok_caption,
        "youtube_description": youtube_description,
        "hashtags": hashtags[:20],
        "shorts_hooks": shorts_hooks[:5],
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
    lyrics = song.get("normalized_song_output") or normalize_lyrics_tags(song.get("complete_lyrics", ""), preset)
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
        lyrics = song.get("normalized_song_output") or normalize_lyrics_tags(song.get("complete_lyrics", ""), preset)
        full_path = folder / export_txt_filename(song, project_name, workflow_mode)
        lyrics_path = folder / "lyrics_only.txt"
        full_text = build_suno_full_package(song, project_name, workflow_mode=workflow_mode)
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
