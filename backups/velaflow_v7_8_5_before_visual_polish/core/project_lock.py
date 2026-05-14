from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from core.project_io import safe_name


ROOT = Path(__file__).resolve().parents[1]
LOCK_ROOT = ROOT / "project_data" / "locks"


def lock_path(project_title: str) -> Path:
    return LOCK_ROOT / f"{safe_name(project_title)}.lock.json"


def acquire_project_lock(project: Dict[str, Any], owner: str = "local_app", force: bool = False) -> Dict[str, Any]:
    LOCK_ROOT.mkdir(parents=True, exist_ok=True)
    path = lock_path(project.get("title", "project"))
    if path.exists() and not force:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            payload = {"owner": "unknown"}
        return {"ok": False, "message": "Project lock already exists", "data": {"path": str(path), "lock": payload}, "error": "locked"}
    payload = {"project": project.get("title", "project"), "owner": owner, "pid": os.getpid(), "locked_at": datetime.now().isoformat(timespec="seconds")}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    project.setdefault("runtime", {})["lock_path"] = str(path)
    return {"ok": True, "message": "Project lock acquired", "data": {"path": str(path), "lock": payload}, "error": ""}


def release_project_lock(project: Dict[str, Any]) -> Dict[str, Any]:
    path = Path((project.get("runtime", {}) or {}).get("lock_path") or lock_path(project.get("title", "project")))
    if path.exists():
        path.unlink()
    return {"ok": True, "message": "Project lock released", "data": {"path": str(path)}, "error": ""}


def project_lock_status(project: Dict[str, Any]) -> Dict[str, Any]:
    path = lock_path(project.get("title", "project"))
    if not path.exists():
        return {"ok": True, "message": "Project is unlocked", "data": {"locked": False, "path": str(path)}, "error": ""}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        payload = {"corrupted": True}
    return {"ok": True, "message": "Project is locked", "data": {"locked": True, "path": str(path), "lock": payload}, "error": ""}
