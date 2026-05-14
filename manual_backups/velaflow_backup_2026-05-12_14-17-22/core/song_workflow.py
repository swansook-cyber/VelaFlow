from __future__ import annotations

import json
import random
import re
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Iterable, List

from core.artist_presets import get_artist_preset
from core.instrument_tag_normalizer import normalize_lyrics_tags, validate_english_only_tags
from core.project_io import safe_name
from core.suno_export import export_suno_files
from providers.provider_manager import generate_text


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT / "project_data" / "projects"
USAGE_OPTIONS = ["chorus", "post-chorus", "TikTok clip", "title line"]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _project_folder(project_name: str, base_dir: str | Path | None = None) -> Path:
    root = Path(base_dir) if base_dir else PROJECT_ROOT
    return root / safe_name(project_name or "project")


def _hook_text(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("hook_text") or value.get("text") or value.get("hook") or "").strip()
    return str(value or "").strip()


def _score_hook(text: str, index: int = 0) -> Dict[str, int]:
    clean = re.sub(r"\s+", "", text or "")
    length = len(clean)
    short_bonus = 16 if 5 <= length <= 16 else 8 if length <= 24 else 0
    repeat_bonus = 7 if any(clean.count(ch) > 1 for ch in clean) else 0
    emotional_words = ["ใจ", "คิดถึง", "พอ", "กลับ", "เจ็บ", "รัก", "เหงา", "ฝน", "คืน", "ลืม"]
    emotion_bonus = sum(5 for word in emotional_words if word in text)
    base = max(62, 88 - index * 3)
    return {
        "emotional_score": min(100, base + emotion_bonus),
        "catchy_score": min(100, base + short_bonus + repeat_bonus),
        "tiktok_potential": min(100, base + short_bonus + (8 if length <= 14 else 0)),
    }


def _normalize_hook(value: Any, index: int = 0) -> Dict[str, Any]:
    text = _hook_text(value) or f"ยังคิดถึงเธออยู่ดี {index + 1}"
    scores = _score_hook(text, index)
    if isinstance(value, dict):
        scores["emotional_score"] = int(value.get("emotional_score") or value.get("emotional") or scores["emotional_score"])
        scores["catchy_score"] = int(value.get("catchy_score") or value.get("catchy") or scores["catchy_score"])
        scores["tiktok_potential"] = int(value.get("tiktok_potential") or value.get("tiktok") or scores["tiktok_potential"])
        reason = value.get("reason_th") or value.get("reason") or "สั้น จำง่าย และเหมาะกับท่อนฮุก"
        usage = value.get("suggested_usage") or USAGE_OPTIONS[index % len(USAGE_OPTIONS)]
        name = value.get("name") or f"Hook {chr(65 + index)}"
    else:
        reason = "สั้น จำง่าย และเหมาะกับท่อนฮุก"
        usage = USAGE_OPTIONS[index % len(USAGE_OPTIONS)]
        name = f"Hook {chr(65 + index)}"
    return {
        "name": name,
        "hook_text": text,
        "emotional_score": max(0, min(100, scores["emotional_score"])),
        "catchy_score": max(0, min(100, scores["catchy_score"])),
        "tiktok_potential": max(0, min(100, scores["tiktok_potential"])),
        "reason_th": reason,
        "suggested_usage": usage if usage in USAGE_OPTIONS else "chorus",
    }


def normalize_hook_candidates(values: Iterable[Any] | None) -> List[Dict[str, Any]]:
    hooks = [_normalize_hook(value, index) for index, value in enumerate(values or []) if _hook_text(value)]
    unique: List[Dict[str, Any]] = []
    seen = set()
    for hook in hooks:
        key = hook["hook_text"]
        if key not in seen:
            unique.append(hook)
            seen.add(key)
    return unique[:5]


def generate_hook_candidates(idea: str = "", artist_preset: Dict[str, Any] | None = None, seed: str | None = None) -> List[Dict[str, Any]]:
    preset = artist_preset or get_artist_preset("vela_moon")
    seed_value = f"{idea or ''}|{seed or datetime.now().isoformat()}|{random.randint(1000, 999999)}"
    rng = random.Random(seed_value)
    hooks = [
        "พอได้แล้วใจ",
        "ยังคิดถึงเธออยู่ดี",
        "ฝนตกในใจฉัน",
        "กลับมาไม่ได้ ก็ไม่เป็นไร",
        "รักที่เหลือคือความเงียบ",
        "ลืมเธอไม่เก่งเลย",
        "เจ็บเบา ๆ แต่ลืมไม่ลง",
        "คืนที่ไม่มีเธอมันยาวเกินไป",
        "อย่าทำให้ใจต้องรอ",
        "คิดถึงจนไม่รู้จะหยุดยังไง",
    ]
    idea_text = (idea or "").strip()
    if "ฝน" in idea_text:
        hooks += ["เปียกทั้งใจเพราะคิดถึงเธอ", "คืนฝนพรำยังมีเธอ", "ฝนหยุดแล้ว ใจยังไม่หยุด"]
    if "ลืม" in idea_text:
        hooks += ["ยิ่งลืมยิ่งจำ", "บอกใจให้ลืมแต่ใจไม่ฟัง"]
    if "กลับ" in idea_text:
        hooks += ["ยังรอที่เดิม", "ถ้ากลับมา ฉันยังอยู่", "กลับมาไม่ได้ ก็ขอให้โชคดี"]
    if preset.get("artist_id") == "vela_moon":
        hooks += ["ยิ้มได้ แต่ไม่ได้แปลว่าลืม", "ใจยังอยู่ที่เพลงเดิม"]
    rng.shuffle(hooks)
    return normalize_hook_candidates(hooks[:5])


def _extract_json(text: str) -> Any:
    match = re.search(r"(\[.*\]|\{.*\})", text or "", re.DOTALL)
    if not match:
        raise ValueError("No JSON found")
    data = json.loads(match.group(1))
    if isinstance(data, dict):
        return data.get("hooks") or data.get("hook_candidates") or data.get("candidate_hooks") or []
    return data


def generate_hook_candidates_with_provider(
    *,
    api_key: str = "",
    model_name: str = "",
    idea: str = "",
    genre: str = "",
    mood: str = "",
    artist_preset: Dict[str, Any] | None = None,
    seed: str | None = None,
) -> Dict[str, Any]:
    preset = artist_preset or get_artist_preset("vela_moon")
    seed_value = seed or f"{datetime.now().isoformat()}-{random.randint(10000, 999999)}"
    if not api_key:
        return {"ok": True, "message": "Using offline fallback hooks", "data": {"hooks": generate_hook_candidates(idea, preset, seed_value), "offline": True, "seed": seed_value}, "error": ""}
    prompt = f"""
Generate 5 fresh Thai hook candidates for a Suno song.
Return JSON only as an array of objects with keys:
name, hook_text, emotional_score, catchy_score, tiktok_potential, reason_th, suggested_usage.

Rules:
- Thai hook text only.
- Make hooks different from generic examples and from each other.
- Short, singable, caption-friendly.
- suggested_usage must be one of: chorus, post-chorus, TikTok clip, title line.
- Scores are 0-100.

User theme: {idea}
Mood: {mood}
Genre: {genre}
Artist preset: {preset.get('artist_name', 'Vela Moon')}
Brand style: {preset.get('brand_style', '')}
Random seed / timestamp: {seed_value}
"""
    fallback_text = json.dumps(generate_hook_candidates(idea, preset, seed_value), ensure_ascii=False)
    text = generate_text(
        provider="gemini",
        api_key=api_key,
        prompt=prompt,
        primary_model=model_name,
        offline_factory=lambda: fallback_text,
    )
    hooks = normalize_hook_candidates(_extract_json(text))
    offline = text == fallback_text
    return {"ok": True, "message": "Using offline fallback hooks" if offline else "Hook candidates generated", "data": {"hooks": hooks, "offline": offline, "seed": seed_value}, "error": ""}


def select_best_hook(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not candidates:
        candidates = generate_hook_candidates()
    return max(
        candidates,
        key=lambda hook: int(hook.get("emotional_score", 0)) + int(hook.get("catchy_score", 0)) + int(hook.get("tiktok_potential", 0)),
    )


def normalize_song_metadata(song: Dict[str, Any], artist_preset: Dict[str, Any] | None = None) -> Dict[str, Any]:
    preset = artist_preset or get_artist_preset(song.get("artist_preset", "vela_moon"))
    normalized = dict(song or {})
    hooks = normalize_hook_candidates(normalized.get("hook_candidates") or normalized.get("candidate_hooks"))
    if not hooks and normalized.get("selected_hook"):
        hooks = normalize_hook_candidates([normalized.get("selected_hook")])
    normalized["hook_candidates"] = hooks
    normalized["candidate_hooks"] = hooks
    selected = normalized.get("selected_hook")
    selected_text = _hook_text(selected)
    if selected_text:
        selected_obj = next((hook for hook in hooks if hook["hook_text"] == selected_text), _normalize_hook(selected, 0))
    else:
        selected_obj = select_best_hook(hooks) if hooks else {}
    normalized["selected_hook"] = selected_obj
    normalized["selected_hook_text"] = selected_obj.get("hook_text", "") if selected_obj else ""
    normalized.setdefault("artist_preset", preset.get("artist_id", "vela_moon"))
    normalized.setdefault("artist_preset_data", preset)
    normalized.setdefault("music_style_prompt", preset.get("default_music_style_prompt", ""))
    settings = preset.get("suno_advanced_settings") or {}
    normalized.setdefault("advanced_settings", settings)
    normalized["weirdness"] = normalized.get("weirdness") or settings.get("weirdness", "")
    normalized["style_influence"] = normalized.get("style_influence") or settings.get("style_influence", "")
    normalized["instrument_tags_language"] = "English only"
    lyrics = normalized.get("normalized_song_output") or normalized.get("complete_lyrics") or ""
    fixed = normalize_lyrics_tags(lyrics, preset)
    normalized["normalized_song_output"] = fixed
    normalized["complete_lyrics"] = fixed
    normalized["instrument_tag_validation"] = validate_english_only_tags(fixed)
    return normalized


def save_song_state(project_name: str, song: Dict[str, Any], base_dir: str | Path | None = None, create_draft: bool = False, workflow_mode: str = "Full Pipeline") -> Dict[str, Any]:
    try:
        folder = _project_folder(project_name, base_dir)
        folder.mkdir(parents=True, exist_ok=True)
        normalized = normalize_song_metadata(song)
        normalized["saved_at"] = _now()
        (folder / "song.json").write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
        (folder / "lyrics.txt").write_text(normalized.get("normalized_song_output", ""), encoding="utf-8")
        normalized["workflow_mode"] = workflow_mode
        suno_export = export_suno_files(project_name, normalized, base_dir, workflow_mode=workflow_mode)
        draft_path = ""
        if create_draft:
            drafts = folder / "song_drafts"
            drafts.mkdir(parents=True, exist_ok=True)
            draft = drafts / f"song_draft_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            draft.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
            draft_path = str(draft)
        return {"ok": True, "message": "Lyrics saved", "data": {"song": normalized, "folder": str(folder), "draft_path": draft_path, "suno_export": suno_export.get("data", {})}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Save lyrics failed", "data": {}, "error": str(exc)}


def load_saved_song(project_name: str, base_dir: str | Path | None = None) -> Dict[str, Any]:
    try:
        path = _project_folder(project_name, base_dir) / "song.json"
        if not path.exists():
            return {"ok": False, "message": "No saved song found", "data": {}, "error": "missing song.json"}
        song = json.loads(path.read_text(encoding="utf-8"))
        return {"ok": True, "message": "Song loaded", "data": {"song": normalize_song_metadata(song), "path": str(path)}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Load saved song failed", "data": {}, "error": str(exc)}


def list_song_drafts(project_name: str, base_dir: str | Path | None = None, limit: int = 8) -> List[Dict[str, Any]]:
    drafts = _project_folder(project_name, base_dir) / "song_drafts"
    if not drafts.exists():
        return []
    rows = []
    for path in sorted(drafts.glob("song_draft_*.json"), key=lambda item: item.stat().st_mtime, reverse=True)[:limit]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        rows.append({
            "name": path.name,
            "path": str(path),
            "saved_at": data.get("saved_at", datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")),
            "selected_hook": _hook_text(data.get("selected_hook")) or data.get("selected_hook_text", ""),
        })
    return rows


def load_song_draft(path: str | Path) -> Dict[str, Any]:
    try:
        source = Path(path)
        song = json.loads(source.read_text(encoding="utf-8"))
        return {"ok": True, "message": "Draft loaded", "data": {"song": normalize_song_metadata(song), "path": str(source)}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Load draft failed", "data": {}, "error": str(exc)}


def compare_song_to_draft(current_song: Dict[str, Any], draft_song: Dict[str, Any]) -> Dict[str, Any]:
    current = normalize_song_metadata(current_song or {})
    draft = normalize_song_metadata(draft_song or {})
    current_lyrics = current.get("normalized_song_output", "")
    draft_lyrics = draft.get("normalized_song_output", "")
    ratio = SequenceMatcher(None, current_lyrics, draft_lyrics).ratio() if current_lyrics or draft_lyrics else 1.0
    rows = [
        {"field": "Selected hook", "current": current.get("selected_hook_text", ""), "draft": draft.get("selected_hook_text", "")},
        {"field": "Music style prompt", "current": current.get("music_style_prompt", "")[:120], "draft": draft.get("music_style_prompt", "")[:120]},
        {"field": "Lyrics similarity", "current": f"{ratio:.0%}", "draft": f"{ratio:.0%}"},
    ]
    return {"ok": True, "message": "Draft compared", "data": {"rows": rows, "similarity": ratio}, "error": ""}
