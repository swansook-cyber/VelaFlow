from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from core.character_engine import apply_character_consistency, create_character_profile, save_character_profile
from core.hook_clip_engine import build_hook_render_package, export_hook_clip_package
from core.hook_intelligence import analyze_opening_hook, save_hook_analysis
from core.paths import resolve_project_folder
from core.preset_engine import get_preset, preset_to_render_settings, preset_to_visual_settings
from core.project_io import safe_name
from core.real_clip_pipeline import render_real_hook_clip
from core.subtitle_engine import generate_styled_subtitles
from core.viral_timing_engine import create_viral_timing_plan, save_viral_timing_plan
from core.voiceover_engine import generate_voiceover_audio
from providers.image_ai import generate_image


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
        project_dir = resolve_project_folder(project_name or "hook_clip", "clips")
        exports_dir = project_dir / "exports"
        final_dir = exports_dir / "final"
        final_dir.mkdir(parents=True, exist_ok=True)
        render_data = render_data or {}
        final_mp4 = Path(str(render_data.get("final_mp4") or ""))
        subtitle_path = Path(str(render_data.get("subtitles") or exports_dir / "subtitles.srt"))
        if final_mp4.is_file():
            shutil.copy2(final_mp4, final_dir / "final_hook_clip.mp4")
        if subtitle_path.is_file():
            shutil.copy2(subtitle_path, final_dir / "subtitles.srt")
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
            "thumbnail_prompt.txt": thumbnail_prompt,
            "upload_checklist.txt": "\n".join(checklist),
        }
        written: dict[str, str] = {}
        for filename, content in files.items():
            path = final_dir / filename
            path.write_text(str(content).strip() + "\n", encoding="utf-8")
            written[filename] = str(path)
        manifest = {
            "generated_by": "VelaFlow",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "project_name": project_name,
            "final_dir": str(final_dir),
            "final_hook_clip": str(final_dir / "final_hook_clip.mp4") if (final_dir / "final_hook_clip.mp4").is_file() else "",
            "subtitles": str(final_dir / "subtitles.srt") if (final_dir / "subtitles.srt").is_file() else "",
            "viral_timing_plan": (timing_result.get("data") or {}).get("path", ""),
            "files": written,
        }
        manifest_path = final_dir / "tiktok_package_manifest.json"
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
        "clear subject, no watermark, no random text"
    )
    return apply_character_consistency(base, character_profile, consistency_strength)


def _apply_preset_to_scenes(package: dict[str, Any], preset: dict[str, Any]) -> None:
    sequence = PRESET_MOTION_SEQUENCES.get(str(preset.get("motion_style") or ""), MOTION_EFFECTS)
    for index, scene in enumerate(package.get("scene_sequence", []) or [], start=1):
        scene["motion_effect"] = sequence[(index - 1) % len(sequence)]
        scene["subtitle_style"] = preset.get("subtitle_style", "")
        scene["transition"] = preset.get("transition_style") or scene.get("transition", "")
        scene["pace"] = preset.get("pace", "")
        scene.setdefault("render_provider_metadata", {})["aspect_ratio"] = preset.get("aspect_ratio", "9:16")


def _generate_scene_images(
    project_name: str,
    package: dict[str, Any],
    *,
    idea: str,
    preset: dict[str, Any],
    character_profile: dict[str, Any] | None,
    consistency_strength: str,
    image_provider: str,
    image_settings: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    project_dir = resolve_project_folder(project_name or "hook_clip", "clips")
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
        output_path = images_dir / f"{safe_name(scene_id)}.png"
        provider_used = image_provider or "offline"
        try:
            image_path = generate_image(provider_used, prompt, str(output_path), settings)
            ok = Path(image_path).is_file()
            error = ""
        except Exception as exc:
            provider_used = "offline"
            image_path = generate_image("offline", prompt, str(output_path), settings)
            ok = Path(image_path).is_file()
            error = str(exc)
        scene["image_prompt"] = prompt
        scene["source_image_path"] = str(image_path)
        scene["image_provider"] = provider_used
        results.append({"scene_id": scene_id, "ok": ok, "provider": provider_used, "path": str(image_path), "prompt": prompt, "error": error})
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
) -> dict[str, Any]:
    try:
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
        enriched_idea = f"{hook_analysis.get('opening_line', '')}\n{idea}".strip()
        content = _idea_content(enriched_idea, source_workflow, preset)
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
        image_results = _generate_scene_images(
            project_name,
            package,
            idea=idea,
            preset=preset,
            character_profile=character_profile,
            consistency_strength=consistency_strength,
            image_provider=image_provider or "offline",
            image_settings=image_settings,
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
        render_result = render_real_hook_clip(project_name, package, workflow_type="hook", voiceover_path=voiceover_path, force=True)
        export_result = export_hook_clip_package(project_name, package)
        project_dir = resolve_project_folder(project_name, "clips")
        exports_dir = project_dir / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        character_save = save_character_profile(project_name, character_profile, "clips") if character_profile else {"ok": False, "data": {}, "error": "no_character_profile"}
        hook_save = save_hook_analysis(project_name, hook_analysis, exports_dir)
        subtitle_result = generate_styled_subtitles(
            package.get("subtitle_timing", []),
            exports_dir,
            preset_id=str(preset.get("preset_id") or ""),
            subtitle_style=effective_subtitle_style or str(preset.get("subtitle_style") or ""),
        )
        viral_timing_plan = create_viral_timing_plan(package, target_duration=duration_seconds, preset_id=str(preset.get("preset_id") or ""))
        timing_result = save_viral_timing_plan(viral_timing_plan, exports_dir / "viral_timing_plan.json")
        package["viral_timing_plan"] = viral_timing_plan
        tiktok_package = export_tiktok_package(project_name, package, render_result.get("data", {}))
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
            "character_profile": character_profile or {},
            "character_profile_path": (character_save.get("data") or {}).get("path", ""),
            "hook_analysis": hook_analysis,
            "hook_analysis_path": (hook_save.get("data") or {}).get("path", ""),
            "styled_subtitles": subtitle_result,
            "viral_timing_plan": viral_timing_plan,
            "viral_timing_plan_path": (timing_result.get("data") or {}).get("path", ""),
            "tiktok_package": tiktok_package,
            "voiceover": voice_result,
            "render": render_result,
            "hook_package_export": export_result,
            "final_mp4": (render_result.get("data") or {}).get("final_mp4", ""),
        }
        quick_manifest_path = exports_dir / "quick_hook_clip_manifest.json"
        render_manifest_path = exports_dir / "render_manifest.json"
        scene_manifest_path = exports_dir / "scene_manifest.json"
        quick_manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        render_manifest_path.write_text(json.dumps((render_result.get("data") or {}).get("manifest", manifest), ensure_ascii=False, indent=2), encoding="utf-8")
        scene_manifest_path.write_text(
            json.dumps(
                {
                    "generated_by": "VelaFlow",
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                    "project_name": project_name,
                    "preset": preset,
                    "character_profile": character_profile or {},
                    "hook_analysis": hook_analysis,
                    "scenes": package.get("scene_sequence", []),
                    "image_results": image_results,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        package["quick_generate"]["manifest_path"] = str(quick_manifest_path)
        return {
            "ok": bool(render_result.get("ok")),
            "message": "Quick hook clip generated" if render_result.get("ok") else "Quick hook package generated, but MP4 render needs attention",
            "data": {
                "package": package,
                "package_export": export_result.get("data", {}),
                "image_results": image_results,
                "character_profile": character_profile or {},
                "character_profile_path": (character_save.get("data") or {}).get("path", ""),
                "hook_analysis": hook_analysis,
                "hook_analysis_path": (hook_save.get("data") or {}).get("path", ""),
                "styled_subtitles": subtitle_result.get("data", {}),
                "viral_timing_plan": viral_timing_plan,
                "viral_timing_plan_path": (timing_result.get("data") or {}).get("path", ""),
                "tiktok_package": tiktok_package.get("data", {}),
                "voiceover": voice_result.get("data", {}),
                "render": render_result.get("data", {}),
                "manifest_path": str(quick_manifest_path),
                "render_manifest_path": str(render_manifest_path),
                "scene_manifest_path": str(scene_manifest_path),
                "final_mp4": (render_result.get("data") or {}).get("final_mp4", ""),
            },
            "error": "" if render_result.get("ok") else render_result.get("error", ""),
        }
    except Exception as exc:
        return {"ok": False, "message": "Quick hook clip generation failed", "data": {}, "error": str(exc)}
