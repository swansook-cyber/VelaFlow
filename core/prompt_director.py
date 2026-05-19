from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from core.real_clip_pipeline import ensure_parent_dir


def summarize_hook_emotion(full_hook_section: str, *, mood: str = "") -> dict[str, Any]:
    text = str(full_hook_section or "").strip()
    lower = text.lower()
    sad_markers = ["คิดถึง", "เจ็บ", "ลืม", "น้ำตา", "เหงา", "alone", "lonely", "miss"]
    hopeful_markers = ["เดินต่อ", "หวัง", "แสง", "กลับมา", "เริ่มใหม่", "hope"]
    intensity = min(100, 55 + len([token for token in sad_markers + hopeful_markers if token in lower]) * 8 + min(20, len(text) // 80))
    if any(token in lower for token in sad_markers):
        tone = "melancholic emotional longing"
    elif any(token in lower for token in hopeful_markers):
        tone = "hopeful emotional release"
    else:
        tone = str(mood or "cinematic emotional Thai pop").strip()
    return {
        "emotional_tone": tone,
        "mood": mood or tone,
        "intensity": intensity,
        "progression": "loneliness to emotional realization to quiet release",
        "keywords": [token for token in sad_markers + hopeful_markers if token in lower][:8],
    }


def build_prompt_director_package(full_hook_section: str, *, song_title: str = "", artist_name: str = "", mood: str = "") -> dict[str, Any]:
    emotion = summarize_hook_emotion(full_hook_section, mood=mood)
    title = song_title or "Untitled Hook"
    artist = artist_name or "VelaFlow Creator"
    hook_clean = re.sub(r"\s+", " ", str(full_hook_section or "").strip())
    base_scene = (
        "Cinematic emotional Thai music video. Young Thai woman alone near apartment window at night. "
        "Slow emotional camera movement. Melancholic atmosphere. Warm cinematic lighting. "
        "Natural human motion. Realistic film look. Vertical 9:16. "
        f"Emotional progression from {emotion['progression']}."
    )
    continuity = (
        "Maintain the same character, same apartment room, same wardrobe, same warm rainy-night lighting palette, "
        "and a continuous emotional arc across the full hook section."
    )
    return {
        "hook_summary": f"{title} by {artist}: {emotion['emotional_tone']} hook sequence about {hook_clean[:180]}",
        "hook_emotion": emotion,
        "image_prompt": (
            f"{base_scene} Premium realistic film still, subtle skin texture, natural shadows, no text, no logo. {continuity}"
        ),
        "video_prompt_flow": (
            f"{base_scene} One continuous vertical cinematic hook sequence for Flow/Veo. {continuity} "
            "No subtitles inside generated video, no text, no watermark, no split screen."
        ),
        "video_prompt_runway": (
            f"{base_scene} Realistic live-action shot progression with wide lonely opening, medium emotional build, "
            f"close-up emotional climax, soft release ending. {continuity}"
        ),
        "thumbnail_prompt": (
            "Vertical emotional thumbnail frame, close-up expressive eyes near rainy window, warm cinematic rim light, "
            "mobile-readable composition, no text, no logo."
        ),
        "cinematic_direction": (
            "Start with a lonely wide shot, move into a medium profile shot, then a close-up for the strongest hook line. "
            "Use slow push-ins, soft dissolves, and bottom-safe subtitle space."
        ),
        "mood_summary": f"{emotion['emotional_tone']} with {emotion['progression']}.",
    }


def export_prompt_director_files(package: dict[str, Any], export_dir: str | Path) -> dict[str, str]:
    folder = Path(export_dir)
    folder.mkdir(parents=True, exist_ok=True)
    files = {
        "hook_summary.txt": package.get("hook_summary", ""),
        "hook_emotion.json": json.dumps(package.get("hook_emotion", {}), ensure_ascii=False, indent=2),
        "image_prompt.txt": package.get("image_prompt", ""),
        "video_prompt_flow.txt": package.get("video_prompt_flow", ""),
        "video_prompt_runway.txt": package.get("video_prompt_runway", ""),
        "thumbnail_prompt.txt": package.get("thumbnail_prompt", ""),
        "cinematic_direction.txt": package.get("cinematic_direction", ""),
        "mood_summary.txt": package.get("mood_summary", ""),
    }
    written = {}
    for filename, content in files.items():
        path = ensure_parent_dir(folder / filename)
        path.write_text(str(content).strip() + "\n", encoding="utf-8-sig")
        written[filename] = str(path)
    return written
