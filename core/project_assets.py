from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.asset_manager import list_assets, register_asset
from core.project_state import ensure_project_structure, sanitize_project_name, utc_now


def link_project_asset(project_name: str, asset_id: str, relation_type: str, target: str) -> dict[str, Any]:
    folder = ensure_project_structure(project_name)
    path = folder / "outputs" / "asset_links.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        data = {"links": []}
    link = {
        "project_name": sanitize_project_name(project_name),
        "asset_id": asset_id,
        "relation_type": relation_type,
        "target": target,
        "created_at": utc_now(),
    }
    data.setdefault("links", []).append(link)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return link


def get_project_asset_links(project_name: str) -> list[dict[str, Any]]:
    path = ensure_project_structure(project_name) / "outputs" / "asset_links.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("links", []) if isinstance(data, dict) else []
    except Exception:
        return []


def cover_prompt_history(project_name: str, prompt: str, linked_agent: str = "MV Agent") -> dict[str, Any]:
    folder = ensure_project_structure(project_name) / "assets" / "covers"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"cover_prompt_{len(list(folder.glob('cover_prompt_*.txt'))) + 1}.txt"
    path.write_text(str(prompt or ""), encoding="utf-8-sig")
    asset = register_asset(path, "covers", project_name, "cover_prompt", linked_agent, ["cover", "prompt"])
    link_project_asset(project_name, asset["asset_id"], "cover_linked_to_release", "release")
    return asset


def approve_cover(project_name: str, asset_id: str) -> dict[str, Any]:
    folder = ensure_project_structure(project_name)
    path = folder / "outputs" / "approved_cover.json"
    data = {"project_name": sanitize_project_name(project_name), "approved_cover_asset_id": asset_id, "updated_at": utc_now()}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def project_asset_summary(project_name: str) -> dict[str, Any]:
    assets = list_assets(project_name)
    links = get_project_asset_links(project_name)
    by_type: dict[str, int] = {}
    for asset in assets:
        by_type[asset.get("asset_type", "file")] = by_type.get(asset.get("asset_type", "file"), 0) + 1
    return {"project_name": sanitize_project_name(project_name), "asset_count": len(assets), "by_type": by_type, "link_count": len(links)}
