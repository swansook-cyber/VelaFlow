from __future__ import annotations

from typing import Any, Dict, List

from core.visual_presets import normalize_visual_settings


SCENE_STRUCTURES = {
    "music_mv": ["Intro", "Verse", "Build", "Hook", "Emotional Peak", "Outro"],
    "seller": ["Hook", "Problem", "Product Showcase", "Demo", "CTA"],
    "podcast": ["Emotional Opening", "Story Beat", "Relatable Moment", "Closing Thought"],
    "clips": ["Hook", "Fast Context", "Viral Beat", "CTA"],
}


def build_camera_direction(camera_preset: str = "Cinematic", workflow_type: str = "clips") -> str:
    settings = normalize_visual_settings({"camera_preset": camera_preset})
    workflow_note = {
        "music_mv": "keep performance and lyric emotion cinematic",
        "seller": "keep product visible and easy to understand",
        "podcast": "keep speaker emotion and atmosphere grounded",
        "clips": "keep the first second visually clear and scroll-stopping",
    }.get(workflow_type, "keep the shot clear and useful")
    return f"{settings['camera_description']}, {workflow_note}"


def build_visual_prompt(
    *,
    workflow_type: str,
    subject: str,
    context: str = "",
    visual_settings: Dict[str, Any] | None = None,
    platform: str = "vertical 9:16",
) -> str:
    settings = normalize_visual_settings(visual_settings)
    return (
        f"{platform} AI-ready visual prompt for {workflow_type}: {subject}. "
        f"Context: {context or 'concise creator content'}. "
        f"Camera: {settings['camera_description']}. "
        f"Lighting: {settings['lighting_description']}. "
        f"Motion: {settings['motion_description']}. "
        f"Mood: {settings['visual_mood_description']}. "
        "Realistic, clean composition, optimized for AI video generation, no random text, no watermark."
    )


def build_scene_flow(workflow_type: str, visual_settings: Dict[str, Any] | None = None) -> List[Dict[str, str]]:
    settings = normalize_visual_settings(visual_settings)
    sections = SCENE_STRUCTURES.get(workflow_type, SCENE_STRUCTURES["clips"])
    return [
        {
            "beat": section,
            "camera": settings["camera_preset"],
            "lighting": settings["lighting_preset"],
            "motion": settings["motion_preset"],
            "visual_mood": settings["visual_mood"],
        }
        for section in sections
    ]


def build_shorts_structure(workflow_type: str, visual_settings: Dict[str, Any] | None = None) -> Dict[str, Any]:
    flow = build_scene_flow(workflow_type, visual_settings)
    return {
        "workflow_type": workflow_type,
        "structure": flow,
        "summary": " -> ".join(item["beat"] for item in flow),
    }


def apply_visual_engine_to_package(package: Dict[str, Any], workflow_type: str, visual_settings: Dict[str, Any] | None = None) -> Dict[str, Any]:
    data = dict(package or {})
    settings = normalize_visual_settings(visual_settings)
    subject = (
        data.get("main_idea")
        or data.get("product_name")
        or data.get("podcast_topic")
        or data.get("episode_title")
        or data.get("song_title")
        or data.get("title")
        or "content idea"
    )
    context = data.get("caption") or data.get("episode_theme") or data.get("target_audience") or data.get("goal") or ""
    visual_prompt = build_visual_prompt(workflow_type=workflow_type, subject=str(subject), context=str(context), visual_settings=settings)
    data["visual_engine"] = {
        "camera_preset": settings["camera_preset"],
        "lighting_preset": settings["lighting_preset"],
        "motion_preset": settings["motion_preset"],
        "visual_mood": settings["visual_mood"],
        "generated_visual_prompt": visual_prompt,
        "scene_flow": build_scene_flow(workflow_type, settings),
        "shorts_structure": build_shorts_structure(workflow_type, settings),
    }
    if data.get("ai_video_prompt"):
        data["ai_video_prompt"] = f"{data['ai_video_prompt']}. Visual direction: {visual_prompt}"
    else:
        data["ai_video_prompt"] = visual_prompt
    if data.get("thumbnail_prompt"):
        data["thumbnail_prompt"] = f"{data['thumbnail_prompt']}. Visual mood: {settings['visual_mood_description']}; lighting: {settings['lighting_description']}"
    return data
