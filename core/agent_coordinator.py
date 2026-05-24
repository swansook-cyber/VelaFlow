from __future__ import annotations

from typing import Any

from core.agents import DirectorAgent, MusicAgent, MVAgent, PodcastAgent, ReleaseAgent, TikTokAgent
from core.agent_memory import load_agent_memory
from core.agent_studio import REQUIRED_AGENT_SECTIONS, generate_agent_package
from core.workspace_manager import load_project
from core.project_assets import project_asset_summary
from providers.base_provider import BaseTextProvider, LocalFallbackProvider


def _agent_for_task(task_name: str, provider: BaseTextProvider, memory: dict[str, Any]):
    lowered = task_name.lower()
    if "lyrics" in lowered or "title" in lowered:
        return MusicAgent(provider=provider, memory=memory)
    if "tiktok" in lowered or "hook" in lowered:
        return TikTokAgent(provider=provider, memory=memory)
    if "mv" in lowered or "storyboard" in lowered:
        return MVAgent(provider=provider, memory=memory)
    if "podcast" in lowered:
        return PodcastAgent(provider=provider, memory=memory)
    return ReleaseAgent(provider=provider, memory=memory)


def _merge_sections(base: dict[str, str], updates: dict[str, str], agent_name: str, sources: dict[str, str]) -> None:
    for key, value in updates.items():
        if key not in REQUIRED_AGENT_SECTIONS or not str(value).strip():
            continue
        if base.get(key):
            base[key] = f"{base[key].strip()}\n\n{str(value).strip()}"
        else:
            base[key] = str(value).strip()
        sources[key] = agent_name


def run_multi_agent_workflow(
    user_goal: str,
    workflow_mode: str = "Auto",
    project_type: str = "General Creative Package",
    language: str = "Thai",
    tone: str = "Emotional",
    use_memory: bool = True,
    provider: BaseTextProvider | None = None,
    project_name: str | None = None,
) -> dict[str, Any]:
    provider = provider or LocalFallbackProvider()
    project_state: dict[str, Any] = {}
    if project_name:
        project_state = load_project(project_name)
        project_memory_path = f"{project_state.get('path')}/memory.json"
        memory = load_agent_memory(project_memory_path) if use_memory else {}
    else:
        memory = load_agent_memory() if use_memory else {}
    context = {
        "user_goal": user_goal,
        "workflow_mode": workflow_mode,
        "project_type": project_type,
        "language": language,
        "tone": tone,
        "project_name": project_name or "",
        "prior_outputs": project_state.get("generated_outputs", []),
        "asset_summary": project_asset_summary(project_name) if project_name else {},
    }
    collaboration_log: list[str] = []
    failures: list[str] = []
    sources: dict[str, str] = {}
    active_agents = ["Director Agent"]

    base_package = generate_agent_package(user_goal, project_type, language, tone, workflow_mode if workflow_mode != "Auto" else "Professional Release", use_memory=use_memory)
    director = DirectorAgent(provider=provider, memory=memory)
    director_result = director.execute_task({"task": "director planning"}, context)
    collaboration_log.extend(director_result.get("log", []))
    director_decisions = director_result.get("assigned_tasks", [])
    _merge_sections(base_package, director_result.get("sections", {}), director.name, sources)

    for task in director_decisions:
        agent = _agent_for_task(str(task.get("task", "")), provider, memory)
        if agent.name not in active_agents:
            active_agents.append(agent.name)
        try:
            result = agent.execute_task(task, context)
            collaboration_log.extend(result.get("log", []))
            if result.get("ok"):
                _merge_sections(base_package, result.get("sections", {}), result.get("agent", agent.name), sources)
            else:
                failures.append(f"{agent.name} failed: {result.get('error', 'unknown error')}")
        except Exception as exc:
            failures.append(f"{agent.name} failed: {type(exc).__name__}: {exc}")
            collaboration_log.append(f"{agent.name} → failed safely, continuing with partial output")

    for section in REQUIRED_AGENT_SECTIONS:
        base_package.setdefault(section, f"{section} ready.")
        sources.setdefault(section, "Template Fallback")

    return {
        "output_package": base_package,
        "active_agents": active_agents,
        "collaboration_log": collaboration_log,
        "director_decisions": director_decisions,
        "section_sources": sources,
        "failures": failures,
        "success": True,
    }
