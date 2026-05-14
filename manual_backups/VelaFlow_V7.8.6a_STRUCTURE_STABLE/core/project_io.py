import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict
from core.character_consistency import (
    apply_character_to_prompt,
    build_character_prompt,
    consistency_report,
    normalize_character,
)
from core.branding import DEFAULT_ARTIST
from core.artist_presets import get_artist_preset
from core.instrument_tag_normalizer import normalize_lyrics_tags, validate_english_only_tags


def safe_name(name: str) -> str:
    keep = [ch for ch in (name or "").strip() if ch.isalnum() or ch in (" ", "-", "_")]
    return ("".join(keep).strip().replace(" ", "_") or "untitled_project")


def _backup_if_exists(path: Path) -> None:
    if not path.exists():
        return
    backup_dir = path.parent / "_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{path.stem}_{stamp}{path.suffix}"
    backup_path.write_bytes(path.read_bytes())


def new_project(title: str, artist: str = DEFAULT_ARTIST) -> Dict[str, Any]:
    return {
        "version": "VelaFlow V7.8.6a",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "title": title,
        "artist": artist,
        "song": {},
        "mv": {},
        "scene_edits": [],
        "character": normalize_character({}),
        "settings": {},
        "assets": {
            "audio_path": "",
            "images": {},
            "image_versions": {},
            "approved_images": {},
            "rejected_images": {},
            "locked_images": {},
            "hero_shot": "",
            "character_references": {},
            "videos": {},
            "video_versions": {},
            "video_metadata": {},
            "locked_videos": {},
        },
        "exports": [],
    }


def save_project(project: Dict[str, Any], base_dir: str = "outputs/projects") -> Path:
    folder = Path(base_dir)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{safe_name(project.get('title','project'))}_v6_project.json"
    _backup_if_exists(path)
    path.write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def save_project_folder(project: Dict[str, Any], base_dir: str = "project_data/projects") -> Path:
    folder = Path(base_dir) / safe_name(project.get("title", "project"))
    folder.mkdir(parents=True, exist_ok=True)
    song = project.get("song", {}) or {}
    mv = project.get("mv", {}) or {}
    settings = project.get("settings", {}) or {}
    character = normalize_character(project.get("character") or mv.get("character_lock", {}) or {})
    assets = project.get("assets", {}) or {}
    storyboard = mv.get("storyboard", []) or []
    _backup_if_exists(folder / "project.json")
    (folder / "project.json").write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "song.json").write_text(json.dumps(song, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "storyboard.json").write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "prompts.json").write_text(json.dumps({
        "image_prompts": [item.get("image_prompt_with_character") or apply_character_to_prompt(item.get("expanded_prompt") or item.get("image_prompt", ""), character) for item in storyboard],
        "video_prompts": [item.get("video_prompt", "") for item in storyboard],
        "negative_prompts": [item.get("negative_prompt", "") for item in storyboard],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "settings.json").write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "character.json").write_text(json.dumps(character, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "character_prompt.txt").write_text(build_character_prompt(character), encoding="utf-8")
    (folder / "character_consistency.json").write_text(json.dumps([
        {
            "scene": item.get("scene", index + 1),
            **consistency_report(item.get("image_prompt_with_character") or apply_character_to_prompt(item.get("expanded_prompt") or item.get("image_prompt", ""), character), character),
        }
        for index, item in enumerate(storyboard)
    ], ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "image_review.json").write_text(json.dumps({
        "images": assets.get("images", {}),
        "image_versions": assets.get("image_versions", {}),
        "approved_images": assets.get("approved_images", {}),
        "rejected_images": assets.get("rejected_images", {}),
        "locked_images": assets.get("locked_images", {}),
        "hero_shot": assets.get("hero_shot", ""),
        "character_references": assets.get("character_references", {}),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "video_pipeline.json").write_text(json.dumps({
        "videos": assets.get("videos", {}),
        "video_versions": assets.get("video_versions", {}),
        "video_metadata": assets.get("video_metadata", {}),
        "locked_videos": assets.get("locked_videos", {}),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    preset = get_artist_preset(song.get("artist_preset", "vela_moon"))
    normalized_lyrics = song.get("normalized_song_output") or normalize_lyrics_tags(song.get("complete_lyrics", "") or project.get("manual_lyrics", ""), preset)
    (folder / "lyrics.txt").write_text(normalized_lyrics, encoding="utf-8")
    (folder / "song.json").write_text(json.dumps({
        **song,
        "normalized_song_output": normalized_lyrics,
        "instrument_tag_validation": validate_english_only_tags(normalized_lyrics),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "artist_preset.json").write_text(json.dumps(song.get("artist_preset_data") or preset, ensure_ascii=False, indent=2), encoding="utf-8")
    return folder


def load_project(path: str) -> Dict[str, Any]:
    source = Path(path)
    try:
        return json.loads(source.read_text(encoding="utf-8"))
    except Exception:
        broken = source.with_suffix(f".broken_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        if source.exists():
            source.replace(broken)
        return new_project(source.stem.replace("_v6_project", ""))
