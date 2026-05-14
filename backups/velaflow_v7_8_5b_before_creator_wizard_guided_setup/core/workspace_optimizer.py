from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.asset_manager import format_bytes
from core.project_io import safe_name


ROOT = Path(__file__).resolve().parents[1]
THUMBNAIL_CACHE = ROOT / "outputs" / "cache" / "thumbnails"


def workspace_performance_report(project: Dict[str, Any]) -> Dict[str, Any]:
    title = safe_name(project.get("title", "project"))
    roots = [
        ROOT / "outputs" / "renders" / title,
        ROOT / "outputs" / "generated_images" / title,
        ROOT / "outputs" / "generated_videos" / title,
        ROOT / "outputs" / "cache",
        ROOT / "outputs" / "previews",
    ]
    rows: List[Dict[str, Any]] = []
    for root in roots:
        count = 0
        size = 0
        if root.exists():
            for item in root.rglob("*"):
                if item.is_file():
                    count += 1
                    size += item.stat().st_size
        rows.append({"path": str(root), "files": count, "bytes": size, "size": format_bytes(size), "exists": root.exists()})
    total = sum(row["bytes"] for row in rows)
    return {"ok": True, "message": "Workspace performance report ready", "data": {"total_bytes": total, "total_size": format_bytes(total), "areas": rows}, "error": ""}


def build_thumbnail_index(project: Dict[str, Any]) -> Dict[str, Any]:
    THUMBNAIL_CACHE.mkdir(parents=True, exist_ok=True)
    assets = project.get("assets", {}) or {}
    images = {}
    images.update(assets.get("images", {}) or {})
    images.update(assets.get("approved_images", {}) or {})
    index = []
    for scene_id, path_value in images.items():
        source = Path(str(path_value))
        if not source.exists():
            continue
        index.append(
            {
                "scene_id": str(scene_id),
                "source": str(source),
                "cache_key": f"{safe_name(project.get('title','project'))}_{scene_id}_{int(source.stat().st_mtime)}",
                "size": format_bytes(source.stat().st_size),
            }
        )
    index_path = THUMBNAIL_CACHE / f"{safe_name(project.get('title','project'))}_thumbnail_index.json"
    index_path.write_text(json.dumps({"created_at": datetime.now().isoformat(timespec="seconds"), "items": index}, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "message": "Thumbnail cache index updated", "data": {"path": str(index_path), "count": len(index)}, "error": ""}


def cleanup_old_cache(ttl_days: int = 14) -> Dict[str, Any]:
    cache_root = ROOT / "outputs" / "cache"
    if not cache_root.exists():
        return {"ok": True, "message": "Cache folder is empty", "data": {"removed": []}, "error": ""}
    cutoff = time.time() - max(1, int(ttl_days)) * 86400
    removed = []
    for path in cache_root.rglob("*"):
        if path.is_file() and path.stat().st_mtime < cutoff:
            size = path.stat().st_size
            path.unlink()
            removed.append({"path": str(path), "bytes": size, "size": format_bytes(size)})
    return {"ok": True, "message": f"Removed {len(removed)} old cache files", "data": {"removed": removed}, "error": ""}
