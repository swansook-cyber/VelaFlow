from __future__ import annotations

from typing import Any

from core.agent_memory import load_agent_memory
from core.agent_workflows import WORKFLOW_MODES
from core.agent_router import route_agent_tasks
from providers.base_provider import BaseTextProvider, LocalFallbackProvider
from providers.gemini_provider import GeminiTextProvider
from providers.openai_provider import OpenAITextProvider


AGENT_AI_PROVIDERS = ["Auto", "Local Template", "Gemini", "OpenAI"]


def resolve_agent_provider(provider_name: str = "Auto") -> BaseTextProvider:
    provider_name = provider_name if provider_name in AGENT_AI_PROVIDERS else "Auto"
    if provider_name in ("Auto", "Gemini"):
        gemini = GeminiTextProvider()
        if gemini.available:
            return gemini
        if provider_name == "Gemini":
            return gemini
    if provider_name in ("Auto", "OpenAI"):
        openai = OpenAITextProvider()
        if openai.available:
            return openai
        if provider_name == "OpenAI":
            return openai
    return LocalFallbackProvider()


def analyze_user_goal(user_input: str, memory_summary: str = "", provider: BaseTextProvider | None = None) -> dict[str, Any]:
    text = str(user_input or "")
    lowered = text.lower()
    goal_type = "general"
    if any(token in lowered for token in ["song", "lyrics", "suno", "spotify", "\u0e40\u0e1e\u0e25\u0e07", "\u0e40\u0e28\u0e23\u0e49\u0e32", "\u0e2d\u0e2d\u0e1f\u0e1f\u0e34\u0e28"]):
        goal_type = "music"
    elif any(token in lowered for token in ["affiliate", "product", "shop", "สินค้า"]):
        goal_type = "affiliate"
    elif any(token in lowered for token in ["podcast", "episode", "พอดแคสต์"]):
        goal_type = "podcast"
    elif any(token in lowered for token in ["mv", "music video", "video prompt", "veo", "runway", "kling"]):
        goal_type = "mv"
    provider_text = ""
    if provider and provider.available and provider.name != "local_template":
        provider_text = provider.analyze_intent(f"Idea: {text}\nMemory: {memory_summary}")[:500]
    return {
        "goal_type": goal_type,
        "summary": provider_text or f"Detected {goal_type} creator request from the idea.",
        "memory_used": bool(memory_summary),
    }


def select_best_workflow(user_input: str, current_mode: str = "Auto", provider: BaseTextProvider | None = None) -> dict[str, str]:
    if current_mode and current_mode != "Auto" and current_mode in WORKFLOW_MODES:
        return {"workflow_mode": current_mode, "reason": "User selected this workflow mode."}
    goal = analyze_user_goal(user_input, provider=provider)
    mapping = {
        "music": "Spotify Commercial Mode",
        "affiliate": "TikTok Viral Mode",
        "podcast": "Podcast Episode Mode",
        "mv": "MV Director Mode",
        "general": "Professional Release",
    }
    selected = mapping.get(goal["goal_type"], "Professional Release")
    return {"workflow_mode": selected, "reason": f"Auto selected from detected {goal['goal_type']} request."}


def generate_creative_strategy(user_input: str, workflow_mode: str, memory_summary: str = "", provider: BaseTextProvider | None = None) -> str:
    fallback = (
        f"Use {workflow_mode} to turn the idea into copy-ready titles, direction, script, prompts, captions, "
        "hashtags, and next actions. Keep output practical and creator-friendly."
    )
    if provider and provider.available and provider.name != "local_template":
        text = provider.generate_strategy(f"Idea: {user_input}\nWorkflow: {workflow_mode}\nMemory: {memory_summary}")
        return text or fallback
    return fallback


def build_execution_plan(user_input: str, project_type: str, workflow_mode: str, memory_summary: str = "") -> list[str]:
    tasks = route_agent_tasks(user_input, project_type, workflow_mode)
    plan = ["Analyze creator idea", f"Use workflow: {workflow_mode}"]
    if memory_summary:
        plan.append("Apply Agent Memory context")
    plan.extend(f"Run task: {item['task']}" for item in tasks)
    plan.append("Export creator files")
    return plan


def think(
    user_input: str,
    workflow_mode: str = "Auto",
    project_type: str = "General Creative Package",
    use_memory: bool = True,
    provider_name: str = "Auto",
) -> dict[str, Any]:
    provider = resolve_agent_provider(provider_name)
    memory = load_agent_memory() if use_memory else {}
    memory_summary = ""
    if memory:
        memory_summary = (
            f"Recent project type: {memory.get('recent_project_type')}; "
            f"recent tone: {memory.get('recent_tone')}; "
            f"recent language: {memory.get('recent_language')}; "
            f"recent titles: {', '.join((memory.get('last_generated_titles') or [])[-3:])}"
        )
    selected = select_best_workflow(user_input, workflow_mode, provider)
    goal = analyze_user_goal(user_input, memory_summary, provider)
    strategy = generate_creative_strategy(user_input, selected["workflow_mode"], memory_summary, provider)
    plan = build_execution_plan(user_input, project_type, selected["workflow_mode"], memory_summary)
    provider_diag = provider.diagnostics()
    warning = ""
    if provider.name != "local_template" and not provider.available:
        warning = f"{provider.name} API key missing. Used local fallback behavior."
    elif provider.name != "local_template" and provider.last_error:
        warning = f"{provider.name} failed. Used local fallback behavior."
    return {
        "provider": provider_diag,
        "goal": goal,
        "selected_workflow": selected["workflow_mode"],
        "selected_workflow_reason": selected["reason"],
        "creative_strategy": strategy,
        "execution_plan": plan,
        "router_tasks": route_agent_tasks(user_input, project_type, selected["workflow_mode"]),
        "memory_summary": memory_summary,
        "warning": warning,
    }
