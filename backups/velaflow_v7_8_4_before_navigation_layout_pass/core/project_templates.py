from __future__ import annotations

from typing import Any, Dict

from core.project_io import new_project
from core.preset_system import get_project_template, list_scene_presets


def apply_template_to_project(project: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
    if not template:
        return project
    project.setdefault("settings", {})
    project["settings"]["template"] = template.get("name", "")
    project["settings"]["render_profile"] = template.get("render_profile", "Standard")
    project["settings"]["subtitle_style"] = template.get("subtitle_style", "simple")
    project["settings"]["motion_style"] = template.get("motion_style", "auto")
    project["settings"]["color_profile"] = template.get("color_profile", "film_look")
    project["settings"]["prompt_rules"] = template.get("prompt_rules", "")
    project.setdefault("song", {})
    project["song"]["music_style_prompt"] = template.get("song_style", project["song"].get("music_style_prompt", ""))
    project["song"]["song_structure"] = template.get("song_structure", [])
    project["song"]["template_name"] = template.get("name", "")
    project.setdefault("mv", {})
    project["mv"]["template"] = {
        "name": template.get("name", ""),
        "scene_presets": template.get("scene_presets", []),
        "prompt_rules": template.get("prompt_rules", ""),
    }
    project["visual_identity"] = build_visual_identity(template)
    return project


def create_project_from_template(title: str, template_name: str, artist: str = "VelaLab") -> Dict[str, Any]:
    project = new_project(title, artist)
    return apply_template_to_project(project, get_project_template(template_name))


def build_visual_identity(template: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "template": template.get("name", ""),
        "color_profile": template.get("color_profile", ""),
        "motion_style": template.get("motion_style", ""),
        "subtitle_style": template.get("subtitle_style", ""),
        "prompt_rules": template.get("prompt_rules", ""),
        "continuity_notes": [
            "Keep the same lead character identity across all scenes.",
            "Keep color and lighting consistent with the selected template.",
            "Use scene presets as a visual vocabulary instead of unrelated locations.",
        ],
    }


def suggested_scene_preset_details(template: Dict[str, Any]) -> list[Dict[str, Any]]:
    wanted = set(template.get("scene_presets", []) or [])
    return [scene for scene in list_scene_presets() if scene.get("name") in wanted]
