from __future__ import annotations

from typing import Any

from core.agents.base_agent import BaseAgent
from core.asset_manager import list_assets


class MusicAgent(BaseAgent):
    name = "Music Agent"
    role = "Titles, lyrics, Suno prompts, and song structure"

    def execute_task(self, task: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        idea = context.get("user_goal", "new song idea")
        tone = context.get("tone", "Emotional")
        project_name = context.get("project_name") or ""
        audio_assets = list_assets(project_name, "audio") if project_name else []
        audio_note = f"\n\n[Asset Note]\nUse {len(audio_assets)} linked audio asset(s) as reference for song continuity." if audio_assets else ""
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
                f"commercial arrangement, cinematic atmosphere, Suno-ready{audio_note}"
            ),
        }
        return {"agent": self.name, "role": self.role, "task": task.get("task"), "ok": True, "sections": sections, "log": ["Music Agent → generating titles, lyrics, Suno prompt"]}
