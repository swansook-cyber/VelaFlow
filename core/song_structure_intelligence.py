from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.artist_presets import get_artist_preset
from core.project_io import safe_name
from core.paths import resolve_project_folder, workflow_project_root


ROOT = Path(__file__).resolve().parents[1]
PRESET_PATH = ROOT / "config" / "presets" / "song_structure_presets.json"
PROJECT_ROOT = workflow_project_root("music_pipeline")
DEFAULT_PRESET_ID = "vela_moon_pop_rock"


def _result(ok: bool, message: str, data: Dict[str, Any] | None = None, error: str = "") -> Dict[str, Any]:
    return {"ok": ok, "message": message, "data": data or {}, "error": error}


def load_structure_presets() -> Dict[str, Dict[str, Any]]:
    try:
        data = json.loads(PRESET_PATH.read_text(encoding="utf-8"))
        return {str(key): value for key, value in data.items() if isinstance(value, dict)}
    except Exception:
        return {}


def list_structure_presets() -> List[Dict[str, Any]]:
    return sorted(load_structure_presets().values(), key=lambda item: item.get("name", ""))


def get_structure_preset(preset_id: str | None = None) -> Dict[str, Any]:
    presets = load_structure_presets()
    return presets.get(preset_id or DEFAULT_PRESET_ID) or presets.get(DEFAULT_PRESET_ID) or next(iter(presets.values()), {})


def _context_value(context: Dict[str, Any], key: str, fallback: str = "") -> str:
    value = context.get(key, fallback)
    return str(value or fallback)


def create_structure_plan(project_context: Dict[str, Any] | None = None, preset_id: str | None = None, artist_preset: Dict[str, Any] | None = None) -> Dict[str, Any]:
    context = project_context or {}
    preset = get_structure_preset(preset_id or context.get("structure_preset"))
    artist = artist_preset or get_artist_preset(context.get("artist_preset", "vela_moon"))
    sections = [dict(item) for item in preset.get("sections", []) or []]
    energy_curve = [{"section": item.get("section", ""), "energy": int(item.get("energy", 0))} for item in sections]
    emotional_arc = " -> ".join([item.get("emotion", "") for item in sections if item.get("emotion")])
    section_order = [item.get("section", "") for item in sections]
    hook_placement = preset.get("recommended_hook_placement", "Chorus and Final Chorus")
    selected_hook = context.get("selected_hook") or {}
    selected_hook_text = selected_hook.get("hook_text", "") if isinstance(selected_hook, dict) else str(selected_hook or "")
    return {
        "preset_id": preset.get("preset_id", preset_id or DEFAULT_PRESET_ID),
        "preset_name": preset.get("name", "Vela Moon Pop Rock"),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "topic": _context_value(context, "topic"),
        "mood": _context_value(context, "mood"),
        "genre": _context_value(context, "genre") or _context_value(context, "music_direction"),
        "artist_preset": artist.get("artist_id", "vela_moon"),
        "target_platform": _context_value(context, "target_platform", "Full Pipeline"),
        "selected_hook": selected_hook_text,
        "recommended_hook_placement": hook_placement,
        "recommended_section_order": section_order,
        "sections": sections,
        "energy_curve": energy_curve,
        "emotional_arc": emotional_arc,
        "notes_for_lyrics_generation": (
            f"Follow section order: {', '.join(section_order)}. "
            f"Place the selected hook around {hook_placement}. "
            "Thai lyrics must remain natural; production tags inside parentheses must stay English only."
        ),
        "notes_for_mv_director": (
            "Use energy curve to pace cuts and motion. Softer sections need quieter visuals; "
            "chorus and final chorus need stronger motion, clearer subtitle emphasis, and more emotional close-ups."
        ),
    }


def validate_structure_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    sections = plan.get("sections", [])
    if not sections:
        errors.append("sections missing")
    for index, item in enumerate(sections):
        energy = item.get("energy")
        try:
            energy_int = int(energy)
        except (TypeError, ValueError):
            errors.append(f"section {index + 1} energy invalid")
            continue
        if not 0 <= energy_int <= 100:
            errors.append(f"section {index + 1} energy out of range")
        if not item.get("section"):
            errors.append(f"section {index + 1} name missing")
    if not plan.get("notes_for_lyrics_generation"):
        errors.append("notes_for_lyrics_generation missing")
    return _result(not errors, "valid" if not errors else "structure plan validation failed", {"errors": errors}, "" if not errors else "invalid_structure_plan")


def _project_folder(project_name: str, base_dir: str | Path | None = None) -> Path:
    if base_dir:
        return Path(base_dir) / safe_name(project_name or "project")
    return resolve_project_folder(project_name or "project", "music_pipeline")


def save_structure_plan(project_name: str, plan: Dict[str, Any], base_dir: str | Path | None = None) -> Dict[str, Any]:
    validation = validate_structure_plan(plan)
    if not validation.get("ok"):
        return _result(False, "Invalid structure plan", validation.get("data", {}), "invalid_structure_plan")
    try:
        folder = _project_folder(project_name, base_dir)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "song_structure_plan.json"
        path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        return _result(True, "Song structure plan saved", {"path": str(path), "folder": str(folder), "plan": plan})
    except Exception as exc:
        return _result(False, "Save structure plan failed", {}, str(exc))


def load_structure_plan(project_name: str, base_dir: str | Path | None = None) -> Dict[str, Any]:
    try:
        path = _project_folder(project_name, base_dir) / "song_structure_plan.json"
        if not path.exists():
            return _result(False, "Song structure plan not found", {"path": str(path)}, "missing_song_structure_plan")
        plan = json.loads(path.read_text(encoding="utf-8"))
        return _result(True, "Song structure plan loaded", {"path": str(path), "plan": plan})
    except Exception as exc:
        return _result(False, "Load structure plan failed", {}, str(exc))


def structure_plan_markdown(plan: Dict[str, Any]) -> str:
    lines = [
        "# Song Structure Plan",
        "",
        f"Preset: {plan.get('preset_name', '')}",
        f"Emotional Arc: {plan.get('emotional_arc', '')}",
        f"Hook Placement: {plan.get('recommended_hook_placement', '')}",
        "",
        "| Section | Energy | Purpose | Emotion | Hook Role | Lyric Density | Arrangement | Suggested Tag |",
        "|---|---:|---|---|---|---|---|---|",
    ]
    for item in plan.get("sections", []) or []:
        lines.append(
            f"| {item.get('section','')} | {item.get('energy','')} | {item.get('purpose','')} | "
            f"{item.get('emotion','')} | {item.get('hook_role','')} | {item.get('lyric_density','')} | "
            f"{item.get('arrangement_density','')} | {item.get('suggested_tag','')} |"
        )
    lines += ["", "## Notes For Lyrics", "", plan.get("notes_for_lyrics_generation", ""), "", "## Notes For MV Director", "", plan.get("notes_for_mv_director", "")]
    return "\n".join(lines)


def structure_plan_prompt(plan: Dict[str, Any]) -> str:
    if not plan:
        return ""
    section_lines = []
    energy_curve = ", ".join(
        f"{item.get('section')} {item.get('energy')}"
        for item in plan.get("energy_curve", []) or []
    )
    for item in plan.get("sections", []) or []:
        section_lines.append(
            f"- {item.get('section','')}: purpose={item.get('purpose','')}, energy={item.get('energy','')}, "
            f"emotion={item.get('emotion','')}, hook_role={item.get('hook_role','')}, "
            f"tag=({item.get('suggested_tag','')})"
        )
    return (
        "\n\nSong Structure Intelligence:\n"
        f"- Preset: {plan.get('preset_name', '')}\n"
        f"- Hook Placement: {plan.get('recommended_hook_placement', '')}\n"
        f"- Emotional Arc: {plan.get('emotional_arc', '')}\n"
        f"- Energy Curve: {energy_curve}\n"
        "- Sections:\n"
        + "\n".join(section_lines)
        + f"\n- Lyrics Notes: {plan.get('notes_for_lyrics_generation', '')}\n"
    )


def export_structure_plan_files(project_name: str, plan: Dict[str, Any], base_dir: str | Path | None = None) -> Dict[str, Any]:
    validation = validate_structure_plan(plan)
    if not validation.get("ok"):
        return _result(False, "Invalid structure plan", validation.get("data", {}), "invalid_structure_plan")
    try:
        folder = _project_folder(project_name, base_dir) / "exports"
        folder.mkdir(parents=True, exist_ok=True)
        json_path = folder / "song_structure_plan.json"
        md_path = folder / "song_structure_plan.md"
        json_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        md_path.write_text(structure_plan_markdown(plan), encoding="utf-8")
        return _result(True, "Song structure exports created", {"json": str(json_path), "markdown": str(md_path)})
    except Exception as exc:
        return _result(False, "Export structure plan failed", {}, str(exc))
