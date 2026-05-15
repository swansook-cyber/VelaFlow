from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from core.provider_runtime import classify_provider_error


DEFAULT_VEO_MODEL = "veo-3.1-generate-preview"


def build_veo_payload(
    *,
    prompt: str,
    aspect_ratio: str = "9:16",
    duration_seconds: int = 8,
    scene_id: str = "",
    subtitle_timing: list[dict[str, Any]] | None = None,
    model: str = DEFAULT_VEO_MODEL,
) -> dict[str, Any]:
    return {
        "model": model,
        "prompt": str(prompt or "").strip(),
        "aspect_ratio": aspect_ratio,
        "duration_seconds": max(3, min(8, int(duration_seconds or 8))),
        "scene_id": scene_id,
        "subtitle_timing": subtitle_timing or [],
        "note": "Provider-ready Veo payload. API keys are supplied at runtime only.",
    }


def _missing_key() -> dict[str, Any]:
    return {
        "ok": False,
        "message": "Veo API key is missing. Add your own Gemini/Veo key in AI Settings.",
        "data": {"status": "Missing Key"},
        "error": "missing_api_key",
    }


def submit_render_job(payload: dict[str, Any], api_key: str = "", timeout_seconds: int = 60) -> dict[str, Any]:
    if not api_key:
        return _missing_key()
    try:
        try:
            from google import genai  # type: ignore
        except Exception as exc:
            return {
                "ok": False,
                "message": "google-genai package is not installed. Veo payload is ready, but no external API was called.",
                "data": {"status": "Provider Unavailable", "payload": payload},
                "error": str(exc),
            }
        client = genai.Client(api_key=api_key)
        operation = client.models.generate_videos(
            model=payload.get("model") or DEFAULT_VEO_MODEL,
            prompt=payload.get("prompt") or "",
            config={
                "aspect_ratio": payload.get("aspect_ratio") or "9:16",
                "duration_seconds": payload.get("duration_seconds") or 8,
            },
        )
        job_id = getattr(operation, "name", "") or getattr(operation, "operation", "") or str(operation)
        return {
            "ok": True,
            "message": "Veo render job submitted",
            "data": {
                "status": "Pending",
                "job_id": job_id,
                "submitted_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            },
            "error": "",
        }
    except Exception as exc:
        reason = classify_provider_error(exc)
        return {"ok": False, "message": f"Veo render job submit failed: {reason}", "data": {"payload": payload, "diagnostic": reason}, "error": reason}


def _get_operation(client: Any, job: Any) -> Any:
    if hasattr(job, "done") or hasattr(job, "response"):
        return client.operations.get(job)
    for call in (
        lambda: client.operations.get(job),
        lambda: client.operations.get(name=str(job)),
        lambda: client.operations.get(operation=str(job)),
    ):
        try:
            return call()
        except TypeError:
            continue
    return client.operations.get(str(job))


def poll_render_status(job: Any, api_key: str = "", timeout_seconds: int = 10) -> dict[str, Any]:
    if not api_key:
        return _missing_key()
    try:
        from google import genai  # type: ignore

        client = genai.Client(api_key=api_key)
        operation = _get_operation(client, job)
        job_id = getattr(operation, "name", "") or str(job)
        if bool(getattr(operation, "done", False)):
            return {"ok": True, "message": "Veo render completed", "data": {"status": "Completed", "job_id": job_id}, "error": ""}
        return {"ok": True, "message": "Veo render still processing", "data": {"status": "Rendering", "job_id": job_id}, "error": ""}
    except Exception as exc:
        reason = classify_provider_error(exc)
        return {"ok": False, "message": f"Veo status polling failed: {reason}", "data": {"diagnostic": reason}, "error": reason}


def download_render_result(job: Any, output_path: str | Path, api_key: str = "") -> dict[str, Any]:
    if not api_key:
        return _missing_key()
    try:
        from google import genai  # type: ignore

        client = genai.Client(api_key=api_key)
        operation = _get_operation(client, job)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        response = getattr(operation, "response", None)
        videos = getattr(response, "generated_videos", []) if response else []
        if not videos:
            return {"ok": False, "message": "Veo result is not ready yet", "data": {"status": "Rendering"}, "error": "not_ready"}
        video = videos[0]
        video_file = getattr(video, "video", None)
        if hasattr(client.files, "download") and video_file is not None:
            client.files.download(file=video_file)
        if hasattr(video_file, "save"):
            video_file.save(str(output))
        else:
            data = getattr(video_file, "video_bytes", None)
            if not data:
                return {"ok": False, "message": "Veo result has no downloadable video bytes", "data": {}, "error": "missing_video_bytes"}
            output.write_bytes(data)
        return {"ok": True, "message": "Veo render result downloaded", "data": {"path": str(output), "status": "Completed"}, "error": ""}
    except Exception as exc:
        reason = classify_provider_error(exc)
        return {"ok": False, "message": f"Veo result download failed: {reason}", "data": {"diagnostic": reason}, "error": reason}
