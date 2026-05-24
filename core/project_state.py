from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECTS_ROOT = Path("projects")
PROJECT_GLOBAL_FOLDERS = ["assets", "exports", "history"]
PROJECT_SUBFOLDERS = ["outputs", "assets", "exports", "history"]


def utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def sanitize_project_name(name: str) -> str:
    text = str(name or "").strip() or "New_Project"
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", text)
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"_+", "_", text).strip("._ ")
    return text[:80] or "New_Project"


def ensure_workspace_root(root: Path = PROJECTS_ROOT) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for folder in PROJECT_GLOBAL_FOLDERS:
        (root / folder).mkdir(parents=True, exist_ok=True)
    return root


def project_path(project_name: str, root: Path = PROJECTS_ROOT) -> Path:
    return ensure_workspace_root(root) / sanitize_project_name(project_name)


def ensure_project_structure(project_name: str, root: Path = PROJECTS_ROOT) -> Path:
    folder = project_path(project_name, root)
    folder.mkdir(parents=True, exist_ok=True)
    for subfolder in PROJECT_SUBFOLDERS:
        (folder / subfolder).mkdir(parents=True, exist_ok=True)
    return folder


def default_project_state(project_name: str) -> dict[str, Any]:
    now = utc_now()
    safe_name = sanitize_project_name(project_name)
    return {
        "project_name": safe_name,
        "display_name": str(project_name or safe_name).strip() or safe_name,
        "created_at": now,
        "updated_at": now,
        "archived": False,
        "user_goals": [],
        "generated_outputs": [],
        "workflow_history": [],
        "active_agents": [],
        "generated_files": [],
        "memory_summary": "",
        "execution_logs": [],
        "versions": [],
    }


def read_json_safe(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        if not path.exists():
            return dict(fallback)
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else dict(fallback)
    except Exception:
        return dict(fallback)


def write_json_safe(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
