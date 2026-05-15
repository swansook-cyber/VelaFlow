from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from core.project_io import safe_name
from core.paths import workflow_project_root
from providers.veo_provider import build_veo_payload, download_render_result, poll_render_status, submit_render_job


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def scene_project_dir(project_name: str) -> Path:
    return workflow_project_root("clips") / safe_name(project_name or "hook_clip")


def scene_jobs_path(project_name: str) -> Path:
    return scene_project_dir(project_name) / "scene_render_jobs.json"


def scene_output_path(project_name: str, scene_id: str = "scene_01") -> Path:
    return scene_project_dir(project_name) / "scenes" / f"{scene_id}.mp4"


def load_scene_jobs(project_name: str) -> dict[str, Any]:
    path = scene_jobs_path(project_name)
    if not path.is_file():
        return {"ok": True, "message": "No scene jobs yet", "data": {"jobs": {}, "path": str(path)}, "error": ""}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {"ok": True, "message": "Scene jobs loaded", "data": {"jobs": data if isinstance(data, dict) else {}, "path": str(path)}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Scene jobs load failed", "data": {"jobs": {}, "path": str(path)}, "error": str(exc)}


def save_scene_job(project_name: str, scene_id: str, job: dict[str, Any]) -> dict[str, Any]:
    loaded = load_scene_jobs(project_name)
    jobs = loaded.get("data", {}).get("jobs", {}) if loaded.get("ok") else {}
    jobs[scene_id] = job
    path = scene_jobs_path(project_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "message": "Scene job saved", "data": {"job": job, "path": str(path), "jobs": jobs}, "error": ""}


def _scene_from_package(hook_package: dict[str, Any], scene_index: int = 0) -> dict[str, Any]:
    scenes = hook_package.get("scene_sequence") or (hook_package.get("scene_package") or {}).get("scenes") or []
    if not scenes:
        return {}
    return scenes[max(0, min(scene_index, len(scenes) - 1))]


def submit_veo_scene_job(project_name: str, hook_package: dict[str, Any], api_key: str, scene_index: int = 0) -> dict[str, Any]:
    scene = _scene_from_package(hook_package, scene_index)
    if not scene:
        return {"ok": False, "message": "Scene is missing", "data": {}, "error": "missing_scene"}
    scene_id = str(scene.get("scene_id") or f"scene_{scene_index + 1:02d}")
    payload = build_veo_payload(
        prompt=scene.get("visual_prompt") or hook_package.get("render_prompt") or hook_package.get("hook_text") or "",
        aspect_ratio="9:16",
        duration_seconds=int(float(scene.get("duration", 5) or 5)),
        scene_id=scene_id,
        subtitle_timing=hook_package.get("subtitle_timing") or [],
    )
    result = submit_render_job(payload, api_key=api_key)
    job = {
        "scene_id": scene_id,
        "provider": "Google Veo",
        "status": result.get("data", {}).get("status", "failed") if result.get("ok") else "failed",
        "job_id": result.get("data", {}).get("job_id", ""),
        "created_at": _now(),
        "updated_at": _now(),
        "output_path": str(scene_output_path(project_name, scene_id)),
        "payload": payload,
        "error": "" if result.get("ok") else (result.get("error") or result.get("message")),
    }
    save_scene_job(project_name, scene_id, job)
    return {"ok": bool(result.get("ok")), "message": result.get("message", ""), "data": {"job": job}, "error": job["error"]}


def poll_veo_scene_job(project_name: str, api_key: str, scene_id: str = "scene_01") -> dict[str, Any]:
    loaded = load_scene_jobs(project_name)
    job = (loaded.get("data", {}).get("jobs", {}) or {}).get(scene_id)
    if not job:
        return {"ok": False, "message": "Scene job not found", "data": {}, "error": "missing_scene_job"}
    result = poll_render_status(job.get("job_id"), api_key=api_key)
    if result.get("ok"):
        job["status"] = result.get("data", {}).get("status", "Rendering")
        job["updated_at"] = _now()
        job["error"] = ""
    else:
        job["status"] = "failed"
        job["error"] = result.get("error") or result.get("message")
        job["updated_at"] = _now()
    save_scene_job(project_name, scene_id, job)
    return {"ok": bool(result.get("ok")), "message": result.get("message", ""), "data": {"job": job}, "error": job.get("error", "")}


def download_veo_scene_result(project_name: str, api_key: str, scene_id: str = "scene_01") -> dict[str, Any]:
    loaded = load_scene_jobs(project_name)
    job = (loaded.get("data", {}).get("jobs", {}) or {}).get(scene_id)
    if not job:
        return {"ok": False, "message": "Scene job not found", "data": {}, "error": "missing_scene_job"}
    output = scene_output_path(project_name, scene_id)
    result = download_render_result(job.get("job_id"), output, api_key=api_key)
    if result.get("ok"):
        job["status"] = "completed"
        job["output_path"] = result.get("data", {}).get("path", str(output))
        job["updated_at"] = _now()
        job["error"] = ""
    else:
        job["error"] = result.get("error") or result.get("message")
        job["updated_at"] = _now()
    save_scene_job(project_name, scene_id, job)
    return {"ok": bool(result.get("ok")), "message": result.get("message", ""), "data": {"job": job, "path": str(output)}, "error": job.get("error", "")}
