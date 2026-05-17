import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from core.project_io import safe_name
from core.paths import resolve_project_folder, workflow_project_root


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


def _next_clip_version(folder: Path) -> int:
    folder.mkdir(parents=True, exist_ok=True)
    versions = []
    for path in folder.glob("final_hook_clip_v*.mp4"):
        try:
            versions.append(int(path.stem.rsplit("_v", 1)[1]))
        except Exception:
            pass
    return (max(versions) if versions else 0) + 1


def save_clip_version(
    project_name: str,
    workflow_type: str,
    *,
    final_mp4: str | Path,
    package: dict[str, Any] | None = None,
    render_data: dict[str, Any] | None = None,
    tiktok_package: dict[str, Any] | None = None,
    variation: str = "default",
) -> Dict[str, Any]:
    source = Path(str(final_mp4 or ""))
    if not source.is_file():
        return {"ok": False, "message": "Final MP4 missing", "data": {}, "error": "missing_final_mp4"}
    project_dir = workflow_project_root(workflow_type or "clips") / safe_name(project_name or "hook_clip")
    version_dir = project_dir / "exports" / "versions"
    version = _next_clip_version(version_dir)
    version_id = f"v{version}"
    video_path = version_dir / f"final_hook_clip_{version_id}.mp4"
    shutil.copy2(source, video_path)
    payload = {
        "generated_by": "VelaFlow",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "project_name": project_name,
        "workflow_type": workflow_type,
        "version": version,
        "version_id": version_id,
        "variation": variation,
        "final_mp4": str(video_path),
        "hook_text": (package or {}).get("hook_text", ""),
        "viral_metrics": (package or {}).get("viral_metrics", {}),
        "render_stage": (render_data or {}).get("render_stage", {}),
        "tiktok_package": tiktok_package or {},
    }
    manifest_path = version_dir / f"clip_version_{version_id}.json"
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "message": "Clip version saved", "data": {"version": version, "version_id": version_id, "path": str(video_path), "manifest_path": str(manifest_path), "version_dir": str(version_dir), "manifest": payload}, "error": ""}


def list_clip_versions(project_name: str, workflow_type: str = "clips") -> list[Dict[str, Any]]:
    version_dir = workflow_project_root(workflow_type or "clips") / safe_name(project_name or "hook_clip") / "exports" / "versions"
    versions = []
    for manifest_path in sorted(version_dir.glob("clip_version_v*.json")):
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        versions.append(payload)
    return versions
