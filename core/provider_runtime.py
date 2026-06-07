from __future__ import annotations

from typing import Any

from core.api_quality_gate import API_QUALITY_WARNING, STATUS_API_READY, STATUS_MISSING_KEY, STATUS_PROVIDER_ERROR
from core.ffmpeg_utils import configure_moviepy_ffmpeg, ffmpeg_version
from providers.ai_provider import normalize_provider, provider_display_name
from providers.gemini_provider import GeminiTextProvider


def _import_status(module_name: str) -> tuple[bool, str]:
    try:
        __import__(module_name)
        return True, "available"
    except Exception as exc:
        return False, str(exc)


def build_provider_runtime_diagnostics(
    provider: str,
    api_key: str = "",
    *,
    api_mode: str = "",
    source: str = "",
) -> dict[str, Any]:
    """Return provider runtime readiness without exposing or persisting API keys."""
    normalized = normalize_provider(provider)
    key_present = bool(str(api_key or "").strip())
    diagnostics: dict[str, Any] = {
        "provider": normalized,
        "provider_label": provider_display_name(normalized),
        "api_mode": api_mode,
        "source": source or ("user" if key_present else "none"),
        "key_present": key_present,
        "runtime_ready": False,
        "status": STATUS_MISSING_KEY if not key_present else STATUS_API_READY,
        "message": API_QUALITY_WARNING if not key_present else "Runtime key is available",
        "checks": {},
    }
    if not key_present:
        return diagnostics

    if normalized == "gemini":
        client_exception = ""
        try:
            gemini_client = GeminiTextProvider(api_key=api_key)
            provider_diag = gemini_client.diagnostics()
            client_initialized = bool(provider_diag.get("client_initialized"))
            configure_result = str(provider_diag.get("configure_result") or "")
            client_init_result = str(provider_diag.get("client_initialization_result") or "")
            client_exception = str(provider_diag.get("client_initialization_error") or provider_diag.get("exception_message") or "")
        except Exception as exc:
            client_initialized = False
            configure_result = "exception"
            client_init_result = "failed"
            client_exception = f"{type(exc).__name__}: {exc}"
        veo_sdk_ok, veo_sdk_message = _import_status("google.genai")
        diagnostics["checks"] = {
            "Gemini runtime ready": client_initialized,
            "Gemini client initialized": client_initialized,
            "Veo render capable": veo_sdk_ok,
            "Veo SDK available": veo_sdk_ok,
        }
        diagnostics["gemini_runtime_ready"] = bool(client_initialized)
        diagnostics["gemini_client_initialized"] = bool(client_initialized)
        diagnostics["gemini_configure_result"] = configure_result
        diagnostics["gemini_client_initialization_result"] = client_init_result
        diagnostics["gemini_exception_message"] = client_exception
        diagnostics["veo_render_capable"] = bool(veo_sdk_ok)
        diagnostics["runtime_ready"] = bool(client_initialized)
        if client_initialized and veo_sdk_ok:
            diagnostics["status"] = STATUS_API_READY
            diagnostics["message"] = "Gemini runtime ready; Veo SDK available"
        elif client_initialized:
            diagnostics["status"] = STATUS_API_READY
            diagnostics["message"] = f"Gemini runtime ready; Veo unavailable: {veo_sdk_message}"
        else:
            diagnostics["status"] = STATUS_PROVIDER_ERROR
            diagnostics["message"] = f"Gemini client initialization failed: {client_exception or client_init_result or 'unknown error'}"
        return diagnostics

    if normalized == "openai":
        sdk_ok, sdk_message = _import_status("openai")
        diagnostics["checks"] = {"OpenAI runtime ready": sdk_ok}
        diagnostics["runtime_ready"] = bool(sdk_ok)
        diagnostics["status"] = STATUS_API_READY if sdk_ok else STATUS_PROVIDER_ERROR
        diagnostics["message"] = "OpenAI runtime ready" if sdk_ok else f"OpenAI SDK unavailable: {sdk_message}"
        return diagnostics

    if normalized == "xai":
        # xAI uses an OpenAI-compatible HTTP interface in this project.
        sdk_ok, sdk_message = _import_status("openai")
        diagnostics["checks"] = {"xAI Grok runtime ready": sdk_ok}
        diagnostics["runtime_ready"] = bool(sdk_ok)
        diagnostics["status"] = STATUS_API_READY if sdk_ok else STATUS_PROVIDER_ERROR
        diagnostics["message"] = "xAI Grok runtime ready" if sdk_ok else f"OpenAI-compatible SDK unavailable: {sdk_message}"
        return diagnostics

    return diagnostics


def build_ffmpeg_runtime_diagnostics(ffmpeg_path: str = "ffmpeg") -> dict[str, Any]:
    """Return FFmpeg/MoviePy readiness for cloud runtime diagnostics."""
    version_info = ffmpeg_version(ffmpeg_path)
    moviepy_info = configure_moviepy_ffmpeg(ffmpeg_path)
    ready = bool(version_info.get("ok") and moviepy_info.get("ok"))
    return {
        "runtime_ready": ready,
        "status": "Ready" if ready else "Missing FFmpeg",
        "ffmpeg_installed": bool(version_info.get("ok")),
        "ffmpeg_path": version_info.get("path", ""),
        "ffmpeg_version": version_info.get("version", ""),
        "ffmpeg_error": version_info.get("error", ""),
        "moviepy_ffmpeg_access": bool(moviepy_info.get("ok")),
        "imageio_ffmpeg_access": bool(moviepy_info.get("imageio_ffmpeg_access", False)),
        "imageio_ffmpeg_message": moviepy_info.get("imageio_ffmpeg_message", ""),
        "moviepy_access": bool(moviepy_info.get("moviepy_access", False)),
        "moviepy_message": moviepy_info.get("moviepy_message", ""),
    }


def classify_provider_error(error: Any) -> str:
    message = str(error or "").lower()
    if any(token in message for token in ["api key", "apikey", "unauthorized", "401", "permission", "forbidden", "invalid credential"]):
        return "auth failed"
    if any(token in message for token in ["quota", "resource exhausted", "429", "rate limit"]):
        return "quota exceeded"
    if any(token in message for token in ["invalid argument", "bad request", "400", "invalid request"]):
        return "invalid request"
    if any(token in message for token in ["region", "location", "country", "not available in your"]):
        return "unsupported region"
    if any(token in message for token in ["quota", "billing", "account", "not enabled", "unsupported"]):
        return "unsupported account"
    if any(token in message for token in ["not found", "404", "model"]):
        return "model not found"
    if any(token in message for token in ["generate_videos", "attributeerror", "unexpected keyword", "method", "not callable"]):
        return "SDK method mismatch"
    return "provider error"
