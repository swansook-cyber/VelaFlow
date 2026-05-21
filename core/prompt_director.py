from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from core.real_clip_pipeline import ensure_parent_dir


CREATOR_EXPORT_MODES = [
    "TikTok Emotional",
    "TikTok Fast Hook",
    "Spotify Canvas",
    "YouTube Shorts",
    "Cinematic MV",
    "Sad Emotional",
    "Pop Viral",
    "Dark Storytelling",
]

PROMPT_STYLES = ["Safe", "Balanced", "Cinematic", "Viral"]

_MODE_PROFILES = {
    "TikTok Emotional": {
        "pacing": "quick emotional opening, close-up hook moment, soft release",
        "camera": "vertical close-ups, slow push-ins, gentle handheld drift",
        "mood": "modern TikTok emotional music edit",
        "caption": "short emotional Thai caption with one strong hook line",
    },
    "TikTok Fast Hook": {
        "pacing": "fast first three seconds, beat cuts, early emotional peak",
        "camera": "tight vertical framing, faster push-ins, punchy scene changes",
        "mood": "scroll-stopping short-form hook energy",
        "caption": "short curiosity caption with high replay value",
    },
    "Spotify Canvas": {
        "pacing": "slow looping motion, minimal scene changes, clean mood",
        "camera": "subtle cinematic drift and loop-friendly composition",
        "mood": "premium emotional music canvas",
        "caption": "clean release note for a music platform",
    },
    "YouTube Shorts": {
        "pacing": "clear story build, readable hook, satisfying ending beat",
        "camera": "wide-to-medium-to-close-up vertical storytelling",
        "mood": "cinematic short-form music story",
        "caption": "slightly longer emotional description with CTA",
    },
    "Cinematic MV": {
        "pacing": "music-video progression with emotional build and climax",
        "camera": "film-language shot progression, dolly push, soft dissolves",
        "mood": "cinematic mini music video",
        "caption": "release-ready emotional music caption",
    },
    "Sad Emotional": {
        "pacing": "slow intro, lingering close-ups, quiet emotional release",
        "camera": "lonely wide shot, profile medium shot, tearful close-up",
        "mood": "sad intimate emotional ballad",
        "caption": "heartbreak caption with quiet emotional pull",
    },
    "Pop Viral": {
        "pacing": "bright hook entry, faster scene progression, replay ending",
        "camera": "clean vertical pop framing, energetic pushes, colorful movement",
        "mood": "polished pop hook for short-form discovery",
        "caption": "catchy short caption for shareability",
    },
    "Dark Storytelling": {
        "pacing": "moody slow build, shadow-heavy emotional turn, dark release",
        "camera": "low-key lighting, negative space, restrained push-ins",
        "mood": "dark cinematic emotional story",
        "caption": "mysterious emotional caption with curiosity gap",
    },
}

_STYLE_PROFILES = {
    "Safe": {
        "detail": "simple clean prompt language, easy for any generator to follow",
        "intensity": "restrained",
        "prompt": "Keep the prompt clear, grounded, and direct.",
    },
    "Balanced": {
        "detail": "balanced cinematic detail with practical creator-ready language",
        "intensity": "medium",
        "prompt": "Use cinematic detail without overloading the generator.",
    },
    "Cinematic": {
        "detail": "more film language, lens feeling, lighting, blocking, and camera movement",
        "intensity": "high cinematic",
        "prompt": "Add filmic lens language, natural shadows, depth of field, and emotional camera movement.",
    },
    "Viral": {
        "detail": "stronger hook wording, faster pacing, retention-focused vertical framing",
        "intensity": "high retention",
        "prompt": "Make the first seconds stronger, the pacing faster, and the hook more TikTok-ready.",
    },
}


def _mode_profile(export_mode: str) -> dict[str, str]:
    return _MODE_PROFILES.get(str(export_mode or "").strip(), _MODE_PROFILES["TikTok Emotional"])


def _style_profile(prompt_style: str) -> dict[str, str]:
    return _STYLE_PROFILES.get(str(prompt_style or "").strip(), _STYLE_PROFILES["Balanced"])


def _hook_lines(full_hook_section: str) -> list[str]:
    return [line.strip() for line in str(full_hook_section or "").splitlines() if line.strip()]


def _format_time(seconds: float) -> str:
    seconds = max(0, float(seconds or 0))
    minutes = int(seconds // 60)
    secs = int(round(seconds - minutes * 60))
    if secs >= 60:
        minutes += 1
        secs -= 60
    return f"{minutes}:{secs:02d}"


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


def build_scene_breakdown(
    full_hook_section: str,
    *,
    hook_duration: float = 15.0,
    export_mode: str = "TikTok Emotional",
    prompt_style: str = "Balanced",
    mood: str = "",
) -> dict[str, Any]:
    lines = _hook_lines(full_hook_section)
    duration = max(4.0, float(hook_duration or 15.0))
    scene_count = max(2, min(6, len(lines) if lines else 3, int(round(duration / 5.0)) or 3))
    if duration >= 24:
        scene_count = max(scene_count, 5)
    elif duration >= 18:
        scene_count = max(scene_count, 4)
    mode = _mode_profile(export_mode)
    style = _style_profile(prompt_style)
    emotion = summarize_hook_emotion(full_hook_section, mood=mood)
    shot_types = ["wide establishing shot", "medium emotional shot", "profile shot", "close-up face and eyes", "emotional release shot", "quiet ending frame"]
    camera_moves = ["slow cinematic drift", "slow push-in", "subtle handheld sway", "emotional close-up push", "soft dissolve-ready movement", "slow pull-out"]
    lighting_steps = ["soft natural window light", "warmer isolated shadows", "stronger contrast on the hook peak", "deep emotional rim light", "soft release glow", "quiet fading light"]
    emotions = ["loneliness", "longing", "realization", "emotional climax", "release", "afterglow"]
    shots = []
    text_blocks = []
    for idx in range(scene_count):
        start = round(duration * idx / scene_count, 2)
        end = round(duration * (idx + 1) / scene_count, 2)
        hook_line = lines[min(idx, len(lines) - 1)] if lines else str(full_hook_section or "").strip()
        shot_type = shot_types[idx % len(shot_types)]
        camera = camera_moves[idx % len(camera_moves)]
        lighting = lighting_steps[idx % len(lighting_steps)]
        scene_emotion = emotions[idx % len(emotions)]
        if idx == scene_count - 1:
            scene_emotion = "emotional release"
        prompt = (
            f"{shot_type} for a vertical 9:16 cinematic music video, same character and same room, "
            f"{lighting}, {scene_emotion}, {camera}, {mode['mood']}, {style['detail']}, "
            "no text, no logo, no watermark, no subtitles inside the image or video."
        )
        shot = {
            "shot_id": f"shot_{idx + 1:02d}",
            "start_time": start,
            "end_time": end,
            "duration": round(end - start, 2),
            "hook_line": hook_line,
            "visual_focus": shot_type,
            "camera_motion": camera,
            "lighting": lighting,
            "emotion": scene_emotion,
            "prompt": prompt,
        }
        shots.append(shot)
        text_blocks.append(
            "\n".join(
                [
                    f"Scene {idx + 1:02d}",
                    f"{_format_time(start)}-{_format_time(end)}",
                    f"Visual: {shot_type}; same character, same location, same emotional palette.",
                    f"Camera: {camera}; {mode['camera']}.",
                    f"Emotion: {scene_emotion}; follows the full hook arc: {emotion['progression']}.",
                    f"Prompt: {prompt}",
                ]
            )
        )
    return {"scene_breakdown": "\n\n".join(text_blocks), "shot_list": shots, "scene_count": scene_count}


def build_prompt_director_package(
    full_hook_section: str,
    *,
    song_title: str = "",
    artist_name: str = "",
    mood: str = "",
    export_mode: str = "TikTok Emotional",
    prompt_style: str = "Balanced",
    hook_duration: float = 15.0,
) -> dict[str, Any]:
    emotion = summarize_hook_emotion(full_hook_section, mood=mood)
    title = song_title or "Untitled Hook"
    artist = artist_name or "VelaFlow Creator"
    hook_clean = re.sub(r"\s+", " ", str(full_hook_section or "").strip())
    mode = _mode_profile(export_mode)
    style = _style_profile(prompt_style)
    scenes = build_scene_breakdown(full_hook_section, hook_duration=hook_duration, export_mode=export_mode, prompt_style=prompt_style, mood=mood)
    base_scene = (
        "Cinematic emotional Thai music video. Young Thai woman alone near apartment window at night. "
        "Slow emotional camera movement. Melancholic atmosphere. Warm cinematic lighting. "
        "Natural human motion. Realistic film look. Vertical 9:16. "
        f"Emotional progression from {emotion['progression']}. "
        f"Creator export mode: {export_mode}. Prompt style: {prompt_style}. "
        f"Pacing: {mode['pacing']}. {style['prompt']}"
    )
    continuity = (
        "Maintain the same character, same apartment room, same wardrobe, same warm rainy-night lighting palette, "
        "and a continuous emotional arc across the full hook section."
    )
    safety = "No text inside video, no logo, no watermark, no subtitles, no subtitle inside AI video."
    scene_language = (
        "Use cinematic pacing, slow emotional camera movement, wide-to-medium-to-close-up scene progression, "
        "natural acting, and clear vertical 9:16 framing."
    )
    return {
        "hook_summary": f"{title} by {artist}: {emotion['emotional_tone']} hook sequence about {hook_clean[:180]}",
        "hook_emotion": emotion,
        "export_mode": export_mode,
        "prompt_style": prompt_style,
        "mode_profile": mode,
        "style_profile": style,
        "scene_breakdown": scenes["scene_breakdown"],
        "shot_list": scenes["shot_list"],
        "scene_count": scenes["scene_count"],
        "image_prompt": (
            f"{base_scene} {scene_language} Premium realistic film still, subtle skin texture, natural shadows, "
            f"{mode['mood']}, {style['detail']}, no text, no logo. {continuity}"
        ),
        "video_prompt_flow": (
            f"{base_scene} One continuous vertical cinematic hook sequence for Flow. {scene_language} "
            f"{mode['camera']}. {continuity} {safety} No split screen."
        ),
        "video_prompt_veo": (
            f"{base_scene} Generate realistic live-action vertical 9:16 video shots with natural human motion. "
            f"{scene_language} {mode['camera']}. {continuity} {safety}"
        ),
        "video_prompt_runway": (
            f"{base_scene} Realistic live-action shot progression with wide lonely opening, medium emotional build, "
            f"close-up emotional climax, soft release ending. {scene_language} {mode['pacing']}. {continuity} {safety}"
        ),
        "video_prompt_kling": (
            f"{base_scene} Cinematic realistic vertical 9:16 music video prompt for Kling. "
            f"{scene_language} Keep emotional continuity and smooth camera movement. {mode['camera']}. {continuity} {safety}"
        ),
        "thumbnail_prompt": (
            "Vertical emotional thumbnail frame, close-up expressive eyes near rainy window, warm cinematic rim light, "
            f"mobile-readable composition, {mode['mood']}, no text, no logo."
        ),
        "cinematic_direction": (
            "Start with a lonely wide shot, move into a medium profile shot, then a close-up for the strongest hook line. "
            f"Use {mode['pacing']}, {mode['camera']}, and bottom-safe subtitle space."
        ),
        "mood_summary": f"{emotion['emotional_tone']} with {emotion['progression']}. {mode['mood']}. {style['detail']}.",
    }


def export_prompt_director_files(package: dict[str, Any], export_dir: str | Path) -> dict[str, str]:
    folder = Path(export_dir)
    folder.mkdir(parents=True, exist_ok=True)
    files = {
        "hook_summary.txt": package.get("hook_summary", ""),
        "hook_emotion.json": json.dumps(package.get("hook_emotion", {}), ensure_ascii=False, indent=2),
        "scene_breakdown.txt": package.get("scene_breakdown", ""),
        "shot_list.json": json.dumps(package.get("shot_list", []), ensure_ascii=False, indent=2),
        "image_prompt.txt": package.get("image_prompt", ""),
        "video_prompt_flow.txt": package.get("video_prompt_flow", ""),
        "video_prompt_veo.txt": package.get("video_prompt_veo", ""),
        "video_prompt_runway.txt": package.get("video_prompt_runway", ""),
        "video_prompt_kling.txt": package.get("video_prompt_kling", ""),
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
