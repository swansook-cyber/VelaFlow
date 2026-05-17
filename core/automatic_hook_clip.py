from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from core.character_engine import apply_character_consistency, create_character_profile, save_character_profile
from core.beat_timing_engine import apply_beat_timing_to_package, create_beat_timing_plan, save_beat_timing
from core.hook_clip_engine import build_hook_render_package, export_hook_clip_package
from core.hook_intelligence import analyze_opening_hook, save_hook_analysis
from core.paths import workflow_project_root
from core.preset_engine import get_preset, preset_to_render_settings, preset_to_visual_settings
from core.project_io import safe_name
from core.real_clip_pipeline import ensure_parent_dir, render_real_hook_clip
from core.render_cache import cache_fingerprint, copy_cached_assets_to_project, load_render_cache, save_render_cache
from core.scene_prompt_engine import apply_scene_director_to_package, apply_scene_prompts_to_package, build_cinematic_quality_report, build_scene_director_plan, build_scene_prompts, save_cinematic_quality_report, save_scene_director_plan, save_scene_prompts
from core.subtitle_engine import generate_styled_subtitles
from core.thumbnail_selector import export_thumbnail
from core.versioning import save_clip_version
from core.viral_timing_engine import create_viral_timing_plan, save_viral_timing_plan
from core.voiceover_engine import generate_voiceover_audio
from providers.image_ai import generate_image, generate_image_with_diagnostics


DEFAULT_VISUAL_SETTINGS = {
    "camera_preset": "TikTok Creator",
    "lighting_preset": "Natural Daylight",
    "motion_preset": "Fast TikTok Cuts",
    "visual_mood": "Viral",
}

DEFAULT_RENDER_SETTINGS = {
    "provider": "Local FFmpeg",
    "aspect_ratio": "9:16",
    "duration": "15s",
    "quality": "Draft",
    "motion_intensity": "High",
    "bundle_name": "Quick Hook Clip",
}

MOTION_EFFECTS = ["slow_zoom", "pan_left", "shake", "cinematic_fade"]
PRESET_MOTION_SEQUENCES = {
    "shake_zoom": ["shake_zoom", "shake_zoom", "hard_cut"],
    "slow_cinematic": ["slow_cinematic", "minimal_pan", "cinematic_fade"],
    "product_focus": ["product_focus", "slow_zoom", "fast_cut"],
    "minimal_pan": ["minimal_pan", "minimal_pan", "dark_fade"],
    "bounce": ["bounce", "bounce", "cartoon_pop"],
    "cinematic_mv": ["cinematic_mv", "slow_cinematic", "film_fade"],
}
VOICE_STYLE_MAP = {
    "energetic": "meme voice",
    "sales": "meme voice",
    "cute": "meme voice",
    "narrator": "calm narrator",
    "calm_narrator": "calm narrator",
    "music": "emotional storyteller",
}


def export_tiktok_package(project_name: str, package: dict[str, Any], render_data: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        workflow_type = "song" if package.get("source_workflow") in {"music", "music_mv", "song"} else "clips"
        project_dir = workflow_project_root(workflow_type) / safe_name(project_name or "hook_clip")
        exports_dir = project_dir / "exports"
        final_dir = exports_dir / "final"
        final_dir.mkdir(parents=True, exist_ok=True)
        render_data = render_data or {}
        final_mp4 = Path(str(render_data.get("final_mp4") or ""))
        subtitle_path = Path(str(render_data.get("subtitles") or exports_dir / "subtitles.srt"))
        if final_mp4.is_file():
            shutil.copy2(final_mp4, ensure_parent_dir(final_dir / "final_hook_clip.mp4"))
        if subtitle_path.is_file():
            shutil.copy2(subtitle_path, ensure_parent_dir(final_dir / "subtitles.srt"))
        styled_subtitles = Path(str(render_data.get("styled_subtitles") or package.get("styled_subtitles_path") or ""))
        if styled_subtitles.is_file():
            shutil.copy2(styled_subtitles, ensure_parent_dir(final_dir / "styled_subtitles.ass"))
        thumbnail = Path(str(render_data.get("thumbnail") or package.get("thumbnail_path") or ""))
        if thumbnail.is_file():
            shutil.copy2(thumbnail, ensure_parent_dir(final_dir / "thumbnail.jpg"))
        thumbnail_score = Path(str(render_data.get("thumbnail_score") or package.get("thumbnail_score_path") or ""))
        if thumbnail_score.is_file():
            shutil.copy2(thumbnail_score, ensure_parent_dir(final_dir / "thumbnail_score.json"))
        scene_prompts = Path(str(render_data.get("scene_prompts") or package.get("scene_prompts_path") or ""))
        if scene_prompts.is_file():
            shutil.copy2(scene_prompts, ensure_parent_dir(final_dir / "scene_prompts.json"))
        beat_timing = Path(str(render_data.get("beat_timing") or package.get("beat_timing_path") or ""))
        if beat_timing.is_file():
            shutil.copy2(beat_timing, ensure_parent_dir(final_dir / "beat_timing.json"))
        scene_director_plan = Path(str(render_data.get("scene_director_plan") or package.get("scene_director_plan_path") or ""))
        if scene_director_plan.is_file():
            shutil.copy2(scene_director_plan, ensure_parent_dir(final_dir / "scene_director_plan.json"))
        cinematic_quality_report = Path(str(render_data.get("cinematic_quality_report") or package.get("cinematic_quality_report_path") or ""))
        if cinematic_quality_report.is_file():
            shutil.copy2(cinematic_quality_report, ensure_parent_dir(final_dir / "cinematic_quality_report.json"))
        render_manifest = Path(str(render_data.get("manifest_path") or package.get("render_manifest_path") or ""))
        if render_manifest.is_file():
            shutil.copy2(render_manifest, ensure_parent_dir(final_dir / "render_manifest.json"))
        render_stage = Path(str(render_data.get("render_stage_path") or package.get("render_stage_path") or ""))
        if render_stage.is_file():
            shutil.copy2(render_stage, ensure_parent_dir(final_dir / "render_stage.json"))
        image_manifest = Path(str(render_data.get("image_generation_manifest") or package.get("image_generation_manifest_path") or ""))
        if image_manifest.is_file():
            shutil.copy2(image_manifest, ensure_parent_dir(final_dir / "image_generation_manifest.json"))
        hook_analysis_file = Path(str(render_data.get("hook_analysis") or package.get("hook_analysis_path") or ""))
        if hook_analysis_file.is_file():
            shutil.copy2(hook_analysis_file, ensure_parent_dir(final_dir / "hook_analysis.json"))
        for item in package.get("image_results", []) or []:
            image_path = Path(str(item.get("path") or ""))
            scene_id = str(item.get("scene_id") or image_path.stem or "scene")
            if image_path.is_file():
                shutil.copy2(image_path, ensure_parent_dir(final_dir / f"{safe_name(scene_id)}.jpg"))
        hook_audio = Path(str(package.get("hook_audio_path") or render_data.get("background_audio_path") or ""))
        if hook_audio.is_file():
            shutil.copy2(hook_audio, ensure_parent_dir(final_dir / "hook_audio.mp3"))
        captions = str(package.get("caption") or package.get("subtitle_line") or package.get("hook_text") or "").strip()
        hashtags = package.get("hashtags") or ["#VelaFlow", "#TikTok", "#Reels", "#Shorts"]
        title = str(package.get("hook_text") or "VelaFlow Hook Clip").strip()
        thumbnail_prompt = str(package.get("thumbnail_prompt") or "").strip() or f"Vertical TikTok thumbnail for: {title}"
        checklist = [
            "[ ] Review final_hook_clip.mp4",
            "[ ] Check subtitles are readable on mobile",
            "[ ] Copy caption and hashtags",
            "[ ] Upload as 9:16 vertical clip",
            "[ ] Review AI output before publishing",
        ]
        timing_plan = package.get("viral_timing_plan") or create_viral_timing_plan(
            package,
            target_duration=(package.get("scene_package") or {}).get("duration_seconds"),
            preset_id=(package.get("creator_outcome_preset") or {}).get("preset_id", ""),
        )
        timing_result = save_viral_timing_plan(timing_plan, final_dir / "viral_timing_plan.json")
        files = {
            "captions.txt": captions,
            "hashtags.txt": " ".join(str(tag) for tag in hashtags),
            "title.txt": title,
            "title_ideas.txt": "\n".join([title, f"{title} | Hook Clip", f"{title} - Short Version"]),
            "thumbnail_prompt.txt": thumbnail_prompt,
            "upload_checklist.txt": "\n".join(checklist),
        }
        written: dict[str, str] = {}
        for filename, content in files.items():
            path = final_dir / filename
            ensure_parent_dir(path)
            path.write_text(str(content).strip() + "\n", encoding="utf-8-sig")
            written[filename] = str(path)
        manifest = {
            "generated_by": "VelaFlow",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "project_name": project_name,
            "final_dir": str(final_dir),
            "final_hook_clip": str(final_dir / "final_hook_clip.mp4") if (final_dir / "final_hook_clip.mp4").is_file() else "",
            "subtitles": str(final_dir / "subtitles.srt") if (final_dir / "subtitles.srt").is_file() else "",
            "hook_audio": str(final_dir / "hook_audio.mp3") if (final_dir / "hook_audio.mp3").is_file() else "",
            "styled_subtitles": str(final_dir / "styled_subtitles.ass") if (final_dir / "styled_subtitles.ass").is_file() else "",
            "thumbnail": str(final_dir / "thumbnail.jpg") if (final_dir / "thumbnail.jpg").is_file() else "",
            "thumbnail_score": str(final_dir / "thumbnail_score.json") if (final_dir / "thumbnail_score.json").is_file() else "",
            "scene_prompts": str(final_dir / "scene_prompts.json") if (final_dir / "scene_prompts.json").is_file() else "",
            "beat_timing": str(final_dir / "beat_timing.json") if (final_dir / "beat_timing.json").is_file() else "",
            "scene_director_plan": str(final_dir / "scene_director_plan.json") if (final_dir / "scene_director_plan.json").is_file() else "",
            "cinematic_quality_report": str(final_dir / "cinematic_quality_report.json") if (final_dir / "cinematic_quality_report.json").is_file() else "",
            "render_manifest": str(final_dir / "render_manifest.json") if (final_dir / "render_manifest.json").is_file() else "",
            "render_stage": str(final_dir / "render_stage.json") if (final_dir / "render_stage.json").is_file() else "",
            "image_generation_manifest": str(final_dir / "image_generation_manifest.json") if (final_dir / "image_generation_manifest.json").is_file() else "",
            "hook_analysis": str(final_dir / "hook_analysis.json") if (final_dir / "hook_analysis.json").is_file() else "",
            "viral_timing_plan": (timing_result.get("data") or {}).get("path", ""),
            "files": written,
        }
        manifest_path = final_dir / "tiktok_package_manifest.json"
        ensure_parent_dir(manifest_path)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "message": "TikTok package exported", "data": {**manifest, "manifest_path": str(manifest_path)}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "TikTok package export failed", "data": {}, "error": str(exc)}


def _idea_content(idea: str, source_workflow: str, preset: dict[str, Any]) -> dict[str, Any]:
    cleaned = " ".join(str(idea or "").split()).strip()
    if not cleaned:
        cleaned = "หยุดดูคลิปนี้ก่อน มีบางอย่างที่คุณอาจเจอเหมือนกัน"
    return {
        "selected_hook_text": cleaned[:120],
        "main_idea": cleaned,
        "source_workflow": source_workflow,
        "creator_outcome_preset": preset,
        "hook_direction": f"{preset.get('hook_style', 'viral')} hook, {preset.get('pace', 'fast')} pace",
        "viral_hooks": [cleaned],
        "subtitle_lines": [cleaned],
    }


def _score_hook_for_retention(text: str, hook_analysis: dict[str, Any], preset: dict[str, Any]) -> dict[str, Any]:
    value = " ".join(str(text or "").split()).strip()
    scores = hook_analysis.get("scores") or {}
    emotional = int(scores.get("emotional_intensity") or 45)
    curiosity = int(scores.get("curiosity") or 45)
    pacing = int(scores.get("pacing") or 60)
    meme = int(scores.get("meme_potential") or 45)
    readability = max(20, min(100, 110 - max(0, len(value) - 55)))
    replay = max(20, min(100, int((curiosity * 0.35) + (readability * 0.30) + (pacing * 0.20) + (meme * 0.15))))
    retention = max(20, min(100, int((emotional * 0.25) + (curiosity * 0.25) + (readability * 0.25) + (pacing * 0.25))))
    total = max(0, min(100, int((emotional + curiosity + replay + retention + readability) / 5)))
    if preset.get("pace") in {"fast", "fun"}:
        total = min(100, total + 5)
    return {
        "hook_score": total,
        "emotional_impact": emotional,
        "replay_potential": replay,
        "short_readability": readability,
        "curiosity_gap": curiosity,
        "tiktok_retention_potential": retention,
        "viral_pacing": pacing,
    }


def _strongest_hook_text(idea: str, hook_analysis: dict[str, Any], preset: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    candidates = [
        str(hook_analysis.get("opening_line") or "").strip(),
        str(hook_analysis.get("shock_line") or "").strip(),
        " ".join(str(idea or "").split()).strip(),
    ]
    scored = []
    for candidate in candidates:
        if not candidate:
            continue
        scored.append({"text": candidate, "scores": _score_hook_for_retention(candidate, hook_analysis, preset)})
    if not scored:
        fallback = "VelaFlow Hook Clip"
        return fallback, _score_hook_for_retention(fallback, hook_analysis, preset)
    best = sorted(scored, key=lambda item: item["scores"]["hook_score"], reverse=True)[0]
    return best["text"], best["scores"]


def _scene_image_prompt(scene: dict[str, Any], idea: str, preset: dict[str, Any], character_profile: dict[str, Any] | None = None, consistency_strength: str = "high") -> str:
    prompt = str(scene.get("visual_prompt") or "").strip()
    lighting = str(scene.get("lighting") or "natural cinematic lighting").strip()
    camera = str(scene.get("camera_direction") or "vertical creator shot").strip()
    if not prompt:
        prompt = f"short-form scene about {idea}"
    style_suffix = ""
    if preset.get("preset_id") == "cute_character":
        style_suffix = f", {preset.get('image_style', 'cute 3D cartoon, colorful, expressive face')}"
    elif preset.get("motion_style") == "product_focus":
        style_suffix = ", clean product showcase composition, clear product focus, creator review style"
    elif preset.get("motion_style") == "slow_cinematic":
        style_suffix = ", emotional cinematic realism, soft film look"
    elif preset.get("motion_style") == "cinematic_mv":
        style_suffix = ", music video cinematic frame, dramatic film look"
    base = (
        f"{prompt}, {camera}, {lighting}{style_suffix}, high quality composition, "
        "single full-screen 9:16 cinematic frame, one scene at a time, no collage, no split screen, "
        "no stacked panels, no tiled frames, not a contact sheet, not a storyboard page, not a grid montage, "
        "same character continuity, same environment continuity, same emotional lighting palette, "
        "clear subject, no watermark, no random text"
    )
    return apply_character_consistency(base, character_profile, consistency_strength)


def _apply_preset_to_scenes(package: dict[str, Any], preset: dict[str, Any]) -> None:
    sequence = PRESET_MOTION_SEQUENCES.get(str(preset.get("motion_style") or ""), MOTION_EFFECTS)
    for index, scene in enumerate(package.get("scene_sequence", []) or [], start=1):
        scene["motion_effect"] = sequence[(index - 1) % len(sequence)]
        scene["render_mode"] = "cinematic_motion"
        scene["subtitle_style"] = preset.get("subtitle_style", "")
        scene["transition"] = preset.get("transition_style") or scene.get("transition", "cinematic_cross_dissolve")
        scene["pace"] = preset.get("pace", "")
        scene["duration"] = max(1.5, min(3.0, float(scene.get("duration", 2.2) or 2.2)))
        scene["motion_quality"] = "subtle_smooth_fullscreen"
        scene.setdefault("render_provider_metadata", {})["aspect_ratio"] = preset.get("aspect_ratio", "9:16")
        if index == 1:
            scene["motion_effect"] = "emotional_push_in"
            scene["duration"] = min(scene["duration"], 2.0)
            scene["pacing_note"] = "first 2 seconds: strongest close-up hook frame, no slow opening"
        elif index == 2:
            scene["motion_effect"] = "cinematic_drift"
            scene["pacing_note"] = "emotional story turn with subtle parallax"
        else:
            scene["motion_effect"] = "slow_cinematic"
            scene["duration"] = max(scene["duration"], 2.4)
            scene["pacing_note"] = "strongest ending frame with soft cinematic push"


def _generate_scene_images(
    project_name: str,
    package: dict[str, Any],
    *,
    idea: str,
    preset: dict[str, Any],
    character_profile: dict[str, Any] | None,
    consistency_strength: str,
    image_provider: str,
    storage_workflow_type: str = "clips",
    image_settings: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    project_dir = workflow_project_root(storage_workflow_type) / safe_name(project_name or "hook_clip")
    images_dir = project_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    settings = {
        "size": "1024x1536",
        "quality": "medium",
        "cache_enabled": False,
        **(image_settings or {}),
    }
    results: list[dict[str, Any]] = []
    for index, scene in enumerate(package.get("scene_sequence", []) or [], start=1):
        scene_id = str(scene.get("scene_id") or f"scene_{index:02d}")
        prompt = _scene_image_prompt(scene, idea, preset, character_profile, consistency_strength)
        output_path = images_dir / f"{safe_name(scene_id)}.jpg"
        provider_used = image_provider or "offline"
        diagnostic = generate_image_with_diagnostics(provider_used, prompt, str(output_path), settings)
        image_path = str((diagnostic.get("data") or {}).get("path") or output_path)
        ok = bool(diagnostic.get("ok")) and Path(image_path).is_file()
        error = diagnostic.get("error", "")
        provider_used = str((diagnostic.get("data") or {}).get("provider_used") or provider_used)
        scene["image_prompt"] = prompt
        scene["source_image_path"] = str(image_path)
        scene["image_provider"] = provider_used
        scene["image_fallback_used"] = bool((diagnostic.get("data") or {}).get("fallback_used"))
        results.append(
            {
                "scene_id": scene_id,
                "ok": ok,
                "provider": provider_used,
                "provider_used": provider_used,
                "provider_requested": (diagnostic.get("data") or {}).get("provider_requested", image_provider),
                "fallback_used": bool((diagnostic.get("data") or {}).get("fallback_used")),
                "fallback_reason": (diagnostic.get("data") or {}).get("fallback_reason", ""),
                "error_type": (diagnostic.get("data") or {}).get("error_type", ""),
                "safe_error_message": (diagnostic.get("data") or {}).get("safe_error_message", ""),
                "validation": (diagnostic.get("data") or {}).get("validation", {}),
                "path": str(image_path),
                "prompt": prompt,
                "error": error,
            }
        )
    return results


def _voiceover_script(package: dict[str, Any]) -> str:
    lines = [str(scene.get("subtitle") or "").strip() for scene in package.get("scene_sequence", []) or []]
    return "\n".join(line for line in lines if line) or str(package.get("hook_text") or "")


def quick_generate_hook_clip(
    project_name: str,
    idea: str,
    *,
    source_workflow: str = "hook_clip",
    clip_mode: str = "Fast Hook",
    duration_seconds: int | None = None,
    visual_settings: dict[str, Any] | None = None,
    render_settings: dict[str, Any] | None = None,
    image_provider: str = "offline",
    image_settings: dict[str, Any] | None = None,
    voiceover_style: str = "calm narrator",
    voiceover_api_key: str = "",
    hook_audio_path: str = "",
    preset_id: str = "viral_meme",
    character_profile: dict[str, Any] | None = None,
    character_type: str = "banana",
    character_personality: str = "Funny",
    character_style: str = "Cute 3D",
    character_voice_style: str = "Cute",
    character_seed: str = "",
    consistency_strength: str = "high",
    subtitle_animation: str = "",
    subtitle_preset: str = "",
    hook_intensity: int = 75,
    meme_level: int = 70,
    chaos_level: int = 35,
    force_cache_refresh: bool = False,
    force_final_render: bool = True,
    variation: str = "default",
) -> dict[str, Any]:
    try:
        progress_stages = [
            {"stage": "analyzing_hook", "label": "Analyzing hook", "status": "pending"},
            {"stage": "generating_scenes", "label": "Generating scenes", "status": "pending"},
            {"stage": "rendering_video", "label": "Rendering video", "status": "pending"},
            {"stage": "syncing_audio", "label": "Syncing audio", "status": "pending"},
            {"stage": "exporting_package", "label": "Exporting package", "status": "pending"},
            {"stage": "completed", "label": "Completed", "status": "pending"},
        ]

        def mark_stage(stage: str, status: str = "completed") -> None:
            for item in progress_stages:
                if item.get("stage") == stage:
                    item["status"] = status
                    item["updated_at"] = datetime.now().isoformat(timespec="seconds")
                    break

        project_name = project_name or "Quick Hook Clip"
        preset = get_preset(preset_id)
        if character_profile is None and preset.get("preset_id") == "cute_character":
            character_profile = create_character_profile(
                character_type,
                personality=character_personality,
                style=character_style,
                voice_style=character_voice_style,
                seed=character_seed,
            )
        preset_duration = int(preset.get("default_duration") or 15)
        duration_seconds = max(5, min(60, int(duration_seconds or preset_duration)))
        visual = {**DEFAULT_VISUAL_SETTINGS, **preset_to_visual_settings(preset), **(visual_settings or {})}
        render = {**DEFAULT_RENDER_SETTINGS, **preset_to_render_settings(preset), **(render_settings or {})}
        render["aspect_ratio"] = str(preset.get("aspect_ratio") or render.get("aspect_ratio") or "9:16")
        render["duration"] = f"{duration_seconds}s"
        voiceover_style = VOICE_STYLE_MAP.get(str(preset.get("voice_style") or ""), voiceover_style)
        hook_analysis = analyze_opening_hook(
            idea,
            hook_style=str(preset.get("hook_style") or "Curiosity").replace("_", " ").title(),
            preset=preset,
            character_profile=character_profile,
        ).get("data", {})
        hook_analysis["hook_intensity"] = hook_intensity
        hook_analysis["meme_level"] = meme_level
        hook_analysis["chaos_level"] = chaos_level
        strongest_hook, viral_metrics = _strongest_hook_text(idea, hook_analysis, preset)
        hook_analysis["viral_metrics"] = viral_metrics
        hook_analysis["selected_hook_text"] = strongest_hook
        mark_stage("analyzing_hook")
        enriched_idea = f"{strongest_hook}\n{idea}".strip()
        content = _idea_content(enriched_idea, source_workflow, preset)
        content["selected_hook_text"] = strongest_hook
        content["viral_metrics"] = viral_metrics
        package_result = build_hook_render_package(
            project_name,
            source_workflow,
            content,
            visual_settings=visual,
            render_settings=render,
            clip_mode=clip_mode,
            duration_seconds=duration_seconds,
            export=True,
        )
        if not package_result.get("ok"):
            return package_result
        package = package_result["data"]["package"]
        package["creator_outcome_preset"] = preset
        package["subtitle_style"] = preset.get("subtitle_style", "")
        package["transition_style"] = preset.get("transition_style", "")
        package["voice_style"] = preset.get("voice_style", "")
        package["character_profile"] = character_profile or {}
        package["hook_analysis"] = hook_analysis
        package["viral_metrics"] = viral_metrics
        package["hook_text"] = strongest_hook
        package["hook_audio_path"] = hook_audio_path
        effective_subtitle_style = subtitle_preset or subtitle_animation or package.get("subtitle_style", "")
        package["subtitle_animation"] = effective_subtitle_style
        package["render_settings"] = {**package.get("render_settings", {}), **render}
        package["quick_generate"] = {
            "enabled": True,
            "idea": idea,
            "preset": preset,
            "image_provider": image_provider or "offline",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        _apply_preset_to_scenes(package, preset)
        mark_stage("generating_scenes")
        storage_workflow_type = "song" if source_workflow in {"music", "music_mv", "song"} else "clips"
        project_dir = workflow_project_root(storage_workflow_type) / safe_name(project_name or "hook_clip")
        exports_dir = project_dir / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        cache_key = cache_fingerprint(
            strongest_hook,
            preset.get("preset_id"),
            source_workflow,
            image_provider or "offline",
            effective_subtitle_style,
            variation,
            character_profile or {},
        )
        cache_status = {"ok": False, "message": "Cache skipped", "data": {"cache_key": cache_key}, "error": "cache_skipped"}
        cached_assets: dict[str, Any] = {}
        if not force_cache_refresh:
            cache_status = load_render_cache(project_name, storage_workflow_type, cache_key)
            if cache_status.get("ok"):
                cached_assets = copy_cached_assets_to_project((cache_status.get("data") or {}).get("manifest", {}), project_name, storage_workflow_type).get("data", {})
        cached_beat_timing = Path(str((cached_assets.get("files") or {}).get("beat_timing") or ""))
        if cached_beat_timing.is_file():
            beat_timing_plan = json.loads(cached_beat_timing.read_text(encoding="utf-8"))
            beat_timing_result = {"ok": True, "data": {"path": str(cached_beat_timing)}, "error": ""}
        else:
            beat_timing_plan = create_beat_timing_plan(
                audio_path=hook_audio_path,
                total_duration=duration_seconds,
                scene_count=len(package.get("scene_sequence", []) or []) or 3,
                pace=str(preset.get("pace") or "fast"),
                hook_text=str(package.get("hook_text") or strongest_hook or idea),
            )
            beat_timing_result = save_beat_timing(beat_timing_plan, exports_dir / "beat_timing.json")
        apply_beat_timing_to_package(package, beat_timing_plan)
        if preset.get("motion_style") == "bounce":
            for scene in package.get("scene_sequence", []) or []:
                scene["motion_effect"] = "bounce"
        package["beat_timing_path"] = (beat_timing_result.get("data") or {}).get("path", "")
        director_plan = build_scene_director_plan(
            package.get("scene_sequence", []),
            song_idea=idea,
            hook_text=str(package.get("hook_text") or strongest_hook or idea),
            lyrics=str(content.get("main_idea") or idea),
            mood=str(preset.get("label") or ""),
            preset_id=str(preset.get("preset_id") or ""),
            audio_duration=float(beat_timing_plan.get("duration") or duration_seconds),
        )
        apply_scene_director_to_package(package, director_plan)
        director_result = save_scene_director_plan(director_plan, exports_dir / "scene_director_plan.json")
        package["scene_director_plan_path"] = (director_result.get("data") or {}).get("path", "")
        scene_prompt_style = "Cute Character" if preset.get("preset_id") == "cute_character" else "TikTok Meme" if preset.get("preset_id") == "viral_meme" else "Emotional"
        cached_scene_prompts = Path(str((cached_assets.get("files") or {}).get("scene_prompts") or ""))
        if cached_scene_prompts.is_file():
            scene_prompt_plan = json.loads(cached_scene_prompts.read_text(encoding="utf-8"))
            scene_prompt_result = {"ok": True, "data": {"path": str(cached_scene_prompts)}, "error": ""}
        else:
            scene_prompt_plan = build_scene_prompts(
                package.get("scene_sequence", []),
                hook_text=str(package.get("hook_text") or content.get("selected_hook_text") or idea),
                style=scene_prompt_style,
                preset_id=str(preset.get("preset_id") or ""),
                mood=str(preset.get("label") or ""),
                scene_director_plan=director_plan,
            )
            scene_prompt_result = save_scene_prompts(scene_prompt_plan, exports_dir / "scene_prompts.json")
        apply_scene_prompts_to_package(package, scene_prompt_plan)
        package["scene_prompts_path"] = (scene_prompt_result.get("data") or {}).get("path", "")
        cached_images = cached_assets.get("image_results") or []
        if cached_images:
            image_results = cached_images
            for scene, item in zip(package.get("scene_sequence", []) or [], image_results):
                scene["source_image_path"] = item.get("path", "")
                scene["image_prompt"] = item.get("prompt", scene.get("image_prompt", ""))
                scene["image_provider"] = item.get("provider_used", item.get("provider", "cache"))
        else:
            image_results = _generate_scene_images(
                project_name,
                package,
                idea=idea,
                preset=preset,
                character_profile=character_profile,
                consistency_strength=consistency_strength,
                image_provider=image_provider or "offline",
                storage_workflow_type=storage_workflow_type,
                image_settings=image_settings,
            )
        package["image_results"] = image_results
        image_manifest_path = ensure_parent_dir(exports_dir / "image_generation_manifest.json")
        image_manifest = {
            "generated_by": "VelaFlow",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "project_name": project_name,
            "provider_requested": image_provider or "offline",
            "fallback_count": sum(1 for item in image_results if item.get("fallback_used")),
            "images": image_results,
            "api_keys_exported": False,
        }
        image_manifest_path.write_text(json.dumps(image_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        package["image_generation_manifest_path"] = str(image_manifest_path)
        cache_save = save_render_cache(
            project_name,
            storage_workflow_type,
            cache_key,
            scene_prompt_path=package.get("scene_prompts_path", ""),
            beat_timing_path=package.get("beat_timing_path", ""),
            scene_director_plan_path=package.get("scene_director_plan_path", ""),
            image_manifest_path=package.get("image_generation_manifest_path", ""),
            image_results=image_results,
        )
        voice_script = _voiceover_script(package)
        package["voiceover_script"] = voice_script
        voice_result = generate_voiceover_audio(
            project_name,
            voice_script,
            style=voiceover_style,
            api_key=voiceover_api_key or "",
            provider="openai",
            output_name="voiceover.mp3",
        )
        voiceover_path = str((voice_result.get("data") or {}).get("audio_path") or "")
        render_result = render_real_hook_clip(project_name, package, workflow_type="hook", voiceover_path=voiceover_path, background_audio_path=hook_audio_path, storage_workflow_type=storage_workflow_type, force=force_final_render)
        mark_stage("rendering_video", "completed" if render_result.get("ok") else "failed")
        render_stage = (render_result.get("data") or {}).get("render_stage", {}) or {}
        mark_stage("syncing_audio", "completed" if render_stage.get("audio_attach_ok", True) or (render_result.get("data") or {}).get("audio_sync_status") else "failed")
        export_result = export_hook_clip_package(project_name, package)
        character_save = save_character_profile(project_name, character_profile, "clips") if character_profile else {"ok": False, "data": {}, "error": "no_character_profile"}
        hook_save = save_hook_analysis(project_name, hook_analysis, exports_dir)
        package["hook_analysis_path"] = (hook_save.get("data") or {}).get("path", "")
        subtitle_result = generate_styled_subtitles(
            package.get("subtitle_timing", []),
            exports_dir,
            preset_id=str(preset.get("preset_id") or ""),
            subtitle_style=effective_subtitle_style or str(preset.get("subtitle_style") or ""),
        )
        styled_subtitle_path = (subtitle_result.get("data") or {}).get("ass", "")
        package["styled_subtitles_path"] = styled_subtitle_path
        cinematic_quality_report = build_cinematic_quality_report(
            scene_prompt_plan=scene_prompt_plan,
            scene_director_plan=director_plan,
            render_stage=render_stage,
            subtitle_result=subtitle_result,
        )
        cinematic_quality_result = save_cinematic_quality_report(cinematic_quality_report, exports_dir / "cinematic_quality_report.json")
        package["cinematic_quality_report_path"] = (cinematic_quality_result.get("data") or {}).get("path", "")
        thumbnail_result = export_thumbnail(package, image_results, exports_dir / "thumbnail.jpg")
        package["thumbnail_path"] = (thumbnail_result.get("data") or {}).get("path", "")
        package["thumbnail_score_path"] = (thumbnail_result.get("data") or {}).get("score_path", "")
        viral_timing_plan = create_viral_timing_plan(package, target_duration=duration_seconds, preset_id=str(preset.get("preset_id") or ""))
        viral_timing_plan["timing_profile"] = beat_timing_plan.get("timing_profile", "")
        viral_timing_plan["emotional_curve"] = beat_timing_plan.get("emotional_curve", [])
        viral_timing_plan["hook_peak_moment"] = beat_timing_plan.get("hook_peak_moment", 0)
        viral_timing_plan["hook_score"] = viral_metrics.get("hook_score", 0)
        viral_timing_plan["viral_pacing"] = viral_metrics.get("viral_pacing", 0)
        viral_timing_plan["thumbnail_quality"] = (thumbnail_result.get("data") or {}).get("score", 0)
        timing_result = save_viral_timing_plan(viral_timing_plan, exports_dir / "viral_timing_plan.json")
        package["viral_timing_plan"] = viral_timing_plan
        render_data_for_export = {
            **(render_result.get("data", {}) or {}),
            "styled_subtitles": styled_subtitle_path,
            "thumbnail": package.get("thumbnail_path", ""),
            "thumbnail_score": package.get("thumbnail_score_path", ""),
            "scene_prompts": package.get("scene_prompts_path", ""),
            "beat_timing": package.get("beat_timing_path", ""),
            "scene_director_plan": package.get("scene_director_plan_path", ""),
            "cinematic_quality_report": package.get("cinematic_quality_report_path", ""),
            "image_generation_manifest": package.get("image_generation_manifest_path", ""),
            "hook_analysis": package.get("hook_analysis_path", ""),
        }
        tiktok_package = export_tiktok_package(project_name, package, render_data_for_export)
        mark_stage("exporting_package", "completed" if tiktok_package.get("ok") else "failed")
        clip_version = save_clip_version(
            project_name,
            storage_workflow_type,
            final_mp4=(render_result.get("data") or {}).get("final_mp4", ""),
            package=package,
            render_data=render_result.get("data", {}),
            tiktok_package=tiktok_package.get("data", {}),
            variation=variation,
        )
        manifest = {
            "generated_by": "VelaFlow",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "project_name": project_name,
            "idea": idea,
            "source_workflow": source_workflow,
            "clip_mode": clip_mode,
            "preset": preset,
            "image_provider": image_provider or "offline",
            "image_results": image_results,
            "image_generation_manifest": image_manifest,
            "image_generation_manifest_path": package.get("image_generation_manifest_path", ""),
            "character_profile": character_profile or {},
            "character_profile_path": (character_save.get("data") or {}).get("path", ""),
            "hook_analysis": hook_analysis,
            "hook_analysis_path": (hook_save.get("data") or {}).get("path", ""),
            "styled_subtitles": subtitle_result,
            "thumbnail": thumbnail_result,
            "scene_prompts": scene_prompt_plan,
            "scene_prompts_path": package.get("scene_prompts_path", ""),
            "beat_timing": beat_timing_plan,
            "beat_timing_path": package.get("beat_timing_path", ""),
            "scene_director_plan": director_plan,
            "scene_director_plan_path": package.get("scene_director_plan_path", ""),
            "cinematic_quality_report": cinematic_quality_report,
            "cinematic_quality_report_path": package.get("cinematic_quality_report_path", ""),
            "viral_timing_plan": viral_timing_plan,
            "viral_metrics": viral_metrics,
            "viral_timing_plan_path": (timing_result.get("data") or {}).get("path", ""),
            "tiktok_package": tiktok_package,
            "clip_version": clip_version,
            "render_cache": {"cache_key": cache_key, "cache_status": cache_status, "cache_save": cache_save},
            "progress_stages": progress_stages,
            "voiceover": voice_result,
            "hook_audio_path": hook_audio_path,
            "render": render_result,
            "hook_package_export": export_result,
            "final_mp4": (render_result.get("data") or {}).get("final_mp4", ""),
        }
        quick_manifest_path = ensure_parent_dir(exports_dir / "quick_hook_clip_manifest.json")
        render_manifest_path = ensure_parent_dir(exports_dir / "render_manifest.json")
        scene_manifest_path = ensure_parent_dir(exports_dir / "scene_manifest.json")
        quick_manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        render_manifest_payload = dict((render_result.get("data") or {}).get("manifest", manifest))
        render_manifest_payload["image_results"] = image_results
        render_manifest_payload["image_generation_manifest_path"] = package.get("image_generation_manifest_path", "")
        render_manifest_payload["render_stage_path"] = (render_result.get("data") or {}).get("render_stage_path", "")
        render_manifest_payload["progress_stages"] = progress_stages
        render_manifest_path.write_text(json.dumps(render_manifest_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        scene_manifest_path.write_text(
            json.dumps(
                {
                    "generated_by": "VelaFlow",
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                    "project_name": project_name,
                    "preset": preset,
                    "character_profile": character_profile or {},
                    "hook_analysis": hook_analysis,
                    "scene_director_plan": director_plan,
                    "scene_director_plan_path": package.get("scene_director_plan_path", ""),
                    "cinematic_quality_report": cinematic_quality_report,
                    "cinematic_quality_report_path": package.get("cinematic_quality_report_path", ""),
                    "scenes": package.get("scene_sequence", []),
                    "image_results": image_results,
                    "image_generation_manifest_path": package.get("image_generation_manifest_path", ""),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        package["quick_generate"]["manifest_path"] = str(quick_manifest_path)
        mark_stage("completed", "completed" if render_result.get("ok") else "failed")
        return {
            "ok": bool(render_result.get("ok")),
            "message": "Quick hook clip generated" if render_result.get("ok") else "Quick hook package generated, but MP4 render needs attention",
            "data": {
                "package": package,
                "package_export": export_result.get("data", {}),
                "image_results": image_results,
                "image_generation_manifest_path": package.get("image_generation_manifest_path", ""),
                "character_profile": character_profile or {},
                "character_profile_path": (character_save.get("data") or {}).get("path", ""),
                "hook_analysis": hook_analysis,
                "hook_analysis_path": (hook_save.get("data") or {}).get("path", ""),
                "styled_subtitles": subtitle_result.get("data", {}),
                "thumbnail": thumbnail_result.get("data", {}),
                "thumbnail_path": package.get("thumbnail_path", ""),
                "thumbnail_score_path": package.get("thumbnail_score_path", ""),
                "scene_prompts": scene_prompt_plan,
                "scene_prompts_path": package.get("scene_prompts_path", ""),
                "scene_director_plan": director_plan,
                "scene_director_plan_path": package.get("scene_director_plan_path", ""),
                "cinematic_quality_report": cinematic_quality_report,
                "cinematic_quality_report_path": package.get("cinematic_quality_report_path", ""),
                "beat_timing": beat_timing_plan,
                "beat_timing_path": package.get("beat_timing_path", ""),
                "viral_timing_plan": viral_timing_plan,
                "viral_metrics": viral_metrics,
                "progress_stages": progress_stages,
                "viral_timing_plan_path": (timing_result.get("data") or {}).get("path", ""),
                "tiktok_package": tiktok_package.get("data", {}),
                "clip_version": clip_version.get("data", {}),
                "render_cache": {"cache_key": cache_key, "cache_hit": bool(cache_status.get("ok")), "cache_status": cache_status.get("message", ""), "cache_dir": (cache_save.get("data") or {}).get("cache_dir", "")},
                "voiceover": voice_result.get("data", {}),
                "hook_audio_path": hook_audio_path,
                "render": render_result.get("data", {}),
                "manifest_path": str(quick_manifest_path),
                "render_manifest_path": str(render_manifest_path),
                "render_stage_path": (render_result.get("data") or {}).get("render_stage_path", ""),
                "scene_manifest_path": str(scene_manifest_path),
                "final_mp4": (render_result.get("data") or {}).get("final_mp4", ""),
            },
            "error": "" if render_result.get("ok") else render_result.get("error", ""),
        }
    except Exception as exc:
        return {"ok": False, "message": "Quick hook clip generation failed", "data": {}, "error": str(exc)}
