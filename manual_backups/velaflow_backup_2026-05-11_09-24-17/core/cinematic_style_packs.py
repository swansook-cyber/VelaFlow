from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
STYLE_PACK_PATH = ROOT / "config" / "presets" / "cinematic_style_packs.json"


def list_cinematic_style_packs() -> List[Dict[str, Any]]:
    try:
        return json.loads(STYLE_PACK_PATH.read_text(encoding="utf-8")).get("packs", [])
    except Exception:
        return []


def get_cinematic_style_pack(name: str) -> Dict[str, Any]:
    return next((pack for pack in list_cinematic_style_packs() if pack.get("name") == name), {})


def apply_cinematic_style_pack(project: Dict[str, Any], pack_name: str) -> Dict[str, Any]:
    pack = get_cinematic_style_pack(pack_name)
    if not pack:
        return {"ok": False, "message": "Style pack not found", "data": {}, "error": "missing_pack"}
    project.setdefault("settings", {})
    project["settings"]["cinematic_style_pack"] = pack_name
    project["settings"]["color_profile"] = pack.get("color_profile", project["settings"].get("color_profile", "film_look"))
    project["settings"]["motion_style"] = pack.get("motion_style", project["settings"].get("motion_style", "cinematic_drift"))
    project["settings"]["subtitle_style"] = pack.get("subtitle_style", project["settings"].get("subtitle_style", "cinematic"))
    project.setdefault("visual_identity", {})
    project["visual_identity"]["cinematic_style_pack"] = pack
    for scene in project.setdefault("mv", {}).setdefault("storyboard", []):
        scene["lighting"] = scene.get("lighting") or pack.get("lighting", "")
        scene["camera_language"] = scene.get("camera_language") or pack.get("camera_language", "")
        prompt = scene.get("image_prompt") or scene.get("expanded_prompt") or ""
        suffix = pack.get("prompt_suffix", "")
        if suffix and suffix not in prompt:
            scene["image_prompt"] = f"{prompt}, {suffix}".strip(", ")
    return {"ok": True, "message": f"Applied cinematic style pack: {pack_name}", "data": {"project": project, "pack": pack}, "error": ""}
