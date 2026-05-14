import re
from typing import Any, Dict, List


DEFAULT_CHARACTER: Dict[str, str] = {
    "name": "",
    "role": "lead singer",
    "gender": "unspecified",
    "age_range": "",
    "ethnicity": "Thai",
    "hair": "",
    "face": "",
    "body": "",
    "outfit": "",
    "color_palette": "",
    "mood": "",
    "style_notes": "",
    "reference_image_path": "",
    "reference_notes": "",
    "negative_notes": "do not change face, hairstyle, outfit, age, ethnicity, or main wardrobe identity",
}

PROMPT_FIELDS = [
    ("name", "name"),
    ("role", "role"),
    ("gender", "gender"),
    ("age_range", "age"),
    ("ethnicity", "ethnicity"),
    ("hair", "hair"),
    ("face", "face"),
    ("body", "body"),
    ("outfit", "outfit"),
    ("color_palette", "color palette"),
    ("mood", "core mood"),
    ("style_notes", "style notes"),
    ("reference_image_path", "reference image"),
    ("reference_notes", "reference notes"),
]

SCORE_FIELDS = [
    ("name", "name"),
    ("gender", "gender"),
    ("ethnicity", "ethnicity"),
    ("hair", "hair"),
    ("face", "face"),
    ("outfit", "outfit"),
    ("mood", "mood"),
    ("style_notes", "style"),
    ("reference_notes", "reference notes"),
]

STOP_WORDS = {
    "and",
    "the",
    "with",
    "for",
    "from",
    "same",
    "main",
    "core",
    "style",
    "notes",
    "image",
    "reference",
    "character",
}


def normalize_character(character: Dict[str, Any] | None) -> Dict[str, str]:
    normalized = dict(DEFAULT_CHARACTER)
    for key, value in (character or {}).items():
        if key in normalized:
            normalized[key] = "" if value is None else str(value).strip()
        else:
            normalized[key] = value
    return normalized


def build_character_prompt(character: Dict[str, Any] | None) -> str:
    character = normalize_character(character)
    parts: List[str] = []
    for key, label in PROMPT_FIELDS:
        value = str(character.get(key, "") or "").strip()
        if value:
            parts.append(f"{label}: {value}")
    if not parts:
        return ""
    negative = str(character.get("negative_notes", "") or "").strip()
    prompt = "Keep one consistent character across every scene; " + "; ".join(parts)
    if negative:
        prompt += f"; continuity guardrails: {negative}"
    return prompt


def apply_character_to_prompt(prompt: str, character: Dict[str, Any] | None, character_note: str = "") -> str:
    prompt = (prompt or "").strip()
    note = (character_note or build_character_prompt(character)).strip()
    if not note:
        return prompt
    if note in prompt:
        return prompt
    separator = "\n\n" if prompt else ""
    return f"{prompt}{separator}Character lock: {note}".strip()


def _tokens(value: str) -> List[str]:
    value = (value or "").lower().strip()
    if not value:
        return []
    words = [word for word in re.findall(r"[a-z0-9]+", value) if len(word) > 2 and word not in STOP_WORDS]
    if words:
        return words[:8]
    return [value]


def consistency_report(prompt: str, character: Dict[str, Any] | None) -> Dict[str, Any]:
    character = normalize_character(character)
    prompt_lower = (prompt or "").lower()
    checks: List[Dict[str, Any]] = []
    for key, label in SCORE_FIELDS:
        value = str(character.get(key, "") or "").strip()
        tokens = _tokens(value)
        if not tokens:
            continue
        matched = any(token in prompt_lower for token in tokens)
        checks.append({"field": key, "label": label, "value": value, "matched": matched})

    if not checks:
        return {"score": 0, "missing": ["No character sheet defined"], "checks": []}

    matched_count = sum(1 for item in checks if item["matched"])
    score = round((matched_count / len(checks)) * 100)
    missing = [item["label"] for item in checks if not item["matched"]]
    return {"score": score, "missing": missing, "checks": checks}


def apply_character_to_storyboard(storyboard: List[Dict[str, Any]], character: Dict[str, Any] | None) -> List[Dict[str, Any]]:
    note = build_character_prompt(character)
    updated: List[Dict[str, Any]] = []
    for scene in storyboard or []:
        item = dict(scene)
        base_prompt = item.get("expanded_prompt") or item.get("image_prompt") or item.get("prompt_core") or ""
        prompt_with_character = apply_character_to_prompt(base_prompt, character, note)
        report = consistency_report(prompt_with_character, character)
        item["character_prompt"] = note
        item["image_prompt_with_character"] = prompt_with_character
        item["character_consistency_score"] = report["score"]
        item["character_consistency_missing"] = report["missing"]
        updated.append(item)
    return updated
