from __future__ import annotations

from typing import Any


API_QUALITY_WARNING = (
    "API generation is unavailable. VelaFlow stopped to protect output quality. "
    "Please check your API key or provider settings."
)

STATUS_API_READY = "API Ready"
STATUS_MISSING_KEY = "Missing API Key"
STATUS_PROVIDER_ERROR = "Provider Error"
STATUS_RATE_LIMITED = "Rate Limited"
STATUS_DEMO = "Offline Demo Mode"
DEMO_LABEL = "Demo / Offline Preview"


def classify_api_error(error: Any) -> str:
    message = str(error or "").lower()
    if any(token in message for token in ["rate limit", "rate_limit", "quota", "resource exhausted", "429"]):
        return STATUS_RATE_LIMITED
    if any(token in message for token in ["api key", "apikey", "unauthorized", "401", "forbidden", "invalid credential", "permission"]):
        return STATUS_PROVIDER_ERROR
    return STATUS_PROVIDER_ERROR


def build_api_quality_gate(
    *,
    api_key: str = "",
    demo_mode: bool = False,
    provider_error: Any = "",
    runtime_ready: bool | None = None,
    provider: str = "",
    key_source: str = "",
) -> dict[str, Any]:
    """Describe whether a production generator may continue without silent fallback."""
    if demo_mode:
        return {
            "ok": True,
            "status": STATUS_DEMO,
            "message": DEMO_LABEL,
            "warning": DEMO_LABEL,
            "demo_mode": True,
            "offline_allowed": True,
            "provider": provider,
            "key_source": key_source,
            "error": "",
        }

    if not str(api_key or "").strip():
        return {
            "ok": False,
            "status": STATUS_MISSING_KEY,
            "message": API_QUALITY_WARNING,
            "warning": API_QUALITY_WARNING,
            "demo_mode": False,
            "offline_allowed": False,
            "provider": provider,
            "key_source": key_source,
            "error": "API key missing",
        }

    if provider_error:
        status = classify_api_error(provider_error)
        return {
            "ok": False,
            "status": status,
            "message": API_QUALITY_WARNING,
            "warning": API_QUALITY_WARNING,
            "demo_mode": False,
            "offline_allowed": False,
            "provider": provider,
            "key_source": key_source,
            "error": str(provider_error),
        }

    if runtime_ready is False:
        return {
            "ok": False,
            "status": STATUS_PROVIDER_ERROR,
            "message": API_QUALITY_WARNING,
            "warning": API_QUALITY_WARNING,
            "demo_mode": False,
            "offline_allowed": False,
            "provider": provider,
            "key_source": key_source,
            "error": "Provider runtime is not ready",
        }

    return {
        "ok": True,
        "status": STATUS_API_READY,
        "message": "API provider is ready.",
        "warning": "",
        "demo_mode": False,
        "offline_allowed": False,
        "provider": provider,
        "key_source": key_source,
        "error": "",
    }


def production_blocked_result(gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": False,
        "message": gate.get("message") or API_QUALITY_WARNING,
        "data": {},
        "error": gate.get("error") or gate.get("status") or STATUS_PROVIDER_ERROR,
        "provider_status": gate,
    }
