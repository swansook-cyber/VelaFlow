from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


MEMORY_PATH = Path("data") / "agent_memory.json"


def _default_memory() -> dict[str, Any]:
    return {
        "recent_project_type": "",
        "recent_tone": "",
        "recent_language": "",
        "last_user_ideas": [],
        "last_generated_titles": [],
        "preferred_creative_direction_summary": "",
        "updated_at": "",
    }


def _safe_list(value: Any, limit: int = 10) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned = [str(item).strip() for item in value if str(item).strip()]
    return cleaned[-limit:]


def _normalize_memory(memory: Any) -> dict[str, Any]:
    base = _default_memory()
    if isinstance(memory, dict):
        base.update(
            {
                "recent_project_type": str(memory.get("recent_project_type") or ""),
                "recent_tone": str(memory.get("recent_tone") or ""),
                "recent_language": str(memory.get("recent_language") or ""),
                "last_user_ideas": _safe_list(memory.get("last_user_ideas")),
                "last_generated_titles": _safe_list(memory.get("last_generated_titles")),
                "preferred_creative_direction_summary": str(memory.get("preferred_creative_direction_summary") or ""),
                "updated_at": str(memory.get("updated_at") or ""),
            }
        )
    return base


def load_agent_memory() -> dict[str, Any]:
    """Load local Agent Studio memory, creating a safe default when needed."""
    try:
        MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not MEMORY_PATH.exists():
            memory = _default_memory()
            save_agent_memory(memory)
            return memory
        with MEMORY_PATH.open("r", encoding="utf-8") as handle:
            return _normalize_memory(json.load(handle))
    except Exception:
        memory = _default_memory()
        try:
            save_agent_memory(memory)
        except Exception:
            pass
        return memory


def save_agent_memory(memory: dict[str, Any]) -> dict[str, Any]:
    safe_memory = _normalize_memory(memory)
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MEMORY_PATH.open("w", encoding="utf-8") as handle:
        json.dump(safe_memory, handle, ensure_ascii=False, indent=2)
    return safe_memory


def update_agent_memory(
    project_type: str,
    language: str,
    tone: str,
    user_idea: str,
    output: dict[str, str],
) -> dict[str, Any]:
    memory = load_agent_memory()
    idea = str(user_idea or "").strip()
    titles = str(output.get("Best Title Ideas") or "")
    generated_titles = [line.strip("- ").strip() for line in titles.splitlines() if line.strip("- ").strip()]

    if idea:
        memory["last_user_ideas"] = _safe_list(memory.get("last_user_ideas") + [idea])
    if generated_titles:
        memory["last_generated_titles"] = _safe_list(memory.get("last_generated_titles") + generated_titles)

    memory["recent_project_type"] = str(project_type or "")
    memory["recent_language"] = str(language or "")
    memory["recent_tone"] = str(tone or "")
    memory["preferred_creative_direction_summary"] = str(output.get("Main Creative Direction") or "")[:500]
    memory["updated_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    return save_agent_memory(memory)
