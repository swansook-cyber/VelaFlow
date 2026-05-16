from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from core.paths import resolve_project_folder
from core.project_io import safe_name


CHARACTER_TYPES: dict[str, dict[str, str]] = {
    "banana": {"label": "🍌 Banana", "species": "banana character", "palette": "bright yellow body, soft brown stem"},
    "cat": {"label": "🐱 Cat", "species": "cat character", "palette": "warm fur color, cute rounded face"},
    "heart": {"label": "🫀 Heart", "species": "talking heart character", "palette": "red and pink heart body"},
    "brain": {"label": "🧠 Brain", "species": "talking brain character", "palette": "soft pink brain texture"},
    "egg": {"label": "🥚 Egg", "species": "fried egg character", "palette": "white egg body, yellow yolk face"},
    "avocado": {"label": "🥑 Avocado", "species": "avocado character", "palette": "green avocado body, warm brown seed"},
    "bread": {"label": "🍞 Bread", "species": "bread character", "palette": "golden toast body"},
    "bubble_tea": {"label": "🧋 Bubble Tea", "species": "bubble tea cup character", "palette": "milk tea beige, black tapioca pearls"},
    "bone": {"label": "🦴 Bone", "species": "talking bone character", "palette": "white bone body, soft gray shadows"},
    "lung": {"label": "🫁 Lung", "species": "talking lung character", "palette": "soft pink lung body"},
}

PERSONALITY_PROMPTS = {
    "Funny": "funny, witty, quick comedic timing",
    "Chaotic": "chaotic, loud, unpredictable, meme energy",
    "Sad": "sad but relatable, emotional, slightly dramatic",
    "Aggressive": "aggressive comic rant, bold facial expressions",
    "Cute": "cute, wholesome, friendly, playful",
    "Dark Humor": "dark humor, dry sarcasm, deadpan expression",
    "Motivational": "motivational, confident, warm encouragement",
}

STYLE_PROMPTS = {
    "Cute 3D": "cute 3D cartoon, soft rounded shapes, expressive face",
    "TikTok Meme": "TikTok viral meme style, bold expression, high contrast",
    "Pixar-like": "premium 3D animated character style, cinematic but original",
    "Cartoon": "colorful cartoon style, clean outlines, expressive face",
    "Chibi": "chibi proportions, oversized head, tiny body, adorable expression",
    "Emotional": "emotional animated character, cinematic lighting, expressive eyes",
}

VIRAL_CHARACTER_IDEAS = [
    "แมว toxic รีวิวแฟนเก่า",
    "สมองด่าหัวใจ",
    "กล้วยโดนเท",
    "ไข่ดาวบ่นชีวิตคนทำงาน",
    "อะโวคาโดสายดาร์ก",
    "หัวใจเถียงกับสมองเรื่องแฟนเก่า",
    "ชานมไข่มุกรีวิวชีวิตออฟฟิศ",
    "ทุเรียนสายดาร์กบ่นเรื่องความรัก",
]


@dataclass
class CharacterProfile:
    character_id: str
    name: str
    species: str
    gender_style: str
    color_palette: str
    accessories: str
    face_style: str
    eye_style: str
    clothing_style: str
    voice_style: str
    personality: str
    seed: str
    reference_prompt: str


def generate_character_seed(name: str = "", character_type: str = "", personality: str = "") -> str:
    source = f"{name}|{character_type}|{personality}|{datetime.now().isoformat(timespec='microseconds')}"
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:12]


def create_character_profile(
    character_type: str = "banana",
    *,
    personality: str = "Funny",
    style: str = "Cute 3D",
    voice_style: str = "Cute",
    seed: str = "",
    name: str = "",
    accessories: str = "",
) -> dict[str, Any]:
    type_data = CHARACTER_TYPES.get(character_type) or CHARACTER_TYPES["banana"]
    seed = seed or generate_character_seed(name or type_data["species"], character_type, personality)
    display_name = name or f"{type_data['species'].title()} {seed[:4]}"
    personality_prompt = PERSONALITY_PROMPTS.get(personality, personality)
    style_prompt = STYLE_PROMPTS.get(style, style)
    accessories = accessories or "small black glasses" if character_type in {"banana", "brain"} else accessories or "no extra accessories"
    profile = CharacterProfile(
        character_id=f"{safe_name(character_type)}_{seed}",
        name=display_name,
        species=type_data["species"],
        gender_style="neutral creator character",
        color_palette=type_data["palette"],
        accessories=accessories,
        face_style=f"{style_prompt}, same face every scene",
        eye_style="large expressive eyes, consistent eye shape",
        clothing_style="simple clean character design, no random logos",
        voice_style=voice_style,
        personality=personality_prompt,
        seed=seed,
        reference_prompt="",
    )
    data = asdict(profile)
    data["reference_prompt"] = build_character_prompt(data)
    return data


def build_character_prompt(profile: dict[str, Any]) -> str:
    return (
        f"{profile.get('name', 'same character')}, {profile.get('species', '')}, "
        f"{profile.get('color_palette', '')}, {profile.get('accessories', '')}, "
        f"{profile.get('face_style', '')}, {profile.get('eye_style', '')}, "
        f"{profile.get('clothing_style', '')}, personality: {profile.get('personality', '')}, "
        "same character, same face, same accessories, same colors, same personality, character consistency"
    )


def apply_character_consistency(scene_prompt: str, profile: dict[str, Any] | None, strength: str = "high") -> str:
    if not profile:
        return scene_prompt
    consistency = build_character_prompt(profile)
    strength_note = "strong character lock" if strength == "high" else "medium character consistency"
    return f"{scene_prompt}, {consistency}, {strength_note}, seed {profile.get('seed', '')}"


def save_character_profile(project_name: str, profile: dict[str, Any], workflow_type: str = "clips") -> dict[str, Any]:
    try:
        folder = resolve_project_folder(project_name or "hook_clip", workflow_type)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "character_profile.json"
        path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "message": "Character profile saved", "data": {"path": str(path), "profile": profile}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Character profile save failed", "data": {}, "error": str(exc)}


def load_character_profile(project_name: str, workflow_type: str = "clips") -> dict[str, Any]:
    path = resolve_project_folder(project_name or "hook_clip", workflow_type) / "character_profile.json"
    try:
        if path.is_file():
            return {"ok": True, "message": "Character profile loaded", "data": {"path": str(path), "profile": json.loads(path.read_text(encoding="utf-8"))}, "error": ""}
        return {"ok": False, "message": "Character profile missing", "data": {"path": str(path)}, "error": "missing_character_profile"}
    except Exception as exc:
        return {"ok": False, "message": "Character profile load failed", "data": {"path": str(path)}, "error": str(exc)}


def random_viral_character_idea(character_type: str = "", personality: str = "") -> str:
    type_label = CHARACTER_TYPES.get(character_type, {}).get("species", "")
    if type_label and personality:
        templates = [
            f"{type_label} {personality.lower()} บ่นเรื่องชีวิต",
            f"{type_label} รีวิวแฟนเก่าแบบ {personality.lower()}",
            f"{type_label} เถียงกับหัวใจเรื่องงาน",
        ]
        return random.choice(templates)
    return random.choice(VIRAL_CHARACTER_IDEAS)
