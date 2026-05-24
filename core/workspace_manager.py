from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from typing import Any

from core.project_state import (
    PROJECTS_ROOT,
    default_project_state,
    ensure_project_structure,
    ensure_workspace_root,
    project_path,
    read_json_safe,
    sanitize_project_name,
    utc_now,
    write_json_safe,
)


def create_project(project_name: str, initial_state: dict[str, Any] | None = None, root: Path = PROJECTS_ROOT) -> dict[str, Any]:
    folder = ensure_project_structure(project_name, root)
    state_path = folder / "project.json"
    state = default_project_state(project_name)
    if initial_state:
        state.update(initial_state)
    state["project_name"] = folder.name
    state["updated_at"] = utc_now()
    write_json_safe(state_path, state)
    memory_path = folder / "memory.json"
    if not memory_path.exists():
        write_json_safe(memory_path, {"project_name": folder.name, "notes": [], "updated_at": utc_now()})
    return {**state, "path": str(folder)}


def load_project(project_name: str, root: Path = PROJECTS_ROOT) -> dict[str, Any]:
    folder = ensure_project_structure(project_name, root)
    fallback = default_project_state(folder.name)
    state = read_json_safe(folder / "project.json", fallback)
    state.setdefault("project_name", folder.name)
    state.setdefault("display_name", folder.name)
    state.setdefault("workflow_history", [])
    state.setdefault("generated_outputs", [])
    state.setdefault("active_agents", [])
    state.setdefault("generated_files", [])
    state.setdefault("execution_logs", [])
    state.setdefault("versions", [])
    state["path"] = str(folder)
    return state


def save_project(project_name: str, state: dict[str, Any], root: Path = PROJECTS_ROOT) -> dict[str, Any]:
    folder = ensure_project_structure(project_name, root)
    current = load_project(folder.name, root)
    current.update(state or {})
    current["project_name"] = folder.name
    current["updated_at"] = utc_now()
    write_json_safe(folder / "project.json", {k: v for k, v in current.items() if k != "path"})
    current["path"] = str(folder)
    return current


def list_projects(root: Path = PROJECTS_ROOT, include_archived: bool = False) -> list[dict[str, Any]]:
    ensure_workspace_root(root)
    projects: list[dict[str, Any]] = []
    for folder in root.iterdir():
        if not folder.is_dir() or folder.name in {"assets", "exports", "history"}:
            continue
        state = load_project(folder.name, root)
        if state.get("archived") and not include_archived:
            continue
        projects.append(state)
    projects.sort(key=lambda item: str(item.get("updated_at", "")), reverse=True)
    return projects


def archive_project(project_name: str, root: Path = PROJECTS_ROOT) -> dict[str, Any]:
    state = load_project(project_name, root)
    state["archived"] = True
    state["updated_at"] = utc_now()
    return save_project(project_name, state, root)


def append_history(project_name: str, event: str, payload: dict[str, Any] | None = None, root: Path = PROJECTS_ROOT) -> dict[str, Any]:
    state = load_project(project_name, root)
    entry = {"timestamp": utc_now(), "event": event, "payload": payload or {}}
    state.setdefault("workflow_history", []).append(entry)
    state.setdefault("execution_logs", []).append(f"{entry['timestamp']} - {event}")
    version_id = f"v{len(state.get('versions', [])) + 1}"
    state.setdefault("versions", []).append({"version": version_id, "timestamp": entry["timestamp"], "event": event})
    saved = save_project(project_name, state, root)
    history_path = Path(saved["path"]) / "history" / f"{version_id}.json"
    write_json_safe(history_path, entry)
    return saved


def append_generation_run(project_name: str, result: dict[str, Any], user_goal: str = "", root: Path = PROJECTS_ROOT) -> dict[str, Any]:
    state = load_project(project_name, root)
    if user_goal:
        state.setdefault("user_goals", []).append(user_goal)
    state.setdefault("generated_outputs", []).append(result.get("output_package", {}))
    state["active_agents"] = result.get("active_agents", [])
    state["generated_files"] = result.get("generated_files", [])
    state["memory_summary"] = result.get("memory_summary", "")
    state.setdefault("execution_logs", []).extend(result.get("actions_performed", []))
    saved = save_project(project_name, state, root)
    return append_history(project_name, "agent_generation", {"user_goal": user_goal, "result": result}, root)


def export_project_zip(project_name: str, root: Path = PROJECTS_ROOT) -> Path:
    state = load_project(project_name, root)
    folder = Path(state["path"])
    export_dir = folder / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    zip_path = export_dir / f"{sanitize_project_name(project_name)}_workspace.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in folder.rglob("*"):
            if path.is_file() and path != zip_path:
                archive.write(path, arcname=str(path.relative_to(folder)))
    return zip_path


def workspace_summary(project_name: str, root: Path = PROJECTS_ROOT) -> dict[str, Any]:
    state = load_project(project_name, root)
    folder = Path(state["path"])
    file_count = sum(1 for path in folder.rglob("*") if path.is_file())
    return {
        "project_name": state.get("project_name"),
        "updated_at": state.get("updated_at"),
        "history_count": len(state.get("workflow_history", [])),
        "output_count": len(state.get("generated_outputs", [])),
        "active_agents": state.get("active_agents", []),
        "file_count": file_count,
    }


def duplicate_project(project_name: str, new_name: str, root: Path = PROJECTS_ROOT) -> dict[str, Any]:
    source = Path(load_project(project_name, root)["path"])
    target = project_path(new_name, root)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    state = load_project(target.name, root)
    state["project_name"] = target.name
    state["display_name"] = new_name
    state["updated_at"] = utc_now()
    return save_project(target.name, state, root)
