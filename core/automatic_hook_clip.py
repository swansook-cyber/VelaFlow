from __future__ import annotations

import json
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image

from core.character_engine import apply_character_consistency, create_character_profile, save_character_profile
from core.beat_timing_engine import apply_beat_timing_to_package, create_beat_timing_plan, save_beat_timing
from core.hook_clip_engine import build_hook_render_package, export_hook_clip_package
from core.hook_intelligence import analyze_opening_hook, save_hook_analysis
from core.paths import workflow_project_root
from core.preset_engine import get_preset, preset_to_render_settings, preset_to_visual_settings
from core.project_io import safe_name
from core.real_clip_pipeline import combine_scene_clips_to_mp4, ensure_parent_dir, render_real_hook_clip, validate_mp4, write_subtitles
from core.render_cache import CACHE_VERSION as RENDER_CACHE_VERSION, cache_fingerprint, copy_cached_assets_to_project, load_render_cache, save_render_cache
from core.scene_prompt_engine import apply_scene_director_to_package, apply_scene_prompts_to_package, build_cinematic_quality_report, build_scene_director_plan, build_scene_prompts, save_cinematic_quality_report, save_scene_director_plan, save_scene_prompts
from core.subtitle_engine import generate_styled_subtitles
from core.thumbnail_selector import export_thumbnail
from core.versioning import save_clip_version
from core.viral_timing_engine import create_viral_timing_plan, save_viral_timing_plan
from core.voiceover_engine import generate_voiceover_audio
from providers.image_ai import generate_image, generate_image_with_diagnostics, validate_image_file
from providers.video_ai import build_hook_video_shot_prompts, generate_video_shot, save_video_generation_manifest


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

CINEMATIC_SHOT_VARIATIONS = [
    {
        "shot_type": "wide negative-space composition",
        "framing_variation": "wide shot with the character small in frame, empty room space carrying the emotion",
        "camera_distance_variation": "wide shot",
        "emotional_angle_variation": "lonely atmosphere before the lyric lands",
        "lighting_evolution": "soft natural intro light with gentle shadows",
        "pose_evolution": "still body language, slight head tilt toward window light",
        "motion_variation": "slow breathing push-in",
    },
    {
        "shot_type": "medium profile / over-shoulder shot",
        "framing_variation": "medium emotional side profile, shoulder and phone/reflection visible, same room",
        "camera_distance_variation": "medium shot",
        "emotional_angle_variation": "private memory moment, stronger isolation",
        "lighting_evolution": "mood isolation with practical room light and deeper side shadow",
        "pose_evolution": "subtle head turn or hand tightening around phone",
        "motion_variation": "subtle handheld drift",
    },
    {
        "shot_type": "close-up eyes / emotional push-in",
        "framing_variation": "close-up eyes near upper third, face fills frame without covering subtitle area",
        "camera_distance_variation": "close-up",
        "emotional_angle_variation": "strongest hook lyric, eye contact and emotional impact",
        "lighting_evolution": "stronger contrast, catchlight in eyes, emotional shadow depth",
        "pose_evolution": "small breath, almost crying but controlled",
        "motion_variation": "emotional push-in",
    },
    {
        "shot_type": "reflection release shot",
        "framing_variation": "medium close-up reflection or silhouette, same clothes and room palette",
        "camera_distance_variation": "medium close-up",
        "emotional_angle_variation": "soft release after the hook peak",
        "lighting_evolution": "softer release light, quiet ending falloff",
        "pose_evolution": "turning away slowly or lowering gaze",
        "motion_variation": "slow pull out",
    },
]

CINEMATIC_CAMERA_STYLES = [
    "wide isolation framing",
    "cinematic drift",
    "slow push-in",
    "handheld emotional sway",
    "parallax depth",
    "rack focus simulation",
    "emotional close-up",
    "slow orbit",
]

CINEMATIC_TRANSITIONS = [
    "cinematic fade",
    "emotional dissolve",
    "soft blur transition",
    "beat cut",
    "light flash",
    "directional motion blend",
]

HARD_IMAGE_NEGATIVE_PROMPT = (
    "storyboard, comic, manga, split screen, contact sheet, tiled frames, cinematic strip, multi-panel layout, "
    "duplicated frame, repeated composition, grid, gallery, UI overlay, subtitles, numbers, watermarks, icons, logos, "
    "text, labels, debug overlay, frame counters, shot sheet, film strip, collage, storyboard page, random symbols, "
    "meme typography, reaction faces, cartoon eyes, anime proportions, sticker aesthetics, thumbnail composition, "
    "exaggerated facial expressions, emoji, social media overlay, score text, rating text"
)

SINGLE_FRAME_POSITIVE_RULE = (
    "single cinematic fullscreen frame, one continuous real-world camera shot, NOT a storyboard or multi-panel composition"
)

VISUAL_MODE = "cinematic_live_action_realism_v3"
CLEAN_RENDER_PIPELINE_VERSION = "cinematic_clean_v3"
VISUAL_MODE_PREFIX = (
    "Ultra realistic cinematic live-action film still. Real human anatomy. Natural skin texture. "
    "Professional movie lighting. No meme. No cartoon. No anime. No exaggerated eyes. No reaction face. "
    "No thumbnail design. No social media overlay. No subtitles. No text. No emoji. No symbols. "
    "No UI. No score. No debug text. No watermark."
)


def _lock_cinematic_visual_prompt(text: str) -> str:
    replacements = {
        "hook": "emotional lyric moment",
        "viral": "cinematic",
        "thumbnail": "film still",
        "meme": "grounded emotional realism",
        "tiktok text": "vertical cinematic framing",
        "reaction": "subtle grounded acting",
        "emoji": "natural expression",
        "score": "emotional intensity",
        "rating": "emotional intensity",
        "caption": "bottom-safe composition",
        "subtitle": "bottom-safe composition",
        "67/100": "emotional intensity",
    }
    value = str(text or "")
    lowered = value.lower()
    for forbidden, replacement in replacements.items():
        if forbidden in lowered:
            value = value.replace(forbidden, replacement).replace(forbidden.title(), replacement)
            lowered = value.lower()
    if VISUAL_MODE_PREFIX.lower() not in value.lower():
        value = f"{VISUAL_MODE_PREFIX} {value}"
    return value


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
        for source_key, filename in [
            ("timeline_director", "timeline_director.json"),
            ("scene_motion_map", "scene_motion_map.json"),
            ("emotional_curve", "emotional_curve.json"),
            ("shot_progression", "shot_progression.json"),
        ]:
            source_path = Path(str(render_data.get(source_key) or package.get(f"{source_key}_path") or ""))
            if source_path.is_file():
                shutil.copy2(source_path, ensure_parent_dir(final_dir / filename))
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
        render_pipeline_report = Path(str(render_data.get("render_pipeline_report_path") or package.get("render_pipeline_report_path") or ""))
        if render_pipeline_report.is_file():
            debug_dir = final_dir / "debug"
            debug_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(render_pipeline_report, ensure_parent_dir(debug_dir / "render_pipeline_report.json"))
        image_manifest = Path(str(render_data.get("image_generation_manifest") or package.get("image_generation_manifest_path") or ""))
        if image_manifest.is_file():
            shutil.copy2(image_manifest, ensure_parent_dir(final_dir / "image_generation_manifest.json"))
        scene_generation_report = Path(str(render_data.get("scene_generation_report") or package.get("scene_generation_report_path") or ""))
        if scene_generation_report.is_file():
            debug_dir = final_dir / "debug"
            debug_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(scene_generation_report, ensure_parent_dir(debug_dir / "scene_generation_report.json"))
        image_validation_report = Path(str(render_data.get("image_validation_report") or package.get("image_validation_report_path") or ""))
        if image_validation_report.is_file():
            debug_dir = final_dir / "debug"
            debug_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(image_validation_report, ensure_parent_dir(debug_dir / "image_validation_report.json"))
        shot_variation_report = Path(str(render_data.get("shot_variation_report") or package.get("shot_variation_report_path") or ""))
        if shot_variation_report.is_file():
            debug_dir = final_dir / "debug"
            debug_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(shot_variation_report, ensure_parent_dir(debug_dir / "shot_variation_report.json"))
        render_cleanup_report = Path(str(render_data.get("render_cleanup_report") or package.get("render_cleanup_report_path") or ""))
        if render_cleanup_report.is_file():
            debug_dir = final_dir / "debug"
            debug_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(render_cleanup_report, ensure_parent_dir(debug_dir / "render_cleanup_report.json"))
        video_generation_manifest = Path(str(render_data.get("video_generation_manifest") or package.get("video_generation_manifest_path") or ""))
        if video_generation_manifest.is_file():
            shutil.copy2(video_generation_manifest, ensure_parent_dir(final_dir / "video_generation_manifest.json"))
        provider_debug = Path(str(render_data.get("provider_debug") or package.get("provider_debug_path") or ""))
        if provider_debug.is_file():
            debug_dir = final_dir / "debug"
            debug_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(provider_debug, ensure_parent_dir(debug_dir / "provider_debug.json"))
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
        thumbnail_prompt = (
            str(package.get("thumbnail_prompt") or "").strip()
            or f"Raw cinematic cover frame for {title}: single fullscreen live-action film still, no text, no graphics, no overlay"
        )
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
            "timeline_director": str(final_dir / "timeline_director.json") if (final_dir / "timeline_director.json").is_file() else "",
            "scene_motion_map": str(final_dir / "scene_motion_map.json") if (final_dir / "scene_motion_map.json").is_file() else "",
            "emotional_curve": str(final_dir / "emotional_curve.json") if (final_dir / "emotional_curve.json").is_file() else "",
            "shot_progression": str(final_dir / "shot_progression.json") if (final_dir / "shot_progression.json").is_file() else "",
            "scene_director_plan": str(final_dir / "scene_director_plan.json") if (final_dir / "scene_director_plan.json").is_file() else "",
            "cinematic_quality_report": str(final_dir / "cinematic_quality_report.json") if (final_dir / "cinematic_quality_report.json").is_file() else "",
            "render_manifest": str(final_dir / "render_manifest.json") if (final_dir / "render_manifest.json").is_file() else "",
            "render_stage": str(final_dir / "render_stage.json") if (final_dir / "render_stage.json").is_file() else "",
            "render_pipeline_report": str(final_dir / "debug" / "render_pipeline_report.json") if (final_dir / "debug" / "render_pipeline_report.json").is_file() else "",
            "image_generation_manifest": str(final_dir / "image_generation_manifest.json") if (final_dir / "image_generation_manifest.json").is_file() else "",
            "video_generation_manifest": str(final_dir / "video_generation_manifest.json") if (final_dir / "video_generation_manifest.json").is_file() else "",
            "provider_debug": str(final_dir / "debug" / "provider_debug.json") if (final_dir / "debug" / "provider_debug.json").is_file() else "",
            "scene_generation_report": str(final_dir / "debug" / "scene_generation_report.json") if (final_dir / "debug" / "scene_generation_report.json").is_file() else "",
            "image_validation_report": str(final_dir / "debug" / "image_validation_report.json") if (final_dir / "debug" / "image_validation_report.json").is_file() else "",
            "shot_variation_report": str(final_dir / "debug" / "shot_variation_report.json") if (final_dir / "debug" / "shot_variation_report.json").is_file() else "",
            "render_cleanup_report": str(final_dir / "debug" / "render_cleanup_report.json") if (final_dir / "debug" / "render_cleanup_report.json").is_file() else "",
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
    shot_variation = scene.get("shot_variation") or {}
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
        f"{prompt}, {camera}, {lighting}{style_suffix}, {SINGLE_FRAME_POSITIVE_RULE}, high quality composition, "
        "cinematic photography, realistic lens, subtle film grain, depth of field, natural facial proportions, "
        "realistic lighting, emotionally grounded acting, Netflix A24 cinematic music video frame, "
        f"shot variation: {shot_variation.get('framing_variation', scene.get('shot_type', 'cinematic shot'))}, "
        f"camera distance: {shot_variation.get('camera_distance_variation', scene.get('camera_distance', 'cinematic'))}, "
        f"emotional angle: {shot_variation.get('emotional_angle_variation', scene.get('emotional_intent', 'emotional'))}, "
        f"lighting evolution: {shot_variation.get('lighting_evolution', scene.get('lighting_direction', lighting))}, "
        f"subtle pose evolution: {shot_variation.get('pose_evolution', scene.get('subject_action', 'natural emotional pose'))}, "
        "single full-screen 9:16 cinematic frame, one scene at a time, no collage, no split screen, "
        "no stacked panels, no tiled frames, not a contact sheet, not a storyboard page, not a grid montage, "
        "same character continuity, same environment continuity, same emotional lighting palette, "
        "unique framing compared with every other scene, no copy-paste composition, clear subject, no watermark, no random text, "
        f"hard negative visual rules: NO {HARD_IMAGE_NEGATIVE_PROMPT}"
    )
    return _lock_cinematic_visual_prompt(apply_character_consistency(base, character_profile, consistency_strength))


def _apply_cinematic_shot_variations(package: dict[str, Any], director_plan: dict[str, Any]) -> dict[str, Any]:
    director_scenes = director_plan.get("scenes") or []
    scenes = package.get("scene_sequence") or []
    for index, scene in enumerate(scenes, start=1):
        variation = CINEMATIC_SHOT_VARIATIONS[min(index - 1, len(CINEMATIC_SHOT_VARIATIONS) - 1)]
        scene["shot_variation"] = variation
        scene["shot_type"] = variation["shot_type"] if scene.get("hook_peak_scene") else scene.get("shot_type") or variation["shot_type"]
        scene["framing_variation"] = variation["framing_variation"]
        scene["camera_distance_variation"] = variation["camera_distance_variation"]
        scene["emotional_angle_variation"] = variation["emotional_angle_variation"]
        scene["lighting_evolution"] = variation["lighting_evolution"]
        scene["pose_evolution"] = variation["pose_evolution"]
        if variation["motion_variation"] == "emotional push-in":
            scene["motion_effect"] = "hook_energy_zoom" if scene.get("hook_peak_scene") else "emotional_push_in"
        elif variation["motion_variation"] == "subtle handheld drift":
            scene["motion_effect"] = "cinematic_drift"
        elif variation["motion_variation"] == "slow pull out":
            scene["motion_effect"] = "slow_cinematic"
    for index, directed in enumerate(director_scenes, start=1):
        variation = CINEMATIC_SHOT_VARIATIONS[min(index - 1, len(CINEMATIC_SHOT_VARIATIONS) - 1)]
        directed["shot_variation"] = variation
        directed["framing_variation"] = variation["framing_variation"]
        directed["camera_distance_variation"] = variation["camera_distance_variation"]
        directed["emotional_angle_variation"] = variation["emotional_angle_variation"]
        directed["lighting_evolution"] = variation["lighting_evolution"]
        directed["pose_evolution"] = variation["pose_evolution"]
        directed["motion_variation"] = variation["motion_variation"]
    director_plan["shot_variation_engine"] = "cinematic_shot_variation_engine_v1"
    director_plan["shot_types_used"] = [scene.get("shot_variation", {}).get("shot_type", scene.get("shot_type", "")) for scene in scenes]
    return package


def _divider_strength(values: list[int]) -> float:
    if len(values) < 8:
        return 0.0
    avg = sum(values) / len(values)
    variance = sum((value - avg) ** 2 for value in values) / len(values)
    stddev = variance ** 0.5
    contrast = min(1.0, abs(avg - 128) / 128)
    uniformity = max(0.0, 1.0 - (stddev / 64.0))
    return round(contrast * uniformity, 3)


def _detect_multi_frame_scene_image(path: str | Path) -> dict[str, Any]:
    image_path = Path(path)
    validation = validate_image_file(image_path, expected_aspect_ratio="9:16")
    result = {
        "path": str(image_path),
        "validation": validation,
        "multiple_frames_detected": False,
        "panel_layout_detected": False,
        "ocr_text_detected": False,
        "text_overlay_score": 0.0,
        "numeric_overlay_score": 0.0,
        "emoji_detected_score": 0.0,
        "cartoon_score": 0.0,
        "thumbnail_layout_score": 0.0,
        "anime_score": 0.0,
        "reaction_face_score": 0.0,
        "duplicate_region_score": 0.0,
        "storyboard_score": 0.0,
        "collage_detection_score": 0.0,
        "fullscreen_validation": {
            "exists": bool(validation.get("file_exists")),
            "vertical_9x16": bool(validation.get("ok")) and abs(float(validation.get("aspect_ratio") or 0) - (9 / 16)) <= 0.09,
            "single_composition": True,
        },
        "error": "",
    }
    if not validation.get("ok"):
        result["error"] = validation.get("error", "image_validation_failed")
        result["fullscreen_validation"]["single_composition"] = False
        result["collage_detection_score"] = 1.0
        result["multiple_frames_detected"] = True
        return result
    try:
        with Image.open(image_path) as image:
            gray = image.convert("L").resize((90, 160))
            width, height = gray.size
            pixels = gray.load()
            vertical_scores = []
            for x in [width // 3, width // 2, (width * 2) // 3]:
                values = [pixels[x, y] for y in range(height)]
                vertical_scores.append(_divider_strength(values))
            horizontal_scores = []
            for y in [height // 3, height // 2, (height * 2) // 3]:
                values = [pixels[x, y] for x in range(width)]
                horizontal_scores.append(_divider_strength(values))
            strong_vertical = sum(1 for score in vertical_scores if score >= 0.86)
            strong_horizontal = sum(1 for score in horizontal_scores if score >= 0.86)
            thirds = [
                gray.crop((0, 0, width, height // 3)),
                gray.crop((0, height // 3, width, (height * 2) // 3)),
                gray.crop((0, (height * 2) // 3, width, height)),
            ]
            region_hashes = []
            for region in thirds:
                mini = region.resize((8, 8))
                values = list(mini.getdata())
                avg = sum(values) / max(1, len(values))
                region_hashes.append("".join("1" if value >= avg else "0" for value in values))
            duplicate_region_score = max(
                [_hash_similarity(region_hashes[left], region_hashes[right]) for left in range(len(region_hashes)) for right in range(left + 1, len(region_hashes))]
                or [0.0]
            )
            result["duplicate_region_score"] = duplicate_region_score
            # Text/UI overlays usually create dense high-contrast detail in the bottom or top safe bands.
            edge_band = gray.crop((0, int(height * 0.74), width, int(height * 0.94)))
            band_values = list(edge_band.resize((90, 24)).getdata())
            band_avg = sum(band_values) / max(1, len(band_values))
            high_contrast = sum(1 for value in band_values if abs(value - band_avg) > 58) / max(1, len(band_values))
            result["text_overlay_score"] = round(min(1.0, high_contrast * 2.2), 3)
            result["numeric_overlay_score"] = round(min(1.0, result["text_overlay_score"] * 0.9), 3)
            result["ocr_text_detected"] = bool(result["text_overlay_score"] >= 0.92 or result["numeric_overlay_score"] >= 0.92)
            saturation_samples = []
            rgb = image.convert("RGB").resize((48, 84))
            for red, green, blue in list(rgb.getdata()):
                max_channel = max(red, green, blue)
                min_channel = min(red, green, blue)
                saturation_samples.append((max_channel - min_channel) / max(1, max_channel))
            avg_saturation = sum(saturation_samples) / max(1, len(saturation_samples))
            bright_saturation = sum(1 for value in saturation_samples if value > 0.55) / max(1, len(saturation_samples))
            result["cartoon_score"] = round(min(1.0, max(0.0, (avg_saturation - 0.42) * 2.2 + bright_saturation * 0.4)), 3)
            result["anime_score"] = round(min(1.0, max(0.0, result["cartoon_score"] * 0.8 + (result["text_overlay_score"] * 0.2))), 3)
            result["emoji_detected_score"] = round(min(1.0, max(0.0, bright_saturation * 1.8 if result["text_overlay_score"] > 0.45 else 0.0)), 3)
            result["reaction_face_score"] = round(min(1.0, max(0.0, result["cartoon_score"] * 0.65 if duplicate_region_score > 0.97 else result["cartoon_score"] * 0.35)), 3)
            # Contact sheets usually have multiple clean divider lines. Single-image scenes can contain
            # high-contrast text, windows, or borders, so require repeated panel-like separators.
            if strong_vertical >= 2 and strong_horizontal >= 1:
                score = round(max(vertical_scores + horizontal_scores), 3)
            elif strong_horizontal >= 2:
                score = round(max(horizontal_scores), 3)
            else:
                score = 0.0
            result["thumbnail_layout_score"] = round(min(1.0, max(score, result["text_overlay_score"] * 0.85)), 3)
            storyboard_score = max(score, duplicate_region_score if duplicate_region_score >= 0.985 and (strong_horizontal or strong_vertical) else 0.0)
            result["storyboard_score"] = round(storyboard_score, 3)
            result["collage_detection_score"] = score
            result["panel_layout_detected"] = score >= 0.82
            drift_detected = (
                result["text_overlay_score"] >= 0.92
                or result["numeric_overlay_score"] >= 0.92
                or result["emoji_detected_score"] >= 0.92
                or result["cartoon_score"] >= 0.94
                or result["thumbnail_layout_score"] >= 0.94
                or result["anime_score"] >= 0.94
                or result["reaction_face_score"] >= 0.94
            )
            result["multiple_frames_detected"] = bool(score >= 0.82 or storyboard_score >= 0.99 or drift_detected)
            result["fullscreen_validation"]["single_composition"] = not result["multiple_frames_detected"]
            result["error"] = "possible_contact_sheet_or_panel_grid" if result["multiple_frames_detected"] else ""
    except Exception as exc:
        result["error"] = f"scene_image_scan_failed: {type(exc).__name__}"
        result["collage_detection_score"] = 1.0
        result["multiple_frames_detected"] = True
        result["fullscreen_validation"]["single_composition"] = False
    return result


def _image_average_hash(path: str | Path, *, size: int = 8) -> str:
    try:
        with Image.open(path) as image:
            gray = image.convert("L").resize((size, size))
            pixels = list(gray.getdata())
    except Exception:
        return ""
    avg = sum(pixels) / max(1, len(pixels))
    return "".join("1" if pixel >= avg else "0" for pixel in pixels)


def _hash_similarity(hash_a: str, hash_b: str) -> float:
    if not hash_a or not hash_b or len(hash_a) != len(hash_b):
        return 0.0
    matches = sum(1 for left, right in zip(hash_a, hash_b) if left == right)
    return round(matches / len(hash_a), 4)


def _write_scene_generation_report(project_name: str, image_results: list[dict[str, Any]], output_path: str | Path) -> dict[str, Any]:
    validations = []
    for item in image_results or []:
        scan = _detect_multi_frame_scene_image(item.get("path", ""))
        validations.append(
            {
                "scene_id": item.get("scene_id", ""),
                "path": item.get("path", ""),
                "provider_used": item.get("provider_used", item.get("provider", "")),
                "dimensions": {
                    "width": (scan.get("validation") or {}).get("width", 0),
                    "height": (scan.get("validation") or {}).get("height", 0),
                    "aspect_ratio": (scan.get("validation") or {}).get("aspect_ratio", 0),
                },
                "fullscreen_validation": scan.get("fullscreen_validation", {}),
                "multiple_frame_detection": {
                    "multiple_frames_detected": scan.get("multiple_frames_detected", False),
                    "panel_layout_detected": scan.get("panel_layout_detected", False),
                    "error": scan.get("error", ""),
                },
                "duplicate_region_score": scan.get("duplicate_region_score", 0.0),
                "storyboard_score": scan.get("storyboard_score", 0.0),
                "ocr_text_detected": scan.get("ocr_text_detected", False),
                "text_overlay_score": scan.get("text_overlay_score", 0.0),
                "numeric_overlay_score": scan.get("numeric_overlay_score", 0.0),
                "emoji_detected_score": scan.get("emoji_detected_score", 0.0),
                "cartoon_score": scan.get("cartoon_score", 0.0),
                "thumbnail_layout_score": scan.get("thumbnail_layout_score", 0.0),
                "anime_score": scan.get("anime_score", 0.0),
                "reaction_face_score": scan.get("reaction_face_score", 0.0),
                "collage_detection_score": scan.get("collage_detection_score", 0.0),
                "regeneration_attempts": item.get("regeneration_attempts", 0),
            }
        )
    forbidden = [item for item in validations if (item.get("multiple_frame_detection") or {}).get("multiple_frames_detected")]
    report = {
        "generated_by": "VelaFlow",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "project_name": project_name,
        "scene_generation_architecture": "independent_fullscreen_scene_images",
        "scene_count": len(image_results or []),
        "per_scene_dimensions": [item.get("dimensions", {}) for item in validations],
        "fullscreen_validation": {
            "one_image_per_scene": len(image_results or []) == len({item.get("scene_id") for item in image_results or []}),
            "all_vertical_9x16": all((item.get("fullscreen_validation") or {}).get("vertical_9x16") for item in validations),
            "all_single_composition": all((item.get("fullscreen_validation") or {}).get("single_composition") for item in validations),
            "no_contact_sheet_assets": not forbidden,
        },
        "multiple_frame_detection": [item.get("multiple_frame_detection", {}) for item in validations],
        "duplicate_region_score": max([float(item.get("duplicate_region_score") or 0) for item in validations] or [0.0]),
        "storyboard_score": max([float(item.get("storyboard_score") or 0) for item in validations] or [0.0]),
        "text_overlay_score": max([float(item.get("text_overlay_score") or 0) for item in validations] or [0.0]),
        "numeric_overlay_score": max([float(item.get("numeric_overlay_score") or 0) for item in validations] or [0.0]),
        "ocr_text_detected": any(bool(item.get("ocr_text_detected")) for item in validations),
        "emoji_detected_score": max([float(item.get("emoji_detected_score") or 0) for item in validations] or [0.0]),
        "cartoon_score": max([float(item.get("cartoon_score") or 0) for item in validations] or [0.0]),
        "thumbnail_layout_score": max([float(item.get("thumbnail_layout_score") or 0) for item in validations] or [0.0]),
        "anime_score": max([float(item.get("anime_score") or 0) for item in validations] or [0.0]),
        "reaction_face_score": max([float(item.get("reaction_face_score") or 0) for item in validations] or [0.0]),
        "collage_detection_score": max([float(item.get("collage_detection_score") or 0) for item in validations] or [0.0]),
        "panel_layout_detected": any((item.get("multiple_frame_detection") or {}).get("panel_layout_detected") for item in validations),
        "regeneration_attempts": sum(int(item.get("regeneration_attempts") or 0) for item in validations),
        "forbidden_scene_image_layout_found": bool(forbidden),
        "text_or_overlay_found": any(bool(item.get("ocr_text_detected")) for item in validations)
        or max([float(item.get("text_overlay_score") or 0) for item in validations] or [0.0]) >= 0.92
        or max([float(item.get("numeric_overlay_score") or 0) for item in validations] or [0.0]) >= 0.92
        or max([float(item.get("emoji_detected_score") or 0) for item in validations] or [0.0]) >= 0.92,
        "scene_images": validations,
    }
    path = ensure_parent_dir(output_path)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = not forbidden and not report["text_or_overlay_found"] and report["fullscreen_validation"]["all_vertical_9x16"]
    error = "scene_image_contact_sheet_detected" if forbidden else "scene_image_text_or_overlay_detected" if report["text_or_overlay_found"] else ""
    return {"ok": ok, "message": "Scene generation report exported", "data": {"path": str(path), "report": report}, "error": error}


def _write_image_validation_report(project_name: str, image_results: list[dict[str, Any]], output_path: str | Path) -> dict[str, Any]:
    scene_report = _write_scene_generation_report(project_name, image_results, output_path)
    report = (scene_report.get("data") or {}).get("report", {})
    report["image_validation_engine"] = "single_frame_provider_output_guard_v1"
    report["visual_mode"] = VISUAL_MODE
    report["render_pipeline_version"] = CLEAN_RENDER_PIPELINE_VERSION
    report["hard_negative_prompt_active"] = True
    report["accepted_for_timeline"] = bool(scene_report.get("ok"))
    path = ensure_parent_dir(output_path)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": scene_report.get("ok"), "message": "Image validation report exported", "data": {"path": str(path), "report": report}, "error": scene_report.get("error", "")}


def _write_render_cleanup_report(
    project_name: str,
    image_results: list[dict[str, Any]],
    output_path: str | Path,
    *,
    cache_status: dict[str, Any] | None = None,
    cache_invalidated: bool = False,
    validation_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validation_report = validation_report or {}
    rejected_images = [
        item
        for item in image_results or []
        if int(item.get("regeneration_attempts") or 0) > 0
        or (item.get("structure_validation") or {}).get("multiple_frames_detected")
        or (item.get("structure_validation") or {}).get("ocr_text_detected")
    ]
    report = {
        "generated_by": "VelaFlow",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "project_name": project_name,
        "render_pipeline_version": CLEAN_RENDER_PIPELINE_VERSION,
        "visual_mode": VISUAL_MODE,
        "cache_invalidated": bool(cache_invalidated),
        "cache_status": {
            "ok": bool((cache_status or {}).get("ok")),
            "message": (cache_status or {}).get("message", ""),
            "error": (cache_status or {}).get("error", ""),
            "required_cache_version": RENDER_CACHE_VERSION,
        },
        "legacy_renderer_removed": True,
        "legacy_renderers_blocked": [
            "thumbnail_composition_renderer",
            "meme_image_renderer",
            "score_overlay_renderer",
            "caption_overlay_renderer",
            "debug_text_renderer",
            "contact_sheet_renderer",
        ],
        "overlay_systems_removed": [
            "automatic image text overlay",
            "numeric score overlay",
            "emoji overlay",
            "caption overlay",
            "hook text overlay",
            "debug metadata overlay",
        ],
        "thumbnail_mode": "raw_validated_cinematic_frame_only",
        "automatic_text_rendering": False,
        "fallback_policy": "text_free_realistic_cinematic_frame_only",
        "validation_pass": bool(validation_report.get("accepted_for_timeline")) and not bool(validation_report.get("text_or_overlay_found")),
        "text_overlay_score": validation_report.get("text_overlay_score", 0.0),
        "numeric_overlay_score": validation_report.get("numeric_overlay_score", 0.0),
        "emoji_detected_score": validation_report.get("emoji_detected_score", 0.0),
        "thumbnail_layout_score": validation_report.get("thumbnail_layout_score", 0.0),
        "ocr_text_detected": bool(validation_report.get("ocr_text_detected")),
        "thumbnail_mode_detected": bool(float(validation_report.get("thumbnail_layout_score") or 0) >= 0.94),
        "rejected_images_count": len(rejected_images),
        "rejected_images": [{"scene_id": item.get("scene_id", ""), "path": item.get("path", "")} for item in rejected_images],
    }
    path = ensure_parent_dir(output_path)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": bool(report["validation_pass"]), "message": "Render cleanup report exported", "data": {"path": str(path), "report": report}, "error": "" if report["validation_pass"] else "cinematic_clean_validation_failed"}


def _write_shot_variation_report(package: dict[str, Any], image_results: list[dict[str, Any]], output_path: str | Path) -> dict[str, Any]:
    scenes = package.get("scene_sequence") or []
    shot_types = [str(scene.get("shot_variation", {}).get("shot_type") or scene.get("shot_type") or "") for scene in scenes]
    framing = [str(scene.get("framing_variation") or scene.get("camera_distance_variation") or "") for scene in scenes]
    motion = [str(scene.get("motion_effect") or "") for scene in scenes]
    hashes = []
    digests = []
    for item in image_results or []:
        image_path = Path(str(item.get("path") or ""))
        hashes.append({"scene_id": item.get("scene_id", ""), "hash": _image_average_hash(image_path)})
        digests.append({"scene_id": item.get("scene_id", ""), "digest": hashlib.sha256(image_path.read_bytes()).hexdigest() if image_path.is_file() else ""})
    pair_scores = []
    exact_duplicate = False
    for left_index in range(len(hashes)):
        for right_index in range(left_index + 1, len(hashes)):
            similarity = _hash_similarity(hashes[left_index]["hash"], hashes[right_index]["hash"])
            same_digest = bool(digests[left_index]["digest"] and digests[left_index]["digest"] == digests[right_index]["digest"])
            exact_duplicate = exact_duplicate or same_digest
            pair_scores.append(
                {
                    "left_scene": hashes[left_index]["scene_id"],
                    "right_scene": hashes[right_index]["scene_id"],
                    "perceptual_similarity": similarity,
                    "exact_duplicate": same_digest,
                }
            )
    raw_duplicate_score = max([float(item["perceptual_similarity"]) for item in pair_scores] or [0.0])
    duplicate_frame_score = 1.0 if exact_duplicate else min(0.99, raw_duplicate_score)
    framing_diversity_score = round((len(set(shot_types)) + len(set(framing))) / max(1, len(shot_types) + len(framing)), 3)
    motion_evolution_score = round(len(set(motion)) / max(1, len(motion)), 3)
    repeated_shot_failure = framing_diversity_score < 0.5 or motion_evolution_score < 0.5
    duplicate_failure = exact_duplicate
    report = {
        "generated_by": "VelaFlow",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "engine": "cinematic_shot_variation_engine_v1",
        "shot_types_used": shot_types,
        "framing_variations": framing,
        "motion_effects": motion,
        "framing_diversity_score": framing_diversity_score,
        "duplicate_frame_score": duplicate_frame_score,
        "raw_perceptual_similarity_score": raw_duplicate_score,
        "motion_evolution_score": motion_evolution_score,
        "duplicate_frame_pairs": pair_scores,
        "exact_duplicate_detected": exact_duplicate,
        "no_identical_scene_reuse": not duplicate_failure,
        "framing_evolution_exists": not repeated_shot_failure,
        "motion_evolution_exists": motion_evolution_score >= 0.5,
        "validation": {
            "ok": not duplicate_failure and not repeated_shot_failure,
            "duplicate_failure": duplicate_failure,
            "repeated_shot_failure": repeated_shot_failure,
        },
    }
    path = ensure_parent_dir(output_path)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    error = "duplicate_scene_frame_detected" if duplicate_failure else "weak_shot_variation_detected" if repeated_shot_failure else ""
    return {"ok": report["validation"]["ok"], "message": "Shot variation report exported", "data": {"path": str(path), "report": report}, "error": error}


def _emotion_pacing_profile(hook_analysis: dict[str, Any], preset: dict[str, Any]) -> str:
    hook_style = str(preset.get("hook_style") or "").lower()
    scores = hook_analysis.get("scores") or {}
    emotional = int(scores.get("emotional_intensity") or hook_analysis.get("hook_intensity") or 60)
    curiosity = int(scores.get("curiosity") or 50)
    if "conversion" in hook_style or "aggressive" in hook_style or curiosity >= 72:
        return "aggressive_hook"
    if emotional >= 70 or "emotional" in hook_style or str(preset.get("preset_id")) == "emotional_story":
        return "sad_emotional"
    if "hope" in hook_style or "story" in hook_style:
        return "hopeful_release"
    return "cinematic_balanced"


def _duration_pattern(scene_count: int, total_duration: float, pacing_profile: str) -> list[float]:
    if pacing_profile == "aggressive_hook":
        pattern = [1.55, 1.8, 2.1, 1.75]
    elif pacing_profile == "sad_emotional":
        pattern = [1.8, 2.15, 2.45, 2.0]
    elif pacing_profile == "hopeful_release":
        pattern = [1.7, 2.0, 2.25, 2.25]
    else:
        pattern = [1.65, 1.95, 2.25, 1.9]
    values = pattern[:scene_count]
    if total_duration and total_duration < sum(values):
        scale = max(0.75, total_duration / max(1.0, sum(values)))
        values = [max(1.45, min(2.6, value * scale)) for value in values]
    return [round(value, 2) for value in values]


def _build_cinematic_timeline_director_v2(package: dict[str, Any], beat_timing_plan: dict[str, Any], hook_analysis: dict[str, Any], preset: dict[str, Any]) -> dict[str, Any]:
    scenes = package.get("scene_sequence") or []
    total_duration = float(beat_timing_plan.get("duration") or sum(float(scene.get("duration") or 2.0) for scene in scenes) or 8.0)
    pacing_profile = _emotion_pacing_profile(hook_analysis, preset)
    durations = _duration_pattern(len(scenes), total_duration, pacing_profile)
    energy_map = {
        "sad_emotional": [28, 52, 86, 58],
        "aggressive_hook": [70, 88, 100, 78],
        "hopeful_release": [38, 58, 82, 64],
        "cinematic_balanced": [45, 62, 88, 60],
    }.get(pacing_profile, [45, 62, 88, 60])
    emotional_map = {
        "sad_emotional": ["lonely setup", "private ache", "hook heartbreak peak", "quiet release"],
        "aggressive_hook": ["instant tension", "rising pressure", "impact peak", "sharp exit"],
        "hopeful_release": ["soft doubt", "realization", "release peak", "open ending"],
        "cinematic_balanced": ["emotional setup", "intimate build", "hook peak", "soft landing"],
    }.get(pacing_profile, ["emotional setup", "intimate build", "hook peak", "soft landing"])
    transition_map = {
        "sad_emotional": ["cinematic fade", "emotional dissolve", "soft blur transition", "cinematic fade"],
        "aggressive_hook": ["beat cut", "light flash", "directional motion blend", "beat cut"],
        "hopeful_release": ["emotional dissolve", "soft blur transition", "cinematic fade", "emotional dissolve"],
        "cinematic_balanced": ["cinematic fade", "soft blur transition", "beat cut", "emotional dissolve"],
    }.get(pacing_profile, CINEMATIC_TRANSITIONS)
    scene_timing = beat_timing_plan.get("scene_timing") or []
    timeline_scenes = []
    cursor = 0.0
    for index, scene in enumerate(scenes, start=1):
        timing = scene_timing[min(index - 1, len(scene_timing) - 1)] if scene_timing else {}
        camera_style = CINEMATIC_CAMERA_STYLES[min(index - 1, len(CINEMATIC_CAMERA_STYLES) - 1)]
        if scene.get("hook_peak_scene") or index == min(3, len(scenes)):
            camera_style = "emotional close-up"
        duration = durations[min(index - 1, len(durations) - 1)] if durations else 1.8
        timeline_scenes.append(
            {
                "scene_id": scene.get("scene_id") or f"scene_{index:02d}",
                "start": round(cursor, 2),
                "end": round(cursor + duration, 2),
                "duration": duration,
                "emotional_beat": emotional_map[min(index - 1, len(emotional_map) - 1)],
                "camera_style": camera_style,
                "motion_style": scene.get("motion_effect") or "cinematic_drift",
                "scene_energy": energy_map[min(index - 1, len(energy_map) - 1)],
                "transition_pacing": transition_map[min(index - 1, len(transition_map) - 1)],
                "lyric_sync": "hook_peak" if scene.get("hook_peak_scene") else timing.get("transition_trigger", "lyric_beat"),
                "beat_peak_alignment": bool(scene.get("hook_peak_scene") or timing.get("hook_peak")),
                "static_scene_allowed": False,
                "minimum_motion_required": "subtle motion, transition motion, or cinematic zoom",
            }
        )
        cursor += duration
    return {
        "generated_by": "VelaFlow",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "engine": "cinematic_timeline_director_v2",
        "pacing_profile": pacing_profile,
        "hook_peak_moment": beat_timing_plan.get("hook_peak_moment", 0),
        "audio_duration": beat_timing_plan.get("duration", total_duration),
        "timeline_duration": round(cursor, 2),
        "hook_pacing_map": {
            "sad_hook": "slower pacing, emotional push-in, lingering shots",
            "aggressive_hook": "quicker cuts, stronger movement, impact transitions",
            "hopeful_hook": "brighter evolution, wider framing, softer movement",
            "active_profile": pacing_profile,
        },
        "rules": {
            "no_static_scenes_longer_than_2s_without_motion": True,
            "single_fullscreen_scene_only": True,
            "scene_must_differ_by_two_or_more_attributes": True,
        },
        "scenes": timeline_scenes,
    }


def _apply_timeline_director_to_package(package: dict[str, Any], timeline_director: dict[str, Any]) -> dict[str, Any]:
    by_id = {item.get("scene_id"): item for item in timeline_director.get("scenes", [])}
    camera_to_motion = {
        "wide isolation framing": "emotional_push_in",
        "cinematic drift": "cinematic_drift",
        "slow push-in": "emotional_push_in",
        "handheld emotional sway": "cinematic_drift",
        "parallax depth": "minimal_pan",
        "rack focus simulation": "slow_cinematic",
        "emotional close-up": "hook_energy_zoom",
        "slow orbit": "slow_cinematic",
    }
    preset_id = str((package.get("creator_outcome_preset") or {}).get("preset_id") or "")
    for scene in package.get("scene_sequence") or []:
        directed = by_id.get(scene.get("scene_id")) or {}
        camera_style = directed.get("camera_style", "")
        scene["duration"] = directed.get("duration", scene.get("duration", 2.0))
        scene["camera_style"] = camera_style
        scene["timeline_director"] = directed
        scene["scene_energy"] = directed.get("scene_energy", 0)
        scene["emotional_beat"] = directed.get("emotional_beat", "")
        scene["transition"] = directed.get("transition_pacing", scene.get("transition", "cinematic fade"))
        if preset_id == "cute_character":
            scene["motion_effect"] = scene.get("motion_effect") or "bounce"
        else:
            scene["motion_effect"] = camera_to_motion.get(camera_style, scene.get("motion_effect", "cinematic_drift"))
        scene["motion_style"] = directed.get("motion_style", scene.get("motion_effect", "cinematic_drift"))
    package["timeline_director"] = timeline_director
    return package


def _save_timeline_director_exports(timeline_director: dict[str, Any], package: dict[str, Any], exports_dir: Path) -> dict[str, str]:
    paths = {
        "timeline_director_path": exports_dir / "timeline_director.json",
        "scene_motion_map_path": exports_dir / "scene_motion_map.json",
        "emotional_curve_path": exports_dir / "emotional_curve.json",
        "shot_progression_path": exports_dir / "shot_progression.json",
    }
    scene_motion_map = {
        "engine": timeline_director.get("engine"),
        "scenes": [
            {
                "scene_id": scene.get("scene_id"),
                "camera_style": scene.get("camera_style"),
                "motion_style": scene.get("motion_style"),
                "motion_effect": (package.get("scene_sequence") or [{}])[index].get("motion_effect", "") if index < len(package.get("scene_sequence") or []) else "",
                "duration": scene.get("duration"),
                "transition_pacing": scene.get("transition_pacing"),
            }
            for index, scene in enumerate(timeline_director.get("scenes") or [])
        ],
    }
    emotional_curve = {
        "engine": timeline_director.get("engine"),
        "pacing_profile": timeline_director.get("pacing_profile"),
        "hook_peak_moment": timeline_director.get("hook_peak_moment"),
        "curve": [
            {
                "scene_id": scene.get("scene_id"),
                "time": scene.get("start"),
                "energy": scene.get("scene_energy"),
                "emotional_beat": scene.get("emotional_beat"),
            }
            for scene in timeline_director.get("scenes") or []
        ],
    }
    shot_progression = {
        "engine": timeline_director.get("engine"),
        "shot_progression": [
            {
                "scene_id": scene.get("scene_id"),
                "shot_type": package_scene.get("shot_type", ""),
                "camera_style": scene.get("camera_style"),
                "framing_variation": package_scene.get("framing_variation", ""),
                "pose_evolution": package_scene.get("pose_evolution", ""),
                "lighting_evolution": package_scene.get("lighting_evolution", ""),
            }
            for scene, package_scene in zip(timeline_director.get("scenes") or [], package.get("scene_sequence") or [])
        ],
    }
    payloads = {
        "timeline_director_path": timeline_director,
        "scene_motion_map_path": scene_motion_map,
        "emotional_curve_path": emotional_curve,
        "shot_progression_path": shot_progression,
    }
    written: dict[str, str] = {}
    for key, payload in payloads.items():
        path = ensure_parent_dir(paths[key])
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        written[key] = str(path)
    return written


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
        diagnostic: dict[str, Any] = {}
        structure_scan: dict[str, Any] = {}
        regeneration_attempts = 0
        active_prompt = prompt
        for attempt in range(3):
            regeneration_attempts = attempt
            diagnostic = generate_image_with_diagnostics(
                provider_used,
                active_prompt,
                str(output_path),
                {**settings, "negative_prompt": HARD_IMAGE_NEGATIVE_PROMPT},
            )
            image_path_candidate = str((diagnostic.get("data") or {}).get("path") or output_path)
            structure_scan = _detect_multi_frame_scene_image(image_path_candidate)
            if not structure_scan.get("multiple_frames_detected") and (structure_scan.get("fullscreen_validation") or {}).get("vertical_9x16"):
                break
            active_prompt = (
                f"{prompt}, STRICT REGENERATION ATTEMPT {attempt + 1}: generate exactly one single cinematic fullscreen frame only, "
                "one continuous real-world camera shot, no storyboard sheet, no panels, no duplicated regions, no text, no numbers, no icons"
            )
            provider_used = image_provider or "offline"
        if structure_scan.get("multiple_frames_detected"):
            # Final rescue uses the local text-free cinematic placeholder so the timeline never accepts a bad sheet.
            diagnostic = generate_image_with_diagnostics(
                "offline",
                f"{prompt}, final fallback: {SINGLE_FRAME_POSITIVE_RULE}, no text, no panels",
                str(output_path),
                {**settings, "negative_prompt": HARD_IMAGE_NEGATIVE_PROMPT},
            )
            structure_scan = _detect_multi_frame_scene_image(str((diagnostic.get("data") or {}).get("path") or output_path))
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
                "structure_validation": structure_scan,
                "regeneration_attempts": regeneration_attempts,
                "hard_negative_prompt": HARD_IMAGE_NEGATIVE_PROMPT,
                "path": str(image_path),
                "prompt": active_prompt,
                "error": error,
            }
        )
    return results


def _voiceover_script(package: dict[str, Any]) -> str:
    lines = [str(scene.get("subtitle") or "").strip() for scene in package.get("scene_sequence", []) or []]
    return "\n".join(line for line in lines if line) or str(package.get("hook_text") or "")


def _try_ai_video_generation(
    project_name: str,
    package: dict[str, Any],
    *,
    exports_dir: Path,
    scenes_dir: Path,
    video_generation_mode: str,
    video_settings: dict[str, Any] | None = None,
    full_hook_lyrics: str = "",
    target_duration: float = 15.0,
    scene_director_plan: dict[str, Any] | None = None,
    emotional_arc: dict[str, Any] | list[Any] | None = None,
) -> dict[str, Any]:
    video_settings = video_settings or {}
    provider = str(video_settings.get("provider") or "gemini_veo")
    mode = str(video_generation_mode or "image_motion_fallback")
    shot_prompts = build_hook_video_shot_prompts(
        full_hook_lyrics=full_hook_lyrics or str(package.get("hook_text") or ""),
        mood=str((package.get("creator_outcome_preset") or {}).get("label") or ""),
        scene_director_plan=scene_director_plan or {},
        emotional_arc=emotional_arc or {},
        target_duration=target_duration,
        shot_count=max(6, int(video_settings.get("prompt_count") or video_settings.get("shot_prompt_count") or 6)),
    )
    shots_dir = exports_dir / "final" / "video_shots"
    shots_dir.mkdir(parents=True, exist_ok=True)
    shot_results: list[dict[str, Any]] = []
    shot_paths: list[str] = []
    fallback_used = mode != "ai_video_provider"
    fallback_reason = "image_motion_mode_selected" if fallback_used else ""
    provider_debug = {
        "provider_selected": provider,
        "api_key_detected": bool(
            (video_settings.get("gemini_api_key") or video_settings.get("google_api_key") or video_settings.get("veo_api_key"))
        ),
        "endpoint_used": "client.models.generate_videos",
        "model_used": str(video_settings.get("model") or video_settings.get("veo_model") or "veo-3.1-generate-preview"),
        "request_status": "not_requested" if mode != "ai_video_provider" else "pending",
        "polling_status": "",
        "download_status": "",
        "mp4_validation_result": {},
        "final_error": "",
    }
    if mode == "ai_video_provider":
        max_real_shots = max(1, min(10, int(video_settings.get("max_real_shots") or 3)))
        for shot in shot_prompts[:max_real_shots]:
            output_path = shots_dir / f"{shot['shot_id']}.mp4"
            result = generate_video_shot(
                shot["prompt"],
                shot["duration_seconds"],
                output_path,
                provider=provider,
                aspect_ratio=str(shot.get("aspect_ratio") or "9:16"),
                motion_style=str(shot.get("motion_style") or ""),
                settings=video_settings,
            )
            shot_results.append({"shot": shot, "result": result})
            result_data = result.get("data") or {}
            provider_debug["request_status"] = "ok" if result.get("ok") else "failed"
            provider_debug["polling_status"] = (result_data.get("provider_status") or result_data.get("fallback_reason") or "")
            provider_debug["download_status"] = "downloaded" if result.get("ok") else ""
            provider_debug["mp4_validation_result"] = result_data.get("validation") or {}
            if not result.get("ok"):
                fallback_used = False
                fallback_reason = result.get("error") or "ai_video_provider_failed"
                provider_debug["final_error"] = fallback_reason
                break
            shot_paths.append(str(output_path))
    provider_debug_path = ensure_parent_dir(exports_dir / "debug" / "provider_debug.json")
    provider_debug_path.write_text(json.dumps(provider_debug, ensure_ascii=False, indent=2), encoding="utf-8")
    provider_confirmed_live = bool(mode == "ai_video_provider" and shot_paths and not fallback_reason)
    manifest_result = save_video_generation_manifest(
        exports_dir / "video_generation_manifest.json",
        {
            "project_name": project_name,
            "mode_requested": mode,
            "mode": mode,
            "provider_used": provider,
            "provider": provider,
            "real_ai_video_used": provider_confirmed_live,
            "provider_confirmed_live": provider_confirmed_live,
            "visual_mode": "cinematic_live_action_video_v1",
            "full_hook_section_used": bool(full_hook_lyrics and len(full_hook_lyrics.strip()) >= len(str(package.get("hook_text") or "").strip())),
            "shot_prompts": shot_prompts,
            "shot_durations": [shot.get("duration_seconds") for shot in shot_prompts],
            "shot_paths": shot_paths,
            "shot_results": shot_results,
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
            "fallback_mode": "image_motion_fallback" if fallback_used else "",
            "provider_debug_path": str(provider_debug_path),
            "final_video_path": "",
            "validation_result": {},
            "api_keys_exported": False,
        },
    )
    return {
        "ok": provider_confirmed_live if mode == "ai_video_provider" else False,
        "message": "AI video shots generated" if provider_confirmed_live else "AI video provider failed" if mode == "ai_video_provider" else "Image motion mode selected",
        "data": {
            "manifest_path": (manifest_result.get("data") or {}).get("path", ""),
            "manifest": (manifest_result.get("data") or {}).get("manifest", {}),
            "provider_debug_path": str(provider_debug_path),
            "shot_prompts": shot_prompts,
            "shot_results": shot_results,
            "shot_paths": shot_paths,
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
        },
        "error": "" if provider_confirmed_live else fallback_reason,
    }


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
    video_generation_mode: str = "image_motion_fallback",
    video_settings: dict[str, Any] | None = None,
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
            CLEAN_RENDER_PIPELINE_VERSION,
            VISUAL_MODE,
            strongest_hook,
            preset.get("preset_id"),
            source_workflow,
            image_provider or "offline",
            video_generation_mode or "image_motion_fallback",
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
        _apply_cinematic_shot_variations(package, director_plan)
        timeline_director = _build_cinematic_timeline_director_v2(package, beat_timing_plan, hook_analysis, preset)
        _apply_timeline_director_to_package(package, timeline_director)
        timeline_paths = _save_timeline_director_exports(timeline_director, package, exports_dir)
        package.update(timeline_paths)
        director_result = save_scene_director_plan(director_plan, exports_dir / "scene_director_plan.json")
        package["scene_director_plan_path"] = (director_result.get("data") or {}).get("path", "")
        scene_prompt_style = "Emotional"
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
        scene_generation_result = _write_scene_generation_report(project_name, image_results, exports_dir / "debug" / "scene_generation_report.json")
        package["scene_generation_report_path"] = (scene_generation_result.get("data") or {}).get("path", "")
        image_validation_result = _write_image_validation_report(project_name, image_results, exports_dir / "debug" / "image_validation_report.json")
        package["image_validation_report_path"] = (image_validation_result.get("data") or {}).get("path", "")
        cache_invalidated = bool(cache_status.get("error") in {"cache_version_mismatch", "cache_stale"} or not cache_status.get("ok"))
        cleanup_result = _write_render_cleanup_report(
            project_name,
            image_results,
            exports_dir / "debug" / "render_cleanup_report.json",
            cache_status=cache_status,
            cache_invalidated=cache_invalidated,
            validation_report=(image_validation_result.get("data") or {}).get("report", {}),
        )
        package["render_cleanup_report_path"] = (cleanup_result.get("data") or {}).get("path", "")
        if not scene_generation_result.get("ok"):
            mark_stage("generating_scenes", "failed")
            return {
                "ok": False,
                "message": "Scene image generation failed fullscreen validation",
                "data": {
                    "package": package,
                    "image_results": image_results,
                    "scene_generation_report": (scene_generation_result.get("data") or {}).get("report", {}),
                    "scene_generation_report_path": package.get("scene_generation_report_path", ""),
                    "image_validation_report_path": package.get("image_validation_report_path", ""),
                    "render_cleanup_report_path": package.get("render_cleanup_report_path", ""),
                    "progress_stages": progress_stages,
                },
                "error": scene_generation_result.get("error") or "scene_image_fullscreen_validation_failed",
            }
        if not cleanup_result.get("ok"):
            mark_stage("generating_scenes", "failed")
            return {
                "ok": False,
                "message": "Scene image generation blocked by cinematic clean validation",
                "data": {
                    "package": package,
                    "image_results": image_results,
                    "image_validation_report_path": package.get("image_validation_report_path", ""),
                    "render_cleanup_report": (cleanup_result.get("data") or {}).get("report", {}),
                    "render_cleanup_report_path": package.get("render_cleanup_report_path", ""),
                    "progress_stages": progress_stages,
                },
                "error": cleanup_result.get("error") or "cinematic_clean_validation_failed",
            }
        shot_variation_result = _write_shot_variation_report(package, image_results, exports_dir / "debug" / "shot_variation_report.json")
        package["shot_variation_report_path"] = (shot_variation_result.get("data") or {}).get("path", "")
        if not shot_variation_result.get("ok"):
            mark_stage("generating_scenes", "failed")
            return {
                "ok": False,
                "message": "Scene image generation failed shot variation validation",
                "data": {
                    "package": package,
                    "image_results": image_results,
                    "scene_generation_report_path": package.get("scene_generation_report_path", ""),
                    "shot_variation_report": (shot_variation_result.get("data") or {}).get("report", {}),
                    "shot_variation_report_path": package.get("shot_variation_report_path", ""),
                    "progress_stages": progress_stages,
                },
                "error": shot_variation_result.get("error") or "shot_variation_validation_failed",
            }
        image_manifest_path = ensure_parent_dir(exports_dir / "image_generation_manifest.json")
        image_manifest = {
            "generated_by": "VelaFlow",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "project_name": project_name,
            "provider_requested": image_provider or "offline",
            "render_pipeline_version": CLEAN_RENDER_PIPELINE_VERSION,
            "visual_mode": VISUAL_MODE,
            "fallback_count": sum(1 for item in image_results if item.get("fallback_used")),
            "images": image_results,
            "scene_generation_report_path": package.get("scene_generation_report_path", ""),
            "image_validation_report_path": package.get("image_validation_report_path", ""),
            "shot_variation_report_path": package.get("shot_variation_report_path", ""),
            "render_cleanup_report_path": package.get("render_cleanup_report_path", ""),
            "api_keys_exported": False,
        }
        image_manifest_path.write_text(json.dumps(image_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        package["image_generation_manifest_path"] = str(image_manifest_path)
        scenes_dir = project_dir / "scenes"
        video_generation = _try_ai_video_generation(
            project_name,
            package,
            exports_dir=exports_dir,
            scenes_dir=scenes_dir,
            video_generation_mode=video_generation_mode,
            video_settings=video_settings or {},
            full_hook_lyrics=str(idea or ""),
            target_duration=float(beat_timing_plan.get("duration") or duration_seconds),
            scene_director_plan=director_plan,
            emotional_arc=beat_timing_plan.get("emotional_curve") or {},
        )
        package["video_generation_mode"] = video_generation_mode
        package["video_generation_manifest_path"] = (video_generation.get("data") or {}).get("manifest_path", "")
        package["video_generation_fallback_used"] = bool((video_generation.get("data") or {}).get("fallback_used"))
        package["provider_debug_path"] = (video_generation.get("data") or {}).get("provider_debug_path", "")
        if video_generation_mode == "ai_video_provider" and not video_generation.get("ok"):
            mark_stage("rendering_video", "failed")
            return {
                "ok": False,
                "message": f"AI Video provider failed: {video_generation.get('error') or 'provider unavailable'}",
                "data": {
                    "package": package,
                    "video_generation": video_generation.get("data", {}),
                    "video_generation_manifest_path": package.get("video_generation_manifest_path", ""),
                    "provider_debug_path": package.get("provider_debug_path", ""),
                    "progress_stages": progress_stages,
                },
                "error": video_generation.get("error") or "ai_video_provider_failed",
            }
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
        video_generation_data = video_generation.get("data") or {}
        video_shot_paths = [path for path in video_generation_data.get("shot_paths", []) if Path(str(path)).is_file()]
        if video_generation.get("ok") and video_shot_paths:
            srt_path = exports_dir / "subtitles.srt"
            write_subtitles(package.get("subtitle_timing", []), srt_path, total_duration=float(beat_timing_plan.get("duration") or duration_seconds))
            ai_subtitle_result = generate_styled_subtitles(
                package.get("subtitle_timing", []),
                exports_dir,
                preset_id=str(preset.get("preset_id") or ""),
                subtitle_style=effective_subtitle_style or str(preset.get("subtitle_style") or ""),
            )
            ai_ass_path = Path(str((ai_subtitle_result.get("data") or {}).get("ass") or ""))
            final_path = ensure_parent_dir(exports_dir / "final_hook_clip.mp4")
            combine_result = combine_scene_clips_to_mp4(
                video_shot_paths,
                final_path,
                subtitle_path=ai_ass_path if ai_ass_path.is_file() else srt_path,
                voiceover_path=voiceover_path,
                background_audio_path=hook_audio_path,
            )
            validation = (combine_result.get("data") or {}).get("validation") or validate_mp4(final_path, require_audio=bool(hook_audio_path))
            render_stage = {
                "render_mode_used": "ai_video_provider",
                "real_ai_video_used": bool(combine_result.get("ok")),
                "fallback_used": False,
                "scene_render_ok": bool(video_shot_paths),
                "completed_scene_count": len(video_shot_paths),
                "combine_ok": bool(combine_result.get("ok")),
                "audio_attach_ok": bool(validation.get("has_audio")),
                "subtitle_ok": srt_path.is_file(),
                "final_mp4_ok": bool(validation.get("valid_mp4")),
                "final_mp4_path": str(final_path) if final_path.is_file() else "",
                "safe_error_message": "" if combine_result.get("ok") else (combine_result.get("error") or "AI video combine failed"),
                "video_generation_manifest_path": package.get("video_generation_manifest_path", ""),
                "video_shot_paths": video_shot_paths,
                "validation": validation,
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
            render_stage_path = ensure_parent_dir(exports_dir / "render_stage.json")
            render_stage_path.write_text(json.dumps(render_stage, ensure_ascii=False, indent=2), encoding="utf-8")
            manifest_payload = {
                "generated_by": "VelaFlow",
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "project_name": project_name,
                "workflow_type": "hook",
                "status": "completed" if combine_result.get("ok") else "failed",
                "final_mp4": str(final_path) if combine_result.get("ok") else "",
                "subtitle_path": str(srt_path),
                "styled_subtitle_path": str(ai_ass_path) if ai_ass_path.is_file() else "",
                "background_audio_path": str(hook_audio_path or ""),
                "voiceover_path": str(voiceover_path or ""),
                "scene_jobs": [{"scene_id": Path(path).stem, "path": path, "status": "completed", "render_mode_used": "ai_video_provider"} for path in video_shot_paths],
                "validation": validation,
                "render_stage": render_stage,
                "render_stage_path": str(render_stage_path),
            }
            manifest_path = ensure_parent_dir(exports_dir / "real_clip_manifest.json")
            manifest_path.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            render_result = {
                "ok": bool(combine_result.get("ok") and validation.get("valid_mp4")),
                "message": "AI video hook clip generated" if combine_result.get("ok") else "AI video combine failed",
                "data": {
                    "manifest": manifest_payload,
                    "manifest_path": str(manifest_path),
                    "render_stage": render_stage,
                    "render_stage_path": str(render_stage_path),
                    "final_mp4": str(final_path) if final_path.is_file() else "",
                    "subtitles": str(srt_path),
                    "styled_subtitles": str(ai_ass_path) if ai_ass_path.is_file() else "",
                    "scene_jobs": manifest_payload["scene_jobs"],
                    "background_audio_path": str(hook_audio_path or ""),
                    "voiceover_path": str(voiceover_path or ""),
                    "duration": validation.get("duration", 0),
                    "validation": validation,
                    "subtitle_burned": (combine_result.get("data") or {}).get("subtitle_burned", False),
                    "subtitle_status": (combine_result.get("data") or {}).get("subtitle_status", "exported_only"),
                    "audio_sync_status": (combine_result.get("data") or {}).get("audio_sync_status", ""),
                    "audio_attached": (combine_result.get("data") or {}).get("audio_attached", False),
                    "uploaded_audio_attached": bool(validation.get("has_audio")),
                    "video_generation_manifest_path": package.get("video_generation_manifest_path", ""),
                },
                "error": "" if combine_result.get("ok") else combine_result.get("error", "ai_video_combine_failed"),
            }
        else:
            render_result = render_real_hook_clip(project_name, package, workflow_type="hook", voiceover_path=voiceover_path, background_audio_path=hook_audio_path, storage_workflow_type=storage_workflow_type, force=force_final_render)
        mark_stage("rendering_video", "completed" if render_result.get("ok") else "failed")
        render_stage = (render_result.get("data") or {}).get("render_stage", {}) or {}
        video_manifest_path = Path(str(package.get("video_generation_manifest_path") or ""))
        if video_manifest_path.is_file():
            try:
                video_manifest_payload = json.loads(video_manifest_path.read_text(encoding="utf-8"))
                video_manifest_payload["final_video_path"] = (render_result.get("data") or {}).get("final_mp4", "")
                video_manifest_payload["validation_result"] = (render_result.get("data") or {}).get("validation", {})
                video_manifest_payload["real_ai_video_used"] = bool(video_manifest_payload.get("real_ai_video_used") and render_result.get("ok"))
                video_manifest_path.write_text(json.dumps(video_manifest_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass
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
            "timeline_director": package.get("timeline_director_path", ""),
            "scene_motion_map": package.get("scene_motion_map_path", ""),
            "emotional_curve": package.get("emotional_curve_path", ""),
            "shot_progression": package.get("shot_progression_path", ""),
            "scene_director_plan": package.get("scene_director_plan_path", ""),
            "cinematic_quality_report": package.get("cinematic_quality_report_path", ""),
            "image_generation_manifest": package.get("image_generation_manifest_path", ""),
            "video_generation_manifest": package.get("video_generation_manifest_path", ""),
            "provider_debug": package.get("provider_debug_path", ""),
            "scene_generation_report": package.get("scene_generation_report_path", ""),
            "image_validation_report": package.get("image_validation_report_path", ""),
            "shot_variation_report": package.get("shot_variation_report_path", ""),
            "render_cleanup_report": package.get("render_cleanup_report_path", ""),
            "hook_analysis": package.get("hook_analysis_path", ""),
            "render_pipeline_report_path": (render_result.get("data") or {}).get("render_pipeline_report_path", ""),
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
            "video_generation": video_generation.get("data", {}),
            "image_generation_manifest_path": package.get("image_generation_manifest_path", ""),
            "video_generation_manifest_path": package.get("video_generation_manifest_path", ""),
            "provider_debug_path": package.get("provider_debug_path", ""),
            "scene_generation_report_path": package.get("scene_generation_report_path", ""),
            "image_validation_report_path": package.get("image_validation_report_path", ""),
            "shot_variation_report_path": package.get("shot_variation_report_path", ""),
            "render_cleanup_report_path": package.get("render_cleanup_report_path", ""),
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
            "timeline_director": timeline_director,
            "timeline_director_path": package.get("timeline_director_path", ""),
            "scene_motion_map_path": package.get("scene_motion_map_path", ""),
            "emotional_curve_path": package.get("emotional_curve_path", ""),
            "shot_progression_path": package.get("shot_progression_path", ""),
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
        render_manifest_payload["video_generation_manifest_path"] = package.get("video_generation_manifest_path", "")
        render_manifest_payload["provider_debug_path"] = package.get("provider_debug_path", "")
        render_manifest_payload["scene_generation_report_path"] = package.get("scene_generation_report_path", "")
        render_manifest_payload["image_validation_report_path"] = package.get("image_validation_report_path", "")
        render_manifest_payload["shot_variation_report_path"] = package.get("shot_variation_report_path", "")
        render_manifest_payload["render_cleanup_report_path"] = package.get("render_cleanup_report_path", "")
        render_manifest_payload["render_pipeline_version"] = CLEAN_RENDER_PIPELINE_VERSION
        render_manifest_payload["timeline_director_path"] = package.get("timeline_director_path", "")
        render_manifest_payload["scene_motion_map_path"] = package.get("scene_motion_map_path", "")
        render_manifest_payload["emotional_curve_path"] = package.get("emotional_curve_path", "")
        render_manifest_payload["shot_progression_path"] = package.get("shot_progression_path", "")
        render_manifest_payload["render_stage_path"] = (render_result.get("data") or {}).get("render_stage_path", "")
        render_manifest_payload["render_pipeline_report_path"] = (render_result.get("data") or {}).get("render_pipeline_report_path", "")
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
                    "timeline_director": timeline_director,
                    "timeline_director_path": package.get("timeline_director_path", ""),
                    "scene_motion_map_path": package.get("scene_motion_map_path", ""),
                    "emotional_curve_path": package.get("emotional_curve_path", ""),
                    "shot_progression_path": package.get("shot_progression_path", ""),
                    "scene_director_plan_path": package.get("scene_director_plan_path", ""),
                    "cinematic_quality_report": cinematic_quality_report,
                    "cinematic_quality_report_path": package.get("cinematic_quality_report_path", ""),
                    "scenes": package.get("scene_sequence", []),
                    "image_results": image_results,
                    "image_generation_manifest_path": package.get("image_generation_manifest_path", ""),
                    "video_generation_manifest_path": package.get("video_generation_manifest_path", ""),
                    "provider_debug_path": package.get("provider_debug_path", ""),
                    "scene_generation_report_path": package.get("scene_generation_report_path", ""),
                    "image_validation_report_path": package.get("image_validation_report_path", ""),
                    "shot_variation_report_path": package.get("shot_variation_report_path", ""),
                    "render_cleanup_report_path": package.get("render_cleanup_report_path", ""),
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
                "video_generation_manifest_path": package.get("video_generation_manifest_path", ""),
                "provider_debug_path": package.get("provider_debug_path", ""),
                "scene_generation_report_path": package.get("scene_generation_report_path", ""),
                "image_validation_report_path": package.get("image_validation_report_path", ""),
                "shot_variation_report_path": package.get("shot_variation_report_path", ""),
                "render_cleanup_report_path": package.get("render_cleanup_report_path", ""),
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
                "timeline_director": timeline_director,
                "timeline_director_path": package.get("timeline_director_path", ""),
                "scene_motion_map_path": package.get("scene_motion_map_path", ""),
                "emotional_curve_path": package.get("emotional_curve_path", ""),
                "shot_progression_path": package.get("shot_progression_path", ""),
                "viral_timing_plan": viral_timing_plan,
                "viral_metrics": viral_metrics,
                "progress_stages": progress_stages,
                "viral_timing_plan_path": (timing_result.get("data") or {}).get("path", ""),
                "tiktok_package": tiktok_package.get("data", {}),
                "clip_version": clip_version.get("data", {}),
                "render_cache": {"cache_key": cache_key, "cache_hit": bool(cache_status.get("ok")), "cache_status": cache_status.get("message", ""), "cache_dir": (cache_save.get("data") or {}).get("cache_dir", ""), "render_pipeline_version": CLEAN_RENDER_PIPELINE_VERSION},
                "voiceover": voice_result.get("data", {}),
                "hook_audio_path": hook_audio_path,
                "render": render_result.get("data", {}),
                "video_generation": video_generation.get("data", {}),
                "video_generation_manifest_path": package.get("video_generation_manifest_path", ""),
                "provider_debug_path": package.get("provider_debug_path", ""),
                "manifest_path": str(quick_manifest_path),
                "render_manifest_path": str(render_manifest_path),
                "render_stage_path": (render_result.get("data") or {}).get("render_stage_path", ""),
                "render_pipeline_report_path": (render_result.get("data") or {}).get("render_pipeline_report_path", ""),
                "scene_manifest_path": str(scene_manifest_path),
                "final_mp4": (render_result.get("data") or {}).get("final_mp4", ""),
            },
            "error": "" if render_result.get("ok") else render_result.get("error", ""),
        }
    except Exception as exc:
        return {"ok": False, "message": "Quick hook clip generation failed", "data": {}, "error": str(exc)}
