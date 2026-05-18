from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from core.paths import workflow_project_root
from core.project_io import safe_name
from core.real_clip_pipeline import combine_scene_clips_to_mp4, ensure_parent_dir, trim_audio_clip, validate_mp4, write_subtitles
from core.subtitle_engine import generate_styled_subtitles
from providers.video_ai import generate_video_shot


MUSIC_VIDEO_V2_VERSION = "music_video_v2_real_ai_video_only"


def _split_hook_lines(text: str, count: int) -> list[str]:
    cleaned = [line.strip() for line in str(text or "").replace("|", "\n").splitlines() if line.strip()]
    if not cleaned:
        cleaned = ["เสียงในท่อนฮุกนี้ยังอยู่ในใจ"]
    while len(cleaned) < count:
        cleaned.append(cleaned[-1])
    return cleaned[:count]


def build_music_video_v2_shot_plan(
    *,
    full_hook_lyrics: str,
    duration_seconds: float,
    mood: str = "",
    shot_count: int | None = None,
) -> list[dict[str, Any]]:
    duration = max(2.0, float(duration_seconds or 0))
    count = int(shot_count or max(4, min(8, math.ceil(duration / 3.0))))
    per_shot = max(2.0, min(4.0, duration / count))
    lines = _split_hook_lines(full_hook_lyrics, count)
    camera = [
        "wide lonely establishing shot, slow cinematic drift",
        "medium emotional profile shot, slow push-in",
        "over-shoulder reflection shot, subtle handheld motion",
        "close-up emotional eyes, strongest hook moment",
        "side profile in same room, gentle parallax depth",
        "soft release shot, slow pull-out",
        "room detail with character in negative space, slow pan",
        "ending close-up with emotional breathing motion",
    ]
    hook = " ".join(str(full_hook_lyrics or "").split())
    plan: list[dict[str, Any]] = []
    for index in range(count):
        prompt = (
            "single continuous cinematic video shot, ultra realistic live-action, vertical 9:16, "
            "natural human motion, cinematic camera movement, realistic skin texture, natural room lighting, "
            "same character, same face, same hairstyle, same wardrobe, same location, same lighting mood, "
            f"{camera[index % len(camera)]}, emotional Thai music video feeling, mood: {mood}, "
            f"hook lyric beat: {lines[index]}, full hook section context: {hook[:520]}, "
            "no text, no subtitles, no logo, no watermark, no emoji, no meme style, no thumbnail style, no split screen, no storyboard"
        )
        plan.append(
            {
                "shot_id": f"shot_{index + 1:02d}",
                "duration_seconds": round(per_shot, 2),
                "aspect_ratio": "9:16",
                "motion_style": camera[index % len(camera)],
                "subtitle": lines[index],
                "prompt": prompt,
            }
        )
    return plan


def _subtitle_timing(lines: list[str], duration: float) -> list[dict[str, Any]]:
    count = max(1, len(lines))
    step = max(0.5, duration / count)
    timing = []
    for index, line in enumerate(lines):
        start = round(index * step, 2)
        end = round(duration if index == count - 1 else min(duration, (index + 1) * step), 2)
        timing.append({"start": start, "end": max(start + 0.4, end), "text": line, "subtitle": line})
    return timing


def _write_creator_assets(final_dir: Path, song: dict[str, Any], full_hook_lyrics: str) -> dict[str, str]:
    title = str(song.get("title") or song.get("song_title") or "VelaFlow Hook Clip").strip()
    artist = str(song.get("artist_name") or song.get("artist") or "VelaFlow Creator").strip()
    mood = str(song.get("mood") or "cinematic emotional").strip()
    files = {
        "tiktok_caption.txt": f"{full_hook_lyrics.strip()[:120]}\n\n#{title.replace(' ', '')} #เพลงเศร้า #ThaiMusic #VelaFlow",
        "youtube_caption.txt": f"{title} - {artist}\n\nCinematic emotional hook clip generated with VelaFlow Music Video V2.\nMood: {mood}",
        "hashtags.txt": f"#{title.replace(' ', '')} #ThaiMusic #เพลงไทย #เพลงเศร้า #EmotionalSong #TikTokMusic #VelaFlow",
        "cover_prompt_1x1.txt": f"cinematic realistic album cover for {title} by {artist}, {mood}, no extra text, premium music artwork",
        "cover_prompt_9x16.txt": f"vertical cinematic music cover frame for {title} by {artist}, emotional close-up, {mood}, no extra text",
        "cover_prompt_16x9.txt": f"wide cinematic YouTube music thumbnail frame for {title} by {artist}, emotional room lighting, no extra text",
        "upload_checklist.txt": "\n".join(
            [
                "[ ] Review final_hook_clip.mp4 on mobile",
                "[ ] Check audio sync",
                "[ ] Check bottom-safe subtitles",
                "[ ] Copy TikTok caption",
                "[ ] Copy YouTube caption",
                "[ ] Copy hashtags",
            ]
        ),
    }
    written: dict[str, str] = {}
    for filename, content in files.items():
        path = ensure_parent_dir(final_dir / filename)
        path.write_text(str(content).strip() + "\n", encoding="utf-8-sig")
        written[filename] = str(path)
    return written


def generate_music_video_v2(
    *,
    project_name: str,
    song: dict[str, Any],
    uploaded_audio_path: str | Path,
    hook_start_time: float,
    hook_end_time: float,
    full_hook_lyrics: str,
    provider: str = "gemini_veo",
    video_settings: dict[str, Any] | None = None,
    video_provider_fn: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    video_settings = video_settings or {}
    video_provider_fn = video_provider_fn or generate_video_shot
    project_dir = workflow_project_root("song") / safe_name(project_name or "music_video_v2")
    exports_dir = project_dir / "exports"
    final_dir = exports_dir / "final"
    shots_dir = final_dir / "video_shots"
    debug_dir = exports_dir / "debug"
    final_dir.mkdir(parents=True, exist_ok=True)
    shots_dir.mkdir(parents=True, exist_ok=True)
    debug_dir.mkdir(parents=True, exist_ok=True)
    duration = max(1.0, float(hook_end_time) - float(hook_start_time))
    hook_audio = exports_dir / "hook_audio.mp3"
    trim = trim_audio_clip(uploaded_audio_path, hook_audio, start_time=hook_start_time, end_time=hook_end_time)
    provider_debug = {
        "provider_selected": provider,
        "api_key_detected": bool(video_settings.get("gemini_api_key") or video_settings.get("google_api_key") or video_settings.get("veo_api_key")),
        "endpoint_used": "client.models.generate_videos",
        "model_used": video_settings.get("model") or video_settings.get("veo_model") or "veo-3.1-generate-preview",
        "request_status": "pending",
        "polling_status": "",
        "download_status": "",
        "mp4_validation_result": {},
        "final_error": "",
    }
    if not trim.get("ok"):
        provider_debug["final_error"] = trim.get("error") or "hook_audio_trim_failed"
        ensure_parent_dir(debug_dir / "provider_debug.json").write_text(json.dumps(provider_debug, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": False, "message": "Hook audio trim failed", "data": {"provider_debug_path": str(debug_dir / "provider_debug.json")}, "error": provider_debug["final_error"]}
    shot_plan = build_music_video_v2_shot_plan(full_hook_lyrics=full_hook_lyrics, duration_seconds=duration, mood=str(song.get("mood") or ""))
    shot_paths: list[str] = []
    shot_results: list[dict[str, Any]] = []
    for shot in shot_plan:
        output = shots_dir / f"{shot['shot_id']}.mp4"
        result = video_provider_fn(
            shot["prompt"],
            shot["duration_seconds"],
            output,
            provider=provider,
            aspect_ratio="9:16",
            motion_style=shot["motion_style"],
            settings=video_settings,
        )
        shot_results.append({"shot": shot, "result": result})
        provider_debug["request_status"] = "ok" if result.get("ok") else "failed"
        provider_debug["polling_status"] = (result.get("data") or {}).get("provider_status", "")
        provider_debug["download_status"] = "downloaded" if result.get("ok") else ""
        provider_debug["mp4_validation_result"] = (result.get("data") or {}).get("validation", {})
        if not result.get("ok"):
            provider_debug["final_error"] = result.get("error") or "real_ai_video_provider_failed"
            ensure_parent_dir(debug_dir / "provider_debug.json").write_text(json.dumps(provider_debug, ensure_ascii=False, indent=2), encoding="utf-8")
            manifest = _write_v2_manifest(final_dir, project_name, provider, shot_plan, shot_results, [], "", {}, provider_debug, False)
            return {
                "ok": False,
                "message": "Real AI Video provider unavailable. Please add a valid Veo/Gemini video key.",
                "data": {"manifest_path": manifest, "provider_debug_path": str(debug_dir / "provider_debug.json"), "shot_results": shot_results},
                "error": provider_debug["final_error"],
            }
        validation = validate_mp4(output, min_duration=1.0, min_file_size=100 * 1024)
        if not validation.get("valid_mp4") or not validation.get("has_video"):
            provider_debug["final_error"] = validation.get("error") or "provider_returned_no_valid_mp4"
            ensure_parent_dir(debug_dir / "provider_debug.json").write_text(json.dumps(provider_debug, ensure_ascii=False, indent=2), encoding="utf-8")
            manifest = _write_v2_manifest(final_dir, project_name, provider, shot_plan, shot_results, [], "", validation, provider_debug, False)
            return {"ok": False, "message": "Provider returned no MP4", "data": {"manifest_path": manifest, "provider_debug_path": str(debug_dir / "provider_debug.json")}, "error": provider_debug["final_error"]}
        shot_paths.append(str(output))
    subtitles = _subtitle_timing([shot["subtitle"] for shot in shot_plan], duration)
    srt_path = final_dir / "subtitles.srt"
    write_subtitles(subtitles, srt_path, total_duration=duration)
    styled = generate_styled_subtitles(subtitles, final_dir, subtitle_style="Thai Emotional MV")
    ass_path = Path(str((styled.get("data") or {}).get("ass") or ""))
    final_mp4 = final_dir / "final_hook_clip.mp4"
    combined = combine_scene_clips_to_mp4(
        shot_paths,
        final_mp4,
        subtitle_path=ass_path if ass_path.is_file() else srt_path,
        background_audio_path=hook_audio,
    )
    final_validation = (combined.get("data") or {}).get("validation") or validate_mp4(final_mp4, require_audio=True)
    ok = bool(combined.get("ok") and final_validation.get("valid_mp4") and final_validation.get("has_audio") and final_validation.get("has_video"))
    provider_debug["mp4_validation_result"] = final_validation
    provider_debug["final_error"] = "" if ok else (combined.get("error") or final_validation.get("error") or "final_video_validation_failed")
    provider_debug_path = ensure_parent_dir(debug_dir / "provider_debug.json")
    provider_debug_path.write_text(json.dumps(provider_debug, ensure_ascii=False, indent=2), encoding="utf-8")
    creator_assets = _write_creator_assets(final_dir, song, full_hook_lyrics)
    manifest_path = _write_v2_manifest(final_dir, project_name, provider, shot_plan, shot_results, shot_paths, str(final_mp4), final_validation, provider_debug, ok)
    if not ok:
        return {"ok": False, "message": "Music Video V2 final MP4 failed validation", "data": {"manifest_path": manifest_path, "provider_debug_path": str(provider_debug_path), "validation": final_validation}, "error": provider_debug["final_error"]}
    return {
        "ok": True,
        "message": "Music Video V2 generated",
        "data": {
            "final_mp4": str(final_mp4),
            "hook_audio": str(hook_audio),
            "subtitles": str(srt_path),
            "styled_subtitles": str(ass_path) if ass_path.is_file() else "",
            "final_dir": str(final_dir),
            "shot_paths": shot_paths,
            "manifest_path": manifest_path,
            "provider_debug_path": str(provider_debug_path),
            "creator_assets": creator_assets,
            "validation": final_validation,
        },
        "error": "",
    }


def _write_v2_manifest(
    final_dir: Path,
    project_name: str,
    provider: str,
    shot_plan: list[dict[str, Any]],
    shot_results: list[dict[str, Any]],
    shot_paths: list[str],
    final_video_path: str,
    validation: dict[str, Any],
    provider_debug: dict[str, Any],
    success: bool,
) -> str:
    manifest = {
        "generated_by": "VelaFlow",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "workflow": MUSIC_VIDEO_V2_VERSION,
        "project_name": project_name,
        "provider_used": provider,
        "real_ai_video_used": bool(success),
        "fallback_used": False,
        "provider_confirmed_live": bool(success),
        "shot_plan": shot_plan,
        "shot_paths": shot_paths,
        "shot_durations": [shot.get("duration_seconds") for shot in shot_plan],
        "shot_results": shot_results,
        "final_video_path": final_video_path,
        "validation_result": validation,
        "provider_debug": provider_debug,
        "api_keys_exported": False,
    }
    path = ensure_parent_dir(final_dir / "video_generation_manifest.json")
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    mirror = ensure_parent_dir(final_dir / "music_video_v2_manifest.json")
    mirror.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)
