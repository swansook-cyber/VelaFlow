from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


def generate_text(
    prompt: str,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    *,
    api_key: str = "",
    model_name: str = "gpt-4.1-mini",
    timeout: int = 60,
    **_: Any,
) -> str:
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY in .env")

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": model_name or "gpt-4.1-mini",
        "messages": messages,
        "temperature": temperature,
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
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
    return str(message.get("content") or "").strip()
