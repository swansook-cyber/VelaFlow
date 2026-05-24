from __future__ import annotations

from typing import Any


WORKFLOW_MODES = [
    "Auto",
    "Quick Generate",
    "Professional Release",
    "TikTok Viral Mode",
    "Spotify Commercial Mode",
    "Podcast Episode Mode",
    "MV Director Mode",
]


WORKFLOW_PROFILES: dict[str, dict[str, Any]] = {
    "Auto": {
        "strategy": "Let the agent choose the strongest workflow from the user idea, memory, and project intent.",
        "length": "adaptive",
        "focus": ["intent detection", "workflow choice", "creator-ready output"],
        "caption_style": "adaptive",
        "checklist_depth": "adaptive",
    },
    "Quick Generate": {
        "strategy": "Fast creator draft with concise outputs and clear next steps.",
        "length": "short",
        "focus": ["speed", "clarity", "copy-ready output"],
        "caption_style": "short and direct",
        "checklist_depth": "basic",
    },
    "Professional Release": {
        "strategy": "Polished release package with stronger positioning, fuller creative direction, and platform-ready assets.",
        "length": "detailed",
        "focus": ["release quality", "brand polish", "complete package"],
        "caption_style": "premium and emotionally clear",
        "checklist_depth": "complete",
    },
    "TikTok Viral Mode": {
        "strategy": "Hook-first package optimized for short attention spans, captions, hashtags, and replay value.",
        "length": "punchy",
        "focus": ["first 2 seconds", "scroll stop", "caption energy", "hashtags"],
        "caption_style": "TikTok-native and punchy",
        "checklist_depth": "viral",
    },
    "Spotify Commercial Mode": {
        "strategy": "Song-release workflow centered on title quality, lyrics, Suno prompt, cover prompt, and release packaging.",
        "length": "song_release",
        "focus": ["song title", "commercial hook", "Suno prompt", "cover art"],
        "caption_style": "music release announcement",
        "checklist_depth": "release",
    },
    "Podcast Episode Mode": {
        "strategy": "Episode planning workflow with intro, segment flow, talking points, and short-clip extraction ideas.",
        "length": "episode",
        "focus": ["episode intro", "segments", "talking points", "shorts extraction"],
        "caption_style": "conversation starter",
        "checklist_depth": "episode",
    },
    "MV Director Mode": {
        "strategy": "Cinematic director workflow with storyboard, scenes, camera movement, lighting, and video prompts.",
        "length": "cinematic",
        "focus": ["storyboard", "shot progression", "camera", "lighting", "video prompt"],
        "caption_style": "cinematic teaser",
        "checklist_depth": "director",
    },
}


def get_workflow_profile(workflow_mode: str) -> dict[str, Any]:
    mode = workflow_mode if workflow_mode in WORKFLOW_PROFILES else "Quick Generate"
    profile = dict(WORKFLOW_PROFILES[mode])
    profile["workflow_mode"] = mode
    return profile


def workflow_memory_hint(memory: dict[str, Any]) -> str:
    if not memory:
        return "No previous Agent Studio memory yet."
    recent = memory.get("recent_project_type") or "new creative package"
    tone = memory.get("recent_tone") or "balanced"
    language = memory.get("recent_language") or "Thai"
    titles = memory.get("last_generated_titles") or []
    title_hint = f" Recent title direction: {titles[-1]}." if titles else ""
    return f"Recent preference: {recent}, {tone} tone, {language} output.{title_hint}"
