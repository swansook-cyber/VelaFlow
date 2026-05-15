from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from core.hook_clip_engine import build_hook_render_package, export_hook_clip_package
from core.paths import resolve_project_folder
from core.project_io import safe_name
from core.real_clip_pipeline import render_real_hook_clip
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
    "duration": "8s",
    "quality": "Draft",
    "motion_intensity": "High",
    "bundle_name": "Quick Hook Clip",
}

MOTION_EFFECTS = ["slow_zoom", "pan_left", "shake", "cinematic_fade"]


def _idea_content(idea: str, source_workflow: str) -> dict[str, Any]:
    cleaned = " ".join(str(idea or "").split()).strip()
    if not cleaned:
        cleaned = "หยุดดูคลิปนี้ก่อน มีบางอย่างที่คุณอาจเจอเหมือนกัน"
    return {
        "selected_hook_text": cleaned[:120],
        "main_idea": cleaned,
        "source_workflow": source_workflow,
        "viral_hooks": [cleaned],
        "subtitle_lines": [cleaned],
    }


def _scene_image_prompt(scene: dict[str, Any], idea: str) -> str:
    prompt = str(scene.get("visual_prompt") or "").strip()
    lighting = str(scene.get("lighting") or "natural cinematic lighting").strip()
    camera = str(scene.get("camera_direction") or "vertical creator shot").strip()
    if not prompt:
        prompt = f"vertical short-form scene about {idea}"
    return (
        f"{prompt}, {camera}, {lighting}, realistic cinematic vertical 9:16 composition, "
        "clear subject, high quality, no watermark, no random text"
    )


def _generate_scene_images(
    project_name: str,
    package: dict[str, Any],
    *,
    idea: str,
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
    scenes = package.get("scene_sequence") or []
    for index, scene in enumerate(scenes, start=1):
        scene_id = str(scene.get("scene_id") or f"scene_{index:02d}")
        prompt = _scene_image_prompt(scene, idea)
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
        scene["motion_effect"] = MOTION_EFFECTS[(index - 1) % len(MOTION_EFFECTS)]
        results.append(
            {
                "scene_id": scene_id,
                "ok": ok,
                "provider": provider_used,
                "path": str(image_path),
                "prompt": prompt,
                "error": error,
            }
        )
    return results


def _voiceover_script(package: dict[str, Any]) -> str:
    lines = []
    for scene in package.get("scene_sequence", []) or []:
        subtitle = str(scene.get("subtitle") or "").strip()
        if subtitle:
            lines.append(subtitle)
    return "\n".join(lines) or str(package.get("hook_text") or "")


def quick_generate_hook_clip(
    project_name: str,
    idea: str,
    *,
    source_workflow: str = "hook_clip",
    clip_mode: str = "Fast Hook",
    duration_seconds: int = 8,
    visual_settings: dict[str, Any] | None = None,
    render_settings: dict[str, Any] | None = None,
    image_provider: str = "offline",
    image_settings: dict[str, Any] | None = None,
    voiceover_style: str = "calm narrator",
    voiceover_api_key: str = "",
) -> dict[str, Any]:
    try:
        project_name = project_name or "Quick Hook Clip"
        visual = {**DEFAULT_VISUAL_SETTINGS, **(visual_settings or {})}
        render = {**DEFAULT_RENDER_SETTINGS, **(render_settings or {})}
        render["aspect_ratio"] = "9:16"
        render["duration"] = f"{max(5, min(10, int(duration_seconds or 8)))}s"
        content = _idea_content(idea, source_workflow)
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
        package["quick_generate"] = {
            "enabled": True,
            "idea": idea,
            "image_provider": image_provider or "offline",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        image_results = _generate_scene_images(
            project_name,
            package,
            idea=idea,
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
            output_name="hook_voiceover.mp3",
        )
        voiceover_path = str((voice_result.get("data") or {}).get("audio_path") or "")
        render_result = render_real_hook_clip(
            project_name,
            package,
            workflow_type="hook",
            voiceover_path=voiceover_path,
            force=True,
        )
        export_result = export_hook_clip_package(project_name, package)
        project_dir = resolve_project_folder(project_name, "clips")
        exports_dir = project_dir / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "generated_by": "VelaFlow",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "project_name": project_name,
            "idea": idea,
            "source_workflow": source_workflow,
            "clip_mode": clip_mode,
            "image_provider": image_provider or "offline",
            "image_results": image_results,
            "voiceover": voice_result,
            "render": render_result,
            "hook_package_export": export_result,
            "final_mp4": (render_result.get("data") or {}).get("final_mp4", ""),
        }
        manifest_path = exports_dir / "quick_hook_clip_manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        package["quick_generate"]["manifest_path"] = str(manifest_path)
        return {
            "ok": bool(render_result.get("ok")),
            "message": "Quick hook clip generated" if render_result.get("ok") else "Quick hook package generated, but MP4 render needs attention",
            "data": {
                "package": package,
                "package_export": export_result.get("data", {}),
                "image_results": image_results,
                "voiceover": voice_result.get("data", {}),
                "render": render_result.get("data", {}),
                "manifest_path": str(manifest_path),
                "final_mp4": (render_result.get("data") or {}).get("final_mp4", ""),
            },
            "error": "" if render_result.get("ok") else render_result.get("error", ""),
        }
    except Exception as exc:
        return {"ok": False, "message": "Quick hook clip generation failed", "data": {}, "error": str(exc)}
