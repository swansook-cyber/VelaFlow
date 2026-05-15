from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from core.provider_runtime import classify_provider_error


DEFAULT_VEO_MODEL = "veo-3.1-generate-preview"
VEO_PROVIDER_METHOD = "client.models.generate_videos"


def _redact_error_text(text: Any) -> str:
    value = str(text or "")
    redacted = value.replace("\n", " ").replace("\r", " ")
    for token in ("api_key", "apikey", "key=", "x-goog-api-key"):
        redacted = redacted.replace(token, "[redacted-key-field]")
    return redacted[:900]


def _safe_error_detail(exc: Any, *, provider_method: str, model: str = "") -> dict[str, Any]:
    category = classify_provider_error(exc)
    exception_type = type(exc).__name__
    message = _redact_error_text(exc)
    return {
        "category": category,
        "provider_error_detail": f"{category}: {message}" if message else category,
        "sdk_exception_type": exception_type,
        "provider_method": provider_method,
        "request_model": model or DEFAULT_VEO_MODEL,
        "safe_message": message,
    }


def _missing_key_detail() -> dict[str, Any]:
    return {
        "category": "missing_api_key",
        "provider_error_detail": "missing_api_key: Add your own Gemini/Veo API key in AI Settings.",
        "sdk_exception_type": "",
        "provider_method": VEO_PROVIDER_METHOD,
        "request_model": DEFAULT_VEO_MODEL,
        "safe_message": "Add your own Gemini/Veo API key in AI Settings.",
    }


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
    detail = _missing_key_detail()
    return {
        "ok": False,
        "message": "Veo API key is missing. Add your own Gemini/Veo key in AI Settings.",
        "data": {"status": "Missing Key", "provider_error_detail": detail, "diagnostic": detail["category"]},
        "error": "missing_api_key",
    }


def test_veo_connection(api_key: str = "", model: str = DEFAULT_VEO_MODEL) -> dict[str, Any]:
    if not api_key:
        return _missing_key()
    try:
        from google import genai  # type: ignore

        client = genai.Client(api_key=api_key)
        has_generate_videos = hasattr(client.models, "generate_videos")
        return {
            "ok": bool(has_generate_videos),
            "message": "Veo SDK method is available" if has_generate_videos else "Google GenAI SDK is installed, but generate_videos method is unavailable.",
            "data": {
                "status": "Ready" if has_generate_videos else "SDK method mismatch",
                "provider_method": VEO_PROVIDER_METHOD,
                "request_model": model or DEFAULT_VEO_MODEL,
                "sdk_exception_type": "",
                "provider_error_detail": "" if has_generate_videos else {
                    "category": "SDK method mismatch",
                    "provider_error_detail": "SDK method mismatch: client.models.generate_videos is unavailable in this google-genai version.",
                    "sdk_exception_type": "",
                    "provider_method": VEO_PROVIDER_METHOD,
                    "request_model": model or DEFAULT_VEO_MODEL,
                    "safe_message": "client.models.generate_videos is unavailable in this google-genai version.",
                },
            },
            "error": "" if has_generate_videos else "sdk_method_mismatch",
        }
    except Exception as exc:
        detail = _safe_error_detail(exc, provider_method="genai.Client", model=model or DEFAULT_VEO_MODEL)
        return {"ok": False, "message": f"Veo connection test failed: {detail['category']}", "data": {"provider_error_detail": detail, "diagnostic": detail["category"]}, "error": detail["category"]}


def list_available_veo_models(api_key: str = "") -> dict[str, Any]:
    if not api_key:
        return _missing_key()
    try:
        from google import genai  # type: ignore

        client = genai.Client(api_key=api_key)
        models_iter = client.models.list()
        models = []
        for model in models_iter:
            name = str(getattr(model, "name", "") or getattr(model, "model", "") or model)
            display_name = str(getattr(model, "display_name", "") or getattr(model, "displayName", "") or "")
            combined = f"{name} {display_name}".lower()
            if "veo" in combined or "video" in combined:
                models.append({"name": name, "display_name": display_name})
        return {
            "ok": True,
            "message": "Available Veo/video models loaded" if models else "No Veo/video models returned for this account.",
            "data": {
                "models": models,
                "provider_method": "client.models.list",
                "request_model": "",
                "provider_error_detail": "" if models else "No Veo/video models returned. The account may not have Veo access, the region may be unsupported, or the SDK may not expose video models.",
            },
            "error": "",
        }
    except Exception as exc:
        detail = _safe_error_detail(exc, provider_method="client.models.list", model="")
        return {"ok": False, "message": f"Available Veo models check failed: {detail['category']}", "data": {"models": [], "provider_error_detail": detail, "diagnostic": detail["category"]}, "error": detail["category"]}


def submit_render_job(payload: dict[str, Any], api_key: str = "", timeout_seconds: int = 60) -> dict[str, Any]:
    if not api_key:
        return _missing_key()
    model = payload.get("model") or DEFAULT_VEO_MODEL
    try:
        try:
            from google import genai  # type: ignore
        except Exception as exc:
            detail = _safe_error_detail(exc, provider_method="import google.genai", model=model)
            return {
                "ok": False,
                "message": "google-genai package is not installed. Veo payload is ready, but no external API was called.",
                "data": {"status": "Provider Unavailable", "payload": payload, "provider_error_detail": detail, "diagnostic": detail["category"]},
                "error": detail["category"],
            }
        client = genai.Client(api_key=api_key)
        operation = client.models.generate_videos(
            model=model,
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
                "provider_method": VEO_PROVIDER_METHOD,
                "request_model": model,
                "sdk_exception_type": "",
            },
            "error": "",
        }
    except Exception as exc:
        detail = _safe_error_detail(exc, provider_method=VEO_PROVIDER_METHOD, model=model)
        return {"ok": False, "message": f"Veo render job submit failed: {detail['category']}", "data": {"payload": payload, "diagnostic": detail["category"], "provider_error_detail": detail}, "error": detail["category"]}


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
            return {"ok": True, "message": "Veo render completed", "data": {"status": "Completed", "job_id": job_id, "provider_method": "client.operations.get"}, "error": ""}
        return {"ok": True, "message": "Veo render still processing", "data": {"status": "Rendering", "job_id": job_id, "provider_method": "client.operations.get"}, "error": ""}
    except Exception as exc:
        detail = _safe_error_detail(exc, provider_method="client.operations.get", model="")
        return {"ok": False, "message": f"Veo status polling failed: {detail['category']}", "data": {"diagnostic": detail["category"], "provider_error_detail": detail}, "error": detail["category"]}


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
            return {"ok": False, "message": "Veo result is not ready yet", "data": {"status": "Rendering", "provider_method": "client.operations.get", "provider_error_detail": "not_ready: Veo result is still rendering."}, "error": "not_ready"}
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
        detail = _safe_error_detail(exc, provider_method="client.operations.get/client.files.download", model="")
        return {"ok": False, "message": f"Veo result download failed: {detail['category']}", "data": {"diagnostic": detail["category"], "provider_error_detail": detail}, "error": detail["category"]}
