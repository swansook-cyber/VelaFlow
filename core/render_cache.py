from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from core.paths import workflow_project_root
from core.project_io import safe_name


CACHE_VERSION = "render_cache_v1"


def cache_fingerprint(*parts: Any) -> str:
    payload = json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def render_cache_dir(project_name: str, workflow_type: str, cache_key: str) -> Path:
    return workflow_project_root(workflow_type or "clips") / safe_name(project_name or "hook_clip") / "cache" / cache_key


def load_render_cache(project_name: str, workflow_type: str, cache_key: str) -> dict[str, Any]:
    folder = render_cache_dir(project_name, workflow_type, cache_key)
    manifest_path = folder / "cache_manifest.json"
    if not manifest_path.is_file():
        return {"ok": False, "message": "Cache miss", "data": {"cache_key": cache_key, "cache_dir": str(folder)}, "error": "cache_miss"}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ok": False, "message": "Cache manifest unreadable", "data": {"cache_key": cache_key, "cache_dir": str(folder)}, "error": str(exc)}
    required = manifest.get("required_files") or []
    missing = [path for path in required if not Path(path).is_file()]
    if missing:
        return {"ok": False, "message": "Cache stale", "data": {"cache_key": cache_key, "cache_dir": str(folder), "missing": missing}, "error": "cache_stale"}
    return {"ok": True, "message": "Cache hit", "data": {"cache_key": cache_key, "cache_dir": str(folder), "manifest": manifest}, "error": ""}


def save_render_cache(
    project_name: str,
    workflow_type: str,
    cache_key: str,
    *,
    scene_prompt_path: str = "",
    beat_timing_path: str = "",
    image_manifest_path: str = "",
    image_results: list[dict[str, Any]] | None = None,
    subtitle_path: str = "",
) -> dict[str, Any]:
    folder = render_cache_dir(project_name, workflow_type, cache_key)
    folder.mkdir(parents=True, exist_ok=True)
    copied: dict[str, str] = {}
    required_files: list[str] = []
    for label, source in {
        "scene_prompts": scene_prompt_path,
        "beat_timing": beat_timing_path,
        "image_manifest": image_manifest_path,
        "subtitles": subtitle_path,
    }.items():
        path = Path(str(source or ""))
        if path.is_file():
            target = folder / path.name
            shutil.copy2(path, target)
            copied[label] = str(target)
            required_files.append(str(target))
    cached_images = []
    for item in image_results or []:
        path = Path(str(item.get("path") or ""))
        if not path.is_file():
            continue
        scene_id = safe_name(str(item.get("scene_id") or path.stem or "scene"))
        target = folder / f"{scene_id}{path.suffix.lower() or '.jpg'}"
        shutil.copy2(path, target)
        cached_item = {**item, "path": str(target), "cached": True}
        cached_images.append(cached_item)
        required_files.append(str(target))
    manifest = {
        "cache_version": CACHE_VERSION,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "cache_key": cache_key,
        "cache_dir": str(folder),
        "files": copied,
        "image_results": cached_images,
        "required_files": required_files,
    }
    manifest_path = folder / "cache_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "message": "Render cache saved", "data": {"cache_key": cache_key, "cache_dir": str(folder), "manifest_path": str(manifest_path), "manifest": manifest}, "error": ""}


def copy_cached_assets_to_project(cache_manifest: dict[str, Any], project_name: str, workflow_type: str) -> dict[str, Any]:
    project_dir = workflow_project_root(workflow_type or "clips") / safe_name(project_name or "hook_clip")
    exports_dir = project_dir / "exports"
    images_dir = project_dir / "images"
    exports_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)
    files = cache_manifest.get("files") or {}
    copied_files: dict[str, str] = {}
    for label, source in files.items():
        source_path = Path(str(source or ""))
        if not source_path.is_file():
            continue
        target = exports_dir / source_path.name
        shutil.copy2(source_path, target)
        copied_files[label] = str(target)
    image_results = []
    for item in cache_manifest.get("image_results") or []:
        source_path = Path(str(item.get("path") or ""))
        if not source_path.is_file():
            continue
        scene_id = safe_name(str(item.get("scene_id") or source_path.stem or "scene"))
        target = images_dir / f"{scene_id}{source_path.suffix.lower() or '.jpg'}"
        shutil.copy2(source_path, target)
        image_results.append({**item, "path": str(target), "cache_hit": True})
    return {"ok": True, "message": "Cached assets restored", "data": {"files": copied_files, "image_results": image_results}, "error": ""}
