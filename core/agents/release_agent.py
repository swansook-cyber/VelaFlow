from __future__ import annotations

from typing import Any

from core.agents.base_agent import BaseAgent


class ReleaseAgent(BaseAgent):
    name = "Release Agent"
    role = "Release checklist, metadata, platform preparation, and packaging"

    def execute_task(self, task: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        project_type = context.get("project_type", "General Creative Package")
        checklist = self.tools.generate_release_checklist(str(project_type))
        sections = {
            "Next Action Checklist": checklist,
            "Project Summary": f"{project_type} coordinated package for: {context.get('user_goal', '')}",
        }
        return {"agent": self.name, "role": self.role, "task": task.get("task"), "ok": True, "sections": sections, "log": ["Release Agent → preparing checklist and package readiness"]}
