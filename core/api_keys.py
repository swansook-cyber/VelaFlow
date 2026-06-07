from __future__ import annotations

import os
import sys
from typing import Any

from core.api_quality_gate import API_QUALITY_WARNING, STATUS_MISSING_KEY


API_MODE_OWN_KEY = "Use My Own API Key"
API_MODE_BETA_KEY = "Use VelaFlow Beta Key"
API_MODES = [API_MODE_OWN_KEY, API_MODE_BETA_KEY]
LOCAL_STORAGE_KEYS = {
    "api_mode": "velaflow_api_mode",
    "provider": "velaflow_ai_provider",
    "gemini": "velaflow_gemini_key",
    "openai": "velaflow_openai_key",
    "xai": "velaflow_xai_key",
}


def normalize_provider(provider: str | None = None) -> str:
    value = (provider or os.getenv("DEFAULT_AI_PROVIDER") or "gemini").strip().lower()
    value = value.replace(" ", "_").replace("-", "_")
    if value in {"openai", "openai_gpt", "gpt"}:
        return "openai"
    if value in {"xai", "xai_grok", "grok", "grok_ai"}:
        return "xai"
    return "gemini"


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


def mask_api_key(api_key: str | None) -> str:
    value = str(api_key or "").strip()
    if not value:
        return "Missing"
    suffix = value[-4:] if len(value) >= 4 else value
    return f"Provided: ****{suffix}"


def resolve_gemini_api_key(settings: Any | None = None, session_state: Any | None = None) -> dict[str, Any]:
    """Resolve Gemini key without exposing the secret value in diagnostics."""
    state = session_state
    if state is None:
        try:
            if "streamlit" not in sys.modules:
                raise RuntimeError("streamlit not loaded")
            from streamlit.runtime.scriptrunner import get_script_run_ctx  # type: ignore

            if get_script_run_ctx() is None:
                raise RuntimeError("streamlit session unavailable")
            import streamlit as st  # type: ignore

            state = st.session_state
        except Exception:
            state = {}

    def _state_get(key: str, default: Any = "") -> Any:
        try:
            return state.get(key, default) if state is not None else default
        except Exception:
            return default

    user_keys = _state_get("user_api_keys", {}) or {}
    session_key = str(user_keys.get("gemini", "") or _state_get("gemini_api_key", "") or "").strip()
    if session_key:
        return {
            "api_key": session_key,
            "enabled": True,
            "source": "session",
            "fallback_reason": "",
            "key_present": True,
        }

    env_key = str(os.getenv("GEMINI_API_KEY") or (getattr(settings, "gemini_api_key", "") if settings is not None else "")).strip()
    if env_key:
        return {
            "api_key": env_key,
            "enabled": True,
            "source": "env",
            "fallback_reason": "",
            "key_present": True,
        }

    return {
        "api_key": "",
        "enabled": False,
        "source": "none",
        "fallback_reason": "Gemini API key not configured",
        "key_present": False,
    }


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
        "source": "none",
        "status": STATUS_MISSING_KEY,
        "user_key_present": bool(user_key),
        "velaflow_key_present": bool(env_key),
        "missing_key": provider_key_env_name(normalized) if mode == API_MODE_BETA_KEY else "User API Key",
        "warning": API_QUALITY_WARNING,
    }
