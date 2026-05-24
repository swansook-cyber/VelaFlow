from __future__ import annotations

from typing import Any

from core.agents.base_agent import BaseAgent


class TikTokAgent(BaseAgent):
    name = "TikTok Agent"
    role = "Hooks, captions, hashtags, and viral strategy"

    def execute_task(self, task: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        idea = context.get("user_goal", "creator idea")
        sections = {
            "TikTok Hook Ideas": "\n".join(
                [
                    f"- อย่าเพิ่งเลื่อน ถ้าเรื่องนี้ตรงกับคุณ: {idea}",
                    f"- ไม่มีใครบอกเรื่องนี้เกี่ยวกับ {str(idea)[:28]}",
                    "- คลิปนี้เริ่มธรรมดา แต่จบแบบจำได้",
                ]
            ),
            "Caption": f"{idea}\n\nเก็บไว้เป็นไอเดียคอนเทนต์ถัดไป",
            "Hashtags": "#VelaFlow #ThaiCreator #TikTokContent #AICreator #CreatorWorkflow",
        }
        return {"agent": self.name, "role": self.role, "task": task.get("task"), "ok": True, "sections": sections, "log": ["TikTok Agent → creating hooks, caption, hashtags"]}
