from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

try:
    from streamlit_js_eval import streamlit_js_eval
except Exception:
    streamlit_js_eval = None


ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from core.artist_presets import (
    DEFAULT_ARTIST_ID,
    GENERAL_CREATOR_CATEGORY,
    PUBLIC_DEFAULT_ARTIST_ID,
    delete_artist_preset,
    duplicate_artist_preset,
    export_artist_preset,
    get_artist_preset,
    import_artist_preset,
    is_locked_artist_preset,
    artist_preset_categories,
    list_artist_presets_by_category,
    list_artist_presets,
    load_default_artist_id,
    save_artist_preset,
    set_default_artist_preset,
)
from core.analytics import cleanup_old_temp_exports, ensure_beta_runtime_dirs, load_beta_analytics, log_beta_event
from core.api_keys import API_MODE_BETA_KEY, API_MODE_OWN_KEY, API_MODES, LOCAL_STORAGE_KEYS, api_mode_label, mask_api_key, provider_key_env_name, resolve_provider_credentials
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
from core.hook_clip_engine import build_hook_render_package, export_hook_clip_package, hook_clip_package_to_text
from core.instrument_tag_normalizer import normalize_lyrics_tags, validate_english_only_tags
from core.job_queue import cancel_job, clear_finished_jobs, list_jobs, submit_job
from core.licensing import get_license_service
from core.marketing_package import build_marketing_package, export_marketing_package
from core.mv_storyboard_generator import export_mv_storyboard, generate_mv_storyboard
from core.navigation_config import (
    FULL_MENU_GROUPS,
    PAGE_LABELS,
    PODCAST_STUDIO_ALLOWED_PAGES,
    HOOK_CLIP_ALLOWED_PAGES,
    SONG_ONLY_ALLOWED_PAGES,
    SONG_ONLY_MENU_GROUPS,
    SELLER_STUDIO_ALLOWED_PAGES,
    VIRAL_CLIPS_ALLOWED_PAGES,
    flatten_pages,
    menu_groups_for_mode,
    normalize_navigation_state,
    page_label,
)
from core.podcast_content import (
    EPISODE_LENGTHS,
    NARRATION_STYLES,
    STORY_TONES,
    build_podcast_dashboard_status,
    export_podcast_content,
    generate_podcast_content,
    podcast_content_to_text,
)
from core.viral_clips_content import (
    CLIP_LENGTHS,
    GOALS,
    SOURCE_TYPES,
    TARGET_PLATFORMS,
    TONE_STYLES as CLIP_TONE_STYLES,
    build_viral_clips_dashboard_status,
    export_viral_clips_content,
    generate_viral_clips_content,
    viral_clips_to_text,
)
from core.visual_presets import (
    DEFAULT_VISUAL_SETTINGS,
    list_camera_presets,
    list_lighting_presets,
    list_motion_presets,
    list_visual_mood_presets,
)
from core.preset_system import list_project_templates
from core.project_io import load_project, new_project, safe_name, save_project, save_project_folder
from core.product_link_analyzer import analyze_product_link
from core.paths import project_folder, resolve_project_folder, workflow_project_root
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
from core.render_connector import (
    RENDER_JOB_PROVIDER_MODES,
    build_render_package,
    check_render_job_status,
    export_render_package,
    load_render_jobs,
    load_render_queue,
    mark_render_queue_item,
    send_render_job,
)
from core.real_clip_pipeline import render_placeholder_scene, render_real_hook_clip
from core.render_engine import run_render
from core.rendering_presets import ASPECT_RATIOS, MOTION_INTENSITIES, RENDER_DURATIONS, RENDER_QUALITIES, get_render_preset_bundle, list_render_preset_bundles, list_rendering_providers
from core.render_profiles import RENDER_PROFILES
from core.render_recovery import export_diagnostic_bundle, latest_failed_render, recover_render_temp
from core.safe_mode import open_project_safe_mode
from core.scene_scoring import score_project_scenes, smart_tiktok_recommendations
from core.scene_story_engine import build_subtitle_timing
from core.seller_content import HOOK_STYLES, TONE_GUIDES, build_seller_dashboard_status, export_seller_content, generate_seller_content, seller_content_to_text
from core.voiceover_engine import VOICEOVER_STYLES, build_voiceover_plan, export_voiceover_plan, generate_voiceover_audio
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
from core.veo_scene_renderer import download_veo_scene_result, load_scene_jobs, poll_veo_scene_job, save_scene_job, scene_output_path, submit_veo_scene_job
from core.version import APP_VERSION, BUILD_VERSION, RELEASE_CHANNEL, build_label
from providers.image_ai import generate_image
from providers.ai_provider import normalize_provider, provider_display_name
from providers.text_ai import analyze_song_with_gemini, generate_song_with_gemini
from providers.video_ai import generate_video
from providers.veo_provider import build_veo_payload, submit_render_job as submit_veo_render_job
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
ensure_beta_runtime_dirs()


DISPLAY_TEXT_FIXES = {
    "เน€เธเธฅเธเนเธซเธกเนเธเธญเธเธเธฑเธ": "เพลงใหม่ของฉัน",
}

WORKFLOW_DEFAULT_NAMES = {
    "Song Studio Only": "เพลงใหม่ของฉัน",
    "Full Pipeline": "โปรเจกต์เพลงใหม่",
    "Seller Studio (Beta)": "แคมเปญใหม่ของฉัน",
    "Podcast Studio": "ตอนใหม่ของฉัน",
    "Podcast Studio (Beta)": "ตอนใหม่ของฉัน",
    "Viral Clips Studio (Beta)": "คลิปไวรัลใหม่",
    "Hook Clip Studio (Beta)": "Hook Clip ใหม่",
    "MV Workflow": "MV Project ใหม่",
}

SONG_DEFAULT_TITLES = {"", "เพลงใหม่ของฉัน", "โปรเจกต์เพลงใหม่"}


def _workflow_default_name(workflow_mode: str | None = None) -> str:
    mode = workflow_mode or st.session_state.get("workflow_mode", "Full Pipeline")
    return WORKFLOW_DEFAULT_NAMES.get(mode, "โปรเจกต์ใหม่")


def _active_ai_provider() -> str:
    return normalize_provider(st.session_state.get("default_ai_provider") or settings.default_ai_provider)


def _active_text_credentials() -> tuple[str, str, str]:
    provider = _active_ai_provider()
    resolved = resolve_provider_credentials(
        settings=settings,
        provider=provider,
        api_mode=st.session_state.get("api_mode", API_MODE_OWN_KEY),
        user_api_keys=st.session_state.get("user_api_keys", {}),
    )
    return resolved["provider"], resolved["api_key"], resolved["model"]


def _active_credential_status() -> dict[str, Any]:
    return resolve_provider_credentials(
        settings=settings,
        provider=_active_ai_provider(),
        api_mode=st.session_state.get("api_mode", API_MODE_OWN_KEY),
        user_api_keys=st.session_state.get("user_api_keys", {}),
    )


def _warn_missing_provider_key(provider: str, api_key: str) -> None:
    if api_key:
        return
    label = provider_display_name(provider)
    resolved = _active_credential_status() if provider == _active_ai_provider() else {}
    key_name = resolved.get("missing_key") or {"openai": "OPENAI_API_KEY", "xai": "XAI_API_KEY"}.get(provider, "GEMINI_API_KEY")
    warning = resolved.get("warning") or f"{label} ยังไม่มี {key_name}. ระบบจะใช้ offline fallback แทนและไม่ crash."
    st.warning(warning)


def _provider_runtime_status(provider: str, api_key: str) -> dict[str, str]:
    resolved = _active_credential_status() if provider == _active_ai_provider() else None
    if api_key:
        source = (resolved or {}).get("source", "")
        source_label = "user key" if source == "user" else "VelaFlow beta key" if source == "velaflow_beta" else "configured key"
        return {"status": "Ready", "message": f"{provider_display_name(provider)} configured via {source_label}"}
    label = provider_display_name(provider)
    key_name = (resolved or {}).get("missing_key") or provider_key_env_name(provider)
    warning = (resolved or {}).get("warning") or f"Missing Key: {key_name}. {label} will fall back where available."
    return {"status": "Offline Fallback", "message": warning}


def _workflow_analytics_key(workflow_mode: str | None = None) -> str:
    mode = workflow_mode or st.session_state.get("workflow_mode", "Full Pipeline")
    return {
        "Song Studio Only": "music",
        "Full Pipeline": "music",
        "Seller Studio (Beta)": "seller",
        "Podcast Studio (Beta)": "podcast",
        "Viral Clips Studio (Beta)": "viral_clips",
        "Hook Clip Studio (Beta)": "viral_clips",
    }.get(mode, "music")


def _log_beta_event(event_type: str, workflow: str | None = None, preset_bundle: str = "", metadata: dict[str, Any] | None = None) -> None:
    provider, _, _ = _active_text_credentials()
    log_beta_event(event_type, workflow=workflow or _workflow_analytics_key(), provider=provider, preset_bundle=preset_bundle, metadata=metadata)


def _js_string(value: str) -> str:
    return json.dumps(str(value or ""))


def _local_storage_read() -> dict[str, Any] | None:
    if streamlit_js_eval is None:
        return {}
    expression = """
JSON.stringify({
  api_mode: localStorage.getItem('velaflow_api_mode') || '',
  provider: localStorage.getItem('velaflow_ai_provider') || '',
  gemini: localStorage.getItem('velaflow_gemini_key') || '',
  openai: localStorage.getItem('velaflow_openai_key') || '',
  xai: localStorage.getItem('velaflow_xai_key') || ''
})
"""
    try:
        raw = streamlit_js_eval(js_expressions=expression, key="velaflow_local_api_read", want_output=True)
        if raw is None:
            return None
        return json.loads(raw) if isinstance(raw, str) and raw.strip().startswith("{") else {}
    except Exception:
        return {}


def _local_storage_script(script: str, key: str) -> None:
    if streamlit_js_eval is not None:
        try:
            streamlit_js_eval(js_expressions=f"{script}\n'ok';", key=key, want_output=True)
            return
        except Exception:
            pass
    components.html(f"<script>{script}</script>", height=0)


def _restore_local_api_state() -> None:
    if st.session_state.get("local_api_state_restored"):
        return
    restored = _local_storage_read()
    if restored is None:
        return
    if restored:
        restored_mode = api_mode_label(restored.get("api_mode", API_MODE_OWN_KEY))
        restored_provider = normalize_provider(restored.get("provider") or st.session_state.get("default_ai_provider") or "gemini")
        keys = {
            provider: str(restored.get(provider, "") or "").strip()
            for provider in ("gemini", "openai", "xai")
            if str(restored.get(provider, "") or "").strip()
        }
        st.session_state.api_mode = restored_mode
        st.session_state.default_ai_provider = restored_provider
        st.session_state.user_api_keys = keys
        st.session_state.local_api_state_source = "localStorage"
    elif streamlit_js_eval is None:
        st.session_state.local_api_state_source = "session_state_only"
    else:
        st.session_state.local_api_state_source = "empty_localStorage"
    st.session_state.local_api_state_restored = True


def _save_api_state_to_local_storage(provider: str, api_mode: str, api_key: str = "") -> None:
    provider = normalize_provider(provider)
    storage_key = LOCAL_STORAGE_KEYS.get(provider, "velaflow_gemini_key")
    statements = [
        f"localStorage.setItem('velaflow_api_mode', {_js_string(api_mode_label(api_mode))});",
        f"localStorage.setItem('velaflow_ai_provider', {_js_string(provider)});",
    ]
    if api_key.strip():
        statements.append(f"localStorage.setItem({_js_string(storage_key)}, {_js_string(api_key.strip())});")
    _local_storage_script("\n".join(statements), f"velaflow_save_api_state_{provider}_{st.session_state.get('api_storage_nonce', 0)}")


def _forget_api_key_from_local_storage(provider: str) -> None:
    provider = normalize_provider(provider)
    storage_key = LOCAL_STORAGE_KEYS.get(provider, "velaflow_gemini_key")
    script = f"""
localStorage.removeItem({_js_string(storage_key)});
localStorage.setItem('velaflow_ai_provider', {_js_string(provider)});
localStorage.setItem('velaflow_api_mode', {_js_string(API_MODE_OWN_KEY)});
"""
    _local_storage_script(script, f"velaflow_forget_api_key_{provider}_{st.session_state.get('api_storage_nonce', 0)}")


def _visual_controls(prefix: str, defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    current = {**DEFAULT_VISUAL_SETTINGS, **(defaults or {})}
    with st.expander("Visual Direction", expanded=False):
        c1, c2 = st.columns(2)
        camera = c1.selectbox("Camera Style", list_camera_presets(), index=list_camera_presets().index(current.get("camera_preset", DEFAULT_VISUAL_SETTINGS["camera_preset"])), key=f"{prefix}_camera_style")
        lighting = c2.selectbox("Lighting Style", list_lighting_presets(), index=list_lighting_presets().index(current.get("lighting_preset", DEFAULT_VISUAL_SETTINGS["lighting_preset"])), key=f"{prefix}_lighting_style")
        motion = c1.selectbox("Motion Style", list_motion_presets(), index=list_motion_presets().index(current.get("motion_preset", DEFAULT_VISUAL_SETTINGS["motion_preset"])), key=f"{prefix}_motion_style")
        mood = c2.selectbox("Visual Mood", list_visual_mood_presets(), index=list_visual_mood_presets().index(current.get("visual_mood", DEFAULT_VISUAL_SETTINGS["visual_mood"])), key=f"{prefix}_visual_mood")
    return {"camera_preset": camera, "lighting_preset": lighting, "motion_preset": motion, "visual_mood": mood}


def _bundle_controls(prefix: str, defaults: dict[str, Any] | None = None) -> tuple[str, dict[str, Any], dict[str, Any]]:
    current_bundle = (defaults or {}).get("bundle_name") or "Custom"
    options = ["Custom"] + list_render_preset_bundles()
    selected = st.selectbox(
        "Visual / Render Preset Bundle",
        options,
        index=options.index(current_bundle) if current_bundle in options else 0,
        key=f"{prefix}_preset_bundle",
        help="เลือกชุด preset เพื่อเติม Visual Direction และ Render Settings อัตโนมัติ",
    )
    if selected == "Custom":
        return selected, {}, {}
    bundle = get_render_preset_bundle(selected)
    visual = {
        "camera_preset": str(bundle.get("camera_preset", "Cinematic")),
        "lighting_preset": str(bundle.get("lighting_preset", "Soft Indoor")),
        "motion_preset": str(bundle.get("motion_preset", "Slow Cinematic")),
        "visual_mood": str(bundle.get("visual_mood", "Emotional")),
    }
    render = {
        "provider": str(bundle.get("provider", "Runway")),
        "aspect_ratio": str(bundle.get("aspect_ratio", "9:16")),
        "duration": str(bundle.get("duration", "5s")),
        "quality": str(bundle.get("quality", "Standard")),
        "motion_intensity": str(bundle.get("motion_intensity", "Medium")),
        "bundle_name": selected,
    }
    st.caption(f"Bundle applied: {selected}")
    return selected, visual, render


def _render_settings_controls(prefix: str, defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    current = {
        "provider": "Runway",
        "aspect_ratio": "9:16",
        "duration": "5s",
        "quality": "Standard",
        "motion_intensity": "Medium",
        "bundle_name": "",
        **(defaults or {}),
    }
    with st.expander("🎬 Render Settings", expanded=False):
        c1, c2 = st.columns(2)
        providers = list_rendering_providers()
        provider = c1.selectbox("Rendering Provider", providers, index=providers.index(current.get("provider", "Runway")) if current.get("provider") in providers else 0, key=f"{prefix}_render_provider")
        aspect_ratio = c2.selectbox("Aspect Ratio", ASPECT_RATIOS, index=ASPECT_RATIOS.index(current.get("aspect_ratio", "9:16")) if current.get("aspect_ratio") in ASPECT_RATIOS else 0, key=f"{prefix}_render_aspect")
        duration = c1.selectbox("Duration", RENDER_DURATIONS, index=RENDER_DURATIONS.index(current.get("duration", "5s")) if current.get("duration") in RENDER_DURATIONS else 0, key=f"{prefix}_render_duration")
        quality = c2.selectbox("Quality", RENDER_QUALITIES, index=RENDER_QUALITIES.index(current.get("quality", "Standard")) if current.get("quality") in RENDER_QUALITIES else 1, key=f"{prefix}_render_quality")
        motion_intensity = c1.selectbox("Motion Intensity", MOTION_INTENSITIES, index=MOTION_INTENSITIES.index(current.get("motion_intensity", "Medium")) if current.get("motion_intensity") in MOTION_INTENSITIES else 1, key=f"{prefix}_render_motion")
        st.caption("Default is vertical 9:16. Start Render can create a local MP4; external provider jobs remain BYO-key/mock until configured.")
    return {"provider": provider, "aspect_ratio": aspect_ratio, "duration": duration, "quality": quality, "motion_intensity": motion_intensity, "bundle_name": current.get("bundle_name", "")}


def _attach_render_connector(project_name: str, workflow_key: str, workflow_type: str, content: Any, render_settings: dict[str, Any], visual_settings: dict[str, Any]) -> dict[str, Any]:
    render_package = build_render_package(project_name, workflow_type, content, render_settings, visual_settings)
    render_root = resolve_project_folder(project_name, workflow_type).parent
    render_export = export_render_package(project_name, render_package, render_root)
    project.setdefault(workflow_key, {})["render_connector"] = {"package": render_package, "export": render_export.get("data", {})}
    if render_export.get("ok"):
        _log_beta_event(
            "render_package_generated",
            workflow=workflow_type,
            preset_bundle=str((render_settings or {}).get("bundle_name") or ""),
            metadata={"ok": True},
        )
    return render_export


def _render_package_preview(render_connector: dict[str, Any] | None) -> None:
    package = (render_connector or {}).get("package", {}) or {}
    payload = package.get("payload", {}) or {}
    metadata = package.get("metadata", {}) or {}
    export_data = (render_connector or {}).get("export", {}) or {}
    if not payload:
        return
    project_name = str(metadata.get("project_name") or st.session_state.get("project", {}).get("title") or "render_project")
    safe_project = safe_name(project_name)
    with st.expander("Render Package Preview", expanded=False):
        c1, c2, c3 = st.columns(3)
        c1.metric("Provider", payload.get("provider", "-"))
        c2.metric("Aspect", payload.get("aspect_ratio", "-"))
        c3.metric("Duration", payload.get("duration", "-"))
        st.caption(f"Quality: {payload.get('quality', '-')} | Motion: {payload.get('motion_intensity', '-')} | Bundle: {payload.get('bundle_name') or '-'}")
        st.text_area("Visual prompt", value=str(payload.get("visual_prompt") or ""), height=120, key=f"preview_visual_{payload.get('provider','')}_{payload.get('duration','')}")
        st.text_area("Thumbnail prompt", value=str(payload.get("thumbnail_prompt") or ""), height=90, key=f"preview_thumb_{payload.get('provider','')}_{payload.get('duration','')}")
        st.write("B-roll ideas")
        st.write(payload.get("b_roll_ideas", []) or [])
        st.write("Scene structure")
        st.write(payload.get("scene_structure", []) or [])
        if export_data.get("txt_path"):
            st.caption(f"Render TXT: {export_data.get('txt_path')}")
        st.divider()
        st.write("Google Flow-style Render Job")
        st.caption("Mock/job metadata only. No Google Veo, Kling, Runway, or external render API is called yet.")
        provider_mode = st.selectbox(
            "Provider Mode",
            RENDER_JOB_PROVIDER_MODES,
            index=0,
            key=f"render_job_provider_mode_{safe_project}_{payload.get('provider','')}_{payload.get('duration','')}",
            help="Manual / Mock creates a fake job id. Ready modes prepare metadata for future provider integrations.",
        )
        if st.button("Send Render Job", key=f"send_render_job_{safe_project}_{payload.get('provider','')}_{payload.get('duration','')}"):
            result = send_render_job(project_name, package, provider_mode)
            if result.get("ok"):
                _log_beta_event("render_job", workflow=str(payload.get("workflow_type") or ""), preset_bundle=str(payload.get("bundle_name") or ""), metadata={"provider_mode": provider_mode})
                st.success(f"Render Job ID: {result['data']['job'].get('job_id')}")
            else:
                st.error(result.get("error") or result.get("message"))
            st.rerun()
        jobs_result = load_render_jobs(project_name)
        jobs = jobs_result.get("data", {}).get("items", [])
        if jobs:
            job_rows = [
                {
                    "Job ID": job.get("job_id", ""),
                    "Status": job.get("status", ""),
                    "Provider mode": job.get("provider_mode", ""),
                    "Provider": job.get("render_provider", ""),
                    "Aspect": job.get("aspect_ratio", ""),
                    "Duration": job.get("duration", ""),
                    "Updated": job.get("updated_at", ""),
                }
                for job in jobs
            ]
            st.dataframe(pd.DataFrame(job_rows), use_container_width=True, height=180)
            selected_job = st.selectbox("Render Job ID", [job.get("job_id", "") for job in jobs], key=f"render_job_select_{safe_project}")
            selected_data = next((job for job in jobs if job.get("job_id") == selected_job), {})
            jc1, jc2 = st.columns(2)
            if jc1.button("Check Status", key=f"check_render_job_{safe_project}"):
                status_result = check_render_job_status(project_name, selected_job)
                if status_result.get("ok"):
                    st.success(f"Status: {status_result['data']['job'].get('status')}")
                else:
                    st.error(status_result.get("error") or status_result.get("message"))
                st.rerun()
            result_path = Path(str(selected_data.get("result_path") or ""))
            if selected_data.get("status") == "Completed" and result_path.is_file():
                jc2.download_button(
                    "Download Result placeholder",
                    data=result_path.read_bytes(),
                    file_name=result_path.name,
                    mime="text/plain",
                    key=f"download_render_job_result_{safe_project}_{selected_job}",
                )
                st.caption(f"Placeholder result path: {result_path}")
            else:
                jc2.button("Download Result placeholder", disabled=True, key=f"download_render_job_disabled_{safe_project}_{selected_job}")
        else:
            st.info("No render jobs yet. Send a mock render job to start.")


def _render_queue_ui(project_name: str, base_dir: str | Path | None = None) -> None:
    st.write("Render Queue")
    if st.button("Refresh Queue", key=f"refresh_render_queue_{safe_name(project_name)}"):
        st.rerun()
    loaded = load_render_queue(project_name, base_dir)
    items = loaded.get("data", {}).get("items", [])
    if not items:
        st.info("No render queue items yet.")
        return
    rows = [
        {
            "Status": item.get("status", ""),
            "Provider": item.get("provider", ""),
            "Workflow type": item.get("workflow_type", ""),
            "Aspect ratio": item.get("aspect_ratio", ""),
            "Duration": item.get("duration", ""),
            "Quality": item.get("quality", ""),
            "Motion intensity": (item.get("payload") or {}).get("motion_intensity", ""),
            "Created time": item.get("created_at", ""),
            "Queue ID": item.get("queue_id", ""),
        }
        for item in items
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, height=220)
    selected = st.selectbox("Queue item", [item.get("queue_id", "") for item in items], key=f"queue_item_select_{safe_name(project_name)}")
    c1, c2 = st.columns(2)
    if c1.button("Export Render Package", key=f"queue_export_{safe_name(project_name)}"):
        item = next((entry for entry in items if entry.get("queue_id") == selected), {})
        package = {"metadata": {"project_name": project_name, "workflow_type": item.get("workflow_type", ""), "provider": item.get("provider", ""), "quality": item.get("quality", "")}, "payload": item.get("payload", {}), "queue_item": item}
        result = export_render_package(project_name, package, base_dir)
        if result.get("ok"):
            _log_beta_event("export", workflow=str(item.get("workflow_type") or ""), preset_bundle=str((item.get("payload") or {}).get("bundle_name") or ""), metadata={"format": "render_package"})
        st.success(f"Render package exported: {result.get('data', {}).get('txt_path')}") if result.get("ok") else st.error(result.get("error") or result.get("message"))
    if c2.button("Mark as Exported", key=f"queue_mark_exported_{safe_name(project_name)}"):
        result = mark_render_queue_item(project_name, selected, "Exported", base_dir)
        st.success("Queue item marked as Exported") if result.get("ok") else st.error(result.get("error") or result.get("message"))
        st.rerun()


def _render_jobs_ui(project_name: str, base_dir: str | Path | None = None) -> None:
    st.write("Render Jobs")
    loaded = load_render_jobs(project_name, base_dir)
    items = loaded.get("data", {}).get("items", [])
    st.caption(f"render_jobs.json: {loaded.get('data', {}).get('path', '')}")
    if not items:
        st.info("No render jobs yet. Generate a render package, then use Send Render Job.")
        return
    rows = [
        {
            "Status": item.get("status", ""),
            "Provider mode": item.get("provider_mode", ""),
            "Provider": item.get("render_provider", ""),
            "Workflow type": item.get("workflow_type", ""),
            "Aspect ratio": item.get("aspect_ratio", ""),
            "Duration": item.get("duration", ""),
            "Quality": item.get("quality", ""),
            "Motion intensity": item.get("motion_intensity", ""),
            "Created time": item.get("created_at", ""),
            "Render Job ID": item.get("job_id", ""),
        }
        for item in items
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, height=220)
    selected = st.selectbox("Render Job ID", [item.get("job_id", "") for item in items], key=f"monitor_render_job_select_{safe_name(project_name)}")
    if st.button("Check Status", key=f"monitor_check_render_job_{safe_name(project_name)}"):
        result = check_render_job_status(project_name, selected, base_dir)
        st.success(f"Status: {result.get('data', {}).get('job', {}).get('status')}") if result.get("ok") else st.error(result.get("error") or result.get("message"))
        st.rerun()


def _hook_source_options(project_context: dict[str, Any]) -> dict[str, Any]:
    return {
        "Music": project_context.get("song", {}) or {},
        "Seller": ((project_context.get("seller_studio", {}) or {}).get("content_package") or {}),
        "Podcast": ((project_context.get("podcast_studio", {}) or {}).get("content_package") or {}),
        "Viral Clips": ((project_context.get("viral_clips_studio", {}) or {}).get("content_package") or {}),
    }


def _hook_workflow_key(label: str) -> str:
    return {"Music": "music", "Seller": "seller", "Podcast": "podcast", "Viral Clips": "viral_clips"}.get(label, "hook_clip")


def _render_hook_clip_preview(hook_package: dict[str, Any]) -> None:
    if not hook_package:
        return
    st.write("🎬 Hook Clip Preview")
    c1, c2, c3 = st.columns(3)
    c1.metric("Duration", f"{(hook_package.get('scene_package') or {}).get('duration_seconds', 8)}s")
    c2.metric("Source", hook_package.get("source_workflow", "-"))
    c3.metric("Provider", ((hook_package.get("render_connector_package") or {}).get("payload") or {}).get("provider", "-"))
    st.markdown(f"**Hook:** {hook_package.get('hook_text', '')}")
    st.caption(f"Subtitle: {hook_package.get('subtitle_line', '')}")
    st.text_area("Thumbnail Prompt", value=hook_package.get("thumbnail_prompt", ""), height=90)
    st.dataframe(pd.DataFrame(hook_package.get("scene_sequence", []) or []), use_container_width=True, height=220)


def _scene_status_badge(status: str) -> str:
    normalized = str(status or "queued").lower()
    if normalized in {"completed", "completed_existing", "ready"}:
        return "completed"
    if normalized in {"rendering", "processing"}:
        return "rendering"
    if normalized in {"failed", "error"}:
        return "failed"
    return "queued"


def _hook_package_project_dir(project_name: str) -> Path:
    return workflow_project_root("clips") / safe_name(project_name or "hook_clip")


def _render_scene_preview_cards(project_name: str, hook_package: dict[str, Any], section_key: str, scene_jobs: dict[str, Any] | None = None) -> None:
    scenes = hook_package.get("scene_sequence") or (hook_package.get("scene_package") or {}).get("scenes") or []
    if not scenes:
        st.info("No scenes available yet.")
        return
    jobs = scene_jobs or {}
    st.write("Scene Preview")
    for index, scene in enumerate(scenes, start=1):
        scene_id = str(scene.get("scene_id") or f"scene_{index:02d}")
        scene_file = scene_output_path(project_name, scene_id)
        job = jobs.get(scene_id, {}) or {}
        status = _scene_status_badge(job.get("status") or ("completed" if scene_file.is_file() else "queued"))
        with st.container(border=True):
            c1, c2 = st.columns([2, 1])
            c1.markdown(f"**Scene {index}: {scene.get('beat') or scene.get('scene_title') or scene_id}**")
            c1.caption(f"Status: {status}")
            c2.caption(f"Duration: {scene.get('duration', '-')}s")
            st.caption(str(scene.get("subtitle") or scene.get("visual_prompt") or "")[:180])
            if scene_file.is_file():
                st.video(str(scene_file))
                st.download_button(
                    "Download Scene MP4",
                    data=scene_file.read_bytes(),
                    file_name=scene_file.name,
                    mime="video/mp4",
                    key=f"{section_key}_download_{scene_id}",
                    use_container_width=True,
                )
            elif status == "failed":
                st.warning(job.get("error") or "Scene render failed.")


def _render_first_scene_locally(project_name: str, hook_package: dict[str, Any], section_key: str) -> dict[str, Any]:
    scenes = hook_package.get("scene_sequence") or (hook_package.get("scene_package") or {}).get("scenes") or []
    if not scenes:
        return {"ok": False, "message": "No scene available", "data": {}, "error": "missing_scene"}
    scene = dict(scenes[0])
    scene_id = str(scene.get("scene_id") or "scene_01")
    project_dir = _hook_package_project_dir(project_name)
    scene_path = project_dir / "scenes" / f"{scene_id}.mp4"
    log_path = project_dir / "exports" / "real_clip_render_log.txt"
    aspect_ratio = ((hook_package.get("render_settings") or {}).get("aspect_ratio") or "9:16")
    job = {"scene_id": scene_id, "status": "rendering", "path": str(scene_path), "error": "", "updated_at": datetime.now().isoformat(timespec="seconds")}
    save_scene_job(project_name, scene_id, job)
    result = render_placeholder_scene(scene, scene_path, aspect_ratio=aspect_ratio, log_path=log_path)
    job["status"] = "completed" if result.get("ok") else "failed"
    job["error"] = result.get("error", "")
    job["updated_at"] = datetime.now().isoformat(timespec="seconds")
    save_scene_job(project_name, scene_id, job)
    return result


def _render_final_downloads(section_key: str, real_output: dict[str, Any]) -> None:
    if not real_output:
        return
    status = real_output.get("manifest", {}).get("status") or real_output.get("status") or "-"
    st.caption(f"Render Status: {status}")
    if real_output.get("final_mp4") and Path(real_output["final_mp4"]).is_file():
        final_path = Path(real_output["final_mp4"])
        st.video(str(final_path))
        st.download_button("Download Final Clip MP4", data=final_path.read_bytes(), file_name=final_path.name, mime="video/mp4", use_container_width=True, key=f"{section_key}_download_final_mp4")
    if real_output.get("subtitles") and Path(real_output["subtitles"]).is_file():
        subtitle_path = Path(real_output["subtitles"])
        st.download_button("Download subtitles.srt", data=subtitle_path.read_bytes(), file_name="subtitles.srt", mime="text/plain", use_container_width=True, key=f"{section_key}_download_srt")


def _mv_storyboard_to_hook_package(project_name: str, storyboard: list[dict[str, Any]], render_settings: dict[str, Any], visual_settings: dict[str, Any]) -> dict[str, Any]:
    scenes: list[dict[str, Any]] = []
    for index, item in enumerate(storyboard or [], start=1):
        scene_id = str(item.get("scene_id") or item.get("id") or f"scene_{index:02d}")
        if not scene_id.startswith("scene_"):
            scene_id = f"scene_{index:02d}"
        subtitle = str(item.get("subtitle") or item.get("lyric_part") or item.get("scene_title") or item.get("title") or "")[:90]
        visual_prompt = str(item.get("visual_prompt") or item.get("prompt") or item.get("image_prompt") or item.get("expanded_prompt") or subtitle or "cinematic vertical music video scene")
        scenes.append(
            {
                "scene_id": scene_id,
                "beat": item.get("scene_title") or item.get("title") or f"MV Scene {index}",
                "subtitle": subtitle,
                "visual_prompt": visual_prompt,
                "camera_direction": item.get("camera_direction") or item.get("camera") or "slow cinematic push-in",
                "lighting": item.get("lighting") or "cinematic emotional lighting",
                "motion": item.get("motion") or item.get("motion_effect") or "slow cinematic motion",
                "pacing": item.get("pacing") or item.get("pacing_note") or "music-video pacing",
                "transition": item.get("transition") or "soft cut",
                "duration": float(item.get("duration") or item.get("duration_seconds") or 2.5),
            }
        )
    if not scenes:
        return {}
    hook_text = scenes[0].get("subtitle") or project_name
    package = {
        "generated_by": "VelaFlow",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source_workflow": "music_mv",
        "hook_text": hook_text,
        "subtitle_line": hook_text,
        "scene_package": {"duration_seconds": sum(float(scene.get("duration", 0) or 0) for scene in scenes), "scenes": scenes},
        "scene_sequence": scenes,
        "subtitle_timing": build_subtitle_timing(scenes),
        "thumbnail_prompt": f"Vertical music video thumbnail for {project_name}, cinematic emotional style, no random text",
        "caption": "",
        "hashtags": ["#VelaFlow", "#MusicVideo", "#Shorts"],
        "render_prompt": "\n".join(str(scene.get("visual_prompt") or "") for scene in scenes),
        "render_settings": {"aspect_ratio": "9:16", **(render_settings or {})},
    }
    content = {"ai_video_prompt": package["render_prompt"], "thumbnail_prompt": package["thumbnail_prompt"], "visual_engine": {"scene_flow": scenes}}
    package["render_connector_package"] = build_render_package(project_name, "music_mv", content, package["render_settings"], visual_settings)
    return package


def _user_api_key(provider: str) -> str:
    return str((st.session_state.get("user_api_keys", {}) or {}).get(normalize_provider(provider), "") or "")


def _render_real_clip_controls(
    project: dict[str, Any],
    section_key: str,
    hook_package: dict[str, Any],
    workflow_type: str,
    *,
    default_voice_style: str = "calm narrator",
) -> None:
    if not hook_package:
        st.info("Generate a hook clip package first.")
        return
    project_name = project.get("title") or _workflow_default_name(st.session_state.get("workflow_mode"))
    existing = ((project.get(section_key, {}) or {}).get("real_output") or {})
    scene_jobs = (load_scene_jobs(project_name).get("data", {}).get("jobs", {}) or {})
    scenes = hook_package.get("scene_sequence") or (hook_package.get("scene_package") or {}).get("scenes") or []
    completed_scenes = sum(
        1
        for index, scene in enumerate(scenes, start=1)
        if scene_output_path(project_name, str(scene.get("scene_id") or f"scene_{index:02d}")).is_file()
    )
    creator_status = str((project.get(section_key, {}) or {}).get("creator_render_status") or existing.get("manifest", {}).get("status") or "queued")
    st.write("Creator Render")
    st.caption("Simple vertical clip rendering for creators. Default output is 9:16. If rendering is unavailable, VelaFlow shows a warning and keeps the scene package ready.")
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Queued", "Yes" if creator_status in {"queued", "rendering", "completed"} else "No")
    p2.metric("Rendering", "Yes" if creator_status == "rendering" else "No")
    p3.metric("Completed", "Yes" if existing.get("final_mp4") and Path(existing.get("final_mp4", "")).is_file() else "No")
    p4.metric("Scenes", f"{completed_scenes}/{len(scenes)}")

    use_voiceover = st.checkbox("Generate voiceover MP3", value=workflow_type in {"podcast", "viral_clips"}, key=f"{section_key}_real_voiceover")
    voice_style = st.selectbox("Voiceover Style", VOICEOVER_STYLES, index=VOICEOVER_STYLES.index(default_voice_style) if default_voice_style in VOICEOVER_STYLES else 0, key=f"{section_key}_real_voice_style")
    col_start, col_scene, col_all = st.columns(3)
    if col_start.button("🎬 Start Render", type="primary", use_container_width=True, key=f"{section_key}_start_render"):
        render_package = hook_package.get("render_connector_package") or {}
        project.setdefault(section_key, {})["creator_render_status"] = "queued"
        if render_package:
            job_result = send_render_job(project_name, render_package, "Manual / Mock")
            if job_result.get("ok"):
                project[section_key]["creator_render_job"] = job_result.get("data", {}).get("job", {})
                st.success("Render queued. You can render Scene 1 or Render All Scenes now.")
            else:
                st.warning(job_result.get("error") or job_result.get("message"))
        else:
            st.warning("Render package is missing. Generate the hook/storyboard package first.")
        _save_project()
        st.rerun()
    if col_scene.button("🎬 Render Scene 1", use_container_width=True, key=f"{section_key}_render_scene_1"):
        project.setdefault(section_key, {})["creator_render_status"] = "rendering"
        _save_project()
        result = _render_first_scene_locally(project_name, hook_package, section_key)
        project.setdefault(section_key, {})["creator_render_status"] = "completed" if result.get("ok") else "failed"
        _save_project()
        if result.get("ok"):
            st.success("Scene 1 rendered as MP4.")
        else:
            st.warning(result.get("error") or result.get("message") or "Render unavailable.")
        st.rerun()
    if col_all.button("🎬 Render All Scenes", use_container_width=True, key=f"{section_key}_render_all_scenes"):
        voiceover_path = ""
        project.setdefault(section_key, {})["creator_render_status"] = "rendering"
        if use_voiceover:
            voice_script = hook_package.get("subtitle_line") or hook_package.get("hook_text") or ""
            voice_result = generate_voiceover_audio(project_name, voice_script, style=voice_style, api_key=_user_api_key("openai"), provider="openai", output_name="hook_voiceover.mp3")
            if voice_result.get("ok"):
                voiceover_path = voice_result.get("data", {}).get("audio_path", "")
                project.setdefault(section_key, {})["voiceover_audio"] = voice_result.get("data", {})
                st.success(voice_result.get("message"))
            else:
                project.setdefault(section_key, {})["voiceover_error"] = voice_result.get("error") or voice_result.get("message")
                st.warning("Voiceover MP3 was not created. Rendering clip without audio.")
        result = render_real_hook_clip(project_name, hook_package, workflow_type=workflow_type, voiceover_path=voiceover_path)
        project.setdefault(section_key, {})["real_output"] = result.get("data", {})
        project[section_key]["creator_render_status"] = "completed" if result.get("ok") else "failed"
        project[section_key]["real_output_status"] = "completed" if result.get("ok") else "failed"
        project[section_key]["real_output_error"] = result.get("error", "")
        _save_project()
        if result.get("ok"):
            _log_beta_event("export", workflow=workflow_type, preset_bundle="real_mp4", metadata={"page": "Creator Render"})
            st.success("Final clip exported.")
        else:
            st.warning(result.get("error") or result.get("message") or "Render unavailable.")
        st.rerun()

    _render_scene_preview_cards(project_name, hook_package, section_key, scene_jobs)

    with st.container(border=True):
        st.markdown("**Provider render: Google Veo Scene 1**")
        st.caption("Optional BYO Gemini/Veo render. If unavailable, use Render Scene 1 / Render All Scenes for local placeholder MP4 output.")
        scene_job = scene_jobs.get("scene_01", {})
        c_submit, c_poll, c_download = st.columns(3)
        if c_submit.button("Submit Scene 1 to Veo", use_container_width=True, key=f"{section_key}_veo_submit_scene_01"):
            gemini_key = _user_api_key("gemini")
            if not gemini_key:
                st.warning("Please add your own Gemini/Veo API key in AI Settings first.")
            else:
                result = submit_veo_scene_job(project_name, hook_package, gemini_key, scene_index=0)
                if result.get("ok"):
                    st.success(f"Veo job submitted: {result['data']['job'].get('job_id')}")
                else:
                    st.warning(result.get("error") or result.get("message"))
                st.rerun()
        if c_poll.button("Check Veo Status", use_container_width=True, key=f"{section_key}_veo_poll_scene_01"):
            result = poll_veo_scene_job(project_name, _user_api_key("gemini"), "scene_01")
            if result.get("ok"):
                st.success(f"Scene 1 status: {result['data']['job'].get('status')}")
            else:
                st.warning(result.get("error") or result.get("message"))
            st.rerun()
        if c_download.button("Download Veo Scene 1", use_container_width=True, key=f"{section_key}_veo_download_scene_01"):
            result = download_veo_scene_result(project_name, _user_api_key("gemini"), "scene_01")
            if result.get("ok"):
                st.success("scene_01.mp4 downloaded")
            else:
                st.warning(result.get("error") or result.get("message"))
            st.rerun()
        if scene_job:
            st.json({key: value for key, value in scene_job.items() if key != "payload"}, expanded=False)

    if st.button("Combine Final Clip", use_container_width=True, key=f"{section_key}_combine_final_clip"):
        result = render_real_hook_clip(project_name, hook_package, workflow_type=workflow_type)
        project.setdefault(section_key, {})["real_output"] = result.get("data", {})
        project[section_key]["creator_render_status"] = "completed" if result.get("ok") else "failed"
        _save_project()
        st.success("Final clip combined.") if result.get("ok") else st.warning(result.get("error") or result.get("message"))
        st.rerun()

    existing = ((project.get(section_key, {}) or {}).get("real_output") or {})
    _render_final_downloads(section_key, existing)

    voice = ((project.get(section_key, {}) or {}).get("voiceover_audio") or {}).get("audio_path", "")
    if voice and Path(voice).is_file():
        voice_path = Path(voice)
        st.audio(str(voice_path))
        st.download_button("Download Voiceover MP3", data=voice_path.read_bytes(), file_name=voice_path.name, mime="audio/mpeg", use_container_width=True, key=f"{section_key}_download_voiceover")


def _seller_campaign_name(project_context: dict[str, Any]) -> str:
    title = _fix_display_text(project_context.get("title", "")).strip()
    return "New Seller Campaign" if title in SONG_DEFAULT_TITLES else title


def _save_seller_product_image(project_context: dict[str, Any], uploaded_file: Any) -> dict[str, Any]:
    if not uploaded_file:
        return {}
    project_name = safe_name(project_context.get("title") or _workflow_default_name("Seller Studio (Beta)"))
    image_dir = resolve_project_folder(project_name, project_context.get("workflow_type") or "seller") / "seller_assets"
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
    preferences = load_user_preferences()
    workflow_mode = preferences.get("workflow_mode", "Full Pipeline")
    initial_artist_preset = load_default_artist_id()
    if initial_artist_preset == DEFAULT_ARTIST_ID:
        initial_artist_preset = PUBLIC_DEFAULT_ARTIST_ID
    defaults = {
        "project": new_project(_workflow_default_name(workflow_mode), DEFAULT_ARTIST, workflow_type_for_mode(workflow_mode)),
        "current_project": "",
        "selected_section": "START",
        "selected_page": "Dashboard",
        "selected_artist_preset": initial_artist_preset,
        "render_profile": "Standard",
        "storyboard": [],
        "generated_song": {},
        "hook_candidates": [],
        "selected_hook": {},
        "normalized_song_output": "",
        "lyrics_saved": False,
        "workflow_mode": workflow_mode,
        "default_ai_provider": normalize_provider(settings.default_ai_provider),
        "api_mode": API_MODE_OWN_KEY,
        "user_api_keys": {},
        "api_storage_nonce": 0,
        "local_api_state_restored": False,
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
    project_context = _project()
    save_project_folder(project_context, workflow_project_root(project_context.get("workflow_type") or project_context.get("project_type")))


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


def _artist_preset_summary(preset: dict[str, Any]) -> str:
    return " | ".join(
        item
        for item in [
            f"Mood: {preset.get('mood', '-')}",
            f"Vocal: {preset.get('vocal_feeling') or preset.get('vocal_style', '-')}",
            f"Pacing: {preset.get('pacing', '-')}",
            f"Sound: {preset.get('instrumentation_style', '-')}",
        ]
        if item
    )


def _select_artist_preset(prefix: str, current_artist_id: str | None = None, compact: bool = True) -> dict[str, Any]:
    categories = artist_preset_categories() or [GENERAL_CREATOR_CATEGORY]
    target_current_id = current_artist_id or PUBLIC_DEFAULT_ARTIST_ID
    current = get_artist_preset(target_current_id)
    current_category = current.get("category") if current.get("artist_id") else GENERAL_CREATOR_CATEGORY
    if not current_artist_id:
        current_category = GENERAL_CREATOR_CATEGORY
    category = st.selectbox(
        "Artist Preset Category",
        categories,
        index=categories.index(current_category) if current_category in categories else 0,
        key=f"{prefix}_artist_preset_category",
        help="เลือกกลุ่ม preset ทั่วไปสำหรับงาน public beta หรือกลุ่ม Vela Moon Signature สำหรับงานเฉพาะตัว",
    )
    presets = list_artist_presets_by_category(category) or list_artist_presets()
    target_id = target_current_id if any(item.get("artist_id") == target_current_id for item in presets) else PUBLIC_DEFAULT_ARTIST_ID
    selected_index = next((idx for idx, item in enumerate(presets) if item.get("artist_id") == target_id), 0)
    labels = [_artist_preset_label(item) if not compact else item.get("artist_name", item.get("artist_id", "Artist")) for item in presets]
    selected_label = st.selectbox(
        "Artist Preset",
        labels,
        index=selected_index,
        key=f"{prefix}_artist_preset",
        help="เลือก preset เพื่อคุม mood, vocal feeling, pacing, instrumentation, hook และ visual direction",
    )
    selected = presets[labels.index(selected_label)]
    st.caption(_artist_preset_summary(selected))
    return selected


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
        "category": st.session_state.get(f"{prefix}_category", original.get("category", "Custom")),
        "description": st.session_state.get(f"{prefix}_description", original.get("description", "")),
        "mood": st.session_state.get(f"{prefix}_mood", original.get("mood", "")),
        "vocal_feeling": st.session_state.get(f"{prefix}_vocal_feeling", original.get("vocal_feeling", "")),
        "pacing": st.session_state.get(f"{prefix}_pacing", original.get("pacing", "")),
        "instrumentation_style": st.session_state.get(f"{prefix}_instrumentation_style", original.get("instrumentation_style", "")),
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
    categories = artist_preset_categories() or [GENERAL_CREATOR_CATEGORY]
    selected_category = st.selectbox("Preset Category", categories, index=0, key="artist_manager_category")
    presets = list_artist_presets_by_category(selected_category) or [get_artist_preset(PUBLIC_DEFAULT_ARTIST_ID)]
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
        st.write(f"Category: {selected.get('category', '')}")
        st.write(f"Description: {selected.get('description', '')}")
        st.write(f"Genre: {selected.get('genre', '')}")
        st.write(f"Mood: {selected.get('mood', '')}")
        st.write(f"Vocal feeling: {selected.get('vocal_feeling') or selected.get('vocal_style', '')}")
        st.write(f"Pacing: {selected.get('pacing', '')}")
        st.write(f"Instrumentation style: {selected.get('instrumentation_style', '')}")
        st.write(f"Vocal style: {selected.get('vocal_style', '')}")
        st.write("Main instruments:", ", ".join(selected.get("main_instruments", []) or []))
        st.code(selected.get("default_music_style_prompt", ""), language="text")

    if locked:
        st.warning("This is a locked system preset. Duplicate it to customize.")
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
        st.text_input("category", value=selected.get("category", "Custom"), disabled=locked, key=f"{prefix}_category")
        st.text_area("description", value=selected.get("description", ""), height=70, disabled=locked, key=f"{prefix}_description")
        st.text_input("mood", value=selected.get("mood", ""), disabled=locked, key=f"{prefix}_mood")
        st.text_input("vocal_feeling", value=selected.get("vocal_feeling", ""), disabled=locked, key=f"{prefix}_vocal_feeling")
        st.text_input("pacing", value=selected.get("pacing", ""), disabled=locked, key=f"{prefix}_pacing")
        st.text_input("instrumentation_style", value=selected.get("instrumentation_style", ""), disabled=locked, key=f"{prefix}_instrumentation_style")
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
    active_provider, active_api_key, active_model = _active_text_credentials()
    st.caption(f"Active AI provider: {provider_display_name(active_provider)} | Model: {active_model}")
    _warn_missing_provider_key(active_provider, active_api_key)
    with st.expander("Quick Start", expanded=False):
        st.markdown("**Quick Start**")
        st.markdown(
            "1. เลือก Music Preset  \n"
            "2. ใส่ไอเดียเพลงสั้น ๆ  \n"
            "3. กด Generate Full Lyrics  \n"
            "4. Copy หรือ Download Release Package"
        )
    creative_direction = project.get("creative_direction") or st.session_state.get("creative_direction", {}) or {}
    structure_plan = (project.get("song", {}) or {}).get("song_structure_plan") or project.get("song_structure_plan") or st.session_state.get("song_structure_plan", {}) or {}
    default_artist_id = load_default_artist_id()
    raw_song = project.get("song", {}) or {}
    raw_artist_id = raw_song.get("artist_preset")
    song = normalize_song_metadata(raw_song, get_artist_preset(raw_artist_id or default_artist_id))
    project["song"] = song
    current_artist_id = raw_artist_id or st.session_state.get("selected_artist_preset") or PUBLIC_DEFAULT_ARTIST_ID

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

    with st.expander("Song Structure Intelligence", expanded=False):
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
        preset = _select_artist_preset("song_studio", current_artist_id)
        st.session_state.selected_artist_preset = preset.get("artist_id", PUBLIC_DEFAULT_ARTIST_ID)
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
    current_project_folder = resolve_project_folder(project.get("title", "project"), project.get("workflow_type") or project.get("project_type"))
    export_dir = current_project_folder / "exports"
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
            api_key=active_api_key,
            model_name=active_model,
            provider=active_provider,
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
        _log_beta_event("generate", workflow="music", metadata={"page": "Song Studio"})
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
                api_key=active_api_key,
                model_name=active_model,
                provider=active_provider,
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
            active_api_key,
            active_model,
            idea_with_hook,
            genre,
            mood,
            vocal,
            viral,
            artist_preset=preset if use_preset else get_artist_preset("vela_moon"),
            music_style_override=final_style_prompt,
            force_english_instrument_tags=force_tags,
            provider=active_provider,
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
        _log_beta_event("generate", workflow="music", metadata={"page": "Song Studio"})
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
                    _log_beta_event("export", workflow="music", metadata={"format": "song_txt"})
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
                    _log_beta_event("export", workflow="music", metadata={"format": "song_txt"})
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
                    _log_beta_event("export", workflow="music", metadata={"format": "song_draft"})
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
            saved_folder = resolve_project_folder(project.get("title", title), project.get("workflow_type") or project.get("project_type"))
            st.json({
                "song_json": str(saved_folder / "song.json"),
                "lyrics_txt": str(saved_folder / "lyrics.txt"),
                "suno_full_package": str(saved_folder / "exports"),
                "lyrics_only": str(saved_folder / "exports" / "lyrics_only.txt"),
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
_restore_local_api_state()
if not st.session_state.get("beta_runtime_prepared"):
    cleanup_old_temp_exports(ttl_hours=48)
    st.session_state.beta_runtime_prepared = True
project = _project()

st.title(f"🎬 {APP_TITLE}")
st.caption(f"{PRODUCT_TAGLINE} by {BRAND_NAME} | {build_label()}")
if str(getattr(settings, "velaflow_mode", "LOCAL")).upper() == "CLOUD":
    st.caption("☁️ Internal Cloud Mode")

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
    "Podcast Studio": "marketing",
    "Viral Clips Studio": "clips",
    "Hook Clip Studio": "clips",
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
    workflow_options = ["Full Pipeline", "Song Studio Only", "Seller Studio (Beta)", "Podcast Studio (Beta)", "Viral Clips Studio (Beta)", "Hook Clip Studio (Beta)"]
    current_mode_for_select = st.session_state.get("workflow_mode", "Full Pipeline")
    if current_mode_for_select not in workflow_options:
        current_mode_for_select = "Full Pipeline"
    selected_mode = st.selectbox(
        "Workflow Mode",
        workflow_options,
        index=workflow_options.index(current_mode_for_select),
        key="workflow_mode_selector",
        help="Song Studio Only = fast songwriting. Full Pipeline = complete music release. Seller Studio = seller content. Podcast Studio = spoken story scripts. Viral Clips = short-form ideas.",
    )
    if selected_mode == "Song Studio Only":
        st.caption("Song Studio Only hides Creator Wizard and advanced pipeline tools for a faster songwriting workflow.")
    elif selected_mode == "Seller Studio (Beta)":
        st.caption("Seller Studio focuses on TikTok/Reels/Shorts product content and hides music pipeline tools.")
    elif selected_mode == "Podcast Studio (Beta)":
        st.caption("Podcast Studio creates Thai narration, story scripts, rant clips, and Shorts ideas.")
    elif selected_mode == "Viral Clips Studio (Beta)":
        st.caption("Viral Clips Studio turns any idea, song, product, or podcast topic into short-form content.")
    elif selected_mode == "Hook Clip Studio (Beta)":
        st.caption("Hook Clip Studio auto-builds 5-10 second vertical hook clips from any workflow.")
    else:
        st.caption("Full Pipeline enables Creator Wizard and full release workflow tools.")
    cloud_label = " · Internal Cloud Mode" if str(getattr(settings, "velaflow_mode", "LOCAL")).upper() == "CLOUD" else ""
    st.caption(f"VelaFlow Beta 0.1.0{cloud_label} · Review AI outputs before publishing · Render jobs are mock/local")
    st.caption("Workflow families ready: Music / Seller / Podcast / MV")
    if selected_mode != st.session_state.get("workflow_mode"):
        st.session_state.workflow_mode = selected_mode
        save_user_preferences({"workflow_mode": selected_mode})
        if not st.session_state.get("current_project") and _fix_display_text((st.session_state.project or {}).get("title", "")) in SONG_DEFAULT_TITLES:
            st.session_state.project = new_project(_workflow_default_name(selected_mode), DEFAULT_ARTIST, workflow_type_for_mode(selected_mode))
        if selected_mode == "Song Studio Only" and st.session_state.selected_page not in SONG_ONLY_ALLOWED_PAGES:
            st.session_state["pending_navigation"] = {"section": "START", "page": "Dashboard"}
        if selected_mode == "Seller Studio (Beta)" and st.session_state.selected_page not in SELLER_STUDIO_ALLOWED_PAGES:
            st.session_state["pending_navigation"] = {"section": "SELLER", "page": "Seller Studio"}
        if selected_mode == "Podcast Studio (Beta)" and st.session_state.selected_page not in PODCAST_STUDIO_ALLOWED_PAGES:
            st.session_state["pending_navigation"] = {"section": "PODCAST", "page": "Podcast Studio"}
        if selected_mode == "Viral Clips Studio (Beta)" and st.session_state.selected_page not in VIRAL_CLIPS_ALLOWED_PAGES:
            st.session_state["pending_navigation"] = {"section": "CLIPS", "page": "Viral Clips Studio"}
        if selected_mode == "Hook Clip Studio (Beta)" and st.session_state.selected_page not in HOOK_CLIP_ALLOWED_PAGES:
            st.session_state["pending_navigation"] = {"section": "CLIPS", "page": "Hook Clip Studio"}
        st.rerun()
    workflow_log_key = f"beta_workflow_seen_{selected_mode}"
    if not st.session_state.get(workflow_log_key):
        _log_beta_event("workflow_usage", _workflow_analytics_key(selected_mode), metadata={"workflow_mode": selected_mode})
        st.session_state[workflow_log_key] = True
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
        if current_workflow_mode == "Seller Studio (Beta)":
            st.info("No seller campaigns yet.")
        elif current_workflow_mode == "Podcast Studio (Beta)":
            st.info("No podcast episodes yet.")
        elif current_workflow_mode == "Hook Clip Studio (Beta)":
            st.info("No hook clip projects yet.")
        elif current_workflow_mode == "Viral Clips Studio (Beta)":
            st.info("No viral clips projects yet.")
        else:
            st.info("No songs yet. Create your first VelaFlow project.")
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
        st.caption(RELEASE_CHANNEL)
        st.caption(f"Package: {license_service.state.package}")
        st.caption(f"Expiry: {license_service.state.expires_at}")
        modules = [("Director", "director"), ("Motion", "motion"), ("Render", "render"), ("Clips", "clips"), ("Canvas", "canvas"), ("Marketing", "marketing")]
        st.caption(" | ".join(f"{'✅' if license_service.module_enabled(module) else '⚪'} {label}" for label, module in modules))
        st.caption(f"Build: {build_label()} / {BUILD_VERSION}")
        st.caption(f"Theme: {active_theme_name()}")
        st.caption(f"Render Profile: {st.session_state.render_profile}")
    st.caption(f"{RELEASE_CHANNEL} | {build_label()} / {BUILD_VERSION}")
    st.caption(f"Active workflow: {st.session_state.get('workflow_mode', 'Full Pipeline')}")
    st.caption(f"Active AI provider: {provider_display_name(_active_ai_provider())}")
    if st.session_state.get("debug_mode", False):
        st.caption(f"Current Section: {st.session_state.selected_section}")
        st.caption(f"Current Page: {st.session_state.selected_page}")
    st.divider()
    with st.expander("Provider Status", expanded=False):
        active_provider, active_api_key, active_model = _active_text_credentials()
        runtime = _provider_runtime_status(active_provider, active_api_key)
        st.caption(f"Active provider: {provider_display_name(active_provider)}")
        st.caption(f"API mode: {st.session_state.get('api_mode', API_MODE_OWN_KEY)}")
        st.caption(f"Active model: {active_model}")
        st.caption(f"Runtime status: {runtime['status']}")
        st.caption(runtime["message"])
        st.caption(f"Gemini model: {settings.gemini_model}")
        st.caption(f"OpenAI model: {settings.openai_text_model}")
        st.caption(f"xAI Grok model: {settings.xai_text_model}")
        st.success("Gemini configured") if settings.gemini_api_key else st.warning("Gemini not configured")
        st.success("OpenAI configured") if settings.openai_api_key else st.warning("OpenAI not configured")
        st.success("xAI Grok configured") if settings.xai_api_key else st.warning("xAI Grok not configured")
        resolved = _active_credential_status()
        st.caption(f"User Key: {'Provided' if resolved.get('user_key_present') else 'Missing'}")
        st.caption(f"VelaFlow Key: {'Configured' if resolved.get('velaflow_key_present') else 'Not configured'}")
        if not active_api_key:
            st.warning("Selected provider will use offline fallback")

if page == "Dashboard":
    _page_header("Dashboard", "Project overview, next step, and daily workflow shortcuts.", project)
    workflow_mode = st.session_state.get("workflow_mode", "Full Pipeline")
    active_provider, _, active_model = _active_text_credentials()
    st.caption(f"{RELEASE_CHANNEL} | Build {BUILD_VERSION} | Active workflow: {workflow_mode} | Active AI provider: {provider_display_name(active_provider)} ({active_model})")
    st.info("VelaFlow Beta 0.1.0 · AI outputs should be reviewed before publishing · Rendering jobs are currently mock/local.", icon="ℹ️")
    is_seller_mode = workflow_mode == "Seller Studio (Beta)"
    is_podcast_mode = workflow_mode == "Podcast Studio (Beta)"
    is_clips_mode = workflow_mode in {"Viral Clips Studio (Beta)", "Hook Clip Studio (Beta)"}
    if is_seller_mode:
        status = build_seller_dashboard_status(project)
    elif is_podcast_mode:
        status = build_podcast_dashboard_status(project)
    elif is_clips_mode:
        status = build_viral_clips_dashboard_status(project)
    else:
        status = build_project_status(project)
    status_data = status.get("data", {}) or {}
    next_step = status.get("next_step", {}) or {}
    audit = {} if (is_seller_mode or is_podcast_mode or is_clips_mode) else run_full_project_audit(project)
    c1, c2, c3, c4 = st.columns(4)
    if is_seller_mode:
        c1.metric("Campaign", status_data.get("campaign_name") or _seller_campaign_name(project))
        c2.metric("Product", status_data.get("product_name") or "No product selected")
        c3.metric("Content Items", status_data.get("content_items", 0))
        c4.metric("Next Step", next_step.get("stage", "Seller Content"))
        st.caption(f"Workflow Mode: {workflow_mode} | Seller package: {status.get('message', '')} | Build {APP_VERSION}")
    elif is_podcast_mode:
        c1.metric("Episode", status_data.get("episode_title") or project.get("title", "ตอนใหม่ของฉัน"))
        c2.metric("Topic", status_data.get("topic") or "No topic selected")
        c3.metric("Content Items", status_data.get("content_items", 0))
        c4.metric("Next Step", next_step.get("stage", "Podcast Script"))
        st.caption(f"Workflow Mode: {workflow_mode} | Podcast package: {status.get('message', '')} | Build {APP_VERSION}")
    elif is_clips_mode:
        c1.metric("Clip Project", status_data.get("campaign_name") or project.get("title", "คลิปไวรัลใหม่"))
        c2.metric("Idea", status_data.get("main_idea") or "No idea selected")
        c3.metric("Content Items", status_data.get("content_items", 0))
        c4.metric("Next Step", next_step.get("stage", "Viral Clips"))
        st.caption(f"Workflow Mode: {workflow_mode} | Viral clips package: {status.get('message', '')} | Build {APP_VERSION}")
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
        fallback_target = "Seller Studio" if is_seller_mode else ("Podcast Studio" if is_podcast_mode else ("Viral Clips Studio" if is_clips_mode else "Song Studio"))
        target = next_step.get("page", fallback_target)
        target = target if target in PAGES else fallback_target
        go_to_page(_section_for_page(target), target)
    if action_cols[1].button("Save Project", use_container_width=True):
        _save_project()
        st.success("Project saved")
    if action_cols[2].button("Export Report", use_container_width=True):
        st.json(export_project_report(project), expanded=False)
    if action_cols[3].button("Clean Safe Temp", use_container_width=True):
        st.json(clean_safe_temp_files(project), expanded=False)
    st.write("Seller Status" if is_seller_mode else ("Podcast Status" if is_podcast_mode else ("Viral Clips Status" if is_clips_mode else "Project Status")))
    st.dataframe(pd.DataFrame(status_data.get("stages", []) or []), use_container_width=True, height=220)
    cols = st.columns(6)
    if is_seller_mode:
        navs = [("Seller Studio", "Seller Studio"), ("System Health", "System Health"), ("AI Settings", "AI Settings")]
    elif is_podcast_mode:
        navs = [("Podcast Studio", "Podcast Studio"), ("System Health", "System Health"), ("AI Settings", "AI Settings")]
    elif is_clips_mode:
        navs = [("Viral Clips Studio", "Viral Clips Studio"), ("System Health", "System Health"), ("AI Settings", "AI Settings")]
    else:
        navs = [
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
    elif is_podcast_mode:
        with st.expander("Podcast Export Snapshot", expanded=False):
            podcast = (project.get("podcast_studio", {}) or {}).get("content_package", {}) or {}
            export_data = (project.get("podcast_studio", {}) or {}).get("export", {}) or {}
            st.caption(f"Episode title: {podcast.get('episode_title') or '-'}")
            st.caption(f"TXT package: {export_data.get('txt_path') or 'not exported'}")
    elif is_clips_mode:
        with st.expander("Viral Clips Export Snapshot", expanded=False):
            clips = (project.get("viral_clips_studio", {}) or {}).get("content_package", {}) or {}
            export_data = (project.get("viral_clips_studio", {}) or {}).get("export", {}) or {}
            st.caption(f"Main idea: {clips.get('main_idea') or '-'}")
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
    active_provider, active_api_key, active_model = _active_text_credentials()
    st.caption(f"Active AI provider: {provider_display_name(active_provider)} | Offline-safe seller generator")
    _warn_missing_provider_key(active_provider, active_api_key)
    seller_existing = project.get("seller_studio", {}) or {}
    _, seller_bundle_visual, seller_bundle_render = _bundle_controls("seller", seller_existing.get("render_settings") or {"bundle_name": "Luxury Product"})
    seller_visual_defaults = seller_bundle_visual or seller_existing.get("visual_settings") or {"camera_preset": "TikTok Creator", "lighting_preset": "Clean Studio", "motion_preset": "Smooth Product Showcase", "visual_mood": "Premium"}
    seller_render_defaults = seller_bundle_render or seller_existing.get("render_settings") or {"provider": "Runway", "aspect_ratio": "9:16", "duration": "15s", "quality": "Standard", "motion_intensity": "Medium"}
    seller_visual_settings = _visual_controls("seller", seller_visual_defaults)
    seller_render_settings = _render_settings_controls("seller", seller_render_defaults)
    c1, c2 = st.columns([1, 1])
    with c1:
        product_link = st.text_input("Product Link (Shopee / TikTok Shop)", value=(seller_existing.get("product_link") or ""), help="วางลิงก์สินค้าเพื่อให้ระบบเดา metadata แบบ local-only ไม่ scrape เว็บ")
        link_notes = st.text_area("Product Link Notes", value=(seller_existing.get("product_link_notes") or ""), height=70, help="ใส่ข้อมูลจากหน้าสินค้าที่อยากให้ระบบใช้ เช่น ราคา จุดเด่น หรือคำเคลม")
        if st.button("Analyze Product Link", use_container_width=True):
            link_result = analyze_product_link(product_link, link_notes)
            project.setdefault("seller_studio", {})["product_link"] = product_link
            project["seller_studio"]["product_link_notes"] = link_notes
            project["seller_studio"]["product_link_metadata"] = link_result.get("data", {})
            _save_project()
            st.success("Product link analyzed locally")
            st.json(link_result.get("data", {}), expanded=False)
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
        hook_style = st.selectbox("Hook Style", HOOK_STYLES, index=0, help="เลือกมุมเปิดคลิป เช่น แก้ปัญหา รีวิว POV หรือ soft sell")
        key_points = st.text_area(
            "Key Selling Points",
            value=st.session_state.get("seller_key_points", ""),
            height=140,
            help="ใส่จุดขายทีละบรรทัด เช่น ใช้ง่าย ประหยัดเวลา เห็นผลไว คุ้มราคา",
        )
        st.info(TONE_GUIDES.get(tone_style, ""), icon="ℹ️")

    if st.button("Generate Seller Content", type="primary", use_container_width=True):
        product_image_meta = (project.get("seller_studio", {}) or {}).get("product_image", {}) or {}
        result = generate_seller_content(
            product_name,
            product_category,
            target_audience,
            key_points,
            tone_style,
            product_image=product_image_meta,
            hook_style=hook_style,
            visual_settings=seller_visual_settings,
            provider=active_provider,
            api_key=active_api_key,
            model_name=active_model,
        )
        if result.get("ok"):
            package = result["data"]
            package["active_ai_provider"] = active_provider
            package["active_ai_model"] = active_model
            st.session_state.seller_product_name = package.get("product_name", "")
            st.session_state.seller_product_category = package.get("product_category", "")
            st.session_state.seller_target_audience = package.get("target_audience", "")
            st.session_state.seller_key_points = "\n".join(package.get("key_selling_points", []))
            project.setdefault("seller_studio", {})["product_image"] = package.get("product_image", product_image_meta)
            project.setdefault("seller_studio", {})["visual_settings"] = seller_visual_settings
            project.setdefault("seller_studio", {})["render_settings"] = seller_render_settings
            project.setdefault("seller_studio", {})["content_package"] = package
            export_result = export_seller_content(project.get("title") or package.get("product_name"), package)
            project["seller_studio"]["export"] = export_result.get("data", {})
            render_export = _attach_render_connector(project.get("title") or package.get("product_name"), "seller_studio", "seller", package, seller_render_settings, seller_visual_settings)
            _save_project()
            _log_beta_event("generate", workflow="seller", preset_bundle=str(seller_render_settings.get("bundle_name") or ""), metadata={"page": "Seller Studio"})
            if export_result.get("ok"):
                _log_beta_event("export", workflow="seller", metadata={"format": "txt_json"})
            st.success("Seller content package generated")
            if export_result.get("ok"):
                st.caption(f"Export: {export_result['data'].get('txt_path')}")
            else:
                st.warning(export_result.get("message", "Export failed"))
            if render_export.get("ok"):
                st.caption(f"Render package: {render_export['data'].get('txt_path')}")
        else:
            st.error(result.get("error") or result.get("message", "Seller content generation failed"))

    seller_package = ((project.get("seller_studio", {}) or {}).get("content_package") or st.session_state.get("seller_content_package") or {})
    _render_package_preview(((project.get("seller_studio", {}) or {}).get("render_connector") or {}))
    if seller_package:
        st.write("Seller Content Package")
        t1, t2, t3 = st.tabs(["Content", "Video Prompt", "Export"])
        with t1:
            st.markdown("**Compressed Benefits**")
            st.write(", ".join(seller_package.get("compressed_benefits", [])) or "-")
            st.caption(f"Hook Style: {seller_package.get('hook_style', '-')}")
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
            render_path = (((project.get("seller_studio", {}) or {}).get("render_connector") or {}).get("export") or {}).get("txt_path")
            if export_path:
                st.caption(f"Export path: {export_path}")
            if render_path:
                st.caption(f"Render package: {render_path}")
            st.download_button(
                "Download seller_content_package.txt",
                data=export_text.encode("utf-8"),
                file_name="seller_content_package.txt",
                mime="text/plain",
                use_container_width=True,
            )
            st.text_area("Copy-ready package", value=export_text, height=260)
        with st.expander("🎬 Hook Clip Preview", expanded=False):
            if st.button("Generate Hook Clip", key="seller_hook_clip_btn", use_container_width=True):
                result = build_hook_render_package(project.get("title") or seller_package.get("product_name") or "seller_hook_clip", "seller", seller_package, visual_settings=seller_visual_settings, render_settings=seller_render_settings)
                if result.get("ok"):
                    project.setdefault("seller_studio", {})["hook_clip"] = result["data"]["package"]
                    _save_project()
                    _log_beta_event("generate", workflow="seller", preset_bundle="Hook Clip", metadata={"page": "Seller Studio"})
                    st.success("Hook clip package generated")
            _render_hook_clip_preview(((project.get("seller_studio", {}) or {}).get("hook_clip") or {}))
            _render_real_clip_controls(project, "seller_studio", ((project.get("seller_studio", {}) or {}).get("hook_clip") or {}), "seller")
    with st.expander("Render Queue", expanded=False):
        _render_queue_ui(project.get("title") or (seller_package or {}).get("product_name") or "seller_project")

elif page == "Podcast Studio":
    _page_header("Podcast Studio", "Create Thai spoken podcast, storytelling, rant, and Shorts-ready narration packages.", project)
    st.caption("Beta workflow: no voice synthesis, no audio rendering, and no automation. This creates scripts and prompts only.")
    active_provider, active_api_key, active_model = _active_text_credentials()
    st.caption(f"Active AI provider: {provider_display_name(active_provider)} | Offline-safe podcast generator")
    _warn_missing_provider_key(active_provider, active_api_key)
    podcast_existing = project.get("podcast_studio", {}) or {}
    _, podcast_bundle_visual, podcast_bundle_render = _bundle_controls("podcast", podcast_existing.get("render_settings") or {"bundle_name": "Podcast Dark Office"})
    podcast_visual_defaults = podcast_bundle_visual or podcast_existing.get("visual_settings") or {"camera_preset": "Documentary", "lighting_preset": "Soft Indoor", "motion_preset": "Documentary Realism", "visual_mood": "Dark Office"}
    podcast_render_defaults = podcast_bundle_render or podcast_existing.get("render_settings") or {"provider": "Luma", "aspect_ratio": "9:16", "duration": "10s", "quality": "Standard", "motion_intensity": "Low"}
    podcast_visual_settings = _visual_controls("podcast", podcast_visual_defaults)
    podcast_render_settings = _render_settings_controls("podcast", podcast_render_defaults)
    c1, c2 = st.columns([1, 1])
    podcast_state = project.get("podcast_studio", {}) or {}
    existing_package = podcast_state.get("content_package", {}) or {}
    with c1:
        podcast_topic = st.text_input(
            "Podcast Topic",
            value=st.session_state.get("podcast_topic", existing_package.get("podcast_topic", "")),
            help="หัวข้อหลักของตอน เช่น เรื่องออฟฟิศ ความรัก การเติบโต หรือเรื่องระบาย",
        )
        episode_theme = st.text_area(
            "Episode Theme",
            value=st.session_state.get("podcast_episode_theme", existing_package.get("episode_theme", "")),
            height=110,
            help="แก่นของตอนนี้ อยากให้คนฟังรู้สึกหรือได้อะไรหลังฟังจบ",
        )
        target_audience = st.text_input(
            "Target Audience",
            value=st.session_state.get("podcast_target_audience", existing_package.get("target_audience", "")),
            help="คนฟังหลัก เช่น คนทำงาน นักศึกษา คนอกหัก หรือคนที่กำลังหมดไฟ",
        )
    with c2:
        story_tone = st.selectbox(
            "Story Tone",
            STORY_TONES,
            index=STORY_TONES.index(existing_package.get("story_tone")) if existing_package.get("story_tone") in STORY_TONES else 0,
            help="เลือกโทนการเล่า เช่น emotional, funny, dark office หรือ viral rant",
        )
        episode_length = st.selectbox(
            "Episode Length",
            EPISODE_LENGTHS,
            index=EPISODE_LENGTHS.index(existing_package.get("episode_length")) if existing_package.get("episode_length") in EPISODE_LENGTHS else 1,
            help="กำหนดความยาวเป้าหมายของสคริปต์",
        )
        narration_style = st.selectbox(
            "Narration Style",
            NARRATION_STYLES,
            index=NARRATION_STYLES.index(existing_package.get("narration_style")) if existing_package.get("narration_style") in NARRATION_STYLES else 0,
            help="เลือกวิธีเล่า เช่น calm storytelling, deep emotional หรือ documentary style",
        )
        st.info("เหมาะสำหรับคลิปเล่าเรื่อง, podcast intro, viral rant, YouTube Shorts และ TikTok spoken content.", icon="ℹ️")

    if st.button("Generate Podcast Episode", type="primary", use_container_width=True):
        result = generate_podcast_content(podcast_topic, episode_theme, story_tone, target_audience, episode_length, narration_style, visual_settings=podcast_visual_settings)
        if result.get("ok"):
            package = result["data"]
            package["active_ai_provider"] = active_provider
            package["active_ai_model"] = active_model
            st.session_state.podcast_topic = package.get("podcast_topic", "")
            st.session_state.podcast_episode_theme = package.get("episode_theme", "")
            st.session_state.podcast_target_audience = package.get("target_audience", "")
            project.setdefault("podcast_studio", {})["content_package"] = package
            project.setdefault("podcast_studio", {})["visual_settings"] = podcast_visual_settings
            project.setdefault("podcast_studio", {})["render_settings"] = podcast_render_settings
            export_result = export_podcast_content(project.get("title") or package.get("episode_title"), package)
            project["podcast_studio"]["export"] = export_result.get("data", {})
            render_export = _attach_render_connector(project.get("title") or package.get("episode_title"), "podcast_studio", "podcast", package, podcast_render_settings, podcast_visual_settings)
            _save_project()
            _log_beta_event("generate", workflow="podcast", preset_bundle=str(podcast_render_settings.get("bundle_name") or ""), metadata={"page": "Podcast Studio"})
            if export_result.get("ok"):
                _log_beta_event("export", workflow="podcast", metadata={"format": "txt_json"})
            st.success("Podcast episode package generated")
            if export_result.get("ok"):
                st.caption(f"Export: {export_result['data'].get('txt_path')}")
            else:
                st.warning(export_result.get("message", "Export failed"))
            if render_export.get("ok"):
                st.caption(f"Render package: {render_export['data'].get('txt_path')}")
        else:
            st.error(result.get("error") or result.get("message", "Podcast generation failed"))

    podcast_package = ((project.get("podcast_studio", {}) or {}).get("content_package") or {})
    _render_package_preview(((project.get("podcast_studio", {}) or {}).get("render_connector") or {}))
    if podcast_package:
        st.write("Podcast Episode Package")
        t1, t2, t3 = st.tabs(["Script", "Shorts & Prompts", "Export"])
        with t1:
            st.markdown("**Episode Hooks**")
            for item in podcast_package.get("episode_hooks", []):
                st.write(f"- {item}")
            st.markdown("**Podcast Intro**")
            for idx, item in enumerate(podcast_package.get("podcast_intro", []), start=1):
                st.write(f"{idx}. {item}")
            st.markdown("**Main Script**")
            for idx, item in enumerate(podcast_package.get("main_script", []), start=1):
                st.write(f"{idx}. {item}")
            with st.expander("Emotional Monologue", expanded=False):
                st.write("\n".join(podcast_package.get("emotional_monologue", [])))
            with st.expander("Viral Rant Version", expanded=False):
                st.write("\n".join(podcast_package.get("viral_rant_version", [])))
        with t2:
            st.markdown("**Shorts Extraction Ideas**")
            for item in podcast_package.get("shorts_extraction_ideas", []):
                st.write(f"- {item}")
            st.markdown("**TikTok Clip Hooks**")
            for item in podcast_package.get("tiktok_clip_hooks", []):
                st.write(f"- {item}")
            st.markdown("**Episode Title Ideas**")
            for item in podcast_package.get("episode_title_ideas", []):
                st.write(f"- {item}")
            st.text_area("YouTube Description", value=podcast_package.get("youtube_description", ""), height=150)
            st.text_area("Hashtags", value=" ".join(podcast_package.get("hashtags", [])), height=80)
            st.text_area("AI Video Prompt", value=podcast_package.get("ai_video_prompt", ""), height=130)
            st.text_area("Thumbnail Prompt", value=podcast_package.get("thumbnail_prompt", ""), height=110)
        with t3:
            export_text = podcast_content_to_text(podcast_package)
            export_path = ((project.get("podcast_studio", {}) or {}).get("export") or {}).get("txt_path")
            render_path = (((project.get("podcast_studio", {}) or {}).get("render_connector") or {}).get("export") or {}).get("txt_path")
            if export_path:
                st.caption(f"Export path: {export_path}")
            if render_path:
                st.caption(f"Render package: {render_path}")
            st.download_button(
                "Download podcast_episode_package.txt",
                data=export_text.encode("utf-8"),
                file_name="podcast_episode_package.txt",
                mime="text/plain",
                use_container_width=True,
            )
            st.text_area("Copy-ready package", value=export_text, height=280)
        with st.expander("🎙️ Voiceover / Hook Clip", expanded=False):
            voice_style = st.selectbox("Voiceover Style", VOICEOVER_STYLES, index=0, key="podcast_voiceover_style")
            if st.button("Generate Voiceover Plan", key="podcast_voiceover_btn", use_container_width=True):
                script_lines = podcast_package.get("main_script", []) or podcast_package.get("emotional_monologue", [])
                plan = build_voiceover_plan(script_lines, voice_style)
                export_result = export_voiceover_plan(project.get("title") or podcast_package.get("episode_title") or "podcast_voiceover", plan)
                project.setdefault("podcast_studio", {})["voiceover_plan"] = plan
                project["podcast_studio"]["voiceover_export"] = export_result.get("data", {})
                _save_project()
                st.success("Voiceover script/timing exported")
            if st.button("Generate Hook Clip", key="podcast_hook_clip_btn", use_container_width=True):
                result = build_hook_render_package(project.get("title") or podcast_package.get("episode_title") or "podcast_hook_clip", "podcast", podcast_package, visual_settings=podcast_visual_settings, render_settings=podcast_render_settings)
                if result.get("ok"):
                    project.setdefault("podcast_studio", {})["hook_clip"] = result["data"]["package"]
                    _save_project()
                    _log_beta_event("generate", workflow="podcast", preset_bundle="Hook Clip", metadata={"page": "Podcast Studio"})
                    st.success("Hook clip package generated")
            _render_hook_clip_preview(((project.get("podcast_studio", {}) or {}).get("hook_clip") or {}))
            _render_real_clip_controls(project, "podcast_studio", ((project.get("podcast_studio", {}) or {}).get("hook_clip") or {}), "podcast", default_voice_style="tired office worker")
    with st.expander("Render Queue", expanded=False):
        _render_queue_ui(project.get("title") or (podcast_package or {}).get("episode_title") or "podcast_project")

elif page == "Viral Clips Studio":
    _page_header("Viral Clips Studio", "Turn any idea, song, product, or podcast topic into concise short-form content.", project)
    st.caption("Beta workflow: no video rendering, scraping, auto posting, or login. This creates copy-ready clip ideas and prompts.")
    active_provider, active_api_key, active_model = _active_text_credentials()
    st.caption(f"Active AI provider: {provider_display_name(active_provider)} | Model: {active_model}")
    _warn_missing_provider_key(active_provider, active_api_key)
    clips_existing = project.get("viral_clips_studio", {}) or {}
    _, clips_bundle_visual, clips_bundle_render = _bundle_controls("viral_clips", clips_existing.get("render_settings") or {"bundle_name": "TikTok Viral"})
    clips_visual_defaults = clips_bundle_visual or clips_existing.get("visual_settings") or {"camera_preset": "TikTok Creator", "lighting_preset": "Natural Daylight", "motion_preset": "Fast TikTok Cuts", "visual_mood": "Viral"}
    clips_render_defaults = clips_bundle_render or clips_existing.get("render_settings") or {"provider": "PixVerse", "aspect_ratio": "9:16", "duration": "15s", "quality": "Draft", "motion_intensity": "High"}
    clips_visual_settings = _visual_controls("viral_clips", clips_visual_defaults)
    clips_render_settings = _render_settings_controls("viral_clips", clips_render_defaults)
    clips_state = project.get("viral_clips_studio", {}) or {}
    existing_package = clips_state.get("content_package", {}) or {}
    c1, c2 = st.columns([1, 1])
    with c1:
        source_type = st.selectbox(
            "Source Type",
            SOURCE_TYPES,
            index=SOURCE_TYPES.index(existing_package.get("source_type")) if existing_package.get("source_type") in SOURCE_TYPES else 0,
            help="เลือกต้นทางไอเดีย เช่น เพลง สินค้า พอดแคสต์ หรือไอเดียทั่วไป",
        )
        character_style = st.selectbox(
            "Viral Character Style",
            ["none", "cute", "sarcastic", "emotional", "chaotic", "sleepy", "dramatic", "overconfident"],
            index=0,
            help="เลือกบุคลิกตัวละครไวรัล เช่น ของกินพูดได้ วัตถุพูดได้ หรือคาแรกเตอร์มีม",
        )
        main_idea = st.text_area(
            "Main Idea",
            value=st.session_state.get("viral_main_idea", existing_package.get("main_idea", "")),
            height=120,
            help="ใส่ใจความหลักของคลิป ยิ่งชัด ระบบยิ่งสร้าง hook ได้ตรง",
        )
        target_platform = st.selectbox(
            "Target Platform",
            TARGET_PLATFORMS,
            index=TARGET_PLATFORMS.index(existing_package.get("target_platform")) if existing_package.get("target_platform") in TARGET_PLATFORMS else 0,
            help="เลือกแพลตฟอร์มหลักเพื่อปรับจังหวะและรูปแบบคำ",
        )
    with c2:
        tone_style = st.selectbox(
            "Tone Style",
            CLIP_TONE_STYLES,
            index=CLIP_TONE_STYLES.index(existing_package.get("tone_style")) if existing_package.get("tone_style") in CLIP_TONE_STYLES else 0,
            help="เลือกโทน เช่น emotional, funny, review หรือ viral energy",
        )
        clip_length = st.selectbox(
            "Clip Length",
            CLIP_LENGTHS,
            index=CLIP_LENGTHS.index(existing_package.get("clip_length")) if existing_package.get("clip_length") in CLIP_LENGTHS else 1,
            help="กำหนดความยาวคลิปเป้าหมาย",
        )
        goal = st.selectbox(
            "Goal",
            GOALS,
            index=GOALS.index(existing_package.get("goal")) if existing_package.get("goal") in GOALS else 3,
            help="เลือกเป้าหมาย เช่น สร้างการรับรู้ ขายของ เล่าเรื่อง หรือไวรัล",
        )
        st.info("เหมาะสำหรับ TikTok / Reels / Shorts และใช้ได้กับเพลง สินค้า พอดแคสต์ หรือไอเดียทั่วไป", icon="ℹ️")

    if st.button("Generate Viral Clips Package", type="primary", use_container_width=True):
        viral_idea = main_idea
        if character_style != "none":
            viral_idea = f"{main_idea}\n\nViral character style: {character_style}. Automatically create character personality, dialogue, subtitle pacing, hook moments, and short vertical scene story."
        result = generate_viral_clips_content(
            source_type,
            viral_idea,
            target_platform,
            tone_style,
            clip_length,
            goal,
            provider=active_provider,
            api_key=active_api_key,
            model_name=active_model,
            visual_settings=clips_visual_settings,
        )
        if result.get("ok"):
            package = result["data"]
            st.session_state.viral_main_idea = package.get("main_idea", "")
            project.setdefault("viral_clips_studio", {})["content_package"] = package
            project.setdefault("viral_clips_studio", {})["visual_settings"] = clips_visual_settings
            project.setdefault("viral_clips_studio", {})["render_settings"] = clips_render_settings
            export_result = export_viral_clips_content(project.get("title") or package.get("main_idea"), package)
            project["viral_clips_studio"]["export"] = export_result.get("data", {})
            render_export = _attach_render_connector(project.get("title") or package.get("main_idea"), "viral_clips_studio", "clips", package, clips_render_settings, clips_visual_settings)
            _save_project()
            _log_beta_event("generate", workflow="viral_clips", preset_bundle=str(clips_render_settings.get("bundle_name") or ""), metadata={"page": "Viral Clips Studio"})
            if export_result.get("ok"):
                _log_beta_event("export", workflow="viral_clips", metadata={"format": "txt_json"})
            st.success("Viral clips package generated")
            if export_result.get("ok"):
                st.caption(f"Export: {export_result['data'].get('txt_path')}")
            else:
                st.warning(export_result.get("message", "Export failed"))
            if render_export.get("ok"):
                st.caption(f"Render package: {render_export['data'].get('txt_path')}")
        else:
            st.error(result.get("error") or result.get("message", "Viral clips generation failed"))

    clips_package = ((project.get("viral_clips_studio", {}) or {}).get("content_package") or {})
    _render_package_preview(((project.get("viral_clips_studio", {}) or {}).get("render_connector") or {}))
    if clips_package:
        st.write("Viral Clips Package")
        t1, t2, t3 = st.tabs(["Content", "Prompts", "Export"])
        with t1:
            st.markdown("**Viral Hooks**")
            for item in clips_package.get("viral_hooks", []):
                st.write(f"- {item}")
            st.markdown("**Short Script**")
            for idx, item in enumerate(clips_package.get("short_script", []), start=1):
                st.write(f"{idx}. {item}")
            st.markdown("**Subtitle Lines**")
            for item in clips_package.get("subtitle_lines", []):
                st.write(f"- {item}")
            st.text_area("Caption", value=clips_package.get("caption", ""), height=90)
            st.text_area("Hashtags", value=" ".join(clips_package.get("hashtags", [])), height=80)
            st.markdown("**CTA**")
            st.write(clips_package.get("cta", "-"))
        with t2:
            st.markdown("**Scene Ideas**")
            for item in clips_package.get("scene_ideas", []):
                st.write(f"- {item}")
            st.markdown("**B-roll Ideas**")
            for item in clips_package.get("broll_ideas", []):
                st.write(f"- {item}")
            st.text_area("AI Video Prompt", value=clips_package.get("ai_video_prompt", ""), height=130)
            st.text_area("Thumbnail Prompt", value=clips_package.get("thumbnail_prompt", ""), height=110)
        with t3:
            export_text = viral_clips_to_text(clips_package)
            export_path = ((project.get("viral_clips_studio", {}) or {}).get("export") or {}).get("txt_path")
            render_path = (((project.get("viral_clips_studio", {}) or {}).get("render_connector") or {}).get("export") or {}).get("txt_path")
            if export_path:
                st.caption(f"Export path: {export_path}")
            if render_path:
                st.caption(f"Render package: {render_path}")
            st.download_button(
                "Download viral_clips_package.txt",
                data=export_text.encode("utf-8"),
                file_name="viral_clips_package.txt",
                mime="text/plain",
                use_container_width=True,
            )
            st.text_area("Copy-ready package", value=export_text, height=280)
        with st.expander("🎬 Hook Clip Preview", expanded=False):
            if st.button("Generate Hook Clip", key="viral_hook_clip_btn", use_container_width=True):
                result = build_hook_render_package(project.get("title") or clips_package.get("main_idea") or "viral_hook_clip", "viral_clips", clips_package, visual_settings=clips_visual_settings, render_settings=clips_render_settings)
                if result.get("ok"):
                    project.setdefault("viral_clips_studio", {})["hook_clip"] = result["data"]["package"]
                    _save_project()
                    _log_beta_event("generate", workflow="viral_clips", preset_bundle="Hook Clip", metadata={"page": "Viral Clips Studio"})
                    st.success("Hook clip package generated")
            _render_hook_clip_preview(((project.get("viral_clips_studio", {}) or {}).get("hook_clip") or {}))
            _render_real_clip_controls(project, "viral_clips_studio", ((project.get("viral_clips_studio", {}) or {}).get("hook_clip") or {}), "viral_clips", default_voice_style="meme voice")
    with st.expander("Render Queue", expanded=False):
        _render_queue_ui(project.get("title") or (clips_package or {}).get("main_idea") or "viral_clips_project")

elif page == "Hook Clip Studio":
    _page_header("Hook Clip Studio", "Automatically build 5-10 second vertical hook clips from any workflow.", project)
    st.caption("Cloud Beta: create hook scenes, render packages, optional BYO-provider payloads, and a real local MP4 output with FFmpeg.")
    sources = _hook_source_options(project)
    default_source = "Seller" if project.get("seller_studio") else "Podcast" if project.get("podcast_studio") else "Viral Clips" if project.get("viral_clips_studio") else "Music"
    source_label = st.selectbox("Hook Source", list(sources), index=list(sources).index(default_source) if default_source in sources else 0)
    source_workflow = _hook_workflow_key(source_label)
    source_content = sources.get(source_label) or {}
    manual_hook = st.text_area("Optional Hook / Quote Override", value="", height=90, help="ถ้ามีประโยคเด็ด ให้ใส่ตรงนี้ ระบบจะใช้แทนการ detect อัตโนมัติ")
    clip_mode = st.selectbox("Clip Mode", ["Fast Hook", "Viral Clip", "Story Clip"], index=0)
    duration = st.slider("Duration", 5, 10, 8)
    _, hook_bundle_visual, hook_bundle_render = _bundle_controls("hook_clip", {"bundle_name": "TikTok Viral"})
    visual_defaults = hook_bundle_visual or {"camera_preset": "TikTok Creator", "lighting_preset": "Natural Daylight", "motion_preset": "Fast TikTok Cuts", "visual_mood": "Viral"}
    render_defaults = hook_bundle_render or {"provider": "PixVerse", "aspect_ratio": "9:16", "duration": f"{duration}s", "quality": "Draft", "motion_intensity": "High"}
    hook_visual_settings = _visual_controls("hook_clip", visual_defaults)
    hook_render_settings = _render_settings_controls("hook_clip", {**render_defaults, "duration": f"{duration}s"})
    if st.button("🎬 Generate Hook Clip", type="primary", use_container_width=True):
        content = {"selected_hook_text": manual_hook} if manual_hook.strip() else source_content
        result = build_hook_render_package(
            project.get("title") or _workflow_default_name("Hook Clip Studio (Beta)"),
            source_workflow,
            content,
            visual_settings=hook_visual_settings,
            render_settings=hook_render_settings,
            clip_mode=clip_mode,
            duration_seconds=duration,
        )
        if result.get("ok"):
            package = result["data"]["package"]
            project.setdefault("hook_clip_studio", {})["hook_clip"] = package
            project["hook_clip_studio"]["source"] = source_label
            project["hook_clip_studio"]["export"] = result["data"].get("export", {})
            _save_project()
            _log_beta_event("generate", workflow="hook_clip", preset_bundle=str(hook_render_settings.get("bundle_name") or ""), metadata={"page": "Hook Clip Studio"})
            st.success("Hook clip package generated")
        else:
            st.error(result.get("error") or result.get("message"))
    hook_package = ((project.get("hook_clip_studio", {}) or {}).get("hook_clip") or {})
    _render_hook_clip_preview(hook_package)
    if hook_package:
        t1, t2 = st.tabs(["Export", "Render"])
        with t1:
            text = hook_clip_package_to_text(hook_package)
            export_data = ((project.get("hook_clip_studio", {}) or {}).get("export") or {})
            if export_data.get("txt_path"):
                st.caption(f"Hook package: {export_data.get('txt_path')}")
            st.download_button("Download hook_clip_package.txt", data=text.encode("utf-8"), file_name="hook_clip_package.txt", mime="text/plain", use_container_width=True)
            st.text_area("Copy-ready hook package", value=text, height=260)
        with t2:
            _render_package_preview({"package": hook_package.get("render_connector_package", {}), "export": hook_package.get("render_connector_export", {})})
            _render_real_clip_controls(project, "hook_clip_studio", hook_package, source_workflow, default_voice_style="meme voice" if source_workflow == "viral_clips" else "calm narrator")
            with st.expander("Render Queue", expanded=True):
                _render_queue_ui(project.get("title") or "hook_clip_project")

elif page == "Creator Wizard":
    _page_header("Creator Wizard", "Guided creative setup for starting a song idea before Song Studio.", project)

    c1, c2 = st.columns([1, 1])
    with c1:
        project_name = st.text_input("Project Name", value=project.get("title", ""), key="wizard_project_name")
        topic = st.selectbox("Step 1: Song Topic", TOPIC_OPTIONS, key="wizard_topic_select")
        custom_topic = st.text_input("Custom Topic", value="", disabled=topic != "Custom", key="wizard_custom_topic")
        mood_choice = st.selectbox("Step 2: Mood", MOOD_OPTIONS, index=0, key="wizard_mood_select")
        music_direction = st.selectbox("Step 3: Music Direction", MUSIC_DIRECTION_OPTIONS, index=0, key="wizard_music_direction_select")
    with c2:
        st.write("Step 4: Artist Preset")
        selected_preset = _select_artist_preset("wizard", st.session_state.get("selected_artist_preset") or PUBLIC_DEFAULT_ARTIST_ID)
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
    mv_existing = project.get("mv", {}) or {}
    _, mv_bundle_visual, mv_bundle_render = _bundle_controls("mv_director", mv_existing.get("render_settings") or {"bundle_name": "Cinematic Sad"})
    if mv_bundle_render and not mv_existing.get("render_settings"):
        mv_bundle_render["aspect_ratio"] = "9:16"
    mv_visual_defaults = mv_bundle_visual or mv_existing.get("visual_settings") or {"camera_preset": "Cinematic", "lighting_preset": "Neon Night", "motion_preset": "Slow Cinematic", "visual_mood": "Emotional"}
    mv_render_defaults = mv_bundle_render or mv_existing.get("render_settings") or {"provider": "Runway", "aspect_ratio": "9:16", "duration": "10s", "quality": "Cinematic", "motion_intensity": "Medium"}
    mv_visual_settings = _visual_controls("mv_director", mv_visual_defaults)
    mv_render_settings = _render_settings_controls("mv_director", mv_render_defaults)
    title = st.text_input("Song Title", value=project.get("title", "เพลงใหม่ของฉัน"))
    artist = st.text_input("Artist", value=project.get("artist", DEFAULT_ARTIST), key="mv_artist")
    lyrics = st.text_area("Lyrics", value=_current_lyrics(), height=320)
    style = st.text_input("Visual Style", value="cinematic emotional Thai pop rock MV")
    scene_count = st.slider("Scene Count", 4, 32, 12)
    c1, c2 = st.columns(2)
    if c1.button("Generate MV Director Plan", type="primary"):
        active_provider, active_api_key, active_model = _active_text_credentials()
        _warn_missing_provider_key(active_provider, active_api_key)
        mv = _safe("Generate MV", analyze_song_with_gemini, active_api_key, active_model, title, artist, lyrics, style, "balanced", scene_count=scene_count, provider=active_provider)
        if mv.get("storyboard") is not None:
            project["title"] = title
            project["artist"] = artist
            project["mv"] = mv
            st.session_state.storyboard = mv.get("storyboard", [])
            _save_project()
            _log_beta_event("generate", workflow="music_mv", metadata={"page": "MV Director"})
            st.success("MV plan generated")
    if c2.button("Generate MV Storyboard", use_container_width=True):
        active_provider, active_api_key, active_model = _active_text_credentials()
        _warn_missing_provider_key(active_provider, active_api_key)
        song_context = dict(project.get("song", {}) or {})
        song_context.setdefault("title", title)
        song_context.setdefault("normalized_song_output", lyrics)
        song_context.setdefault("genre", style)
        storyboard_result = generate_mv_storyboard(song_context, project, scene_count=min(10, max(5, int(scene_count or 8))), visual_settings=mv_visual_settings)
        if storyboard_result.get("ok"):
            metadata = storyboard_result["data"].get("metadata", {})
            metadata["active_ai_provider"] = active_provider
            metadata["active_ai_model"] = active_model
            storyboard = storyboard_result["data"].get("storyboard", [])
            project["title"] = title
            project["artist"] = artist
            project.setdefault("mv", {})["storyboard"] = storyboard
            project["mv"]["visual_settings"] = mv_visual_settings
            project["mv"]["render_settings"] = mv_render_settings
            project["mv"]["mv_storyboard_metadata"] = metadata
            export_result = export_mv_storyboard(title, storyboard, metadata)
            project["mv"]["mv_storyboard_export"] = export_result.get("data", {})
            render_export = _attach_render_connector(title, "mv", "music_mv", storyboard, mv_render_settings, mv_visual_settings)
            st.session_state.storyboard = storyboard
            _save_project()
            _log_beta_event("mv_storyboard_generated", workflow="music_mv", preset_bundle=str(mv_render_settings.get("bundle_name") or ""), metadata={"page": "MV Director"})
            if export_result.get("ok"):
                _log_beta_event("export", workflow="music_mv", metadata={"format": "mv_storyboard"})
            st.success("MV storyboard generated")
            if export_result.get("ok"):
                st.caption(f"Export: {export_result['data'].get('txt_path')}")
            if render_export.get("ok"):
                st.caption(f"Render package: {render_export['data'].get('txt_path')}")
            else:
                st.warning(export_result.get("message", "Storyboard export failed"))
        else:
            st.error(storyboard_result.get("error") or storyboard_result.get("message", "Storyboard generation failed"))
    _render_package_preview(((project.get("mv", {}) or {}).get("render_connector") or {}))
    mv_storyboard = ((project.get("mv", {}) or {}).get("storyboard", []) or [])
    if mv_storyboard:
        st.divider()
        mv_hook_package = _mv_storyboard_to_hook_package(title or project.get("title") or "mv_project", mv_storyboard, mv_render_settings, mv_visual_settings)
        if mv_hook_package:
            project.setdefault("mv", {})["mv_render_clip_package"] = mv_hook_package
            _render_real_clip_controls(project, "mv", mv_hook_package, "music_mv", default_voice_style="calm narrator")
    else:
        st.info("Generate an MV storyboard first, then Start Render will appear here.")
    with st.expander("Render Queue", expanded=False):
        _render_queue_ui(title or project.get("title") or "mv_project")
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
    with st.expander("Render Queue", expanded=True):
        _render_queue_ui(project.get("title") or "project")
    with st.expander("Render Jobs", expanded=True):
        _render_jobs_ui(project.get("title") or "project")
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
    settings.default_ai_provider = _active_ai_provider()
    st.json(run_healthcheck(settings), expanded=False)
    active_provider, active_api_key, _ = _active_text_credentials()
    runtime = _provider_runtime_status(active_provider, active_api_key)
    st.info(f"Provider Runtime: {runtime['status']} · {runtime['message']}", icon="ℹ️")
    resolved = _active_credential_status()
    st.json(
        {
            "Active Provider": provider_display_name(active_provider),
            "API Mode": resolved.get("api_mode"),
            "User Key": "Provided" if resolved.get("user_key_present") else "Missing",
            "VelaFlow Key": "Configured" if resolved.get("velaflow_key_present") else "Not configured",
        },
        expanded=False,
    )
    with st.expander("Beta Analytics Snapshot", expanded=False):
        analytics = load_beta_analytics()
        st.caption("Local aggregate counters only. No personal tracking, prompts, lyrics, products, or user IDs are stored.")
        c1, c2, c3 = st.columns(3)
        c1.metric("Generate", analytics.get("generate_count", 0))
        c2.metric("Export", analytics.get("export_count", 0))
        c3.metric("Render Jobs", analytics.get("render_job_count", 0))
        st.json(
            {
                "workflow_usage": analytics.get("workflow_usage", {}),
                "active_provider_usage": analytics.get("active_provider_usage", {}),
                "preset_bundle_usage": analytics.get("preset_bundle_usage", {}),
                "quality_tracking": analytics.get("quality_tracking", {}),
            },
            expanded=False,
        )
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
    provider_options = {"Gemini": "gemini", "OpenAI GPT": "openai", "xAI Grok": "xai"}
    current_provider = _active_ai_provider()
    current_api_mode = api_mode_label(st.session_state.get("api_mode", API_MODE_OWN_KEY))
    api_mode = st.radio(
        "API Mode",
        API_MODES,
        index=API_MODES.index(current_api_mode),
        horizontal=True,
        help="Use My Own API Key = tester pays provider usage. Use VelaFlow Beta Key = use environment key if configured.",
    )
    if api_mode != st.session_state.get("api_mode"):
        st.session_state.api_mode = api_mode
        _save_api_state_to_local_storage(st.session_state.get("default_ai_provider", "gemini"), api_mode)
        st.success(f"API Mode set to {api_mode}")
    provider_label = st.selectbox(
        "AI Provider",
        list(provider_options),
        index=list(provider_options.values()).index(current_provider) if current_provider in provider_options.values() else 0,
        help="เลือกผู้ให้บริการ AI หลักตั้งแต่ต้นงาน ถ้าไม่มี API key ระบบจะใช้ offline fallback",
    )
    selected_provider = provider_options[provider_label]
    if selected_provider != st.session_state.get("default_ai_provider"):
        st.session_state.default_ai_provider = selected_provider
        _save_api_state_to_local_storage(selected_provider, st.session_state.get("api_mode", API_MODE_OWN_KEY))
        st.success(f"Active AI provider set to {provider_label}")
    st.warning("Your API key is used only to call the selected AI provider. Do not share it with others.")
    st.caption("Your API key is stored only in this browser/device. Do not use shared devices.")
    if st.session_state.get("local_api_state_source") == "session_state_only":
        st.caption("localStorage helper is unavailable in this environment, so keys persist only for this Streamlit session.")
    user_keys = st.session_state.setdefault("user_api_keys", {})
    existing_user_key = str(user_keys.get(selected_provider, "") or "")
    input_nonce_key = f"user_api_key_nonce_{selected_provider}"
    st.session_state.setdefault(input_nonce_key, 0)
    entered_key = st.text_input(
        f"{provider_label} API Key",
        value=existing_user_key,
        type="password",
        help="ใส่ API key ของคุณเอง ระบบจะเก็บไว้ใน session ของเบราว์เซอร์นี้เท่านั้น และจะไม่บันทึกลงไฟล์โปรเจกต์หรือ export",
        key=f"user_api_key_input_{selected_provider}_{st.session_state[input_nonce_key]}",
    )
    k1, k2 = st.columns(2)
    if k1.button("Save on this device", use_container_width=True):
        if entered_key.strip():
            st.session_state.user_api_keys[selected_provider] = entered_key.strip()
            st.session_state.api_mode = API_MODE_OWN_KEY
            st.session_state.default_ai_provider = selected_provider
            st.session_state.api_storage_nonce += 1
            _save_api_state_to_local_storage(selected_provider, API_MODE_OWN_KEY, entered_key.strip())
            st.success("API key saved on this device")
        else:
            st.warning("Paste an API key before saving.")
    if k2.button("Forget API Key", use_container_width=True):
        st.session_state.user_api_keys.pop(selected_provider, None)
        st.session_state[input_nonce_key] += 1
        st.session_state.api_mode = API_MODE_OWN_KEY
        st.session_state.api_storage_nonce += 1
        _forget_api_key_from_local_storage(selected_provider)
        st.success("API key forgotten from this browser/device")
    resolved = resolve_provider_credentials(
        settings=settings,
        provider=selected_provider,
        api_mode=st.session_state.get("api_mode", API_MODE_OWN_KEY),
        user_api_keys=st.session_state.get("user_api_keys", {}),
    )
    runtime = _provider_runtime_status(selected_provider, resolved.get("api_key", ""))
    st.write(f"Active provider: {provider_label}")
    st.write(f"API Mode: {resolved.get('api_mode')}")
    st.info(f"Runtime status: {runtime['status']} · {runtime['message']}", icon="ℹ️")
    st.write("User Key:", mask_api_key(user_keys.get(selected_provider, "")))
    st.write("VelaFlow Key:", "Configured" if resolved.get("velaflow_key_present") else "Not configured")
    st.write(f"Gemini model: {settings.gemini_model}")
    st.write("Gemini configured:", bool(settings.gemini_api_key))
    st.write(f"OpenAI GPT model: {settings.openai_text_model}")
    st.write("OpenAI configured:", bool(settings.openai_api_key))
    st.write(f"xAI Grok model: {settings.xai_text_model}")
    st.write("xAI Grok configured:", bool(settings.xai_api_key))
    st.caption("Environment variables: GEMINI_API_KEY, OPENAI_API_KEY, XAI_API_KEY, DEFAULT_AI_PROVIDER")
    st.caption("No payment, cloud sync, online license, full video AI, packaging, or watermark enforcement was added.")

elif page == "Artist Preset Manager":
    _render_artist_preset_manager()

