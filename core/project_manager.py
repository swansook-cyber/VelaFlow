from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.branding import DEFAULT_ARTIST
from core.paths import (
    LEGACY_PROJECTS_ROOT,
    PROJECT_DATA_ROOT,
    WORKFLOW_PROJECT_ROOTS,
    is_project_data_child,
    iter_project_folders,
    project_folder,
    project_search_roots,
    resolve_project_folder,
    workflow_project_root,
)
from providers.ai_provider import normalize_provider
from core.api_keys import api_mode_label, API_MODE_OWN_KEY
from core.project_io import new_project, safe_name, save_project_folder
from core.workspace_manager import (
    append_generation_run as append_workspace_generation_run,
    append_history as append_workspace_history,
    create_project as create_workspace_project,
    export_project_zip as export_workspace_project_zip,
    load_project as load_workspace_project,
    save_project as save_workspace_project,
    workspace_summary as workspace_project_summary,
)
from core.asset_manager import (
    attach_asset_to_project,
    generate_asset_metadata,
    import_asset,
    list_assets,
    register_asset,
    safe_asset_filename,
)
from core.media_pipeline import (
    cover_pipeline,
    create_pipeline_item,
    load_pipeline,
    mv_pipeline,
    release_package_pipeline,
    save_pipeline,
    storyboard_pipeline,
    transition_stage,
)
from core.storyboard_manager import create_storyboard, add_scene, export_storyboard_json, export_storyboard_txt


ROOT = Path(__file__).resolve().parents[1]
PROJECTS_ROOT = LEGACY_PROJECTS_ROOT
ARCHIVE_ROOT = PROJECT_DATA_ROOT / "archive"
DELETED_BACKUPS_ROOT = PROJECT_DATA_ROOT / "deleted_backups"
PREFERENCES_PATH = ROOT / "config" / "user_preferences.json"
WORKFLOW_MODES = ["Full Pipeline", "Song Studio Only", "Seller Studio (Beta)", "Podcast Studio (Beta)", "Viral Clips Studio (Beta)", "Hook Clip Studio (Beta)"]
WORKFLOW_MODE_PROJECT_TYPES = {
    "Full Pipeline": {"song", "music_pipeline", "mv", "legacy"},
    "Song Studio Only": {"song", "music_pipeline", "legacy"},
    "Seller Studio (Beta)": {"seller"},
    "Podcast Studio": {"podcast"},
    "Podcast Studio (Beta)": {"podcast"},
    "Viral Clips Studio (Beta)": {"clips"},
    "Hook Clip Studio (Beta)": {"clips", "seller", "podcast", "song", "music_pipeline", "hook_clip"},
    "MV Workflow": {"mv", "music_pipeline"},
}
WORKFLOW_MODE_NEW_PROJECT_TYPE = {
    "Full Pipeline": "music_pipeline",
    "Song Studio Only": "song",
    "Seller Studio (Beta)": "seller",
    "Podcast Studio": "podcast",
    "Podcast Studio (Beta)": "podcast",
    "Viral Clips Studio (Beta)": "clips",
    "Hook Clip Studio (Beta)": "hook_clip",
    "MV Workflow": "mv",
}
WORKFLOW_MODE_SESSION_LABEL = {
    "Full Pipeline": "Current Song Session",
    "Song Studio Only": "Current Song Session",
    "Seller Studio (Beta)": "Current Seller Session",
    "Podcast Studio": "Current Podcast Session",
    "Podcast Studio (Beta)": "Current Podcast Session",
    "Viral Clips Studio (Beta)": "Current Clips Session",
    "Hook Clip Studio (Beta)": "Current Hook Clip Session",
    "MV Workflow": "Current MV Session",
}

TEST_PROJECT_PREFIXES = ("Smoke_", "Test_", "Demo_Debug_", "Debug_", "Internal_")
CREATOR_PROJECT_FOLDERS = ("audio", "hooks", "prompts", "remaster", "exports", "subtitles")

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
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def sanitize_project_name(name: str) -> str:
    return safe_name(name or "untitled_project")


def is_test_project_name(name: str) -> bool:
    normalized = safe_name(str(name or "").strip())
    display = str(name or "").strip()
    return any(normalized.startswith(prefix) or display.startswith(prefix) for prefix in TEST_PROJECT_PREFIXES)


def filter_visible_projects(projects: List[Dict[str, Any]], *, developer_mode: bool = False) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in projects:
        project_name = str(item.get("project_name") or item.get("display_name") or "")
        is_test = is_test_project_name(project_name)
        if is_test and not developer_mode:
            continue
        row = dict(item)
        row["is_test_project"] = is_test
        if developer_mode and is_test and not str(row.get("display_name", "")).startswith("[TEST] "):
            row["display_name"] = f"[TEST] {row.get('display_name') or project_name}"
        rows.append(row)
    return sorted(rows, key=lambda item: (bool(item.get("is_test_project")), -float(item.get("last_modified_ts", 0) or 0), str(item.get("display_name") or item.get("project_name") or "").lower()))


def ensure_creator_project_folders(project_name: str, workflow_type: str | None = "song") -> Dict[str, Any]:
    try:
        folder = resolve_project_folder(project_name or "project", workflow_type or "song")
        created = []
        for name in CREATOR_PROJECT_FOLDERS:
            target = folder / name
            target.mkdir(parents=True, exist_ok=True)
            created.append(str(target))
        return {"ok": True, "message": "Creator folders ready", "data": {"project_folder": str(folder), "folders": created}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Creator folders failed", "data": {}, "error": str(exc)}


def _active_path(project_name: str) -> Path:
    return resolve_project_folder(project_name)


def _is_safe_active_project_path(path: Path) -> bool:
    resolved = path.resolve()
    if not path.exists() or not path.is_dir():
        return False
    if not is_project_data_child(resolved):
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


def workflow_type_for_mode(workflow_mode: str | None) -> str:
    return WORKFLOW_MODE_NEW_PROJECT_TYPE.get(workflow_mode or "Full Pipeline", "music_pipeline")


def session_label_for_mode(workflow_mode: str | None) -> str:
    return WORKFLOW_MODE_SESSION_LABEL.get(workflow_mode or "Full Pipeline", "Current Session")


def infer_project_type(project: Dict[str, Any], song: Dict[str, Any] | None = None) -> str:
    if not isinstance(project, dict):
        return "legacy"
    explicit = str(project.get("workflow_type") or project.get("project_type") or "").strip()
    if explicit:
        return explicit
    if project.get("seller_studio"):
        return "seller"
    if project.get("podcast") or project.get("podcast_studio"):
        return "podcast"
    if project.get("viral_clips_studio"):
        return "clips"
    mv = project.get("mv", {}) or {}
    if mv.get("storyboard"):
        return "music_pipeline"
    song = song if isinstance(song, dict) else project.get("song", {}) or {}
    if song:
        return "song"
    return "legacy"


def project_visible_in_workflow(project_type: str, workflow_mode: str | None) -> bool:
    allowed = WORKFLOW_MODE_PROJECT_TYPES.get(workflow_mode or "Full Pipeline", WORKFLOW_MODE_PROJECT_TYPES["Full Pipeline"])
    normalized = project_type or "legacy"
    return normalized in allowed or (normalized == "legacy" and "legacy" in allowed)


def _project_summary_from_folder(folder: Path) -> Dict[str, Any]:
    project_name = folder.name
    project = _read_json(folder / "project.json", {})
    song = _read_json(folder / "song.json", project.get("song", {}) if isinstance(project, dict) else {})
    storyboard = _read_json(folder / "storyboard.json", ((project.get("mv", {}) or {}).get("storyboard", []) if isinstance(project, dict) else []))
    lyrics_path = folder / "lyrics.txt"
    render_root = ROOT / "outputs" / "renders" / sanitize_project_name(project.get("title") or project_name if isinstance(project, dict) else project_name)
    exports_folder = folder / "exports"
    thumbnail = next(exports_folder.rglob("thumbnail.jpg"), None) if exports_folder.exists() else None
    suno_full = next(exports_folder.glob("*_full_pipeline.txt"), None) if exports_folder.exists() else None
    if suno_full is None and exports_folder.exists():
        suno_full = next(exports_folder.glob("*_song_only.txt"), None)
    if suno_full is None:
        suno_full = folder / "exports" / "suno_full_package.txt"
    modified = folder.stat().st_mtime if folder.exists() else 0
    song_title = song.get("title") or (project.get("title") if isinstance(project, dict) else "") or project_name
    workflow_type = infer_project_type(project if isinstance(project, dict) else {}, song)
    return {
        "project_name": folder.name,
        "display_name": project.get("title", folder.name) if isinstance(project, dict) else folder.name,
        "path": str(folder),
        "workflow_type": workflow_type,
        "project_type": workflow_type,
        "song_title": song_title,
        "artist": project.get("artist", DEFAULT_ARTIST) if isinstance(project, dict) else DEFAULT_ARTIST,
        "artist_preset": song.get("artist_preset", ""),
        "selected_hook": _selected_hook_text(song),
        "last_modified": datetime.fromtimestamp(modified).isoformat(timespec="seconds") if modified else "",
        "last_modified_ts": modified,
        "thumbnail": str(thumbnail) if thumbnail and thumbnail.is_file() else "",
        "has_lyrics": bool((song.get("normalized_song_output") or song.get("complete_lyrics") or "").strip()) or (lyrics_path.is_file() and bool(lyrics_path.read_text(encoding="utf-8").strip())),
        "has_storyboard": bool(storyboard),
        "has_render": bool(render_root.exists() and any(render_root.rglob("final_*.mp4"))),
        "suno_txt_ready": bool(suno_full and suno_full.is_file()),
    }


def get_project_summary(project_name: str) -> Dict[str, Any]:
    return _project_summary_from_folder(_active_path(project_name))


def autosave_project_state(project_name: str, workflow_type: str | None, payload: Dict[str, Any], label: str = "autosave") -> Dict[str, Any]:
    try:
        folder = resolve_project_folder(project_name, workflow_type)
        autosave_path = folder / "runtime" / f"{safe_name(label or 'autosave')}.json"
        snapshot = {
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "project_name": project_name,
            "workflow_type": workflow_type or infer_project_type(payload if isinstance(payload, dict) else {}),
            "payload": payload or {},
        }
        _write_json(autosave_path, snapshot)
        return {"ok": True, "message": "Autosave complete", "data": {"path": str(autosave_path), "snapshot": snapshot}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Autosave failed", "data": {}, "error": str(exc)}


def load_autosave_project_state(project_name: str, workflow_type: str | None, label: str = "autosave") -> Dict[str, Any]:
    try:
        folder = resolve_project_folder(project_name, workflow_type)
        autosave_path = folder / "runtime" / f"{safe_name(label or 'autosave')}.json"
        snapshot = _read_json(autosave_path, {})
        return {"ok": bool(snapshot), "message": "Autosave loaded" if snapshot else "No autosave found", "data": {"path": str(autosave_path), "snapshot": snapshot}, "error": "" if snapshot else "missing_autosave"}
    except Exception as exc:
        return {"ok": False, "message": "Load autosave failed", "data": {}, "error": str(exc)}


def project_health_summary(project_name: str, workflow_type: str | None = "song") -> Dict[str, Any]:
    try:
        from core.error_recovery import recover_partial_render
        from core.render_queue import render_queue_summary
        from core.storage_cleanup import project_storage_summary

        storage = project_storage_summary(project_name, workflow_type or "song").get("data", {})
        queue = render_queue_summary(project_name, workflow_type or "song").get("data", {})
        recovery = recover_partial_render(project_name, workflow_type or "song").get("data", {})
        return {
            "ok": True,
            "message": "Project health ready",
            "data": {
                "render_status": (queue.get("active") or queue.get("latest") or {}).get("status", "idle"),
                "cache_health": storage.get("cache_health", "ok"),
                "storage_usage": storage.get("storage_label", "0 B"),
                "latest_successful_render": recovery.get("latest_successful_render") or storage.get("latest_successful_render", ""),
                "failed_stages": recovery.get("failed_stages", []),
                "render_success_rate": queue.get("success_rate", 0),
                "queue": queue,
                "storage": storage,
                "recovery": recovery,
            },
            "error": "",
        }
    except Exception as exc:
        return {"ok": False, "message": "Project health unavailable", "data": {}, "error": str(exc)}


def list_projects(workflow_mode: str | None = None, workflow_type: str | None = None) -> List[Dict[str, Any]]:
    seen = set()
    rows: List[Dict[str, Any]] = []
    for folder in iter_project_folders():
        key = str(folder.resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        summary = _project_summary_from_folder(folder)
        if workflow_type and summary.get("workflow_type") != workflow_type:
            continue
        if workflow_mode and not project_visible_in_workflow(summary.get("workflow_type", "legacy"), workflow_mode):
            continue
        rows.append(summary)
    return sorted(rows, key=lambda item: item.get("last_modified_ts", 0), reverse=True)


def create_project(project_name: str, workflow_type: str | None = None) -> Dict[str, Any]:
    try:
        name = sanitize_project_name(project_name)
        if project_exists(name):
            return {"ok": False, "message": "Project already exists", "data": {}, "error": "exists"}
        project = new_project(project_name or name, DEFAULT_ARTIST)
        project["workflow_type"] = workflow_type or "music_pipeline"
        project["project_type"] = project["workflow_type"]
        folder = save_project_folder(project, workflow_project_root(project["workflow_type"]))
        ensure_creator_project_folders(project_name or name, project["workflow_type"])
        return {"ok": True, "message": "Project created", "data": {"project": project, "folder": str(folder)}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Create project failed", "data": {}, "error": str(exc)}


def rename_project(old_name: str, new_name: str) -> Dict[str, Any]:
    try:
        src = _active_path(old_name)
        workflow_type = infer_project_type(_read_json(src / "project.json", {}))
        dst = project_folder(new_name, workflow_type)
        if not _is_safe_active_project_path(src):
            return {"ok": False, "message": "Project not found", "data": {}, "error": "missing"}
        if dst.exists():
            return {"ok": False, "message": "Target project exists", "data": {}, "error": "exists"}
        dst.parent.mkdir(parents=True, exist_ok=True)
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
        workflow_label = src.parent.name if src.parent.name != "projects" else "legacy"
        dst = ARCHIVE_ROOT / workflow_label / f"{src.name}_{_now_stamp()}"
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
        workflow_label = src.parent.name if src.parent.name != "projects" else "legacy"
        backup = DELETED_BACKUPS_ROOT / workflow_label / f"{src.name}_{_now_stamp()}"
        shutil.copytree(src, backup)
        shutil.rmtree(src)
        return {"ok": True, "message": "Project deleted with backup", "data": {"backup_path": str(backup)}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Delete project failed", "data": {}, "error": str(exc)}


def list_archived_projects() -> List[Dict[str, Any]]:
    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    rows = []
    for folder in ARCHIVE_ROOT.rglob("*"):
        if folder.is_dir():
            if not (folder / "project.json").exists():
                continue
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
    prefs["default_ai_provider"] = normalize_provider(prefs.get("default_ai_provider", "gemini"))
    prefs["api_mode"] = api_mode_label(prefs.get("api_mode", API_MODE_OWN_KEY))
    return prefs


def save_user_preferences(preferences: Dict[str, Any]) -> Dict[str, Any]:
    try:
        prefs = load_user_preferences()
        prefs.update(preferences or {})
        if prefs.get("workflow_mode") not in WORKFLOW_MODES:
            prefs["workflow_mode"] = "Full Pipeline"
        prefs["default_ai_provider"] = normalize_provider(prefs.get("default_ai_provider", "gemini"))
        prefs["api_mode"] = api_mode_label(prefs.get("api_mode", API_MODE_OWN_KEY))
        _write_json(PREFERENCES_PATH, prefs)
        return {"ok": True, "message": "Preferences saved", "data": {"preferences": prefs, "path": str(PREFERENCES_PATH)}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Save preferences failed", "data": {}, "error": str(exc)}
