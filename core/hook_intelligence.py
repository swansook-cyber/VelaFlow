from __future__ import annotations

import re
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.scene_scoring import score_project_scenes


def analyze_hooks(project: Dict[str, Any], limit: int = 8) -> Dict[str, Any]:
    storyboard = ((project.get("mv", {}) or {}).get("storyboard", []) or [])
    candidates: List[Dict[str, Any]] = []
    scene_scores = {item["scene_id"]: item for item in score_project_scenes(project)}
    for index, scene in enumerate(storyboard):
        scene_id = str(scene.get("scene") or index + 1)
        text = scene.get("subtitle_text") or scene.get("lyric_part") or ""
        for line in _lines(text):
            score = _hook_score(line, scene, scene_scores.get(scene_id, {}))
            candidates.append(
                {
                    "scene_id": scene_id,
                    "text": line,
                    "hook_score": score,
                    "subtitle_emphasis": _emphasis(line, score),
                    "shorts_ready": score >= 70,
                    "recommended_motion": "hook_energy_zoom" if score >= 75 else "emotional_push_in",
                    "recommended_subtitle": "tiktok_bold" if score >= 70 else "cinematic",
                }
            )
    candidates = sorted(candidates, key=lambda item: item["hook_score"], reverse=True)[: max(1, int(limit or 8))]
    return {"ok": True, "message": "Hook intelligence analyzed offline", "data": {"candidates": candidates}, "error": ""}


def _lines(text: str) -> List[str]:
    parts = [part.strip() for part in re.split(r"[\n\r]+|[.!?]", str(text or "")) if part.strip()]
    return parts or ([str(text).strip()] if str(text).strip() else [])


def _hook_score(line: str, scene: Dict[str, Any], score: Dict[str, Any]) -> int:
    text = " ".join([line, str(scene.get("emotion", "")), str(scene.get("pacing_note", "")), str(scene.get("section", ""))]).lower()
    value = 25 + min(25, len(line.strip()) // 3)
    value += 18 if any(word in text for word in ["hook", "chorus", "final chorus", "drop"]) else 0
    value += 12 if any(word in text for word in ["รัก", "คิดถึง", "เจ็บ", "เหงา", "ใจ", "คืน"]) else 0
    value += 12 if any(word in text for word in ["love", "miss", "heart", "lonely", "cry", "viral"]) else 0
    value += int(score.get("hook_potential", 0) * 0.25)
    return max(0, min(100, value))


def _emphasis(line: str, score: int) -> str:
    if score >= 80:
        return "bold center punch-in"
    if len(line) > 70:
        return "split into two subtitle beats"
    if score >= 65:
        return "highlight final phrase"
    return "soft bottom subtitle"


HOOK_STYLES = ["Curiosity", "Drama", "Shock", "Funny", "Relationship", "Dark humor", "Affiliate sell", "Storytelling"]


def analyze_opening_hook(idea: str, *, hook_style: str = "Curiosity", preset: dict[str, Any] | None = None, character_profile: dict[str, Any] | None = None) -> Dict[str, Any]:
    text = " ".join(str(idea or "").split()).strip() or "หยุดดูคลิปนี้ก่อน"
    style = hook_style if hook_style in HOOK_STYLES else "Curiosity"
    preset = preset or {}
    character_name = str((character_profile or {}).get("name") or "").strip()
    style_prefix = {
        "Curiosity": "เดี๋ยวก่อน เรื่องนี้แปลกกว่าที่คิด",
        "Drama": "ไม่มีใครเตรียมใจเจอเรื่องนี้",
        "Shock": "อันนี้แรง แต่จริงมาก",
        "Funny": "ขอพูดแบบไม่อ้อม",
        "Relationship": "ถ้าหัวใจพูดได้ มันคงพูดแบบนี้",
        "Dark humor": "ชีวิตมันตลกร้ายตรงนี้แหละ",
        "Affiliate sell": "ถ้ายังเจอปัญหานี้ ต้องดูอันนี้",
        "Storytelling": "เรื่องมันเริ่มจากประโยคเดียว",
    }[style]
    opening_line = f"{character_name + ': ' if character_name else ''}{style_prefix}"
    shock_line = text[:90]
    emotional_intensity = _score_keywords(text, ["เจ็บ", "เหงา", "ร้องไห้", "รัก", "โดนเท", "toxic", "sad", "heart"]) + (15 if style in {"Drama", "Relationship"} else 0)
    curiosity = _score_keywords(text, ["ทำไม", "อะไร", "จริง", "ลับ", "แปลก", "why", "secret"]) + (25 if style in {"Curiosity", "Shock"} else 0)
    meme_potential = _score_keywords(text, ["แมว", "กล้วย", "หัวใจ", "สมอง", "ไข่ดาว", "รีวิว", "บ่น", "meme"]) + (20 if style in {"Funny", "Dark humor"} else 0)
    pacing = 85 if preset.get("pace") in {"fast", "fun"} else 60 if preset.get("pace") == "medium" else 45
    subtitle_density = 80 if style in {"Shock", "Funny", "Affiliate sell"} else 65
    hook_score = max(0, min(100, int((emotional_intensity + curiosity + meme_potential + pacing + subtitle_density) / 5 + 25)))
    data = {
        "generated_by": "VelaFlow",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "hook_style": style,
        "opening_line": opening_line,
        "shock_line": shock_line,
        "emotion_trigger": _emotion_trigger(text, style),
        "subtitle_emphasis": _emphasis(shock_line or opening_line, hook_score),
        "camera_direction": "fast punch-in close-up" if hook_score >= 75 else "medium close-up push-in",
        "zoom_recommendation": "shake zoom in first second" if preset.get("motion_style") in {"shake_zoom", "bounce"} else "slow push-in",
        "hook_pacing": "0-1s face reveal, 1-3s punch line, 3s subtitle emphasis",
        "hook_score": hook_score,
        "scores": {
            "emotional_intensity": max(0, min(100, emotional_intensity)),
            "curiosity": max(0, min(100, curiosity)),
            "pacing": max(0, min(100, pacing)),
            "subtitle_density": max(0, min(100, subtitle_density)),
            "meme_potential": max(0, min(100, meme_potential)),
        },
    }
    return {"ok": True, "message": "Opening hook analyzed", "data": data, "error": ""}


def save_hook_analysis(project_name: str, analysis: dict[str, Any], export_dir: str | Path) -> dict[str, Any]:
    try:
        path = Path(export_dir) / "hook_analysis.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "message": "Hook analysis saved", "data": {"path": str(path)}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Hook analysis save failed", "data": {}, "error": str(exc)}


def _score_keywords(text: str, keywords: list[str]) -> int:
    lowered = text.lower()
    return min(100, 35 + sum(12 for word in keywords if word.lower() in lowered))


def _emotion_trigger(text: str, style: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ["โดนเท", "แฟนเก่า", "อกหัก", "heart"]):
        return "relationship pain"
    if any(word in lowered for word in ["ขาย", "รีวิว", "สินค้า", "shop"]):
        return "problem-solution buying moment"
    if style in {"Funny", "Dark humor"}:
        return "relatable meme frustration"
    return "curiosity and emotional recognition"
