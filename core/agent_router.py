from __future__ import annotations

from typing import Any


ROUTABLE_TASKS = [
    "lyrics generation",
    "title generation",
    "TikTok hook generation",
    "release package",
    "MV storyboard",
    "podcast structure",
]

TASK_AGENT_MAP = {
    "lyrics generation": "Music Agent",
    "title generation": "Music Agent",
    "TikTok hook generation": "TikTok Agent",
    "release package": "Release Agent",
    "MV storyboard": "MV Agent",
    "podcast structure": "Podcast Agent",
}


def route_agent_tasks(user_input: str, project_type: str, workflow_mode: str) -> list[dict[str, Any]]:
    text = f"{user_input} {project_type} {workflow_mode}".lower()
    tasks: list[dict[str, Any]] = []
    music_request = any(word in text for word in ["spotify", "song", "lyrics", "suno", "\u0e40\u0e1e\u0e25\u0e07", "\u0e40\u0e28\u0e23\u0e49\u0e32", "\u0e2d\u0e2d\u0e1f\u0e1f\u0e34\u0e28"])
    if music_request:
        tasks.extend(
            [
                {"task": "title generation", "reason": "music release needs a strong title"},
                {"task": "lyrics generation", "reason": "song workflow needs lyrics or hook lines"},
                {"task": "TikTok hook generation", "reason": "music release needs short-form hook ideas"},
                {"task": "MV storyboard", "reason": "music release needs a visual storyboard"},
                {"task": "release package", "reason": "creator needs export-ready release assets"},
            ]
        )
    if "tiktok" in text or "viral" in text or "affiliate" in text or "product" in text:
        tasks.append({"task": "TikTok hook generation", "reason": "short-form workflow needs scroll-stop hooks"})
    if "mv" in text or "video" in text or "director" in text:
        tasks.append({"task": "MV storyboard", "reason": "video workflow needs scene and camera direction"})
    if "podcast" in text or "episode" in text:
        tasks.append({"task": "podcast structure", "reason": "podcast workflow needs intro, segments, and talking points"})
    if not tasks:
        tasks = [
            {"task": "title generation", "reason": "every creative package needs a clear title"},
            {"task": "release package", "reason": "general workflow should end with copy-ready assets"},
        ]
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for task in tasks:
        if task["task"] not in seen:
            task["agent"] = TASK_AGENT_MAP.get(task["task"], "Release Agent")
            unique.append(task)
            seen.add(task["task"])
    return unique
