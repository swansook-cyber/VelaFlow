from __future__ import annotations

from typing import Any

from core.agents.base_agent import BaseAgent


class MusicAgent(BaseAgent):
    name = "Music Agent"
    role = "Titles, lyrics, Suno prompts, and song structure"

    def execute_task(self, task: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        idea = context.get("user_goal", "new song idea")
        tone = context.get("tone", "Emotional")
        title = f"{str(idea).strip()[:36] or 'New Song'}"
        sections = {
            "Best Title Ideas": f"- {title}\n- คืนที่ยังจำ\n- ยังอยู่ในใจ",
            "Lyrics or Script": (
                "[Opening Hook]\n"
                f"{title}\n\n"
                "[Verse]\n"
                "เล่าอารมณ์จริงให้เหมือนคนฟังเคยผ่าน\n\n"
                "[Chorus]\n"
                "ประโยคจำง่าย ร้องตามง่าย และกลับมาในหัวอีกครั้ง"
            ),
            "Suno / Music Style Prompt": (
                f"modern Thai pop, {tone.lower()} vocal, memorable chorus, warm production, "
                "commercial arrangement, cinematic atmosphere, Suno-ready"
            ),
        }
        return {"agent": self.name, "role": self.role, "task": task.get("task"), "ok": True, "sections": sections, "log": ["Music Agent → generating titles, lyrics, Suno prompt"]}
