from __future__ import annotations

import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from core.real_clip_pipeline import ensure_parent_dir, validate_mp4
from core.video_muxer import write_ffprobe_text


VEO_MODEL = os.getenv("VEO_MODEL", "veo-3.1-generate-preview")
PROVIDER_METHOD = "client.models.generate_videos"
LIVE_PROVIDER_TEST_PROMPT = (
    "A cinematic vertical video of a lonely woman sitting near a rainy window at night, "
    "soft warm lighting, subtle motion, realistic film look"
)


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
        clipped_duration = max(4, min(8, int(round(duration_seconds))))
        config: Any = {"aspectRatio": aspect_ratio, "durationSeconds": clipped_duration, "numberOfVideos": 1}
        if types is not None and hasattr(types, "GenerateVideosConfig"):
            config = types.GenerateVideosConfig(aspectRatio=aspect_ratio, durationSeconds=clipped_duration, numberOfVideos=1)
        debug["request_payload"] = {
            "model": model,
            "durationSeconds": clipped_duration,
            "aspectRatio": aspect_ratio,
            "numberOfVideos": 1,
            "provider_method": PROVIDER_METHOD,
        }
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
        LIVE_PROVIDER_TEST_PROMPT,
        output_path,
        duration_seconds=8,
        aspect_ratio="9:16",
        settings=settings or {},
    )


def run_live_veo_provider_test(debug_dir: str | Path, *, settings: dict[str, Any] | None = None) -> dict[str, Any]:
    debug_path = Path(debug_dir)
    debug_path.mkdir(parents=True, exist_ok=True)
    output_path = debug_path / "live_provider_test.mp4"
    response_path = debug_path / "live_provider_response.json"
    ffprobe_path = debug_path / "live_ffprobe.txt"
    result = test_veo_video_provider(output_path, settings=settings or {})
    payload = {
        "ok": bool(result.get("ok")),
        "provider_method": PROVIDER_METHOD,
        "model": (settings or {}).get("model") or (settings or {}).get("veo_model") or VEO_MODEL,
        "aspect_ratio": "9:16",
        "duration_seconds": 8,
        "prompt": LIVE_PROVIDER_TEST_PROMPT,
        "mp4_path": str(output_path),
        "response": result,
        "validation": (result.get("data") or {}).get("validation") or (result.get("data") or {}).get("debug", {}).get("validation") or {},
    }
    response_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if output_path.is_file():
        write_ffprobe_text(output_path, ffprobe_path)
    else:
        ffprobe_path.write_text("MP4 not created; ffprobe not run.\n", encoding="utf-8")
    payload["response_path"] = str(response_path)
    payload["ffprobe_path"] = str(ffprobe_path)
    return payload
