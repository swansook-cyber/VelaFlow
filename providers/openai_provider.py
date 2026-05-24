from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from providers.base_provider import BaseTextProvider


class OpenAITextProvider(BaseTextProvider):
    name = "openai"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        super().__init__(api_key or os.getenv("OPENAI_API_KEY"), model or os.getenv("OPENAI_TEXT_MODEL") or "gpt-4o-mini")

    def generate_text(self, prompt: str) -> str:
        if not self.api_key:
            self.last_error = "OPENAI_API_KEY missing"
            return ""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are VelaFlow Agent Studio, a concise creator workflow strategist."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
        }
        try:
            request = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=25) as response:
                data = json.loads(response.read().decode("utf-8"))
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return str(text or "").strip()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, Exception) as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            return ""
