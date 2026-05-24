from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from providers.base_provider import BaseTextProvider


class GeminiTextProvider(BaseTextProvider):
    name = "gemini"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        super().__init__(api_key or os.getenv("GEMINI_API_KEY"), model or os.getenv("GEMINI_TEXT_MODEL") or "gemini-1.5-flash")

    def generate_text(self, prompt: str) -> str:
        if not self.api_key:
            self.last_error = "GEMINI_API_KEY missing"
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
                data = json.loads(response.read().decode("utf-8"))
            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            return str(text or "").strip()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, Exception) as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            return ""
