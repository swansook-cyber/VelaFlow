from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from core.paths import workflow_project_root
from core.project_io import safe_name


ACTIVE_STATUSES = {"queued", "rendering"}
FINAL_STATUSES = {"completed", "failed", "cancelled", "stale"}


def _now() -> datetime:
    return datetime.now()


def _stamp() -> str:
    return _now().isoformat(timespec="seconds")


def render_runtime_dir(project_name: str, workflow_type: str = "song") -> Path:
    root = workflow_project_root(workflow_type or "song") / safe_name(project_name or "project")
    path = root / "runtime"
    path.mkdir(parents=True, exist_ok=True)
    return path


def render_queue_path(project_name: str, workflow_type: str = "song") -> Path:
    return render_runtime_dir(project_name, workflow_type) / "render_queue.json"


def render_lock_path(project_name: str, workflow_type: str = "song") -> Path:
    return render_runtime_dir(project_name, workflow_type) / "render.lock"


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


def load_creator_render_queue(project_name: str, workflow_type: str = "song") -> dict[str, Any]:
    path = render_queue_path(project_name, workflow_type)
    payload = _read_json(path, {"jobs": []})
    jobs = payload.get("jobs") if isinstance(payload, dict) else []
    if not isinstance(jobs, list):
        jobs = []
    return {"ok": True, "message": "Render queue loaded", "data": {"path": str(path), "jobs": jobs}, "error": ""}


def save_creator_render_queue(project_name: str, workflow_type: str, jobs: list[dict[str, Any]]) -> dict[str, Any]:
    path = render_queue_path(project_name, workflow_type)
    payload = {"updated_at": _stamp(), "project_name": project_name, "workflow_type": workflow_type, "jobs": jobs}
    _write_json(path, payload)
    return {"ok": True, "message": "Render queue saved", "data": {"path": str(path), "jobs": jobs}, "error": ""}


def active_render_job(project_name: str, workflow_type: str = "song") -> dict[str, Any] | None:
    jobs = load_creator_render_queue(project_name, workflow_type)["data"]["jobs"]
    for job in reversed(jobs):
        if str(job.get("status", "")).lower() in ACTIVE_STATUSES:
            return job
    return None


def release_stale_render_jobs(project_name: str, workflow_type: str = "song", timeout_seconds: int = 900) -> dict[str, Any]:
    loaded = load_creator_render_queue(project_name, workflow_type)
    jobs = loaded["data"]["jobs"]
    cutoff = _now() - timedelta(seconds=max(60, int(timeout_seconds or 900)))
    released = []
    for job in jobs:
        if str(job.get("status", "")).lower() not in ACTIVE_STATUSES:
            continue
        try:
            created_at = datetime.fromisoformat(str(job.get("created_at") or job.get("updated_at") or ""))
        except Exception:
            created_at = cutoff - timedelta(seconds=1)
        if created_at < cutoff:
            job["status"] = "stale"
            job["safe_error_message"] = "Render took too long and was released safely. You can retry."
            job["updated_at"] = _stamp()
            released.append(job.get("job_id"))
    if released:
        save_creator_render_queue(project_name, workflow_type, jobs)
        lock_path = render_lock_path(project_name, workflow_type)
        if lock_path.is_file():
            lock_path.unlink(missing_ok=True)
    return {"ok": True, "message": "Stale render jobs released", "data": {"released": released, "jobs": jobs}, "error": ""}


def start_render_job(
    project_name: str,
    workflow_type: str = "song",
    *,
    stage: str = "quick_generate",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    release_stale_render_jobs(project_name, workflow_type)
    active = active_render_job(project_name, workflow_type)
    if active:
        return {
            "ok": False,
            "message": "Render already running",
            "data": {"active_job": active},
            "error": "active_render_job",
        }
    jobs = load_creator_render_queue(project_name, workflow_type)["data"]["jobs"]
    job_id = f"{safe_name(stage)}_{_now().strftime('%Y%m%d_%H%M%S')}"
    job = {
        "job_id": job_id,
        "project_name": project_name,
        "workflow_type": workflow_type,
        "stage": stage,
        "status": "rendering",
        "created_at": _stamp(),
        "updated_at": _stamp(),
        "metadata": metadata or {},
    }
    jobs.append(job)
    save_creator_render_queue(project_name, workflow_type, jobs)
    lock_path = render_lock_path(project_name, workflow_type)
    lock_path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "message": "Render job started", "data": {"job": job, "lock_path": str(lock_path)}, "error": ""}


def complete_render_job(
    project_name: str,
    workflow_type: str,
    job_id: str,
    *,
    status: str = "completed",
    result: dict[str, Any] | None = None,
    error: str = "",
    safe_error_message: str = "",
) -> dict[str, Any]:
    loaded = load_creator_render_queue(project_name, workflow_type)
    jobs = loaded["data"]["jobs"]
    normalized = status if status in FINAL_STATUSES else "completed"
    updated_job = None
    for job in jobs:
        if str(job.get("job_id")) == str(job_id):
            job["status"] = normalized
            job["updated_at"] = _stamp()
            job["result"] = result or {}
            job["error"] = error or ""
            job["safe_error_message"] = safe_error_message or ""
            updated_job = job
            break
    save_creator_render_queue(project_name, workflow_type, jobs)
    lock_path = render_lock_path(project_name, workflow_type)
    if lock_path.is_file():
        try:
            lock_payload = json.loads(lock_path.read_text(encoding="utf-8"))
        except Exception:
            lock_payload = {}
        if not job_id or str(lock_payload.get("job_id")) == str(job_id):
            lock_path.unlink(missing_ok=True)
    return {"ok": True, "message": "Render job completed", "data": {"job": updated_job, "jobs": jobs}, "error": ""}


def render_queue_summary(project_name: str, workflow_type: str = "song") -> dict[str, Any]:
    jobs = load_creator_render_queue(project_name, workflow_type)["data"]["jobs"]
    active = next((job for job in reversed(jobs) if str(job.get("status", "")).lower() in ACTIVE_STATUSES), None)
    latest = jobs[-1] if jobs else {}
    completed_count = len([job for job in jobs if str(job.get("status", "")).lower() == "completed"])
    failed_count = len([job for job in jobs if str(job.get("status", "")).lower() == "failed"])
    finished_count = completed_count + failed_count
    success_rate = round((completed_count / finished_count) * 100, 1) if finished_count else 0.0
    return {
        "ok": True,
        "message": "Render queue summary",
        "data": {
            "active": active,
            "latest": latest,
            "job_count": len(jobs),
            "completed_count": completed_count,
            "failed_count": failed_count,
            "success_rate": success_rate,
        },
        "error": "",
    }
