from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.paths import workflow_project_root
from core.project_io import safe_name


FRIENDLY_MESSAGES = {
    "missing_ffmpeg": "Render engine is not available right now. Please try again after the server finishes starting.",
    "active_render_job": "A clip is already rendering for this project. Please wait for it to finish before starting another one.",
    "missing_scene_clips": "Scene videos could not be created. Your images and subtitles were saved, so you can retry the render.",
    "scene_video_render_failed": "Scene video could not be created. Please retry final render.",
    "cache_stale": "Some cached assets are old or missing. VelaFlow will regenerate only the missing parts.",
    "cache_miss": "No saved render cache was found. VelaFlow will build fresh assets.",
    "timeout": "Render took too long. VelaFlow stopped safely so you can retry.",
    "permission denied": "The server could not write the render file. Please retry with a new version.",
    "no space": "Storage is running low. Clean old temporary files and try again.",
    "memory": "The server is low on memory. VelaFlow will use the safer lightweight render path.",
}


def friendly_error_message(error: Any, default: str = "Clip render needs attention. Please retry.") -> str:
    text = str(error or "").strip()
    if not text:
        return default
    lowered = text.lower()
    for marker, message in FRIENDLY_MESSAGES.items():
        if marker in lowered:
            return message
    if len(text) > 180 or "\n" in text:
        return default
    return text


def _read_json(path: Path, default: Any) -> Any:
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


def _project_dir(project_name: str, workflow_type: str) -> Path:
    return workflow_project_root(workflow_type or "song") / safe_name(project_name or "project")


def recover_partial_render(project_name: str, workflow_type: str = "song") -> dict[str, Any]:
    root = _project_dir(project_name, workflow_type)
    exports = root / "exports"
    scenes = root / "scenes"
    final_mp4 = exports / "final_hook_clip.mp4"
    stage = _read_json(exports / "render_stage.json", {})
    scene_clips = sorted(scenes.glob("scene_*.mp4")) if scenes.exists() else []
    images = sorted((root / "images").glob("scene_*.jpg")) if (root / "images").exists() else []
    failed_stages = []
    if stage and not stage.get("scene_render_ok", True):
        failed_stages.append("scene_render")
    if stage and not stage.get("combine_ok", True):
        failed_stages.append("combine")
    if stage and not stage.get("final_mp4_ok", True):
        failed_stages.append("final_mp4")
    if images and not scene_clips:
        failed_stages.append("missing_scene_clips")
    latest_successful_render = str(final_mp4) if final_mp4.is_file() and final_mp4.stat().st_size > 0 else ""
    return {
        "ok": True,
        "message": "Partial render recovery inspected",
        "data": {
            "project_dir": str(root),
            "latest_successful_render": latest_successful_render,
            "scene_clip_count": len(scene_clips),
            "image_count": len(images),
            "failed_stages": sorted(set(failed_stages)),
            "can_retry_final_render": bool(images),
            "safe_error_message": friendly_error_message(stage.get("safe_error_message") or stage.get("error") or ""),
        },
        "error": "",
    }


def build_recovery_plan(
    project_name: str,
    workflow_type: str = "song",
    *,
    last_error: Any = "",
    cache_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    recovery = recover_partial_render(project_name, workflow_type)["data"]
    failed_stages = list(recovery.get("failed_stages") or [])
    if last_error:
        failed_stages.append(str(last_error))
    actions = []
    if recovery.get("latest_successful_render"):
        actions.append("Use latest successful render while retrying a new version.")
    if recovery.get("can_retry_final_render"):
        actions.append("Reuse existing images/subtitles and retry final render.")
    if cache_status and cache_status.get("ok"):
        actions.append("Reuse cached scene assets.")
    if not actions:
        actions.append("Retry with the safe static render path.")
    return {
        "ok": True,
        "message": "Recovery plan ready",
        "data": {
            "failed_stages": sorted(set(failed_stages)),
            "actions": actions,
            "safe_error_message": friendly_error_message(last_error),
            "recovery": recovery,
        },
        "error": "",
    }
