from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from providers.base_provider import BaseTextProvider


OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"


def generate_text(
    prompt: str,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    *,
    api_key: str = "",
    model_name: str = DEFAULT_OPENAI_MODEL,
    timeout: int = 60,
    **_: Any,
) -> str:
    """OpenAI module adapter matching the shared provider contract."""
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY in .env")
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    payload = {"model": model_name or DEFAULT_OPENAI_MODEL, "messages": messages, "temperature": temperature}
    request = urllib.request.Request(
        f"{OPENAI_BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API error {exc.code}: {detail}") from exc
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message", {}) if isinstance(choice, dict) else {}
    text = str(message.get("content") or "").strip()
    if not text:
        raise ValueError("OpenAI returned no text")
    return text


class OpenAITextProvider(BaseTextProvider):
    name = "openai"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        super().__init__(api_key or os.getenv("OPENAI_API_KEY"), model or os.getenv("OPENAI_TEXT_MODEL") or DEFAULT_OPENAI_MODEL)

    def generate_text(self, prompt: str) -> str:
        if not self.api_key:
            self.last_error = "OPENAI_API_KEY missing"
            return ""
        try:
            return generate_text(
                prompt,
                system_prompt="You are VelaFlow Agent Studio, a concise creator workflow strategist.",
                api_key=self.api_key,
                model_name=self.model,
                timeout=25,
            )
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            return ""
