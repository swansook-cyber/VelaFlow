from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.project_io import safe_name


ROOT = Path(__file__).resolve().parents[1]
LIBRARY_PATH = ROOT / "project_data" / "asset_library.json"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _load_library() -> Dict[str, Any]:
    try:
        return json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"items": []}


def save_asset_library(library: Dict[str, Any]) -> Dict[str, Any]:
    LIBRARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    LIBRARY_PATH.write_text(json.dumps(library, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "message": "Asset library saved", "data": {"path": str(LIBRARY_PATH)}, "error": ""}


def index_project_assets(project: Dict[str, Any]) -> Dict[str, Any]:
    assets = project.get("assets", {}) or {}
    storyboard = ((project.get("mv", {}) or {}).get("storyboard", []) or [])
    scenes = {str(scene.get("scene") or index + 1): scene for index, scene in enumerate(storyboard)}
    rows: List[Dict[str, Any]] = []
    title = project.get("title", "project")

    for scene_id, image_path in (assets.get("approved_images", {}) or {}).items():
        scene = scenes.get(str(scene_id), {})
        rows.append(_asset_row("approved_image", title, scene_id, image_path, scene))
    for scene_id, image_path in (assets.get("images", {}) or {}).items():
        scene = scenes.get(str(scene_id), {})
        rows.append(_asset_row("generated_image", title, scene_id, image_path, scene))
    for scene_id, video_path in (assets.get("videos", {}) or {}).items():
        scene = scenes.get(str(scene_id), {})
        rows.append(_asset_row("video_slot", title, scene_id, video_path, scene))
    for scene_id, versions in (assets.get("image_versions", {}) or {}).items():
        scene = scenes.get(str(scene_id), {})
        for version in versions or []:
            row = _asset_row("image_version", title, scene_id, version.get("path", ""), scene)
            row["prompt"] = version.get("prompt", "")
            row["version"] = version.get("version", "")
            rows.append(row)
    for item in reusable_project_items(project):
        rows.append(item)

    return {"ok": True, "message": "Project assets indexed", "data": {"items": rows}, "error": ""}


def _asset_row(kind: str, project_title: str, scene_id: str, path_value: str, scene: Dict[str, Any]) -> Dict[str, Any]:
    path = Path(str(path_value)) if path_value else Path()
    return {
        "id": f"{safe_name(project_title)}:{kind}:{scene_id}:{path.name}",
        "kind": kind,
        "project": project_title,
        "scene_id": str(scene_id),
        "path": str(path_value or ""),
        "exists": bool(path_value and path.exists()),
        "mood": scene.get("emotion", ""),
        "color": scene.get("lighting", "") or scene.get("color_profile", ""),
        "genre": scene.get("genre", ""),
        "emotion": scene.get("emotion", ""),
        "camera": scene.get("camera", ""),
        "prompt": scene.get("image_prompt") or scene.get("expanded_prompt") or "",
        "favorite": False,
        "created_at": _now(),
    }


def reusable_project_items(project: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    title = project.get("title", "project")
    character = project.get("character", {}) or {}
    if any(character.get(key) for key in ["name", "gender", "hair", "outfit", "mood", "reference_notes"]):
        rows.append(
            {
                "id": f"{safe_name(title)}:character:{character.get('name','lead')}",
                "kind": "favorite_character",
                "project": title,
                "scene_id": "",
                "path": character.get("reference_image_path", ""),
                "exists": bool(character.get("reference_image_path") and Path(character.get("reference_image_path")).exists()),
                "mood": character.get("mood", ""),
                "color": "",
                "genre": "",
                "emotion": character.get("mood", ""),
                "camera": "",
                "prompt": character.get("reference_notes", ""),
                "favorite": True,
                "created_at": _now(),
            }
        )
    song = project.get("song", {}) or {}
    hook = song.get("selected_hook") or song.get("tiktok_clip_cut_recommendation") or ""
    if hook:
        rows.append(
            {
                "id": f"{safe_name(title)}:hook",
                "kind": "reusable_hook",
                "project": title,
                "scene_id": "",
                "path": "",
                "exists": False,
                "mood": "",
                "color": "",
                "genre": song.get("genre", ""),
                "emotion": "hook",
                "camera": "",
                "prompt": json.dumps(hook, ensure_ascii=False) if not isinstance(hook, str) else hook,
                "favorite": True,
                "created_at": _now(),
            }
        )
    return rows


def update_library_from_project(project: Dict[str, Any]) -> Dict[str, Any]:
    library = _load_library()
    existing = {item.get("id"): item for item in library.get("items", [])}
    indexed = index_project_assets(project)["data"]["items"]
    for item in indexed:
        existing[item["id"]] = {**existing.get(item["id"], {}), **item}
    library["items"] = sorted(existing.values(), key=lambda item: item.get("created_at", ""), reverse=True)
    result = save_asset_library(library)
    result["data"]["count"] = len(library["items"])
    return result


def search_asset_library(query: str = "", mood: str = "", color: str = "", genre: str = "", emotion: str = "") -> List[Dict[str, Any]]:
    items = _load_library().get("items", []) or []
    terms = [value.lower().strip() for value in [query, mood, color, genre, emotion] if value and value.strip()]
    if not terms:
        return items
    filtered = []
    for item in items:
        haystack = " ".join(str(item.get(key, "") or "") for key in ["kind", "project", "mood", "color", "genre", "emotion", "camera", "prompt"]).lower()
        if all(term in haystack for term in terms):
            filtered.append(item)
    return filtered


def export_asset_library(output_dir: str | Path | None = None) -> Dict[str, Any]:
    output = Path(output_dir) if output_dir else ROOT / "outputs" / "asset_library"
    output.mkdir(parents=True, exist_ok=True)
    target = output / f"asset_library_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    data = _load_library()
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "message": "Asset library exported", "data": {"path": str(target), "count": len(data.get("items", []))}, "error": ""}


def import_asset_library(source_path: str | Path) -> Dict[str, Any]:
    source = Path(source_path)
    if not source.exists():
        return {"ok": False, "message": "Asset library import source missing", "data": {}, "error": "missing_source"}
    imported = json.loads(source.read_text(encoding="utf-8"))
    library = _load_library()
    existing = {item.get("id"): item for item in library.get("items", [])}
    for item in imported.get("items", []) or []:
        existing[item.get("id")] = item
    library["items"] = list(existing.values())
    save_asset_library(library)
    return {"ok": True, "message": "Asset library imported", "data": {"count": len(library["items"])}, "error": ""}


def copy_asset_to_project(item: Dict[str, Any], project: Dict[str, Any], target_scene_id: str) -> Dict[str, Any]:
    path_value = item.get("path", "")
    if not path_value or not Path(path_value).exists():
        return {"ok": False, "message": "Reusable asset path is missing", "data": {}, "error": "missing_asset"}
    project_name = safe_name(project.get("title", "project"))
    target_dir = ROOT / "outputs" / "reused_assets" / project_name
    target_dir.mkdir(parents=True, exist_ok=True)
    source = Path(path_value)
    target = target_dir / f"scene_{str(target_scene_id).zfill(2)}_{source.name}"
    shutil.copy2(source, target)
    project.setdefault("assets", {}).setdefault("approved_images", {})[str(target_scene_id)] = str(target)
    return {"ok": True, "message": "Asset reused for project scene", "data": {"path": str(target), "scene_id": str(target_scene_id)}, "error": ""}
