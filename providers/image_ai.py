import base64
import hashlib
import importlib.metadata
import json
import os
import time
from pathlib import Path
from typing import Any, Dict

import requests
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
IMAGE_CACHE_DIR = ROOT / "outputs" / "cache" / "images"
DEFAULT_NEGATIVE_PROMPT = (
    "bad anatomy, extra fingers, deformed hands, deformed face, low quality, blurry, "
    "duplicate character, inconsistent character, watermark, text artifacts, storyboard, comic, manga, "
    "split screen, contact sheet, tiled frames, cinematic strip, multi-panel layout, duplicated frame, "
    "repeated composition, grid, gallery, UI overlay, subtitles, numbers, watermarks, icons, logos, "
    "text, labels, debug overlay, frame counters, shot sheet, film strip, collage, storyboard page"
)

VISUAL_MODE = "cinematic_live_action_realism_v3"
VISUAL_MODE_PROMPT_PREFIX = (
    "Ultra realistic cinematic live-action film still. "
    "Real human anatomy. "
    "Natural skin texture. "
    "Professional movie lighting. "
    "No meme. "
    "No cartoon. "
    "No anime. "
    "No exaggerated eyes. "
    "No reaction face. "
    "No thumbnail design. "
    "No social media overlay. "
    "No subtitles. "
    "No text. "
    "No emoji. "
    "No symbols. "
    "No UI. "
    "No score. "
    "No debug text. "
    "No watermark."
)
SINGLE_FRAME_PROMPT_RULE = (
    "single cinematic fullscreen frame, one continuous real-world camera shot, "
    "NOT a storyboard or multi-panel composition, no text inside the image, no numbers, no UI overlay"
)
FORBIDDEN_PROVIDER_PROMPT_TERMS = {
    "hook": "emotional lyric moment",
    "viral": "cinematic",
    "thumbnail": "film still",
    "meme": "grounded emotional realism",
    "tiktok text": "vertical cinematic framing",
    "reaction": "subtle grounded acting",
    "emoji": "natural expression",
    "score": "emotional intensity",
    "rating": "emotional intensity",
    "caption": "bottom-safe composition",
    "subtitle": "bottom-safe composition",
    "67/100": "emotional intensity",
}


class ImageProviderError(RuntimeError):
    def __init__(self, error_type: str, safe_message: str, provider: str = "", exception_type: str = "") -> None:
        super().__init__(safe_message)
        self.error_type = error_type
        self.safe_message = safe_message
        self.provider = provider
        self.exception_type = exception_type


def _safe_error_message(error: Exception, provider: str) -> tuple[str, str]:
    text = str(error or "").lower()
    if isinstance(error, ImageProviderError):
        return error.error_type, error.safe_message
    if "quota" in text or "rate limit" in text or "429" in text:
        return "quota_exceeded", f"{provider} quota or rate limit reached."
    if "401" in text or "403" in text or "api key" in text or "auth" in text or "permission" in text:
        return "auth_failed", f"{provider} API key was rejected or lacks image access."
    if "404" in text or "model" in text:
        return "model_unavailable", f"{provider} image model is unavailable for this account."
    if "timeout" in text:
        return "timeout", f"{provider} image request timed out."
    return "provider_error", f"{provider} image generation failed."


def _package_version(package_name: str) -> str:
    try:
        return importlib.metadata.version(package_name)
    except Exception:
        return "not_installed"


def _dedupe(values: list[str]) -> list[str]:
    return [value for value in dict.fromkeys(str(item).strip() for item in values if str(item or "").strip())]


def _gemini_image_model_candidates(settings: Dict[str, Any]) -> list[str]:
    configured = [
        settings.get("gemini_image_model", ""),
        os.getenv("GEMINI_IMAGE_MODEL", ""),
        *os.getenv("GEMINI_IMAGE_MODELS", "").split(","),
    ]
    known_public_candidates = [
        "gemini-2.5-flash-image-preview",
        "imagen-4.0-generate-001",
        "imagen-4.0-fast-generate-001",
        "imagen-3.0-generate-002",
    ]
    return _dedupe([*configured, *known_public_candidates])


def _openai_image_model_candidates(settings: Dict[str, Any]) -> list[str]:
    configured = [
        settings.get("openai_image_model", ""),
        os.getenv("OPENAI_IMAGE_MODEL", ""),
        *os.getenv("OPENAI_IMAGE_MODELS", "").split(","),
    ]
    return _dedupe([*configured, "gpt-image-1", "gpt-image-1-mini", "gpt-image-1.5", "dall-e-3"])


def _model_name(value: Any) -> str:
    raw = str(getattr(value, "name", "") or value or "").strip()
    return raw.replace("models/", "")


def _gemini_list_available_models(client: Any) -> list[str]:
    try:
        models = client.models.list()
        names = []
        for model in models:
            name = _model_name(model)
            if name:
                names.append(name)
        return _dedupe(names)
    except Exception:
        return []


def detect_image_provider_capability(provider: str, settings: Dict[str, Any] | None = None) -> Dict[str, Any]:
    settings = settings or {}
    provider = (provider or "offline").lower()
    if provider in {"gemini_image", "gemini_images"}:
        api_key = settings.get("gemini_api_key") or (os.getenv("GEMINI_API_KEY", "") if settings.get("allow_env_key") else "")
        diagnostics = {
            "provider": "gemini_image",
            "requested_model": settings.get("gemini_image_model") or os.getenv("GEMINI_IMAGE_MODEL", ""),
            "actual_model": "",
            "provider_available": bool(api_key),
            "image_generation_supported": False,
            "sdk_version": _package_version("google-genai"),
            "available_models": [],
            "model_candidates": _gemini_image_model_candidates(settings),
            "fallback_reason": "" if api_key else "missing_api_key",
        }
        if not api_key:
            return diagnostics
        try:
            from google import genai  # type: ignore

            client = genai.Client(api_key=api_key)
            available = _gemini_list_available_models(client)
            diagnostics["available_models"] = available
            if available:
                candidate_set = set(_gemini_image_model_candidates(settings))
                image_like = [name for name in available if any(marker in name.lower() for marker in ("image", "imagen"))]
                matched = next((name for name in _gemini_image_model_candidates(settings) if name in available), "")
                diagnostics["actual_model"] = matched or (image_like[0] if image_like else "")
                diagnostics["image_generation_supported"] = bool(diagnostics["actual_model"])
                diagnostics["fallback_reason"] = "" if diagnostics["image_generation_supported"] else "no_image_capable_model_listed"
            else:
                diagnostics["actual_model"] = _gemini_image_model_candidates(settings)[0]
                diagnostics["image_generation_supported"] = True
                diagnostics["fallback_reason"] = "model_list_unavailable_try_configured_model"
            return diagnostics
        except Exception as error:
            error_type, safe = _safe_error_message(error, "Gemini")
            diagnostics["provider_available"] = False
            diagnostics["fallback_reason"] = error_type
            diagnostics["safe_error_message"] = safe
            diagnostics["sdk_exception_type"] = type(error).__name__
            return diagnostics
    if provider == "openai_images":
        api_key = settings.get("openai_api_key") or (os.getenv("OPENAI_API_KEY", "") if settings.get("allow_env_key") else "")
        model = _openai_image_model_candidates(settings)[0]
        return {
            "provider": "openai_images",
            "requested_model": settings.get("openai_image_model") or os.getenv("OPENAI_IMAGE_MODEL", ""),
            "actual_model": model,
            "provider_available": bool(api_key),
            "image_generation_supported": bool(api_key),
            "sdk_version": "http_api",
            "model_candidates": _openai_image_model_candidates(settings),
            "fallback_reason": "" if api_key else "missing_api_key",
        }
    return {
        "provider": provider,
        "requested_model": "",
        "actual_model": "offline_placeholder",
        "provider_available": provider in {"offline", "manual"},
        "image_generation_supported": provider in {"offline", "manual"},
        "sdk_version": "",
        "fallback_reason": "offline_placeholder_selected" if provider in {"offline", "manual"} else "unsupported_provider",
    }


def _safe_name(value: str) -> str:
    cleaned = "".join(ch for ch in (value or "") if ch.isalnum() or ch in (" ", "-", "_")).strip()
    return cleaned.replace(" ", "_") or "image"


def _cache_key(provider: str, prompt: str, settings: Dict[str, Any]) -> str:
    payload = json.dumps({"provider": provider, "prompt": prompt, "settings": settings}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _enforce_single_frame_prompt(prompt: str) -> str:
    value = str(prompt or "").strip()
    lowered = value.lower()
    for forbidden, replacement in FORBIDDEN_PROVIDER_PROMPT_TERMS.items():
        if forbidden in lowered:
            value = value.replace(forbidden, replacement).replace(forbidden.title(), replacement)
            lowered = value.lower()
    if "single cinematic fullscreen frame" not in value.lower():
        value = f"{value}, {SINGLE_FRAME_PROMPT_RULE}"
    if VISUAL_MODE_PROMPT_PREFIX.lower() not in value.lower():
        value = f"{VISUAL_MODE_PROMPT_PREFIX} {value}"
    return value


def _write_prompt_sidecar(output_path: Path, prompt: str, negative_prompt: str, metadata: Dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar = output_path.with_suffix(".json")
    safe_metadata = {k: v for k, v in metadata.items() if "key" not in str(k).lower() and "token" not in str(k).lower() and "secret" not in str(k).lower()}
    sidecar.write_text(
        json.dumps(
            {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "metadata": safe_metadata,
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
    seed = int(hashlib.sha256(f"{provider}|{prompt}".encode("utf-8")).hexdigest()[:8], 16)
    warm_shift = seed % 36
    x_shift = ((seed >> 5) % 17 - 8) / 100
    light_shift = ((seed >> 11) % 19 - 9) / 100
    image = Image.new("RGB", (width, height), (20, 22, 28))
    draw = ImageDraw.Draw(image)
    for y in range(height):
        ratio = y / max(1, height - 1)
        r = int(22 + ratio * (22 + warm_shift * 0.25))
        g = int(24 + ratio * (14 + warm_shift * 0.12))
        b = int(32 + ratio * (38 - warm_shift * 0.15))
        draw.line((0, y, width, y), fill=(r, g, b))
    # Text-free cinematic fallback: single vertical frame, soft window light, one silhouette.
    glow_center = (int(width * (0.72 + light_shift)), int(height * (0.24 + abs(light_shift) * 0.25)))
    for radius, alpha in [(420, 28), (300, 38), (180, 54)]:
        bbox = (
            glow_center[0] - radius,
            glow_center[1] - radius,
            glow_center[0] + radius,
            glow_center[1] + radius,
        )
        draw.ellipse(bbox, fill=(min(255, 40 + alpha), min(255, 52 + alpha), min(255, 74 + alpha)))
    floor_y = int(height * 0.72)
    draw.rectangle((0, floor_y, width, height), fill=(16, 17, 22))
    body_x = int(width * (0.48 + x_shift))
    body_y = int(height * (0.48 + abs(x_shift) * 0.3))
    draw.ellipse((body_x - 54, body_y - 120, body_x + 54, body_y - 12), fill=(38, 35, 38))
    draw.rounded_rectangle((body_x - 82, body_y - 20, body_x + 82, body_y + 260), radius=56, fill=(34, 31, 35))
    window_x = int(width * (0.09 + ((seed >> 18) % 9) / 100))
    draw.rectangle((window_x, int(height * 0.16), window_x + int(width * 0.05), int(height * 0.66)), fill=(60, 62, 72))
    draw.rectangle((window_x + int(width * 0.05), int(height * 0.16), window_x + int(width * 0.31), int(height * 0.20)), fill=(72, 74, 84))
    draw.rectangle((window_x + int(width * 0.05), int(height * 0.22), window_x + int(width * 0.29), int(height * 0.65)), fill=(118 + warm_shift // 3, 101, 82))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return str(output_path)


def _normalize_to_jpg(input_path: Path, output_path: Path, target_ratio: str = "9:16") -> str:
    width, height = (1080, 1920) if target_ratio == "9:16" else _parse_size("1024x1536")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(input_path) as image:
        image = image.convert("RGB")
        ratio = max(width / image.width, height / image.height)
        resized = image.resize((int(image.width * ratio), int(image.height * ratio)))
        left = max(0, (resized.width - width) // 2)
        top = max(0, (resized.height - height) // 2)
        cropped = resized.crop((left, top, left + width, top + height))
        cropped.save(output_path, "JPEG", quality=92)
    return str(output_path)


def validate_image_file(path: str | Path, *, expected_aspect_ratio: str = "9:16") -> Dict[str, Any]:
    image_path = Path(path)
    result: Dict[str, Any] = {
        "ok": False,
        "path": str(image_path),
        "file_exists": image_path.is_file(),
        "file_size": 0,
        "width": 0,
        "height": 0,
        "aspect_ratio": 0.0,
        "error": "",
    }
    if not image_path.is_file():
        result["error"] = "missing_image_file"
        return result
    result["file_size"] = image_path.stat().st_size
    if result["file_size"] <= 0:
        result["error"] = "empty_image_file"
        return result
    try:
        with Image.open(image_path) as image:
            image.verify()
        with Image.open(image_path) as image:
            result["width"] = int(image.width)
            result["height"] = int(image.height)
            result["aspect_ratio"] = round(image.width / max(1, image.height), 4)
    except Exception:
        result["error"] = "image_not_readable"
        return result
    if result["width"] <= 0 or result["height"] <= 0:
        result["error"] = "invalid_dimensions"
        return result
    target = 9 / 16 if expected_aspect_ratio == "9:16" else result["aspect_ratio"]
    if abs(float(result["aspect_ratio"]) - target) > 0.09:
        result["error"] = "aspect_ratio_needs_normalization"
    result["ok"] = result["error"] in {"", "aspect_ratio_needs_normalization"}
    return result


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


def _openai_image(prompt: str, output_path: Path, settings: Dict[str, Any]) -> tuple[str, str]:
    api_key = settings.get("openai_api_key") or (os.getenv("OPENAI_API_KEY", "") if settings.get("allow_env_key") else "")
    if not api_key:
        raise ImageProviderError("missing_api_key", "OpenAI API key is missing.", "openai_images")
    models = _openai_image_model_candidates(settings)
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
            return decoded, model_name
        except Exception as error:
            last_error = error
            if "404" not in str(error) and "model" not in str(error).lower():
                raise
    error_type, safe_message = _safe_error_message(last_error or RuntimeError("unknown"), "OpenAI")
    raise ImageProviderError(error_type, safe_message, "openai_images", type(last_error).__name__ if last_error else "RuntimeError")


def _extract_gemini_generated_image(response: Any, output_path: Path) -> str | None:
    generated_images = getattr(response, "generated_images", None) or []
    for generated in generated_images:
        image = getattr(generated, "image", None)
        data = getattr(image, "image_bytes", None) or getattr(image, "data", None)
        if data:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(data)
            return str(output_path)
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
    return None


def _gemini_generate_with_model(client: Any, types: Any, model_name: str, prompt: str, output_path: Path) -> str:
    if model_name.lower().startswith("imagen"):
        config_cls = getattr(types, "GenerateImagesConfig", None)
        if not config_cls:
            raise ImageProviderError("sdk_method_mismatch", "Installed google-genai SDK does not support Imagen image generation.", "gemini_image")
        response = client.models.generate_images(
            model=model_name,
            prompt=prompt,
            config=config_cls(number_of_images=1, output_mime_type="image/jpeg", aspect_ratio="9:16"),
        )
    else:
        modality = getattr(types, "Modality", None)
        text_modality = getattr(modality, "TEXT", "TEXT") if modality else "TEXT"
        image_modality = getattr(modality, "IMAGE", "IMAGE") if modality else "IMAGE"
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=[text_modality, image_modality]),
        )
    decoded = _extract_gemini_generated_image(response, output_path)
    if not decoded:
        raise ImageProviderError("empty_image_response", "Gemini returned no image bytes.", "gemini_image")
    return decoded


def _gemini_image(prompt: str, output_path: Path, settings: Dict[str, Any]) -> tuple[str, str, Dict[str, Any]]:
    api_key = settings.get("gemini_api_key") or (os.getenv("GEMINI_API_KEY", "") if settings.get("allow_env_key") else "")
    if not api_key:
        raise ImageProviderError("missing_api_key", "Gemini API key is missing.", "gemini_image")
    capability: Dict[str, Any] = {"provider": "gemini_image", "sdk_version": _package_version("google-genai")}
    try:
        from google import genai  # type: ignore
        from google.genai import types  # type: ignore

        client = genai.Client(api_key=api_key)
        available_models = _gemini_list_available_models(client)
        capability["available_models"] = available_models
        candidates = _gemini_image_model_candidates(settings)
        if available_models:
            image_like = [name for name in available_models if any(marker in name.lower() for marker in ("image", "imagen"))]
            candidates = [name for name in candidates if name in available_models] or image_like
        if not candidates:
            capability["image_generation_supported"] = False
            raise ImageProviderError("model_unavailable", "No Gemini image-capable model is available for this API key.", "gemini_image")
        last_error: Exception | None = None
        for model_name in candidates:
            try:
                result = _gemini_generate_with_model(client, types, model_name, prompt, output_path)
                capability.update({"actual_model": model_name, "image_generation_supported": True})
                return result, model_name, capability
            except Exception as error:
                last_error = error
                if isinstance(error, ImageProviderError) and error.error_type in {"auth_failed", "quota_exceeded"}:
                    raise
                continue
        raise last_error or ImageProviderError("model_unavailable", "Gemini image generation did not succeed with available models.", "gemini_image")
    except Exception as error:
        error_type, safe_message = _safe_error_message(error, "Gemini")
        if isinstance(error, ImageProviderError):
            error_type = error.error_type
            safe_message = error.safe_message
        capability.update({"image_generation_supported": False, "fallback_reason": error_type})
        raise ImageProviderError(error_type, safe_message, "gemini_image", type(error).__name__)


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
    prompt = _enforce_single_frame_prompt(prompt)
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

    diagnostic = generate_image_with_diagnostics(provider, prompt, str(output), settings)
    result = str((diagnostic.get("data") or {}).get("path") or output)

    if use_cache and Path(result).exists():
        IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(Path(result).read_bytes())
    return result


def generate_image_with_diagnostics(provider: str, prompt: str, output_path: str, settings: Dict[str, Any] | None = None) -> Dict[str, Any]:
    settings = settings or {}
    provider = (provider or "offline").lower()
    output = Path(output_path).with_suffix(".jpg")
    raw_output = output.with_suffix(".raw")
    prompt = _enforce_single_frame_prompt(prompt)
    negative_prompt = settings.get("negative_prompt") or DEFAULT_NEGATIVE_PROMPT
    character_note = settings.get("character_note", "")
    if character_note and character_note not in prompt:
        prompt = f"{prompt}, character consistency: {character_note}"
    _write_prompt_sidecar(output, prompt, negative_prompt, {"provider": provider, **{k: v for k, v in settings.items() if "key" not in k.lower()}})
    provider_used = provider
    fallback_used = False
    fallback_reason = ""
    error_type = ""
    safe_error_message = ""
    exception_type = ""
    requested_model = ""
    actual_model = ""
    provider_available = provider in {"manual", "offline"}
    image_generation_supported = provider in {"manual", "offline"}
    sdk_version = ""
    primary_diagnostics: Dict[str, Any] = {}
    try:
        if provider in {"manual", "offline"}:
            fallback_used = True
            fallback_reason = "offline_placeholder_selected"
            provider_used = "offline"
            actual_model = "offline_placeholder"
            generated = _placeholder_image(output, prompt, "offline_placeholder", settings.get("size", "1024x1536"))
        elif provider == "openai_images":
            primary_diagnostics = detect_image_provider_capability("openai_images", settings)
            requested_model = str(primary_diagnostics.get("requested_model") or "")
            generated, actual_model = _openai_image(prompt, raw_output, {**settings, "size": settings.get("size", "1024x1536")})
            provider_available = True
            image_generation_supported = True
        elif provider in {"gemini_image", "gemini_images"}:
            primary_diagnostics = detect_image_provider_capability("gemini_image", settings)
            requested_model = str(primary_diagnostics.get("requested_model") or "")
            try:
                generated, actual_model, gemini_capability = _gemini_image(prompt, raw_output, {**settings, "size": settings.get("size", "1024x1536")})
                primary_diagnostics.update(gemini_capability)
                provider_available = True
                image_generation_supported = True
            except Exception as gemini_error:
                openai_key = settings.get("openai_api_key") or (os.getenv("OPENAI_API_KEY", "") if settings.get("allow_env_key") else "")
                if openai_key:
                    fallback_reason = _safe_error_message(gemini_error, "Gemini")[0]
                    primary_diagnostics["fallback_reason"] = fallback_reason
                    generated, actual_model = _openai_image(prompt, raw_output, {**settings, "size": settings.get("size", "1024x1536")})
                    provider_used = "openai_images"
                    fallback_used = False
                    provider_available = True
                    image_generation_supported = True
                    primary_diagnostics["openai_fallback_active"] = True
                    primary_diagnostics["gemini_unavailable_reason"] = fallback_reason
                else:
                    raise gemini_error
        elif provider in {"flux", "sdxl"}:
            generated = _generic_http_image(provider, prompt, negative_prompt, raw_output, settings)
        else:
            raise ImageProviderError("unsupported_provider", f"{provider} is not supported for image generation.", provider)
        generated_path = Path(generated)
        if not fallback_used:
            generated = _normalize_to_jpg(generated_path, output, "9:16")
            if generated_path != output and generated_path.exists():
                try:
                    generated_path.unlink()
                except Exception:
                    pass
    except Exception as error:
        fallback_used = True
        error_type, safe_error_message = _safe_error_message(error, provider)
        if isinstance(error, ImageProviderError):
            error_type = error.error_type
            safe_error_message = error.safe_message
        exception_type = getattr(error, "exception_type", "") or type(error).__name__
        fallback_reason = error_type
        provider_used = "offline"
        actual_model = "offline_placeholder"
        generated = _placeholder_image(output, prompt, f"{provider}_{error_type}", settings.get("size", "1024x1536"))
    validation = validate_image_file(generated, expected_aspect_ratio="9:16")
    if validation.get("error") == "aspect_ratio_needs_normalization":
        generated = _normalize_to_jpg(Path(generated), output, "9:16")
        validation = validate_image_file(generated, expected_aspect_ratio="9:16")
    ok = bool(validation.get("ok"))
    if not ok and not fallback_used:
        fallback_used = True
        fallback_reason = validation.get("error", "validation_failed")
        error_type = fallback_reason
        safe_error_message = "Generated image failed validation; placeholder was used for this scene."
        provider_used = "offline"
        generated = _placeholder_image(output, prompt, f"{provider}_{fallback_reason}", settings.get("size", "1024x1536"))
        validation = validate_image_file(generated, expected_aspect_ratio="9:16")
        ok = bool(validation.get("ok"))
    return {
        "ok": ok,
        "message": "Image generated" if ok and not fallback_used else "Image placeholder fallback used",
        "data": {
            "path": str(generated),
            "visual_mode": VISUAL_MODE,
            "provider_requested": provider,
            "provider_used": provider_used,
            "requested_model": requested_model or str(primary_diagnostics.get("requested_model") or ""),
            "actual_model": actual_model or str(primary_diagnostics.get("actual_model") or ""),
            "provider_available": provider_available or bool(primary_diagnostics.get("provider_available")),
            "image_generation_supported": image_generation_supported or bool(primary_diagnostics.get("image_generation_supported")),
            "sdk_version": sdk_version or str(primary_diagnostics.get("sdk_version") or ""),
            "openai_fallback_active": bool(primary_diagnostics.get("openai_fallback_active")),
            "gemini_unavailable_reason": str(primary_diagnostics.get("gemini_unavailable_reason") or ""),
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
            "error_type": error_type,
            "safe_error_message": safe_error_message,
            "sdk_exception_type": exception_type,
            "provider_diagnostics": primary_diagnostics,
            "validation": validation,
            "prompt": prompt,
        },
        "error": "" if ok else validation.get("error", "image_generation_failed"),
    }
