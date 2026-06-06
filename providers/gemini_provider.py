from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from core.api_keys import resolve_gemini_api_key
from providers.base_provider import BaseTextProvider


class GeminiTextProvider(BaseTextProvider):
    name = "gemini"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        resolved_key = str(api_key or "").strip() if api_key is not None else str(resolve_gemini_api_key().get("api_key", "") or "").strip()
        resolved_model = (
            str(model or "").strip()
            or str(os.getenv("GEMINI_TEXT_MODEL") or "").strip()
            or str(os.getenv("GEMINI_MODEL") or "").strip()
            or "gemini-2.5-flash"
        )
        super().__init__(resolved_key, resolved_model)
        self.last_status = ""
        self.debug_log: list[dict[str, Any]] = []

    def _record_debug(self, **details: Any) -> None:
        safe_details = {
            key: ("yes" if key == "api_key_detected" and value else "no" if key == "api_key_detected" else value)
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
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            request = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=25) as response:
                self.last_status = str(getattr(response, "status", "") or "ok")
                data = json.loads(response.read().decode("utf-8"))
            candidates = data.get("candidates") or []
            parts = ((candidates[0] if candidates else {}).get("content") or {}).get("parts") or []
            text = "\n".join(str(part.get("text", "") or "").strip() for part in parts if part.get("text"))
            text = text.strip()
            if not text:
                self.last_error = "Gemini returned no text"
                self._record_debug(event="empty_response", api_response_status=self.last_status, exception_message=self.last_error)
                return ""
            self._record_debug(event="request_success", api_response_status=self.last_status)
            return text
        except urllib.error.HTTPError as exc:
            self.last_status = str(getattr(exc, "code", "") or "http_error")
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            detail = f"{type(exc).__name__}: {exc}"
            if body:
                detail = f"{detail} | {body[:800]}"
            self.last_error = detail
            self._record_debug(event="request_exception", api_response_status=self.last_status, exception_message=self.last_error)
            return ""
        except (urllib.error.URLError, TimeoutError, Exception) as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
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
                "debug_log": self.debug_log,
            }
        )
        return data


GeminiProvider = GeminiTextProvider
