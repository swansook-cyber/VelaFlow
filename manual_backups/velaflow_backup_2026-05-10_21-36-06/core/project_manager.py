from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.branding import DEFAULT_ARTIST
from core.project_io import new_project, safe_name, save_project_folder


ROOT = Path(__file__).resolve().parents[1]
PROJECTS_ROOT = ROOT / "project_data" / "projects"
ARCHIVE_ROOT = ROOT / "project_data" / "archive"
DELETED_BACKUPS_ROOT = ROOT / "project_data" / "deleted_backups"
PREFERENCES_PATH = ROOT / "config" / "user_preferences.json"
WORKFLOW_MODES = ["Full Pipeline", "Song Studio Only"]

PROTECTED_ROOTS = {
    (ROOT / "backups").resolve(),
    (ROOT / "config").resolve(),
    (ROOT / "docs").resolve(),
    (ROOT / "app").resolve(),
    (ROOT / "core").resolve(),
    (ROOT / "providers").resolve(),
    (ROOT / "tests").resolve(),
}


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _read_json(path: Path, default: Any) -> Any:
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def sanitize_project_name(name: str) -> str:
    return safe_name(name or "untitled_project")


def _active_path(project_name: str) -> Path:
    return PROJECTS_ROOT / sanitize_project_name(project_name)


def _is_safe_active_project_path(path: Path) -> bool:
    resolved = path.resolve()
    projects_root = PROJECTS_ROOT.resolve()
    if not path.exists() or not path.is_dir():
        return False
    if resolved.parent != projects_root:
        return False
    if resolved in PROTECTED_ROOTS:
        return False
    return True


def project_exists(name: str) -> bool:
    return _active_path(name).is_dir()


def _selected_hook_text(song: Dict[str, Any]) -> str:
    selected = song.get("selected_hook")
    if isinstance(selected, dict):
        return str(selected.get("hook_text") or selected.get("text") or "")
    return str(song.get("selected_hook_text") or selected or "")


def get_project_summary(project_name: str) -> Dict[str, Any]:
    folder = _active_path(project_name)
    project = _read_json(folder / "project.json", {})
    song = _read_json(folder / "song.json", project.get("song", {}) if isinstance(project, dict) else {})
    storyboard = _read_json(folder / "storyboard.json", ((project.get("mv", {}) or {}).get("storyboard", []) if isinstance(project, dict) else []))
    lyrics_path = folder / "lyrics.txt"
    render_root = ROOT / "outputs" / "renders" / sanitize_project_name(project.get("title") or project_name if isinstance(project, dict) else project_name)
    suno_full = folder / "exports" / "suno_full_package.txt"
    modified = folder.stat().st_mtime if folder.exists() else 0
    song_title = song.get("title") or (project.get("title") if isinstance(project, dict) else "") or project_name
    return {
        "project_name": folder.name,
        "display_name": project.get("title", folder.name) if isinstance(project, dict) else folder.name,
        "path": str(folder),
        "song_title": song_title,
        "artist": project.get("artist", DEFAULT_ARTIST) if isinstance(project, dict) else DEFAULT_ARTIST,
        "artist_preset": song.get("artist_preset", ""),
        "selected_hook": _selected_hook_text(song),
        "last_modified": datetime.fromtimestamp(modified).isoformat(timespec="seconds") if modified else "",
        "last_modified_ts": modified,
        "has_lyrics": bool((song.get("normalized_song_output") or song.get("complete_lyrics") or "").strip()) or (lyrics_path.is_file() and bool(lyrics_path.read_text(encoding="utf-8").strip())),
        "has_storyboard": bool(storyboard),
        "has_render": bool(render_root.exists() and any(render_root.rglob("final_*.mp4"))),
        "suno_txt_ready": suno_full.is_file(),
    }


def list_projects() -> List[Dict[str, Any]]:
    PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
    seen = set()
    rows: List[Dict[str, Any]] = []
    for folder in PROJECTS_ROOT.iterdir():
        if not folder.is_dir():
            continue
        key = folder.name.lower()
        if key in seen:
            continue
        seen.add(key)
        rows.append(get_project_summary(folder.name))
    return sorted(rows, key=lambda item: item.get("last_modified_ts", 0), reverse=True)


def create_project(project_name: str) -> Dict[str, Any]:
    try:
        name = sanitize_project_name(project_name)
        if project_exists(name):
            return {"ok": False, "message": "Project already exists", "data": {}, "error": "exists"}
        project = new_project(project_name or name, DEFAULT_ARTIST)
        folder = save_project_folder(project, PROJECTS_ROOT)
        return {"ok": True, "message": "Project created", "data": {"project": project, "folder": str(folder)}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Create project failed", "data": {}, "error": str(exc)}


def rename_project(old_name: str, new_name: str) -> Dict[str, Any]:
    try:
        src = _active_path(old_name)
        dst = _active_path(new_name)
        if not _is_safe_active_project_path(src):
            return {"ok": False, "message": "Project not found", "data": {}, "error": "missing"}
        if dst.exists():
            return {"ok": False, "message": "Target project exists", "data": {}, "error": "exists"}
        src.rename(dst)
        project_path = dst / "project.json"
        project = _read_json(project_path, {})
        if isinstance(project, dict):
            project["title"] = new_name
            _write_json(project_path, project)
        return {"ok": True, "message": "Project renamed", "data": {"folder": str(dst)}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Rename project failed", "data": {}, "error": str(exc)}


def archive_project(project_name: str) -> Dict[str, Any]:
    try:
        src = _active_path(project_name)
        if not _is_safe_active_project_path(src):
            return {"ok": False, "message": "Project not found", "data": {}, "error": "missing"}
        ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
        dst = ARCHIVE_ROOT / f"{src.name}_{_now_stamp()}"
        counter = 1
        while dst.exists():
            counter += 1
            dst = ARCHIVE_ROOT / f"{src.name}_{_now_stamp()}_{counter}"
        shutil.move(str(src), str(dst))
        return {"ok": True, "message": "Project archived", "data": {"archive_path": str(dst)}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Archive project failed", "data": {}, "error": str(exc)}


def delete_project(project_name: str, confirm: bool = False) -> Dict[str, Any]:
    try:
        if not confirm:
            return {"ok": False, "message": "Delete requires confirmation", "data": {}, "error": "confirmation_required"}
        src = _active_path(project_name)
        if not _is_safe_active_project_path(src):
            return {"ok": False, "message": "Project not found or unsafe path", "data": {}, "error": "unsafe_or_missing"}
        DELETED_BACKUPS_ROOT.mkdir(parents=True, exist_ok=True)
        backup = DELETED_BACKUPS_ROOT / f"{src.name}_{_now_stamp()}"
        shutil.copytree(src, backup)
        shutil.rmtree(src)
        return {"ok": True, "message": "Project deleted with backup", "data": {"backup_path": str(backup)}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Delete project failed", "data": {}, "error": str(exc)}


def list_archived_projects() -> List[Dict[str, Any]]:
    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    rows = []
    for folder in ARCHIVE_ROOT.iterdir():
        if folder.is_dir():
            rows.append({
                "project_name": folder.name,
                "path": str(folder),
                "archived_at": datetime.fromtimestamp(folder.stat().st_mtime).isoformat(timespec="seconds"),
                "last_modified_ts": folder.stat().st_mtime,
            })
    return sorted(rows, key=lambda item: item["last_modified_ts"], reverse=True)


def load_user_preferences() -> Dict[str, Any]:
    prefs = _read_json(PREFERENCES_PATH, {})
    mode = prefs.get("workflow_mode", "Full Pipeline")
    if mode not in WORKFLOW_MODES:
        mode = "Full Pipeline"
    prefs["workflow_mode"] = mode
    return prefs


def save_user_preferences(preferences: Dict[str, Any]) -> Dict[str, Any]:
    try:
        prefs = load_user_preferences()
        prefs.update(preferences or {})
        if prefs.get("workflow_mode") not in WORKFLOW_MODES:
            prefs["workflow_mode"] = "Full Pipeline"
        _write_json(PREFERENCES_PATH, prefs)
        return {"ok": True, "message": "Preferences saved", "data": {"preferences": prefs, "path": str(PREFERENCES_PATH)}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Save preferences failed", "data": {}, "error": str(exc)}
