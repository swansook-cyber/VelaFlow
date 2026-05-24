from __future__ import annotations

from typing import Any

from core.agent_memory import load_agent_memory
from core import agent_tools
from providers.base_provider import BaseTextProvider, LocalFallbackProvider


class BaseAgent:
    name = "Base Agent"
    role = "General creative assistant"

    def __init__(self, provider: BaseTextProvider | None = None, memory: dict[str, Any] | None = None) -> None:
        self.provider = provider or LocalFallbackProvider()
        self.memory = memory if memory is not None else load_agent_memory()
        self.tools = agent_tools

    def _safe_provider_text(self, prompt: str, fallback: str) -> str:
        try:
            if self.provider and self.provider.available and self.provider.name != "local_template":
                text = self.provider.generate_text(prompt)
                if text:
                    return text
        except Exception:
            pass
        return fallback

    def execute_task(self, task: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        return {
            "agent": self.name,
            "role": self.role,
            "task": task.get("task", "general"),
            "ok": True,
            "sections": {},
            "log": [f"{self.name} handled {task.get('task', 'general')}"],
        }
