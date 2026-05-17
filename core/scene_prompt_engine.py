from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


PROMPT_STYLES: dict[str, dict[str, str]] = {
    "Emotional": {
        "aesthetic": "cinematic Thai emotional short film, warm low-key lighting, intimate framing",
        "metaphor": "empty room, soft window light, objects left behind",
        "palette": "warm amber and soft shadow",
    },
    "Dark": {
        "aesthetic": "dark urban night, realistic cinematic drama, high contrast shadows",
        "metaphor": "wet street, neon reflection, lonely silhouette",
        "palette": "deep blue, black, muted red",
    },
    "Romantic": {
        "aesthetic": "romantic cinematic realism, soft glow, gentle close-up emotion",
        "metaphor": "two coffee cups, city lights, almost-touching hands",
        "palette": "rose gold, soft cream, warm night lights",
    },
    "TikTok Meme": {
        "aesthetic": "cinematic vertical TikTok meme energy, expressive character reaction, bold composition",
        "metaphor": "oversized reaction face, playful prop, punchline-ready frame",
        "palette": "bright contrast, clean colorful background",
    },
    "Anime Nostalgia": {
        "aesthetic": "anime-inspired nostalgic city evening, emotional slice-of-life frame",
        "metaphor": "train window, school bag, sunset sky, drifting petals",
        "palette": "orange sunset, pastel purple, soft blue",
    },
    "Dreamy": {
        "aesthetic": "dreamy surreal cinematic look, soft focus, floating light particles",
        "metaphor": "mirror reflection, mist, glowing doorway, slow memory feeling",
        "palette": "lavender, pale blue, moonlit silver",
    },
    "Podcast Drama": {
        "aesthetic": "dramatic podcast clip visual, office night realism, documentary close-up",
        "metaphor": "desk lamp, empty office chair, unread messages",
        "palette": "fluorescent office green, shadow, muted gray",
    },
    "Cute Character": {
        "aesthetic": "cute 3D cartoon viral character, expressive face, vertical short-form style",
        "metaphor": "tiny character in an oversized real-life situation",
        "palette": "bright playful colors, clean soft background",
    },
}


REALISM_PROMPT_LAYER = (
    "cinematic realism, realistic skin texture, natural facial proportions, "
    "realistic hair detail, realistic fabric folds, natural room detail, subtle imperfections, "
    "natural depth, cinematic shadows, believable exposure, soft film grain, human emotional presence"
)

REALISM_NEGATIVE_LAYER = (
    "avoid plastic AI faces, avoid synthetic skin, avoid oversharpened eyes, avoid fake HDR look, "
    "avoid unrealistic glow, avoid fantasy aesthetics, avoid random exposure jumps, "
    "avoid flat lighting, avoid robotic pose, avoid warped hands, avoid inconsistent face"
)

LIGHTING_EVOLUTION = {
    1: "soft natural window light, gentle falloff, quiet intro atmosphere",
    2: "mood isolation with practical room light, deeper side shadow, same exposure family",
    3: "stronger contrast, emotional shadow depth, natural eye catchlight, hook peak intensity",
    4: "softer release light, lower contrast, quiet emotional closure",
}


EMOTION_KEYWORDS: dict[str, list[str]] = {
    "heartbreak": ["เจ็บ", "เสียใจ", "เลิก", "ลืม", "ร้องไห้", "พอแล้ว", "hurt", "heartbreak"],
    "lonely": ["เหงา", "คนเดียว", "ว่างเปล่า", "คิดถึง", "lonely", "missing"],
    "hope": ["เริ่มใหม่", "เดินต่อ", "หวัง", "ดีขึ้น", "hope", "heal"],
    "anger": ["โกรธ", "พัง", "ไม่ไหว", "toxic", "rant"],
    "love": ["รัก", "แฟน", "หัวใจ", "romantic", "crush"],
    "funny": ["ฮา", "ตลก", "บ่น", "meme", "funny"],
}


STYLE_ALIASES = {
    "emotional_story": "Emotional",
    "viral_meme": "TikTok Meme",
    "cute_character": "Cute Character",
    "podcast_drama": "Podcast Drama",
    "cinematic_mv": "Dreamy",
    "affiliate_sell": "TikTok Meme",
}


def normalize_prompt_style(style: str | None, preset_id: str | None = None) -> str:
    candidate = str(style or "").strip()
    if candidate in PROMPT_STYLES:
        return candidate
    mapped = STYLE_ALIASES.get(str(preset_id or "").strip())
    if mapped:
        return mapped
    lowered = candidate.lower()
    for name in PROMPT_STYLES:
        if name.lower() == lowered:
            return name
    return "Emotional"


def detect_scene_emotion(text: str) -> dict[str, Any]:
    value = str(text or "").lower()
    scores: dict[str, int] = {}
    for emotion, keywords in EMOTION_KEYWORDS.items():
        scores[emotion] = sum(1 for keyword in keywords if keyword.lower() in value)
    primary = max(scores, key=scores.get) if any(scores.values()) else "emotional"
    intensity = min(100, 45 + scores.get(primary, 0) * 18 + min(25, len(value) // 18))
    return {"primary_emotion": primary, "intensity": intensity, "scores": scores}


def _clean_lyric(lyric: str) -> str:
    cleaned = re.sub(r"\[[^\]]+\]", " ", str(lyric or ""))
    cleaned = re.sub(r"\([^)]*\)", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _metaphor_for_emotion(emotion: str, style_config: dict[str, str]) -> str:
    overrides = {
        "heartbreak": "cracked mirror, empty side of the bed, rain sliding on glass",
        "lonely": "one chair under street light, unread chat bubbles, silent night room",
        "hope": "first morning light, open door, slow walk forward",
        "anger": "tight close-up, harsh shadow, phone screen glowing in the dark",
        "love": "soft city lights, hand holding a small keepsake, warm reflection",
        "funny": "oversized everyday object, expressive reaction, playful visual punchline",
    }
    return overrides.get(emotion, style_config["metaphor"])


def build_scene_prompt(
    lyric: str,
    *,
    style: str = "Emotional",
    scene_index: int = 1,
    hook_text: str = "",
    preset_id: str = "",
    mood: str = "",
    director_scene: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prompt_style = normalize_prompt_style(style, preset_id)
    style_config = PROMPT_STYLES[prompt_style]
    cleaned = _clean_lyric(lyric or hook_text)
    emotion = detect_scene_emotion(" ".join([cleaned, hook_text, mood]))
    metaphor = _metaphor_for_emotion(emotion["primary_emotion"], style_config)
    scene_progression = {
        1: {
            "focus": "wide establishing shot, lonely room and emotional atmosphere, strongest mood in the first 2 seconds",
            "camera": "wide vertical establishing shot, one subject only, full-screen scene",
            "shot_type": "wide establishing shot",
            "camera_distance": "wide",
            "subject_action": "same character alone in the room, still body language, looking toward a window or empty space",
            "lighting": LIGHTING_EVOLUTION[1],
            "composition": "eyes near upper third when visible, cinematic negative space, no collage, no split screen, empty lower third for subtitles",
        },
        2: {
            "focus": "emotional story turn with new angle",
            "camera": "medium side angle in the same environment, cinematic depth and parallax",
            "shot_type": "medium emotional shot",
            "camera_distance": "medium",
            "subject_action": "same character in the same room, stronger feeling, hand holding a phone or small memory object",
            "lighting": LIGHTING_EVOLUTION[2],
            "composition": "proper headroom, same character and location continuity, one emotional moment at a time",
        },
        3: {
            "focus": "close-up emotional face and eyes, strongest hook moment, replay-worthy emotional peak",
            "camera": "dramatic push-in frame with the same character, clear silhouette or face priority",
            "shot_type": "close-up emotional face / eyes",
            "camera_distance": "close-up",
            "subject_action": "same character close-up, eyes carrying the hook lyric, strongest emotional expression",
            "lighting": LIGHTING_EVOLUTION[3],
            "composition": "eyes near upper third, full-screen mini movie ending, mobile thumbnail readable, high contrast center subject, subtitle-safe lower third",
        },
    }
    progression = scene_progression.get(scene_index, scene_progression[3])
    if director_scene:
        progression = {
            **progression,
            "focus": director_scene.get("emotional_intent") or progression["focus"],
            "shot_type": director_scene.get("shot_type") or progression["shot_type"],
            "camera_distance": director_scene.get("camera_distance") or progression["camera_distance"],
            "subject_action": director_scene.get("subject_action") or progression["subject_action"],
            "lighting": director_scene.get("lighting_direction") or progression["lighting"],
        }
    cinematic_prompt = (
        f"{style_config['aesthetic']}, {progression['focus']}, visual metaphor: {metaphor}, "
        f"emotion: {emotion['primary_emotion']} intensity {emotion['intensity']}/100, "
        f"cinematic shot type: {progression['shot_type']}, camera distance: {progression['camera_distance']}, "
        f"subject action: {progression['subject_action']}, {progression['camera']}, {progression['lighting']}, {progression['composition']}, "
        f"{REALISM_PROMPT_LAYER}, "
        "lens feeling: intimate 35mm/50mm emotional cinema lens, motion-friendly composition, "
        f"vertical 9:16 composition, TikTok-ready framing, subtitle-safe lower third, "
        "strong continuity reference: same character identity, same face, same facial proportions, same hairstyle, same hair color, same clothes, same wardrobe fabric, same room/location, "
        "same emotional environment, same cinematic color palette, same lighting palette, "
        "one full-screen scene at a time, no stacked images, no collage, no split-screen layout, "
        "not a contact sheet, not a storyboard panel page, not a grid montage, not tiled frames, "
        "consistent visual story across scenes but clearly different framing, "
        f"{style_config['palette']} color palette, realistic depth, high quality, {REALISM_NEGATIVE_LAYER}, no watermark, no random text, no text inside image"
    )
    return {
        "scene_id": f"scene_{scene_index:02d}",
        "source_lyric": cleaned,
        "prompt_style": prompt_style,
        "emotion": emotion,
        "visual_metaphor": metaphor,
        "camera_language": progression["camera"],
        "shot_type": progression["shot_type"],
        "camera_distance": progression["camera_distance"],
        "subject_action": progression["subject_action"],
        "lighting_direction": progression["lighting"],
        "composition_note": progression["composition"],
        "cinematic_prompt": cinematic_prompt,
        "tiktok_aesthetic": style_config["aesthetic"],
        "subtitle_safe_note": "Keep important faces and objects away from the lower subtitle area.",
        "realistic_prompt_mode": True,
        "realism_prompt_layer": REALISM_PROMPT_LAYER,
        "realism_negative_layer": REALISM_NEGATIVE_LAYER,
    }


def build_scene_director_plan(
    scenes: list[dict[str, Any]],
    *,
    song_idea: str = "",
    hook_text: str = "",
    lyrics: str = "",
    mood: str = "",
    preset_id: str = "",
    audio_duration: float = 0.0,
) -> dict[str, Any]:
    text_context = " ".join([song_idea, hook_text, lyrics, mood])
    emotion = detect_scene_emotion(text_context)
    scene_count = max(3, min(4, len(scenes or []) or 3))
    continuity = {
        "character": "same character across every scene with consistent identity",
        "face": "same face, natural facial proportions, realistic skin texture",
        "hair": "same hairstyle, same hair color, realistic hair detail",
        "clothes": "same clothing and wardrobe with realistic fabric folds",
        "location": "same room or connected emotional location with consistent room details",
        "lighting_palette": "same cinematic warm/low-key palette with emotionally evolving contrast",
        "mood": "same emotional cinematic mood",
        "realism": "natural lighting, subtle imperfections, no plastic AI skin, no fake HDR glow",
    }
    progression = [
        {
            "song_section": "hook opening",
            "emotional_intent": "establish loneliness and atmosphere immediately",
            "shot_type": "wide establishing shot",
            "camera_distance": "wide",
            "subject_action": "alone in the same room, still body language, emotional atmosphere",
            "lighting_direction": LIGHTING_EVOLUTION[1],
            "motion_intensity": "slow breathing motion",
            "transition_style": "cinematic_cross_dissolve",
            "hook_peak": False,
        },
        {
            "song_section": "hook build",
            "emotional_intent": "make the feeling more personal and intimate",
            "shot_type": "medium emotional shot",
            "camera_distance": "medium",
            "subject_action": "same character holding a phone or memory object in the same room",
            "lighting_direction": LIGHTING_EVOLUTION[2],
            "motion_intensity": "subtle handheld drift / parallax",
            "transition_style": "blur_motion_transition",
            "hook_peak": False,
        },
        {
            "song_section": "strongest hook lyric",
            "emotional_intent": "land the strongest hook with the most emotional face/eyes",
            "shot_type": "close-up emotional face / eyes",
            "camera_distance": "close-up",
            "subject_action": "same character close-up, eyes carry the hook lyric",
            "lighting_direction": LIGHTING_EVOLUTION[3],
            "motion_intensity": "emotional push-in with cinematic micro movement",
            "transition_style": "light_flash_transition",
            "hook_peak": True,
        },
        {
            "song_section": "emotional release",
            "emotional_intent": "give visual closure without changing character or location",
            "shot_type": "emotional release ending",
            "camera_distance": "medium close-up",
            "subject_action": "same character exhales or turns away slowly",
            "lighting_direction": LIGHTING_EVOLUTION[4],
            "motion_intensity": "slow pull out with quiet breathing motion",
            "transition_style": "dip_to_black",
            "hook_peak": False,
        },
    ][:scene_count]
    directed_scenes = []
    total = float(audio_duration or 0.0)
    first_cut = 1.8 if total >= 5 else max(1.0, total * 0.33)
    for index, scene in enumerate(scenes or [{} for _ in range(scene_count)], start=1):
        template = progression[min(index - 1, len(progression) - 1)]
        directed_scenes.append(
            {
                "scene_id": scene.get("scene_id") or f"scene_{index:02d}",
                "song_section": template["song_section"],
                "emotional_intent": template["emotional_intent"],
                "shot_type": template["shot_type"],
                "camera_distance": template["camera_distance"],
                "subject_action": template["subject_action"],
                "lighting_direction": template["lighting_direction"],
                "motion_intensity": template["motion_intensity"],
                "transition_style": template["transition_style"],
                "continuity_notes": continuity,
                "hook_peak_scene": bool(template["hook_peak"]),
                "subtitle_emphasis": "strongest hook line" if template["hook_peak"] else "short emotional line",
                "target_start": 0.0 if index == 1 else round(first_cut + (index - 2) * max(1.5, (total - first_cut) / max(1, scene_count - 1)), 2) if total else 0.0,
                "director_note": "Keep the same character, same room, same clothing, same lighting. Do not change faces, outfits, locations, or palette.",
            }
        )
    return {
        "generated_by": "VelaFlow",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "song_idea": song_idea,
        "hook_text": hook_text,
        "mood": mood,
        "preset_id": preset_id,
        "audio_duration": audio_duration,
        "primary_emotion": emotion,
        "hook_peak_target": "within first 2 seconds when possible",
        "continuity_notes": continuity,
        "realistic_prompt_mode": True,
        "realism_mode": "cinematic_realism_v1",
        "lighting_profile": {
            "intro": LIGHTING_EVOLUTION[1],
            "verse": LIGHTING_EVOLUTION[2],
            "hook": LIGHTING_EVOLUTION[3],
            "ending": LIGHTING_EVOLUTION[4],
        },
        "motion_profile": {
            "style": "human emotional cinematic micro movement",
            "preferred_motion": ["slow breathing motion", "subtle handheld drift", "emotional push-in", "slow pull out"],
            "avoid": ["robotic movement", "aggressive zoom spam", "slideshow feeling"],
        },
        "shot_progression": [item["shot_type"] for item in directed_scenes],
        "scenes": directed_scenes,
    }


def build_scene_prompts(
    scenes: list[dict[str, Any]],
    *,
    hook_text: str = "",
    style: str = "Emotional",
    preset_id: str = "",
    mood: str = "",
    scene_director_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prompts: list[dict[str, Any]] = []
    director_scenes = (scene_director_plan or {}).get("scenes") or []
    for index, scene in enumerate(scenes or [], start=1):
        lyric = str(scene.get("subtitle") or scene.get("lyric_part") or scene.get("visual_prompt") or hook_text)
        director_scene = director_scenes[min(index - 1, len(director_scenes) - 1)] if director_scenes else None
        prompt = build_scene_prompt(lyric, style=style, scene_index=index, hook_text=hook_text, preset_id=preset_id, mood=mood, director_scene=director_scene)
        prompts.append(prompt)
    return {
        "generated_by": "VelaFlow",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "style": normalize_prompt_style(style, preset_id),
        "hook_text": hook_text,
        "scene_director_applied": bool(scene_director_plan),
        "scene_prompts": prompts,
    }


def apply_scene_prompts_to_package(package: dict[str, Any], scene_prompt_plan: dict[str, Any]) -> dict[str, Any]:
    prompts = scene_prompt_plan.get("scene_prompts") or []
    scenes = package.get("scene_sequence") or []
    for scene, prompt in zip(scenes, prompts):
        scene["base_visual_prompt"] = scene.get("visual_prompt", "")
        scene["visual_prompt"] = prompt.get("cinematic_prompt", scene.get("visual_prompt", ""))
        scene["visual_metaphor"] = prompt.get("visual_metaphor", "")
        scene["detected_emotion"] = prompt.get("emotion", {})
    package["scene_prompt_plan"] = scene_prompt_plan
    return package


def apply_scene_director_to_package(package: dict[str, Any], director_plan: dict[str, Any]) -> dict[str, Any]:
    by_id = {item.get("scene_id"): item for item in director_plan.get("scenes", []) or []}
    for index, scene in enumerate(package.get("scene_sequence") or [], start=1):
        directed = by_id.get(scene.get("scene_id")) or (director_plan.get("scenes") or [{}])[min(index - 1, len(director_plan.get("scenes") or [{}]) - 1)]
        scene["song_section"] = directed.get("song_section", scene.get("song_section", "hook"))
        scene["emotional_intent"] = directed.get("emotional_intent", "")
        scene["shot_type"] = directed.get("shot_type", "")
        scene["camera_distance"] = directed.get("camera_distance", "")
        scene["subject_action"] = directed.get("subject_action", "")
        scene["lighting_direction"] = directed.get("lighting_direction", scene.get("lighting", ""))
        scene["motion_intensity"] = directed.get("motion_intensity", "")
        scene["transition"] = directed.get("transition_style", scene.get("transition", "cinematic_cross_dissolve"))
        scene["continuity_notes"] = directed.get("continuity_notes", {})
        scene["hook_peak_scene"] = bool(directed.get("hook_peak_scene"))
        scene["subtitle_emphasis"] = directed.get("subtitle_emphasis", "")
    package["scene_director_plan"] = director_plan
    return package


def build_cinematic_quality_report(
    *,
    scene_prompt_plan: dict[str, Any],
    scene_director_plan: dict[str, Any],
    render_stage: dict[str, Any] | None = None,
    subtitle_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    render_stage = render_stage or {}
    subtitle_data = (subtitle_result or {}).get("data") or {}
    prompts = scene_prompt_plan.get("scene_prompts") or []
    return {
        "generated_by": "VelaFlow",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "realism_mode": "cinematic_realism_v1",
        "realistic_prompt_mode": bool(scene_director_plan.get("realistic_prompt_mode", True)),
        "continuity_mode": "same_character_same_room_same_palette",
        "lighting_profile": scene_director_plan.get("lighting_profile", {}),
        "motion_profile": scene_director_plan.get("motion_profile", {}),
        "subtitle_profile": {
            "style": "premium bottom-safe cinematic Thai subtitles",
            "mode": subtitle_data.get("mode", ""),
            "font_size_target": "small-to-medium cinematic, hook line may slightly enlarge",
            "position": "bottom safe area",
            "shadow": "soft black outline/shadow",
        },
        "prompt_quality": {
            "scene_count": len(prompts),
            "realism_terms_present": all("realistic skin texture" in str(item.get("cinematic_prompt", "")).lower() for item in prompts),
            "continuity_terms_present": all("same face" in str(item.get("cinematic_prompt", "")).lower() and "same hairstyle" in str(item.get("cinematic_prompt", "")).lower() for item in prompts),
            "negative_ai_terms_present": all("avoid plastic ai faces" in str(item.get("cinematic_prompt", "")).lower() for item in prompts),
        },
        "render_quality": {
            "visual_composition_mode": render_stage.get("visual_composition_mode", ""),
            "motion_quality_layer": render_stage.get("motion_quality_layer", ""),
            "static_only_chain": bool(render_stage.get("static_only_chain")),
            "subtitle_status": render_stage.get("subtitle_status", ""),
            "final_mp4_ok": bool(render_stage.get("final_mp4_ok")),
            "audio_attach_ok": bool(render_stage.get("audio_attach_ok")),
        },
    }


def save_cinematic_quality_report(report: dict[str, Any], output_path: str | Path) -> dict[str, Any]:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "message": "Cinematic quality report exported", "data": {"path": str(path)}, "error": ""}


def save_scene_prompts(scene_prompt_plan: dict[str, Any], output_path: str | Path) -> dict[str, Any]:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(scene_prompt_plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "message": "Scene prompts exported", "data": {"path": str(path)}, "error": ""}


def save_scene_director_plan(scene_director_plan: dict[str, Any], output_path: str | Path) -> dict[str, Any]:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(scene_director_plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "message": "Scene director plan exported", "data": {"path": str(path)}, "error": ""}
