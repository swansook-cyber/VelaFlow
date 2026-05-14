from __future__ import annotations

from typing import Any

import google.generativeai as genai


def generate_text(
    prompt: str,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    *,
    api_key: str = "",
    model_name: str = "gemini-2.5-flash",
    timeout: int = 60,
    **_: Any,
) -> str:
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY in .env")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name or "gemini-2.5-flash",
        system_instruction=system_prompt or None,
        generation_config={"temperature": temperature},
    )
    response = model.generate_content(prompt, request_options={"timeout": timeout})
    return (response.text or "").strip()
