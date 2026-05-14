from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from core.project_io import new_project


def open_project_safe_mode(path: str | Path) -> Dict[str, Any]:
    source = Path(path)
    if not source.exists():
        return {"ok": False, "message": "Project file not found", "data": {}, "error": "missing_project"}
    try:
        project = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(project, dict):
            raise ValueError("project is not a JSON object")
        project.setdefault("title", source.stem)
        project.setdefault("song", {})
        project.setdefault("mv", {})
        project.setdefault("assets", {})
        project.setdefault("settings", {})
        project["safe_mode_loaded_from"] = str(source)
        return {"ok": True, "message": "Project opened in safe mode", "data": {"project": project}, "error": ""}
    except Exception as error:
        backup = source.with_suffix(f".broken_{datetime.now().strftime('%Y%m%d_%H%M%S')}{source.suffix}")
        shutil.copy2(source, backup)
        project = new_project(source.stem)
        project["safe_mode_error"] = str(error)
        project["safe_mode_backup"] = str(backup)
        return {"ok": True, "message": "Corrupted project opened as safe placeholder", "data": {"project": project, "backup": str(backup)}, "error": str(error)}
