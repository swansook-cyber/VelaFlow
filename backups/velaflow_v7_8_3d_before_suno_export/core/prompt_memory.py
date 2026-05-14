from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[1]
MEMORY_PATH = ROOT / "config" / "prompt_memory.json"


DEFAULT_MEMORY: Dict[str, Any] = {
    "preferred_render_profile": "Cinematic",
    "preferred_subtitle_style": "cinematic",
    "preferred_motion_style": "cinematic_drift",
    "preferred_color_profile": "film_look",
    "prompt_keywords": ["cinematic Thai emotional realism", "consistent lead character"],
    "favorite_scene_tags": ["emotional close-up", "neon city"],
    "updated_at": "",
}


def load_prompt_memory(path: str | Path | None = None) -> Dict[str, Any]:
    source = Path(path) if path else MEMORY_PATH
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    memory = dict(DEFAULT_MEMORY)
    memory.update(data if isinstance(data, dict) else {})
    return memory


def save_prompt_memory(memory: Dict[str, Any], path: str | Path | None = None) -> Dict[str, Any]:
    target = Path(path) if path else MEMORY_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(DEFAULT_MEMORY)
    payload.update(memory or {})
    payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "message": "Prompt memory saved", "data": {"path": str(target), "memory": payload}, "error": ""}


def apply_prompt_memory_to_project(project: Dict[str, Any], memory: Dict[str, Any] | None = None) -> Dict[str, Any]:
    memory = memory or load_prompt_memory()
    project.setdefault("settings", {})
    project["settings"]["render_profile"] = memory.get("preferred_render_profile", "Cinematic")
    project["settings"]["subtitle_style"] = memory.get("preferred_subtitle_style", "cinematic")
    project["settings"]["motion_style"] = memory.get("preferred_motion_style", "cinematic_drift")
    project["settings"]["color_profile"] = memory.get("preferred_color_profile", "film_look")
    project.setdefault("visual_identity", {})
    project["visual_identity"]["color_profile"] = memory.get("preferred_color_profile", "film_look")
    project["visual_identity"]["motion_style"] = memory.get("preferred_motion_style", "cinematic_drift")
    project["visual_identity"]["subtitle_style"] = memory.get("preferred_subtitle_style", "cinematic")
    project["visual_identity"]["prompt_rules"] = ", ".join(memory.get("prompt_keywords", []) or [])
    project["visual_identity"]["favorite_scene_tags"] = memory.get("favorite_scene_tags", [])
    return project
