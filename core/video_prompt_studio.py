from __future__ import annotations

from datetime import datetime
from typing import Any


PROJECT_TYPES = ["Music MV", "TikTok Affiliate Clip", "Spotify Canvas", "YouTube Shorts"]
TARGET_PLATFORMS = ["Google Whisk", "Flow", "Veo", "Runway", "Kling", "Pika", "Luma", "Multi Platform"]
CLIP_LENGTHS = ["6s", "10s", "15s", "30s", "60s"]
PRESETS: dict[str, dict[str, str]] = {
    "Sad Pop MV": {
        "project_type": "Music MV",
        "mood": "sad, emotional, intimate",
        "visual_style": "cinematic Thai pop, rainy window, soft warm light",
        "target_platform": "Flow",
        "clip_length": "15s",
        "reference_style_notes": "A24-style emotional realism, no text in frame",
    },
    "Office Rant Podcast Clip": {
        "project_type": "YouTube Shorts",
        "mood": "tired, relatable, direct",
        "visual_style": "dark office desk, late night, realistic creator monologue",
        "target_platform": "Runway",
        "clip_length": "30s",
        "reference_style_notes": "close-up office stress, clean captions added later",
    },
    "TikTok Affiliate Product Promo": {
        "project_type": "TikTok Affiliate Clip",
        "mood": "useful, fast, creator-friendly",
        "visual_style": "UGC product close-up, hands-on demo, bright home setup",
        "target_platform": "Kling",
        "clip_length": "15s",
        "reference_style_notes": "no fake price text, natural hand interaction",
    },
    "Cinematic Spotify Canvas": {
        "project_type": "Spotify Canvas",
        "mood": "minimal, looping, atmospheric",
        "visual_style": "single cinematic object/character loop, premium lighting",
        "target_platform": "Luma",
        "clip_length": "6s",
        "reference_style_notes": "seamless loop feeling, no typography",
    },
    "Emotional Story Short": {
        "project_type": "YouTube Shorts",
        "mood": "heartbreak, reflective, human",
        "visual_style": "realistic cinematic apartment, emotional close-up",
        "target_platform": "Veo",
        "clip_length": "30s",
        "reference_style_notes": "same character, same room, emotional progression",
    },
}


def _clean(value: str, fallback: str = "") -> str:
    return " ".join(str(value or fallback).split()).strip()


def _lines(text: str) -> list[str]:
    rows = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    if rows:
        return rows
    compact = _clean(text)
    return [compact] if compact else []


def _scene_count(clip_length: str) -> int:
    digits = "".join(ch for ch in str(clip_length) if ch.isdigit())
    seconds = int(digits or 15)
    if seconds <= 6:
        return 2
    if seconds <= 15:
        return 3
    if seconds <= 30:
        return 5
    return 6


def _word_count(text: str) -> int:
    return len([part for part in str(text or "").replace("\n", " ").split(" ") if part.strip()])


def _is_bullet_heavy(text: str) -> bool:
    rows = [row.strip() for row in str(text or "").splitlines() if row.strip()]
    if len(rows) < 6:
        return False
    bullet_rows = [row for row in rows if row.startswith(("-", "*", "•")) or row[:2].replace(".", "").isdigit()]
    return len(bullet_rows) / max(1, len(rows)) > 0.65


def _video_quality_report(package: dict[str, Any]) -> dict[str, Any]:
    prompts = [str(prompt or "") for prompt in package.get("shot_prompts", [])]
    full_text = "\n".join(
        [
            package.get("full_shot_package", ""),
            package.get("whisk_prompt", ""),
            package.get("video_prompt", ""),
            package.get("negative_prompt", ""),
        ]
    )
    required_terms = ["vertical 9:16", "camera", "lighting", "mood", "no text", "no watermark"]
    return {
        "min_scene_count": len(package.get("scene_list", [])) >= 2,
        "shot_prompts_detailed": all(_word_count(prompt) >= 28 for prompt in prompts),
        "required_terms_present": all(term in full_text.lower() for term in required_terms),
        "not_bullet_only": not _is_bullet_heavy(package.get("full_shot_package", "")),
        "no_placeholder_text": "placeholder" not in full_text.lower() and "lorem" not in full_text.lower(),
    }


def build_video_prompt_package(
    *,
    project_type: str,
    main_idea: str,
    mood: str,
    visual_style: str,
    target_platform: str,
    clip_length: str,
    reference_style_notes: str = "",
) -> dict[str, Any]:
    project_type = project_type if project_type in PROJECT_TYPES else "Music MV"
    target_platform = target_platform if target_platform in TARGET_PLATFORMS else "Multi Platform"
    clip_length = clip_length if clip_length in CLIP_LENGTHS else "15s"
    mood = _clean(mood, "emotional cinematic")
    visual_style = _clean(visual_style, "realistic cinematic vertical video")
    idea_lines = _lines(main_idea)[:8]
    idea_summary = idea_lines[0] if idea_lines else "A short emotional creator video"
    scene_total = _scene_count(clip_length)
    scene_list = []
    shot_prompts = []
    for index in range(scene_total):
        shot_id = f"shot_{index + 1:02d}"
        source_line = idea_lines[index % len(idea_lines)] if idea_lines else idea_summary
        energy = ["opening hook", "emotional build", "detail moment", "climax", "release", "ending loop"][min(index, 5)]
        camera = ["slow push-in", "gentle handheld drift", "medium close-up pan", "emotional close-up", "soft pull-out", "subtle loop motion"][min(index, 5)]
        lighting = ["soft natural light", "warm cinematic shadows", "stronger contrast", "emotional highlight", "soft release light", "clean loop lighting"][min(index, 5)]
        scene = {
            "shot_id": shot_id,
            "duration_hint": "2-4 seconds",
            "visual_focus": source_line,
            "camera_movement": camera,
            "lighting": lighting,
            "emotion": energy,
            "prompt": (
                f"Single continuous vertical 9:16 cinematic shot for {target_platform}, {visual_style}. "
                f"Story moment: {source_line}. Emotional intent: {energy}; mood: {mood}. "
                f"Camera movement: {camera} with natural motion and stable subject continuity. "
                f"Lighting: {lighting}, realistic shadows, clean depth of field, platform-safe framing. "
                "No text, no subtitles, no logo, no watermark, no collage, no split screen."
            ),
        }
        scene_list.append(scene)
        shot_prompts.append(scene["prompt"])
    continuity = "Keep the same character, location, wardrobe, lighting palette, and emotional tone across all shots."
    negative_prompt = "No text, no subtitles, no logos, no watermark, no split screen, no collage, no storyboard sheet, no comic panels, no UI overlay, no distorted hands, no extra faces."
    whisk_prompt = (
        f"Image/style reference prompt for Google Whisk: vertical 9:16, {visual_style}. {continuity} "
        f"Create one clean reference frame for: {idea_summary}. Mood: {mood}. {negative_prompt}"
    )
    video_prompt = (
        f"{target_platform} AI video prompt: Create a {clip_length} {project_type} in vertical 9:16. "
        f"Concept: {idea_summary}. {continuity} Build a shot-by-shot emotional progression with "
        "opening hook, visual detail, emotional peak, and soft ending. Use natural human motion, "
        f"cinematic camera movement, realistic lighting, and color tone: {visual_style}. Mood: {mood}. "
        f"Reference notes: {_clean(reference_style_notes, 'clean cinematic continuity')}. {negative_prompt}"
    )
    full_package = "\n\n".join(
        [
            "OVERALL VIDEO CONCEPT",
            f"{project_type}: {idea_summary}\nMood: {mood}\nVisual style: {visual_style}\nTarget: {target_platform}\nLength: {clip_length}",
            "SCENE LIST / STORYBOARD",
            "\n\n".join(
                f"{scene['shot_id']}\nVisual: {scene['visual_focus']}\nCamera: {scene['camera_movement']}\nLighting: {scene['lighting']}\nPrompt: {scene['prompt']}"
                for scene in scene_list
            ),
            "WHISK IMAGE PROMPT",
            whisk_prompt,
            "VIDEO PROMPT",
            video_prompt,
            "NEGATIVE PROMPT",
            negative_prompt,
        ]
    )
    thai_caption = f"คลิปนี้เล่าอารมณ์แบบ {mood} ผ่านภาพ {visual_style}"
    english_caption = f"A {mood} {project_type.lower()} concept built for {target_platform}."
    hashtags = ["#VelaFlow", "#AIVideo", "#VideoPrompt", "#Shorts", "#TikTokCreator"]
    package = {
        "ok": True,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "project_type": project_type,
        "main_idea": main_idea,
        "mood": mood,
        "visual_style": visual_style,
        "target_platform": target_platform,
        "clip_length": clip_length,
        "reference_style_notes": reference_style_notes,
        "overall_video_concept": f"{project_type} with {mood} mood: {idea_summary}",
        "scene_list": scene_list,
        "shot_prompts": shot_prompts,
        "whisk_prompt": whisk_prompt,
        "video_prompt": video_prompt,
        "camera_movement": ", ".join(scene["camera_movement"] for scene in scene_list),
        "lighting_and_color_tone": visual_style,
        "negative_prompt": negative_prompt,
        "thai_caption": thai_caption,
        "english_caption": english_caption,
        "hashtags": hashtags,
        "full_shot_package": full_package,
    }
    package["quality_report"] = _video_quality_report(package)
    package["ok"] = all(package["quality_report"].values())
    return package


def video_prompt_package_to_text(package: dict[str, Any]) -> str:
    return "\n\n".join(
        [
            "VELAFLOW VIDEO PROMPT STUDIO",
            f"Project Type: {package.get('project_type', '')}",
            f"Target Platform: {package.get('target_platform', '')}",
            f"Clip Length: {package.get('clip_length', '')}",
            "",
            package.get("full_shot_package", ""),
            "THAI CAPTION",
            package.get("thai_caption", ""),
            "ENGLISH CAPTION",
            package.get("english_caption", ""),
            "HASHTAGS",
            " ".join(package.get("hashtags", [])),
        ]
    )
