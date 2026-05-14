import json
import threading
import time
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict


ROOT = Path(__file__).resolve().parents[1]
JOBS_DIR = ROOT / "outputs" / "jobs"
JOBS_PATH = JOBS_DIR / "jobs.json"
_LOCK = threading.RLock()
_WORKER_THREAD: threading.Thread | None = None
_HANDLERS: dict[str, Callable[[dict[str, Any], "JobContext"], Any]] = {}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _load_jobs_unlocked() -> list[dict[str, Any]]:
    if not JOBS_PATH.exists():
        return []
    try:
        return json.loads(JOBS_PATH.read_text(encoding="utf-8"))
    except Exception:
        broken = JOBS_PATH.with_suffix(f".broken_{int(time.time())}.json")
        JOBS_PATH.replace(broken)
        return []


def _save_jobs_unlocked(jobs: list[dict[str, Any]]) -> None:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    tmp = JOBS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(JOBS_PATH)


def list_jobs() -> list[dict[str, Any]]:
    with _LOCK:
        jobs = _load_jobs_unlocked()
        return sorted(jobs, key=lambda job: job.get("created_at", ""), reverse=True)


def get_job(job_id: str) -> dict[str, Any] | None:
    with _LOCK:
        for job in _load_jobs_unlocked():
            if job.get("id") == job_id:
                return job
    return None


def _update_job(job_id: str, **updates: Any) -> dict[str, Any] | None:
    with _LOCK:
        jobs = _load_jobs_unlocked()
        for job in jobs:
            if job.get("id") == job_id:
                job.update(updates)
                job["updated_at"] = _now()
                _save_jobs_unlocked(jobs)
                return job
    return None


def append_log(job_id: str, message: str, level: str = "INFO") -> None:
    entry = {"ts": _now(), "level": level, "message": message}
    with _LOCK:
        jobs = _load_jobs_unlocked()
        for job in jobs:
            if job.get("id") == job_id:
                job.setdefault("logs", []).append(entry)
                job["updated_at"] = entry["ts"]
                _save_jobs_unlocked(jobs)
                return


class JobContext:
    def __init__(self, job_id: str):
        self.job_id = job_id

    def log(self, message: str, level: str = "INFO") -> None:
        append_log(self.job_id, message, level)

    def progress(self, value: int, message: str | None = None) -> None:
        value = max(0, min(int(value), 100))
        _update_job(self.job_id, progress=value)
        if message:
            self.log(message)

    def is_cancel_requested(self) -> bool:
        job = get_job(self.job_id) or {}
        return job.get("cancel_requested") is True or job.get("status") == "CANCEL_REQUESTED"

    def checkpoint(self, message: str = "Cancel requested") -> None:
        if self.is_cancel_requested():
            self.log(message, "WARN")
            raise RuntimeError("Job canceled")


def register_handler(job_type: str, handler: Callable[[dict[str, Any], JobContext], Any]) -> None:
    _HANDLERS[job_type] = handler


def submit_job(job_type: str, name: str, payload: dict[str, Any] | None = None) -> str:
    job_id = str(uuid.uuid4())
    job = {
        "id": job_id,
        "type": job_type,
        "name": name,
        "status": "QUEUED",
        "progress": 0,
        "payload": payload or {},
        "result": None,
        "error": "",
        "logs": [{"ts": _now(), "level": "INFO", "message": "Job queued"}],
        "cancel_requested": False,
        "created_at": _now(),
        "updated_at": _now(),
        "started_at": "",
        "finished_at": "",
    }
    with _LOCK:
        jobs = _load_jobs_unlocked()
        jobs.append(job)
        _save_jobs_unlocked(jobs)
    start_worker()
    return job_id


def cancel_job(job_id: str) -> None:
    job = get_job(job_id)
    if not job:
        return
    if job.get("status") == "QUEUED":
        _update_job(job_id, status="CANCELED", progress=0, cancel_requested=True, finished_at=_now())
        append_log(job_id, "Job canceled before start", "WARN")
    elif job.get("status") == "RUNNING":
        _update_job(job_id, status="CANCEL_REQUESTED", cancel_requested=True)
        append_log(job_id, "Cancel requested; waiting for current step to stop", "WARN")


def clear_finished_jobs() -> None:
    with _LOCK:
        jobs = [job for job in _load_jobs_unlocked() if job.get("status") not in {"DONE", "FAILED", "CANCELED"}]
        _save_jobs_unlocked(jobs)


def recover_interrupted_jobs() -> None:
    with _LOCK:
        changed = False
        jobs = _load_jobs_unlocked()
        for job in jobs:
            if job.get("status") in {"RUNNING", "CANCEL_REQUESTED"}:
                job["status"] = "QUEUED"
                job["progress"] = min(int(job.get("progress", 0) or 0), 95)
                job["cancel_requested"] = False
                job.setdefault("logs", []).append({"ts": _now(), "level": "WARN", "message": "Recovered interrupted job"})
                changed = True
        if changed:
            _save_jobs_unlocked(jobs)


def _next_queued_job() -> dict[str, Any] | None:
    with _LOCK:
        jobs = _load_jobs_unlocked()
        for job in jobs:
            if job.get("status") == "QUEUED":
                job["status"] = "RUNNING"
                job["progress"] = max(int(job.get("progress", 0) or 0), 1)
                job["started_at"] = job.get("started_at") or _now()
                job["updated_at"] = _now()
                _save_jobs_unlocked(jobs)
                return job
    return None


def _worker_loop() -> None:
    recover_interrupted_jobs()
    while True:
        job = _next_queued_job()
        if not job:
            return
        job_id = job["id"]
        context = JobContext(job_id)
        handler = _HANDLERS.get(job.get("type"))
        if not handler:
            _update_job(job_id, status="FAILED", error=f"No handler for {job.get('type')}", finished_at=_now())
            append_log(job_id, "No handler registered", "ERROR")
            continue
        try:
            context.log("Job started")
            context.checkpoint()
            result = handler(job.get("payload", {}), context)
            if context.is_cancel_requested():
                _update_job(job_id, status="CANCELED", progress=0, cancel_requested=True, finished_at=_now())
                context.log("Job canceled", "WARN")
            else:
                _update_job(job_id, status="DONE", progress=100, result=result, finished_at=_now())
                context.log("Job completed", "OK")
        except Exception as error:
            status = "CANCELED" if "canceled" in str(error).lower() else "FAILED"
            _update_job(job_id, status=status, error=str(error), finished_at=_now())
            context.log(str(error), "ERROR")
            context.log(traceback.format_exc(limit=6), "ERROR")


def start_worker() -> None:
    global _WORKER_THREAD
    if _WORKER_THREAD and _WORKER_THREAD.is_alive():
        return
    _WORKER_THREAD = threading.Thread(target=_worker_loop, name="vela-job-worker", daemon=True)
    _WORKER_THREAD.start()
