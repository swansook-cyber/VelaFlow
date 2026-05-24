from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseTextProvider(ABC):
    name = "base"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = (api_key or "").strip()
        self.model = (model or "").strip()
        self.last_error = ""

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    @abstractmethod
    def generate_text(self, prompt: str) -> str:
        raise NotImplementedError

    def analyze_intent(self, text: str) -> str:
        return self.generate_text(f"Analyze this creator request and return concise intent:\n{text}")

    def summarize(self, text: str) -> str:
        return self.generate_text(f"Summarize this for a creator workflow in 3 bullet points:\n{text}")

    def generate_strategy(self, input: str) -> str:
        return self.generate_text(f"Create a practical creative strategy for this idea:\n{input}")

    def diagnostics(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "model": self.model,
            "api_key_detected": bool(self.api_key),
            "available": self.available,
            "last_error": self.last_error,
        }


class LocalFallbackProvider(BaseTextProvider):
    name = "local_template"

    @property
    def available(self) -> bool:
        return True

    def generate_text(self, prompt: str) -> str:
        return "Local fallback reasoning: use the idea, memory, tone, and workflow heuristics to build a practical creator package."
