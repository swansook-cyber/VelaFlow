import json
import re
import shutil
import time
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

from core.project_state import ensure_workspace_root, sanitize_project_name

from core.project_io import safe_name
from core.paths import resolve_project_folder


ROOT = Path(__file__).resolve().parents[1]
PROJECTS_ROOT = ROOT / "projects"
GLOBAL_ASSET_INDEX = PROJECTS_ROOT / "assets" / "asset_index.json"


def _asset_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def safe_asset_filename(filename: str) -> str:
    text = str(filename or "asset").strip()
    stem = Path(text).stem or "asset"
    suffix = Path(text).suffix.lower()
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", stem)
    stem = re.sub(r"\s+", "_", stem)
    stem = re.sub(r"_+", "_", stem).strip("._ ")[:80] or "asset"
    return f"{stem}{suffix}"


def _load_asset_index(index_path: Path = GLOBAL_ASSET_INDEX) -> dict[str, Any]:
    try:
        if index_path.exists():
            with index_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                data.setdefault("assets", [])
                return data
    except Exception:
        pass
    return {"assets": []}


def _save_asset_index(index: dict[str, Any], index_path: Path = GLOBAL_ASSET_INDEX) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("w", encoding="utf-8") as handle:
        json.dump(index, handle, ensure_ascii=False, indent=2)


def generate_asset_metadata(
    path: str | Path,
    asset_type: str = "file",
    project_name: str | None = None,
    generation_source: str = "manual",
    linked_agent: str = "",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    file_path = Path(path)
    return {
        "asset_id": f"{sanitize_project_name(project_name or 'global')}_{safe_asset_filename(file_path.name)}_{time.time_ns()}",
        "filename": safe_asset_filename(file_path.name),
        "path": str(file_path),
        "asset_type": asset_type,
        "project_name": sanitize_project_name(project_name or ""),
        "created_at": _asset_now(),
        "updated_at": _asset_now(),
        "generation_source": generation_source,
        "linked_agent": linked_agent,
        "tags": tags or [],
        "exists": file_path.exists(),
        "bytes": file_path.stat().st_size if file_path.is_file() else 0,
        "status": "draft",
    }


def register_asset(
    path: str | Path,
    asset_type: str = "file",
    project_name: str | None = None,
    generation_source: str = "manual",
    linked_agent: str = "",
    tags: list[str] | None = None,
    index_path: str | Path | None = None,
) -> dict[str, Any]:
    ensure_workspace_root(PROJECTS_ROOT)
    index_file = Path(index_path) if index_path else GLOBAL_ASSET_INDEX
    metadata = generate_asset_metadata(path, asset_type, project_name, generation_source, linked_agent, tags)
    index = _load_asset_index(index_file)
    index["assets"] = [item for item in index.get("assets", []) if item.get("asset_id") != metadata["asset_id"]]
    index["assets"].append(metadata)
    _save_asset_index(index, index_file)
    return metadata


def import_asset(
    source_path: str | Path,
    asset_type: str,
    project_name: str,
    generation_source: str = "import",
    linked_agent: str = "",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    source = Path(source_path)
    safe_project = sanitize_project_name(project_name)
    target_dir = PROJECTS_ROOT / safe_project / "assets" / asset_type
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / safe_asset_filename(source.name)
    if source.is_file():
        shutil.copy2(source, target)
    else:
        target.write_text("", encoding="utf-8")
    return register_asset(target, asset_type, safe_project, generation_source, linked_agent, tags)


def list_assets(project_name: str | None = None, asset_type: str | None = None, index_path: str | Path | None = None) -> list[dict[str, Any]]:
    index_file = Path(index_path) if index_path else GLOBAL_ASSET_INDEX
    index = _load_asset_index(index_file)
    safe_project = sanitize_project_name(project_name or "") if project_name else ""
    assets = []
    for item in index.get("assets", []):
        if safe_project and item.get("project_name") != safe_project:
            continue
        if asset_type and item.get("asset_type") != asset_type:
            continue
        if item.get("path") and not Path(item["path"]).exists():
            item = {**item, "exists": False}
        assets.append(item)
    return assets


def attach_asset_to_project(asset_id: str, project_name: str, relation: str = "reference", index_path: str | Path | None = None) -> dict[str, Any]:
    index_file = Path(index_path) if index_path else GLOBAL_ASSET_INDEX
    index = _load_asset_index(index_file)
    safe_project = sanitize_project_name(project_name)
    for item in index.get("assets", []):
        if item.get("asset_id") == asset_id:
            item["project_name"] = safe_project
            item["relation"] = relation
            item["updated_at"] = _asset_now()
            _save_asset_index(index, index_file)
            return item
    return {"asset_id": asset_id, "project_name": safe_project, "relation": relation, "missing": True}


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
