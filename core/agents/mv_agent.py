from __future__ import annotations

from typing import Any

from core.agents.base_agent import BaseAgent


class MVAgent(BaseAgent):
    name = "MV Agent"
    role = "Storyboard, scenes, camera direction, and visual prompts"

    def execute_task(self, task: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        idea = context.get("user_goal", "emotional video")
        sections = {
            "Video Prompt": (
                f"Vertical 9:16 cinematic music video for {idea}. Single realistic subject, natural lighting, "
                "same location continuity, slow emotional camera movement, no text, no logo, no watermark."
            ),
            "Cover Image Prompt": (
                f"Cinematic cover image for {idea}, emotional close-up, warm shadows, premium composition, no text."
            ),
            "Main Creative Direction": (
                "Scene 1: wide lonely setup. Scene 2: medium emotional realization. "
                "Scene 3: close-up hook moment. Camera evolves from quiet drift to emotional push-in."
            ),
        }
        return {"agent": self.name, "role": self.role, "task": task.get("task"), "ok": True, "sections": sections, "log": ["MV Agent → building storyboard, camera, visual prompts"]}
