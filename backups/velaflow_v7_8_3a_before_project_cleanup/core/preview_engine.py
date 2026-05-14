from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

from core.render_engine import run_render


ROOT = Path(__file__).resolve().parents[1]


def _scene_id(scene: Dict[str, Any], index: int) -> str:
    return str(scene.get("scene") or index + 1)


def build_preview_project(project: Dict[str, Any], scene_index: int, duration_seconds: int = 5) -> Dict[str, Any]:
    preview = deepcopy(project)
    storyboard = ((project.get("mv", {}) or {}).get("storyboard", []) or [])
    if not storyboard:
        preview.setdefault("mv", {})["storyboard"] = []
        return preview

    index = max(0, min(int(scene_index), len(storyboard) - 1))
    scene = dict(storyboard[index])
    scene_id = _scene_id(scene, index)
    scene["duration_seconds"] = max(1, min(int(duration_seconds or 5), int(scene.get("duration_seconds") or duration_seconds or 5)))
    scene["scene"] = scene_id
    preview.setdefault("mv", {})["storyboard"] = [scene]
    preview["title"] = f"{project.get('title', 'project')} Preview Scene {scene_id}"

    assets = deepcopy(project.get("assets", {}) or {})
    for key in ["approved_images", "images", "videos", "video_metadata"]:
        values = assets.get(key, {}) or {}
        selected = values.get(scene_id) or values.get(str(int(scene_id)) if str(scene_id).isdigit() else scene_id)
        assets[key] = {scene_id: selected} if selected else {}
    preview["assets"] = assets
    return preview


def run_scene_preview(project: Dict[str, Any], scene_index: int, options: Dict[str, Any] | None = None, progress_callback=None) -> Dict[str, Any]:
    options = options or {}
    duration = int(options.get("preview_seconds", 5) or 5)
    preview_project = build_preview_project(project, scene_index, duration)
    render_options = {
        "base_dir": options.get("base_dir", ROOT / "outputs" / "previews"),
        "aspect_ratios": [options.get("aspect_ratio", "16:9")],
        "audio_path": options.get("audio_path", ""),
        "subtitle_mode": options.get("subtitle_mode", "simple"),
        "motion_style": options.get("motion_style", "auto"),
        "transition_mode": options.get("transition_mode", "none"),
        "render_profile": options.get("render_profile", "Draft"),
        "color_grade": options.get("color_grade", "none"),
        "beat_sync": bool(options.get("beat_sync", False)),
        "ffmpeg_path": options.get("ffmpeg_path", "ffmpeg"),
    }
    result = run_render(preview_project, render_options, progress_callback=progress_callback)
    if not isinstance(result.get("data"), dict):
        result["data"] = {}
    result["data"]["preview_scene_index"] = scene_index
    result["data"]["preview_seconds"] = duration
    return result
