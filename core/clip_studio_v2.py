from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from core.hook_audio import trim_hook_audio, validate_final_clip
from core.paths import workflow_project_root
from core.project_io import safe_name
from core.real_clip_pipeline import ensure_parent_dir
from core.video_muxer import ffprobe_summary, mux_video_shots_with_audio, write_ffprobe_text
from providers.veo_video_provider import VEO_MODEL, generate_veo_video_shot


CLIP_STUDIO_V2_MODE = "clip_studio_v2"


def build_clip_studio_v2_shot_prompts(full_hook_lyrics: str, *, hook_duration: float, mood_preset: str = "") -> list[dict[str, Any]]:
    count = max(3, min(5, math.ceil(max(6.0, hook_duration) / 4.0)))
    duration = max(2.0, min(4.0, hook_duration / count))
    lines = [line.strip() for line in str(full_hook_lyrics or "").splitlines() if line.strip()] or [str(full_hook_lyrics or "emotional hook").strip()]
    cameras = [
        "wide cinematic room shot with slow drift",
        "medium emotional profile shot with slow push-in",
        "over-shoulder reflection shot with natural hand movement",
        "close-up emotional eyes with subtle breathing motion",
        "soft release shot with slow pull-out",
    ]
    hook_context = " ".join(str(full_hook_lyrics or "").split())
    prompts = []
    for index in range(count):
        lyric = lines[index % len(lines)]
        prompt = (
            "single continuous cinematic video shot, realistic cinematic live-action, vertical 9:16, "
            "natural human motion, cinematic camera movement, same character, same location, same wardrobe, same lighting mood, "
            f"{cameras[index]}, emotional Thai music video mood, mood preset: {mood_preset}, lyric emotion: {lyric}, "
            f"full hook section context: {hook_context[:600]}, no text, no subtitle inside video, no subtitles, no logo, no watermark, "
            "no emoji, no meme style, no thumbnail style, no split screen, no storyboard"
        )
        prompts.append(
            {
                "shot_id": f"shot_{index + 1:02d}",
                "duration_seconds": round(duration, 2),
                "aspect_ratio": "9:16",
                "prompt": prompt,
                "subtitle": lyric,
            }
        )
    return prompts


def _subtitle_timing(shots: list[dict[str, Any]], total_duration: float) -> list[dict[str, Any]]:
    cursor = 0.0
    timing = []
    for index, shot in enumerate(shots):
        duration = float(shot.get("duration_seconds") or 2.0)
        end = total_duration if index == len(shots) - 1 else min(total_duration, cursor + duration)
        timing.append({"start": round(cursor, 2), "end": round(max(cursor + 0.5, end), 2), "text": shot.get("subtitle", ""), "subtitle": shot.get("subtitle", "")})
        cursor = end
    return timing


def _creator_files(final_dir: Path, song: dict[str, Any], full_hook_lyrics: str) -> dict[str, str]:
    title = str(song.get("title") or "VelaFlow Hook Clip").strip()
    artist = str(song.get("artist_name") or "VelaFlow Creator").strip()
    payload = {
        "tiktok_caption.txt": f"{full_hook_lyrics[:120]}\n\n#เพลงไทย #ThaiMusic #VelaFlow #TikTokMusic",
        "youtube_caption.txt": f"{title} - {artist}\n\nReal AI video hook clip generated with VelaFlow Clip Studio V2.",
        "hashtags.txt": f"#{title.replace(' ', '')} #ThaiMusic #เพลงไทย #เพลงเศร้า #VelaFlow",
        "cover_prompt_1x1.txt": f"cinematic emotional music cover for {title} by {artist}, no extra text",
        "cover_prompt_9x16.txt": f"vertical cinematic cover frame for {title} by {artist}, no extra text",
        "cover_prompt_16x9.txt": f"wide cinematic music thumbnail frame for {title} by {artist}, no extra text",
        "upload_checklist.txt": "[ ] Review final video\n[ ] Check audio sync\n[ ] Check subtitles\n[ ] Copy caption and hashtags",
    }
    written = {}
    for filename, content in payload.items():
        path = ensure_parent_dir(final_dir / filename)
        path.write_text(str(content).strip() + "\n", encoding="utf-8-sig")
        written[filename] = str(path)
    return written


def generate_clip_studio_v2(
    *,
    project_name: str,
    song: dict[str, Any],
    uploaded_mp3_path: str | Path,
    hook_start_time: float,
    hook_end_time: float,
    full_hook_lyrics: str,
    mood_preset: str = "",
    provider_settings: dict[str, Any] | None = None,
    video_provider_fn: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    provider_settings = provider_settings or {}
    video_provider_fn = video_provider_fn or generate_veo_video_shot
    hook_duration = max(1.0, float(hook_end_time) - float(hook_start_time))
    project_dir = workflow_project_root("song") / safe_name(project_name or "clip_studio_v2")
    exports_dir = project_dir / "exports"
    final_dir = exports_dir / "final"
    shots_dir = final_dir / "video_shots"
    debug_dir = exports_dir / "debug"
    final_dir.mkdir(parents=True, exist_ok=True)
    shots_dir.mkdir(parents=True, exist_ok=True)
    debug_dir.mkdir(parents=True, exist_ok=True)
    hook_audio = exports_dir / "hook_audio.mp3"
    audio_result = trim_hook_audio(uploaded_mp3_path, hook_audio, hook_start_time=hook_start_time, hook_end_time=hook_end_time)
    provider_debug = {
        "provider_selected": "gemini_veo",
        "api_key_detected": bool(provider_settings.get("gemini_api_key") or provider_settings.get("google_api_key") or provider_settings.get("veo_api_key")),
        "endpoint_used": "client.models.generate_videos",
        "model_used": provider_settings.get("model") or provider_settings.get("veo_model") or VEO_MODEL,
        "request_status": "pending",
        "polling_status": "",
        "download_status": "",
        "mp4_validation_result": {},
        "final_error": "",
    }
    if not audio_result.get("ok"):
        provider_debug["final_error"] = audio_result.get("error") or "hook_audio_trim_failed"
        return _fail(final_dir, debug_dir, project_name, provider_debug, hook_start_time, hook_end_time, hook_duration, [], [], provider_debug["final_error"])
    shot_prompts = build_clip_studio_v2_shot_prompts(full_hook_lyrics, hook_duration=hook_duration, mood_preset=mood_preset)
    shot_paths: list[str] = []
    shot_results: list[dict[str, Any]] = []
    for shot in shot_prompts:
        output = shots_dir / f"{shot['shot_id']}.mp4"
        result = video_provider_fn(
            shot["prompt"],
            output,
            duration_seconds=shot["duration_seconds"],
            aspect_ratio="9:16",
            settings=provider_settings,
        )
        shot_results.append({"shot": shot, "result": result})
        debug = (result.get("data") or {}).get("debug") or {}
        provider_debug.update({key: value for key, value in debug.items() if key in provider_debug})
        if not result.get("ok"):
            error = result.get("message") or result.get("error") or "Real AI Video provider unavailable or failed. No fallback was used."
            provider_debug["final_error"] = error
            return _fail(final_dir, debug_dir, project_name, provider_debug, hook_start_time, hook_end_time, hook_duration, shot_prompts, shot_results, error)
        validation = ffprobe_summary(output)
        if not validation.get("valid_mp4") or not validation.get("has_video"):
            provider_debug["final_error"] = "shot ffprobe validation failed"
            return _fail(final_dir, debug_dir, project_name, provider_debug, hook_start_time, hook_end_time, hook_duration, shot_prompts, shot_results, "shot ffprobe validation failed")
        shot_paths.append(str(output))
    subtitle_timing = _subtitle_timing(shot_prompts, hook_duration)
    final_mp4 = final_dir / "final_hook_clip.mp4"
    mux = mux_video_shots_with_audio(shot_paths, hook_audio, final_mp4, subtitle_timing=subtitle_timing, subtitles_dir=final_dir)
    validation = validate_final_clip(final_mp4, require_audio=True)
    ffprobe_text = write_ffprobe_text(final_mp4, debug_dir / "ffprobe_final.txt")
    success = bool(mux.get("ok") and validation.get("valid_mp4") and validation.get("has_video") and validation.get("has_audio"))
    if not success:
        provider_debug["final_error"] = mux.get("error") or validation.get("error") or "final ffprobe validation failed"
        return _fail(final_dir, debug_dir, project_name, provider_debug, hook_start_time, hook_end_time, hook_duration, shot_prompts, shot_results, provider_debug["final_error"], validation)
    assets = _creator_files(final_dir, song, full_hook_lyrics)
    manifest = _manifest(
        final_dir,
        project_name,
        provider_debug,
        hook_start_time,
        hook_end_time,
        hook_duration,
        shot_prompts,
        shot_results,
        shot_paths,
        str(final_mp4),
        validation,
        "",
        True,
    )
    return {
        "ok": True,
        "message": "Clip Studio V2 generated real AI video",
        "data": {
            "final_mp4": str(final_mp4),
            "hook_audio": str(hook_audio),
            "final_dir": str(final_dir),
            "shot_paths": shot_paths,
            "manifest_path": manifest,
            "provider_debug_path": str(debug_dir / "provider_debug.json"),
            "ffprobe_final": ffprobe_text,
            "creator_assets": assets,
            "validation": validation,
        },
        "error": "",
    }


def _fail(final_dir: Path, debug_dir: Path, project_name: str, provider_debug: dict[str, Any], start: float, end: float, duration: float, shot_prompts: list[dict[str, Any]], shot_results: list[dict[str, Any]], error: str, validation: dict[str, Any] | None = None) -> dict[str, Any]:
    provider_debug_path = ensure_parent_dir(debug_dir / "provider_debug.json")
    provider_debug_path.write_text(json.dumps(provider_debug, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = _manifest(final_dir, project_name, provider_debug, start, end, duration, shot_prompts, shot_results, [], "", validation or {}, error, False)
    return {
        "ok": False,
        "message": "Real AI Video provider unavailable or failed. No fallback was used.",
        "data": {"manifest_path": manifest, "provider_debug_path": str(provider_debug_path), "validation": validation or {}},
        "error": error,
    }


def _manifest(final_dir: Path, project_name: str, provider_debug: dict[str, Any], start: float, end: float, duration: float, shot_prompts: list[dict[str, Any]], shot_results: list[dict[str, Any]], shot_paths: list[str], final_video_path: str, validation: dict[str, Any], error: str, success: bool) -> str:
    payload = {
        "mode": CLIP_STUDIO_V2_MODE,
        "provider": provider_debug.get("provider_selected", "gemini_veo"),
        "model": provider_debug.get("model_used", VEO_MODEL),
        "real_ai_video_used": bool(success),
        "provider_confirmed_live": bool(success),
        "fallback_used": False,
        "hook_start_time": start,
        "hook_end_time": end,
        "hook_duration": duration,
        "shot_paths": shot_paths,
        "shot_prompts": shot_prompts,
        "shot_results": shot_results,
        "final_video_path": final_video_path,
        "ffprobe_summary": validation,
        "error": error,
        "api_keys_exported": False,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    path = ensure_parent_dir(final_dir / "video_generation_manifest.json")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)
