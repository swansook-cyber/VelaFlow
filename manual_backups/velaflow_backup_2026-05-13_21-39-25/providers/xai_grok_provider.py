from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


XAI_BASE_URL = "https://api.x.ai/v1"
DEFAULT_XAI_MODEL = "grok-4.3"


def generate_text(
    prompt: str,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    *,
    api_key: str = "",
    model_name: str = DEFAULT_XAI_MODEL,
    timeout: int = 60,
    **_: Any,
) -> str:
    if not api_key:
        raise RuntimeError("Missing XAI_API_KEY in .env")

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": model_name or DEFAULT_XAI_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    request = urllib.request.Request(
        f"{XAI_BASE_URL}/chat/completions",
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
        raise RuntimeError(f"xAI Grok API error {exc.code}: {detail}") from exc
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message", {}) if isinstance(choice, dict) else {}
    return str(message.get("content") or "").strip()
