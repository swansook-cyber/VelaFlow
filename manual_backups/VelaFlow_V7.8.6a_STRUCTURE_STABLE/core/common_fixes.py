from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from core.project_io import safe_name


def fix_common_issues(project: Dict[str, Any]) -> Dict[str, Any]:
    fixes: List[str] = []
    project.setdefault("song", {})
    project.setdefault("mv", {})
    project.setdefault("assets", {})
    project.setdefault("settings", {})
    assets = project["assets"]
    for key, default in {
        "audio_path": "",
        "images": {},
        "image_versions": {},
        "approved_images": {},
        "rejected_images": {},
        "locked_images": {},
        "hero_shot": "",
        "videos": {},
        "video_versions": {},
        "video_metadata": {},
        "locked_videos": {},
    }.items():
        if key not in assets:
            assets[key] = default
            fixes.append(f"created assets.{key}")
    if not project["settings"].get("render_profile"):
        project["settings"]["render_profile"] = "Draft"
        fixes.append("set default render_profile=Draft")
    if not project["settings"].get("subtitle_style"):
        project["settings"]["subtitle_style"] = "simple"
        fixes.append("set default subtitle_style=simple")
    storyboard = project["mv"].setdefault("storyboard", [])
    for index, scene in enumerate(storyboard):
        scene.setdefault("scene", index + 1)
        scene.setdefault("duration_seconds", 5)
        if not scene.get("subtitle_text") and scene.get("lyric_part"):
            scene["subtitle_text"] = scene.get("lyric_part", "")
            fixes.append(f"scene {scene['scene']}: copied lyric_part to subtitle_text")
        if not scene.get("image_prompt") and scene.get("scene_visual"):
            scene["image_prompt"] = scene.get("scene_visual", "")
            fixes.append(f"scene {scene['scene']}: copied scene_visual to image_prompt")
    stale = []
    for scene_id, path_value in list((assets.get("approved_images", {}) or {}).items()):
        if path_value and not Path(path_value).exists():
            stale.append(scene_id)
    for scene_id in stale:
        assets["approved_images"].pop(scene_id, None)
        fixes.append(f"removed stale approved image for scene {scene_id}")
    project.setdefault("runtime", {})["last_common_fix_project"] = safe_name(project.get("title", "project"))
    return {"ok": True, "message": f"Applied {len(fixes)} common fixes", "data": {"project": project, "fixes": fixes}, "error": ""}
