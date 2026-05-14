from __future__ import annotations

from typing import Any

from providers.ai_provider import normalize_provider


API_MODE_OWN_KEY = "Use My Own API Key"
API_MODE_BETA_KEY = "Use VelaFlow Beta Key"
API_MODES = [API_MODE_OWN_KEY, API_MODE_BETA_KEY]


def api_mode_label(value: str | None) -> str:
    return value if value in API_MODES else API_MODE_OWN_KEY


def provider_key_env_name(provider: str) -> str:
    normalized = normalize_provider(provider)
    return {"openai": "OPENAI_API_KEY", "xai": "XAI_API_KEY"}.get(normalized, "GEMINI_API_KEY")


def provider_env_key(settings: Any, provider: str) -> str:
    normalized = normalize_provider(provider)
    if normalized == "openai":
        return str(getattr(settings, "openai_api_key", "") or "")
    if normalized == "xai":
        return str(getattr(settings, "xai_api_key", "") or "")
    return str(getattr(settings, "gemini_api_key", "") or "")


def provider_model_name(settings: Any, provider: str) -> str:
    normalized = normalize_provider(provider)
    if normalized == "openai":
        return str(getattr(settings, "openai_text_model", "") or "gpt-4.1-mini")
    if normalized == "xai":
        return str(getattr(settings, "xai_text_model", "") or "grok-4.3")
    return str(getattr(settings, "gemini_model", "") or "gemini-2.5-flash")


def resolve_provider_credentials(
    *,
    settings: Any,
    provider: str,
    api_mode: str | None = None,
    user_api_keys: dict[str, str] | None = None,
) -> dict[str, Any]:
    normalized = normalize_provider(provider)
    mode = api_mode_label(api_mode)
    user_keys = user_api_keys or {}
    user_key = str(user_keys.get(normalized, "") or "").strip()
    env_key = provider_env_key(settings, normalized).strip()
    if mode == API_MODE_OWN_KEY and user_key:
        return {
            "provider": normalized,
            "api_key": user_key,
            "model": provider_model_name(settings, normalized),
            "api_mode": mode,
            "source": "user",
            "status": "Ready",
            "user_key_present": True,
            "velaflow_key_present": bool(env_key),
        }
    if mode == API_MODE_BETA_KEY and env_key:
        return {
            "provider": normalized,
            "api_key": env_key,
            "model": provider_model_name(settings, normalized),
            "api_mode": mode,
            "source": "velaflow_beta",
            "status": "Ready",
            "user_key_present": bool(user_key),
            "velaflow_key_present": True,
        }
    return {
        "provider": normalized,
        "api_key": "",
        "model": provider_model_name(settings, normalized),
        "api_mode": mode,
        "source": "offline_fallback",
        "status": "Offline Fallback",
        "user_key_present": bool(user_key),
        "velaflow_key_present": bool(env_key),
        "missing_key": provider_key_env_name(normalized) if mode == API_MODE_BETA_KEY else "User API Key",
    }
