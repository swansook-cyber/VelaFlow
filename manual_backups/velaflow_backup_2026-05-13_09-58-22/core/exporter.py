import csv
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List
from core.character_consistency import (
    apply_character_to_prompt,
    build_character_prompt,
    consistency_report,
    normalize_character,
)
from core.project_io import safe_name
from core.branding import PROGRAM_NAME
from core.artist_presets import get_artist_preset
from core.instrument_tag_normalizer import normalize_lyrics_tags, validate_english_only_tags
from core.suno_export import build_suno_full_package, export_txt_filename
from core.song_structure_intelligence import structure_plan_markdown


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text or "", encoding="utf-8")


def _storyboard_markdown(storyboard: List[Dict[str, Any]]) -> str:
    lines = ["# Storyboard", "", "| Scene | Time | Duration | Lyric | Emotion | Scene Visual | Camera | Lighting | Transition |", "|---:|---|---:|---|---|---|---|---|---|"]
    for item in storyboard:
        lines.append(
            f"| {item.get('scene','')} | {item.get('time_range','')} | {item.get('duration_seconds','')} | {str(item.get('lyric_part','')).replace('|','/')} | "
            f"{str(item.get('emotion','')).replace('|','/')} | {str(item.get('scene_visual') or item.get('visual_description','')).replace('|','/')} | "
            f"{str(item.get('camera') or item.get('camera_motion','')).replace('|','/')} | {str(item.get('lighting','')).replace('|','/')} | "
            f"{str(item.get('transition','')).replace('|','/')} |"
        )
    return "\n".join(lines)


def export_package(base_dir: str, title: str, result: Dict[str, Any], lyrics: str = "", song_result: Dict[str, Any] | None = None, project: Dict[str, Any] | None = None) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = Path(base_dir) / f"{safe_name(title)}_{timestamp}"
    for sub in ["youtube", "tiktok", "facebook", "spotify", "exports", "prompts", "project_files", "video_slots", "image_slots", "reference_assets", "render_scripts"]:
        (folder / sub).mkdir(parents=True, exist_ok=True)

    _write(folder / "project_files" / "lyrics.txt", lyrics)
    _write(folder / "project_files" / "mv_analysis.json", json.dumps(result or {}, ensure_ascii=False, indent=2))
    _write(folder / "project_files" / "song_result.json", json.dumps(song_result or {}, ensure_ascii=False, indent=2))
    _write(folder / "project_files" / "project_settings.json", json.dumps(project or {}, ensure_ascii=False, indent=2))
    _write(folder / "project_files" / "README_EXPORT.txt", (
        f"{PROGRAM_NAME} Export Package\n"
        "1) ตรวจ Storyboard และ Prompt ทุกฉากก่อนส่งไปสร้างภาพ/วิดีโอ\n"
        "2) ใช้ image_slots เป็น prompt รายฉากสำหรับ Flux/SDXL/OpenAI/Leonardo/Midjourney\n"
        "3) ใช้ video_slots เป็น prompt รายฉากสำหรับ Kling/Runway/Luma/Flow\n"
        "4) นำไฟล์ video scene กลับมาวางตามชื่อ scene_01.mp4, scene_02.mp4 ...\n"
        "5) ใช้ render_scripts/ffmpeg_concat_list.txt หรือ V6 Render Lab เพื่อรวม MV\n"
        "6) ไม่มี Auto Upload ให้ตรวจไฟล์ก่อนอัปโหลดเอง\n"
    ))

    storyboard = (result or {}).get("storyboard", []) or []
    character = normalize_character(((project or {}).get("character", {}) or (result or {}).get("character_lock", {}) or {}))
    character_prompt = build_character_prompt(character)
    media_assets = ((project or {}).get("assets", {}) or {})
    video_assets = media_assets.get("videos", {}) or {}
    video_metadata = media_assets.get("video_metadata", {}) or {}
    _write(folder / "project_files" / "storyboard.md", _storyboard_markdown(storyboard))
    _write(folder / "project_files" / "character.json", json.dumps(character, ensure_ascii=False, indent=2))
    _write(folder / "project_files" / "character_prompt.txt", character_prompt)
    _write(folder / "project_files" / "character_consistency.json", json.dumps([
        {
            "scene": item.get("scene", index + 1),
            **consistency_report(item.get("image_prompt_with_character") or apply_character_to_prompt(item.get("expanded_prompt") or item.get("image_prompt", ""), character, character_prompt), character),
        }
        for index, item in enumerate(storyboard)
    ], ensure_ascii=False, indent=2))
    reference_value = character.get("reference_image_path", "") or ""
    reference_path = Path(reference_value)
    if reference_value and reference_path.is_file():
        shutil.copy2(reference_path, folder / "reference_assets" / reference_path.name)
    if storyboard:
        fieldnames = ["scene","time_range","duration_seconds","pacing_note","lyric_part","emotion","scene_visual","visual_description","camera","camera_motion","lighting","transition","subtitle_style","prompt_core","expanded_prompt","character_prompt","image_prompt","image_prompt_with_character","character_consistency_score","video_prompt","negative_prompt"]
        with (folder / "project_files" / "storyboard.csv").open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for item in storyboard:
                writer.writerow({k: item.get(k, "") for k in fieldnames})

    concat_lines = []
    image_lines, video_lines = [], []
    for item in storyboard:
        scene = str(item.get("scene", "")).zfill(2)
        head = f"Scene {scene} | {item.get('time_range','')} | {item.get('lyric_part','')}"
        image_prompt = item.get("image_prompt_with_character") or apply_character_to_prompt(item.get("expanded_prompt") or item.get("image_prompt", ""), character, character_prompt)
        image_lines += [head, image_prompt, f"Negative: {item.get('negative_prompt','')}", "-"*80]
        video_prompt = apply_character_to_prompt(item.get("video_prompt", ""), character, character_prompt)
        video_lines += [head, video_prompt, f"Camera: {item.get('camera_motion','')}", "-"*80]
        _write(folder / "image_slots" / f"scene_{scene}_image_prompt.txt", image_prompt)
        _write(folder / "video_slots" / f"scene_{scene}_video_prompt.txt", video_prompt)
        scene_key = str(int(scene)) if scene.isdigit() else scene
        video_src = Path(video_assets.get(scene_key) or video_assets.get(scene) or "")
        suffix = video_src.suffix if video_src.is_file() else ".mp4"
        concat_lines.append(f"file '../video_slots/scene_{scene}{suffix}'")
    _write(folder / "prompts" / "image_prompts.txt", "\n".join(image_lines))
    _write(folder / "prompts" / "video_prompts.txt", "\n".join(video_lines))
    _write(folder / "render_scripts" / "ffmpeg_concat_list.txt", "\n".join(concat_lines))

    caps = (result or {}).get("captions", {}) or {}
    hashtags = " ".join(caps.get("hashtags", []) or [])
    _write(folder / "youtube" / "youtube_titles.txt", "\n".join(caps.get("youtube_title_options", []) or []))
    _write(folder / "youtube" / "youtube_description.txt", caps.get("youtube_description", ""))
    _write(folder / "youtube" / "youtube_hashtags.txt", hashtags)
    _write(folder / "tiktok" / "tiktok_caption.txt", caps.get("tiktok_caption", ""))
    _write(folder / "facebook" / "facebook_caption.txt", caps.get("facebook_caption", ""))
    _write(folder / "facebook" / "pinned_comment.txt", caps.get("pinned_comment", ""))

    covers = (result or {}).get("cover_prompts", {}) or {}
    _write(folder / "spotify" / "cover_prompt_1x1.txt", covers.get("spotify_1x1", ""))
    _write(folder / "youtube" / "thumbnail_prompt_16x9.txt", covers.get("youtube_thumbnail_16x9", ""))
    _write(folder / "tiktok" / "cover_prompt_9x16.txt", covers.get("tiktok_cover_9x16", ""))

    if song_result:
        artist_preset = get_artist_preset(song_result.get("artist_preset", "vela_moon"))
        normalized_lyrics = song_result.get("normalized_song_output") or normalize_lyrics_tags(song_result.get("complete_lyrics", ""), artist_preset)
        validation = validate_english_only_tags(normalized_lyrics)
        _write(folder / "project_files" / "song.json", json.dumps(song_result, ensure_ascii=False, indent=2))
        _write(folder / "spotify" / "suno_lyrics.txt", normalized_lyrics)
        _write(folder / "exports" / export_txt_filename(song_result, title, "Full Pipeline"), build_suno_full_package(song_result, title, workflow_mode="Full Pipeline"))
        _write(folder / "exports" / "lyrics_only.txt", normalized_lyrics)
        _write(folder / "spotify" / "suno_style_prompt.txt", song_result.get("music_style_prompt", ""))
        _write(folder / "spotify" / "suno_settings.json", json.dumps({
            "advanced_settings": song_result.get("advanced_settings", {}),
            "instrument_selection": song_result.get("instrument_selection", {}),
            "instrument_tags": song_result.get("instrument_tags", {}),
            "energy_curve": song_result.get("energy_curve", {}),
            "artist_preset": song_result.get("artist_preset", "vela_moon"),
            "instrument_tags_language": song_result.get("instrument_tags_language", "English only"),
        }, ensure_ascii=False, indent=2))
        _write(folder / "spotify" / "artist_preset.json", json.dumps(song_result.get("artist_preset_data") or artist_preset, ensure_ascii=False, indent=2))
        _write(folder / "spotify" / "hook_candidates.json", json.dumps(song_result.get("hook_candidates") or song_result.get("candidate_hooks", []), ensure_ascii=False, indent=2))
        _write(folder / "spotify" / "selected_hook.json", json.dumps(song_result.get("selected_hook") or {"hook_text": song_result.get("selected_hook_text", "")}, ensure_ascii=False, indent=2))
        _write(folder / "spotify" / "instrument_tag_validation.json", json.dumps(validation, ensure_ascii=False, indent=2))
        structure_plan = song_result.get("song_structure_plan") or {}
        if structure_plan:
            _write(folder / "exports" / "song_structure_plan.json", json.dumps(structure_plan, ensure_ascii=False, indent=2))
            _write(folder / "exports" / "song_structure_plan.md", structure_plan_markdown(structure_plan))
        _write(folder / "tiktok" / "tiktok_cut_recommendations.txt", json.dumps(song_result.get("tiktok_clip_cut_recommendation", []), ensure_ascii=False, indent=2))
        _write(folder / "spotify" / "suno_music_style_prompt.txt", song_result.get("music_style_prompt", ""))
        _write(folder / "spotify" / "complete_lyrics_for_suno.txt", normalized_lyrics)
        _write(folder / "tiktok" / "song_clip_cut_recommendations.txt", json.dumps(song_result.get("tiktok_clip_cut_recommendation", []), ensure_ascii=False, indent=2))
    image_assets = media_assets
    _write(folder / "project_files" / "image_review.json", json.dumps({
        "approved_images": image_assets.get("approved_images", {}),
        "rejected_images": image_assets.get("rejected_images", {}),
        "locked_images": image_assets.get("locked_images", {}),
        "hero_shot": image_assets.get("hero_shot", ""),
        "image_versions": image_assets.get("image_versions", {}),
    }, ensure_ascii=False, indent=2))
    _write(folder / "project_files" / "video_pipeline.json", json.dumps({
        "videos": image_assets.get("videos", {}),
        "video_versions": image_assets.get("video_versions", {}),
        "video_metadata": image_assets.get("video_metadata", {}),
        "locked_videos": image_assets.get("locked_videos", {}),
    }, ensure_ascii=False, indent=2))
    images = image_assets.get("approved_images", {}) or {}
    for scene, image_path in images.items():
        src = Path(image_path)
        if src.exists():
            shutil.copy2(src, folder / "image_slots" / f"scene_{str(scene).zfill(2)}{src.suffix or '.png'}")
    for scene, video_path in video_assets.items():
        src = Path(video_path)
        scene_label = str(scene).zfill(2)
        meta = video_metadata.get(str(scene), {})
        if src.is_file():
            shutil.copy2(src, folder / "video_slots" / f"scene_{scene_label}{src.suffix or '.mp4'}")
        metadata_path = Path(meta.get("metadata_path", "") or src.with_suffix(".json"))
        if metadata_path.is_file():
            shutil.copy2(metadata_path, folder / "video_slots" / f"scene_{scene_label}_video_metadata.json")
        slot_note_path = Path(meta.get("slot_note_path", "") or src.with_suffix(".video_slot.txt"))
        if slot_note_path.is_file():
            shutil.copy2(slot_note_path, folder / "video_slots" / f"scene_{scene_label}_video_slot.txt")
    return folder
