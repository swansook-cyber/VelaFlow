import shutil
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List

from core.project_io import safe_name
from core.paths import resolve_project_folder


ROOT = Path(__file__).resolve().parents[1]


def _size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def format_bytes(size: int) -> str:
    value = float(size)
    for unit in ["B", "KB", "MB", "GB"]:
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def project_asset_summary(project: Dict[str, Any]) -> Dict[str, Any]:
    title = safe_name(project.get("title", "project"))
    paths = {
        "generated_images": ROOT / "outputs" / "generated_images" / title,
        "generated_videos": ROOT / "outputs" / "generated_videos" / title,
        "renders": ROOT / "outputs" / "renders" / title,
        "project_data": resolve_project_folder(title, project.get("workflow_type") or project.get("project_type")),
        "image_cache": ROOT / "outputs" / "cache" / "images",
        "jobs": ROOT / "outputs" / "jobs",
    }
    rows: List[Dict[str, Any]] = []
    total = 0
    for label, path in paths.items():
        size = _size(path)
        total += size
        rows.append({"area": label, "path": str(path), "bytes": size, "size": format_bytes(size), "exists": path.exists()})
    return {"project": title, "total_bytes": total, "total_size": format_bytes(total), "areas": rows}


def clear_rejected_images(project: Dict[str, Any]) -> Dict[str, Any]:
    assets = project.get("assets", {}) or {}
    approved = set(str(path) for path in (assets.get("approved_images", {}) or {}).values())
    rejected = assets.get("rejected_images", {}) or {}
    removed = []
    for path_value in list(rejected.values()):
        path = Path(path_value)
        if str(path) in approved:
            continue
        if path.is_file():
            path.unlink()
            removed.append(str(path))
    assets["rejected_images"] = {}
    return {"ok": True, "message": f"Removed {len(removed)} rejected images", "data": {"removed": removed}, "error": ""}


def clear_image_cache() -> Dict[str, Any]:
    path = ROOT / "outputs" / "cache" / "images"
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return {"ok": True, "message": "Image cache cleared", "data": {"path": str(path)}, "error": ""}


def clear_temp_renders(project: Dict[str, Any]) -> Dict[str, Any]:
    render_root = ROOT / "outputs" / "renders" / safe_name(project.get("title", "project"))
    removed = []
    if render_root.exists():
        for temp in render_root.rglob("temp"):
            if temp.is_dir():
                shutil.rmtree(temp)
                removed.append(str(temp))
    return {"ok": True, "message": f"Removed {len(removed)} temp render folders", "data": {"removed": removed}, "error": ""}


def prune_scene_cache(ttl_days: int = 14) -> Dict[str, Any]:
    cache_root = ROOT / "outputs" / "renders" / "_scene_cache"
    if not cache_root.exists():
        return {"ok": True, "message": "Scene cache is empty", "data": {"removed": []}, "error": ""}
    cutoff = time.time() - max(1, int(ttl_days)) * 86400
    removed = []
    for path in cache_root.rglob("*.mp4"):
        if path.stat().st_mtime < cutoff:
            path.unlink()
            removed.append(str(path))
    return {"ok": True, "message": f"Pruned {len(removed)} cached scene clips", "data": {"removed": removed, "ttl_days": ttl_days}, "error": ""}


def prune_render_history(project: Dict[str, Any], keep_latest: int = 8) -> Dict[str, Any]:
    render_root = ROOT / "outputs" / "renders" / safe_name(project.get("title", "project"))
    if not render_root.exists():
        return {"ok": True, "message": "No render history", "data": {"removed": []}, "error": ""}
    renders = sorted([path for path in render_root.iterdir() if path.is_dir()], key=lambda path: path.stat().st_mtime, reverse=True)
    removed = []
    for path in renders[max(1, int(keep_latest)) :]:
        shutil.rmtree(path)
        removed.append(str(path))
    return {"ok": True, "message": f"Pruned {len(removed)} old renders", "data": {"removed": removed, "keep_latest": keep_latest}, "error": ""}


def archive_project(project: Dict[str, Any], output_dir: str | Path | None = None) -> Dict[str, Any]:
    output = Path(output_dir) if output_dir else ROOT / "outputs" / "archives"
    output.mkdir(parents=True, exist_ok=True)
    title = safe_name(project.get("title", "project"))
    archive_path = output / f"{title}_archive.zip"
    project_paths = [
        resolve_project_folder(title, project.get("workflow_type") or project.get("project_type")),
        ROOT / "outputs" / "generated_images" / title,
        ROOT / "outputs" / "generated_videos" / title,
        ROOT / "outputs" / "renders" / title,
    ]
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for base in project_paths:
            if not base.exists():
                continue
            for file in base.rglob("*"):
                if file.is_file():
                    zf.write(file, file.relative_to(ROOT))
    return {"ok": True, "message": "Project archived", "data": {"archive_path": str(archive_path)}, "error": ""}
