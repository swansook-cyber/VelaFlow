from __future__ import annotations

from typing import Any

from core.agents.base_agent import BaseAgent
from core.asset_manager import list_assets


class MVAgent(BaseAgent):
    name = "MV Agent"
    role = "Storyboard, scenes, camera direction, and visual prompts"

    def execute_task(self, task: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        idea = context.get("user_goal", "emotional video")
        project_name = context.get("project_name") or ""
        available_assets = list_assets(project_name) if project_name else []
        asset_note = f"Reference available assets: {len(available_assets)} item(s). " if available_assets else ""
        prior_outputs = context.get("prior_outputs") or []
        continuity_note = "Reuse the established character, room, lighting palette, and emotional arc from prior outputs." if prior_outputs else "Build a consistent character, location, lighting palette, and emotional arc from the first scene."
        sections = {
            "Video Prompt": (
                f"{asset_note}Vertical 9:16 cinematic music video for {idea}. Single realistic subject, natural lighting, "
                "same location continuity, slow emotional camera movement, no text, no logo, no watermark."
            ),
            "Cover Image Prompt": (
                f"Cinematic cover image for {idea}, emotional close-up, warm shadows, premium composition, no text."
            ),
            "Main Creative Direction": (
                "Scene 1: wide lonely setup. Scene 2: medium emotional realization. "
                f"Scene 3: close-up hook moment. Camera evolves from quiet drift to emotional push-in. {continuity_note}"
            ),
        }
        return {"agent": self.name, "role": self.role, "task": task.get("task"), "ok": True, "sections": sections, "log": ["MV Agent → building storyboard, camera, visual prompts"]}
