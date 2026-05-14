from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from core.artist_presets import get_artist_preset, list_artist_presets
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
from core.preset_system import list_project_templates
from core.project_io import load_project, new_project, safe_name, save_project, save_project_folder
from core.project_lock import acquire_project_lock, project_lock_status, release_project_lock
from core.project_templates import apply_template_to_project, create_project_from_template
from core.project_workflow import backup_project, build_project_status, clean_safe_temp_files, duplicate_project, export_project_report, list_recent_projects
from core.production_audit import export_project_audit, run_full_project_audit
from core.render_engine import run_render
from core.render_profiles import RENDER_PROFILES
from core.render_recovery import export_diagnostic_bundle, latest_failed_render, recover_render_temp
from core.safe_mode import open_project_safe_mode
from core.scene_scoring import score_project_scenes, smart_tiktok_recommendations
from core.settings import get_settings
from core.stable_build import STABLE_FREEZE_NAME, create_stable_candidate_snapshot
from core.theme import active_theme_name
from core.version import APP_VERSION, BUILD_VERSION, build_label
from providers.image_ai import generate_image
from providers.text_ai import analyze_song_with_gemini, generate_song_with_gemini
from providers.video_ai import generate_video


st.set_page_config(page_title=WINDOW_TITLE, page_icon="🎬", layout="wide")
settings = get_settings()
license_service = get_license_service()


def _ensure_state() -> None:
    defaults = {
        "project": new_project("เพลงใหม่ของฉัน", DEFAULT_ARTIST),
        "current_project": "",
        "selected_page": "Dashboard",
        "selected_artist_preset": "vela_moon",
        "render_profile": "Standard",
        "storyboard": [],
        "generated_song": {},
        "normalized_song_output": "",
        "queue_state": {},
        "job_state": {},
        "audit_state": {},
        "beta_test_state": {},
        "active_template": "",
        "active_preset_pack": "",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
    project = st.session_state.project
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


_ensure_state()
project = _project()

st.title(f"🎬 {APP_TITLE}")
st.caption(f"{PRODUCT_TAGLINE} by {BRAND_NAME} | V7.8.1c UI Polish Pass")

PAGE_MODULES = {
    "Dashboard": "core",
    "Creator Wizard": "core",
    "Song Studio": "director",
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
}
PAGES = list(PAGE_MODULES)
MENU_GROUPS = {
    "Start": ["Dashboard", "Creator Wizard", "Song Studio"],
    "Creation": ["MV Director", "Character Studio", "Image Lab", "Image Review", "Video Lab"],
    "Production": ["Render Lab", "Smart Clip Factory", "Queue Monitor"],
    "Intelligence": ["Creative Intelligence", "Production Audit", "Beta Test Mode", "Asset Intelligence"],
    "Export": ["Marketing Package", "Final Package"],
    "System": ["System Health", "Release Hardening Tools", "AI Settings"],
}

with st.sidebar:
    st.header("Navigation")
    current = st.session_state.get("selected_page", st.session_state.get("nav_page", "Dashboard"))
    current_group = next((name for name, items in MENU_GROUPS.items() if current in items), "Start")
    group = st.selectbox("Section", list(MENU_GROUPS), index=list(MENU_GROUPS).index(current_group), key="sidebar_group")
    group_pages = MENU_GROUPS[group]
    page = st.radio("Menu", group_pages, index=group_pages.index(current) if current in group_pages else 0, label_visibility="collapsed", key="sidebar_page")
    st.session_state.nav_page = page
    st.session_state.selected_page = page
    st.divider()
    st.write("Current Project")
    recent = list_recent_projects()
    if recent:
        recent_options = ["Current session"] + [item["path"] for item in recent]
        selected_recent = st.selectbox(
            "Project",
            recent_options,
            format_func=lambda value: "Current session" if value == "Current session" else next((item["title"] for item in recent if item["path"] == value), value),
            key="sidebar_project_selector",
        )
        if st.button("Load Project", use_container_width=True, disabled=selected_recent == "Current session"):
            loaded_project = _safe("Load project", load_project, selected_recent)
            if isinstance(loaded_project, dict) and loaded_project.get("title"):
                st.session_state.project = loaded_project
                st.session_state.current_project = selected_recent
                st.rerun()
    else:
        st.caption(project.get("title", "project") if "project" in st.session_state else "No recent projects")
    st.divider()
    st.write("License Status")
    st.caption(f"Package: {license_service.state.package}")
    st.caption(f"Expiry: {license_service.state.expires_at}")
    for label, module in [("Director", "director"), ("Motion", "motion"), ("Render", "render"), ("Clips", "clips"), ("Canvas", "canvas"), ("Marketing", "marketing")]:
        st.caption(f"{'✅' if license_service.module_enabled(module) else '⚪'} {label}")
    st.caption(f"Build: {build_label()} / {BUILD_VERSION}")
    st.caption(f"Theme: {active_theme_name()}")
    st.caption(f"Render Profile: {st.session_state.render_profile}")
    st.divider()
    st.write("Provider Status")
    st.caption(f"Gemini model: {settings.gemini_model}")
    st.success("Gemini API ready") if settings.gemini_api_key else st.warning("Offline fallback active")

if page == "Dashboard":
    st.subheader("Dashboard")
    status = build_project_status(project)
    status_data = status.get("data", {}) or {}
    next_step = status.get("next_step", {}) or {}
    audit = run_full_project_audit(project)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Project", project.get("title", "project"))
    c2.metric("Artist", project.get("artist", DEFAULT_ARTIST))
    c3.metric("Scenes", len((project.get("mv", {}) or {}).get("storyboard", []) or []))
    c4.metric("Next Step", next_step.get("stage", "Song"))
    st.caption(f"Build {APP_VERSION} | {project.get('version', 'legacy project')}")
    action_cols = st.columns([1.2, 1, 1, 1])
    if action_cols[0].button(f"Continue: {next_step.get('label', 'Next Step')}", type="primary", use_container_width=True):
        target = next_step.get("page", "Song Studio")
        st.session_state.selected_page = target if target in PAGES else "Song Studio"
        st.session_state.nav_page = st.session_state.selected_page
        st.rerun()
    if action_cols[1].button("Save Project", use_container_width=True):
        _save_project()
        st.success("Project saved")
    if action_cols[2].button("Export Report", use_container_width=True):
        st.json(export_project_report(project), expanded=False)
    if action_cols[3].button("Clean Safe Temp", use_container_width=True):
        st.json(clean_safe_temp_files(project), expanded=False)
    st.write("Project Status")
    st.dataframe(pd.DataFrame(status_data.get("stages", []) or []), use_container_width=True, height=220)
    cols = st.columns(5)
    navs = [("Song Studio", "Song Studio"), ("MV Director", "MV Director"), ("Image Review", "Image Review"), ("Render Lab", "Render Lab"), ("Final Package", "Final Package")]
    for col, (label, target) in zip(cols, navs):
        if col.button(label, use_container_width=True):
            st.session_state.nav_page = target
            st.rerun()
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

elif page == "Creator Wizard":
    st.subheader("Creator Wizard")
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
    st.subheader("Song Studio - Artist Presets + English Instrument Tags")
    artist_presets = list_artist_presets() or [get_artist_preset("vela_moon")]
    names = [preset.get("artist_name", preset.get("artist_id", "Vela Moon")) for preset in artist_presets]
    current_artist_id = (project.get("song", {}) or {}).get("artist_preset", st.session_state.selected_artist_preset)
    current_index = next((idx for idx, preset in enumerate(artist_presets) if preset.get("artist_id") == current_artist_id), 0)
    left, right = st.columns([1.1, 0.9])
    with left:
        title = st.text_input("Project / Song Title", value=project.get("title", "เพลงใหม่ของฉัน"))
        artist = st.text_input("Artist", value=project.get("artist", DEFAULT_ARTIST))
        idea = st.text_area("Song Idea / Story", height=160)
        genre = st.selectbox("Genre", ["Pop Rock", "Heartbreak Ballad", "T-Pop", "Night Drive", "Isaan Indie"], index=0)
        mood = st.selectbox("Mood", ["เศร้า", "คิดถึง", "เหงากลางคืน", "อบอุ่น", "ให้กำลังใจ"], index=1)
        vocal = st.selectbox("Vocal", ["smooth emotional male vocal", "emotional male vocal", "soft female vocal", "duet male and female"], index=0)
        viral = st.selectbox("Viral Level", ["balanced", "high", "ultra hook-focused"], index=1)
    with right:
        selected_name = st.selectbox("Artist Preset", names, index=current_index)
        preset = artist_presets[names.index(selected_name)]
        st.session_state.selected_artist_preset = preset.get("artist_id", "vela_moon")
        use_preset = st.checkbox("Use Artist Preset Style", value=True)
        force_tags = st.checkbox("Force English Instrument Tags", value=True)
        style_override = st.text_area("Music Style Prompt Override", value=preset.get("default_music_style_prompt", ""), height=120)
        with st.expander("Preset Summary", expanded=True):
            st.write(f"Genre: {preset.get('genre', '')}")
            st.write(f"Vocal: {preset.get('vocal_style', '')}")
            st.write(", ".join(preset.get("main_instruments", []) or []))
            st.json(preset.get("suno_advanced_settings", {}), expanded=False)
    if st.button("Generate Song for Suno", type="primary"):
        if not idea.strip():
            st.error("กรุณาใส่ไอเดียเพลง")
            st.stop()
        song_result = _safe(
            "Generate song",
            generate_song_with_gemini,
            settings.gemini_api_key,
            settings.gemini_model,
            idea,
            genre,
            mood,
            vocal,
            viral,
            artist_preset=preset if use_preset else get_artist_preset("vela_moon"),
            music_style_override=style_override if use_preset else "",
            force_english_instrument_tags=force_tags,
        )
        if song_result.get("ok") is False and "title" not in song_result:
            st.stop()
        song_result["artist_preset"] = preset.get("artist_id", "vela_moon")
        song_result["artist_preset_data"] = preset
        song_result["instrument_tags_language"] = "English only"
        project["title"] = song_result.get("title") or title
        project["artist"] = artist
        project["song"] = song_result
        st.session_state.generated_song = song_result
        st.session_state.normalized_song_output = song_result.get("normalized_song_output", "")
        _save_project()
        st.success("Song generated")
    song = project.get("song", {}) or {}
    if song:
        t1, t2, t3, t4 = st.tabs(["Hook", "Suno Style", "Lyrics", "TikTok Cut"])
        with t1:
            st.write("Title:", song.get("title", ""))
            st.write("Selected Hook:", song.get("selected_hook", ""))
            st.json(song.get("candidate_hooks", []), expanded=False)
        with t2:
            st.code(song.get("music_style_prompt", ""), language="text")
            st.json(song.get("advanced_settings", {}), expanded=False)
            st.json({"artist_preset": song.get("artist_preset", "vela_moon"), "instrument_tags_language": song.get("instrument_tags_language", "English only")}, expanded=False)
        with t3:
            edited = st.text_area("Complete Lyrics with Tags", value=song.get("complete_lyrics", ""), height=520)
            validation = validate_english_only_tags(edited)
            if not validation.get("ok"):
                st.warning("Some instrument tags still contain Thai. Click Auto Fix Tags.")
            c1, c2 = st.columns(2)
            if c1.button("Auto Fix Instrument Tags"):
                fixed = normalize_lyrics_tags(edited, get_artist_preset(song.get("artist_preset", "vela_moon")))
                song["original_song_output"] = song.get("original_song_output") or edited
                song["normalized_song_output"] = fixed
                song["complete_lyrics"] = fixed
                song["instrument_tag_validation"] = validate_english_only_tags(fixed)
                st.session_state.normalized_song_output = fixed
                _save_project()
                st.rerun()
            if c2.button("Save Edited Lyrics"):
                fixed = normalize_lyrics_tags(edited, get_artist_preset(song.get("artist_preset", "vela_moon")))
                song["complete_lyrics"] = fixed
                song["normalized_song_output"] = fixed
                song["instrument_tag_validation"] = validate_english_only_tags(fixed)
                _save_project()
                st.success("Saved")
            with st.expander("Normalized Song Output", expanded=True):
                st.text_area("normalized_song_output", value=song.get("normalized_song_output", ""), height=220, key="normalized_song_output_display")
            with st.expander("Instrument Tag Validation", expanded=False):
                st.json(validation, expanded=False)
        with t4:
            st.json(song.get("tiktok_clip_cut_recommendation", []), expanded=False)

elif page == "MV Director":
    st.subheader("MV Director")
    title = st.text_input("Song Title", value=project.get("title", "เพลงใหม่ของฉัน"))
    artist = st.text_input("Artist", value=project.get("artist", DEFAULT_ARTIST), key="mv_artist")
    lyrics = st.text_area("Lyrics", value=_current_lyrics(), height=320)
    style = st.text_input("Visual Style", value="cinematic emotional Thai pop rock MV")
    scene_count = st.slider("Scene Count", 4, 32, 12)
    if st.button("Generate MV Director Plan", type="primary"):
        mv = _safe("Generate MV", analyze_song_with_gemini, settings.gemini_api_key, settings.gemini_model, title, artist, lyrics, style, "balanced", scene_count=scene_count)
        if mv.get("storyboard") is not None:
            project["title"] = title
            project["artist"] = artist
            project["mv"] = mv
            st.session_state.storyboard = mv.get("storyboard", [])
            _save_project()
            st.success("MV plan generated")
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
    st.subheader("Render Lab")
    c1, c2, c3 = st.columns(3)
    profile = c1.selectbox("Render Profile", list(RENDER_PROFILES.keys()), index=list(RENDER_PROFILES.keys()).index(st.session_state.render_profile) if st.session_state.render_profile in RENDER_PROFILES else 0)
    aspects = c2.multiselect("Aspect Ratios", ["16:9", "9:16", "1:1"], default=["16:9"])
    subtitle_mode = c3.selectbox("Subtitle Mode", ["none", "simple", "karaoke", "tiktok", "cinematic"], index=1)
    audio_path = st.text_input("Audio Path", value=(project.get("assets", {}) or {}).get("audio_path", ""))
    st.session_state.render_profile = profile
    with st.expander("Preview / Advanced Render Controls", expanded=False):
        st.caption("Use preview before expensive full render. Smart Clip Factory remains available from Production.")
        st.selectbox("Motion Style", ["auto", "still", "cinematic_drift", "slow_zoom_in", "slow_zoom_out", "hook_energy_zoom"], key="render_motion_style")
        st.selectbox("Transition Style", ["none", "fade", "blur dissolve", "flash cut", "emotional dip to black"], key="render_transition_style")
        if st.button("Open Smart Clip Factory"):
            st.session_state.selected_page = "Smart Clip Factory"
            st.session_state.nav_page = "Smart Clip Factory"
            st.rerun()
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
    st.subheader("Smart Clip Factory")
    latest = _latest_render_dir(project)
    source_video = st.text_input("Source Final Render", value=str(latest / "final_9x16.mp4"))
    clip_type = st.selectbox("Clip Type", list(CLIP_TYPES.keys()))
    preview = st.checkbox("Preview Mode", value=True)
    if st.button("Generate Clip", type="primary"):
        st.json(generate_clip(project, source_video, latest, clip_type, settings.ffmpeg_path, preview=preview), expanded=False)
    if st.button("Generate Full Clip Set"):
        st.json(generate_clip_set(project, source_video, latest, settings.ffmpeg_path, preview=preview), expanded=False)

elif page == "Marketing Package":
    st.subheader("Marketing Package")
    package = build_marketing_package(project)
    st.json(package.get("data", {}), expanded=False)
    if st.button("Export Marketing Package", type="primary"):
        st.json(export_marketing_package(project), expanded=False)

elif page == "Final Package":
    st.subheader("Final Package")
    render_dir = st.text_input("Render Folder", value=str(_latest_render_dir(project)))
    st.caption("Preflight checks run before packaging. A project backup is created before build.")
    st.dataframe(pd.DataFrame(inspect_final_package_inputs(project, render_dir).get("data", {}).get("checks", [])), use_container_width=True)
    if st.button("Build Final Release Package", type="primary"):
        backup_project(project, "before_final_package")
        st.json(build_final_release_package(project, ROOT / "outputs" / "final_packages" / safe_name(project.get("title", "project")), render_dir, zip_package=True), expanded=False)

elif page == "Creative Intelligence":
    st.subheader("Creative Intelligence")
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
    st.subheader("Production Audit")
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
    st.subheader("System Health")
    st.json(run_healthcheck(settings), expanded=False)
    project_path = st.text_input("Safe Mode Project JSON")
    if st.button("Open Safe Mode", disabled=not project_path):
        st.json(open_project_safe_mode(project_path), expanded=False)

elif page == "Release Hardening Tools":
    st.subheader("Release Hardening Tools")
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
