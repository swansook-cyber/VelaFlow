from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.project_state import ensure_project_structure, sanitize_project_name, utc_now


def create_storyboard(project_name: str, title: str, creative_direction: str = "") -> dict[str, Any]:
    return {
        "storyboard_id": f"storyboard_{sanitize_project_name(title)}_{utc_now().replace(':', '')}",
        "project_name": sanitize_project_name(project_name),
        "title": title,
        "creative_direction": creative_direction,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "scenes": [],
    }


def add_scene(
    storyboard: dict[str, Any],
    shot_description: str,
    camera_movement: str,
    lighting: str,
    mood: str,
    duration: float,
    prompt: str,
) -> dict[str, Any]:
    storyboard = dict(storyboard or {})
    scenes = list(storyboard.get("scenes", []))
    scene = {
        "scene_number": len(scenes) + 1,
        "shot_description": shot_description,
        "camera_movement": camera_movement,
        "lighting": lighting,
        "mood": mood,
        "duration": float(duration or 0),
        "prompt": prompt,
    }
    scenes.append(scene)
    storyboard["scenes"] = scenes
    storyboard["updated_at"] = utc_now()
    return storyboard


def storyboard_to_text(storyboard: dict[str, Any]) -> str:
    lines = [storyboard.get("title", "Storyboard"), "=" * len(storyboard.get("title", "Storyboard")), storyboard.get("creative_direction", ""), ""]
    for scene in storyboard.get("scenes", []):
        lines.extend(
            [
                f"Scene {scene.get('scene_number')}",
                f"Duration: {scene.get('duration')}s",
                f"Shot: {scene.get('shot_description')}",
                f"Camera: {scene.get('camera_movement')}",
                f"Lighting: {scene.get('lighting')}",
                f"Mood: {scene.get('mood')}",
                f"Prompt: {scene.get('prompt')}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def export_storyboard_txt(storyboard: dict[str, Any], project_name: str | None = None) -> Path:
    project = project_name or storyboard.get("project_name") or "Storyboard_Project"
    folder = ensure_project_structure(project) / "assets" / "storyboards"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{sanitize_project_name(storyboard.get('title', 'storyboard'))}.txt"
    path.write_text(storyboard_to_text(storyboard), encoding="utf-8-sig")
    return path


def export_storyboard_json(storyboard: dict[str, Any], project_name: str | None = None) -> Path:
    project = project_name or storyboard.get("project_name") or "Storyboard_Project"
    folder = ensure_project_structure(project) / "assets" / "storyboards"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{sanitize_project_name(storyboard.get('title', 'storyboard'))}.json"
    path.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
