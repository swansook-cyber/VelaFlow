from __future__ import annotations

import os
from typing import Any

from providers import gemini_provider, openai_provider, xai_grok_provider


PROVIDER_LABELS = {
    "gemini": "Gemini",
    "openai": "OpenAI GPT",
    "openai_gpt": "OpenAI GPT",
    "xai": "xAI Grok",
    "xai_grok": "xAI Grok",
    "grok": "xAI Grok",
}


def normalize_provider(provider: str | None = None) -> str:
    value = (provider or os.getenv("DEFAULT_AI_PROVIDER") or "gemini").strip().lower()
    value = value.replace(" ", "_").replace("-", "_")
    if value in {"openai", "openai_gpt", "gpt"}:
        return "openai"
    if value in {"xai", "xai_grok", "grok", "grok_ai"}:
        return "xai"
    return "gemini"


def provider_display_name(provider: str | None = None) -> str:
    return PROVIDER_LABELS.get(normalize_provider(provider), "Gemini")


def provider_api_key(provider: str | None = None, explicit_key: str = "") -> str:
    if explicit_key:
        return explicit_key
    selected = normalize_provider(provider)
    if selected == "openai":
        return os.getenv("OPENAI_API_KEY", "")
    if selected == "xai":
        return os.getenv("XAI_API_KEY", "")
    return os.getenv("GEMINI_API_KEY", "")


def provider_model(provider: str | None = None, explicit_model: str = "") -> str:
    if explicit_model:
        return explicit_model
    selected = normalize_provider(provider)
    if selected == "openai":
        return os.getenv("OPENAI_TEXT_MODEL", "gpt-4.1-mini")
    if selected == "xai":
        return os.getenv("XAI_TEXT_MODEL", "grok-4.3")
    return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def generate_text(
    prompt: str,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    *,
    provider: str | None = None,
    api_key: str = "",
    model_name: str = "",
    timeout: int = 60,
    **kwargs: Any,
) -> str:
    selected = normalize_provider(provider)
    key = provider_api_key(selected, api_key)
    model = provider_model(selected, model_name)
    if selected == "openai":
        return openai_provider.generate_text(
            prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            api_key=key,
            model_name=model,
            timeout=timeout,
            **kwargs,
        )
    if selected == "xai":
        return xai_grok_provider.generate_text(
            prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            api_key=key,
            model_name=model,
            timeout=timeout,
            **kwargs,
        )
    return gemini_provider.generate_text(
        prompt,
        system_prompt=system_prompt,
        temperature=temperature,
        api_key=key,
        model_name=model,
        timeout=timeout,
        **kwargs,
    )
