from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.project_io import safe_name


ROOT = Path(__file__).resolve().parents[1]


def render_state_path(render_dir: str | Path) -> Path:
    return Path(render_dir) / "render_state.json"


def load_render_state(render_dir: str | Path) -> Dict[str, Any]:
    path = render_state_path(render_dir)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"completed_scenes": [], "failed_scenes": [], "updated_at": ""}


def save_render_state(render_dir: str | Path, state: Dict[str, Any]) -> Dict[str, Any]:
    path = render_state_path(render_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(state or {})
    payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "message": "Render state saved", "data": {"path": str(path), "state": payload}, "error": ""}


def mark_scene_rendered(render_dir: str | Path, aspect: str, scene_id: str, path: str) -> None:
    state = load_render_state(render_dir)
    completed = state.setdefault("completed_scenes", [])
    record = {"aspect": aspect, "scene_id": str(scene_id), "path": path}
    if not any(item.get("aspect") == aspect and str(item.get("scene_id")) == str(scene_id) for item in completed):
        completed.append(record)
    save_render_state(render_dir, state)


def mark_scene_failed(render_dir: str | Path, aspect: str, scene_id: str, error: str) -> None:
    state = load_render_state(render_dir)
    failed = state.setdefault("failed_scenes", [])
    failed.append({"aspect": aspect, "scene_id": str(scene_id), "error": error, "at": datetime.now().isoformat(timespec="seconds")})
    save_render_state(render_dir, state)


def latest_failed_render(project: Dict[str, Any]) -> Dict[str, Any]:
    runtime_dir = (project.get("runtime", {}) or {}).get("last_render_dir", "")
    if runtime_dir and Path(runtime_dir).exists():
        manifest = Path(runtime_dir) / "render_manifest.json"
        try:
            data = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else {}
            if data.get("render_status") in {"FAILED", "PARTIAL"}:
                return {"ok": True, "message": "Runtime failed render found", "data": {"render_dir": str(Path(runtime_dir)), "state": load_render_state(runtime_dir)}, "error": ""}
        except Exception:
            pass
    root = ROOT / "outputs" / "renders" / safe_name(project.get("title", "project"))
    if not root.exists():
        return {"ok": False, "message": "No render history", "data": {}, "error": "missing_render_history"}
    candidates: List[Path] = []
    for manifest in root.glob("*/render_manifest.json"):
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            if data.get("render_status") in {"FAILED", "PARTIAL"}:
                candidates.append(manifest.parent)
        except Exception:
            continue
    if not candidates:
        return {"ok": False, "message": "No failed render found", "data": {}, "error": "missing_failed_render"}
    latest = sorted(candidates, key=lambda path: path.stat().st_mtime, reverse=True)[0]
    return {"ok": True, "message": "Latest failed render found", "data": {"render_dir": str(latest), "state": load_render_state(latest)}, "error": ""}


def export_diagnostic_bundle(project: Dict[str, Any], output_dir: str | Path | None = None) -> Dict[str, Any]:
    title = safe_name(project.get("title", "project"))
    output = Path(output_dir) if output_dir else ROOT / "outputs" / "diagnostics"
    output.mkdir(parents=True, exist_ok=True)
    bundle = output / f"{title}_diagnostics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    paths = [
        ROOT / "outputs" / "jobs" / "jobs.json",
        ROOT / "outputs" / "streamlit-8501-out.log",
        ROOT / "outputs" / "streamlit-8501-err.log",
        ROOT / "project_data" / "last_session.json",
        ROOT / "config" / "theme.json",
        ROOT / "config" / "export.json",
        ROOT / "config" / "license.json",
    ]
    render_root = ROOT / "outputs" / "renders" / title
    if render_root.exists():
        paths.extend(sorted(render_root.rglob("render_log.txt"), key=lambda path: path.stat().st_mtime, reverse=True)[:5])
        paths.extend(sorted(render_root.rglob("render_manifest.json"), key=lambda path: path.stat().st_mtime, reverse=True)[:5])
        paths.extend(sorted(render_root.rglob("render_state.json"), key=lambda path: path.stat().st_mtime, reverse=True)[:5])
    with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("project_snapshot.json", json.dumps(project, ensure_ascii=False, indent=2))
        for path in paths:
            if path.exists() and path.is_file():
                zf.write(path, path.relative_to(ROOT))
    return {"ok": True, "message": "Diagnostic bundle exported", "data": {"path": str(bundle)}, "error": ""}


def recover_render_temp(render_dir: str | Path) -> Dict[str, Any]:
    render_path = Path(render_dir)
    cache = render_path / "cache"
    clips = list(cache.rglob("scene_*.mp4")) if cache.exists() else []
    return {"ok": True, "message": f"Found {len(clips)} recoverable scene clips", "data": {"render_dir": str(render_path), "clips": [str(path) for path in clips]}, "error": ""}
