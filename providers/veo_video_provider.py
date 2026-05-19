from __future__ import annotations

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from core.real_clip_pipeline import ensure_parent_dir, validate_mp4


VEO_MODEL = os.getenv("VEO_MODEL", "veo-3.1-generate-preview")
PROVIDER_METHOD = "client.models.generate_videos"


def _api_key(settings: dict[str, Any] | None = None) -> str:
    settings = settings or {}
    return str(
        settings.get("gemini_api_key")
        or settings.get("google_api_key")
        or settings.get("veo_api_key")
        or os.getenv("GEMINI_API_KEY", "")
        or os.getenv("GOOGLE_API_KEY", "")
        or os.getenv("VEO_API_KEY", "")
    ).strip()


def _operation_name(operation: Any) -> str:
    if isinstance(operation, str):
        return operation
    for attr in ("name", "operation", "id"):
        value = getattr(operation, attr, "")
        if value:
            return str(value)
    if isinstance(operation, dict):
        for key in ("name", "operation", "id", "job_id"):
            if operation.get(key):
                return str(operation[key])
    return str(operation or "")


def _get_operation(client: Any, operation: Any) -> Any:
    name = _operation_name(operation)
    for call in (
        lambda: client.operations.get(operation),
        lambda: client.operations.get(name=name),
        lambda: client.operations.get(operation=name),
        lambda: client.operations.get(name),
    ):
        try:
            return call()
        except TypeError:
            continue
    return client.operations.get(operation)


def _download_operation_video(client: Any, operation: Any, output_path: Path) -> bool:
    response = getattr(operation, "response", None)
    videos = getattr(response, "generated_videos", []) if response else []
    if not videos:
        return False
    video_file = getattr(videos[0], "video", None)
    if video_file is None:
        return False
    ensure_parent_dir(output_path)
    if hasattr(client.files, "download"):
        client.files.download(file=video_file)
    if hasattr(video_file, "save"):
        video_file.save(str(output_path))
        return output_path.is_file()
    data = getattr(video_file, "video_bytes", None) or getattr(video_file, "data", None)
    if data:
        output_path.write_bytes(data)
        return True
    return False


def generate_veo_video_shot(
    prompt: str,
    output_path: str | Path,
    *,
    duration_seconds: float = 4.0,
    aspect_ratio: str = "9:16",
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = settings or {}
    output = Path(output_path)
    key = _api_key(settings)
    model = str(settings.get("model") or settings.get("veo_model") or VEO_MODEL)
    debug = {
        "provider": "gemini_veo",
        "provider_method": PROVIDER_METHOD,
        "model": model,
        "api_key_detected": bool(key),
        "request_status": "pending",
        "polling_status": "",
        "download_status": "",
        "validation": {},
        "error": "",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    if not key:
        debug["request_status"] = "failed"
        debug["error"] = "Veo API key missing"
        return {"ok": False, "message": "Veo API key missing", "data": {"debug": debug, "path": str(output)}, "error": "missing_api_key"}
    try:
        from google import genai  # type: ignore

        try:
            from google.genai import types  # type: ignore
        except Exception:
            types = None
        client = genai.Client(api_key=key)
        config: Any = {"aspect_ratio": aspect_ratio, "duration_seconds": max(2, min(8, int(round(duration_seconds))))}
        if types is not None and hasattr(types, "GenerateVideosConfig"):
            config = types.GenerateVideosConfig(aspect_ratio=aspect_ratio, duration_seconds=max(2, min(8, int(round(duration_seconds)))))
        operation = client.models.generate_videos(model=model, prompt=prompt, config=config)
        debug["request_status"] = "submitted"
        debug["operation_name"] = _operation_name(operation)
        timeout = int(settings.get("timeout_seconds") or os.getenv("VEO_TIMEOUT_SECONDS", "900"))
        interval = max(2, int(settings.get("poll_interval_seconds") or os.getenv("VEO_POLL_INTERVAL_SECONDS", "10")))
        started = time.time()
        while time.time() - started <= timeout:
            operation = _get_operation(client, operation)
            debug["polling_status"] = "done" if bool(getattr(operation, "done", False)) else "rendering"
            if bool(getattr(operation, "done", False)):
                if not _download_operation_video(client, operation, output):
                    debug["download_status"] = "failed"
                    debug["error"] = "Provider returned no MP4"
                    return {"ok": False, "message": "Provider returned no MP4", "data": {"debug": debug, "path": str(output)}, "error": "provider_returned_no_mp4"}
                debug["download_status"] = "downloaded"
                validation = validate_mp4(output, min_duration=1.0, min_file_size=100 * 1024)
                debug["validation"] = validation
                if not validation.get("valid_mp4") or not validation.get("has_video"):
                    debug["error"] = "Provider MP4 failed ffprobe validation"
                    return {"ok": False, "message": "Provider MP4 failed ffprobe validation", "data": {"debug": debug, "path": str(output), "validation": validation}, "error": "provider_mp4_invalid"}
                return {"ok": True, "message": "Veo video shot generated", "data": {"path": str(output), "debug": debug, "validation": validation}, "error": ""}
            time.sleep(interval)
        debug["error"] = "Video generation timed out"
        return {"ok": False, "message": "Video generation timed out", "data": {"debug": debug, "path": str(output)}, "error": "provider_timeout"}
    except Exception as exc:
        debug["request_status"] = "failed"
        debug["error"] = str(exc).replace(key, "[redacted]")[:800]
        return {"ok": False, "message": debug["error"], "data": {"debug": debug, "path": str(output)}, "error": type(exc).__name__}


def test_veo_video_provider(output_path: str | Path, *, settings: dict[str, Any] | None = None) -> dict[str, Any]:
    return generate_veo_video_shot(
        "single continuous cinematic video shot, ultra realistic live-action, vertical 9:16, natural human motion, cinematic camera movement, emotional close-up, no text, no subtitles, no logo, no watermark, no split screen, no storyboard",
        output_path,
        duration_seconds=2,
        aspect_ratio="9:16",
        settings=settings or {},
    )
