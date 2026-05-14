import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from core.project_io import safe_name
from core.paths import resolve_project_folder


ROOT = Path(__file__).resolve().parents[1]


def next_version_path(folder: Path, stem: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    versions = []
    for path in folder.glob(f"{stem}_v*.json"):
        try:
            versions.append(int(path.stem.rsplit("_v", 1)[1]))
        except Exception:
            pass
    version = (max(versions) if versions else 0) + 1
    return folder / f"{stem}_v{version:03d}.json"


def save_project_version(project: Dict[str, Any], label: str = "snapshot") -> Dict[str, Any]:
    project_name = safe_name(project.get("title", "project"))
    folder = resolve_project_folder(project_name, project.get("workflow_type") or project.get("project_type")) / "versions"
    path = next_version_path(folder, label)
    payload = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "label": label,
        "project_title": project.get("title", ""),
        "project_version": project.get("version", ""),
        "storyboard": ((project.get("mv", {}) or {}).get("storyboard", []) or []),
        "song": project.get("song", {}),
        "assets": project.get("assets", {}),
        "settings": project.get("settings", {}),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "message": "Project version saved", "data": {"path": str(path)}, "error": ""}
