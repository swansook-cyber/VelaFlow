from __future__ import annotations

import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from core.paths import workflow_project_root
from core.project_io import safe_name


BROKEN_SCENE_MIN_BYTES = 100 * 1024


def _project_dir(project_name: str, workflow_type: str = "song") -> Path:
    return workflow_project_root(workflow_type or "song") / safe_name(project_name or "project")


def _is_inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except Exception:
        return False


def format_size(num_bytes: int | float) -> str:
    value = float(num_bytes or 0)
    for unit in ["B", "KB", "MB", "GB"]:
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} GB"


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except Exception:
                continue
    return total


def _latest_successful_render(root: Path) -> str:
    candidates = []
    for pattern in ["exports/final_hook_clip.mp4", "exports/versions/final_hook_clip_v*.mp4", "exports/final/final_hook_clip.mp4"]:
        candidates.extend(root.glob(pattern))
    valid = [path for path in candidates if path.is_file() and path.stat().st_size > 1024]
    if not valid:
        return ""
    latest = max(valid, key=lambda path: path.stat().st_mtime)
    return str(latest)


def project_storage_summary(project_name: str, workflow_type: str = "song") -> dict[str, Any]:
    root = _project_dir(project_name, workflow_type)
    cache_root = root / "cache"
    scenes_root = root / "scenes"
    versions_root = root / "exports" / "versions"
    broken_scene_clips = []
    if scenes_root.exists():
        for path in scenes_root.glob("scene_*.mp4"):
            if path.is_file() and path.stat().st_size < BROKEN_SCENE_MIN_BYTES:
                broken_scene_clips.append(str(path))
    return {
        "ok": True,
        "message": "Project storage summary",
        "data": {
            "project_dir": str(root),
            "storage_bytes": _dir_size(root),
            "storage_label": format_size(_dir_size(root)),
            "cache_count": len([path for path in cache_root.iterdir() if path.is_dir()]) if cache_root.exists() else 0,
            "version_count": len(list(versions_root.glob("final_hook_clip_v*.mp4"))) if versions_root.exists() else 0,
            "broken_scene_clips": broken_scene_clips,
            "latest_successful_render": _latest_successful_render(root),
            "cache_health": "ok" if not broken_scene_clips else "needs cleanup",
        },
        "error": "",
    }


def cleanup_project_storage(
    project_name: str,
    workflow_type: str = "song",
    *,
    keep_versions: int = 3,
    max_cache_age_days: int = 7,
    dry_run: bool = False,
) -> dict[str, Any]:
    root = _project_dir(project_name, workflow_type)
    root.mkdir(parents=True, exist_ok=True)
    deleted: list[str] = []
    skipped: list[str] = []

    def remove_path(path: Path) -> None:
        if not _is_inside(path, root):
            skipped.append(str(path))
            return
        deleted.append(str(path))
        if dry_run:
            return
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)

    for pattern in ["**/*.tmp", "**/*.part", "**/*_tmp.mp4", "**/*.corrupt"]:
        for path in root.glob(pattern):
            if path.is_file():
                remove_path(path)

    scenes_root = root / "scenes"
    if scenes_root.exists():
        for path in scenes_root.glob("scene_*.mp4"):
            if path.is_file() and path.stat().st_size < BROKEN_SCENE_MIN_BYTES:
                remove_path(path)

    cutoff = datetime.now() - timedelta(days=max(1, int(max_cache_age_days or 7)))
    cache_root = root / "cache"
    if cache_root.exists():
        cache_dirs = sorted([path for path in cache_root.iterdir() if path.is_dir()], key=lambda item: item.stat().st_mtime, reverse=True)
        for path in cache_dirs[5:]:
            try:
                modified = datetime.fromtimestamp(path.stat().st_mtime)
            except Exception:
                modified = cutoff - timedelta(days=1)
            if modified < cutoff:
                remove_path(path)

    versions_root = root / "exports" / "versions"
    if versions_root.exists():
        version_files = sorted(versions_root.glob("final_hook_clip_v*.mp4"), key=lambda item: item.stat().st_mtime, reverse=True)
        for video_path in version_files[max(0, keep_versions):]:
            remove_path(video_path)
            manifest = versions_root / video_path.name.replace("final_hook_clip_", "clip_version_").replace(".mp4", ".json")
            if manifest.is_file():
                remove_path(manifest)

    summary = project_storage_summary(project_name, workflow_type)["data"]
    return {
        "ok": True,
        "message": "Cleanup complete" if not dry_run else "Cleanup preview ready",
        "data": {"deleted": deleted, "skipped": skipped, "dry_run": dry_run, "summary": summary},
        "error": "",
    }
