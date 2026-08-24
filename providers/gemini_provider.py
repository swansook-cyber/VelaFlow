from __future__ import annotations

import os
from typing import Any

import google.generativeai as genai

from core.api_keys import redact_secret, resolve_gemini_api_key
from core.song_quality_core import safe_exception_summary
from providers.base_provider import BaseTextProvider


DEFAULT_GEMINI_TEXT_MODEL = "gemini-2.5-flash"


def _build_model(api_key: str, model_name: str, system_prompt: str | None = None) -> Any:
    if not str(api_key or "").strip():
        raise ValueError("GEMINI_API_KEY missing")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name or DEFAULT_GEMINI_TEXT_MODEL,
        system_instruction=system_prompt or None,
    )
    if not callable(getattr(model, "generate_content", None)):
        raise AttributeError(f"'{type(model).__name__}' object has no attribute 'generate_content'")
    return model


def _extract_response_text(response: Any) -> str:
    if response is None:
        raise ValueError("Gemini returned an empty response")

    try:
        direct_text = str(getattr(response, "text", "") or "").strip()
    except (ValueError, AttributeError):
        direct_text = ""
    if direct_text:
        return direct_text

    text_parts: list[str] = []
    for candidate in getattr(response, "candidates", None) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", None) or []:
            value = str(getattr(part, "text", "") or "").strip()
            if value:
                text_parts.append(value)
    extracted = "\n".join(text_parts).strip()
    if not extracted:
        raise ValueError("Gemini returned no text")
    return extracted


def _generate_with_model(model: Any, prompt: str, *, temperature: float, timeout: int) -> str:
    response = model.generate_content(
        prompt,
        generation_config={"temperature": float(temperature)},
        request_options={"timeout": max(10, int(timeout))},
    )
    return _extract_response_text(response)


def generate_text(
    prompt: str,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    *,
    api_key: str = "",
    model_name: str = "",
    timeout: int = 60,
    **_kwargs: Any,
) -> str:
    """Gemini text contract used by providers.ai_provider."""
    model = _build_model(api_key, model_name or DEFAULT_GEMINI_TEXT_MODEL, system_prompt)
    return _generate_with_model(model, prompt, temperature=temperature, timeout=timeout)


class GeminiTextProvider(BaseTextProvider):
    name = "gemini"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        resolved_key = str(api_key or "").strip() if api_key is not None else str(resolve_gemini_api_key().get("api_key", "") or "").strip()
        resolved_model = (
            str(model or "").strip()
            or str(os.getenv("GEMINI_TEXT_MODEL") or "").strip()
            or str(os.getenv("GEMINI_MODEL") or "").strip()
            or DEFAULT_GEMINI_TEXT_MODEL
        )
        super().__init__(resolved_key, resolved_model)
        self.last_status = ""
        self._model_client = None
        self.configure_result = "missing_api_key"
        self.client_initialized = False
        self.client_initialization_result = "not_initialized"
        self.client_initialization_error = "Gemini API key missing"
        if self.api_key:
            try:
                self._model_client = _build_model(self.api_key, self.model)
                self.configure_result = "configured"
                self.client_initialized = True
                self.client_initialization_result = "initialized"
                self.client_initialization_error = ""
            except Exception as exc:
                self.configure_result = "failed"
                self.client_initialization_result = "failed"
                self.client_initialization_error = safe_exception_summary(exc)
        self.debug_log: list[dict[str, Any]] = []
        self._record_debug(
            event="client_init",
            provider_selected=self.name,
            model_used=self.model,
            api_key_detected=bool(self.api_key),
            configure_result=self.configure_result,
            client_initialization_result=self.client_initialization_result,
            exception_message=self.client_initialization_error,
        )

    def _record_debug(self, **details: Any) -> None:
        safe_details = {
            key: (
                "yes"
                if key == "api_key_detected" and value
                else "no"
                if key == "api_key_detected"
                else redact_secret(value, self.api_key)
                if isinstance(value, str)
                else value
            )
            for key, value in details.items()
        }
        self.debug_log.append(safe_details)
        self.debug_log = self.debug_log[-20:]

    def generate_text(self, prompt: str) -> str:
        self.last_error = ""
        self.last_status = ""
        self._record_debug(
            event="request_start",
            provider_selected=self.name,
            model_used=self.model,
            api_key_detected=bool(self.api_key),
        )
        if not self.api_key:
            self.last_error = "GEMINI_API_KEY missing"
            self._record_debug(event="request_skipped", exception_message=self.last_error)
            return ""
        if self._model_client is None:
            self.last_error = self.client_initialization_error or "Gemini client initialization failed"
            self._record_debug(event="request_skipped", exception_message=self.last_error)
            return ""
        try:
            text = _generate_with_model(self._model_client, prompt, temperature=0.7, timeout=25)
            self.last_status = "ok"
            self._record_debug(event="request_success", api_response_status=self.last_status)
            return text
        except Exception as exc:
            self.last_error = safe_exception_summary(exc)
            self._record_debug(event="request_exception", api_response_status=self.last_status, exception_message=self.last_error)
            return ""

    def diagnostics(self) -> dict[str, Any]:
        data = super().diagnostics()
        data.update(
            {
                "provider_selected": self.name,
                "model_used": self.model,
                "api_response_status": self.last_status,
                "exception_message": self.last_error,
                "configure_result": self.configure_result,
                "client_initialized": self.client_initialized,
                "client_initialization_result": self.client_initialization_result,
                "client_initialization_error": self.client_initialization_error,
                "debug_log": self.debug_log,
            }
        )
        return data


GeminiProvider = GeminiTextProvider
