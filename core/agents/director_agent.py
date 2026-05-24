from __future__ import annotations

from typing import Any

from core.agents.base_agent import BaseAgent
from core.agent_router import route_agent_tasks


class DirectorAgent(BaseAgent):
    name = "Director Agent"
    role = "Analyze overall goal, assign tasks, and merge outputs"

    def assign_tasks(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        tasks = route_agent_tasks(
            str(context.get("user_goal", "")),
            str(context.get("project_type", "General Creative Package")),
            str(context.get("workflow_mode", "Auto")),
        )
        if not any(task["task"] == "release package" for task in tasks):
            tasks.append({"task": "release package", "reason": "final package needs creator delivery actions"})
        return tasks

    def execute_task(self, task: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        assigned = self.assign_tasks(context)
        sections = {
            "Agent Strategy": (
                "Director Agent selected a collaborative workflow and delegated specialized tasks.\n"
                + "\n".join(f"- {item['task']}: {item['reason']}" for item in assigned)
            )
        }
        return {"agent": self.name, "role": self.role, "task": "director planning", "ok": True, "sections": sections, "assigned_tasks": assigned, "log": ["Director Agent → analyzing project and assigning specialist agents"]}
