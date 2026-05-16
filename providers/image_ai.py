import base64
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict

import requests
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
IMAGE_CACHE_DIR = ROOT / "outputs" / "cache" / "images"
DEFAULT_NEGATIVE_PROMPT = (
    "bad anatomy, extra fingers, deformed hands, deformed face, low quality, blurry, "
    "duplicate character, inconsistent character, watermark, text artifacts"
)


def _safe_name(value: str) -> str:
    cleaned = "".join(ch for ch in (value or "") if ch.isalnum() or ch in (" ", "-", "_")).strip()
    return cleaned.replace(" ", "_") or "image"


def _cache_key(provider: str, prompt: str, settings: Dict[str, Any]) -> str:
    payload = json.dumps({"provider": provider, "prompt": prompt, "settings": settings}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _write_prompt_sidecar(output_path: Path, prompt: str, negative_prompt: str, metadata: Dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar = output_path.with_suffix(".json")
    sidecar.write_text(
        json.dumps(
            {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "metadata": metadata,
                "created_at": time.time(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _placeholder_image(output_path: Path, prompt: str, provider: str, size: str = "1024x1024") -> str:
    width, height = _parse_size(size)
    width = min(max(width, 512), 1536)
    height = min(max(height, 512), 1536)
    image = Image.new("RGB", (width, height), (18, 20, 27))
    draw = ImageDraw.Draw(image)
    accent = (63, 180, 255)
    draw.rectangle((0, 0, width - 1, height - 1), outline=accent, width=6)
    draw.rectangle((24, 24, width - 24, height - 24), outline=(66, 74, 90), width=2)
    title = f"{provider.upper()} PLACEHOLDER"
    lines = _wrap_text(prompt, max(28, width // 28))[:12]
    try:
        font_title = ImageFont.truetype("arial.ttf", max(24, width // 28))
        font_body = ImageFont.truetype("arial.ttf", max(18, width // 44))
    except Exception:
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()
    draw.text((42, 42), title, fill=accent, font=font_title)
    y = 110
    for line in lines:
        draw.text((42, y), line, fill=(235, 238, 245), font=font_body)
        y += max(24, height // 32)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return str(output_path)


def _wrap_text(text: str, max_chars: int) -> list[str]:
    words = (text or "").split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join(current + [word])
        if len(candidate) > max_chars and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines or ["No prompt"]


def _parse_size(size: str) -> tuple[int, int]:
    try:
        width, height = (size or "1024x1024").lower().split("x", 1)
        return int(width), int(height)
    except Exception:
        return 1024, 1024


def _decode_image_payload(data: Dict[str, Any], output_path: Path) -> str | None:
    candidates: list[Any] = []
    if "data" in data and isinstance(data["data"], list):
        candidates.extend(data["data"])
    if "images" in data and isinstance(data["images"], list):
        candidates.extend(data["images"])
    candidates.append(data)

    for item in candidates:
        if not isinstance(item, dict):
            continue
        b64_value = item.get("b64_json") or item.get("image") or item.get("image_base64") or item.get("base64")
        if b64_value:
            if "," in b64_value and b64_value.strip().startswith("data:"):
                b64_value = b64_value.split(",", 1)[1]
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(base64.b64decode(b64_value))
            return str(output_path)
        image_url = item.get("url") or item.get("output_url")
        if image_url:
            response = requests.get(image_url, timeout=120)
            response.raise_for_status()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(response.content)
            return str(output_path)
    return None


def _openai_image(prompt: str, output_path: Path, settings: Dict[str, Any]) -> str:
    api_key = settings.get("openai_api_key") or os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return _placeholder_image(output_path, prompt, "openai_missing_key", settings.get("size", "1024x1024"))
    requested_model = settings.get("openai_image_model") or os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1.5")
    models = list(dict.fromkeys([requested_model, "gpt-image-1.5", "gpt-image-1", "gpt-image-1-mini"]))
    last_error: Exception | None = None
    for model_name in models:
        body = {
            "model": model_name,
            "prompt": prompt,
            "size": settings.get("size") or os.getenv("OPENAI_IMAGE_SIZE", "1024x1024"),
            "quality": settings.get("quality") or os.getenv("OPENAI_IMAGE_QUALITY", "medium"),
            "n": 1,
        }
        if settings.get("background"):
            body["background"] = settings["background"]
        try:
            response = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=body,
                timeout=int(settings.get("timeout") or os.getenv("IMAGE_REQUEST_TIMEOUT", "180")),
            )
            response.raise_for_status()
            decoded = _decode_image_payload(response.json(), output_path)
            if not decoded:
                raise RuntimeError("OpenAI image response did not contain an image payload")
            return decoded
        except Exception as error:
            last_error = error
            if "404" not in str(error) and "model" not in str(error).lower():
                raise
    raise RuntimeError(f"OpenAI image generation failed: {last_error}")


def _gemini_image(prompt: str, output_path: Path, settings: Dict[str, Any]) -> str:
    api_key = settings.get("gemini_api_key") or os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return _placeholder_image(output_path, prompt, "gemini_image_missing_key", settings.get("size", "1024x1536"))
    model_name = settings.get("gemini_image_model") or os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image-preview")
    try:
        from google import genai  # type: ignore
        from google.genai import types  # type: ignore

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
        )
        candidates = getattr(response, "candidates", []) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", []) if content else []
            for part in parts:
                inline_data = getattr(part, "inline_data", None)
                data = getattr(inline_data, "data", None) if inline_data else None
                if data:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_bytes(data)
                    return str(output_path)
        raise RuntimeError("Gemini image response did not contain image bytes")
    except Exception:
        return _placeholder_image(output_path, prompt, "gemini_image_fallback", settings.get("size", "1024x1536"))


def _generic_http_image(provider: str, prompt: str, negative_prompt: str, output_path: Path, settings: Dict[str, Any]) -> str:
    env_prefix = provider.upper()
    endpoint = settings.get("endpoint") or os.getenv(f"{env_prefix}_API_URL", "")
    token = settings.get("api_key") or os.getenv(f"{env_prefix}_API_KEY", "")
    if not endpoint:
        return _placeholder_image(output_path, prompt, f"{provider}_missing_endpoint", settings.get("size", "1024x1024"))
    width, height = _parse_size(settings.get("size", "1024x1024"))
    body = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "width": width,
        "height": height,
        "seed": settings.get("seed"),
        "settings": settings,
    }
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.post(endpoint, headers=headers, json=body, timeout=int(settings.get("timeout") or os.getenv("IMAGE_REQUEST_TIMEOUT", "180")))
    response.raise_for_status()
    decoded = _decode_image_payload(response.json(), output_path)
    if not decoded:
        raise RuntimeError(f"{provider} response did not contain an image payload")
    return decoded


def generate_image(provider: str, prompt: str, output_path: str, settings: Dict[str, Any] | None = None) -> str:
    settings = settings or {}
    provider = (provider or "manual").lower()
    output = Path(output_path)
    negative_prompt = settings.get("negative_prompt") or DEFAULT_NEGATIVE_PROMPT
    character_note = settings.get("character_note", "")
    if character_note and character_note not in prompt:
        prompt = f"{prompt}, character consistency: {character_note}"

    _write_prompt_sidecar(output, prompt, negative_prompt, {"provider": provider, **settings})
    cache_id = _cache_key(provider, prompt, settings)
    cache_path = IMAGE_CACHE_DIR / f"{cache_id}{output.suffix or '.png'}"
    use_cache = settings.get("cache_enabled", os.getenv("IMAGE_CACHE_ENABLED", "true")).lower() not in {"0", "false", "no"} if isinstance(settings.get("cache_enabled", "true"), str) else bool(settings.get("cache_enabled", True))
    if use_cache and cache_path.exists():
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(cache_path.read_bytes())
        return str(output)

    if provider in {"manual", "offline"}:
        result = _placeholder_image(output, prompt, provider, settings.get("size", "1024x1024"))
    elif provider == "openai_images":
        result = _openai_image(prompt, output, settings)
    elif provider in {"gemini_image", "gemini_images"}:
        result = _gemini_image(prompt, output, settings)
    elif provider in {"flux", "sdxl"}:
        result = _generic_http_image(provider, prompt, negative_prompt, output, settings)
    else:
        result = _placeholder_image(output, prompt, f"{provider}_unsupported", settings.get("size", "1024x1024"))

    if use_cache and Path(result).exists():
        IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(Path(result).read_bytes())
    return result
