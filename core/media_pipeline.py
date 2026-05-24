from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.project_state import ensure_project_structure, sanitize_project_name, utc_now


PIPELINE_STAGES = ["draft", "approved", "exported"]
PIPELINE_TYPES = ["storyboard", "cover", "mv", "release_package"]


def create_pipeline_item(project_name: str, pipeline_type: str, asset_id: str = "", title: str = "") -> dict[str, Any]:
    pipeline_type = pipeline_type if pipeline_type in PIPELINE_TYPES else "release_package"
    return {
        "pipeline_id": f"{pipeline_type}_{sanitize_project_name(title or asset_id or 'item')}_{utc_now().replace(':', '')}",
        "project_name": sanitize_project_name(project_name),
        "pipeline_type": pipeline_type,
        "asset_id": asset_id,
        "title": title or pipeline_type,
        "stage": "draft",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "history": [{"stage": "draft", "timestamp": utc_now()}],
    }


def transition_stage(item: dict[str, Any], new_stage: str) -> dict[str, Any]:
    if new_stage not in PIPELINE_STAGES:
        new_stage = "draft"
    item = dict(item or {})
    item["stage"] = new_stage
    item["updated_at"] = utc_now()
    item.setdefault("history", []).append({"stage": new_stage, "timestamp": item["updated_at"]})
    return item


def save_pipeline(project_name: str, items: list[dict[str, Any]]) -> Path:
    folder = ensure_project_structure(project_name)
    path = folder / "outputs" / "media_pipeline.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"items": items, "updated_at": utc_now()}, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_pipeline(project_name: str) -> list[dict[str, Any]]:
    path = ensure_project_structure(project_name) / "outputs" / "media_pipeline.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("items", []) if isinstance(data, dict) else []
    except Exception:
        return []


def storyboard_pipeline(project_name: str, storyboard_id: str) -> dict[str, Any]:
    return create_pipeline_item(project_name, "storyboard", storyboard_id, "Storyboard")


def cover_pipeline(project_name: str, cover_asset_id: str) -> dict[str, Any]:
    return create_pipeline_item(project_name, "cover", cover_asset_id, "Cover")


def mv_pipeline(project_name: str, storyboard_id: str) -> dict[str, Any]:
    return create_pipeline_item(project_name, "mv", storyboard_id, "Music Video")


def release_package_pipeline(project_name: str, package_id: str) -> dict[str, Any]:
    return create_pipeline_item(project_name, "release_package", package_id, "Release Package")
