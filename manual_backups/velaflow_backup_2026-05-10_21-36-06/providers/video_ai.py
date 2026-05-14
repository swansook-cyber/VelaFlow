import base64
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict

import requests


ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_VIDEO_PROVIDERS = {"manual", "offline", "kling", "runway", "luma", "pixverse", "veo", "google_flow"}
DEFAULT_VIDEO_NEGATIVE_PROMPT = (
    "warped face, changing identity, flicker, jitter, melted hands, extra fingers, "
    "bad anatomy, duplicate character, unstable camera, low quality, blurry frames, watermark"
)


def _write_sidecar(output_path: Path, prompt: str, metadata: Dict[str, Any]) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar = output_path.with_suffix(".json")
    sidecar.write_text(
        json.dumps(
            {
                "prompt": prompt,
                "metadata": metadata,
                "created_at": time.time(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return sidecar


def _write_slot_note(output_path: Path, prompt: str, metadata: Dict[str, Any]) -> Path:
    note_path = output_path.with_suffix(".video_slot.txt")
    lines = [
        f"Provider: {metadata.get('provider', '')}",
        f"Status: {metadata.get('status', '')}",
        f"Scene: {metadata.get('scene', '')}",
        f"Expected output: {output_path.name}",
        f"Duration: {metadata.get('duration_seconds', '')} seconds",
        f"Aspect ratio: {metadata.get('aspect_ratio', '')}",
        f"Source image: {metadata.get('image_path', '')}",
        "",
        "Prompt:",
        prompt or "",
        "",
        "Negative prompt:",
        metadata.get("negative_prompt", ""),
        "",
        "Notes:",
        metadata.get("reason", ""),
    ]
    note_path.write_text("\n".join(lines), encoding="utf-8")
    return note_path


def _placeholder_result(provider: str, prompt: str, image_path: str, output_path: Path, settings: Dict[str, Any], reason: str) -> str:
    metadata = {
        "provider": provider,
        "status": "placeholder",
        "reason": reason,
        "scene": settings.get("scene", ""),
        "image_path": image_path,
        "duration_seconds": settings.get("duration_seconds", 5),
        "aspect_ratio": settings.get("aspect_ratio", "16:9"),
        "negative_prompt": settings.get("negative_prompt") or DEFAULT_VIDEO_NEGATIVE_PROMPT,
        "character_note": settings.get("character_note", ""),
        "reference_image_path": settings.get("reference_image_path", ""),
        "output_path": str(output_path),
        "ready_for_render": False,
    }
    _write_sidecar(output_path, prompt, metadata)
    _write_slot_note(output_path, prompt, metadata)
    return str(output_path)


def _manual_result(prompt: str, image_path: str, output_path: Path, settings: Dict[str, Any]) -> str:
    manual_path = Path(settings.get("manual_video_path", "") or "")
    if manual_path.is_file():
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.suffix.lower() != manual_path.suffix.lower():
            output_path = output_path.with_suffix(manual_path.suffix.lower())
        shutil.copy2(manual_path, output_path)
        metadata = {
            "provider": "manual",
            "status": "ready",
            "scene": settings.get("scene", ""),
            "image_path": image_path,
            "manual_video_path": str(manual_path),
            "duration_seconds": settings.get("duration_seconds", 5),
            "aspect_ratio": settings.get("aspect_ratio", "16:9"),
            "negative_prompt": settings.get("negative_prompt") or DEFAULT_VIDEO_NEGATIVE_PROMPT,
            "output_path": str(output_path),
            "ready_for_render": True,
        }
        _write_sidecar(output_path, prompt, metadata)
        return str(output_path)
    return _placeholder_result("manual", prompt, image_path, output_path, settings, "Manual provider needs a local video file.")


def _decode_video_payload(data: Dict[str, Any], output_path: Path) -> str | None:
    candidates: list[Any] = []
    if isinstance(data.get("data"), list):
        candidates.extend(data["data"])
    if isinstance(data.get("videos"), list):
        candidates.extend(data["videos"])
    if isinstance(data.get("output"), list):
        candidates.extend(data["output"])
    candidates.append(data)

    for item in candidates:
        if not isinstance(item, dict):
            continue
        b64_value = item.get("b64_json") or item.get("video") or item.get("video_base64") or item.get("base64")
        if b64_value:
            if "," in b64_value and b64_value.strip().startswith("data:"):
                b64_value = b64_value.split(",", 1)[1]
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(base64.b64decode(b64_value))
            return str(output_path)
        video_url = item.get("url") or item.get("video_url") or item.get("output_url")
        if video_url:
            response = requests.get(video_url, timeout=300)
            response.raise_for_status()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(response.content)
            return str(output_path)
    return None


def _generic_http_video(provider: str, prompt: str, image_path: str, output_path: Path, settings: Dict[str, Any]) -> str:
    env_prefix = provider.upper()
    endpoint = settings.get("endpoint") or os.getenv(f"{env_prefix}_API_URL", "")
    token = settings.get("api_key") or os.getenv(f"{env_prefix}_API_KEY", "")
    if not endpoint:
        return _placeholder_result(provider, prompt, image_path, output_path, settings, f"{provider} API endpoint is not configured.")

    body = {
        "prompt": prompt,
        "negative_prompt": settings.get("negative_prompt") or DEFAULT_VIDEO_NEGATIVE_PROMPT,
        "image_path": image_path,
        "duration_seconds": settings.get("duration_seconds", 5),
        "aspect_ratio": settings.get("aspect_ratio", "16:9"),
        "motion_strength": settings.get("motion_strength", "medium"),
        "seed": settings.get("seed"),
        "settings": settings,
    }
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.post(endpoint, headers=headers, json=body, timeout=int(settings.get("timeout") or os.getenv("VIDEO_REQUEST_TIMEOUT", "300")))
    response.raise_for_status()
    data = response.json()
    decoded = _decode_video_payload(data, output_path)
    status = "ready" if decoded else "submitted"
    metadata = {
        "provider": provider,
        "status": status,
        "scene": settings.get("scene", ""),
        "image_path": image_path,
        "duration_seconds": settings.get("duration_seconds", 5),
        "aspect_ratio": settings.get("aspect_ratio", "16:9"),
        "negative_prompt": body["negative_prompt"],
        "response": data,
        "output_path": str(output_path),
        "ready_for_render": bool(decoded),
    }
    _write_sidecar(output_path, prompt, metadata)
    if not decoded:
        _write_slot_note(output_path, prompt, metadata)
    return decoded or str(output_path)


def generate_video(provider: str, prompt: str, image_path: str, output_path: str, settings: Dict[str, Any] | None = None) -> str:
    settings = settings or {}
    provider = (provider or "manual").lower()
    output = Path(output_path)
    if provider not in SUPPORTED_VIDEO_PROVIDERS:
        return _placeholder_result(provider, prompt, image_path, output, settings, f"Unsupported provider: {provider}")

    character_note = settings.get("character_note", "")
    if character_note and character_note not in prompt:
        prompt = f"{prompt}\n\nCharacter lock: {character_note}"

    if provider == "manual":
        return _manual_result(prompt, image_path, output, settings)
    if provider == "offline":
        return _placeholder_result("offline", prompt, image_path, output, settings, "Offline video mode creates a render slot only.")
    return _generic_http_video(provider, prompt, image_path, output, settings)
