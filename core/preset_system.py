from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
PRESET_DIR = ROOT / "config" / "presets"


def _load_json(name: str, default: Dict[str, Any]) -> Dict[str, Any]:
    path = PRESET_DIR / name
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def list_project_templates() -> List[Dict[str, Any]]:
    return _load_json("project_templates.json", {"templates": []}).get("templates", [])


def get_project_template(name: str) -> Dict[str, Any]:
    return next((item for item in list_project_templates() if item.get("name") == name), {})


def list_preset_packs() -> List[Dict[str, Any]]:
    return _load_json("preset_packs.json", {"packs": []}).get("packs", [])


def get_preset_pack(name: str) -> Dict[str, Any]:
    return next((item for item in list_preset_packs() if item.get("name") == name), {})


def list_scene_presets() -> List[Dict[str, Any]]:
    return _load_json("scene_presets.json", {"scenes": []}).get("scenes", [])


def list_global_presets() -> Dict[str, Any]:
    return _load_json("global_presets.json", {})
