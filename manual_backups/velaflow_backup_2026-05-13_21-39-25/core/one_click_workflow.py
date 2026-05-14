from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from core.clip_factory import choose_clip_scene


def build_full_mv_draft_payload(project: Dict[str, Any], ffmpeg_path: str = "") -> Dict[str, Any]:
    settings = project.get("settings", {}) or {}
    return {
        "project": project,
        "audio_path": (project.get("assets", {}) or {}).get("audio_path", ""),
        "aspect_ratios": ["16:9"],
        "subtitle_mode": settings.get("subtitle_style", "simple"),
        "motion_style": settings.get("motion_style", "auto"),
        "transition_mode": "fade",
        "render_profile": "Draft",
        "color_grade": settings.get("color_profile", "none"),
        "beat_sync": False,
        "ffmpeg_path": ffmpeg_path,
    }


def build_tiktok_set_plan(project: Dict[str, Any], source_video: str = "", render_dir: str | Path = "", ffmpeg_path: str = "") -> Dict[str, Any]:
    clip_types = ["15s teaser", "30s teaser", "60s promo", "Hook Clip", "Emotional Quote Clip"]
    clips: List[Dict[str, Any]] = []
    for clip_type in clip_types:
        scene = choose_clip_scene(project, clip_type)
        clips.append(
            {
                "clip_type": clip_type,
                "scene_id": scene.get("scene_id", ""),
                "source_video": source_video,
                "render_dir": str(render_dir),
                "preview": False,
                "ffmpeg_path": ffmpeg_path,
            }
        )
    return {"ok": True, "message": "TikTok set plan ready", "data": {"clips": clips}, "error": ""}


def release_package_checklist(project: Dict[str, Any]) -> Dict[str, Any]:
    song = project.get("song", {}) or {}
    mv = project.get("mv", {}) or {}
    assets = project.get("assets", {}) or {}
    checks = [
        {"name": "Song metadata", "ok": bool(song)},
        {"name": "Storyboard", "ok": bool(mv.get("storyboard"))},
        {"name": "Approved visuals", "ok": bool(assets.get("approved_images"))},
        {"name": "Audio", "ok": bool(assets.get("audio_path"))},
        {"name": "Marketing package ready", "ok": bool(project.get("marketing_package"))},
    ]
    return {"ok": all(item["ok"] for item in checks[:3]), "message": "Release checklist created", "data": {"checks": checks}, "error": ""}
