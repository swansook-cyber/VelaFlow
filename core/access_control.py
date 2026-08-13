from __future__ import annotations

import hmac
import os
from typing import Any, Mapping, MutableMapping


NETWORK_MODES = {"CLOUD", "PRODUCTION", "NETWORK"}
NETWORK_ENV_MARKERS = (
    "RAILWAY_ENVIRONMENT",
    "RAILWAY_PUBLIC_DOMAIN",
    "RAILWAY_PROJECT_ID",
)


def is_network_production(environment: Mapping[str, str] | None = None) -> bool:
    """Return True only for an explicitly network-hosted production runtime."""
    env = environment if environment is not None else os.environ
    mode = str(env.get("VELAFLOW_MODE", "LOCAL") or "LOCAL").strip().upper()
    return mode in NETWORK_MODES or any(str(env.get(name, "") or "").strip() for name in NETWORK_ENV_MARKERS)


def access_gate_policy(
    environment: Mapping[str, str] | None = None,
    *,
    configured_password: str = "",
) -> dict[str, Any]:
    network = is_network_production(environment)
    password_configured = bool(str(configured_password or "").strip())
    return {
        "network_production": network,
        "password_configured": password_configured,
        "authentication_required": network,
        "fail_closed": network and not password_configured,
        "local_development_bypass": not network,
        "project_namespace": "SINGLE-USER GLOBAL PROJECT STORE",
    }


def authenticate_access_password(provided_password: str, configured_password: str) -> bool:
    expected = str(configured_password or "")
    provided = str(provided_password or "")
    if not expected:
        return False
    return hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))


def sign_out_access_session(session_state: MutableMapping[str, Any]) -> None:
    session_state.pop("velaflow_authenticated", None)
    session_state.pop("velaflow_access_password_input", None)
    session_state.pop("velaflow_access_error", None)
