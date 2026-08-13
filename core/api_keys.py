from __future__ import annotations

import json
import os
import re
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
    "remember": "velaflow_remember_api_keys",
}
REMEMBER_API_KEYS_DEFAULT = False


def api_key_persistence_enabled(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def build_browser_api_key_storage_script(
    provider: str,
    api_mode: str,
    api_key: str = "",
    *,
    remember: bool = REMEMBER_API_KEYS_DEFAULT,
) -> str:
    """Build browser storage commands without persisting secrets by default."""
    normalized = normalize_provider(provider)
    statements = [
        f"localStorage.setItem({json.dumps(LOCAL_STORAGE_KEYS['api_mode'])}, {json.dumps(api_mode_label(api_mode))});",
        f"localStorage.setItem({json.dumps(LOCAL_STORAGE_KEYS['provider'])}, {json.dumps(normalized)});",
        f"localStorage.setItem({json.dumps(LOCAL_STORAGE_KEYS['remember'])}, {json.dumps('true' if remember else 'false')});",
    ]
    if remember and str(api_key or "").strip():
        storage_key = LOCAL_STORAGE_KEYS.get(normalized, LOCAL_STORAGE_KEYS["gemini"])
        statements.append(f"localStorage.setItem({json.dumps(storage_key)}, {json.dumps(str(api_key).strip())});")
    elif not remember:
        for provider_name in ("gemini", "openai", "xai"):
            statements.append(f"localStorage.removeItem({json.dumps(LOCAL_STORAGE_KEYS[provider_name])});")
    return "\n".join(statements)


def saved_browser_api_keys(restored: Any) -> dict[str, str]:
    values = restored if isinstance(restored, dict) else {}
    return {
        provider: str(values.get(provider, "") or "").strip()
        for provider in ("gemini", "openai", "xai")
        if str(values.get(provider, "") or "").strip()
    }


def browser_api_key_restore_plan(restored: Any, *, use_saved_keys: bool = False) -> dict[str, Any]:
    """Keep legacy keys inactive unless persistence was opted in or use is explicit."""
    values = restored if isinstance(restored, dict) else {}
    saved = saved_browser_api_keys(values)
    remember = api_key_persistence_enabled(values.get("remember"))
    activate = remember or bool(use_saved_keys)
    return {
        "remember": remember,
        "active_keys": dict(saved) if activate else {},
        "pending_keys": {} if activate else dict(saved),
        "saved_keys_found": bool(saved),
        "source": "localStorage" if remember else "explicit_saved_keys" if use_saved_keys and saved else "legacy_saved_keys_detected" if saved else "localStorage_preferences_only",
    }


def redact_secret(value: Any, *secrets: str) -> str:
    """Redact known credentials and common API-key transports from diagnostics."""
    result = str(value or "")
    for secret in secrets:
        token = str(secret or "").strip()
        if token:
            result = result.replace(token, "[REDACTED]")
    result = re.sub(r"([?&]key=)[^&\s]+", r"\1[REDACTED]", result, flags=re.IGNORECASE)
    result = re.sub(r"(x-goog-api-key\s*[:=]\s*)[^\s,;]+", r"\1[REDACTED]", result, flags=re.IGNORECASE)
    result = re.sub(r"(authorization\s*[:=]\s*)(?:bearer\s+)?[^\s,;]+", r"\1[REDACTED]", result, flags=re.IGNORECASE)
    return result


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
