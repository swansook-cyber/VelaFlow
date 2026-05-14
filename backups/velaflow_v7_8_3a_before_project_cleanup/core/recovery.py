from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.project_io import new_project, safe_name


ROOT = Path(__file__).resolve().parents[1]
SESSION_PATH = ROOT / "project_data" / "last_session.json"


def save_last_session(project: Dict[str, Any], path: str | Path | None = None) -> Dict[str, Any]:
    target = Path(path) if path else SESSION_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "project_title": project.get("title", "project"),
        "project": project,
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "message": "Last session saved", "data": {"path": str(target)}, "error": ""}


def recover_last_session(path: str | Path | None = None) -> Dict[str, Any]:
    source = Path(path) if path else SESSION_PATH
    if not source.exists():
        return {"ok": False, "message": "No last session found", "data": {"project": None}, "error": "missing_session"}
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
        project = payload.get("project", {}) or {}
        if not isinstance(project, dict) or not project.get("title"):
            raise ValueError("last session project is invalid")
        return {"ok": True, "message": "Last session recovered", "data": {"project": project, "path": str(source)}, "error": ""}
    except Exception as error:
        broken = source.with_suffix(f".broken_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        shutil.copy2(source, broken)
        return {"ok": False, "message": "Last session is corrupted", "data": {"broken_backup": str(broken), "project": new_project(source.stem)}, "error": str(error)}


def detect_corrupted_project(path: str | Path) -> Dict[str, Any]:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
        ok = isinstance(payload, dict) and bool(payload.get("title"))
        return {"ok": ok, "message": "Project JSON valid" if ok else "Project JSON missing title", "data": {"path": str(source)}, "error": "" if ok else "invalid_project"}
    except Exception as error:
        return {"ok": False, "message": "Project JSON corrupted", "data": {"path": str(source)}, "error": str(error)}


def available_project_backups(project_title: str) -> List[Dict[str, Any]]:
    project_dir = ROOT / "project_data" / "projects" / safe_name(project_title)
    candidates = list((project_dir / "_backups").glob("*.json")) if (project_dir / "_backups").exists() else []
    candidates += list((project_dir / "_auto_backups").glob("*.json")) if (project_dir / "_auto_backups").exists() else []
    return [
        {"path": str(path), "modified_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")}
        for path in sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True)
    ]
