from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from core.artist_presets import (
    DEFAULT_ARTIST_ID,
    delete_artist_preset,
    duplicate_artist_preset,
    export_artist_preset,
    get_artist_preset,
    import_artist_preset,
    is_locked_artist_preset,
    list_artist_presets,
    load_default_artist_id,
    save_artist_preset,
    set_default_artist_preset,
)
from core.asset_manager import clear_image_cache, clear_rejected_images, clear_temp_renders, project_asset_summary
from core.beta_testing import (
    BETA_RATING_AREAS,
    add_beta_issue,
    beta_test_checklist,
    compare_render_versions,
    export_beta_report,
    list_beta_sessions,
    load_beta_session,
    mark_stable_candidate,
    new_beta_session,
    update_beta_ratings,
)
from core.branding import APP_TITLE, BRAND_NAME, DEFAULT_ARTIST, PRODUCT_TAGLINE, WINDOW_TITLE
from core.character_consistency import apply_character_to_storyboard, build_character_prompt, normalize_character
from core.clip_factory import CLIP_TYPES, generate_clip, generate_clip_set
from core.common_fixes import fix_common_issues
from core.creator_wizard import (
    MOOD_OPTIONS,
    MUSIC_DIRECTION_OPTIONS,
    TARGET_PLATFORM_OPTIONS,
    TOPIC_OPTIONS,
    creative_direction_prompt,
    generate_creative_direction,
    save_creative_direction,
    suggest_project_name,
)
from core.creative_suggestions import build_creative_suggestions
from core.emotional_arc import analyze_emotional_arc
from core.exporter import export_package
from core.final_package import build_final_release_package, inspect_final_package_inputs
from core.healthcheck import run_healthcheck, run_pre_render_healthcheck
from core.hook_intelligence import analyze_hooks
from core.instrument_tag_normalizer import normalize_lyrics_tags, validate_english_only_tags
from core.job_queue import cancel_job, clear_finished_jobs, list_jobs, submit_job
from core.licensing import get_license_service
from core.marketing_package import build_marketing_package, export_marketing_package
from core.mv_storyboard_generator import export_mv_storyboard, generate_mv_storyboard
from core.navigation_config import (
    FULL_MENU_GROUPS,
    PAGE_LABELS,
    SONG_ONLY_ALLOWED_PAGES,
    SONG_ONLY_MENU_GROUPS,
    SELLER_STUDIO_ALLOWED_PAGES,
    flatten_pages,
    menu_groups_for_mode,
    normalize_navigation_state,
    page_label,
)
from core.preset_system import list_project_templates
from core.project_io import load_project, new_project, safe_name, save_project, save_project_folder
from core.project_lock import acquire_project_lock, project_lock_status, release_project_lock
from core.project_manager import (
    archive_project,
    create_project as create_managed_project,
    delete_project,
    get_project_summary,
    list_archived_projects,
    list_projects as list_managed_projects,
    load_user_preferences,
    rename_project,
    save_user_preferences,
    session_label_for_mode,
    workflow_type_for_mode,
)
from core.project_templates import apply_template_to_project, create_project_from_template
from core.project_workflow import backup_project, build_project_status, clean_safe_temp_files, duplicate_project, export_project_report, list_recent_projects
from core.production_audit import export_project_audit, run_full_project_audit
from core.render_engine import run_render
from core.render_profiles import RENDER_PROFILES
from core.render_recovery import export_diagnostic_bundle, latest_failed_render, recover_render_temp
from core.safe_mode import open_project_safe_mode
from core.scene_scoring import score_project_scenes, smart_tiktok_recommendations
from core.seller_content import TONE_GUIDES, build_seller_dashboard_status, export_seller_content, generate_seller_content, seller_content_to_text
from core.settings import get_settings
from core.stable_build import STABLE_FREEZE_NAME, create_stable_candidate_snapshot
from core.song_workflow import (
    compare_song_to_draft,
    generate_hook_candidates,
    generate_hook_candidates_with_provider,
    list_song_drafts,
    load_saved_song,
    load_song_draft,
    normalize_hook_candidates,
    normalize_song_metadata,
    save_song_state,
    select_best_hook,
)
from core.song_structure_intelligence import (
    create_structure_plan,
    export_structure_plan_files,
    get_structure_preset,
    list_structure_presets,
    save_structure_plan,
    structure_plan_prompt,
    validate_structure_plan,
)
from core.suno_export import export_suno_files, resolve_export_txt_filename
from core.theme import active_theme_name
from core.ui_styles import apply_global_styles
from core.version import APP_VERSION, BUILD_VERSION, build_label
from providers.image_ai import generate_image
from providers.text_ai import analyze_song_with_gemini, generate_song_with_gemini
from providers.video_ai import generate_video
from app.presets import (
    DEFAULT_MUSIC_PRESET,
    DEFAULT_VOCAL_DIRECTION,
    get_music_preset,
    get_recommended_ai_controls,
    get_vocal_direction,
    list_music_preset_names,
    list_vocal_direction_names,
    music_preset_prompt,
    vocal_direction_prompt,
)


st.set_page_config(page_title=WINDOW_TITLE, page_icon="🎬", layout="wide")
apply_global_styles()
settings = get_settings()
license_service = get_license_service()


DISPLAY_TEXT_FIXES = {
    "เน€เธเธฅเธเนเธซเธกเนเธเธญเธเธเธฑเธ": "เพลงใหม่ของฉัน",
}

WORKFLOW_DEFAULT_NAMES = {
    "Song Studio Only": "เพลงใหม่ของฉัน",
    "Full Pipeline": "โปรเจกต์เพลงใหม่",
    "Seller Studio (Beta)": "แคมเปญใหม่ของฉัน",
    "Podcast Studio": "ตอนใหม่ของฉัน",
    "MV Workflow": "MV Project ใหม่",
}

SONG_DEFAULT_TITLES = {"", "เพลงใหม่ของฉัน", "โปรเจกต์เพลงใหม่"}


def _workflow_default_name(workflow_mode: str | None = None) -> str:
    mode = workflow_mode or st.session_state.get("workflow_mode", "Full Pipeline")
    return WORKFLOW_DEFAULT_NAMES.get(mode, "โปรเจกต์ใหม่")


def _seller_campaign_name(project_context: dict[str, Any]) -> str:
    title = _fix_display_text(project_context.get("title", "")).strip()
    return "New Seller Campaign" if title in SONG_DEFAULT_TITLES else title


def _save_seller_product_image(project_context: dict[str, Any], uploaded_file: Any) -> dict[str, Any]:
    if not uploaded_file:
        return {}
    project_name = safe_name(project_context.get("title") or _workflow_default_name("Seller Studio (Beta)"))
    image_dir = ROOT / "project_data" / "projects" / project_name / "seller_assets"
    image_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(uploaded_file.name).suffix.lower() or ".png"
    filename = f"product_image{suffix}"
    path = image_dir / filename
    path.write_bytes(uploaded_file.getvalue())
    return {
        "path": str(path),
        "filename": filename,
        "original_filename": uploaded_file.name,
        "content_type": getattr(uploaded_file, "type", ""),
        "uploaded_at": datetime.now().isoformat(timespec="seconds"),
    }


def _fix_display_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    fixed = value
    for bad, good in DISPLAY_TEXT_FIXES.items():
        fixed = fixed.replace(bad, good)
    return fixed


def _ensure_state() -> None:
    workflow_mode = load_user_preferences().get("workflow_mode", "Full Pipeline")
    defaults = {
        "project": new_project(_workflow_default_name(workflow_mode), DEFAULT_ARTIST, workflow_type_for_mode(workflow_mode)),
        "current_project": "",
        "selected_section": "START",
        "selected_page": "Dashboard",
        "selected_artist_preset": load_default_artist_id(),
        "render_profile": "Standard",
        "storyboard": [],
        "generated_song": {},
        "hook_candidates": [],
        "selected_hook": {},
        "normalized_song_output": "",
        "lyrics_saved": False,
        "workflow_mode": workflow_mode,
        "queue_state": {},
        "job_state": {},
        "audit_state": {},
        "beta_test_state": {},
        "active_template": "",
        "active_preset_pack": "",
        "creative_direction": {},
        "wizard_topic": "",
        "wizard_mood": "",
        "wizard_music_direction": "",
        "wizard_target_platform": "",
        "song_structure_plan": {},
        "use_structure_plan_for_lyrics": True,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
    project = st.session_state.project
    project["title"] = _fix_display_text(project.get("title", _workflow_default_name()))
    project["artist"] = _fix_display_text(project.get("artist", DEFAULT_ARTIST))
    project.setdefault("workflow_type", workflow_type_for_mode(st.session_state.get("workflow_mode", "Full Pipeline")))
    project.setdefault("project_type", project.get("workflow_type"))
    project.setdefault("song", {})
    project.setdefault("mv", {})
    project.setdefault("assets", {})
    project["assets"].setdefault("approved_images", {})
    project["assets"].setdefault("rejected_images", {})
    project["assets"].setdefault("images", {})
    project["assets"].setdefault("videos", {})
    project["character"] = normalize_character(project.get("character", {}) or {})


def _safe(label: str, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    try:
        return func(*args, **kwargs)
    except Exception as exc:
        st.error(f"{label} failed: {exc}")
        return {"ok": False, "message": label, "data": {}, "error": str(exc)}


def _project() -> dict[str, Any]:
    return st.session_state.project


def _current_lyrics() -> str:
    song = _project().get("song", {}) or {}
    return song.get("normalized_song_output") or song.get("complete_lyrics") or st.session_state.get("manual_lyrics", "")


def _latest_render_dir(project: dict[str, Any]) -> Path:
    root = ROOT / "outputs" / "renders" / safe_name(project.get("title", "project"))
    dirs = sorted([path for path in root.glob("*") if path.is_dir()], key=lambda path: path.stat().st_mtime, reverse=True) if root.exists() else []
    return dirs[0] if dirs else root


def _save_project() -> None:
    save_project_folder(_project(), str(ROOT / "project_data" / "projects"))


def _load_managed_project(path: str) -> dict[str, Any]:
    folder = Path(path)
    project_path = folder / "project.json"
    if project_path.is_file():
        return load_project(str(project_path))
    return new_project(folder.name.replace("_", " "), DEFAULT_ARTIST)


def _page_header(title: str, subtitle: str = "", project_context: dict[str, Any] | None = None) -> None:
    st.subheader(title)
    if subtitle:
        st.caption(subtitle)
    if project_context is not None:
        st.caption(f"Current project: {project_context.get('title', 'project')}")


def _continue_to_mv_director() -> None:
    if st.session_state.get("workflow_mode") == "Song Studio Only":
        st.session_state.workflow_mode = "Full Pipeline"
        save_user_preferences({"workflow_mode": "Full Pipeline"})
    st.session_state["pending_navigation"] = {"section": "VISUAL", "page": "MV Director"}
    st.rerun()


def _direction_for_song_idea(base_idea: str, direction: dict[str, Any]) -> str:
    return f"{base_idea or ''}{creative_direction_prompt(direction)}".strip()


def _structure_for_song_idea(base_idea: str, structure_plan: dict[str, Any], enabled: bool = True) -> str:
    if not enabled:
        return base_idea or ""
    return f"{base_idea or ''}{structure_plan_prompt(structure_plan)}".strip()


def _music_preset_for_song_idea(base_idea: str, music_preset: dict[str, str]) -> str:
    return f"{base_idea or ''}{music_preset_prompt(music_preset)}".strip()


def _song_idea_with_vocal_direction(base_idea: str, vocal_direction: dict[str, str]) -> str:
    return f"{base_idea or ''}{vocal_direction_prompt(vocal_direction)}".strip()


def _music_style_with_preset(style_prompt: str, music_preset: dict[str, str], vocal_direction: dict[str, str] | None = None) -> str:
    parts = [style_prompt.strip()] if style_prompt.strip() else []
    if music_preset:
        parts.append(
            "Music preset direction: "
            f"{music_preset.get('genre', '')}; "
            f"{music_preset.get('mood', '')}; "
            f"{music_preset.get('vocal_style', '')}; "
            f"{music_preset.get('arrangement', '')}. "
            f"{music_preset.get('prompt_suffix', '')}"
        )
    if vocal_direction:
        parts.append(
            "Vocal direction: "
            f"{vocal_direction.get('vocal_style', '')}; "
            f"{vocal_direction.get('delivery', '')}; "
            f"{vocal_direction.get('emotional_tone', '')}."
        )
    return "\n".join(parts).strip()


def _settings_from_ai_controls(controls: dict[str, Any]) -> dict[str, Any]:
    return {
        "weirdness": int(controls.get("weirdness", 10)),
        "style_influence": int(controls.get("style_influence", 65)),
        "reason_th": controls.get("reason", ""),
        "weirdness_range": list(controls.get("weirdness_range", ())),
        "style_influence_range": list(controls.get("style_influence_range", ())),
        "manual": bool(controls.get("manual", False)),
    }


def _structure_energy_rows(plan: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in plan.get("sections", []) or []:
        energy = int(item.get("energy", 0) or 0)
        rows.append({
            "section": item.get("section", ""),
            "energy": energy,
            "bar": "█" * max(1, round(energy / 15)),
            "purpose": item.get("purpose", ""),
            "emotion": item.get("emotion", ""),
            "hook_role": item.get("hook_role", ""),
            "suggested_tag": item.get("suggested_tag", ""),
        })
    return rows


def _render_suno_downloads(project_name: str, song: dict[str, Any]) -> None:
    lyrics = song.get("normalized_song_output") or song.get("complete_lyrics") or ""
    if not lyrics.strip():
        st.info("No lyrics available yet.")
        return
    workflow_mode = st.session_state.get("workflow_mode", "Full Pipeline")
    export_result = export_suno_files(project_name, song, workflow_mode=workflow_mode)
    if not export_result.get("ok"):
        st.warning(export_result.get("error") or "Suno export is not ready yet.")
        return
    data = export_result.get("data", {})
    resolved_filename = data.get("suno_full_filename") or resolve_export_txt_filename(song, project_name, workflow_mode, data.get("suno_full_text", ""))
    if resolved_filename == "velaflow_export.txt":
        resolved_filename = resolve_export_txt_filename({**song, "title": project_name}, project_name, workflow_mode, data.get("suno_full_text", ""))
    st.success("Lyrics saved successfully")
    st.caption(f"TXT filename: {resolved_filename}")
    d1, d2, d3, d4 = st.columns(4)
    d1.download_button(
        "Download Suno TXT",
        data=data.get("suno_full_text", ""),
        file_name=resolved_filename,
        mime="text/plain",
        use_container_width=True,
        help="ดาวน์โหลดเนื้อเพลง แคปชั่น SEO คำอธิบาย YouTube แฮชแท็ก และพรอมต์ปกเพลงเป็นไฟล์ TXT",
    )
    d2.download_button(
        "Download Lyrics Only",
        data=data.get("lyrics_only_text", ""),
        file_name="lyrics_only.txt",
        mime="text/plain",
        use_container_width=True,
        help="ดาวน์โหลดเฉพาะเนื้อเพลงพร้อมแท็กสำหรับนำไปใช้ใน Suno",
    )
    if d3.button("Copy Lyrics for Suno", use_container_width=True, key="show_copy_lyrics_for_suno_btn", help="เปิดกล่องเนื้อเพลงเพื่อคัดลอกไปวางใน Suno ได้ง่ายขึ้น"):
        st.session_state.show_copy_lyrics_for_suno_open = True
    with d4:
        if st.button("Continue to MV Director", use_container_width=True, key="suno_continue_mv", help="ไปต่อขั้นตอนวางแผน MV จากเนื้อเพลงที่บันทึกแล้ว"):
            _continue_to_mv_director()
    with st.expander("Copy Lyrics for Suno", expanded=st.session_state.get("show_copy_lyrics_for_suno_open", True)):
        st.caption("คัดลอกเนื้อเพลงส่วนนี้ไปใช้กับ Suno ได้ทันที")
        st.text_area("Copy-ready lyrics", value=data.get("lyrics_only_text", lyrics), height=260, key="copy_lyrics_for_suno", help="เนื้อเพลงที่ผ่านการจัดรูปแบบและแก้แท็กเครื่องดนตรีแล้ว")
    with st.expander("Release Package Copy Blocks", expanded=False):
        st.caption("รวมข้อความสำหรับนำไปโพสต์หรือใช้ทำสื่อโปรโมตเพลง")
        c1, c2 = st.columns(2)
        with c1:
            st.text_area("Copy SEO Caption", value=data.get("seo_caption", ""), height=110, key="copy_seo_caption", help="แคปชั่นสั้น ๆ สำหรับ YouTube, TikTok, Reels หรือ Shorts")
            st.text_area("Copy TikTok Caption", value=data.get("tiktok_caption", ""), height=120, key="copy_tiktok_caption", help="แคปชั่นสำหรับคลิปสั้น TikTok, Reels หรือ Shorts")
            st.text_area("Copy Hashtags", value=data.get("hashtags_text", ""), height=110, key="copy_hashtags", help="แฮชแท็กเพลงไทย อารมณ์เพลง แนวเพลง ชื่อศิลปิน และชื่อเพลง")
        with c2:
            st.text_area("Copy YouTube Description", value=data.get("youtube_description", ""), height=160, key="copy_youtube_description", help="คำอธิบาย YouTube ที่มีชื่อเพลง ศิลปิน เครดิต และแฮชแท็ก")
            st.text_area("Copy Cover Prompts", value=data.get("cover_prompts_text", ""), height=160, key="copy_cover_prompts", help="พรอมต์สำหรับนำไปสร้างปกเพลง 3 ขนาด: 1:1, 16:9 และ 9:16")
    st.write("Suno TXT path")
    st.code(data.get("suno_full_package", ""), language="text")
    st.write("Open exports folder path")
    st.code(data.get("exports_dir", ""), language="text")
    st.caption(f"Lyrics Only: {data.get('lyrics_only', '')}")


def _artist_preset_label(preset: dict[str, Any]) -> str:
    badges = []
    if preset.get("is_default"):
        badges.append("default")
    badges.append("locked" if preset.get("locked") else "custom")
    return f"{preset.get('artist_name', preset.get('artist_id', 'Artist'))} ({', '.join(badges)})"


def _lines_to_list(text: str) -> list[str]:
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


def _dict_to_section_text(values: dict[str, Any]) -> str:
    return "\n".join(f"{section}: {tag}" for section, tag in (values or {}).items())


def _section_text_to_dict(text: str) -> dict[str, str]:
    output: dict[str, str] = {}
    for line in (text or "").splitlines():
        if not line.strip() or ":" not in line:
            continue
        section, tag = line.split(":", 1)
        output[section.strip()] = tag.strip()
    return output


def _preset_from_editor(original: dict[str, Any], prefix: str) -> dict[str, Any]:
    settings_data = original.get("suno_advanced_settings", {}) or {}
    mv = original.get("mv_identity", {}) or {}
    marketing = original.get("marketing_identity", {}) or {}
    return {
        "artist_id": st.session_state.get(f"{prefix}_artist_id", original.get("artist_id", "")),
        "artist_name": st.session_state.get(f"{prefix}_artist_name", original.get("artist_name", "")),
        "brand_style": st.session_state.get(f"{prefix}_brand_style", original.get("brand_style", "")),
        "genre": st.session_state.get(f"{prefix}_genre", original.get("genre", "")),
        "default_language": st.session_state.get(f"{prefix}_default_language", original.get("default_language", "Thai lyrics")),
        "music_prompt_language": "English only",
        "instrument_tags_language": "English only",
        "vocal_style": st.session_state.get(f"{prefix}_vocal_style", original.get("vocal_style", "")),
        "default_music_style_prompt": st.session_state.get(f"{prefix}_style_prompt", original.get("default_music_style_prompt", "")),
        "lyric_style": st.session_state.get(f"{prefix}_lyric_style", original.get("lyric_style", "")),
        "hook_style": st.session_state.get(f"{prefix}_hook_style", original.get("hook_style", "")),
        "writing_rules": _lines_to_list(st.session_state.get(f"{prefix}_writing_rules", "\n".join(original.get("writing_rules", []) or []))),
        "song_structure": _lines_to_list(st.session_state.get(f"{prefix}_song_structure", "\n".join(original.get("song_structure", []) or []))),
        "main_instruments": _lines_to_list(st.session_state.get(f"{prefix}_main_instruments", "\n".join(original.get("main_instruments", []) or []))),
        "supporting_instruments": _lines_to_list(st.session_state.get(f"{prefix}_supporting_instruments", "\n".join(original.get("supporting_instruments", []) or []))),
        "atmosphere_elements": _lines_to_list(st.session_state.get(f"{prefix}_atmosphere_elements", "\n".join(original.get("atmosphere_elements", []) or []))),
        "section_instrument_tags": _section_text_to_dict(st.session_state.get(f"{prefix}_section_tags", _dict_to_section_text(original.get("section_instrument_tags", {}) or {}))),
        "suno_advanced_settings": {
            "weirdness": int(st.session_state.get(f"{prefix}_weirdness", settings_data.get("weirdness", 10))),
            "style_influence": int(st.session_state.get(f"{prefix}_style_influence", settings_data.get("style_influence", 65))),
            "reason_th": st.session_state.get(f"{prefix}_reason_th", settings_data.get("reason_th", "")),
        },
        "mv_identity": {
            "render_profile": st.session_state.get(f"{prefix}_render_profile", mv.get("render_profile", "Cinematic")),
            "subtitle_style": st.session_state.get(f"{prefix}_subtitle_style", mv.get("subtitle_style", "cinematic")),
            "color_profile": st.session_state.get(f"{prefix}_color_profile", mv.get("color_profile", "")),
            "camera_language": _lines_to_list(st.session_state.get(f"{prefix}_camera_language", "\n".join(mv.get("camera_language", []) or []))),
            "visual_mood": st.session_state.get(f"{prefix}_visual_mood", mv.get("visual_mood", "")),
        },
        "marketing_identity": {
            "tone": st.session_state.get(f"{prefix}_marketing_tone", marketing.get("tone", "")),
            "target_platforms": _lines_to_list(st.session_state.get(f"{prefix}_target_platforms", "\n".join(marketing.get("target_platforms", []) or []))),
            "hook_style": st.session_state.get(f"{prefix}_marketing_hook_style", marketing.get("hook_style", "")),
        },
        "locked": bool(original.get("locked") and original.get("artist_id") == DEFAULT_ARTIST_ID),
    }


def _render_artist_preset_manager() -> None:
    _page_header("Artist Preset Manager", "Create, duplicate, import, export, and set local artist presets.", _project())
    presets = list_artist_presets() or [get_artist_preset(DEFAULT_ARTIST_ID)]
    labels = [_artist_preset_label(item) for item in presets]
    selected_label = st.selectbox("Artist Preset", labels, key="artist_manager_select")
    selected = presets[labels.index(selected_label)]
    selected_id = selected.get("artist_id", DEFAULT_ARTIST_ID)
    locked = is_locked_artist_preset(selected_id) or bool(selected.get("locked"))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Preset", selected.get("artist_name", selected_id))
    c2.metric("Type", "Locked" if locked else "Custom")
    c3.metric("Default", "Yes" if selected.get("is_default") else "No")
    suno = selected.get("suno_advanced_settings", {}) or {}
    c4.metric("Suno", f"W {suno.get('weirdness', 0)} / SI {suno.get('style_influence', 0)}")

    with st.expander("Preset Summary", expanded=True):
        st.write(f"Genre: {selected.get('genre', '')}")
        st.write(f"Vocal style: {selected.get('vocal_style', '')}")
        st.write("Main instruments:", ", ".join(selected.get("main_instruments", []) or []))
        st.code(selected.get("default_music_style_prompt", ""), language="text")

    if locked:
        st.warning("Vela Moon is a locked system preset. Duplicate it to customize.")
        d1, d2, d3 = st.columns([1, 1, 1])
        custom_id = d1.text_input("Custom Artist ID", value="vela_moon_custom", key="duplicate_locked_artist_id")
        custom_name = d2.text_input("Custom Artist Name", value="Vela Moon Custom", key="duplicate_locked_artist_name")
        if d3.button("Duplicate Vela Moon to Custom Preset", use_container_width=True):
            result = duplicate_artist_preset(selected_id, custom_id, custom_name)
            if result.get("ok"):
                st.success("Preset duplicated")
                st.rerun()
            else:
                st.error(result.get("message", "Duplicate failed"))

    prefix = f"artist_mgr_{selected_id}"
    t_basic, t_song, t_inst, t_suno, t_mv, t_marketing, t_io = st.tabs(["Basic", "Song", "Instruments", "Suno", "MV Identity", "Marketing", "Import / Export"])
    with t_basic:
        st.text_input("artist_id", value=selected.get("artist_id", ""), disabled=locked, key=f"{prefix}_artist_id")
        st.text_input("artist_name", value=selected.get("artist_name", ""), disabled=locked, key=f"{prefix}_artist_name")
        st.text_input("brand_style", value=selected.get("brand_style", ""), disabled=locked, key=f"{prefix}_brand_style")
        st.text_input("genre", value=selected.get("genre", ""), disabled=locked, key=f"{prefix}_genre")
        st.text_input("default_language", value=selected.get("default_language", "Thai lyrics"), disabled=locked, key=f"{prefix}_default_language")
        st.text_input("vocal_style", value=selected.get("vocal_style", ""), disabled=locked, key=f"{prefix}_vocal_style")
    with t_song:
        st.text_area("default_music_style_prompt", value=selected.get("default_music_style_prompt", ""), height=110, disabled=locked, key=f"{prefix}_style_prompt")
        st.text_area("lyric_style", value=selected.get("lyric_style", ""), height=80, disabled=locked, key=f"{prefix}_lyric_style")
        st.text_area("hook_style", value=selected.get("hook_style", ""), height=80, disabled=locked, key=f"{prefix}_hook_style")
        st.text_area("writing_rules (one per line)", value="\n".join(selected.get("writing_rules", []) or []), height=140, disabled=locked, key=f"{prefix}_writing_rules")
        st.text_area("song_structure (one per line)", value="\n".join(selected.get("song_structure", []) or []), height=140, disabled=locked, key=f"{prefix}_song_structure")
    with t_inst:
        st.text_area("main_instruments (English only, one per line)", value="\n".join(selected.get("main_instruments", []) or []), height=110, disabled=locked, key=f"{prefix}_main_instruments")
        st.text_area("supporting_instruments (English only, one per line)", value="\n".join(selected.get("supporting_instruments", []) or []), height=110, disabled=locked, key=f"{prefix}_supporting_instruments")
        st.text_area("atmosphere_elements (English only, one per line)", value="\n".join(selected.get("atmosphere_elements", []) or []), height=110, disabled=locked, key=f"{prefix}_atmosphere_elements")
        st.text_area("section_instrument_tags (Section: English tag)", value=_dict_to_section_text(selected.get("section_instrument_tags", {}) or {}), height=220, disabled=locked, key=f"{prefix}_section_tags")
    with t_suno:
        st.slider("weirdness", 0, 100, int(suno.get("weirdness", 10)), disabled=locked, key=f"{prefix}_weirdness")
        st.slider("style_influence", 0, 100, int(suno.get("style_influence", 65)), disabled=locked, key=f"{prefix}_style_influence")
        st.text_area("reason_th", value=suno.get("reason_th", ""), height=120, disabled=locked, key=f"{prefix}_reason_th")
    with t_mv:
        mv = selected.get("mv_identity", {}) or {}
        st.text_input("render_profile", value=mv.get("render_profile", "Cinematic"), disabled=locked, key=f"{prefix}_render_profile")
        st.text_input("subtitle_style", value=mv.get("subtitle_style", "cinematic"), disabled=locked, key=f"{prefix}_subtitle_style")
        st.text_input("color_profile", value=mv.get("color_profile", ""), disabled=locked, key=f"{prefix}_color_profile")
        st.text_area("camera_language (one per line)", value="\n".join(mv.get("camera_language", []) or []), height=100, disabled=locked, key=f"{prefix}_camera_language")
        st.text_area("visual_mood", value=mv.get("visual_mood", ""), height=100, disabled=locked, key=f"{prefix}_visual_mood")
    with t_marketing:
        marketing = selected.get("marketing_identity", {}) or {}
        st.text_area("tone", value=marketing.get("tone", ""), height=90, disabled=locked, key=f"{prefix}_marketing_tone")
        st.text_area("target_platforms (one per line)", value="\n".join(marketing.get("target_platforms", []) or []), height=100, disabled=locked, key=f"{prefix}_target_platforms")
        st.text_area("hook_style", value=marketing.get("hook_style", ""), height=90, disabled=locked, key=f"{prefix}_marketing_hook_style")
    with t_io:
        export_result = export_artist_preset(selected_id)
        if export_result.get("ok"):
            st.download_button("Export Preset JSON", data=export_result["data"]["json"], file_name=f"{selected_id}.json", mime="application/json", use_container_width=True)
        uploaded = st.file_uploader("Import Preset JSON", type=["json"], key="artist_preset_import")
        overwrite = st.checkbox("Overwrite existing custom preset", value=False, key="artist_import_overwrite")
        save_copy = st.checkbox("Save as new copy if ID exists", value=True, key="artist_import_copy")
        if st.button("Import Preset", disabled=uploaded is None, use_container_width=True):
            try:
                data = json.loads(uploaded.getvalue().decode("utf-8")) if uploaded is not None else {}
                result = import_artist_preset(data, overwrite=overwrite, save_as_copy=save_copy)
                if result.get("ok"):
                    st.success("Preset imported")
                    st.rerun()
                else:
                    st.error(result.get("message", "Import failed"))
            except Exception as exc:
                st.error(f"Import failed: {exc}")

    edited = _preset_from_editor(selected, prefix)
    a1, a2, a3, a4, a5 = st.columns(5)
    if a1.button("Save Preset", type="primary", disabled=locked, use_container_width=True):
        result = save_artist_preset(edited)
        if result.get("ok"):
            st.success("Artist preset saved")
            st.rerun()
        else:
            st.error(result.get("message", "Save failed"))
            st.json(result.get("data", {}), expanded=False)
    if a2.button("Set Default", use_container_width=True):
        result = set_default_artist_preset(selected_id)
        if result.get("ok"):
            st.session_state.selected_artist_preset = selected_id
            st.success("Default artist preset updated")
            st.rerun()
        else:
            st.error(result.get("message", "Set default failed"))
    if a3.button("Duplicate", use_container_width=True):
        result = duplicate_artist_preset(selected_id, f"{selected_id}_copy", f"{selected.get('artist_name', selected_id)} Copy")
        if result.get("ok"):
            st.success("Preset duplicated")
            st.rerun()
        else:
            st.error(result.get("message", "Duplicate failed"))
    if a4.button("Create New", use_container_width=True):
        result = duplicate_artist_preset(DEFAULT_ARTIST_ID, "new_custom_artist", "New Custom Artist")
        if result.get("ok"):
            st.success("New preset created from Vela Moon")
            st.rerun()
        else:
            st.error(result.get("message", "Create failed"))
    confirm_delete = st.checkbox("Confirm delete selected custom preset", value=False, disabled=locked, key="artist_delete_confirm")
    if a5.button("Delete", disabled=locked or not confirm_delete, use_container_width=True):
        result = delete_artist_preset(selected_id)
        if result.get("ok"):
            st.success("Artist preset deleted")
            st.rerun()
        else:
            st.error(result.get("message", "Delete failed"))


def _render_song_studio(project: dict[str, Any]) -> None:
    _page_header("Song Studio", "Generate hooks, lyrics, and Suno-ready Thai lyrics with English production tags.", project)
    with st.container(border=True):
        st.markdown("**Quick Start**")
        st.markdown(
            "1. เลือก Music Preset  \n"
            "2. ใส่ไอเดียเพลงสั้น ๆ  \n"
            "3. กด Generate Full Lyrics  \n"
            "4. Copy หรือ Download Release Package"
        )
    creative_direction = project.get("creative_direction") or st.session_state.get("creative_direction", {}) or {}
    structure_plan = (project.get("song", {}) or {}).get("song_structure_plan") or project.get("song_structure_plan") or st.session_state.get("song_structure_plan", {}) or {}
    artist_presets = list_artist_presets() or [get_artist_preset("vela_moon")]
    names = [_artist_preset_label(preset) for preset in artist_presets]
    default_artist_id = load_default_artist_id()
    song = normalize_song_metadata(project.get("song", {}) or {}, get_artist_preset((project.get("song", {}) or {}).get("artist_preset") or default_artist_id))
    project["song"] = song
    current_artist_id = song.get("artist_preset") or st.session_state.get("selected_artist_preset") or default_artist_id
    current_index = next((idx for idx, preset_item in enumerate(artist_presets) if preset_item.get("artist_id") == current_artist_id), 0)

    if creative_direction:
        with st.container(border=True):
            st.markdown("**Creative Direction Loaded**")
            dc1, dc2, dc3, dc4 = st.columns(4)
            dc1.metric("Topic", creative_direction.get("topic", "-"))
            dc2.metric("Mood", creative_direction.get("mood", "-"))
            dc3.metric("Preset", creative_direction.get("artist_preset", "-"))
            dc4.metric("Platform", creative_direction.get("target_platform", "-"))
            st.caption(f"Hook: {creative_direction.get('hook_direction', '')}")
            st.caption(f"Music: {creative_direction.get('music_style_direction', '')}")
            if st.button("Clear Creative Direction", key="song_clear_creative_direction"):
                project.pop("creative_direction", None)
                st.session_state.creative_direction = {}
                _save_project()
                st.rerun()

    with st.expander("Song Structure Intelligence", expanded=bool(structure_plan)):
        structure_presets = list_structure_presets()
        structure_labels = [item.get("name", item.get("preset_id", "")) for item in structure_presets] or ["Vela Moon Pop Rock"]
        current_structure_id = structure_plan.get("preset_id") or "vela_moon_pop_rock"
        current_structure_index = next((idx for idx, item in enumerate(structure_presets) if item.get("preset_id") == current_structure_id), 0)
        selected_structure_label = st.selectbox("Structure Preset", structure_labels, index=current_structure_index, key="song_structure_preset", help="เลือกโครงสร้างเพลงคร่าว ๆ เพื่อช่วยวางท่อนและพลังของเพลง")
        selected_structure = structure_presets[structure_labels.index(selected_structure_label)] if structure_presets else get_structure_preset("vela_moon_pop_rock")
        use_structure_plan = st.checkbox("Use Structure Plan for Lyrics", value=st.session_state.get("use_structure_plan_for_lyrics", True), key="use_structure_plan_for_lyrics")
        if st.button("Generate / Refresh Structure Plan", key="song_generate_structure_plan", help="สร้างหรืออัปเดตแผนโครงสร้างเพลงจากไอเดียและพรีเซ็ตปัจจุบัน"):
            context = {
                **creative_direction,
                "topic": creative_direction.get("topic") or project.get("title", ""),
                "mood": creative_direction.get("mood", ""),
                "genre": creative_direction.get("music_direction", ""),
                "artist_preset": current_artist_id,
                "target_platform": creative_direction.get("target_platform", "Full Pipeline"),
                "selected_hook": song.get("selected_hook", {}),
            }
            structure_plan = create_structure_plan(context, selected_structure.get("preset_id"), get_artist_preset(current_artist_id))
            project["song_structure_plan"] = structure_plan
            project.setdefault("song", {})["song_structure_plan"] = structure_plan
            st.session_state.song_structure_plan = structure_plan
            save_structure_plan(project.get("title", "project"), structure_plan)
            _save_project()
            st.success("Song structure plan generated")
            st.rerun()
        if structure_plan:
            st.write(f"Selected structure preset: {structure_plan.get('preset_name', '')}")
            st.caption(f"Hook placement: {structure_plan.get('recommended_hook_placement', '')}")
            st.caption(f"Emotional arc: {structure_plan.get('emotional_arc', '')}")
            st.dataframe(pd.DataFrame(_structure_energy_rows(structure_plan)), use_container_width=True, height=260)
            with st.container(border=True):
                st.markdown("**Notes for lyrics / MV Director**")
                st.caption(structure_plan.get("notes_for_lyrics_generation", ""))
                st.caption(structure_plan.get("notes_for_mv_director", ""))

    left, right = st.columns([1.1, 0.9])
    with left:
        title = st.text_input("Project / Song Title", value=project.get("title", "เพลงใหม่ของฉัน"), help="ใส่ชื่อเพลงที่ต้องการ หรือเว้นว่างให้ระบบช่วยคิดชื่อเพลง")
        artist = st.text_input("Artist", value=project.get("artist", DEFAULT_ARTIST), help="ชื่อศิลปินที่จะแสดงในแพ็กเกจเพลง เช่น Vela Moon")
        idea = st.text_area("Song Idea / Story", height=160, key="song_idea", help="เล่าเรื่องเพลงสั้น ๆ เช่น เพลงเกี่ยวกับคิดถึงแฟนเก่าในคืนฝนตก")
        genre_options = ["Pop Rock", "Heartbreak Ballad", "T-Pop", "Night Drive", "Isaan Indie"]
        direction_genre = creative_direction.get("music_direction", "")
        genre_index = next((idx for idx, item in enumerate(genre_options) if item.lower() in direction_genre.lower() or direction_genre.lower() in item.lower()), 0)
        genre = st.selectbox("Genre", genre_options, index=genre_index, help="เลือกแนวเพลงหลักเพื่อให้ดนตรีและคำร้องไปในทิศทางเดียวกัน")
        mood_options = ["เศร้า", "คิดถึง", "เหงากลางคืน", "อบอุ่น", "ให้กำลังใจ"]
        mood = st.selectbox("Mood", mood_options, index=1, help="เลือกอารมณ์หลักของเพลง เช่น เศร้า เหงา ให้กำลังใจ หรือรัก")
        vocal = st.selectbox("Vocal", ["smooth emotional male vocal", "emotional male vocal", "soft female vocal", "duet male and female"], index=0, help="เลือกโทนเสียงร้องที่อยากให้เพลงรู้สึกใกล้เคียงที่สุด")
        vocal_language = st.selectbox("Language", ["Thai lyrics"], index=0, disabled=True, help="ตอนนี้ Song Studio ตั้งค่าให้เนื้อเพลงเป็นภาษาไทย และแท็กดนตรีในวงเล็บเป็นภาษาอังกฤษ")
        viral = st.selectbox("Viral Level", ["balanced", "high", "ultra hook-focused"], index=1, help="เลือกระดับความเน้นฮุก ถ้าทำคลิปสั้นให้เลือก high หรือ ultra hook-focused")
    with right:
        selected_name = st.selectbox("Artist Preset", names, index=current_index, help="เลือกตัวตนศิลปินเพื่อคุมแนวเสียงร้อง เนื้อเพลง และภาพรวมเพลง")
        preset = artist_presets[names.index(selected_name)]
        st.session_state.selected_artist_preset = preset.get("artist_id", "vela_moon")
        use_preset = st.checkbox("Use Artist Preset Style", value=True)
        force_tags = st.checkbox("Force English Instrument Tags", value=True)
        music_preset_names = list_music_preset_names()
        current_music_preset = song.get("music_preset", DEFAULT_MUSIC_PRESET)
        music_preset_index = music_preset_names.index(current_music_preset) if current_music_preset in music_preset_names else 0
        selected_music_preset_name = st.selectbox("Music Preset", music_preset_names, index=music_preset_index, key="song_music_preset", help="เลือกสไตล์สำเร็จรูปเพื่อให้ระบบสร้างเพลงออกมาในโทนที่ต้องการ")
        selected_music_preset = get_music_preset(selected_music_preset_name)
        st.info(selected_music_preset.get("description", ""))
        vocal_direction_names = list_vocal_direction_names()
        current_vocal_direction = song.get("vocal_direction", DEFAULT_VOCAL_DIRECTION)
        vocal_direction_index = vocal_direction_names.index(current_vocal_direction) if current_vocal_direction in vocal_direction_names else 0
        selected_vocal_direction_name = st.selectbox("Vocal Direction", vocal_direction_names, index=vocal_direction_index, key="song_vocal_direction", help="เลือกทิศทางเสียงร้องและอารมณ์การถ่ายทอดของเพลง")
        selected_vocal_direction = get_vocal_direction(selected_vocal_direction_name)
        st.caption(selected_vocal_direction.get("description", ""))
        current_ranges = {
            "Weirdness": f"{selected_music_preset.get('weirdness_range', [8, 14])[0]}-{selected_music_preset.get('weirdness_range', [8, 14])[1]}",
            "Style Influence": f"{selected_music_preset.get('style_influence_range', [55, 68])[0]}-{selected_music_preset.get('style_influence_range', [55, 68])[1]}",
        }
        st.caption(f"AI controls range: Weirdness {current_ranges['Weirdness']} / Style Influence {current_ranges['Style Influence']}")
        style_override = st.text_area("Music Style Prompt Override", value=preset.get("default_music_style_prompt", ""), height=120, help="แก้รายละเอียดดนตรีเพิ่มเติม ถ้าอยากระบุเครื่องดนตรีหรือโทนเพลงเอง")
        with st.expander("Preset Summary", expanded=True):
            st.write(f"Genre: {preset.get('genre', '')}")
            st.write(f"Vocal: {preset.get('vocal_style', '')}")
            st.write(", ".join(preset.get("main_instruments", []) or []))
            st.json(preset.get("suno_advanced_settings", {}), expanded=False)
        with st.expander("Music Preset Details", expanded=False):
            st.json(selected_music_preset, expanded=False)

    hook_candidates = normalize_hook_candidates(song.get("hook_candidates") or song.get("candidate_hooks") or st.session_state.get("hook_candidates", []))
    selected_hook = song.get("selected_hook") if isinstance(song.get("selected_hook"), dict) else st.session_state.get("selected_hook", {})
    selected_hook_text = (selected_hook or {}).get("hook_text") or song.get("selected_hook_text", "")
    lyrics_text = song.get("normalized_song_output") or song.get("complete_lyrics", "")
    validation = validate_english_only_tags(lyrics_text) if lyrics_text else {"ok": False}
    lyrics_generated = bool(lyrics_text)
    lyrics_saved = bool(song.get("saved_at")) or st.session_state.get("lyrics_saved", False)
    export_dir = ROOT / "project_data" / "projects" / safe_name(project.get("title", "project")) / "exports"
    suno_ready = bool(lyrics_saved and export_dir.exists() and any(export_dir.glob("*.txt")))
    ready_for_mv = lyrics_generated and bool(validation.get("ok"))

    st.write("Workflow Status")
    s1, s2, s3, s4, s5, s6, s7 = st.columns(7)
    s1.metric("Hooks", "Yes" if hook_candidates else "No")
    s2.metric("Hook Selected", "Yes" if selected_hook_text else "No")
    s3.metric("Lyrics", "Yes" if lyrics_generated else "No")
    s4.metric("English Tags", "Yes" if validation.get("ok") else "No")
    s5.metric("Saved", "Yes" if lyrics_saved else "No")
    s6.metric("Suno TXT", "Ready" if suno_ready else "No")
    s7.metric("MV Ready", "Yes" if ready_for_mv else "No")

    st.divider()
    st.markdown("**Step 1-2: Hook Candidates**")
    hook_actions = st.columns(3)
    generate_hooks_clicked = hook_actions[0].button("Generate Hook Candidates", type="primary", key="song_generate_hooks", help="สร้างตัวเลือกฮุกหลายแบบให้เลือกก่อนเขียนเนื้อเพลงเต็ม")
    regenerate_hooks_clicked = hook_actions[1].button("Regenerate Hooks", key="song_regenerate_hooks", help="ล้างฮุกเดิมแล้วสร้างชุดใหม่ ถ้ายังไม่ถูกใจ")
    hook_cache_dir = ROOT / "outputs" / "cache" / "text"
    if hook_cache_dir.exists() and hook_actions[2].button("Clear Hook Cache", key="song_clear_hook_cache", help="ล้างข้อมูลฮุกเก่าที่แคชไว้ เพื่อให้ลองไอเดียใหม่ได้สะอาดขึ้น"):
        for cache_file in hook_cache_dir.glob("*.json"):
            cache_file.unlink(missing_ok=True)
        st.success("Hook cache cleared")
        st.rerun()
    if generate_hooks_clicked or regenerate_hooks_clicked:
        if not idea.strip():
            st.warning("ใส่ไอเดียเพลงก่อน เพื่อให้ hook เข้ากับเรื่องของเพลง")
        song.pop("hook_candidates", None)
        song.pop("candidate_hooks", None)
        song.pop("selected_hook", None)
        song.pop("selected_hook_text", None)
        st.session_state.hook_candidates = []
        st.session_state.selected_hook = {}
        hook_result = generate_hook_candidates_with_provider(
            api_key=settings.gemini_api_key,
            model_name=settings.gemini_model,
            idea=_song_idea_with_vocal_direction(_music_preset_for_song_idea(_structure_for_song_idea(_direction_for_song_idea(idea, creative_direction), structure_plan, use_structure_plan), selected_music_preset), selected_vocal_direction),
            genre=genre,
            mood=mood,
            artist_preset=preset if use_preset else get_artist_preset("vela_moon"),
        )
        candidates = hook_result.get("data", {}).get("hooks", [])
        if hook_result.get("data", {}).get("offline"):
            st.warning("Using offline fallback hooks")
        hook_style_prompt = _music_style_with_preset(style_override if use_preset else preset.get("default_music_style_prompt", ""), selected_music_preset, selected_vocal_direction)
        ai_controls = get_recommended_ai_controls(selected_music_preset_name)
        advanced_settings = _settings_from_ai_controls(ai_controls)
        song.update({
            "hook_candidates": candidates,
            "candidate_hooks": candidates,
            "artist_preset": preset.get("artist_id", "vela_moon"),
            "artist_preset_data": preset,
            "music_style_prompt": hook_style_prompt,
            "music_preset": selected_music_preset_name,
            "music_preset_data": selected_music_preset,
            "vocal_direction": selected_vocal_direction_name,
            "vocal_direction_data": selected_vocal_direction,
            "advanced_settings": advanced_settings,
            "weirdness": advanced_settings["weirdness"],
            "style_influence": advanced_settings["style_influence"],
            "instrument_tags_language": "English only",
            "hook_generation_seed": hook_result.get("data", {}).get("seed", ""),
            "hook_generation_offline": hook_result.get("data", {}).get("offline", False),
            "song_structure_plan": structure_plan,
        })
        project["title"] = title
        project["artist"] = artist
        project["song"] = song
        st.session_state.hook_candidates = candidates
        _save_project()
        st.success("Hook candidates generated")
        st.rerun()

    hook_candidates = normalize_hook_candidates(project.get("song", {}).get("hook_candidates") or project.get("song", {}).get("candidate_hooks") or st.session_state.get("hook_candidates", []))
    if hook_candidates:
        for index, hook in enumerate(hook_candidates):
            is_selected = hook.get("hook_text") == selected_hook_text
            with st.container(border=True):
                h1, h2 = st.columns([3, 1])
                h1.markdown(f"**{hook.get('hook_text', '')}**")
                h2.markdown("`SELECTED`" if is_selected else "")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Emotional", hook.get("emotional_score", 0))
                m2.metric("Catchy", hook.get("catchy_score", 0))
                m3.metric("TikTok", hook.get("tiktok_potential", 0))
                m4.metric("Usage", hook.get("suggested_usage", "chorus"))
                st.progress(int(hook.get("emotional_score", 0)) / 100, text="Emotional")
                st.progress(int(hook.get("catchy_score", 0)) / 100, text="Catchy")
                st.progress(int(hook.get("tiktok_potential", 0)) / 100, text="TikTok")
                st.caption(hook.get("reason_th", ""))
                if st.button("Select Hook", key=f"song_select_hook_{index}", disabled=is_selected, help="เลือกฮุกนี้เป็นแกนหลักของท่อน Chorus หรือท่อนจำ"):
                    song = project.setdefault("song", {})
                    song["hook_candidates"] = hook_candidates
                    song["candidate_hooks"] = hook_candidates
                    song["selected_hook"] = hook
                    song["selected_hook_text"] = hook.get("hook_text", "")
                    st.session_state.selected_hook = hook
                    _save_project()
                    st.success(f"Hook selected: {hook.get('hook_text', '')}")
                    st.toast("Hook selected")
                    st.rerun()
    else:
        st.info("ยังไม่มี hook candidates. กด Generate Hook Candidates ก่อน หรือ Generate Full Lyrics จะสร้างและเลือก hook อัตโนมัติ")

    st.divider()
    st.markdown("**Step 3-5: Generate Full Lyrics, Normalize Tags, Preview**")
    if st.button("Generate Full Lyrics Using Selected Hook", key="song_generate_full_lyrics", help="สร้างเนื้อเพลงพร้อม Release Package สำหรับนำไปใช้งานต่อ"):
        if not idea.strip():
            st.error("กรุณาใส่ไอเดียเพลง")
            st.stop()
        if not hook_candidates:
            hook_result = generate_hook_candidates_with_provider(
                api_key=settings.gemini_api_key,
                model_name=settings.gemini_model,
                idea=_song_idea_with_vocal_direction(_music_preset_for_song_idea(_structure_for_song_idea(_direction_for_song_idea(idea, creative_direction), structure_plan, use_structure_plan), selected_music_preset), selected_vocal_direction),
                genre=genre,
                mood=mood,
                artist_preset=preset if use_preset else get_artist_preset("vela_moon"),
            )
            candidates = hook_result.get("data", {}).get("hooks", [])
            if hook_result.get("data", {}).get("offline"):
                st.warning("Using offline fallback hooks")
        else:
            candidates = hook_candidates
        hook = project.get("song", {}).get("selected_hook") if isinstance(project.get("song", {}).get("selected_hook"), dict) else {}
        if not hook:
            hook = select_best_hook(candidates)
            st.info(f"ยังไม่ได้เลือก hook ระบบเลือกคะแนนรวมสูงสุดให้: {hook.get('hook_text', '')}")
        idea_with_hook = (
            f"{_song_idea_with_vocal_direction(_music_preset_for_song_idea(_structure_for_song_idea(_direction_for_song_idea(idea, creative_direction), structure_plan, use_structure_plan), selected_music_preset), selected_vocal_direction)}\n\nSelected Hook: {hook.get('hook_text', '')}\n"
            "Use this selected hook as the main chorus or strongest memorable line. "
            "Keep Thai lyrics natural. Keep all parentheses tags English only."
        )
        final_style_prompt = _music_style_with_preset(style_override if use_preset else preset.get("default_music_style_prompt", ""), selected_music_preset, selected_vocal_direction)
        ai_controls = get_recommended_ai_controls(selected_music_preset_name)
        advanced_settings = _settings_from_ai_controls(ai_controls)
        song_result = _safe(
            "Generate song",
            generate_song_with_gemini,
            settings.gemini_api_key,
            settings.gemini_model,
            idea_with_hook,
            genre,
            mood,
            vocal,
            viral,
            artist_preset=preset if use_preset else get_artist_preset("vela_moon"),
            music_style_override=final_style_prompt,
            force_english_instrument_tags=force_tags,
        )
        if song_result.get("ok") is False and "title" not in song_result:
            st.stop()
        song_result["hook_candidates"] = candidates
        song_result["candidate_hooks"] = candidates
        song_result["selected_hook"] = hook
        song_result["selected_hook_text"] = hook.get("hook_text", "")
        song_result["artist_preset"] = preset.get("artist_id", "vela_moon")
        song_result["artist_preset_data"] = preset
        song_result["music_preset"] = selected_music_preset_name
        song_result["music_preset_data"] = selected_music_preset
        song_result["vocal_direction"] = selected_vocal_direction_name
        song_result["vocal_direction_data"] = selected_vocal_direction
        song_result["advanced_settings"] = advanced_settings
        song_result["weirdness"] = advanced_settings["weirdness"]
        song_result["style_influence"] = advanced_settings["style_influence"]
        song_result["instrument_tags_language"] = "English only"
        song_result["song_structure_plan"] = structure_plan
        song_result = normalize_song_metadata(song_result, preset)
        project["title"] = song_result.get("title") or title
        project["artist"] = artist
        project["song"] = song_result
        st.session_state.generated_song = song_result
        st.session_state.normalized_song_output = song_result.get("normalized_song_output", "")
        st.session_state.hook_candidates = candidates
        st.session_state.selected_hook = hook
        st.session_state.lyrics_saved = False
        _save_project()
        st.success("Full lyrics generated and instrument tags normalized")
        st.rerun()

    song = normalize_song_metadata(project.get("song", {}) or {}, get_artist_preset((project.get("song", {}) or {}).get("artist_preset") or load_default_artist_id()))
    if song.get("hook_candidates") or song.get("normalized_song_output") or song.get("complete_lyrics"):
        project["song"] = song
        t1, t2, t3, t4, t5 = st.tabs(["Hook", "Suno Style", "Lyrics", "Save / Continue", "Draft History"])
        with t1:
            st.write("Title:", song.get("title", ""))
            st.write("Selected Hook:", song.get("selected_hook_text", ""))
            st.dataframe(pd.DataFrame(song.get("hook_candidates", [])), use_container_width=True)
        with t2:
            st.write("Music Preset:", song.get("music_preset", DEFAULT_MUSIC_PRESET))
            st.write("Vocal Direction:", song.get("vocal_direction", DEFAULT_VOCAL_DIRECTION))
            st.code(song.get("music_style_prompt", ""), language="text")
            st.json(song.get("advanced_settings", {}), expanded=False)
            st.json({"artist_preset": song.get("artist_preset", "vela_moon"), "instrument_tags_language": song.get("instrument_tags_language", "English only")}, expanded=False)
        with t3:
            edited = st.text_area("Preview Final Lyrics / Edit Before Save", value=song.get("normalized_song_output") or song.get("complete_lyrics", ""), height=520, help="ตรวจและแก้เนื้อเพลงก่อนบันทึก ระบบจะคงเนื้อไทยไว้และดูแลแท็กดนตรีให้เป็นอังกฤษ")
            validation = validate_english_only_tags(edited)
            if not validation.get("ok"):
                st.warning("Some instrument tags still contain Thai. Click Auto Fix Tags.")
            c1, c2 = st.columns(2)
            if c1.button("Auto Fix Instrument Tags", help="แก้ข้อความในวงเล็บให้เป็นภาษาอังกฤษ โดยไม่แปลเนื้อเพลงไทย"):
                fixed = normalize_lyrics_tags(edited, get_artist_preset(song.get("artist_preset", "vela_moon")))
                song["original_song_output"] = song.get("original_song_output") or edited
                song["normalized_song_output"] = fixed
                song["complete_lyrics"] = fixed
                song["instrument_tag_validation"] = validate_english_only_tags(fixed)
                st.session_state.normalized_song_output = fixed
                _save_project()
                st.rerun()
            if c2.button("Apply Edited Lyrics", help="ใช้เนื้อเพลงที่แก้ในช่องนี้เป็นเวอร์ชันล่าสุด"):
                fixed = normalize_lyrics_tags(edited, get_artist_preset(song.get("artist_preset", "vela_moon")))
                song["complete_lyrics"] = fixed
                song["normalized_song_output"] = fixed
                song["instrument_tag_validation"] = validate_english_only_tags(fixed)
                _save_project()
                st.success("Edited lyrics applied")
            with st.expander("Normalized Song Output", expanded=True):
                st.text_area("normalized_song_output", value=song.get("normalized_song_output", ""), height=220, key="normalized_song_output_display", help="เนื้อเพลงเวอร์ชันที่พร้อมนำไปใช้ต่อและ export")
            with st.expander("Instrument Tag Validation", expanded=False):
                st.json(validation, expanded=False)
        with t4:
            st.write("Save Flow")
            col1, col2, col3, col4 = st.columns(4)
            if col1.button("Save Lyrics", type="primary", use_container_width=True, help="บันทึกเนื้อเพลงและสร้างไฟล์ TXT สำหรับ Release Package"):
                result = save_song_state(project.get("title", title), song, workflow_mode=st.session_state.get("workflow_mode", "Full Pipeline"))
                if result.get("ok"):
                    project["song"] = result["data"]["song"]
                    song = project["song"]
                    st.session_state.lyrics_saved = True
                    _save_project()
                    st.success("Lyrics saved. Ready for MV Director.")
                    st.toast("Lyrics saved")
                else:
                    st.error(result.get("error", "Save failed"))
            if col2.button("Save Lyrics & Continue to MV Director", use_container_width=True, help="บันทึกเนื้อเพลงก่อน แล้วไปต่อหน้าวางแผน MV"):
                result = save_song_state(project.get("title", title), song, workflow_mode=st.session_state.get("workflow_mode", "Full Pipeline"))
                if result.get("ok"):
                    project["song"] = result["data"]["song"]
                    song = project["song"]
                    st.session_state.lyrics_saved = True
                    _save_project()
                    st.success("Lyrics saved. Ready for MV Director.")
                    st.toast("Lyrics saved")
                    _continue_to_mv_director()
                else:
                    st.error(result.get("error", "Save failed"))
            if col3.button("Save Draft", use_container_width=True, help="เก็บร่างนี้ไว้เปรียบเทียบหรือกลับมาใช้ภายหลัง"):
                result = save_song_state(project.get("title", title), song, create_draft=True, workflow_mode=st.session_state.get("workflow_mode", "Full Pipeline"))
                if result.get("ok"):
                    project["song"] = result["data"]["song"]
                    song = project["song"]
                    st.session_state.lyrics_saved = True
                    _save_project()
                    st.success(f"Draft saved: {result['data'].get('draft_path', '')}")
                    st.toast("Draft saved")
                else:
                    st.error(result.get("error", "Draft save failed"))
            if col4.button("Load Last Saved Lyrics", use_container_width=True, help="โหลดเนื้อเพลงล่าสุดที่เคยบันทึกไว้ในโปรเจกต์นี้"):
                result = load_saved_song(project.get("title", title))
                if result.get("ok"):
                    project["song"] = result["data"]["song"]
                    st.session_state.generated_song = project["song"]
                    st.session_state.normalized_song_output = project["song"].get("normalized_song_output", "")
                    st.session_state.lyrics_saved = True
                    st.success("Last saved lyrics loaded")
                    st.toast("Draft loaded")
                    st.rerun()
                else:
                    st.warning(result.get("message", "No saved song found"))
            st.json({
                "song_json": str(ROOT / "project_data" / "projects" / safe_name(project.get("title", title)) / "song.json"),
                "lyrics_txt": str(ROOT / "project_data" / "projects" / safe_name(project.get("title", title)) / "lyrics.txt"),
                "suno_full_package": str(ROOT / "project_data" / "projects" / safe_name(project.get("title", title)) / "exports"),
                "lyrics_only": str(ROOT / "project_data" / "projects" / safe_name(project.get("title", title)) / "exports" / "lyrics_only.txt"),
                "ready_for_mv_director": bool((song.get("normalized_song_output") or song.get("complete_lyrics")) and song.get("instrument_tag_validation", {}).get("ok", False)),
            }, expanded=False)
            _render_suno_downloads(project.get("title", title), song)
        with t5:
            drafts = list_song_drafts(project.get("title", title))
            if drafts:
                draft_names = [draft["name"] for draft in drafts]
                chosen = st.selectbox("Recent Drafts", draft_names, key="song_draft_select")
                chosen_draft = drafts[draft_names.index(chosen)]
                dc1, dc2 = st.columns(2)
                if dc1.button("Load Draft", use_container_width=True):
                    result = load_song_draft(chosen_draft["path"])
                    if result.get("ok"):
                        project["song"] = result["data"]["song"]
                        st.session_state.generated_song = project["song"]
                        st.session_state.normalized_song_output = project["song"].get("normalized_song_output", "")
                        st.success("Draft loaded")
                        st.rerun()
                    else:
                        st.error(result.get("error", "Load draft failed"))
                if dc2.button("Compare Current vs Draft", use_container_width=True):
                    result = load_song_draft(chosen_draft["path"])
                    if result.get("ok"):
                        compare = compare_song_to_draft(song, result["data"]["song"])
                        st.dataframe(pd.DataFrame(compare["data"]["rows"]), use_container_width=True)
                st.dataframe(pd.DataFrame(drafts), use_container_width=True)
            else:
                st.info("ยังไม่มี draft history")
        with st.expander("TikTok Cut Recommendation", expanded=False):
            st.json(song.get("tiktok_clip_cut_recommendation", []), expanded=False)


_ensure_state()
project = _project()

st.title(f"🎬 {APP_TITLE}")
st.caption(f"{PRODUCT_TAGLINE} by {BRAND_NAME} | V7.8.6a Song Structure Intelligence v1")

PAGE_MODULES = {
    "Dashboard": "core",
    "Creator Wizard": "core",
    "Song Studio": "director",
    "Song Library": "core",
    "MV Director": "director",
    "Character Studio": "director",
    "Image Lab": "assets",
    "Image Review": "assets",
    "Video Lab": "providers",
    "Render Lab": "render",
    "Smart Clip Factory": "clips",
    "Marketing Package": "marketing",
    "Final Package": "render",
    "Creative Intelligence": "director",
    "Production Audit": "core",
    "Beta Test Mode": "core",
    "Asset Intelligence": "assets",
    "Queue Monitor": "render",
    "System Health": "core",
    "Release Hardening Tools": "core",
    "AI Settings": "providers",
    "Artist Preset Manager": "providers",
    "Seller Studio": "marketing",
}
MENU_GROUPS = menu_groups_for_mode(st.session_state.get("workflow_mode", "Full Pipeline"))
PAGES = flatten_pages(MENU_GROUPS)
ALL_PAGES = flatten_pages(FULL_MENU_GROUPS)


def _section_for_page(page_name: str) -> str:
    return next((section for section, items in MENU_GROUPS.items() if page_name in items), "START")


def _sync_navigation_state() -> None:
    pending = st.session_state.pop("pending_navigation", None)
    if isinstance(pending, dict):
        pending_page = pending.get("page")
        pending_section = pending.get("section")
        if pending_page in flatten_pages(MENU_GROUPS):
            st.session_state.selected_page = pending_page
            st.session_state.selected_section = pending_section if pending_section in MENU_GROUPS else _section_for_page(pending_page)
    legacy_page = st.session_state.pop("nav_page", None)
    if legacy_page and legacy_page in PAGES:
        st.session_state.selected_page = legacy_page
    page_name = st.session_state.get("selected_page", "Dashboard")
    section_name = st.session_state.get("selected_section") or _section_for_page(page_name)
    section_name, page_name = normalize_navigation_state(MENU_GROUPS, section_name, page_name)
    st.session_state.selected_section = section_name
    st.session_state.selected_page = page_name


def go_to_page(section_name: str, page_name: str) -> None:
    target_section = section_name if section_name in MENU_GROUPS else _section_for_page(page_name)
    if page_name not in MENU_GROUPS.get(target_section, []):
        target_section = _section_for_page(page_name)
    if page_name not in PAGES:
        target_section = "START"
        page_name = "Dashboard"
    st.session_state["pending_navigation"] = {"section": target_section, "page": page_name}
    st.rerun()


_sync_navigation_state()

with st.sidebar:
    st.header("Navigation")
    selected_mode = st.selectbox(
        "Workflow Mode",
        ["Full Pipeline", "Song Studio Only", "Seller Studio (Beta)"],
        index=["Full Pipeline", "Song Studio Only", "Seller Studio (Beta)"].index(
            st.session_state.get("workflow_mode", "Full Pipeline")
            if st.session_state.get("workflow_mode", "Full Pipeline") in ["Full Pipeline", "Song Studio Only", "Seller Studio (Beta)"]
            else "Full Pipeline"
        ),
        key="workflow_mode_selector",
        help="Song Studio Only = fast minimal songwriting workflow. Full Pipeline = complete release/content workflow. Seller Studio = short-form seller content workflow.",
    )
    if selected_mode == "Song Studio Only":
        st.caption("Song Studio Only hides Creator Wizard and advanced pipeline tools for a faster songwriting workflow.")
    elif selected_mode == "Seller Studio (Beta)":
        st.caption("Seller Studio focuses on TikTok/Reels/Shorts product content and hides music pipeline tools.")
    else:
        st.caption("Full Pipeline enables Creator Wizard and full release workflow tools.")
    if selected_mode != st.session_state.get("workflow_mode"):
        st.session_state.workflow_mode = selected_mode
        save_user_preferences({"workflow_mode": selected_mode})
        if not st.session_state.get("current_project") and _fix_display_text((st.session_state.project or {}).get("title", "")) in SONG_DEFAULT_TITLES:
            st.session_state.project = new_project(_workflow_default_name(selected_mode), DEFAULT_ARTIST, workflow_type_for_mode(selected_mode))
        if selected_mode == "Song Studio Only" and st.session_state.selected_page not in SONG_ONLY_ALLOWED_PAGES:
            st.session_state["pending_navigation"] = {"section": "START", "page": "Dashboard"}
        if selected_mode == "Seller Studio (Beta)" and st.session_state.selected_page not in SELLER_STUDIO_ALLOWED_PAGES:
            st.session_state["pending_navigation"] = {"section": "SELLER", "page": "Seller Studio"}
        st.rerun()
    group = st.selectbox("Section", list(MENU_GROUPS), key="selected_section")
    group_pages = MENU_GROUPS[group]
    if st.session_state.selected_page not in group_pages:
        st.session_state.selected_page = group_pages[0]
    page = st.radio("Menu", group_pages, label_visibility="collapsed", key="selected_page", format_func=page_label)
    st.divider()
    st.write("Current Project")
    current_workflow_mode = st.session_state.get("workflow_mode", "Full Pipeline")
    current_session_label = session_label_for_mode(current_workflow_mode)
    managed_projects = list_managed_projects(workflow_mode=current_workflow_mode)
    selected_recent = current_session_label
    if managed_projects:
        recent_options = [current_session_label] + [item["path"] for item in managed_projects]
        selected_recent = st.selectbox(
            "Project",
            recent_options,
            format_func=lambda value: current_session_label if value == current_session_label else next((item["display_name"] for item in managed_projects if item["path"] == value), value),
            key="sidebar_project_selector",
        )
        if st.button("Load Project", use_container_width=True, disabled=selected_recent == current_session_label):
            loaded_project = _safe("Load project", _load_managed_project, selected_recent)
            if isinstance(loaded_project, dict) and loaded_project.get("title"):
                st.session_state.project = loaded_project
                st.session_state.current_project = selected_recent
                st.rerun()
    else:
        st.info("No seller campaigns yet." if current_workflow_mode == "Seller Studio (Beta)" else "No songs yet. Create your first VelaFlow project.")
        st.caption(project.get("title", "project") if "project" in st.session_state else "No recent projects")
    current_info = None
    if selected_recent != current_session_label:
        current_info = next((item for item in managed_projects if item["path"] == selected_recent), None)
    elif project.get("title"):
        active_name = safe_name(project.get("title", "project"))
        current_info = next((item for item in managed_projects if item["project_name"] == active_name), None)
    with st.expander("Project Info", expanded=False):
        st.caption(f"Status: {'Active' if current_info else 'Current Session'}")
        st.caption(f"Workflow Mode: {st.session_state.get('workflow_mode', 'Full Pipeline')}")
        st.caption(f"Project Type: {(current_info or project).get('workflow_type') or (current_info or project).get('project_type') or '-'}")
        if current_info:
            st.caption(f"Last Modified: {current_info.get('last_modified', '')}")
            st.caption(f"Artist Preset: {current_info.get('artist_preset') or '-'}")
        else:
            st.caption("Last Modified: unsaved session")
            st.caption(f"Artist Preset: {(project.get('song', {}) or {}).get('artist_preset', '-')}")
    if st.button("Refresh Project List", use_container_width=True):
        st.rerun()
    with st.expander("Project Management", expanded=False):
        new_name = st.text_input("New Project Name", value="", key="sidebar_new_project_name")
        if st.button("New Project", use_container_width=True, key="sidebar_new_project_btn"):
            result = create_managed_project(new_name or _workflow_default_name(current_workflow_mode), workflow_type=workflow_type_for_mode(current_workflow_mode))
            if result.get("ok"):
                st.session_state.project = result["data"]["project"]
                st.session_state.current_project = result["data"]["folder"]
                st.success("Project created")
                st.rerun()
            else:
                st.error(result.get("error") or result.get("message"))
        if managed_projects and selected_recent != current_session_label:
            selected_project_name = Path(selected_recent).name
            rename_to = st.text_input("Rename To", value="", key="sidebar_rename_project_name")
            if st.button("Rename Project", use_container_width=True, key="sidebar_rename_project_btn"):
                result = rename_project(selected_project_name, rename_to)
                if result.get("ok"):
                    st.session_state.current_project = result["data"]["folder"]
                    st.success("Project renamed")
                    st.toast("Project renamed")
                    st.rerun()
                else:
                    st.error(result.get("error") or result.get("message"))
            if st.button("Archive Project", use_container_width=True, key="sidebar_archive_project_btn"):
                result = archive_project(selected_project_name)
                archive_ok = bool(result.get("ok", False))
                if archive_ok:
                    if st.session_state.get("current_project") == selected_recent:
                        st.session_state.current_project = ""
                    st.success("Project archived")
                    st.toast("Project archived")
                    st.rerun()
                else:
                    st.error(result.get("error") or result.get("message"))
            confirm_delete = st.checkbox("Confirm delete", key="sidebar_delete_confirm")
            if st.button("Delete Project", use_container_width=True, key="sidebar_delete_project_btn"):
                if confirm_delete:
                    result = delete_project(selected_project_name, confirm=True)
                    if result.get("ok"):
                        if st.session_state.get("current_project") == selected_recent:
                            st.session_state.current_project = ""
                            st.session_state.project = new_project(_workflow_default_name(current_workflow_mode), DEFAULT_ARTIST, workflow_type_for_mode(current_workflow_mode))
                        st.success("Project deleted with backup")
                        st.toast("Project deleted")
                        st.rerun()
                    else:
                        st.error(result.get("error") or result.get("message"))
                else:
                    st.warning("Check Confirm delete before deleting.")
        elif not managed_projects:
            st.caption("No saved projects yet.")
    st.divider()
    with st.expander("License Status", expanded=False):
        st.caption(f"Package: {license_service.state.package}")
        st.caption(f"Expiry: {license_service.state.expires_at}")
        modules = [("Director", "director"), ("Motion", "motion"), ("Render", "render"), ("Clips", "clips"), ("Canvas", "canvas"), ("Marketing", "marketing")]
        st.caption(" | ".join(f"{'✅' if license_service.module_enabled(module) else '⚪'} {label}" for label, module in modules))
        st.caption(f"Build: {build_label()} / {BUILD_VERSION}")
        st.caption(f"Theme: {active_theme_name()}")
        st.caption(f"Render Profile: {st.session_state.render_profile}")
    if st.session_state.get("debug_mode", False):
        st.caption(f"Current Section: {st.session_state.selected_section}")
        st.caption(f"Current Page: {st.session_state.selected_page}")
    st.divider()
    with st.expander("Provider Status", expanded=False):
        st.caption(f"Gemini model: {settings.gemini_model}")
        st.success("Gemini API ready") if settings.gemini_api_key else st.warning("Offline fallback active")

if page == "Dashboard":
    _page_header("Dashboard", "Project overview, next step, and daily workflow shortcuts.", project)
    workflow_mode = st.session_state.get("workflow_mode", "Full Pipeline")
    is_seller_mode = workflow_mode == "Seller Studio (Beta)"
    status = build_seller_dashboard_status(project) if is_seller_mode else build_project_status(project)
    status_data = status.get("data", {}) or {}
    next_step = status.get("next_step", {}) or {}
    audit = {} if is_seller_mode else run_full_project_audit(project)
    c1, c2, c3, c4 = st.columns(4)
    if is_seller_mode:
        c1.metric("Campaign", status_data.get("campaign_name") or _seller_campaign_name(project))
        c2.metric("Product", status_data.get("product_name") or "No product selected")
        c3.metric("Content Items", status_data.get("content_items", 0))
        c4.metric("Next Step", next_step.get("stage", "Seller Content"))
        st.caption(f"Workflow Mode: {workflow_mode} | Seller package: {status.get('message', '')} | Build {APP_VERSION}")
    else:
        c1.metric("Project", project.get("title", "project"))
        c2.metric("Artist", project.get("artist", DEFAULT_ARTIST))
        c3.metric("Scenes", len((project.get("mv", {}) or {}).get("storyboard", []) or []))
        c4.metric("Next Step", next_step.get("stage", "Song"))
        current_artist_preset = (project.get("song", {}) or {}).get("artist_preset") or st.session_state.get("selected_artist_preset") or load_default_artist_id()
        st.caption(
            f"Workflow Mode: {workflow_mode} | "
            f"Artist Preset: {current_artist_preset} | Build {APP_VERSION} | {project.get('version', 'legacy project')}"
        )
    action_cols = st.columns([1.2, 1, 1, 1])
    if action_cols[0].button(f"Continue: {next_step.get('label', 'Next Step')}", type="primary", use_container_width=True):
        target = next_step.get("page", "Seller Studio" if is_seller_mode else "Song Studio")
        target = target if target in PAGES else ("Seller Studio" if is_seller_mode else "Song Studio")
        go_to_page(_section_for_page(target), target)
    if action_cols[1].button("Save Project", use_container_width=True):
        _save_project()
        st.success("Project saved")
    if action_cols[2].button("Export Report", use_container_width=True):
        st.json(export_project_report(project), expanded=False)
    if action_cols[3].button("Clean Safe Temp", use_container_width=True):
        st.json(clean_safe_temp_files(project), expanded=False)
    st.write("Seller Status" if is_seller_mode else "Project Status")
    st.dataframe(pd.DataFrame(status_data.get("stages", []) or []), use_container_width=True, height=220)
    cols = st.columns(6)
    navs = [("Seller Studio", "Seller Studio"), ("System Health", "System Health"), ("AI Settings", "AI Settings")] if is_seller_mode else [
        ("Song Studio", "Song Studio"),
        ("Song Library", "Song Library"),
        ("Artist Preset Manager", "Artist Preset Manager"),
        ("MV Director", "MV Director"),
        ("Image Review", "Image Review"),
        ("Render Lab", "Render Lab"),
        ("Final Package", "Final Package"),
    ]
    navs = [(label, target) for label, target in navs if target in PAGES][:6]
    for col, (label, target) in zip(cols, navs):
        if col.button(page_label(label), use_container_width=True):
            go_to_page(_section_for_page(target), target)
    if is_seller_mode:
        with st.expander("Seller Export Snapshot", expanded=False):
            seller = (project.get("seller_studio", {}) or {}).get("content_package", {}) or {}
            export_data = (project.get("seller_studio", {}) or {}).get("export", {}) or {}
            st.caption(f"Caption ready: {'yes' if seller.get('caption') else 'no'}")
            st.caption(f"TXT package: {export_data.get('txt_path') or 'not exported'}")
    else:
        with st.expander("Recent Projects", expanded=False):
            st.dataframe(pd.DataFrame(list_recent_projects()), use_container_width=True)
        with st.expander("Production Audit Snapshot", expanded=False):
            a1, a2, a3 = st.columns(3)
            a1.metric("Audit Score", audit.get("data", {}).get("score", 0))
            a2.metric("Verdict", audit.get("data", {}).get("verdict", ""))
            a3.metric("Ready", "yes" if audit.get("data", {}).get("ready_for_final_render") else "no")
            st.dataframe(pd.DataFrame(audit.get("data", {}).get("fix_first", [])), use_container_width=True, height=160)
    with st.expander("Release Hardening Snapshot", expanded=False):
        st.json(project_lock_status(project), expanded=False)
        if st.button("Export Diagnostics"):
            st.json(export_diagnostic_bundle(project), expanded=False)

elif page == "Seller Studio":
    _page_header("Seller Studio", "Generate short-form TikTok, Reels, and affiliate seller content from product details.", project)
    st.caption("Beta workflow: no scraping, no auto posting, no video rendering. This creates a ready-to-copy content package.")
    c1, c2 = st.columns([1, 1])
    with c1:
        product_name = st.text_input("Product Name", value=st.session_state.get("seller_product_name", ""), help="ชื่อสินค้าหรือชื่อรุ่นที่ต้องการทำคอนเทนต์ขาย")
        product_category = st.text_input("Product Category", value=st.session_state.get("seller_product_category", ""), help="หมวดหมู่สินค้า เช่น skincare, gadget, home item")
        target_audience = st.text_input("Target Audience", value=st.session_state.get("seller_target_audience", ""), help="กลุ่มคนที่อยากขายให้ เช่น นักเรียน คนทำงาน หรือสายเดินทาง")
        uploaded_image = st.file_uploader("Product Image", type=["jpg", "jpeg", "png", "webp"], help="อัปโหลดรูปสินค้าเพื่อเก็บไว้เป็น reference สำหรับ prompt และ shot ideas")
        product_image_meta = (project.get("seller_studio", {}) or {}).get("product_image", {}) or {}
        if uploaded_image:
            product_image_meta = _save_seller_product_image(project, uploaded_image)
            project.setdefault("seller_studio", {})["product_image"] = product_image_meta
            _save_project()
            st.success("Product image saved")
        if product_image_meta.get("path") and Path(product_image_meta["path"]).is_file():
            st.image(product_image_meta["path"], caption=product_image_meta.get("original_filename") or product_image_meta.get("filename") or "Product image", use_container_width=True)
            st.caption("Product image attached. Use visual details from the image for shot ideas, thumbnail prompt, and video prompt.")
    with c2:
        tone_options = list(TONE_GUIDES)
        tone_style = st.selectbox("Tone Style", tone_options, index=0, help="เลือกน้ำเสียงของคลิปให้เหมาะกับสินค้าและกลุ่มผู้ชม")
        key_points = st.text_area(
            "Key Selling Points",
            value=st.session_state.get("seller_key_points", ""),
            height=140,
            help="ใส่จุดขายทีละบรรทัด เช่น ใช้ง่าย ประหยัดเวลา เห็นผลไว คุ้มราคา",
        )
        st.info(TONE_GUIDES.get(tone_style, ""), icon="ℹ️")

    if st.button("Generate Seller Content", type="primary", use_container_width=True):
        product_image_meta = (project.get("seller_studio", {}) or {}).get("product_image", {}) or {}
        result = generate_seller_content(product_name, product_category, target_audience, key_points, tone_style, product_image=product_image_meta)
        if result.get("ok"):
            package = result["data"]
            st.session_state.seller_product_name = package.get("product_name", "")
            st.session_state.seller_product_category = package.get("product_category", "")
            st.session_state.seller_target_audience = package.get("target_audience", "")
            st.session_state.seller_key_points = "\n".join(package.get("key_selling_points", []))
            project.setdefault("seller_studio", {})["product_image"] = package.get("product_image", product_image_meta)
            project.setdefault("seller_studio", {})["content_package"] = package
            export_result = export_seller_content(project.get("title") or package.get("product_name"), package)
            project["seller_studio"]["export"] = export_result.get("data", {})
            _save_project()
            st.success("Seller content package generated")
            if export_result.get("ok"):
                st.caption(f"Export: {export_result['data'].get('txt_path')}")
            else:
                st.warning(export_result.get("message", "Export failed"))
        else:
            st.error(result.get("error") or result.get("message", "Seller content generation failed"))

    seller_package = ((project.get("seller_studio", {}) or {}).get("content_package") or st.session_state.get("seller_content_package") or {})
    if seller_package:
        st.write("Seller Content Package")
        t1, t2, t3 = st.tabs(["Content", "Video Prompt", "Export"])
        with t1:
            st.markdown("**TikTok Hooks**")
            for item in seller_package.get("tiktok_hooks", []):
                st.write(f"- {item}")
            st.markdown("**Short Video Script**")
            st.markdown("15 seconds")
            for idx, item in enumerate(seller_package.get("script_15s", []) or seller_package.get("short_video_script", []), start=1):
                st.write(f"{idx}. {item}")
            st.markdown("30 seconds")
            for idx, item in enumerate(seller_package.get("script_30s", []) or seller_package.get("short_video_script", []), start=1):
                st.write(f"{idx}. {item}")
            st.markdown("60 seconds")
            for idx, item in enumerate(seller_package.get("script_60s", []), start=1):
                st.write(f"{idx}. {item}")
            st.markdown("**CTA Suggestions**")
            for item in seller_package.get("cta_suggestions", []):
                st.write(f"- {item}")
            st.text_area("Caption", value=seller_package.get("caption", ""), height=90)
            st.text_area("Hashtags", value=" ".join(seller_package.get("hashtags", [])), height=80)
        with t2:
            st.text_area("AI Video Prompt", value=seller_package.get("ai_video_prompt", ""), height=140)
            st.text_area("Thumbnail Prompt", value=seller_package.get("thumbnail_prompt", ""), height=120)
            image_data = seller_package.get("product_image", {}) or {}
            if image_data.get("path"):
                st.caption(f"Product image reference: {image_data.get('path')}")
            st.markdown("**B-roll Shot Ideas**")
            for item in seller_package.get("broll_shot_ideas", []):
                st.write(f"- {item}")
        with t3:
            export_text = seller_content_to_text(seller_package)
            export_path = ((project.get("seller_studio", {}) or {}).get("export") or {}).get("txt_path")
            if export_path:
                st.caption(f"Export path: {export_path}")
            st.download_button(
                "Download seller_content_package.txt",
                data=export_text.encode("utf-8"),
                file_name="seller_content_package.txt",
                mime="text/plain",
                use_container_width=True,
            )
            st.text_area("Copy-ready package", value=export_text, height=260)

elif page == "Creator Wizard":
    _page_header("Creator Wizard", "Guided creative setup for starting a song idea before Song Studio.", project)
    artist_presets = list_artist_presets() or [get_artist_preset(load_default_artist_id())]
    preset_ids = [item.get("artist_id", "vela_moon") for item in artist_presets]
    default_artist = st.session_state.get("selected_artist_preset") or load_default_artist_id()
    preset_index = preset_ids.index(default_artist) if default_artist in preset_ids else 0

    c1, c2 = st.columns([1, 1])
    with c1:
        project_name = st.text_input("Project Name", value=project.get("title", ""), key="wizard_project_name")
        topic = st.selectbox("Step 1: Song Topic", TOPIC_OPTIONS, key="wizard_topic_select")
        custom_topic = st.text_input("Custom Topic", value="", disabled=topic != "Custom", key="wizard_custom_topic")
        mood_choice = st.selectbox("Step 2: Mood", MOOD_OPTIONS, index=0, key="wizard_mood_select")
        music_direction = st.selectbox("Step 3: Music Direction", MUSIC_DIRECTION_OPTIONS, index=0, key="wizard_music_direction_select")
    with c2:
        selected_preset_label = st.selectbox(
            "Step 4: Artist Preset",
            [_artist_preset_label(item) for item in artist_presets],
            index=preset_index,
            key="wizard_artist_preset_select",
        )
        selected_preset = artist_presets[[_artist_preset_label(item) for item in artist_presets].index(selected_preset_label)]
        structure_presets = list_structure_presets()
        structure_labels = [item.get("name", item.get("preset_id", "")) for item in structure_presets] or ["Vela Moon Pop Rock"]
        default_structure_index = next((idx for idx, item in enumerate(structure_presets) if item.get("preset_id") == "vela_moon_pop_rock"), 0)
        selected_structure_label = st.selectbox("Step 5: Song Structure", structure_labels, index=default_structure_index, key="wizard_structure_preset_select")
        selected_structure = structure_presets[structure_labels.index(selected_structure_label)] if structure_presets else get_structure_preset("vela_moon_pop_rock")
        target_platform = st.selectbox("Step 6: Target Platform", TARGET_PLATFORM_OPTIONS, index=5, key="wizard_target_platform_select")
        fallback_name = suggest_project_name(topic, custom_topic)
        st.caption(f"Fallback project name: {fallback_name}")
        if st.button("Generate Creative Direction", type="primary", use_container_width=True):
            direction = generate_creative_direction(
                topic=topic,
                custom_topic=custom_topic,
                mood=mood_choice,
                music_direction=music_direction,
                artist_preset_id=selected_preset.get("artist_id"),
                target_platform=target_platform,
            )
            st.session_state.creative_direction = direction
            st.session_state.wizard_topic = direction.get("topic", "")
            st.session_state.wizard_mood = mood_choice
            st.session_state.wizard_music_direction = music_direction
            st.session_state.wizard_target_platform = target_platform
            st.success("Creative direction generated")

    direction = st.session_state.get("creative_direction", {}) or project.get("creative_direction", {}) or {}
    structure_context = {
        **(direction or {}),
        "topic": (direction or {}).get("topic") or (custom_topic if topic == "Custom" else topic),
        "mood": mood_choice,
        "music_direction": music_direction,
        "artist_preset": selected_preset.get("artist_id", "vela_moon"),
        "target_platform": target_platform,
    }
    structure_preview = create_structure_plan(structure_context, selected_structure.get("preset_id"), selected_preset)
    with st.expander("Song Structure Preview", expanded=True):
        st.caption(f"Hook placement: {structure_preview.get('recommended_hook_placement', '')}")
        st.caption(f"Emotional arc: {structure_preview.get('emotional_arc', '')}")
        st.dataframe(pd.DataFrame(_structure_energy_rows(structure_preview)), use_container_width=True, height=220)
    if direction:
        st.write("Creative Direction")
        st.json(direction, expanded=False)
        if st.button("Use This Direction in Song Studio", type="primary", use_container_width=True):
            title = project_name.strip() or suggest_project_name(topic, custom_topic)
            if not project.get("title") or project.get("title") == "เพลงใหม่ของฉัน":
                project["title"] = title
            else:
                project["title"] = project_name.strip() or project.get("title", title)
            project["artist"] = selected_preset.get("artist_name", DEFAULT_ARTIST)
            project["creative_direction"] = direction
            structure_plan = create_structure_plan(structure_context, selected_structure.get("preset_id"), selected_preset)
            project["song_structure_plan"] = structure_plan
            project.setdefault("settings", {})["render_profile"] = direction.get("suggested_render_profile", "Cinematic")
            project.setdefault("settings", {})["subtitle_style"] = direction.get("suggested_subtitle_style", "cinematic")
            project.setdefault("song", {})["artist_preset"] = direction.get("artist_preset", selected_preset.get("artist_id", "vela_moon"))
            project.setdefault("song", {})["song_structure_plan"] = structure_plan
            save_result = save_creative_direction(project.get("title", title), direction)
            save_structure_plan(project.get("title", title), structure_plan)
            _save_project()
            st.session_state.selected_artist_preset = direction.get("artist_preset", selected_preset.get("artist_id", "vela_moon"))
            st.session_state.song_idea = direction.get("project_concept", "")
            st.session_state.creative_direction = direction
            st.session_state.song_structure_plan = structure_plan
            st.success(f"Creative direction saved: {save_result.get('data', {}).get('path', '')}")
            go_to_page("SONG", "Song Studio")

    with st.expander("Advanced: Apply Project Template", expanded=False):
        templates = list_project_templates()
        names = [item.get("name", "Template") for item in templates] or ["Blank"]
        selected = st.selectbox("Project Template", names)
        title = st.text_input("New Project Title", value=project.get("title", "เพลงใหม่ของฉัน"))
        if st.button("Create / Apply Template", type="primary"):
            if selected != "Blank":
                st.session_state.project = create_project_from_template(title, selected)
            else:
                st.session_state.project = new_project(title, DEFAULT_ARTIST)
            _save_project()
            st.success("Project template applied")
        st.dataframe(pd.DataFrame(templates), use_container_width=True)

elif page == "Song Studio":
    _render_song_studio(project)

elif page == "Song Library":
    _page_header("Song Library", "Browse song projects, drafts, and Suno export readiness.", project)
    projects = list_managed_projects(workflow_mode="Song Studio Only")
    rows = [
        {
            "project_name": item.get("project_name", ""),
            "song_title": item.get("song_title", ""),
            "artist_preset": item.get("artist_preset", ""),
            "selected_hook": item.get("selected_hook", ""),
            "last_modified": item.get("last_modified", ""),
            "has_lyrics": item.get("has_lyrics", False),
            "suno_txt_ready": item.get("suno_txt_ready", False),
            "has_storyboard": item.get("has_storyboard", False),
            "has_render": item.get("has_render", False),
        }
        for item in projects
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, height=260)
    if not projects:
        st.info("No songs yet. Create your first VelaFlow project in Song Studio.")
    else:
        project_names = [item["project_name"] for item in projects]
        selected_project = st.selectbox("Song Project", project_names, key="song_library_project")
        selected_summary = next((item for item in projects if item["project_name"] == selected_project), projects[0])
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        if c1.button("Open in Song Studio", use_container_width=True):
            loaded = _safe("Load project", _load_managed_project, selected_summary["path"])
            if isinstance(loaded, dict) and loaded.get("title"):
                st.session_state.project = loaded
                st.session_state.current_project = selected_summary["path"]
                go_to_page("SONG", "Song Studio")
        if c2.button("Continue to MV Director", use_container_width=True):
            loaded = _safe("Load project", _load_managed_project, selected_summary["path"])
            if isinstance(loaded, dict) and loaded.get("title"):
                st.session_state.project = loaded
                st.session_state.current_project = selected_summary["path"]
                if st.session_state.get("workflow_mode") == "Song Studio Only":
                    st.session_state.workflow_mode = "Full Pipeline"
                    save_user_preferences({"workflow_mode": "Full Pipeline"})
                st.session_state["pending_navigation"] = {"section": "VISUAL", "page": "MV Director"}
                st.rerun()
        if c3.button("Archive", use_container_width=True):
            result = archive_project(selected_project)
            if result.get("ok"):
                st.success("Project archived")
                st.toast("Project archived")
                st.rerun()
            else:
                st.error(result.get("error") or result.get("message"))
        confirm_library_delete = c4.checkbox("Confirm", key="song_library_delete_confirm")
        if c4.button("Delete", use_container_width=True):
            result = delete_project(selected_project, confirm=confirm_library_delete)
            if result.get("ok"):
                st.success("Project deleted with backup")
                st.toast("Project deleted")
                st.rerun()
            else:
                st.warning(result.get("message", "Delete requires confirmation"))
        if c5.button("Export Lyrics", use_container_width=True):
            folder = Path(selected_summary["path"])
            song = json.loads((folder / "song.json").read_text(encoding="utf-8")) if (folder / "song.json").is_file() else {}
            lyrics = song.get("normalized_song_output") or song.get("complete_lyrics") or ((folder / "lyrics.txt").read_text(encoding="utf-8") if (folder / "lyrics.txt").is_file() else "")
            export_dir = ROOT / "outputs" / "song_library_exports" / selected_project
            export_dir.mkdir(parents=True, exist_ok=True)
            export_path = export_dir / "lyrics.txt"
            export_path.write_text(lyrics, encoding="utf-8")
            st.success(f"Lyrics exported: {export_path}")
        if c6.button("View Drafts", use_container_width=True):
            st.session_state.song_library_show_drafts = selected_project
        if st.session_state.get("song_library_show_drafts") == selected_project:
            st.write("Drafts")
            st.dataframe(pd.DataFrame(list_song_drafts(selected_project)), use_container_width=True)
        with st.expander("Archived Projects", expanded=False):
            st.dataframe(pd.DataFrame(list_archived_projects()), use_container_width=True)

elif page == "MV Director":
    _page_header("MV Director", "Turn lyrics into a storyboard and scene plan.", project)
    title = st.text_input("Song Title", value=project.get("title", "เพลงใหม่ของฉัน"))
    artist = st.text_input("Artist", value=project.get("artist", DEFAULT_ARTIST), key="mv_artist")
    lyrics = st.text_area("Lyrics", value=_current_lyrics(), height=320)
    style = st.text_input("Visual Style", value="cinematic emotional Thai pop rock MV")
    scene_count = st.slider("Scene Count", 4, 32, 12)
    c1, c2 = st.columns(2)
    if c1.button("Generate MV Director Plan", type="primary"):
        mv = _safe("Generate MV", analyze_song_with_gemini, settings.gemini_api_key, settings.gemini_model, title, artist, lyrics, style, "balanced", scene_count=scene_count)
        if mv.get("storyboard") is not None:
            project["title"] = title
            project["artist"] = artist
            project["mv"] = mv
            st.session_state.storyboard = mv.get("storyboard", [])
            _save_project()
            st.success("MV plan generated")
    if c2.button("Generate MV Storyboard", use_container_width=True):
        song_context = dict(project.get("song", {}) or {})
        song_context.setdefault("title", title)
        song_context.setdefault("normalized_song_output", lyrics)
        song_context.setdefault("genre", style)
        storyboard_result = generate_mv_storyboard(song_context, project, scene_count=min(10, max(5, int(scene_count or 8))))
        if storyboard_result.get("ok"):
            metadata = storyboard_result["data"].get("metadata", {})
            storyboard = storyboard_result["data"].get("storyboard", [])
            project["title"] = title
            project["artist"] = artist
            project.setdefault("mv", {})["storyboard"] = storyboard
            project["mv"]["mv_storyboard_metadata"] = metadata
            export_result = export_mv_storyboard(title, storyboard, metadata)
            project["mv"]["mv_storyboard_export"] = export_result.get("data", {})
            st.session_state.storyboard = storyboard
            _save_project()
            st.success("MV storyboard generated")
            if export_result.get("ok"):
                st.caption(f"Export: {export_result['data'].get('txt_path')}")
            else:
                st.warning(export_result.get("message", "Storyboard export failed"))
        else:
            st.error(storyboard_result.get("error") or storyboard_result.get("message", "Storyboard generation failed"))
    storyboard_export = ((project.get("mv", {}) or {}).get("mv_storyboard_export") or {}).get("txt_path")
    if storyboard_export:
        st.caption(f"Latest storyboard export: {storyboard_export}")
    st.dataframe(pd.DataFrame((project.get("mv", {}) or {}).get("storyboard", []) or []), use_container_width=True, height=360)

elif page == "Character Studio":
    st.subheader("Character Studio")
    char = normalize_character(project.get("character", {}) or {})
    c1, c2, c3 = st.columns(3)
    char["name"] = c1.text_input("Character Name", value=char.get("name", ""))
    char["gender"] = c2.selectbox("Gender", ["male", "female", "non-binary", "unspecified"], index=["male", "female", "non-binary", "unspecified"].index(char.get("gender", "male") if char.get("gender", "male") in ["male", "female", "non-binary", "unspecified"] else "male"))
    char["hair"] = c3.text_input("Hair", value=char.get("hair", "short black hair"))
    char["outfit"] = st.text_input("Outfit", value=char.get("outfit", "dark hoodie"))
    char["mood"] = st.text_input("Mood", value=char.get("mood", "lonely expression"))
    char["reference_notes"] = st.text_area("Reference Notes", value=char.get("reference_notes", ""), height=120)
    if st.button("Save Character / Apply To Storyboard", type="primary"):
        project["character"] = char
        project["mv"] = apply_character_to_storyboard(project.get("mv", {}) or {}, char)
        _save_project()
        st.success("Character saved")
    st.code(build_character_prompt(char), language="text")

elif page == "Image Lab":
    st.subheader("Image Lab")
    storyboard = (project.get("mv", {}) or {}).get("storyboard", []) or []
    scene_options = [str(item.get("scene", idx + 1)) for idx, item in enumerate(storyboard)] or ["1"]
    scene_id = st.selectbox("Scene", scene_options)
    scene = next((item for item in storyboard if str(item.get("scene")) == scene_id), {})
    prompt = st.text_area("Image Prompt", value=scene.get("image_prompt") or scene.get("expanded_prompt") or "", height=180)
    provider = st.selectbox("Image Provider", ["offline", "manual", "flux", "sdxl", "openai_images"], index=0)
    if st.button("Generate Image Placeholder", type="primary"):
        out = ROOT / "outputs" / "generated_images" / safe_name(project.get("title", "project")) / f"scene_{scene_id}.png"
        _safe("Generate image", generate_image, provider, prompt, str(out), {"scene": scene_id})
        project["assets"].setdefault("images", {})[scene_id] = str(out)
        _save_project()
        st.success(f"Image saved: {out}")
    st.json(project.get("assets", {}).get("images", {}), expanded=False)

elif page == "Image Review":
    st.subheader("Image Review")
    images = project.get("assets", {}).get("images", {}) or {}
    approved = project.get("assets", {}).setdefault("approved_images", {})
    rejected = project.get("assets", {}).setdefault("rejected_images", {})
    rows = [{"scene": scene, "path": path, "approved": scene in approved, "rejected": scene in rejected} for scene, path in images.items()]
    st.dataframe(pd.DataFrame(rows), use_container_width=True)
    scene = st.selectbox("Review Scene", list(images.keys()) or [""])
    if scene:
        st.caption(images.get(scene, ""))
        c1, c2 = st.columns(2)
        if c1.button("Approve Image"):
            approved[scene] = images[scene]
            rejected.pop(scene, None)
            _save_project()
            st.success("Approved")
        if c2.button("Reject Image"):
            rejected[scene] = images[scene]
            approved.pop(scene, None)
            _save_project()
            st.warning("Rejected")

elif page == "Video Lab":
    st.subheader("Video Lab")
    scene = st.text_input("Scene ID", value="1")
    prompt = st.text_area("Video Prompt", height=140)
    image_path = st.text_input("Source Image Path", value=(project.get("assets", {}).get("approved_images", {}) or {}).get(scene, ""))
    provider = st.selectbox("Video Provider", ["offline", "manual", "kling", "runway", "luma"], index=0)
    if st.button("Generate Video Slot / Placeholder", type="primary"):
        out = ROOT / "outputs" / "generated_videos" / safe_name(project.get("title", "project")) / f"scene_{scene}.mp4"
        _safe("Generate video", generate_video, provider, prompt, image_path, str(out), {"scene": scene})
        project["assets"].setdefault("videos", {})[scene] = str(out)
        _save_project()
        st.success(f"Video slot saved: {out}")
    st.json(project.get("assets", {}).get("videos", {}), expanded=False)

elif page == "Render Lab":
    _page_header("Render Lab", "Render approved scenes, subtitles, and motion into video outputs.", project)
    c1, c2, c3 = st.columns(3)
    profile = c1.selectbox("Render Profile", list(RENDER_PROFILES.keys()), index=list(RENDER_PROFILES.keys()).index(st.session_state.render_profile) if st.session_state.render_profile in RENDER_PROFILES else 0)
    aspects = c2.multiselect("Aspect Ratios", ["16:9", "9:16", "1:1"], default=["16:9"])
    subtitle_mode = c3.selectbox("Subtitle Mode", ["none", "simple", "karaoke", "tiktok", "cinematic"], index=1)
    audio_path = st.text_input("Audio Path", value=(project.get("assets", {}) or {}).get("audio_path", ""))
    st.session_state.render_profile = profile
    with st.expander("Preview / Advanced Render Controls", expanded=False):
        st.caption("Use preview before expensive full render. Clip Factory remains available from Production.")
        st.selectbox("Motion Style", ["auto", "still", "cinematic_drift", "slow_zoom_in", "slow_zoom_out", "hook_energy_zoom"], key="render_motion_style")
        st.selectbox("Transition Style", ["none", "fade", "blur dissolve", "flash cut", "emotional dip to black"], key="render_transition_style")
        if st.button("Open Clip Factory"):
            go_to_page("PRODUCTION", "Smart Clip Factory")
    if st.button("Pre-render Healthcheck"):
        st.json(run_pre_render_healthcheck(project), expanded=False)
    if st.button("Render Now", type="primary"):
        result = _safe("Render", run_render, project, {"render_profile": profile, "aspect_ratios": aspects, "subtitle_mode": subtitle_mode, "audio_path": audio_path, "ffmpeg_path": settings.ffmpeg_path})
        project.setdefault("runtime", {})["last_render_dir"] = result.get("data", {}).get("render_dir", "")
        _save_project()
        st.json(result, expanded=False)
    latest = _latest_render_dir(project)
    st.caption(f"Latest render folder: {latest}")
    if st.button("Recover Render Temp"):
        st.json(recover_render_temp(latest), expanded=False)

elif page == "Smart Clip Factory":
    _page_header("Clip Factory", "Create short-form clips, hook clips, and teaser exports.", project)
    latest = _latest_render_dir(project)
    source_video = st.text_input("Source Final Render", value=str(latest / "final_9x16.mp4"))
    clip_type = st.selectbox("Clip Type", list(CLIP_TYPES.keys()))
    preview = st.checkbox("Preview Mode", value=True)
    if st.button("Generate Clip", type="primary"):
        st.json(generate_clip(project, source_video, latest, clip_type, settings.ffmpeg_path, preview=preview), expanded=False)
    if st.button("Generate Full Clip Set"):
        st.json(generate_clip_set(project, source_video, latest, settings.ffmpeg_path, preview=preview), expanded=False)

elif page == "Marketing Package":
    _page_header("Marketing Package", "Build captions, descriptions, hashtags, and upload notes.", project)
    package = build_marketing_package(project)
    st.json(package.get("data", {}), expanded=False)
    if st.button("Export Marketing Package", type="primary"):
        st.json(export_marketing_package(project), expanded=False)

elif page == "Final Package":
    _page_header("Final Package", "Inspect and assemble the final release package.", project)
    render_dir = st.text_input("Render Folder", value=str(_latest_render_dir(project)))
    st.caption("Preflight checks run before packaging. A project backup is created before build.")
    st.dataframe(pd.DataFrame(inspect_final_package_inputs(project, render_dir).get("data", {}).get("checks", [])), use_container_width=True)
    if st.button("Build Final Release Package", type="primary"):
        backup_project(project, "before_final_package")
        st.json(build_final_release_package(project, ROOT / "outputs" / "final_packages" / safe_name(project.get("title", "project")), render_dir, zip_package=True), expanded=False)

elif page == "Creative Intelligence":
    _page_header("Creative Intelligence", "Review emotional arc, hooks, cinematic notes, and TikTok recommendations.", project)
    tabs = st.tabs(["Emotional Arc", "Hook Intelligence", "Cinematic Director", "Narrative & Performance", "Production Audit", "TikTok"])
    with tabs[0]:
        st.json(analyze_emotional_arc(project), expanded=False)
    with tabs[1]:
        st.json(analyze_hooks(project), expanded=False)
    with tabs[2]:
        st.dataframe(pd.DataFrame(score_project_scenes(project)), use_container_width=True)
    with tabs[3]:
        st.json(build_creative_suggestions(project), expanded=False)
    with tabs[4]:
        audit = run_full_project_audit(project)
        st.metric("Audit Score", audit.get("data", {}).get("score", 0))
        st.dataframe(pd.DataFrame(audit.get("data", {}).get("checks", [])), use_container_width=True, height=300)
    with tabs[5]:
        st.json(smart_tiktok_recommendations(project), expanded=False)

elif page == "Production Audit":
    _page_header("Quality Audit", "Run final quality checks before render or release.", project)
    audit = run_full_project_audit(project)
    st.metric("Audit Score", audit.get("data", {}).get("score", 0))
    st.write(audit.get("data", {}).get("verdict", ""))
    st.dataframe(pd.DataFrame(audit.get("data", {}).get("checks", [])), use_container_width=True, height=420)
    if st.button("Export Audit Report"):
        st.json(export_project_audit(project), expanded=False)

elif page == "Beta Test Mode":
    st.subheader("Beta Test Mode")
    sessions = list_beta_sessions(project)
    if st.button("New Beta Session", type="primary"):
        result = new_beta_session(project)
        st.session_state.beta_test_state["active"] = result.get("data", {}).get("session", {}).get("session_id", "")
        st.json(result, expanded=False)
    session_ids = [row["session_id"] for row in sessions]
    if session_ids:
        sid = st.selectbox("Beta Session", session_ids)
        loaded = load_beta_session(project, sid)
        session = loaded.get("data", {}).get("session", {})
        tabs = st.tabs(["Checklist", "Ratings", "Issues", "Compare Renders", "Report / Freeze"])
        with tabs[0]:
            st.dataframe(pd.DataFrame(beta_test_checklist(project, session).get("data", {}).get("checks", [])), use_container_width=True)
        with tabs[1]:
            ratings = {area: st.slider(area, 0, 10, int((session.get("ratings", {}) or {}).get(area, 0))) for area in BETA_RATING_AREAS}
            if st.button("Save Ratings"):
                st.json(update_beta_ratings(project, sid, ratings), expanded=False)
        with tabs[2]:
            area = st.selectbox("Area", BETA_RATING_AREAS)
            severity = st.selectbox("Severity", ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
            desc = st.text_input("Issue")
            if st.button("Add Issue", disabled=not desc):
                st.json(add_beta_issue(project, sid, area, severity, desc), expanded=False)
            st.dataframe(pd.DataFrame(session.get("issues", []) or []), use_container_width=True)
        with tabs[3]:
            a = st.text_input("Render A")
            b = st.text_input("Render B")
            if st.button("Compare", disabled=not (a and b)):
                st.dataframe(pd.DataFrame(compare_render_versions(a, b).get("data", {}).get("rows", [])), use_container_width=True)
        with tabs[4]:
            if st.button("Export Beta Test Report"):
                st.json(export_beta_report(project, sid), expanded=False)
            if st.button("Mark Build as Stable Candidate"):
                st.json(mark_stable_candidate(project, sid), expanded=False)
            if st.button("Create Stable Candidate Snapshot"):
                st.caption(STABLE_FREEZE_NAME)
                st.json(create_stable_candidate_snapshot(project, sid), expanded=False)
    st.dataframe(pd.DataFrame(sessions), use_container_width=True)

elif page == "Asset Intelligence":
    st.subheader("Asset Intelligence")
    summary = project_asset_summary(project)
    st.metric("Project Disk Usage", summary.get("total_size", "0 B"))
    st.dataframe(pd.DataFrame(summary.get("areas", [])), use_container_width=True)
    c1, c2, c3 = st.columns(3)
    if c1.button("Clear Temp Renders"):
        st.json(clear_temp_renders(project), expanded=False)
    if c2.button("Clear Rejected Images"):
        st.json(clear_rejected_images(project), expanded=False)
    if c3.button("Clear Image Cache"):
        st.json(clear_image_cache(), expanded=False)

elif page == "Queue Monitor":
    st.subheader("Queue Monitor")
    jobs = list_jobs()
    st.dataframe(pd.DataFrame(jobs), use_container_width=True, height=420)
    c1, c2 = st.columns(2)
    if c1.button("Clear Finished Jobs"):
        clear_finished_jobs()
        st.rerun()
    cancel_id = c2.text_input("Cancel Job ID")
    if st.button("Cancel Job", disabled=not cancel_id):
        cancel_job(cancel_id)
        st.warning("Cancel requested")

elif page == "System Health":
    _page_header("System Health", "Check local environment, folders, providers, and safe mode.", project)
    st.json(run_healthcheck(settings), expanded=False)
    project_path = st.text_input("Safe Mode Project JSON")
    if st.button("Open Safe Mode", disabled=not project_path):
        st.json(open_project_safe_mode(project_path), expanded=False)

elif page == "Release Hardening Tools":
    _page_header("Recovery Tools", "Project lock, diagnostics, safe cleanup, and recovery utilities.", project)
    st.json(project_lock_status(project), expanded=False)
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("Lock Project"):
        st.json(acquire_project_lock(project), expanded=False)
    if c2.button("Release Lock"):
        st.json(release_project_lock(project), expanded=False)
    if c3.button("Fix Common Issues"):
        result = fix_common_issues(project)
        st.session_state.project = result.get("data", {}).get("project", project)
        st.json(result, expanded=False)
    if c4.button("Export Diagnostics"):
        st.json(export_diagnostic_bundle(project), expanded=False)
    if st.button("Clean Safe Temp Files"):
        st.json(clean_safe_temp_files(project), expanded=False)
    if st.button("Duplicate Project / Save As"):
        st.json(duplicate_project(project, f"{project.get('title','project')} Copy"), expanded=False)

elif page == "AI Settings":
    st.subheader("AI Settings")
    st.write(f"Gemini model: {settings.gemini_model}")
    st.write("API key present:", bool(settings.gemini_api_key))
    st.caption("No payment, cloud sync, online license, full video AI, packaging, or watermark enforcement was added.")

elif page == "Artist Preset Manager":
    _render_artist_preset_manager()

