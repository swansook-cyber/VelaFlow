from __future__ import annotations

from typing import Any

from core.agents.base_agent import BaseAgent


class PodcastAgent(BaseAgent):
    name = "Podcast Agent"
    role = "Episode structure, talking points, narration flow, and shorts extraction"

    def execute_task(self, task: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        idea = context.get("user_goal", "episode idea")
        sections = {
            "Lyrics or Script": (
                f"[Episode Intro]\nวันนี้เราจะคุยเรื่อง {idea}\n\n"
                "[Segment 1]\nทำไมเรื่องนี้สำคัญกับคนฟัง\n\n"
                "[Segment 2]\nเล่า story หรือ case ที่ทำให้คนอิน\n\n"
                "[Segment 3]\nสรุปเป็นบทเรียนที่เอาไปใช้ได้\n\n"
                "[Shorts Extraction]\nตัดช่วงคำถามแรงที่สุดเป็นคลิป 20-30 วินาที"
            )
        }
        return {"agent": self.name, "role": self.role, "task": task.get("task"), "ok": True, "sections": sections, "log": ["Podcast Agent → structuring episode and shorts moments"]}
