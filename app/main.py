from __future__ import annotations

import io
import json
import hashlib
import shutil
import sys
import time
import zipfile
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
from core.agent_memory import load_agent_memory, save_agent_memory
from core.agent_executor import run_agent_workflow
from core.agent_brain import AGENT_AI_PROVIDERS
from core.agent_studio import AGENT_LANGUAGES, AGENT_PROJECT_TYPES, AGENT_TONES, AGENT_WORKFLOW_MODES, agent_package_to_text, generate_agent_package
from core.asset_manager import list_assets as list_workspace_assets, register_asset
from core.media_pipeline import load_pipeline as load_media_pipeline, save_pipeline as save_media_pipeline, transition_stage
from core.project_assets import cover_prompt_history, project_asset_summary as workspace_asset_summary
from core.storyboard_manager import add_scene as add_storyboard_scene, create_storyboard, export_storyboard_json, export_storyboard_txt
from core.workspace_manager import archive_project as archive_workspace_project, create_project as create_workspace_project, export_project_zip as export_workspace_zip, list_projects as list_workspace_projects, load_project as load_workspace_project, workspace_summary
from core.analytics import beta_analytics_summary, cleanup_old_temp_exports, ensure_beta_runtime_dirs, load_beta_analytics, log_beta_event
from core.affiliate_engine import (
    AFFILIATE_MODES,
    TRENDING_AFFILIATE_IDEAS,
    analyze_affiliate_product,
    build_affiliate_clip_brief,
    build_affiliate_scripts,
    build_affiliate_shot_list,
    export_affiliate_package,
    generate_affiliate_hooks,
    normalize_affiliate_product,
)
from core.automatic_hook_clip import export_tiktok_package, quick_generate_hook_clip
from core.character_engine import CHARACTER_TYPES, PERSONALITY_PROMPTS, STYLE_PROMPTS, random_viral_character_idea
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
from core.beta_access import load_beta_access, register_beta_activity, save_beta_access
from core.character_consistency import apply_character_to_storyboard, build_character_prompt, normalize_character
from core.character_studio import (
    CHARACTER_STYLES,
    DEFAULT_CHARACTER_INPUTS,
    PLATFORMS,
    REQUIRED_CHARACTER_SECTIONS,
    SCENE_BACKGROUNDS,
    USE_CASES,
    character_prompt_pack_to_text,
    generate_character_prompt_pack,
)
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
from core.creative_pack_generator import CREATIVE_PACK_PRESETS, creative_release_pack_to_text, export_creative_release_pack, generate_creative_release_pack
from core.emotional_arc import analyze_emotional_arc
from core.exporter import export_package
from core.final_package import build_final_release_package, inspect_final_package_inputs
from core.ffmpeg_utils import configure_moviepy_ffmpeg, ffmpeg_version
from core.healthcheck import run_healthcheck, run_pre_render_healthcheck
from core.hook_intelligence import analyze_hooks
from core.hook_clip_engine import build_hook_render_package, export_hook_clip_package, hook_clip_package_to_text
from core.hook_detector import detect_hook_section
from core.hook_package_generator import build_final_creator_zip, extract_full_hook_section, generate_full_hook_creator_package
from core.instrument_tag_normalizer import normalize_lyrics_tags, validate_english_only_tags
from core.job_queue import cancel_job, clear_finished_jobs, list_jobs, submit_job
from core.prompt_director import CREATOR_EXPORT_MODES, PROMPT_STYLES
from core.licensing import get_license_service
from core.lyrics_expander import analyze_song_completeness, apply_music_direction_tags, ensure_full_song_structure
from core.music_direction_engine import build_music_direction
from core.marketing_package import build_marketing_package, export_marketing_package
from core.clip_studio_v2 import generate_clip_studio_v2
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
from core.preset_engine import apply_preset_to_project, get_preset, list_presets
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
from core.video_prompt_studio import (
    CLIP_LENGTHS as VIDEO_PROMPT_CLIP_LENGTHS,
    PRESETS as VIDEO_PROMPT_PRESETS,
    PROJECT_TYPES as VIDEO_PROMPT_PROJECT_TYPES,
    TARGET_PLATFORMS as VIDEO_PROMPT_TARGET_PLATFORMS,
    build_video_prompt_package,
    video_prompt_package_to_text,
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
    autosave_project_state,
    archive_project,
    create_project as create_managed_project,
    delete_project,
    ensure_creator_project_folders,
    filter_visible_projects,
    get_project_summary,
    is_test_project_name,
    project_health_summary,
    list_archived_projects,
    list_projects as list_managed_projects,
    load_autosave_project_state,
    load_user_preferences,
    rename_project,
    save_user_preferences,
    session_label_for_mode,
    workflow_type_for_mode,
)
from core.error_recovery import build_recovery_plan, friendly_error_message
from core.provider_runtime import build_provider_runtime_diagnostics
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
from core.render_queue import (
    complete_render_job as complete_creator_render_job,
    load_creator_render_queue,
    release_stale_render_jobs,
    start_render_job as start_creator_render_job,
)
from core.storage_cleanup import cleanup_project_storage
from core.real_clip_pipeline import ensure_parent_dir, probe_media, render_image_motion_scene, render_real_hook_clip, trim_audio_clip, validate_mp4
from core.render_engine import run_render
from core.rendering_presets import ASPECT_RATIOS, MOTION_INTENSITIES, RENDER_DURATIONS, RENDER_QUALITIES, get_render_preset_bundle, list_render_preset_bundles, list_rendering_providers
from core.remaster_engine import REMASTER_STYLES, remaster_song_audio
from core.render_profiles import RENDER_PROFILES
from core.render_recovery import export_diagnostic_bundle, latest_failed_render, recover_render_temp
from core.safe_mode import open_project_safe_mode
from core.scene_scoring import score_project_scenes, smart_tiktok_recommendations
from core.scene_story_engine import build_subtitle_timing
from core.subtitle_engine import list_viral_subtitle_presets
from core.thumbnail_selector import score_affiliate_thumbnail_candidates
from core.trend_finder import (
    TREND_AUDIENCES,
    TREND_CATEGORIES,
    TREND_CONTENT_STYLES,
    TREND_PLATFORMS,
    TREND_PRICE_RANGES,
    export_trend_package,
    find_affiliate_trends,
)
from core.seller_content import HOOK_STYLES, TONE_GUIDES, build_seller_dashboard_status, export_seller_content, generate_seller_content, seller_content_to_text
from core.shorts_factory import generate_shorts_factory, list_shorts_variations
from core.voiceover_engine import VOICEOVER_STYLES, build_voiceover_plan, export_voiceover_plan, generate_voiceover_audio
from core.settings import get_settings
from core.stable_build import STABLE_FREEZE_NAME, create_stable_candidate_snapshot
from core.song_workflow import (
    compare_song_to_draft,
    detect_best_song_hook,
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
from core.song_title_engine import generate_song_title_candidates, generate_song_title_from_idea, is_placeholder_song_title
from core.suno_export import export_creator_final_assets, export_suno_files, resolve_export_txt_filename
from core.theme import active_theme_name
from core.ui_styles import apply_global_styles
from core.veo_scene_renderer import download_veo_scene_result, load_scene_jobs, poll_veo_scene_job, save_scene_job, scene_output_path, submit_veo_scene_job
from core.version import APP_VERSION, BUILD_VERSION, RELEASE_CHANNEL, build_label
from core.versioning import list_clip_versions
from providers.image_ai import generate_image
from providers.ai_provider import normalize_provider, provider_display_name
from providers.text_ai import analyze_song_with_gemini, generate_song_with_gemini
from providers.veo_video_provider import run_live_veo_provider_test
from providers.veo_provider import build_veo_payload, list_available_veo_models, submit_render_job as submit_veo_render_job, test_veo_connection
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


def _sync_provider_runtime_state() -> dict[str, Any]:
    resolved = _active_credential_status()
    diagnostics = build_provider_runtime_diagnostics(
        resolved.get("provider", _active_ai_provider()),
        resolved.get("api_key", ""),
        api_mode=str(resolved.get("api_mode") or ""),
        source=str(resolved.get("source") or ""),
    )
    st.session_state.provider_runtime = {
        **diagnostics,
        "user_key_present": bool(resolved.get("user_key_present")),
        "velaflow_key_present": bool(resolved.get("velaflow_key_present")),
        "missing_key": resolved.get("missing_key", ""),
        "warning": resolved.get("warning", ""),
    }
    return st.session_state.provider_runtime


def _runtime_api_keys_for_health() -> dict[str, str]:
    if st.session_state.get("api_mode", API_MODE_OWN_KEY) != API_MODE_OWN_KEY:
        return {}
    return {
        provider: str(key or "")
        for provider, key in (st.session_state.get("user_api_keys", {}) or {}).items()
        if str(key or "").strip()
    }


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
        diagnostics = build_provider_runtime_diagnostics(provider, api_key, api_mode=str((resolved or {}).get("api_mode") or ""), source=str((resolved or {}).get("source") or ""))
        source = (resolved or {}).get("source", "")
        source_label = "user key" if source == "user" else "VelaFlow beta key" if source == "velaflow_beta" else "configured key"
        return {"status": str(diagnostics.get("status") or "Ready"), "message": f"{diagnostics.get('message')} · configured via {source_label}"}
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
    _sync_provider_runtime_state()


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
        st.caption("Default is vertical 9:16. Creator render uses local MP4 export or real BYO provider rendering when available.")
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
        developer_mode = st.toggle(
            "Advanced / Developer: show mock render sandbox",
            value=False,
            key=f"developer_mock_render_toggle_{safe_project}_{payload.get('provider','')}_{payload.get('duration','')}",
            help="Shows mock job IDs for testing only. Real creator rendering is handled in the Creator Render / REAL PROVIDER MODE panel.",
        )
        if not developer_mode:
            st.caption("REAL PROVIDER MODE: use Creator Render, Veo provider render, image-to-video render, and Final MP4 export outside this preview.")
            return
        st.divider()
        st.warning("MOCK MODE - Developer Only. These mock job IDs are not real provider render jobs.")
        st.write("Mock Render Sandbox (Developer Only)")
        provider_mode = st.selectbox(
            "Mock Provider Mode",
            RENDER_JOB_PROVIDER_MODES,
            index=0,
            key=f"render_job_provider_mode_{safe_project}_{payload.get('provider','')}_{payload.get('duration','')}",
            help="Developer-only sandbox. Manual / Mock creates a fake job id.",
        )
        if st.button("Send Mock Render Job", key=f"send_render_job_{safe_project}_{payload.get('provider','')}_{payload.get('duration','')}"):
            result = send_render_job(project_name, package, provider_mode)
            if result.get("ok"):
                _log_beta_event("render_job", workflow=str(payload.get("workflow_type") or ""), preset_bundle=str(payload.get("bundle_name") or ""), metadata={"provider_mode": provider_mode, "mock": True})
                st.success(f"Mock Render Job ID: {result['data']['job'].get('job_id')}")
            else:
                st.error(result.get("error") or result.get("message"))
            st.rerun()
        jobs_result = load_render_jobs(project_name)
        jobs = [job for job in jobs_result.get("data", {}).get("items", []) if str(job.get("job_id", "")).startswith("mock_")]
        if jobs:
            job_rows = [
                {
                    "Mock Job ID": job.get("job_id", ""),
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
            selected_job = st.selectbox("Mock Render Job ID", [job.get("job_id", "") for job in jobs], key=f"render_job_select_{safe_project}")
            selected_data = next((job for job in jobs if job.get("job_id") == selected_job), {})
            jc1, jc2 = st.columns(2)
            if jc1.button("Check Mock Status", key=f"check_render_job_{safe_project}"):
                status_result = check_render_job_status(project_name, selected_job)
                if status_result.get("ok"):
                    st.success(f"Mock status: {status_result['data']['job'].get('status')}")
                else:
                    st.error(status_result.get("error") or status_result.get("message"))
                st.rerun()
            result_path = Path(str(selected_data.get("result_path") or ""))
            if selected_data.get("status") == "Completed" and result_path.is_file():
                jc2.download_button(
                    "Download Mock Result",
                    data=result_path.read_bytes(),
                    file_name=result_path.name,
                    mime="text/plain",
                    key=f"download_render_job_result_{safe_project}_{selected_job}",
                )
                st.caption(f"Mock result path: {result_path}")
            else:
                jc2.button("Download Mock Result", disabled=True, key=f"download_render_job_disabled_{safe_project}_{selected_job}")
        else:
            st.info("No mock render jobs yet.")


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
    st.write("Mock Render Sandbox (Developer Only)")
    st.warning("MOCK MODE - this view is for testing metadata only. Real provider render jobs do not use mock_xxx IDs.")
    loaded = load_render_jobs(project_name, base_dir)
    items = [item for item in loaded.get("data", {}).get("items", []) if str(item.get("job_id", "")).startswith("mock_")]
    st.caption(f"render_jobs.json: {loaded.get('data', {}).get('path', '')}")
    if not items:
        st.info("No mock render jobs yet.")
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
            "Mock Render Job ID": item.get("job_id", ""),
        }
        for item in items
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, height=220)
    selected = st.selectbox("Mock Render Job ID", [item.get("job_id", "") for item in items], key=f"monitor_render_job_select_{safe_name(project_name)}")
    if st.button("Check Mock Status", key=f"monitor_check_render_job_{safe_name(project_name)}"):
        result = check_render_job_status(project_name, selected, base_dir)
        st.success(f"Mock status: {result.get('data', {}).get('job', {}).get('status')}") if result.get("ok") else st.error(result.get("error") or result.get("message"))
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
    result = render_image_motion_scene(scene, scene_path, aspect_ratio=aspect_ratio, log_path=log_path)
    job["status"] = "completed" if result.get("ok") else "failed"
    job["error"] = result.get("error", "")
    job["updated_at"] = datetime.now().isoformat(timespec="seconds")
    save_scene_job(project_name, scene_id, job)
    return result


def _render_final_downloads(section_key: str, real_output: dict[str, Any]) -> None:
    if not real_output:
        return
    status = real_output.get("manifest", {}).get("status") or real_output.get("status") or "-"
    duration = real_output.get("duration") or (real_output.get("manifest", {}) or {}).get("duration") or (real_output.get("validation", {}) or {}).get("duration", 0)
    if status == "completed":
        st.success(f"Render completed · {float(duration or 0):.1f}s")
    elif status == "failed":
        stage = real_output.get("render_stage") or (real_output.get("manifest", {}) or {}).get("render_stage", {})
        clean_error = stage.get("safe_error_message") or "Render failed: scene video could not be created"
        st.warning(clean_error)
    else:
        st.caption(f"Render Status: {status}")
    if real_output.get("final_mp4") and Path(real_output["final_mp4"]).is_file():
        final_path = Path(real_output["final_mp4"])
        st.markdown("**Final Video Preview**")
        subtitle_status = real_output.get("subtitle_status") or (real_output.get("render_stage") or {}).get("subtitle_status", "")
        audio_sync_status = real_output.get("audio_sync_status") or (real_output.get("render_stage") or {}).get("audio_sync_status", "")
        if subtitle_status:
            st.caption(f"Subtitle status: {subtitle_status}")
        if audio_sync_status:
            st.caption(f"Audio sync: {audio_sync_status}")
        st.video(str(final_path))
        st.download_button("Download Final Clip MP4", data=final_path.read_bytes(), file_name=final_path.name, mime="video/mp4", use_container_width=True, key=f"{section_key}_download_final_mp4")
    if real_output.get("subtitles") and Path(real_output["subtitles"]).is_file():
        subtitle_path = Path(real_output["subtitles"])
        st.download_button("Download subtitles.srt", data=subtitle_path.read_bytes(), file_name="subtitles.srt", mime="text/plain", use_container_width=True, key=f"{section_key}_download_srt")


def _render_tiktok_package_downloads(section_key: str, package_data: dict[str, Any]) -> None:
    if not package_data:
        return
    final_dir = Path(str(package_data.get("final_dir") or ""))
    if not final_dir.exists():
        return
    key_scope = hashlib.sha1(str(final_dir.resolve()).encode("utf-8", errors="ignore")).hexdigest()[:10]
    st.caption(f"Final export package: {final_dir}")
    thumbnail_path = final_dir / "thumbnail.jpg"
    if thumbnail_path.is_file():
        st.image(str(thumbnail_path), caption="Thumbnail preview", use_container_width=True)
    suno_path = final_dir / "suno_export.txt"
    if suno_path.is_file():
        st.download_button(
            "🎵 Download Suno TXT",
            data=suno_path.read_bytes(),
            file_name="suno_export.txt",
            mime="text/plain",
            use_container_width=True,
            key=f"{section_key}_download_suno_export_txt",
        )
    cover_files = [
        ("1:1", final_dir / "cover_prompt_1x1.txt"),
        ("9:16", final_dir / "cover_prompt_9x16.txt"),
        ("16:9", final_dir / "cover_prompt_16x9.txt"),
    ]
    if any(path.is_file() for _, path in cover_files):
        with st.expander("🖼 Generate Cover Prompts", expanded=False):
            for idx, (label, path) in enumerate(cover_files):
                if path.is_file():
                    prompt_key = f"{section_key}_{key_scope}_cover_prompt_{idx}"
                    st.text_area(f"{label} cover prompt", value=path.read_text(encoding="utf-8-sig"), height=120, key=prompt_key)
                    st.download_button(
                        f"Download {path.name}",
                        data=path.read_bytes(),
                        file_name=path.name,
                        mime="text/plain",
                        use_container_width=True,
                        key=f"{section_key}_{key_scope}_download_cover_inline_{idx}_{path.stem}",
                    )
    caption_path = final_dir / "tiktok_caption.txt"
    youtube_path = final_dir / "youtube_caption.txt"
    hashtags_path = final_dir / "hashtags.txt"
    if caption_path.is_file():
        st.text_area("📱 TikTok Caption", value=caption_path.read_text(encoding="utf-8-sig"), height=110, key=f"{section_key}_tiktok_caption_preview")
    if youtube_path.is_file():
        with st.expander("📺 YouTube Caption", expanded=False):
            st.text_area("YouTube caption", value=youtube_path.read_text(encoding="utf-8-sig"), height=180, key=f"{section_key}_youtube_caption_preview")
    if hashtags_path.is_file():
        st.text_area("#️⃣ Hashtags", value=hashtags_path.read_text(encoding="utf-8-sig"), height=90, key=f"{section_key}_hashtags_preview")
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in final_dir.iterdir():
            if path.is_file():
                archive.write(path, path.name)
    st.download_button(
        "🎬 Download Final TikTok Package",
        data=zip_buffer.getvalue(),
        file_name="velaflow_tiktok_package.zip",
        mime="application/zip",
        use_container_width=True,
        key=f"{section_key}_download_tiktok_package_zip",
    )
    creator_downloads = [
        ("tiktok_caption.txt", "text/plain"),
        ("youtube_caption.txt", "text/plain"),
        ("hashtags.txt", "text/plain"),
        ("cover_prompt_1x1.txt", "text/plain"),
        ("cover_prompt_9x16.txt", "text/plain"),
        ("cover_prompt_16x9.txt", "text/plain"),
        ("upload_checklist.txt", "text/plain"),
    ]
    developer_downloads = [
        ("captions.txt", "text/plain"),
        ("title.txt", "text/plain"),
        ("title_ideas.txt", "text/plain"),
        ("thumbnail.jpg", "image/jpeg"),
        ("thumbnail_score.json", "application/json"),
        ("thumbnail_prompt.txt", "text/plain"),
        ("hook_analysis.json", "application/json"),
        ("styled_subtitles.ass", "text/plain"),
        ("scene_prompts.json", "application/json"),
        ("beat_timing.json", "application/json"),
        ("render_manifest.json", "application/json"),
        ("render_stage.json", "application/json"),
        ("upload_checklist.txt", "text/plain"),
        ("viral_timing_plan.json", "application/json"),
        ("hook_audio.mp3", "audio/mpeg"),
    ]
    download_list = creator_downloads + (developer_downloads if st.session_state.get("developer_mode") else [])
    seen_downloads: set[str] = set()
    for filename, mime in download_list:
        if filename in seen_downloads:
            continue
        seen_downloads.add(filename)
        path = final_dir / filename
        if path.is_file():
            st.download_button(
                f"Download {filename}",
                data=path.read_bytes(),
                file_name=filename,
                mime=mime,
                use_container_width=True,
                key=f"{section_key}_{key_scope}_download_file_{len(seen_downloads)}_{Path(filename).stem}",
            )


def _render_creator_package_downloads(section_key: str, package_data: dict[str, Any]) -> None:
    final_dir = Path(str((package_data or {}).get("final_dir") or ""))
    if not final_dir.exists():
        return
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for filename in [
            "final_hook_clip.mp4",
            "thumbnail.jpg",
            "captions.txt",
            "hashtags.txt",
            "title.txt",
            "title_ideas.txt",
            "upload_checklist.txt",
            "subtitles.srt",
        ]:
            path = final_dir / filename
            if path.is_file():
                archive.write(path, path.name)
    st.download_button(
        "Download TikTok Package ZIP",
        data=zip_buffer.getvalue(),
        file_name="velaflow_tiktok_package.zip",
        mime="application/zip",
        use_container_width=True,
        key=f"{section_key}_download_creator_package_zip",
    )


def _render_creator_metrics(quick_data: dict[str, Any]) -> None:
    viral_metrics = quick_data.get("viral_metrics") or ((quick_data.get("package") or {}).get("viral_metrics") or {})
    if not viral_metrics:
        return
    thumbnail_quality = ((quick_data.get("thumbnail") or {}).get("score") or ((quick_data.get("tiktok_package") or {}).get("thumbnail_quality") or 0))
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Hook", viral_metrics.get("hook_score", 0))
    m2.metric("Emotion", viral_metrics.get("emotional_impact", viral_metrics.get("emotional_score", 0)))
    m3.metric("Pacing", viral_metrics.get("viral_pacing", 0))
    m4.metric("Thumbnail", thumbnail_quality or "-")
    m5.metric("Retention", viral_metrics.get("tiktok_retention_potential", viral_metrics.get("replay_potential", 0)))


def _creator_image_settings() -> tuple[str, dict[str, Any]]:
    image_settings = {
        "size": "1024x1536",
        "quality": "medium",
        "cache_enabled": False,
        "openai_api_key": _user_api_key("openai"),
        "gemini_api_key": _user_api_key("gemini"),
        "openai_image_model": getattr(settings, "openai_image_model", "gpt-image-1.5"),
    }
    if image_settings["gemini_api_key"]:
        return "gemini_image", image_settings
    if image_settings["openai_api_key"]:
        return "openai_images", image_settings
    return "offline", image_settings


def _run_creator_one_click_clip(project: dict[str, Any], idea: str, selected_preset: dict[str, Any], variation: str, *, force_cache_refresh: bool, force_final_render: bool, hook_audio_path: str = "") -> dict[str, Any]:
    project_name = project.get("title") or "My Viral Clip"
    image_provider, image_settings = _creator_image_settings()
    cleanup_project_storage(project_name, "song", keep_versions=3, dry_run=False)
    release_stale_render_jobs(project_name, "song")
    queue_result = start_creator_render_job(
        project_name,
        "song",
        stage="creator_one_click",
        metadata={"preset_id": selected_preset.get("preset_id"), "variation": variation},
    )
    if not queue_result.get("ok"):
        return {"ok": False, "message": queue_result.get("message", ""), "data": {}, "error": queue_result.get("error", "active_render_job")}
    job_id = ((queue_result.get("data") or {}).get("job") or {}).get("job_id", "")
    result: dict[str, Any] = {"ok": False, "message": "", "data": {}, "error": ""}
    started_at = time.time()
    try:
        result = quick_generate_hook_clip(
            project_name,
            idea,
            source_workflow="music",
            clip_mode="Fast Hook",
            duration_seconds=int(selected_preset.get("default_duration") or 15),
            image_provider=image_provider,
            image_settings=image_settings,
            preset_id=str(selected_preset.get("preset_id") or "emotional_story"),
            voiceover_style="emotional storyteller",
            voiceover_api_key=_user_api_key("openai"),
            subtitle_preset="Thai Emotional MV" if str(selected_preset.get("preset_id")) == "emotional_story" else "TikTok Meme",
            hook_audio_path=hook_audio_path,
            force_cache_refresh=force_cache_refresh,
            force_final_render=force_final_render,
            variation=variation,
        )
        if not result.get("ok"):
            result = quick_generate_hook_clip(
                project_name,
                idea,
                source_workflow="music",
                clip_mode="Fast Hook",
                duration_seconds=int(selected_preset.get("default_duration") or 15),
                image_provider=image_provider,
                image_settings=image_settings,
                preset_id=str(selected_preset.get("preset_id") or "emotional_story"),
                voiceover_style="emotional storyteller",
                voiceover_api_key=_user_api_key("openai"),
                subtitle_preset="Thai Emotional MV" if str(selected_preset.get("preset_id")) == "emotional_story" else "TikTok Meme",
                force_cache_refresh=False,
                force_final_render=True,
                variation=f"{variation}_auto_retry",
            )
    except Exception as exc:
        result = {"ok": False, "message": "Render failed", "data": {}, "error": str(exc)}
    finally:
        render_duration = round(time.time() - started_at, 2)
        (result.setdefault("data", {}) if isinstance(result.get("data"), dict) else {}).setdefault("render_duration", render_duration)
        complete_creator_render_job(
            project_name,
            "song",
            job_id,
            status="completed" if result.get("ok") else "failed",
            result={
                "final_mp4": (result.get("data") or {}).get("final_mp4", ""),
                "render_stage_path": (result.get("data") or {}).get("render_stage_path", ""),
            },
            error=str(result.get("error") or ""),
            safe_error_message="" if result.get("ok") else friendly_error_message(result.get("error") or result.get("message")),
        )
        register_beta_activity(1)
        log_beta_event(
            "creator_render",
            workflow="music",
            preset_bundle=str(selected_preset.get("label") or selected_preset.get("preset_id") or ""),
            metadata={
                "status": "completed" if result.get("ok") else "failed",
                "ok": bool(result.get("ok")),
                "mood_preset": str(selected_preset.get("label") or ""),
                "hook_style": str(selected_preset.get("hook_style") or ""),
                "render_duration": render_duration,
                "page": "Song Studio",
            },
        )
    return result


def _run_affiliate_one_click_clip(project_name: str, brief: dict[str, Any], preset_id: str = "affiliate_sell", variation: str = "default") -> dict[str, Any]:
    image_provider, image_settings = _creator_image_settings()
    release_stale_render_jobs(project_name, "clips")
    queue_result = start_creator_render_job(
        project_name,
        "clips",
        stage="affiliate_clip",
        metadata={"mode": brief.get("mode", ""), "preset_id": preset_id, "variation": variation},
    )
    if not queue_result.get("ok"):
        return {"ok": False, "message": queue_result.get("message", ""), "data": {}, "error": queue_result.get("error", "active_render_job")}
    job_id = ((queue_result.get("data") or {}).get("job") or {}).get("job_id", "")
    started_at = time.time()
    result: dict[str, Any] = {"ok": False, "message": "", "data": {}, "error": ""}
    try:
        result = quick_generate_hook_clip(
            project_name,
            str(brief.get("prompt") or ""),
            source_workflow="seller",
            clip_mode="Fast Hook",
            duration_seconds=20,
            image_provider=image_provider,
            image_settings=image_settings,
            preset_id=preset_id,
            voiceover_style="meme voice",
            voiceover_api_key=_user_api_key("openai"),
            subtitle_preset="Affiliate CTA",
            force_cache_refresh=False,
            force_final_render=True,
            variation=f"affiliate_{variation}",
        )
    except Exception as exc:
        result = {"ok": False, "message": "Affiliate render failed", "data": {}, "error": str(exc)}
    finally:
        render_duration = round(time.time() - started_at, 2)
        complete_creator_render_job(
            project_name,
            "clips",
            job_id,
            status="completed" if result.get("ok") else "failed",
            result={"final_mp4": (result.get("data") or {}).get("final_mp4", "")},
            error=str(result.get("error") or ""),
            safe_error_message="" if result.get("ok") else friendly_error_message(result.get("error") or result.get("message")),
        )
        log_beta_event(
            "creator_render",
            workflow="seller",
            preset_bundle="Affiliate Studio",
            metadata={
                "status": "completed" if result.get("ok") else "failed",
                "ok": bool(result.get("ok")),
                "mood_preset": str(brief.get("mode") or "Affiliate Studio"),
                "hook_style": str(((brief.get("viral_score") or {}).get("best_hook") or {}).get("hook_type") or "affiliate"),
                "render_duration": render_duration,
                "page": "Affiliate Studio",
            },
        )
    return result


def _render_affiliate_studio(project: dict[str, Any]) -> None:
    _page_header("Affiliate Studio", "Create TikTok affiliate hooks, scripts, shot lists, and export packages.", project)
    st.caption("Paste a product link or enter product details manually. No posting bots, no login automation, no heavy scraping.")
    state = project.setdefault("affiliate_studio", {})
    beta = state.setdefault("beta", {})
    beta.setdefault("export_count", 0)
    beta.setdefault("activity_count", 0)
    badge_cols = st.columns([1, 1, 1])
    badge_cols[0].caption("Founding Member build")
    badge_cols[1].caption(f"Exports: {beta.get('export_count', 0)}")
    badge_cols[2].caption(f"Creator actions: {beta.get('activity_count', 0)}")
    st.markdown("#### Simple flow")
    st.write("Paste Product URL -> Analyze Product -> Generate Hooks + Scripts -> Export Creator Package")
    tabs = st.tabs(["Product Analyzer", "🔥 Affiliate Trend Finder", "Viral Hook Generator", "TikTok Script Studio", "Creator Package Export", "Trending Ideas"])

    with tabs[0]:
        st.markdown("### Product Analyzer")
        product_source = st.radio("Product input", ["Product URL", "Manual Product Mode"], horizontal=True, key="affiliate_product_source", index=0 if state.get("product_source", "Product URL") == "Product URL" else 1)
        product_url = ""
        if product_source == "Product URL":
            product_url = st.text_input("Paste Product URL", value=state.get("product_url", ""), key="affiliate_product_url", placeholder="Shopee, TikTok Shop, Lazada, or Amazon link")
            analyze_url = st.button("Analyze Product", use_container_width=True, key="affiliate_analyze_product_url")
            if analyze_url:
                if not product_url.strip():
                    st.warning("Paste a product URL first, or switch to Manual Product Mode.")
                else:
                    with st.status("Checking product page...", expanded=False) as status:
                        link_result = analyze_product_link(product_url, state.get("manual_description", ""), retry_count=1)
                        status.update(label="Product check complete", state="complete", expanded=False)
                    link_data = link_result.get("data", {}) or {}
                    state["product_source"] = product_source
                    state["product_url"] = product_url
                    state["link_analysis"] = link_data
                    state["product_name"] = link_data.get("title") or state.get("product_name", "")
                    state["product_type"] = link_data.get("category") or state.get("product_type", "")
                    state["manual_description"] = link_data.get("description") or state.get("manual_description", "")
                    state["manual_attention"] = not bool(link_data.get("extracted_success"))
                    state["price"] = link_data.get("price") or link_data.get("pricing") or state.get("price", "")
                    state["rating"] = link_data.get("rating") or state.get("rating", "")
                    beta["activity_count"] = int(beta.get("activity_count", 0)) + 1
                    _save_project()
                    st.rerun()

        link_analysis = state.get("link_analysis") or {}
        if link_analysis:
            st.caption(f"Detected: {link_analysis.get('platform', 'unknown')} • {link_analysis.get('extraction_status', 'manual fallback')}")
            extracted = [label for label, key in [("Title", "title"), ("Description", "description"), ("Image", "image"), ("Price", "price"), ("Category", "category")] if link_analysis.get(key)]
            missing = [label for label, key in [("Title", "title"), ("Description", "description"), ("Image", "image"), ("Price", "price"), ("Category", "category")] if not link_analysis.get(key)]
            if link_analysis.get("extracted_success") and extracted:
                st.success("Extracted: " + ", ".join(extracted))
            if missing:
                st.caption("Missing: " + ", ".join(missing))
            if link_analysis.get("manual_fallback_message"):
                st.warning("ไม่สามารถดึงข้อมูลจากลิงก์นี้ได้ กรุณาวางชื่อสินค้า/รายละเอียดสินค้าเอง")
            original_url = str(link_analysis.get("original_url") or link_analysis.get("url") or "")
            if "s.shopee.co.th" in original_url:
                st.info("ลิงก์ Shopee แบบย่อบางรายการอาจไม่เปิดข้อมูลสินค้าโดยตรง ให้เปิดสินค้าในแอป Shopee แล้วคัดลอกชื่อสินค้า/รายละเอียดมาวางแทน")
            if st.session_state.get("developer_mode"):
                with st.expander("Developer extraction details", expanded=False):
                    st.write(f"original_url: {link_analysis.get('original_url', '')}")
                    st.write(f"resolved_url: {link_analysis.get('resolved_url', '')}")
                    st.write(f"platform: {link_analysis.get('platform', 'unknown')}")
                    st.write(f"extraction_source: {link_analysis.get('extraction_source', {})}")
                    st.write(f"extracted_title_exists: {link_analysis.get('extracted_title_exists', False)}")
                    st.write(f"extracted_description_exists: {link_analysis.get('extracted_description_exists', False)}")
                    st.write(f"extracted_image_exists: {link_analysis.get('extracted_image_exists', False)}")
                    st.write(f"failure_reason: {link_analysis.get('failure_reason', '')}")
                    st.write(f"Status: {link_analysis.get('extraction_status', '')}")
                    if link_analysis.get("fetch_error"):
                        st.write(f"Error: {link_analysis.get('fetch_error')}")

        with st.container(border=True):
            if state.get("manual_attention"):
                st.info("Manual Product Mode is ready. Fill these fields to continue.")
            mode = st.selectbox("Affiliate Mode", AFFILIATE_MODES, index=AFFILIATE_MODES.index(state.get("mode", AFFILIATE_MODES[0])) if state.get("mode") in AFFILIATE_MODES else 0, key="affiliate_mode")
            product_name = st.text_input("Product Title", value=state.get("product_name", ""), key="affiliate_product_name")
            product_type = st.text_input("Product Category", value=state.get("product_type", ""), key="affiliate_product_type")
            manual_description = st.text_area("Product Description", value=state.get("manual_description", ""), height=90, key="affiliate_product_description")
            target_audience = st.text_input("Target Audience", value=state.get("target_audience", "TikTok shoppers"), key="affiliate_target_audience")
            benefits = st.text_area("Product Benefits", value=state.get("benefits", ""), height=70, key="affiliate_product_benefits", placeholder="Example: saves time, looks premium, easier morning routine")
            emotional_angle = st.text_input("Emotional Angle", value=state.get("emotional_angle", "ชีวิตง่ายขึ้น"), key="affiliate_emotional_angle")
            pain_point = st.text_input("Pain Point", value=state.get("pain_point", ""), key="affiliate_pain_point")
            creator_notes = st.text_area("Creator Notes", value=state.get("creator_notes", ""), height=70, key="affiliate_creator_notes", placeholder="Any shooting angle, offer detail, or tone you want")
            cta_style = st.selectbox("CTA Style", ["soft sell", "urgent deal", "review first", "creator recommendation"], index=0, key="affiliate_cta_style")
            generate = st.button("Generate Affiliate Creator Package", type="primary", use_container_width=True, disabled=not bool(product_name.strip()), key="affiliate_generate_package")

        product = {
            "product_name": product_name,
            "product_type": product_type,
            "description": manual_description,
            "benefits": benefits,
            "target_audience": target_audience,
            "emotional_angle": emotional_angle,
            "pain_point": pain_point,
            "creator_notes": creator_notes,
            "cta_style": cta_style,
            "url": product_url,
            "platform": link_analysis.get("platform", "manual") if product_source == "Product URL" else "manual",
            "price": state.get("price", ""),
            "rating": state.get("rating", ""),
        }
        analysis = analyze_affiliate_product(product)
        score_cols = st.columns(3)
        score_cols[0].metric("Viral Potential", analysis["scores"]["viral_potential"])
        score_cols[1].metric("Hook Potential", analysis["scores"]["hook_potential"])
        score_cols[2].metric("TikTok Fit", analysis["scores"]["tiktok_compatibility"])
        st.caption(f"Recommended style: {analysis['recommended_content_style']}")
        st.write("Recommendations: " + " • ".join(analysis.get("recommendation_labels", [])))

        if generate:
            brief = build_affiliate_clip_brief(product, mode)
            package_result = export_affiliate_package(project.get("title") or product_name or "Affiliate Product", brief, {})
            state.update(normalize_affiliate_product(product))
            state["product_source"] = product_source
            state["product_url"] = product_url
            state["manual_description"] = manual_description
            state["benefits"] = benefits
            state["creator_notes"] = creator_notes
            state["mode"] = mode
            state["brief"] = brief
            state["affiliate_package"] = package_result.get("data", {})
            state["ok"] = bool(package_result.get("ok"))
            state["safe_error_message"] = "" if package_result.get("ok") else friendly_error_message(package_result.get("error") or package_result.get("message"))
            if package_result.get("ok"):
                beta["export_count"] = int(beta.get("export_count", 0)) + 1
                beta["activity_count"] = int(beta.get("activity_count", 0)) + 1
            project["affiliate_studio"] = state
            _save_project()
            st.rerun()

    brief = state.get("brief") or {}
    product_for_preview = normalize_affiliate_product(brief.get("product") or state)
    hooks = brief.get("hooks") or generate_affiliate_hooks(product_for_preview, state.get("mode", AFFILIATE_MODES[0]))
    scripts = brief.get("scripts") or build_affiliate_scripts(product_for_preview, hooks)
    shot_plan = {"shot_list": brief.get("shot_list") or [], "scene_breakdown": brief.get("scene_breakdown") or ""}
    if not shot_plan["shot_list"]:
        shot_plan = build_affiliate_shot_list(product_for_preview, hooks)

    with tabs[1]:
        st.markdown("### 🔥 Affiliate Trend Finder")
        st.write("Discover creator-friendly product ideas before you pick a product link.")
        tf1, tf2 = st.columns(2)
        trend_platform = tf1.selectbox("Platform", TREND_PLATFORMS, index=TREND_PLATFORMS.index(state.get("trend_platform", "TikTok Shop")) if state.get("trend_platform") in TREND_PLATFORMS else 0, key="affiliate_trend_platform")
        trend_category = tf2.selectbox("Category", TREND_CATEGORIES, index=TREND_CATEGORIES.index(state.get("trend_category", "Beauty")) if state.get("trend_category") in TREND_CATEGORIES else 0, key="affiliate_trend_category")
        tf3, tf4 = st.columns(2)
        trend_style = tf3.selectbox("Content Style", TREND_CONTENT_STYLES, index=TREND_CONTENT_STYLES.index(state.get("trend_style", "Problem/Solution")) if state.get("trend_style") in TREND_CONTENT_STYLES else 4, key="affiliate_trend_style")
        trend_audience = tf4.selectbox("Audience", TREND_AUDIENCES, index=TREND_AUDIENCES.index(state.get("trend_audience", "Office Workers")) if state.get("trend_audience") in TREND_AUDIENCES else 1, key="affiliate_trend_audience")
        trend_price = st.selectbox("Price Range", TREND_PRICE_RANGES, index=TREND_PRICE_RANGES.index(state.get("trend_price", "Budget")) if state.get("trend_price") in TREND_PRICE_RANGES else 0, key="affiliate_trend_price")
        b1, b2 = st.columns(2)
        generate_trends = b1.button("Generate Trend Ideas", type="primary", use_container_width=True, key="affiliate_generate_trends")
        regenerate_trends = b2.button("Regenerate", use_container_width=True, key="affiliate_regenerate_trends")
        if generate_trends or regenerate_trends:
            trend_result = find_affiliate_trends(trend_platform, trend_category, trend_style, trend_audience, trend_price, count=5)
            state["trend_platform"] = trend_platform
            state["trend_category"] = trend_category
            state["trend_style"] = trend_style
            state["trend_audience"] = trend_audience
            state["trend_price"] = trend_price
            state["trend_result"] = trend_result
            beta["activity_count"] = int(beta.get("activity_count", 0)) + 1
            project["affiliate_studio"] = state
            _save_project()
            st.rerun()

        trend_result = state.get("trend_result") or find_affiliate_trends(trend_platform, trend_category, trend_style, trend_audience, trend_price, count=3)
        for idea in (trend_result.get("ideas") or [])[:5]:
            with st.container(border=True):
                top_cols = st.columns([2.2, 1, 1])
                top_cols[0].markdown(f"**{idea['product_name']}**")
                top_cols[1].metric("Trend", idea["trend_score"])
                top_cols[2].caption(f"{idea['best_platform']} • {idea['competition_level']}")
                st.write("Why it may convert: " + " • ".join(idea["why_it_may_convert"][:2]))
                with st.expander("Hooks, shots, and thumbnail ideas", expanded=False):
                    st.write("Hooks")
                    st.write("\n".join(f"- {hook}" for hook in idea["viral_hooks"]))
                    st.write("Shot ideas")
                    st.write("\n".join(f"- {shot}" for shot in idea["shot_ideas"]))
                    st.write("Thumbnail")
                    st.write("\n".join(f"- {thumb}" for thumb in idea["thumbnail_ideas"]))
        if st.button("Export Trend Package ZIP", use_container_width=True, key="affiliate_export_trend_package"):
            trend_export = export_trend_package(project.get("title") or "Affiliate Trends", trend_result)
            state["trend_package"] = trend_export.get("data", {})
            if trend_export.get("ok"):
                beta["export_count"] = int(beta.get("export_count", 0)) + 1
                st.success("Trend package ready.")
            else:
                st.warning(friendly_error_message(trend_export.get("error", "Trend export failed")))
            project["affiliate_studio"] = state
            _save_project()
            st.rerun()
        trend_package = state.get("trend_package") or {}
        trend_zip = Path(str(trend_package.get("zip_path") or ""))
        if trend_zip.is_file():
            st.download_button("Download Trend Package ZIP", data=trend_zip.read_bytes(), file_name="affiliate_trend_package.zip", mime="application/zip", use_container_width=True, key="affiliate_trend_package_zip")

    with tabs[2]:
        st.markdown("### Viral Hook Generator")
        for item in hooks[:8]:
            with st.container(border=True):
                st.caption(item["hook_type"].replace("_", " ").title())
                st.write(item["hook_text"])
                m1, m2, m3 = st.columns(3)
                m1.metric("Hook", item["hook_strength"])
                m2.metric("CTA", item["cta_strength"])
                m3.metric("Scroll Stop", item["scroll_stop_score"])

    with tabs[3]:
        st.markdown("### TikTok Script Studio")
        for label, key in [("15s Script", "tiktok_script_15s"), ("30s Script", "tiktok_script_30s"), ("POV Version", "pov_script"), ("Review Version", "review_script"), ("Emotional Sell Version", "emotional_sell_script"), ("Aesthetic Version", "aesthetic_script")]:
            with st.expander(label, expanded=label == "15s Script"):
                st.text_area(label, value=scripts.get(key, ""), height=140, key=f"affiliate_script_preview_{key}")
        st.markdown("#### Shot List")
        st.text_area("Scene Breakdown", value=shot_plan["scene_breakdown"], height=220, key="affiliate_scene_breakdown_preview")

    with tabs[4]:
        st.markdown("### Creator Package Export")
        package = state.get("affiliate_package") or {}
        if package:
            st.success("Affiliate Creator Package Ready")
            ready_cols = st.columns(2)
            ready_cols[0].write("✅ Hooks Ready")
            ready_cols[0].write("✅ Scripts Ready")
            ready_cols[0].write("✅ Captions Ready")
            ready_cols[1].write("✅ Shot List Ready")
            ready_cols[1].write("✅ Thumbnail Prompt Ready")
            ready_cols[1].write("✅ Creator ZIP Ready")
            zip_path = Path(str(package.get("zip_path") or ""))
            if zip_path.is_file():
                st.download_button("Download Affiliate Creator Package ZIP", data=zip_path.read_bytes(), file_name="affiliate_creator_package.zip", mime="application/zip", use_container_width=True, key="affiliate_creator_package_zip")
            final_dir = Path(str(package.get("final_dir") or ""))
            if final_dir.exists():
                copy_cols = st.columns(2)
                hook_file = final_dir / "hooks" / "viral_hooks.txt"
                caption_file = final_dir / "captions" / "captions.txt"
                thumb_file = final_dir / "creator" / "thumbnail_prompt.txt"
                if hook_file.exists():
                    copy_cols[0].text_area("Copy Hooks", value=hook_file.read_text(encoding="utf-8-sig"), height=120, key="affiliate_copy_hooks")
                if caption_file.exists():
                    copy_cols[1].text_area("Copy Captions", value=caption_file.read_text(encoding="utf-8-sig"), height=120, key="affiliate_copy_captions")
                if thumb_file.exists():
                    st.text_area("Copy Thumbnail Prompt", value=thumb_file.read_text(encoding="utf-8-sig"), height=90, key="affiliate_copy_thumbnail_prompt")
                with st.expander("Included creator files", expanded=False):
                    st.write("\n".join(sorted(str(path.relative_to(final_dir)).replace("\\", "/") for path in final_dir.rglob("*") if path.is_file())))
                with st.expander("Send beta feedback", expanded=False):
                    feedback = st.text_area("What felt confusing or useful?", value="", height=90, key="affiliate_beta_feedback")
                    if st.button("Save Affiliate Feedback", use_container_width=True, key="affiliate_save_feedback") and feedback.strip():
                        feedback_dir = workflow_project_root("seller") / safe_name(project.get("title") or "affiliate") / "feedback"
                        feedback_dir.mkdir(parents=True, exist_ok=True)
                        (feedback_dir / f"affiliate_feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt").write_text(feedback.strip(), encoding="utf-8-sig")
                        st.success("Feedback saved locally.")
        elif state.get("safe_error_message"):
            st.warning(state.get("safe_error_message"))
        else:
            st.info("Analyze a product and generate the creator package first.")

    with tabs[5]:
        st.markdown("### Trending Affiliate Ideas")
        for idea in TRENDING_AFFILIATE_IDEAS:
            with st.container(border=True):
                cols = st.columns([1.4, 2.4, 1, 1.4])
                cols[0].markdown(f"**{idea['category']}**")
                cols[1].write(idea["idea"])
                cols[2].metric("Viral", idea["viral_potential"])
                cols[3].caption(f"{idea['content_difficulty']} • {idea['recommended_style']}")
                st.caption(f"Easy to shoot {idea['easy_to_shoot']}/100 • Emotional sell {idea['emotional_sell']}/100 • Before/After {idea['before_after_strength']}/100")


def _render_shorts_factory(project: dict[str, Any]) -> None:
    _page_header("Shorts Factory", "Generate 5 TikTok-ready variations for A/B testing.", project)
    st.caption("One button creates emotional, aggressive hook, fast pacing, stronger CTA, and alternate thumbnail versions.")
    state = project.setdefault("shorts_factory", {})
    affiliate_state = project.get("affiliate_studio", {}) or {}
    default_prompt = ((affiliate_state.get("brief") or {}).get("prompt") or state.get("base_prompt") or "")
    with st.container(border=True):
        source_type = st.selectbox("Source Type", ["Affiliate Product", "Music Hook", "General Idea"], index=0, key="shorts_factory_source_type")
        base_prompt = st.text_area(
            "Base Idea / Product Brief",
            value=default_prompt,
            height=160,
            key="shorts_factory_base_prompt",
            placeholder="วาง product brief, hook, หรือไอเดียหลักที่อยากทำหลายเวอร์ชัน",
        )
        st.caption("Variations: " + ", ".join(item["label"] for item in list_shorts_variations()))
        generate = st.button("Generate 5 Viral Variations", type="primary", use_container_width=True, disabled=not bool(base_prompt.strip()), key="shorts_factory_generate")
    if generate:
        project_name = project.get("title") or "Shorts Factory"
        image_provider, image_settings = _creator_image_settings()
        with st.status("Generating 5 variations sequentially...", expanded=True) as status:
            st.write("Queueing batch safely")
            st.write("Rendering variations one by one")
            st.write("Exporting comparison package")
            result = generate_shorts_factory(
                project_name,
                base_prompt,
                source_workflow="seller" if source_type == "Affiliate Product" else "music" if source_type == "Music Hook" else "hook_clip",
                workflow_type="clips",
                image_provider=image_provider,
                image_settings=image_settings,
                max_variations=5,
            )
            status.update(label="Shorts Factory ready" if result.get("ok") else friendly_error_message(result.get("error") or result.get("message")), state="complete" if result.get("ok") else "error", expanded=False)
        state["base_prompt"] = base_prompt
        state["source_type"] = source_type
        state["result"] = result.get("data", {})
        state["ok"] = bool(result.get("ok"))
        state["safe_error_message"] = "" if result.get("ok") else friendly_error_message(result.get("error") or result.get("message"))
        project["shorts_factory"] = state
        _save_project()
        _log_beta_event("creator_render", workflow="seller", preset_bundle="Shorts Factory", metadata={"status": "completed" if result.get("ok") else "failed", "ok": bool(result.get("ok")), "page": "Shorts Factory"})
        st.rerun()

    result_data = state.get("result") or {}
    comparison = result_data.get("comparison") or {}
    export = result_data.get("export") or {}
    if comparison:
        st.markdown("## Variation Comparison")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Best Retention", (comparison.get("best_retention_estimate") or {}).get("label", "-"))
        c2.metric("Strongest Hook", (comparison.get("strongest_hook") or {}).get("label", "-"))
        c3.metric("Best Thumbnail", (comparison.get("best_thumbnail") or {}).get("label", "-"))
        c4.metric("Best CTA", (comparison.get("best_cta") or {}).get("label", "-"))
        c5.metric("Most Emotional", (comparison.get("most_emotional_version") or {}).get("label", "-"))
        for row in comparison.get("scores", []) or []:
            with st.expander(f"{row.get('label')} · Score {row.get('overall_score', 0)}", expanded=False):
                mp4 = Path(str(row.get("final_mp4") or ""))
                if mp4.is_file():
                    st.video(str(mp4))
                    st.download_button(f"Download {row.get('label')} MP4", data=mp4.read_bytes(), file_name=mp4.name, mime="video/mp4", use_container_width=True, key=f"shorts_factory_download_{row.get('variation_id')}")
                st.caption(f"Hook {row.get('hook_score', 0)} · Retention {row.get('retention_estimate', 0)} · CTA {row.get('cta_score', 0)} · Thumbnail {row.get('thumbnail_score', 0)}")
        final_dir = Path(str(export.get("final_dir") or ""))
        if final_dir.exists():
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
                for path in final_dir.iterdir():
                    if path.is_file():
                        archive.write(path, path.name)
            st.download_button("Download Viral Experiment Package", data=zip_buffer.getvalue(), file_name="velaflow_shorts_factory.zip", mime="application/zip", use_container_width=True, key="shorts_factory_zip")
    elif state.get("safe_error_message"):
        st.warning(state.get("safe_error_message"))
    else:
        st.info("Paste a product brief or hook, then generate 5 viral variations.")


def _export_beta_feedback(project: dict[str, Any], message: str = "") -> dict[str, Any]:
    try:
        feedback_dir = ROOT / "project_data" / "feedback"
        feedback_dir.mkdir(parents=True, exist_ok=True)
        project_name = project.get("title") or "project"
        song = project.get("song", {}) or {}
        clip = song.get("creator_clip") or song.get("short_clip") or {}
        render_data = clip.get("real_output") or {}
        health = project_health_summary(project_name, "song").get("data", {})
        profile = load_beta_access()
        payload = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "app_version": APP_VERSION,
            "build_version": BUILD_VERSION,
            "beta_status": profile.get("beta_status", "active"),
            "creator_id": profile.get("creator_id", ""),
            "creator_name": profile.get("creator_name", ""),
            "message": message,
            "project": {
                "title": project_name,
                "workflow_type": project.get("workflow_type") or project.get("project_type") or "song",
            },
            "render_stage": render_data.get("render_stage", {}),
            "diagnostics_summary": {
                "render_status": health.get("render_status", ""),
                "cache_health": health.get("cache_health", ""),
                "storage_usage": health.get("storage_usage", ""),
                "failed_stages": health.get("failed_stages", []),
            },
            "api_keys_exported": False,
        }
        path = feedback_dir / f"feedback_{safe_name(project_name)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "message": "Feedback saved", "data": {"path": str(path), "payload": payload}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Feedback export failed", "data": {}, "error": str(exc)}


def _render_creator_music_flow(project: dict[str, Any]) -> None:
    st.markdown("## Create a Viral TikTok Clip")
    st.caption(f"VelaFlow Beta {APP_VERSION} · Creator Mode · Song idea → hook → finished song audio → cinematic TikTok clip")
    song = project.setdefault("song", {})
    creator_state = song.get("creator_clip") or song.get("short_clip") or {}
    content_presets = list_presets()
    preset_labels = [str(item.get("label") or item.get("preset_id")) for item in content_presets]
    default_index = next((idx for idx, item in enumerate(content_presets) if item.get("preset_id") == "emotional_story"), 0)
    with st.container(border=True):
        idea = st.text_area(
            "Song Idea",
            value=st.session_state.get("creator_song_idea", ""),
            height=140,
            key="creator_song_idea",
            placeholder="เช่น เพลงคิดถึงคนเก่าในคืนฝนตก อยากได้คลิปเศร้า ๆ แบบ TikTok",
            help="ใส่ไอเดียสั้น ๆ หรือวางท่อนเพลงที่อยากทำเป็นคลิป",
        )
        selected_label = st.selectbox(
            "Mood Preset",
            preset_labels,
            index=default_index,
            key="creator_mood_preset",
            help="เลือกอารมณ์ผลลัพธ์ ระบบจะตั้งค่าภาพ จังหวะ subtitle และ pacing ให้เอง",
        )
        selected_preset = content_presets[preset_labels.index(selected_label)] if content_presets else get_preset("emotional_story")
        st.caption(str(selected_preset.get("description") or "Designed for one-click creator output."))
        st.markdown("**Upload Finished Song**")
        audio_state = song.setdefault("creator_audio", creator_state.get("hook_audio", {}))
        song["creator_audio"] = _render_hook_audio_controls(project.get("title") or "My Viral Clip", audio_state, "creator_song_audio", "song")
        hook_audio_path = str(((song.get("creator_audio") or {}).get("hook_audio") or {}).get("path") or "")
        if hook_audio_path:
            st.caption("This hook audio will drive scene timing, subtitle emphasis, and final MP4 duration.")
        generate_clicked = st.button(
            "Generate Cinematic Hook Clip",
            type="primary",
            use_container_width=True,
            disabled=not bool(idea.strip()),
            key="creator_generate_viral_tiktok_clip",
            help="สร้าง hook, cinematic scene images, audio-synced motion, subtitles, MP4 และ TikTok package ในปุ่มเดียว",
        )
    retry_variation = st.session_state.pop("creator_retry_variation", "")
    if retry_variation:
        generate_clicked = True
    if generate_clicked:
        active_variation = retry_variation or "default"
        force_cache_refresh = active_variation in {"stronger_emotion", "faster_tiktok", "alternate_scene_style"}
        force_final_render = True
        status_box = st.status("Creating your TikTok clip...", expanded=True)
        with status_box:
            for label in ["Analyzing hook", "Generating scenes", "Rendering video", "Syncing audio", "Exporting package"]:
                st.write(label)
            result = _run_creator_one_click_clip(project, idea, selected_preset, active_variation, force_cache_refresh=force_cache_refresh, force_final_render=force_final_render, hook_audio_path=str(((song.get("creator_audio") or {}).get("hook_audio") or {}).get("path") or ""))
            if result.get("ok"):
                status_box.update(label="Clip ready", state="complete", expanded=False)
            else:
                status_box.update(label=friendly_error_message(result.get("error") or result.get("message")), state="error", expanded=False)
        data = result.get("data", {}) or {}
        song["creator_clip"] = {
            "idea": idea,
            "preset": selected_preset,
            "variation": active_variation,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "quick_generate": data,
            "real_output": data.get("render", {}),
            "final_mp4": data.get("final_mp4", ""),
            "tiktok_package": data.get("tiktok_package", {}),
            "hook_audio": (song.get("creator_audio") or {}).get("hook_audio", {}),
            "ok": bool(result.get("ok")),
            "safe_error_message": "" if result.get("ok") else friendly_error_message(result.get("error") or result.get("message")),
        }
        song["short_clip"] = song["creator_clip"]
        project["song"] = song
        _save_project()
        _log_beta_event("generate", workflow="music", preset_bundle=str(selected_preset.get("label", "Creator Mode")), metadata={"page": "Song Studio", "mode": "creator"})
        st.rerun()

    creator_state = (project.get("song", {}) or {}).get("creator_clip") or {}
    quick_data = creator_state.get("quick_generate") or {}
    real_output = creator_state.get("real_output") or {}
    st.markdown("## Final Export Package")
    if real_output and Path(str(real_output.get("final_mp4") or "")).is_file():
        _render_final_downloads("creator_music_flow", real_output)
        _render_creator_metrics(quick_data)
        _render_creator_package_downloads("creator_music_flow", creator_state.get("tiktok_package") or quick_data.get("tiktok_package") or {})
        r1, r2, r3, r4 = st.columns(4)
        if r1.button("Retry Render", use_container_width=True, key="creator_retry_render"):
            st.session_state["creator_retry_variation"] = "retry_render"
            st.rerun()
        if r2.button("Stronger Emotion", use_container_width=True, key="creator_stronger_emotion"):
            st.session_state["creator_retry_variation"] = "stronger_emotion"
            st.rerun()
        if r3.button("Faster TikTok Pace", use_container_width=True, key="creator_faster_tiktok"):
            st.session_state["creator_retry_variation"] = "faster_tiktok"
            st.rerun()
        if r4.button("Alternate Scene Style", use_container_width=True, key="creator_alternate_style"):
            st.session_state["creator_retry_variation"] = "alternate_scene_style"
            st.rerun()
    else:
        message = creator_state.get("safe_error_message") or "No clip yet. Add a song idea and tap Generate Viral TikTok Clip."
        st.info(message)
    if st.session_state.get("developer_mode"):
        health = project_health_summary(project.get("title") or "My Viral Clip", "song")
        if health.get("ok"):
            data = health.get("data", {})
            analytics = beta_analytics_summary().get("data", {})
            h1, h2, h3 = st.columns(3)
            h1.caption(f"Render success rate: {data.get('render_success_rate', 0)}%")
            h2.caption(f"Avg render time: {analytics.get('avg_render_duration', 0)}s")
            h3.caption(f"Storage: {data.get('storage_usage', '0 B')}")
        with st.expander("Send Feedback / Diagnostics", expanded=False):
            feedback_text = st.text_area("Feedback note", value="", height=90, key="creator_feedback_note", placeholder="บอกเราว่าคลิปนี้ใช้ได้ไหม มีอะไรที่อยากให้ปรับ")
            if st.button("Send Feedback", use_container_width=True, key="creator_send_feedback"):
                feedback = _export_beta_feedback(project, feedback_text)
                if feedback.get("ok"):
                    st.success("Feedback saved for beta review.")
                    st.caption((feedback.get("data") or {}).get("path", ""))
                else:
                    st.warning(friendly_error_message(feedback.get("error") or feedback.get("message")))


def _save_uploaded_audio(project_name: str, uploaded: Any, workflow_type: str = "song") -> dict[str, Any]:
    if not uploaded:
        return {"ok": False, "message": "No audio uploaded", "data": {}, "error": "missing_upload"}
    try:
        ensure_creator_project_folders(project_name or "project", workflow_type)
        folder = resolve_project_folder(project_name or "project", workflow_type) / "assets" / "audio"
        folder.mkdir(parents=True, exist_ok=True)
        suffix = Path(uploaded.name).suffix.lower() if getattr(uploaded, "name", "") else ".mp3"
        if suffix not in {".mp3", ".wav", ".m4a"}:
            suffix = ".mp3"
        path = ensure_parent_dir(folder / f"song_audio{suffix}")
        path.write_bytes(uploaded.getbuffer())
        return {"ok": True, "message": "Song audio uploaded", "data": {"path": str(path), "filename": getattr(uploaded, "name", path.name)}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Audio upload failed", "data": {}, "error": str(exc)}


def _creator_package_recommendations(full_hook: str, detection: dict[str, Any], mood: str = "") -> dict[str, Any]:
    text = f"{full_hook}\n{mood}\n{detection.get('energy_profile_summary', '')}".lower()
    duration = float(detection.get("hook_duration") or 0)
    confidence = float(detection.get("confidence_score", detection.get("confidence", 0)) or 0)
    if "dark" in text or "เหงา" in text:
        export_mode = "Dark Storytelling"
        prompt_style = "Cinematic"
        ai_tool = "Kling or Flow"
    elif "pop" in text or "viral" in text:
        export_mode = "Pop Viral"
        prompt_style = "Viral"
        ai_tool = "Flow or Veo"
    elif duration and duration <= 16:
        export_mode = "TikTok Fast Hook"
        prompt_style = "Viral"
        ai_tool = "Flow or Kling"
    elif "เศร้า" in text or "ลืม" in text or "คิดถึง" in text or "miss" in text:
        export_mode = "Sad Emotional"
        prompt_style = "Cinematic"
        ai_tool = "Kling or Runway"
    else:
        export_mode = "TikTok Emotional"
        prompt_style = "Cinematic" if confidence >= 60 else "Balanced"
        ai_tool = "Flow or Kling"
    suggested_duration = duration if duration else 22.0
    suggested_duration = min(30.0, max(15.0, suggested_duration))
    return {
        "export_mode": export_mode,
        "prompt_style": prompt_style,
        "ai_tool": ai_tool,
        "hook_duration": round(suggested_duration, 1),
    }


def _render_hook_audio_controls(project_name: str, state: dict[str, Any], key_prefix: str, workflow_type: str = "song") -> dict[str, Any]:
    st.markdown("**Hook Audio**")
    uploaded = st.file_uploader("Upload Song Audio", type=["mp3", "wav", "m4a"], key=f"{key_prefix}_song_audio_upload", help="อัปโหลดเพลงเต็ม แล้วตัดเฉพาะช่วง hook ไปใช้เป็นเสียงคลิป")
    if uploaded:
        upload_result = _save_uploaded_audio(project_name, uploaded, workflow_type)
        if upload_result.get("ok"):
            state["song_audio"] = upload_result["data"]
            st.success("Song audio uploaded")
        else:
            st.warning(upload_result.get("error") or upload_result.get("message"))
    audio_path = str((state.get("song_audio") or {}).get("path") or "")
    if audio_path:
        st.caption(f"Audio: {audio_path}")
    detect_cols = st.columns([1, 1])
    quota_saving = detect_cols[1].toggle("Quota-saving 8s hook", value=bool(state.get("quota_saving_hook", True)), key=f"{key_prefix}_quota_saving_hook")
    state["quota_saving_hook"] = quota_saving
    if detect_cols[0].button("Auto Detect Full Hook", key=f"{key_prefix}_auto_detect_hook", use_container_width=True, disabled=not bool(audio_path)):
        debug_dir = resolve_project_folder(project_name or "project", workflow_type if workflow_type in {"song", "clips"} else "song") / "exports" / "debug"
        detection = detect_hook_section(audio_path, output_dir=debug_dir, quota_saving_mode=quota_saving, ffmpeg_path=settings.ffmpeg_path)
        state["hook_detection"] = detection.get("data", {})
        if detection.get("ok"):
            st.success("Hook section detected")
        else:
            st.error(detection.get("message") or detection.get("error") or "Hook detection failed")
    detection_data = state.get("hook_detection") or {}
    if detection_data:
        with st.container(border=True):
            st.markdown("**Suggested Hook**")
            d1, d2, d3, d4 = st.columns(4)
            d1.metric("Start", f"{float(detection_data.get('hook_start_time', 0)):.1f}s")
            d2.metric("End", f"{float(detection_data.get('hook_end_time', 0)):.1f}s")
            d3.metric("Duration", f"{float(detection_data.get('hook_duration', 0)):.1f}s")
            d4.metric("Confidence", f"{int(detection_data.get('confidence', 0))}%")
            st.caption(str(detection_data.get("reason") or ""))
            if st.button("Apply Suggested Hook", key=f"{key_prefix}_apply_detected_hook", use_container_width=True):
                state["hook_start_time"] = float(detection_data.get("hook_start_time") or state.get("hook_start_time", 15.0))
                state["hook_end_time"] = float(detection_data.get("hook_end_time") or state.get("hook_end_time", 30.0))
                st.success("Suggested hook applied. You can still adjust it manually.")
                st.rerun()
    c1, c2 = st.columns(2)
    start = c1.number_input("Hook Start Time", min_value=0.0, value=float(state.get("hook_start_time", 15.0)), step=0.5, key=f"{key_prefix}_hook_start")
    end = c2.number_input("Hook End Time", min_value=1.0, value=float(state.get("hook_end_time", 30.0)), step=0.5, key=f"{key_prefix}_hook_end")
    state["hook_start_time"] = start
    state["hook_end_time"] = end
    hook_audio = str((state.get("hook_audio") or {}).get("path") or "")
    if st.button("Trim Hook Audio", key=f"{key_prefix}_trim_hook_audio", use_container_width=True, disabled=not bool(audio_path)):
        project_folder_type = workflow_type if workflow_type in {"song", "clips"} else "song"
        export_dir = resolve_project_folder(project_name or "project", project_folder_type) / "exports"
        result = trim_audio_clip(audio_path, export_dir / "hook_audio.mp3", start_time=start, end_time=end, ffmpeg_path=settings.ffmpeg_path)
        if result.get("ok"):
            state["hook_audio"] = result["data"]
            hook_audio = result["data"]["path"]
            st.success("hook_audio.mp3 exported")
        else:
            st.warning(result.get("error") or result.get("message"))
    if hook_audio and Path(hook_audio).is_file():
        st.audio(hook_audio)
        st.download_button("Download hook_audio.mp3", data=Path(hook_audio).read_bytes(), file_name="hook_audio.mp3", mime="audio/mpeg", key=f"{key_prefix}_download_hook_audio", use_container_width=True)
    return state


def _render_remaster_studio(project: dict[str, Any]) -> None:
    _page_header("Optional Creator Mastering", "Polish AI-generated songs for clearer vocal, better loudness, and streaming-ready export.", project)
    st.caption("Optional tool for finished AI songs. Local FFmpeg only. No DAW, timeline, mixer, plugin chain, video render, lip sync, or encode video workflow is added.")
    remaster_state = project.setdefault("remaster_studio", {})
    uploaded = st.file_uploader(
        "Upload song WAV/MP3",
        type=["wav", "mp3", "m4a"],
        key="remaster_audio_upload",
        help="Local FFmpeg processing only. No paid AI APIs are used.",
    )
    if uploaded:
        upload_result = _save_uploaded_audio(project.get("title") or "remaster_project", uploaded, "song")
        if upload_result.get("ok"):
            remaster_state["source_audio"] = upload_result["data"]
            project["remaster_studio"] = remaster_state
            _save_project()
            st.success("Original song uploaded")
        else:
            st.warning(upload_result.get("error") or upload_result.get("message"))
    source_path = str((remaster_state.get("source_audio") or {}).get("path") or "")
    style = st.selectbox("Select Mastering Preset", REMASTER_STYLES, index=0, key="remaster_style")
    if source_path and Path(source_path).is_file():
        st.markdown("**Preview original**")
        st.audio(source_path)
    st.caption("Processing: WAV conversion, loudness normalization, clipping protection, light EQ, optional stereo widening, high-quality WAV export.")
    if st.button("Generate Mastered WAV", type="primary", use_container_width=True, disabled=not bool(source_path), key="generate_mastered_wav"):
        with st.spinner("Generating mastered WAV locally..."):
            result = remaster_song_audio(
                source_path,
                project_name=project.get("title") or "remaster_project",
                remaster_style=style,
                ffmpeg_path=settings.ffmpeg_path,
            )
        remaster_state["last_result"] = result.get("data", {})
        remaster_state["last_ok"] = bool(result.get("ok"))
        remaster_state["last_error"] = result.get("error", "")
        project["remaster_studio"] = remaster_state
        _save_project()
        if result.get("ok"):
            st.success("Mastered WAV ready")
        else:
            st.error(result.get("error") or result.get("message") or "Remaster failed")
        st.rerun()
    result_data = remaster_state.get("last_result") or {}
    mastered_wav = Path(str(result_data.get("mastered_wav") or ""))
    mp3_preview = Path(str(result_data.get("mp3_preview") or ""))
    zip_path = Path(str(result_data.get("zip_path") or ""))
    report = result_data.get("report") or {}
    if mastered_wav.is_file():
        st.markdown("**Preview mastered**")
        st.audio(str(mastered_wav))
        c1, c2 = st.columns(2)
        c1.metric("Duration Match", "Yes" if report.get("duration_matches_original") else "Review")
        c2.metric("Clipping", "Protected" if report.get("no_clipping_above_0db") else "Check")
        st.download_button(
            "Download Mastered WAV",
            data=mastered_wav.read_bytes(),
            file_name="mastered_song.wav",
            mime="audio/wav",
            use_container_width=True,
            key="download_mastered_wav",
        )
    if mp3_preview.is_file():
        st.download_button(
            "Download MP3 Preview",
            data=mp3_preview.read_bytes(),
            file_name="mastered_preview.mp3",
            mime="audio/mpeg",
            use_container_width=True,
            key="download_mastered_mp3_preview",
        )
    if zip_path.is_file():
        st.download_button(
            "Download Remaster Package ZIP",
            data=zip_path.read_bytes(),
            file_name="remaster_package.zip",
            mime="application/zip",
            use_container_width=True,
            key="download_remaster_package_zip",
        )
    if st.session_state.get("developer_mode") and result_data.get("report_path"):
        with st.expander("Remaster Report", expanded=False):
            st.json(report, expanded=False)


def _hook_comparison_cards(detection: dict[str, Any], full_hook: str, target_duration: float) -> list[dict[str, Any]]:
    base_confidence = int(detection.get("confidence_score", detection.get("confidence", 62)) or 62)
    energy_text = str(detection.get("energy_profile_summary") or "")
    sad_bonus = 8 if any(token in full_hook for token in ["ลืม", "คิดถึง", "รัก", "เหงา", "เจ็บ"]) else 0
    return [
        {"type": "Emotional", "score": min(99, base_confidence + sad_bonus), "tone": "intimate longing", "platform": "TikTok / Shorts", "duration": f"{int(target_duration)}s"},
        {"type": "Viral", "score": min(99, base_confidence + (6 if target_duration <= 20 else 2)), "tone": "fast hook", "platform": "TikTok", "duration": "15-20s"},
        {"type": "Cinematic", "score": min(99, base_confidence + 5), "tone": "mini MV", "platform": "Flow / Kling", "duration": "20-30s"},
        {"type": "Sad", "score": min(99, base_confidence + sad_bonus + 3), "tone": "heartbreak", "platform": "Kling / Runway", "duration": "20-30s"},
        {"type": "Aggressive", "score": min(99, base_confidence + (8 if "strongest" in energy_text.lower() else 0)), "tone": "high energy", "platform": "TikTok", "duration": "15s"},
    ]


def _read_creator_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig") if path.is_file() else ""
    except Exception:
        return ""


def _render_creator_dashboard(project: dict[str, Any]) -> None:
    _page_header("Creator Dashboard", "Simple tools for songs, hooks, podcasts, affiliate scripts, and release packages.", project)
    state = project.setdefault("creator_dashboard", {})
    st.info("สร้างแพ็กเพลง เนื้อเพลง prompt caption และ checklist ได้ในหน้าเดียว โดยไม่ต้องใช้ระบบ render")

    card_cols = st.columns(5)
    cards = [
        ("Create Song Package", "ทำเพลงพร้อม Suno/Udio", "Generate Song", "CREATE", "Song Studio Only"),
        ("Create TikTok Hook", "ทำไอเดียฮุกสั้น", "Hook Clip Studio", "PRODUCTION", "Full Pipeline"),
        ("Create Podcast Clip", "ทำสคริปต์พอดแคสต์", "Podcast Studio", "PODCAST", "Podcast Studio (Beta)"),
        ("Create Affiliate Script", "ทำสคริปต์ขายสินค้า", "Affiliate Studio", "PRODUCTION", "Full Pipeline"),
        ("Open Advanced Tools", "เปิดเครื่องมือทั้งหมด", "Dashboard", "START", "Full Pipeline"),
    ]
    for col, (label, help_text, target_page, target_section, target_mode) in zip(card_cols, cards):
        with col:
            st.markdown(f"**{label}**")
            st.caption(help_text)
            if st.button("Open", key=f"creator_dashboard_card_{target_page}", use_container_width=True):
                if target_mode != "Song Studio Only":
                    st.session_state.force_developer_mode = True
                if target_mode != st.session_state.get("workflow_mode"):
                    st.session_state.workflow_mode = target_mode
                    st.session_state.pending_navigation = {"section": target_section, "page": target_page}
                    st.rerun()
                go_to_page(target_section, target_page)

    st.markdown("### One-Click Song Package")
    st.caption("ใส่ไอเดียเพลงสั้น ๆ แล้ว VelaFlow จะจัดชุดเนื้อเพลง prompt และข้อความโปรโมตให้ copy ใช้ต่อได้ทันที")
    form_cols = st.columns(2)
    idea = form_cols[0].text_area("Song idea", value=state.get("idea", ""), height=120, key="creator_dashboard_song_idea", help="เช่น เพลงเศร้าในออฟฟิศ หรือ คนที่ยังลืมแฟนเก่าไม่ได้")
    mood = form_cols[1].text_input("Mood", value=state.get("mood", "emotional"), key="creator_dashboard_mood", help="อารมณ์เพลง เช่น เศร้า อบอุ่น เหงา มีหวัง")
    genre = form_cols[0].selectbox(
        "Genre",
        list(CREATIVE_PACK_PRESETS),
        index=list(CREATIVE_PACK_PRESETS).index(state.get("genre", "Vela Moon Emotional Pop Rock")) if state.get("genre") in CREATIVE_PACK_PRESETS else list(CREATIVE_PACK_PRESETS).index("Vela Moon Emotional Pop Rock"),
        key="creator_dashboard_genre",
    )
    vocal_style = form_cols[1].text_input("Vocal style", value=state.get("vocal_style", "Thai male vocal, warm emotional tone"), key="creator_dashboard_vocal_style")
    language = form_cols[0].selectbox("Language", ["Thai", "English", "Thai + English"], index=["Thai", "English", "Thai + English"].index(state.get("language", "Thai")) if state.get("language") in {"Thai", "English", "Thai + English"} else 0, key="creator_dashboard_language")
    if st.button("Generate Song Package", type="primary", use_container_width=True, key="creator_dashboard_generate_song_package"):
        combined_idea = "\n".join(
            [
                str(idea or "").strip(),
                f"Mood: {mood}",
                f"Vocal style: {vocal_style}",
                f"Language: {language}",
            ]
        ).strip()
        result = generate_creative_release_pack(combined_idea, genre, str(project.get("artist") or DEFAULT_ARTIST))
        state.update({"idea": idea, "mood": mood, "genre": genre, "vocal_style": vocal_style, "language": language, "result": result})
        project["creator_dashboard"] = state
        project.setdefault("song", {})["idea"] = idea
        project["song"]["title"] = (result.get("pack") or {}).get("Suggested title", "")
        project["song"]["complete_lyrics"] = (result.get("pack") or {}).get("Full lyrics", "")
        project["song"]["style_prompt"] = (result.get("pack") or {}).get("AI PRODUCER PROMPT", (result.get("pack") or {}).get("AI Producer Prompt", (result.get("pack") or {}).get("Music style prompt for Suno/Udio", "")))
        _save_project()
        st.success("Song package ready")
        st.rerun()

    result = state.get("result") or {}
    pack = result.get("pack") or {}
    if not pack:
        st.caption("เริ่มจากไอเดียเพลง แล้วกด Generate Song Package")
        return

    output_blocks = [
        ("Song Title Suggestions", pack.get("Suggested title", "")),
        ("Structured Lyrics", pack.get("Full lyrics", "")),
        ("Lyrics for Suno", pack.get("SUNO LYRICS FIELD", pack.get("Full lyrics", ""))),
        ("Style for Suno", pack.get("SUNO STYLE OF MUSIC FIELD", "")),
        ("Producer Notes", pack.get("PRODUCER NOTES", pack.get("AI PRODUCER PROMPT", ""))),
        ("SEO Caption", pack.get("Caption", "")),
        ("YouTube Description", pack.get("YouTube description", "")),
        ("Hashtags", pack.get("Hashtags", "")),
        ("Cover Prompt", pack.get("Cover prompt", "")),
        ("Release Checklist", "1. Copy lyrics into Suno/Udio\n2. Use the producer prompt as style guidance\n3. Generate 2-3 takes\n4. Pick the strongest hook\n5. Use cover prompt and captions for release"),
    ]
    for idx, (label, value) in enumerate(output_blocks):
        st.button(f"Copy {label}", key=f"creator_dashboard_copy_{idx}", use_container_width=True)
        st.text_area(label, value=value, height=160 if len(str(value)) > 240 else 90, key=f"creator_dashboard_output_{idx}")

    txt_payload = creative_release_pack_to_text(result)
    st.download_button(
        "Download Full Package TXT",
        data=txt_payload.encode("utf-8-sig"),
        file_name="velaflow_song_package.txt",
        mime="text/plain",
        use_container_width=True,
        key="creator_dashboard_download_txt",
    )


def _render_ai_creative_pack_generator(project: dict[str, Any], active_stage: str = "Idea") -> None:
    _page_header("AI Creative Pack Generator", "Create lyrics, prompts, storyboard, captions, and release package. Render outside with your favorite tools.", project)
    state = project.setdefault("creative_pack_v1", {})
    st.info("Create lyrics, prompts, storyboard, captions, and release package. Render outside with your favorite tools.")
    stage_cols = st.columns(4)
    stages = ["Idea", "Generate Song", "Generate Visual Pack", "Export Release Pack"]
    for idx, stage in enumerate(stages):
        if stage == active_stage:
            stage_cols[idx].success(stage)
        else:
            stage_cols[idx].caption(stage)

    preset_names = list(CREATIVE_PACK_PRESETS)
    with st.container(border=True):
        st.markdown("### Quick Start")
        q1, q2, q3 = st.columns(3)
        q1.markdown("**1. Choose preset**")
        q1.caption("Pick the creative direction.")
        q2.markdown("**2. Enter song idea**")
        q2.caption("Write one simple concept.")
        q3.markdown("**3. Generate & Export**")
        q3.caption("Download TXT or ZIP.")
    with st.container(border=True):
        st.markdown("### Idea")
        c1, c2 = st.columns([2, 1])
        idea = c1.text_area(
            "Song idea / creative concept",
            value=state.get("idea", str((project.get("song", {}) or {}).get("idea") or "")),
            height=150,
            key="creative_pack_idea",
            help="ใส่ไอเดียสั้น ๆ เช่น เพลงเศร้าในออฟฟิศ หรือ รักคนที่ไม่กลับมา",
        )
        preset = c2.selectbox(
            "Quality Preset",
            preset_names,
            index=preset_names.index(state.get("preset", "Thai Sad Pop")) if state.get("preset") in preset_names else 0,
            key="creative_pack_preset",
        )
        artist_name = c2.text_input("Artist name", value=state.get("artist_name", str(project.get("artist") or DEFAULT_ARTIST)), key="creative_pack_artist")
        st.caption("High-quality presets include Thai Sad Pop, Office Burnout, TikTok Emotional Hook, plus Vela Moon Signature Pop Rock presets for Spotify-friendly Thai emotional pop rock.")

    generate_pack = st.button(
        "Generate Full Release Pack",
        type="primary",
        use_container_width=True,
        disabled=not bool(str(idea or "").strip()),
        key="creative_pack_generate_full_release_pack",
    )
    if generate_pack:
        result = generate_creative_release_pack(idea, preset, artist_name)
        export = export_creative_release_pack(project.get("title") or result["pack"].get("Suggested title") or "VelaFlow Release", result, artist_name)
        state.update(
            {
                "idea": idea,
                "preset": preset,
                "artist_name": artist_name,
                "release_pack": result,
                "export": export.get("data", {}),
                "last_error": export.get("error", ""),
            }
        )
        project["creative_pack_v1"] = state
        project.setdefault("song", {})["idea"] = idea
        project["song"]["title"] = result["pack"].get("Suggested title", "")
        project["song"]["complete_lyrics"] = result["pack"].get("Full lyrics", "")
        project["song"]["style_prompt"] = result["pack"].get("AI PRODUCER PROMPT", result["pack"].get("AI Producer Prompt", result["pack"].get("Music style prompt for Suno/Udio", "")))
        _save_project()
        _log_beta_event("generate", workflow="creative_pack_v1", metadata={"page": active_stage, "preset": preset})
        if export.get("ok"):
            st.success("Release Pack ready")
        else:
            st.warning(export.get("error") or "Release Pack generated, but export failed")
        st.rerun()

    result = state.get("release_pack") or {}
    pack = result.get("pack") or {}
    export_data = state.get("export") or {}
    if not pack:
        st.caption("Ready when you are: choose a preset, enter a song idea, then click Generate Full Release Pack.")
        return

    st.markdown("### Generate Song")
    song_cols = st.columns(3)
    song_cols[0].metric("Suggested Title", pack.get("Suggested title", "-"))
    song_cols[1].metric("Preset", result.get("preset", "-"))
    song_cols[2].metric("Mode", "No Render")
    st.text_area("Song concept", value=pack.get("Song concept", ""), height=110, key="creative_pack_song_concept")
    st.text_area("Hook", value=pack.get("Hook", ""), height=120, key="creative_pack_hook")
    st.button("Copy Lyrics for Suno", use_container_width=True, key="creative_pack_copy_suno_lyrics")
    st.text_area("Suno Lyrics Field", value=pack.get("SUNO LYRICS FIELD", pack.get("Full lyrics", "")), height=300, key="creative_pack_full_lyrics")
    st.button("Copy Style for Suno", use_container_width=True, key="creative_pack_copy_suno_style")
    st.text_area("Suno Style of Music Field", value=pack.get("SUNO STYLE OF MUSIC FIELD", ""), height=140, key="creative_pack_suno_style_field")
    st.button("Copy Producer Notes", use_container_width=True, key="creative_pack_copy_producer_notes")
    st.text_area("Producer Notes", value=pack.get("PRODUCER NOTES", pack.get("AI PRODUCER PROMPT", pack.get("Music style prompt for Suno/Udio", ""))), height=260, key="creative_pack_music_style")
    st.text_area("Advanced Suno Settings", value=pack.get("Advanced Suno Settings", ""), height=150, key="creative_pack_advanced_suno_settings")

    st.markdown("### Generate Visual Pack")
    visual_cols = st.columns(2)
    with visual_cols[0]:
        st.button("Copy Cover Prompt", use_container_width=True, key="creative_pack_copy_cover")
        st.text_area("Cover prompt", value=pack.get("Cover prompt", ""), height=140, key="creative_pack_cover_prompt")
        st.button("Copy MV Storyboard Prompt", use_container_width=True, key="creative_pack_copy_storyboard")
        st.text_area("MV storyboard prompt", value=pack.get("MV storyboard prompt", ""), height=170, key="creative_pack_mv_storyboard_prompt")
    with visual_cols[1]:
        st.button("Copy Shorts/TikTok Ideas", use_container_width=True, key="creative_pack_copy_shorts")
        st.text_area("Shorts/TikTok ideas", value=pack.get("Shorts/TikTok ideas", ""), height=160, key="creative_pack_shorts_ideas")
        st.button("Copy Caption", use_container_width=True, key="creative_pack_copy_caption")
        st.text_area("Caption", value=pack.get("Caption", ""), height=110, key="creative_pack_caption")
        st.text_area("Hashtags", value=pack.get("Hashtags", ""), height=90, key="creative_pack_hashtags")

    st.markdown("### Export Release Pack")
    st.text_area("YouTube description", value=pack.get("YouTube description", ""), height=160, key="creative_pack_youtube_description")
    st.text_area("Release notes", value=pack.get("Release notes", ""), height=120, key="creative_pack_release_notes")
    txt_payload = creative_release_pack_to_text(result)
    download_cols = st.columns(2)
    txt_name = Path(str(export_data.get("txt_path") or "velaflow_release_pack.txt")).name
    zip_path = Path(str(export_data.get("zip_path") or ""))
    download_cols[0].download_button(
        "Download TXT",
        data=txt_payload.encode("utf-8-sig"),
        file_name=txt_name,
        mime="text/plain",
        use_container_width=True,
        key="creative_pack_download_txt",
    )
    if zip_path.is_file():
        download_cols[1].download_button(
            "Download ZIP",
            data=zip_path.read_bytes(),
            file_name=zip_path.name,
            mime="application/zip",
            use_container_width=True,
            key="creative_pack_download_zip",
        )
    elif state.get("last_error"):
        download_cols[1].warning(state.get("last_error"))


def _render_one_click_creator_flow(project: dict[str, Any]) -> None:
    _page_header("One Click Creator Flow", "Finish lyrics, hook prompts, remaster, and creator ZIP in one stable local workflow.", project)
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"] { border-color: rgba(255,255,255,0.10); border-radius: 14px; }
        .velaflow-creator-hero { padding: 1rem 1.1rem; border-radius: 16px; background: linear-gradient(135deg, rgba(34,34,46,.92), rgba(18,18,24,.94)); border: 1px solid rgba(255,255,255,.10); }
        .velaflow-creator-hero h3 { margin: 0 0 .35rem 0; }
        .velaflow-pill { display: inline-block; padding: .24rem .55rem; border-radius: 999px; background: rgba(255,255,255,.08); margin-right: .35rem; font-size: .78rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    beta_profile = load_beta_access()
    st.markdown(
        f"""
        <div class="velaflow-creator-hero">
          <span class="velaflow-pill">VelaFlow Closed Beta</span>
          <span class="velaflow-pill">Founding Member</span>
          <span class="velaflow-pill">Local FFmpeg Workflow</span>
          <h3>Upload song → receive creator package</h3>
          <p style="margin:.15rem 0 0 0;color:rgba(255,255,255,.72)">Built for Flow, Veo, Runway, Kling, CapCut, TikTok, Shorts, and Spotify promo workflows.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(f"Founding Creator: {beta_profile.get('creator_name', 'Founding Creator')} · Exports: {beta_profile.get('total_renders', 0)}")
    st.markdown("### Quick Start")
    with st.container(border=True):
        st.markdown(
            "1. Upload or paste your finished song/lyrics  \n"
            "2. Detect the strongest full hook  \n"
            "3. Generate creator prompts and scene plan  \n"
            "4. Remaster audio locally  \n"
            "5. Download one final creator ZIP"
        )
    with st.expander("Example workflows", expanded=False):
        st.table(
            [
                {"Workflow": "Emotional TikTok hook", "Target": "20s", "Export Mode": "TikTok Emotional", "Remaster": "TikTok Loud"},
                {"Workflow": "Spotify teaser", "Target": "15s", "Export Mode": "Spotify Canvas", "Remaster": "Spotify Balanced"},
                {"Workflow": "Cinematic MV preview", "Target": "30s", "Export Mode": "Cinematic MV", "Remaster": "Cinematic Wide"},
                {"Workflow": "Sad short", "Target": "20s", "Export Mode": "Sad Emotional", "Remaster": "Emotional Soft"},
            ]
        )
    with st.expander("Creator tips", expanded=False):
        st.markdown(
            "- Use 20s for emotional TikTok hooks.  \n"
            "- Use 15s for aggressive short hooks.  \n"
            "- Use 30s for cinematic MV teasers.  \n"
            "- Copy Flow/Kling prompts first for fast external video generation."
        )
    flow_state = project.setdefault("one_click_creator", {})
    lyrics_source = str((project.get("song", {}) or {}).get("complete_lyrics") or (project.get("song", {}) or {}).get("normalized_song_output") or "")
    lyrics_text = st.text_area("Lyrics / Song Hook", value=flow_state.get("lyrics_text", lyrics_source), height=220, key="one_click_lyrics")
    flow_state["lyrics_text"] = lyrics_text
    uploaded = st.file_uploader("Upload finished song", type=["mp3", "wav", "m4a"], key="one_click_song_upload")
    if uploaded:
        upload_result = _save_uploaded_audio(project.get("title") or "one_click_creator", uploaded, "song")
        if upload_result.get("ok"):
            flow_state["source_audio"] = upload_result["data"]
            project["one_click_creator"] = flow_state
            _save_project()
            st.success("Song uploaded")
        else:
            st.warning(upload_result.get("error") or upload_result.get("message"))
    source_path = str((flow_state.get("source_audio") or {}).get("path") or "")
    if source_path and Path(source_path).is_file():
        source_probe = probe_media(source_path, ffmpeg_path=settings.ffmpeg_path)
        if not source_probe.get("ok") or not source_probe.get("has_audio", True):
            st.error("Invalid audio file. Please upload a playable WAV/MP3/M4A.")
            source_path = ""
        else:
            st.audio(source_path)
    c1, c2, c3 = st.columns(3)
    target_duration = float(c1.selectbox("Target Hook", [15, 20, 30], index=1, key="one_click_target_hook_duration"))
    remaster_style = c2.selectbox("Remaster Preset", REMASTER_STYLES, index=0, key="one_click_remaster_style")
    export_mode = c3.selectbox("Export Mode", CREATOR_EXPORT_MODES, index=0, key="one_click_export_mode")
    prompt_style = st.selectbox("Prompt Style", PROMPT_STYLES, index=1, key="one_click_prompt_style")
    detection = flow_state.get("hook_detection") or {}
    if source_path:
        if st.button("Auto Detect Best Full Hook", use_container_width=True, key="one_click_detect_hook"):
            debug_dir = resolve_project_folder(project.get("title") or "one_click_creator", "song") / "exports" / "debug"
            detected = detect_hook_section(source_path, output_dir=debug_dir, quota_saving_mode=False, min_hook_duration=target_duration, max_hook_duration=target_duration, ffmpeg_path=settings.ffmpeg_path)
            flow_state["hook_detection"] = detected.get("data", {})
            project["one_click_creator"] = flow_state
            _save_project()
            if detected.get("ok"):
                st.success("Full hook detected")
            else:
                st.error(detected.get("error") or detected.get("message") or "Hook detection failed")
            st.rerun()
    full_hook = extract_full_hook_section(lyrics_text, fallback_hook=str((project.get("song", {}) or {}).get("selected_hook_text") or ""))
    if detection:
        st.markdown("### Hook Comparison Cards")
        card_cols = st.columns(5)
        for idx, card in enumerate(_hook_comparison_cards(detection, full_hook, target_duration)):
            with card_cols[idx]:
                st.metric(card["type"], card["score"])
                st.caption(f"{card['tone']} · {card['platform']} · {card['duration']}")
        rec = _creator_package_recommendations(full_hook, detection, str((project.get("song", {}) or {}).get("mood") or ""))
        st.info(f"Recommended: {rec['export_mode']} · {rec['prompt_style']} · {rec['ai_tool']} · {rec['hook_duration']}s")
    if st.button("Generate Creator Package", type="primary", use_container_width=True, disabled=not bool(source_path), key="one_click_generate_creator_package"):
        progress = st.progress(0, text="analyzing song")
        debug_dir = resolve_project_folder(project.get("title") or "one_click_creator", "song") / "exports" / "debug"
        detected = detect_hook_section(source_path, output_dir=debug_dir, quota_saving_mode=False, min_hook_duration=target_duration, max_hook_duration=target_duration, ffmpeg_path=settings.ffmpeg_path)
        if not detected.get("ok"):
            st.error(detected.get("error") or "Hook detection failed")
            return
        progress.progress(20, text="detecting hook")
        data = detected["data"]
        package = generate_full_hook_creator_package(
            project_name=project.get("title") or "one_click_creator",
            uploaded_mp3_path=source_path,
            lyrics_text=lyrics_text,
            fallback_hook=full_hook,
            song_title=str((project.get("song", {}) or {}).get("title") or project.get("title") or ""),
            artist_name=str((project.get("song", {}) or {}).get("artist_name") or project.get("artist") or ""),
            mood=str((project.get("song", {}) or {}).get("mood") or ""),
            export_mode=export_mode,
            prompt_style=prompt_style,
            hook_start_time=float(data.get("hook_start_time") or 0),
            hook_end_time=float(data.get("hook_end_time") or target_duration),
            ffmpeg_path=settings.ffmpeg_path,
        )
        if not package.get("ok"):
            st.error(package.get("error") or "Creator prompt package failed")
            return
        progress.progress(45, text="generating prompts")
        remaster = remaster_song_audio(source_path, project_name=project.get("title") or "one_click_creator", remaster_style=remaster_style, ffmpeg_path=settings.ffmpeg_path)
        if not remaster.get("ok"):
            st.error(remaster.get("error") or "Remaster failed")
            return
        progress.progress(70, text="remastering audio")
        final_zip = build_final_creator_zip(
            package_dir=package["data"]["package_dir"],
            original_audio_path=source_path,
            remaster_data=remaster["data"],
            output_zip_path=resolve_project_folder(project.get("title") or "one_click_creator", "song") / "exports" / "final_creator_package.zip",
        )
        progress.progress(90, text="building creator package")
        flow_state["hook_detection"] = data
        flow_state["creator_package"] = package.get("data", {})
        flow_state["remaster"] = remaster.get("data", {})
        flow_state["final_zip"] = final_zip.get("data", {})
        flow_state["last_ok"] = bool(final_zip.get("ok"))
        flow_state["last_error"] = final_zip.get("error", "")
        project["one_click_creator"] = flow_state
        _save_project()
        if final_zip.get("ok"):
            register_beta_activity(1)
        progress.progress(100, text="complete")
        if final_zip.get("ok"):
            st.success("Final Creator ZIP ready")
        else:
            st.warning(final_zip.get("error") or "Final ZIP created with missing files")
        st.rerun()
    final_zip_path = Path(str((flow_state.get("final_zip") or {}).get("zip_path") or ""))
    remaster_data = flow_state.get("remaster") or {}
    source_audio_path = Path(source_path)
    mastered = Path(str(remaster_data.get("mastered_wav") or ""))
    if source_audio_path.is_file() or mastered.is_file():
        st.markdown("### Original vs Mastered")
        if source_audio_path.is_file():
            st.markdown("**Play Original**")
            st.audio(str(source_audio_path))
        if mastered.is_file():
            st.markdown("**Play Mastered**")
            st.audio(str(mastered))
            st.caption("A/B Compare: play each preview above and switch between them.")
    if final_zip_path.is_file():
        package_dir = Path(str((flow_state.get("creator_package") or {}).get("package_dir") or ""))
        st.markdown("### Creator Delivery")
        d1, d2, d3 = st.columns(3)
        d1.success("Hook Ready")
        d2.success("Prompt Package Ready")
        d3.success("Remastered Audio Ready")
        d1, d2, d3 = st.columns(3)
        d1.success("Subtitle Ready")
        d2.success("Thumbnail Prompt Ready")
        d3.success("Creator ZIP Ready")
        st.download_button("Download Creator ZIP", data=final_zip_path.read_bytes(), file_name="velaflow_final_creator_package.zip", mime="application/zip", use_container_width=True, key="one_click_download_final_zip")
        if package_dir.is_dir():
            copy_cols = st.columns(2)
            with copy_cols[0]:
                st.text_area("Copy Flow Prompt", value=_read_creator_file(package_dir / "video_prompt_flow.txt"), height=120, key="one_click_copy_flow_prompt")
            with copy_cols[1]:
                st.text_area("Copy Veo Prompt", value=_read_creator_file(package_dir / "video_prompt_veo.txt"), height=120, key="one_click_copy_veo_prompt")
            copy_cols = st.columns(2)
            with copy_cols[0]:
                st.text_area("Copy TikTok Caption", value=_read_creator_file(package_dir / "tiktok_caption.txt"), height=120, key="one_click_copy_tiktok_caption")
            with copy_cols[1]:
                st.text_area("Copy Thumbnail Prompt", value=_read_creator_file(package_dir / "thumbnail_prompt.txt"), height=120, key="one_click_copy_thumbnail_prompt")
        with st.expander("Send beta feedback", expanded=False):
            feedback_text = st.text_area("What felt confusing or useful?", value="", height=90, key="one_click_feedback_text")
            if st.button("Send Feedback", use_container_width=True, key="one_click_send_feedback"):
                feedback = _export_beta_feedback(project, feedback_text)
                if feedback.get("ok"):
                    st.success("Feedback saved for the beta team.")
                else:
                    st.warning(friendly_error_message(feedback.get("error") or feedback.get("message")))
    elif (flow_state.get("creator_package") or {}).get("package_dir") and (flow_state.get("remaster") or {}).get("mastered_wav"):
        if st.button("Retry Export ZIP", use_container_width=True, key="one_click_retry_export_zip"):
            retry = build_final_creator_zip(
                package_dir=(flow_state.get("creator_package") or {}).get("package_dir", ""),
                original_audio_path=source_path,
                remaster_data=flow_state.get("remaster") or {},
                output_zip_path=resolve_project_folder(project.get("title") or "one_click_creator", "song") / "exports" / "final_creator_package.zip",
            )
            flow_state["final_zip"] = retry.get("data", {})
            flow_state["last_ok"] = bool(retry.get("ok"))
            flow_state["last_error"] = retry.get("error", "")
            project["one_click_creator"] = flow_state
            _save_project()
            st.rerun()


def _image_provider_controls(key_prefix: str) -> tuple[str, dict[str, Any]]:
    labels = ["Offline Placeholder", "OpenAI Images", "Gemini Image"]
    selected = st.selectbox(
        "Image Provider",
        labels,
        index=0,
        key=f"{key_prefix}_image_provider",
        help="เลือกตัวสร้างภาพฉาก ถ้า provider ใช้ไม่ได้ VelaFlow จะ fallback เป็น placeholder อัตโนมัติ",
    )
    provider = {
        "Offline Placeholder": "offline",
        "OpenAI Images": "openai_images",
        "Gemini Image": "gemini_image",
    }[selected]
    settings_payload = {
        "size": "1024x1536",
        "quality": "medium",
        "cache_enabled": False,
        "openai_api_key": _user_api_key("openai"),
        "gemini_api_key": _user_api_key("gemini"),
        "openai_image_model": getattr(settings, "openai_image_model", "gpt-image-1.5"),
    }
    if provider == "openai_images" and not settings_payload["openai_api_key"]:
        st.info("OpenAI key missing. Placeholder images will be used.")
    if provider == "gemini_image" and not settings_payload["gemini_api_key"]:
        st.info("Gemini key missing. Placeholder images will be used.")
    return provider, settings_payload


def _safe_provider_error_text(detail: Any) -> str:
    if isinstance(detail, dict):
        return str(detail.get("provider_error_detail") or detail.get("safe_message") or detail.get("category") or "").strip()
    return str(detail or "").strip()


def _render_veo_diagnostics_card(title: str, data: dict[str, Any] | None) -> None:
    if not data:
        return
    detail = data.get("provider_error_detail", "")
    if isinstance(detail, dict):
        provider_error_detail = _safe_provider_error_text(detail)
        sdk_exception_type = str(detail.get("sdk_exception_type") or data.get("sdk_exception_type") or "")
        request_model = str(detail.get("request_model") or data.get("request_model") or "")
        provider_method = str(detail.get("provider_method") or data.get("provider_method") or "")
    else:
        provider_error_detail = _safe_provider_error_text(detail or data.get("error") or data.get("message") or "")
        sdk_exception_type = str(data.get("sdk_exception_type") or "")
        request_model = str(data.get("request_model") or "")
        provider_method = str(data.get("provider_method") or "")
    if not any([provider_error_detail, sdk_exception_type, request_model, provider_method]):
        return
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.caption("Safe diagnostics only. API keys are never displayed.")
        c1, c2 = st.columns(2)
        c1.text_input("request_model", value=request_model or "-", disabled=True, key=f"{safe_name(title)}_request_model")
        c2.text_input("provider_method", value=provider_method or "-", disabled=True, key=f"{safe_name(title)}_provider_method")
        c1.text_input("sdk_exception_type", value=sdk_exception_type or "-", disabled=True, key=f"{safe_name(title)}_sdk_exception_type")
        c2.text_input("status/error", value=str(data.get("status") or data.get("error") or "-"), disabled=True, key=f"{safe_name(title)}_status")
        st.text_area("provider_error_detail", value=provider_error_detail or "-", height=90, disabled=True, key=f"{safe_name(title)}_provider_error_detail")


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
    ffmpeg_info = ffmpeg_version(settings.ffmpeg_path)
    ffmpeg_ready = bool(ffmpeg_info.get("ok"))
    if ffmpeg_ready:
        configure_moviepy_ffmpeg(settings.ffmpeg_path)
    st.write("Creator Render")
    st.caption("Simple vertical clip rendering for creators. Default output is 9:16. If rendering is unavailable, VelaFlow shows a warning and keeps the scene package ready.")
    if ffmpeg_ready:
        st.success(f"✅ FFmpeg runtime ready: {ffmpeg_info.get('path')}")
    else:
        st.warning("⚠ FFmpeg runtime unavailable. Local MP4 render buttons are disabled, but provider packages and Veo scene jobs still work.")
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Queued", "Yes" if creator_status in {"queued", "rendering", "completed"} else "No")
    p2.metric("Rendering", "Yes" if creator_status == "rendering" else "No")
    p3.metric("Completed", "Yes" if existing.get("final_mp4") and Path(existing.get("final_mp4", "")).is_file() else "No")
    p4.metric("Scenes", f"{completed_scenes}/{len(scenes)}")

    use_voiceover = st.checkbox("Generate voiceover MP3", value=workflow_type in {"podcast", "viral_clips"}, key=f"{section_key}_real_voiceover")
    voice_style = st.selectbox("Voiceover Style", VOICEOVER_STYLES, index=VOICEOVER_STYLES.index(default_voice_style) if default_voice_style in VOICEOVER_STYLES else 0, key=f"{section_key}_real_voice_style")
    col_start, col_scene, col_all = st.columns(3)
    if col_start.button("🎬 Start Render", type="primary", use_container_width=True, key=f"{section_key}_start_render"):
        project.setdefault(section_key, {})["creator_render_status"] = "queued"
        if scenes:
            st.success("REAL PROVIDER MODE ready. Render Scene 1, Render All Scenes, or submit Scene 1 to Veo.")
        else:
            st.warning("Scene package is missing. Generate the hook/storyboard package first.")
        _save_project()
        st.rerun()
    if col_scene.button("🎬 Render Scene 1", use_container_width=True, disabled=not ffmpeg_ready, key=f"{section_key}_render_scene_1"):
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
    if col_all.button("🎬 Render All Scenes", use_container_width=True, disabled=not ffmpeg_ready, key=f"{section_key}_render_all_scenes"):
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
        st.markdown("**REAL PROVIDER MODE - Google Veo Scene 1 / Image-to-video render**")
        st.caption("Use BYO Gemini/Veo key. No mock_xxx job IDs are shown here. If Veo is unavailable, local MP4 scene rendering remains available above.")
        veo_runtime = build_provider_runtime_diagnostics("gemini", _user_api_key("gemini"), api_mode=st.session_state.get("api_mode", API_MODE_OWN_KEY), source="user")
        st.caption(
            f"Gemini runtime: {veo_runtime.get('status')} · "
            f"Gemini client: {'ready' if veo_runtime.get('gemini_client_initialized') else 'not ready'} · "
            f"Veo: {'capable' if veo_runtime.get('veo_render_capable') else 'unavailable'}"
        )
        scene_job = scene_jobs.get("scene_01", {})
        c_test, c_models = st.columns(2)
        if c_test.button("Test Veo Connection", use_container_width=True, key=f"{section_key}_veo_test_connection"):
            result = test_veo_connection(_user_api_key("gemini"))
            st.session_state[f"{section_key}_veo_connection_diagnostics"] = result.get("data", {})
            if result.get("ok"):
                st.success(result.get("message", "Veo connection ready"))
            else:
                detail = result.get("data", {}).get("provider_error_detail") or result.get("message")
                st.warning(_safe_provider_error_text(detail) or result.get("error") or "Veo connection failed")
        if c_models.button("Available Veo Models", use_container_width=True, key=f"{section_key}_veo_available_models"):
            result = list_available_veo_models(_user_api_key("gemini"))
            st.session_state[f"{section_key}_veo_models_diagnostics"] = result.get("data", {})
            if result.get("ok"):
                models = result.get("data", {}).get("models", [])
                if models:
                    st.dataframe(pd.DataFrame(models), use_container_width=True, hide_index=True)
                else:
                    st.info(result.get("data", {}).get("provider_error_detail") or result.get("message"))
            else:
                detail = result.get("data", {}).get("provider_error_detail") or result.get("message")
                st.warning(_safe_provider_error_text(detail) or result.get("error") or "Model diagnostics failed")
        _render_veo_diagnostics_card("Veo Connection Diagnostics", st.session_state.get(f"{section_key}_veo_connection_diagnostics", {}))
        _render_veo_diagnostics_card("Available Veo Models Diagnostics", st.session_state.get(f"{section_key}_veo_models_diagnostics", {}))
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
                    detail = result.get("data", {}).get("job", {}).get("provider_error_detail") or result.get("message")
                    st.warning(_safe_provider_error_text(detail) or result.get("error") or "Veo submit failed")
                st.rerun()
        if c_poll.button("Check Veo Status", use_container_width=True, key=f"{section_key}_veo_poll_scene_01"):
            result = poll_veo_scene_job(project_name, _user_api_key("gemini"), "scene_01")
            if result.get("ok"):
                st.success(f"Scene 1 status: {result['data']['job'].get('status')}")
            else:
                detail = result.get("data", {}).get("job", {}).get("provider_error_detail") or result.get("message")
                st.warning(_safe_provider_error_text(detail) or result.get("error") or "Veo status check failed")
            st.rerun()
        if c_download.button("Download Veo Scene 1", use_container_width=True, key=f"{section_key}_veo_download_scene_01"):
            result = download_veo_scene_result(project_name, _user_api_key("gemini"), "scene_01")
            if result.get("ok"):
                st.success("scene_01.mp4 downloaded")
            else:
                detail = result.get("data", {}).get("job", {}).get("provider_error_detail") or result.get("message")
                st.warning(_safe_provider_error_text(detail) or result.get("error") or "Veo download failed")
            st.rerun()
        if scene_job:
            detail = scene_job.get("provider_error_detail")
            if detail:
                st.warning(_safe_provider_error_text(detail))
            _render_veo_diagnostics_card("Scene 1 Provider Diagnostics", scene_job)
            st.json({key: value for key, value in scene_job.items() if key != "payload"}, expanded=False)

    if st.button("Combine Final Clip", use_container_width=True, disabled=not ffmpeg_ready, key=f"{section_key}_combine_final_clip"):
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
        "provider_runtime": {},
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
    autosave_project_state(
        project_context.get("title", "project"),
        project_context.get("workflow_type") or project_context.get("project_type"),
        project_context,
    )


def _render_project_health_card(project_name: str, workflow_type: str = "song", key_prefix: str = "project_health") -> None:
    health = project_health_summary(project_name, workflow_type)
    if not health.get("ok"):
        return
    data = health.get("data", {}) or {}
    with st.expander("Project Health", expanded=False):
        h1, h2, h3 = st.columns(3)
        h1.metric("Render", str(data.get("render_status") or "idle").title())
        h2.metric("Cache", str(data.get("cache_health") or "ok").title())
        h3.metric("Storage", data.get("storage_usage", "0 B"))
        latest = data.get("latest_successful_render")
        if latest:
            st.caption(f"Latest successful render: {latest}")
        failed = data.get("failed_stages") or []
        if failed:
            st.warning("Recoverable issue: " + ", ".join(str(item) for item in failed))
        else:
            st.caption("No failed render stages detected.")
        if st.button("Clean Safe Runtime Files", key=f"{key_prefix}_cleanup", use_container_width=True):
            result = cleanup_project_storage(project_name, workflow_type, keep_versions=3, dry_run=False)
            removed = len((result.get("data") or {}).get("deleted") or [])
            st.success(f"Cleanup complete. Removed {removed} safe runtime item(s).")
            st.rerun()
        if st.session_state.get("developer_mode"):
            queue = load_creator_render_queue(project_name, workflow_type).get("data", {})
            st.json({"queue": queue, "health": data}, expanded=False)


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
    creator_mode = not st.session_state.get("developer_mode", False)
    continue_label = "Continue to Clip Studio" if creator_mode else "Continue to MV Director"
    continue_help = "ไปต่อขั้นตอนอัปโหลดเพลงและสร้าง cinematic hook clip" if creator_mode else "ไปต่อขั้นตอนวางแผน MV จากเนื้อเพลงที่บันทึกแล้ว"
    with d4:
        if st.button(continue_label, use_container_width=True, key="suno_continue_mv", help=continue_help):
            if creator_mode:
                go_to_page("MUSIC", "Hook Clip Studio")
            else:
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


def _render_creator_lyrics_action_bar(project: dict[str, Any], song: dict[str, Any], edited_lyrics: str, *, key_prefix: str) -> None:
    project_name = project.get("title") or song.get("title") or "VelaFlow Song"
    workflow_mode = st.session_state.get("workflow_mode", "Song Studio Only")
    temp_song = {**song, "complete_lyrics": edited_lyrics, "normalized_song_output": edited_lyrics}
    export_result = export_suno_files(project_name, temp_song, workflow_mode=workflow_mode) if str(edited_lyrics or "").strip() else {"ok": False, "data": {}}
    export_data = export_result.get("data", {}) if export_result.get("ok") else {}
    lyrics_txt = export_data.get("lyrics_only_text") or edited_lyrics
    suno_txt = export_data.get("suno_full_text") or edited_lyrics
    suno_filename = export_data.get("suno_full_filename") or resolve_export_txt_filename(temp_song, project_name, workflow_mode, suno_txt)
    cols = st.columns(5)
    if cols[0].button("Save", type="primary", use_container_width=True, key=f"{key_prefix}_save"):
        temp_song["instrument_tag_validation"] = validate_english_only_tags(edited_lyrics)
        result = save_song_state(project_name, temp_song, workflow_mode=workflow_mode)
        if result.get("ok"):
            project["song"] = result["data"]["song"]
            st.session_state.lyrics_saved = True
            st.session_state.normalized_song_output = edited_lyrics
            _save_project()
            _log_beta_event("export", workflow="music", metadata={"format": "song_txt"})
            st.success("Lyrics saved")
            st.rerun()
        else:
            st.error(result.get("error", "Save failed"))
    if cols[1].button("Copy", use_container_width=True, key=f"{key_prefix}_copy"):
        st.session_state[f"{key_prefix}_show_copy"] = True
    cols[2].download_button("Lyrics TXT", data=lyrics_txt, file_name="lyrics_only.txt", mime="text/plain", use_container_width=True, key=f"{key_prefix}_lyrics_txt")
    cols[3].download_button("Suno TXT", data=suno_txt, file_name=suno_filename, mime="text/plain", use_container_width=True, key=f"{key_prefix}_suno_txt")
    if cols[4].button("Release Package", use_container_width=True, key=f"{key_prefix}_release"):
        if export_result.get("ok"):
            project["song"] = temp_song
            _save_project()
            st.success("Release package generated")
        else:
            st.error(export_result.get("error") or "Release package failed")
    if st.session_state.get(f"{key_prefix}_show_copy"):
        st.text_area("Copy Lyrics", value=lyrics_txt, height=220, key=f"{key_prefix}_copy_text")


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
    creator_mode = not st.session_state.get("developer_mode", False)
    if creator_mode:
        st.info(
            "Creator Mode: สร้าง hook, เขียนเนื้อเพลง, export ไป Suno, อัปโหลดเพลงที่ทำเสร็จ แล้วสร้าง cinematic hook clip ได้ในหน้านี้",
            icon="🎵",
        )

    if creative_direction and not creator_mode:
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

    use_structure_plan = st.session_state.get("use_structure_plan_for_lyrics", True)
    if not creator_mode:
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
        current_hook_for_title = (song.get("selected_hook") or {}).get("hook_text") if isinstance(song.get("selected_hook"), dict) else song.get("selected_hook_text", "")
        title_candidates = generate_song_title_candidates(idea=idea, hook_text=str(current_hook_for_title or ""), lyrics=str(song.get("normalized_song_output") or song.get("complete_lyrics") or ""))
        if title_candidates and is_placeholder_song_title(title):
            suggested_title = st.session_state.get("suggested_song_title") or title_candidates[0]["title"]
            st.caption(f"Suggested Song Title: {suggested_title}")
            tc1, tc2 = st.columns(2)
            if tc1.button("Accept Title", key="song_accept_suggested_title", use_container_width=True):
                project["title"] = suggested_title
                project.setdefault("song", {})["title"] = suggested_title
                project["song"]["generated_title"] = suggested_title
                st.session_state.suggested_song_title = suggested_title
                _save_project()
                st.rerun()
            if tc2.button("Regenerate Title", key="song_regenerate_suggested_title", use_container_width=True):
                index = int(st.session_state.get("suggested_song_title_index", 0)) + 1
                st.session_state.suggested_song_title_index = index
                st.session_state.suggested_song_title = title_candidates[index % len(title_candidates)]["title"]
                st.rerun()
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
        with st.expander("Preset Summary", expanded=not creator_mode):
            st.write(f"Genre: {preset.get('genre', '')}")
            st.write(f"Vocal: {preset.get('vocal_style', '')}")
            st.write(", ".join(preset.get("main_instruments", []) or []))
            if not creator_mode:
                st.json(preset.get("suno_advanced_settings", {}), expanded=False)
        if not creator_mode:
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
    st.markdown("**Hooks**")
    hook_actions = st.columns(3)
    generate_hooks_clicked = hook_actions[0].button("Generate Viral Hooks", type="primary", key="song_generate_hooks", help="สร้างตัวเลือกฮุกหลายแบบให้เลือกก่อนเขียนเนื้อเพลงเต็ม")
    regenerate_hooks_clicked = hook_actions[1].button("Try New Hooks", key="song_regenerate_hooks", help="ลองฮุกชุดใหม่ถ้ายังไม่ถูกใจ")
    hook_cache_dir = ROOT / "outputs" / "cache" / "text"
    if hook_cache_dir.exists() and hook_actions[2].button("Reset Hooks", key="song_clear_hook_cache", help="เริ่มชุดฮุกใหม่ให้สะอาดขึ้น"):
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
        st.info("ยังไม่มี hook. กด Generate Viral Hooks ก่อน หรือ Generate Full Lyrics จะสร้างและเลือก hook ให้อัตโนมัติ")

    st.divider()
    st.markdown("**Lyrics**")
    if st.button("Generate Full Lyrics", key="song_generate_full_lyrics", help="สร้างเนื้อเพลงเต็มจากไอเดียและฮุกที่เลือก"):
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
        resolved_title = title.strip()
        generated_title_used = False
        if is_placeholder_song_title(resolved_title):
            resolved_title = generate_song_title_from_idea(idea=idea, hook_text=str(hook.get("hook_text", "")))
            generated_title_used = True
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
        raw_lyrics = str(song_result.get("normalized_song_output") or song_result.get("complete_lyrics") or song_result.get("original_song_output") or "")
        active_artist_preset = preset if use_preset else get_artist_preset("vela_moon")
        completeness = ensure_full_song_structure(
            raw_lyrics,
            hook_text=str(hook.get("hook_text", "")),
            idea=idea,
            artist_preset=active_artist_preset,
            genre=genre,
            mood=mood,
            vocal=vocal,
            style_preset=selected_music_preset,
        )
        if not completeness["before"].get("ok") and active_api_key:
            strict_idea = (
                f"{idea_with_hook}\n\n"
                "CRITICAL FULL SONG REQUIREMENTS:\n"
                "- Write a complete commercial-length Thai song, not a short demo.\n"
                "- Must include [Intro], [Verse 1], [Pre-Chorus], [Chorus], [Verse 2], [Pre-Chorus], [Chorus], [Bridge], [Final Chorus], [Outro].\n"
                "- Minimum 24 lyric lines, minimum 120 total words, chorus minimum 4 lines.\n"
                "- No empty sections and no one-line chorus.\n"
            )
            retry_result = _safe(
                "Regenerate complete song",
                generate_song_with_gemini,
                active_api_key,
                active_model,
                strict_idea,
                genre,
                mood,
                vocal,
                viral,
                artist_preset=preset if use_preset else get_artist_preset("vela_moon"),
                music_style_override=final_style_prompt,
                force_english_instrument_tags=force_tags,
                provider=active_provider,
            )
            retry_lyrics = str(retry_result.get("normalized_song_output") or retry_result.get("complete_lyrics") or retry_result.get("original_song_output") or "")
            retry_completeness = ensure_full_song_structure(
                retry_lyrics,
                hook_text=str(hook.get("hook_text", "")),
                idea=idea,
                artist_preset=active_artist_preset,
                genre=genre,
                mood=mood,
                vocal=vocal,
                style_preset=selected_music_preset,
            )
            if retry_completeness["before"].get("score", 0) > completeness["before"].get("score", 0):
                song_result = retry_result
                completeness = retry_completeness
        if completeness.get("expanded"):
            song_result["local_expansion_applied"] = True
        song_result["complete_lyrics"] = completeness["lyrics"]
        song_result["normalized_song_output"] = completeness["lyrics"]
        song_result["song_completeness"] = completeness["after"]
        song_result["song_completeness_before_expansion"] = completeness["before"]
        song_result["music_direction"] = completeness.get("music_direction") or build_music_direction(
            genre=genre,
            mood=mood,
            vocal=vocal,
            artist_preset=active_artist_preset,
            style_preset=selected_music_preset,
        )
        song_result["music_style_prompt"] = song_result["music_direction"].get("master_music_style_prompt") or final_style_prompt
        song_result["bpm"] = song_result["music_direction"].get("bpm")
        song_result["hook_candidates"] = candidates
        song_result["candidate_hooks"] = candidates
        song_result["selected_hook"] = hook
        song_result["selected_hook_text"] = hook.get("hook_text", "")
        song_result["idea"] = idea
        song_result["title"] = resolved_title
        song_result["song_title"] = resolved_title
        song_result["generated_title"] = resolved_title
        song_result["title_generated_from_idea"] = generated_title_used
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
        project["title"] = resolved_title
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

    st.divider()
    with st.container(border=True):
        st.markdown("**Or Paste Existing Lyrics**")
        st.caption("มีเนื้อเพลงอยู่แล้ว วางตรงนี้เพื่อให้ VelaFlow เลือก hook และสร้าง short clip ได้ทันที")
        pasted_lyrics = st.text_area(
            "Paste lyrics",
            value="",
            height=180,
            key="song_paste_existing_lyrics",
            help="วางเนื้อเพลงไทย หรือเนื้อเพลงพร้อม section tags เช่น [Chorus]",
        )
        if st.button("Use Pasted Lyrics for Hook Clip", use_container_width=True, disabled=not bool(pasted_lyrics.strip()), key="song_use_pasted_lyrics"):
            fixed = normalize_lyrics_tags(pasted_lyrics, preset)
            pasted_music_direction = build_music_direction(
                genre=genre,
                mood=mood,
                vocal=vocal,
                artist_preset=preset,
                style_preset=selected_music_preset,
            )
            fixed = apply_music_direction_tags(fixed, pasted_music_direction)
            pasted_title = title.strip()
            if is_placeholder_song_title(pasted_title):
                pasted_title = generate_song_title_from_idea(idea=idea, hook_text=selected_hook_text, lyrics=fixed)
            pasted_song = normalize_song_metadata(
                {
                    "title": pasted_title,
                    "song_title": pasted_title,
                    "generated_title": pasted_title,
                    "idea": idea,
                    "artist": artist,
                    "complete_lyrics": fixed,
                    "normalized_song_output": fixed,
                    "artist_preset": preset.get("artist_id", "vela_moon"),
                    "artist_preset_data": preset,
                    "music_preset": selected_music_preset_name,
                    "music_preset_data": selected_music_preset,
                    "vocal_direction": selected_vocal_direction_name,
                    "vocal_direction_data": selected_vocal_direction,
                    "music_direction": pasted_music_direction,
                    "music_style_prompt": pasted_music_direction.get("master_music_style_prompt"),
                    "instrument_tags_language": "English only",
                },
                preset,
            )
            best = detect_best_song_hook(pasted_song)
            pasted_song["selected_hook"] = {
                "hook_text": best.get("hook_text", ""),
                "emotional_score": best.get("emotional_score", 0),
                "catchy_score": best.get("catchy_score", 0),
                "tiktok_potential": best.get("tiktok_potential", 0),
                "suggested_usage": best.get("section", "chorus"),
            }
            pasted_song["selected_hook_text"] = best.get("hook_text", "")
            project["title"] = pasted_title
            project["artist"] = artist
            project["song"] = normalize_song_metadata(pasted_song, preset)
            st.session_state.generated_song = project["song"]
            st.session_state.normalized_song_output = project["song"].get("normalized_song_output", "")
            st.session_state.selected_hook = project["song"].get("selected_hook", {})
            _save_project()
            st.success("Lyrics loaded. Best hook selected for short clip.")
            st.rerun()

    song = normalize_song_metadata(project.get("song", {}) or {}, get_artist_preset((project.get("song", {}) or {}).get("artist_preset") or load_default_artist_id()))
    if song.get("hook_candidates") or song.get("normalized_song_output") or song.get("complete_lyrics"):
        project["song"] = song
        lyrics_for_editor = song.get("normalized_song_output") or song.get("complete_lyrics", "")
        if lyrics_for_editor:
            st.divider()
            st.markdown("## Edit Lyrics")
            edited_creator_lyrics = st.text_area(
                "Lyrics Editor",
                value=lyrics_for_editor,
                height=420,
                key="song_creator_lyrics_editor",
                help="แก้เนื้อเพลงได้ต่อเนื่อง แล้วใช้ปุ่มด้านล่างเพื่อบันทึกหรือส่งออก",
            )
            song["complete_lyrics"] = edited_creator_lyrics
            song["normalized_song_output"] = edited_creator_lyrics
            project["song"] = song
            completeness_view = analyze_song_completeness(edited_creator_lyrics)
            st.markdown("### Song Completeness Score")
            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("Score", completeness_view.get("score", 0))
            sc2.metric("Lyric Lines", completeness_view.get("line_count", 0))
            sc3.metric("Chorus Quality", completeness_view.get("chorus_quality", 0))
            sc4.metric("Est. Duration", f"{completeness_view.get('estimated_duration_seconds', 0)}s")
            if not completeness_view.get("ok"):
                st.warning("Song structure is still short. Full generation should include verses, pre-chorus, chorus, bridge, final chorus, and outro.")
            music_direction_view = song.get("music_direction") or build_music_direction(
                genre=str(song.get("genre") or ""),
                mood=str(song.get("mood") or ""),
                vocal=str(song.get("vocal") or song.get("vocal_direction") or ""),
                artist_preset=get_artist_preset(song.get("artist_preset", "vela_moon")),
                style_preset=song.get("music_preset_data") if isinstance(song.get("music_preset_data"), dict) else {},
            )
            song["music_direction"] = music_direction_view
            st.markdown("### Music Direction Preview")
            md1, md2, md3 = st.columns(3)
            md1.metric("BPM", music_direction_view.get("bpm", "-"))
            md2.metric("Genre Fusion", str(music_direction_view.get("genre_fusion", "-"))[:28])
            md3.metric("Vocal Tone", str(music_direction_view.get("vocal_tone", "-"))[:28])
            st.caption(f"Instrument Palette: {', '.join(music_direction_view.get('instrument_palette', []))}")
            st.caption(f"Energy Curve: {music_direction_view.get('mood_progression', '')}")
            with st.expander("Arrangement Map", expanded=False):
                for row in music_direction_view.get("arrangement_map", []):
                    st.markdown(f"**{row.get('section', '')}** {row.get('arrangement_tag', '')}")
            _render_creator_lyrics_action_bar(project, song, edited_creator_lyrics, key_prefix="song_creator_action_bar")
        st.divider()
        best_hook = detect_best_song_hook(song)
        st.markdown("## 🎯 Best Hook Detected")
        with st.container(border=True):
            st.markdown(f"### {best_hook.get('hook_text', '')}")
            h1, h2, h3, h4 = st.columns(4)
            h1.metric("Hook Score", best_hook.get("hook_score") or best_hook.get("tiktok_potential", 0))
            h2.metric("Emotional", best_hook.get("emotional_score", 0))
            h3.metric("TikTok", best_hook.get("tiktok_potential", 0))
            h4.metric("Replay", best_hook.get("replay_value", 0))
            st.caption(f"Estimated clip length: 15s | Section: {best_hook.get('section', '-')}")
            if best_hook.get("reason"):
                st.caption(best_hook.get("reason", ""))

        st.markdown("## 🎵 Upload Song Audio")
        short_clip = song.get("short_clip") or {}
        real_output = short_clip.get("real_output") or {}
        short_clip = song.setdefault("short_clip", short_clip)
        with st.container(border=True):
            st.caption("อัปโหลดเพลงเต็ม แล้วเลือกช่วง hook สำหรับ Music Video V2 ต้องมีไฟล์เสียงจริงก่อนสร้างคลิป")
            song["short_clip"] = _render_hook_audio_controls(project.get("title") or song.get("title") or title, short_clip, "song_short_clip", "song")
            project["song"] = song
            _save_project()

        video_settings = {
            "provider": "gemini_veo",
            "gemini_api_key": _user_api_key("gemini"),
            "shot_count": 6,
        }
        song_audio_path = str(((song.get("short_clip") or {}).get("song_audio") or {}).get("path") or "")
        st.markdown("### Quick Start")
        with st.container(border=True):
            st.markdown(
                "1. Generate lyrics  \n"
                "2. Upload finished song  \n"
                "3. Detect full hook  \n"
                "4. Generate creator package  \n"
                "5. Copy prompts into Flow / Veo / Kling  \n"
                "6. Download final AI clips externally"
            )
        with st.expander("Example Creator Workflows", expanded=False):
            st.table(
                [
                    {"Workflow": "Sad emotional TikTok", "Export Mode": "Sad Emotional", "Prompt Style": "Cinematic", "Recommended Tool": "Kling", "Hook Duration": "20-24s"},
                    {"Workflow": "Viral heartbreak clip", "Export Mode": "TikTok Fast Hook", "Prompt Style": "Viral", "Recommended Tool": "Flow", "Hook Duration": "15-20s"},
                    {"Workflow": "Spotify Canvas", "Export Mode": "Spotify Canvas", "Prompt Style": "Safe", "Recommended Tool": "Runway", "Hook Duration": "15s loop"},
                    {"Workflow": "Cinematic MV teaser", "Export Mode": "Cinematic MV", "Prompt Style": "Cinematic", "Recommended Tool": "Veo or Kling", "Hook Duration": "24-30s"},
                    {"Workflow": "Dark storytelling short", "Export Mode": "Dark Storytelling", "Prompt Style": "Cinematic", "Recommended Tool": "Kling", "Hook Duration": "20-30s"},
                ]
            )
        full_hook_preview = extract_full_hook_section(
            str(song.get("complete_lyrics") or song.get("normalized_song_output") or ""),
            fallback_hook=str(best_hook.get("section_text") or best_hook.get("hook_text") or ""),
        )
        detection_preview = (song.get("short_clip") or {}).get("hook_detection") or {}
        recommendations = _creator_package_recommendations(full_hook_preview, detection_preview, str(song.get("mood") or mood or ""))
        st.markdown("### Hook Preview")
        with st.container(border=True):
            hp1, hp2, hp3, hp4 = st.columns(4)
            hp1.metric("Hook Start", f"{float((song.get('short_clip') or {}).get('hook_start_time', detection_preview.get('hook_start_time', 15.0))):.1f}s")
            hp2.metric("Hook End", f"{float((song.get('short_clip') or {}).get('hook_end_time', detection_preview.get('hook_end_time', 30.0))):.1f}s")
            hook_duration_preview = float((song.get("short_clip") or {}).get("hook_end_time", detection_preview.get("hook_end_time", 30.0))) - float((song.get("short_clip") or {}).get("hook_start_time", detection_preview.get("hook_start_time", 15.0)))
            hp3.metric("Hook Duration", f"{max(0.0, hook_duration_preview):.1f}s")
            hp4.metric("Confidence Score", f"{int(detection_preview.get('confidence_score', detection_preview.get('confidence', 0)) or 0)}%")
            if detection_preview:
                st.caption(f"Detection Reason: {detection_preview.get('detection_reason') or detection_preview.get('reason') or '-'}")
                st.caption(f"Energy Summary: {detection_preview.get('energy_profile_summary') or '-'}")
                st.caption(f"Suggested Use: {detection_preview.get('suggested_use') or '-'}")
            st.text_area(
                "Full Hook Lyrics Preview",
                value=full_hook_preview,
                height=130,
                disabled=True,
                key="song_full_hook_lyrics_preview",
            )
        st.markdown("### Recommended Setup")
        with st.container(border=True):
            rec1, rec2, rec3, rec4 = st.columns(4)
            rec1.metric("Export Mode", recommendations["export_mode"])
            rec2.metric("Prompt Style", recommendations["prompt_style"])
            rec3.metric("Best Tool", recommendations["ai_tool"])
            rec4.metric("Suggested Hook", f"{recommendations['hook_duration']}s")
        st.markdown("### Full Hook Creator Package")
        st.caption("One package for Flow, Veo, Runway, Kling, Pika, CapCut, captions, subtitles, and scene planning.")
        mode_col, style_col = st.columns(2)
        creator_export_mode = mode_col.selectbox(
            "Creator Export Mode",
            CREATOR_EXPORT_MODES,
            index=CREATOR_EXPORT_MODES.index(recommendations["export_mode"]) if recommendations["export_mode"] in CREATOR_EXPORT_MODES else 0,
            key="song_creator_export_mode",
        )
        prompt_style = style_col.selectbox(
            "Prompt Style",
            PROMPT_STYLES,
            index=PROMPT_STYLES.index(recommendations["prompt_style"]) if recommendations["prompt_style"] in PROMPT_STYLES else 1,
            key="song_creator_prompt_style",
        )
        if st.button("Generate Full Creator Package", type="primary", use_container_width=True, key="song_generate_creator_hook_package", disabled=not bool(song_audio_path)):
            package_result = generate_full_hook_creator_package(
                project_name=project.get("title") or song.get("title") or title,
                uploaded_mp3_path=song_audio_path,
                lyrics_text=str(song.get("complete_lyrics") or song.get("normalized_song_output") or ""),
                fallback_hook=str(best_hook.get("section_text") or best_hook.get("hook_text") or ""),
                song_title=str(song.get("title") or title or ""),
                artist_name=str(song.get("artist_name") or artist or ""),
                mood=str(song.get("mood") or mood or ""),
                export_mode=creator_export_mode,
                prompt_style=prompt_style,
                hook_start_time=float((song.get("short_clip") or {}).get("hook_start_time", 15.0)),
                hook_end_time=float((song.get("short_clip") or {}).get("hook_end_time", 30.0)),
                ffmpeg_path=settings.ffmpeg_path,
            )
            song.setdefault("short_clip", {})["creator_package"] = package_result.get("data", {})
            song["short_clip"]["creator_package_ok"] = bool(package_result.get("ok"))
            song["short_clip"]["creator_package_error"] = package_result.get("error", "")
            project["song"] = song
            _save_project()
            if package_result.get("ok"):
                st.success("Creator Package Ready")
            else:
                st.error(package_result.get("error") or package_result.get("message") or "Creator package failed")
            st.rerun()
        creator_package = ((song.get("short_clip") or {}).get("creator_package") or {})
        if creator_package.get("manifest"):
            manifest_files = list((creator_package.get("manifest") or {}).get("generated_files", {}).keys())
            if manifest_files:
                st.markdown("#### Creator Package Ready")
                ready_cols = st.columns(3)
                ready_cols[0].success("Full Hook Audio")
                ready_cols[1].success("AI Video Prompts")
                ready_cols[2].success("Scene Breakdown")
                ready_cols = st.columns(3)
                ready_cols[0].success("Subtitles")
                ready_cols[1].success("Captions")
                ready_cols[2].success("Thumbnail Prompt")
                st.info("Recommended next step: use Flow or Kling for best cinematic vertical clips.")
                with st.expander("Included creator files", expanded=False):
                    st.caption(", ".join(manifest_files))
        package_dir_value = str(creator_package.get("package_dir") or "")
        package_dir = Path(package_dir_value) if package_dir_value else None
        prompt_files = [
            ("Flow Prompt", "video_prompt_flow.txt"),
            ("Veo Prompt", "video_prompt_veo.txt"),
            ("Runway Prompt", "video_prompt_runway.txt"),
            ("Kling Prompt", "video_prompt_kling.txt"),
            ("Image Prompt", "image_prompt.txt"),
            ("Thumbnail Prompt", "thumbnail_prompt.txt"),
        ]
        if package_dir and package_dir.is_dir():
            scene_breakdown_path = package_dir / "scene_breakdown.txt"
            if scene_breakdown_path.is_file():
                with st.expander("Scene Breakdown", expanded=False):
                    st.text_area(
                        "Cinematic Scene Plan",
                        value=scene_breakdown_path.read_text(encoding="utf-8-sig"),
                        height=180,
                        key="song_creator_scene_breakdown_preview",
                    )
            st.markdown("#### Copy Prompts")
            for idx, (label, filename) in enumerate(prompt_files):
                prompt_path = package_dir / filename
                if prompt_path.is_file():
                    prompt_text = prompt_path.read_text(encoding="utf-8-sig")
                    with st.expander(label, expanded=idx == 0):
                        st.text_area(label, value=prompt_text, height=150, key=f"song_creator_copy_prompt_{idx}_{filename}")
                        if st.button(f"Copy {label}", key=f"song_creator_copy_button_{idx}_{filename}", use_container_width=True):
                            st.info(f"{label} is ready above. Select the text box and copy it.")
        if creator_package.get("zip_path") and Path(str(creator_package.get("zip_path"))).is_file():
            zip_path = Path(str(creator_package.get("zip_path")))
            st.download_button(
                "Download Creator Package ZIP",
                data=zip_path.read_bytes(),
                file_name="velaflow_creator_package.zip",
                mime="application/zip",
                use_container_width=True,
                key="song_download_full_hook_creator_package",
            )
        st.markdown("### Clip Studio V2")
        st.caption("Mode: Real AI Video")
        st.caption("Provider: Gemini/Veo")
        st.caption("Status: submitting → polling → downloading → muxing → complete")
        st.caption("Generates 2-3 real Veo shots from the full hook range, then muxes hook_audio.mp3 and burns bottom-safe subtitles.")
        st.caption("Real AI Video only. If Veo/Gemini video is unavailable, VelaFlow stops instead of using image-motion fallback.")
        if st.button(
            "Generate Real AI Video Clip",
            type="primary",
            use_container_width=True,
            key="song_generate_music_video_v2",
            disabled=not bool(song_audio_path),
        ):
            project_name = project.get("title") or song.get("title") or title
            full_hook_lyrics = str(best_hook.get("section_text") or best_hook.get("hook_text") or song.get("complete_lyrics") or song.get("lyrics") or "")
            with st.spinner("Generating real AI video shots..."):
                v2_result = generate_clip_studio_v2(
                    project_name=project_name,
                    song=song,
                    uploaded_mp3_path=song_audio_path,
                    hook_start_time=float((song.get("short_clip") or {}).get("hook_start_time", 15.0)),
                    hook_end_time=float((song.get("short_clip") or {}).get("hook_end_time", 30.0)),
                    full_hook_lyrics=full_hook_lyrics,
                    mood_preset=str(song.get("mood") or mood or ""),
                    provider_settings={"gemini_api_key": _user_api_key("gemini")},
                )
            song.setdefault("short_clip", {})["music_video_v2"] = v2_result.get("data", {})
            song["short_clip"]["music_video_v2_ok"] = bool(v2_result.get("ok"))
            song["short_clip"]["music_video_v2_error"] = v2_result.get("error", "")
            project["song"] = song
            _save_project()
            if v2_result.get("ok"):
                st.success("Music Video V2 ready.")
            else:
                st.error("Real AI Video provider unavailable or failed. No fallback was used.")
            st.rerun()
        v2_data = ((song.get("short_clip") or {}).get("music_video_v2") or {})
        if v2_data.get("final_mp4") and Path(str(v2_data.get("final_mp4"))).is_file():
            st.video(str(v2_data["final_mp4"]))
            st.download_button("Download Music Video V2 MP4", data=Path(v2_data["final_mp4"]).read_bytes(), file_name="final_hook_clip.mp4", mime="video/mp4", use_container_width=True, key="song_v2_download_final_mp4")
        elif (song.get("short_clip") or {}).get("music_video_v2_error"):
            st.warning(f"Real AI Video provider failed: {(song.get('short_clip') or {}).get('music_video_v2_error')}")
        if v2_data.get("final_dir") and Path(str(v2_data.get("final_dir"))).is_dir():
            final_dir = Path(str(v2_data.get("final_dir")))
            package_files = [path for path in final_dir.iterdir() if path.is_file()]
            package_buffer = io.BytesIO()
            with zipfile.ZipFile(package_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
                for path in package_files:
                    archive.write(path, path.name)
            st.download_button(
                "Download TikTok Package",
                data=package_buffer.getvalue(),
                file_name="music_video_v2_tiktok_package.zip",
                mime="application/zip",
                use_container_width=True,
                key="song_v2_download_tiktok_package",
            )
        if not st.session_state.get("developer_mode"):
            return

        st.markdown("## Developer Legacy Hook Clip Path")
        if st.button("Test Live Veo Provider", use_container_width=True, key="song_test_live_veo_provider"):
            debug_dir = workflow_project_root("song") / safe_name(project.get("title") or song.get("title") or title or "clip_studio_v2") / "exports" / "debug"
            with st.spinner("Running live Veo provider proof test..."):
                live_test = run_live_veo_provider_test(debug_dir, settings={"gemini_api_key": _user_api_key("gemini")})
            if live_test.get("ok"):
                st.success("PROVIDER OK")
            else:
                st.error("PROVIDER FAILED")
            st.json(live_test)
        content_presets = list_presets()
        preset_labels = [str(item.get("label") or item.get("preset_id")) for item in content_presets]
        default_preset_index = next((idx for idx, item in enumerate(content_presets) if item.get("preset_id") == "emotional_story"), 0)
        selected_clip_preset_label = st.selectbox(
            "Content Preset",
            preset_labels,
            index=default_preset_index,
            key="song_short_content_preset",
            help="Developer-only legacy image-motion path.",
        )
        selected_clip_preset = content_presets[preset_labels.index(selected_clip_preset_label)] if content_presets else get_preset("emotional_story")
        st.caption(str(selected_clip_preset.get("description") or "Legacy developer path"))
        video_generation_mode = "image_motion_fallback"
        ffmpeg_info = ffmpeg_version(settings.ffmpeg_path)
        st.caption(f"FFmpeg: {ffmpeg_info.get('path') if ffmpeg_info.get('ok') else 'unavailable'}")
        image_provider, image_settings = _image_provider_controls("song_short_clip")
        hook_audio_path = str(((song.get("short_clip") or {}).get("hook_audio") or {}).get("path") or "")
        r1, r2, r3 = st.columns(3)
        if r1.button("Retry Scene Images", use_container_width=True, key="song_retry_scene_images"):
            st.session_state["song_short_force_cache_refresh"] = True
            st.session_state["song_short_variation"] = "retry_images"
            st.rerun()
        if r2.button("Retry Final Render", use_container_width=True, key="song_retry_final_render"):
            st.session_state["song_short_force_render"] = True
            st.session_state["song_short_variation"] = "retry_render"
            st.rerun()
        if r3.button("Generate Alternate Version", use_container_width=True, key="song_generate_alternate"):
            st.session_state["song_short_force_cache_refresh"] = True
            st.session_state["song_short_variation"] = "alternate"
            st.rerun()
        s1, s2, s3 = st.columns(3)
        if s1.button("Stronger Emotion", use_container_width=True, key="song_stronger_emotion"):
            st.session_state["song_short_variation"] = "stronger_emotion"
            st.session_state["song_short_force_cache_refresh"] = True
            st.rerun()
        if s2.button("More Cinematic", use_container_width=True, key="song_more_cinematic"):
            st.session_state["song_short_variation"] = "more_cinematic"
            st.session_state["song_short_force_cache_refresh"] = True
            st.rerun()
        if s3.button("Faster TikTok Pace", use_container_width=True, key="song_faster_tiktok"):
            st.session_state["song_short_variation"] = "faster_tiktok"
            st.session_state["song_short_force_cache_refresh"] = True
            st.rerun()
        active_variation = st.session_state.get("song_short_variation", "default")
        if active_variation != "default":
            st.caption(f"Next version: {active_variation.replace('_', ' ')}")
        if st.button(
            "Quick Generate TikTok Hook",
            type="primary",
            use_container_width=True,
            disabled=not bool(best_hook.get("hook_text")),
            key="song_generate_short_from_hook",
            help="ปุ่มเดียวสร้าง scene prompts, images/fallback, motion, subtitles, thumbnail, final MP4 และ TikTok package",
        ):
            project_name = project.get("title") or song.get("title") or title
            idea_payload = "\n".join(
                [
                    str(best_hook.get("clip_prompt", "")),
                    "",
                    f"Hook text: {best_hook.get('hook_text', '')}",
                    f"Song mood: {mood}",
                    f"Music preset: {song.get('music_preset', DEFAULT_MUSIC_PRESET)}",
                    f"Variation: {active_variation}",
                    "Create exactly 3 concise scenes for a 9:16 short-form hook clip.",
                ]
            )
            release_stale_render_jobs(project_name, "song")
            queue_result = start_creator_render_job(
                project_name,
                "song",
                stage="quick_generate_hook_clip",
                metadata={"preset_id": selected_clip_preset.get("preset_id"), "variation": active_variation},
            )
            if not queue_result.get("ok"):
                st.warning(friendly_error_message(queue_result.get("error") or queue_result.get("message")))
                st.stop()
            job_id = ((queue_result.get("data") or {}).get("job") or {}).get("job_id", "")
            result: dict[str, Any] = {"ok": False, "message": "", "data": {}, "error": ""}
            try:
                with st.spinner("Rendering scenes... combining clip... preparing TikTok package..."):
                    result = quick_generate_hook_clip(
                        project_name,
                        idea_payload,
                        source_workflow="music",
                        clip_mode="Fast Hook",
                        duration_seconds=15,
                        image_provider=image_provider,
                        image_settings=image_settings,
                        video_generation_mode=video_generation_mode,
                        video_settings=video_settings,
                        preset_id=str(selected_clip_preset.get("preset_id") or "emotional_story"),
                        voiceover_style="emotional storyteller",
                        voiceover_api_key=_user_api_key("openai"),
                        subtitle_preset="Thai Emotional MV" if str(selected_clip_preset.get("preset_id")) == "emotional_story" else "TikTok Meme",
                        hook_audio_path=hook_audio_path,
                        force_cache_refresh=bool(st.session_state.pop("song_short_force_cache_refresh", False)),
                        force_final_render=bool(st.session_state.pop("song_short_force_render", True)),
                        variation=str(active_variation or "default"),
                    )
            except Exception as exc:
                result = {"ok": False, "message": "Render failed", "data": {}, "error": str(exc)}
            finally:
                safe_message = "" if result.get("ok") else friendly_error_message(result.get("error") or result.get("message"))
                complete_creator_render_job(
                    project_name,
                    "song",
                    job_id,
                    status="completed" if result.get("ok") else "failed",
                    result={
                        "final_mp4": (result.get("data") or {}).get("final_mp4", ""),
                        "render_stage_path": (result.get("data") or {}).get("render_stage_path", ""),
                    },
                    error=str(result.get("error") or ""),
                    safe_error_message=safe_message,
                )
            st.session_state["song_short_variation"] = "default"
            if result.get("ok"):
                final_dir = str(((result.get("data") or {}).get("tiktok_package") or {}).get("final_dir") or "")
                if final_dir:
                    creator_assets = export_creator_final_assets(
                        project_name,
                        song,
                        final_dir,
                        workflow_mode=st.session_state.get("workflow_mode", "Full Pipeline"),
                    )
                    if creator_assets.get("ok"):
                        result.setdefault("data", {}).setdefault("tiktok_package", {})["creator_assets"] = creator_assets.get("data", {})
                    else:
                        st.warning("Clip created, but creator export assets could not be refreshed.")
            song["short_clip"] = {
                "selected_hook": best_hook,
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "quick_generate": result.get("data", {}),
                "hook_clip_package": (result.get("data", {}) or {}).get("package", {}),
                "real_output": (result.get("data", {}) or {}).get("render", {}),
                "final_mp4": (result.get("data", {}) or {}).get("final_mp4", ""),
                "subtitles": ((result.get("data", {}) or {}).get("render", {}) or {}).get("subtitles", ""),
                "hook_audio": (song.get("short_clip") or {}).get("hook_audio", {}),
                "ok": bool(result.get("ok")),
                "error": result.get("error", ""),
                "safe_error_message": friendly_error_message(result.get("error") or result.get("message")) if not result.get("ok") else "",
            }
            project.setdefault("hook_clip_studio", {})["hook_clip"] = song["short_clip"].get("hook_clip_package", {})
            project["hook_clip_studio"]["source"] = "Music"
            project["hook_clip_studio"]["quick_generate"] = result.get("data", {})
            project["hook_clip_studio"]["real_output"] = song["short_clip"].get("real_output", {})
            project["hook_clip_studio"]["creator_render_status"] = "completed" if result.get("ok") else "failed"
            project["song"] = song
            _save_project()
            _log_beta_event("generate", workflow="music", preset_bundle="Song-to-Short Hook Clip", metadata={"page": "Song Studio"})
            if result.get("ok"):
                st.success("Hook short clip generated. Download final_hook_clip.mp4 below.")
            else:
                recovery = build_recovery_plan(project_name, "song", last_error=result.get("error") or result.get("message"))
                st.warning((recovery.get("data") or {}).get("safe_error_message") or "Clip package generated, but MP4 render needs attention.")
            st.rerun()

        st.markdown("## ✅ Preview / Download")
        if st.session_state.get("developer_mode"):
            _render_project_health_card(project.get("title") or song.get("title") or title, "song", "song_short_project_health")
        quick_data = short_clip.get("quick_generate") or {}
        if real_output:
            _render_final_downloads("song_short_clip", real_output)
            package_data = (short_clip.get("quick_generate") or {}).get("tiktok_package") or {}
            _render_tiktok_package_downloads("song_short_clip", package_data)
        elif short_clip.get("final_mp4") and Path(str(short_clip.get("final_mp4"))).is_file():
            _render_final_downloads("song_short_clip", {"final_mp4": short_clip.get("final_mp4"), "subtitles": short_clip.get("subtitles"), "status": "completed"})
        else:
            st.info("Quick Generate TikTok Hook แล้ว preview และ download จะขึ้นตรงนี้ทันที")
        video_generation = quick_data.get("video_generation") or {}
        if video_generation:
            manifest = video_generation.get("manifest") or {}
            provider_used = manifest.get("provider_used") or manifest.get("provider") or "-"
            status = "complete" if manifest.get("real_ai_video_used") else "fallback" if manifest.get("fallback_used") else "ready"
            st.caption(f"AI Video provider: {provider_used} · status: {status}")
            if video_generation.get("fallback_used"):
                st.warning(f"AI Video provider failed: {video_generation.get('fallback_reason') or 'provider unavailable'}. Used fallback.")
            elif video_generation.get("manifest_path"):
                st.success("AI Video shot manifest ready")
        thumbnail_path = Path(str((quick_data.get("thumbnail") or {}).get("path") or quick_data.get("thumbnail_path") or ""))
        if thumbnail_path.is_file():
            st.markdown("**Cover Frame Preview**")
            st.image(str(thumbnail_path), caption="Raw validated cinematic frame, no overlay", use_container_width=True)
        viral_metrics = quick_data.get("viral_metrics") or ((quick_data.get("package") or {}).get("viral_metrics") or {})
        thumbnail_quality = ((quick_data.get("thumbnail") or {}).get("score") or ((quick_data.get("tiktok_package") or {}).get("thumbnail_quality") or 0))
        timing_profile = (quick_data.get("beat_timing") or {}).get("timing_profile") or (quick_data.get("viral_timing_plan") or {}).get("timing_profile", "")
        if viral_metrics:
            st.markdown("**TikTok Optimization**")
            vm1, vm2, vm3, vm4 = st.columns(4)
            vm1.metric("Hook score", viral_metrics.get("hook_score", 0))
            vm2.metric("Emotional intensity", viral_metrics.get("emotional_impact", 0))
            vm3.metric("Viral pacing", viral_metrics.get("viral_pacing", 0))
            vm4.metric("Cover frame", thumbnail_quality or "-")
            if timing_profile:
                st.caption(f"Pacing profile: {timing_profile}")
        versions = list_clip_versions(project.get("title") or song.get("title") or title, "song")
        if versions:
            with st.expander("Compare Versions", expanded=False):
                rows = [
                    {
                        "version": item.get("version_id"),
                        "variation": item.get("variation", "default"),
                        "hook_score": ((item.get("viral_metrics") or {}).get("hook_score") or "-"),
                        "created_at": item.get("created_at", ""),
                    }
                    for item in versions[-5:]
                ]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                latest = Path(str(versions[-1].get("final_mp4") or ""))
                if latest.is_file():
                    st.download_button("Download Latest Version MP4", data=latest.read_bytes(), file_name=latest.name, mime="video/mp4", use_container_width=True, key="song_download_latest_version")
        image_results = quick_data.get("image_results") or []
        if image_results:
            st.markdown("**Generated Scene Images**")
            for index, item in enumerate(image_results):
                path = Path(str(item.get("path") or ""))
                scene_label = str(item.get("scene_id") or path.stem or f"scene_{index + 1:02d}")
                st.caption(f"{index + 1}. {scene_label} · fullscreen vertical scene")
                if path.is_file():
                    st.image(str(path), caption=scene_label, use_container_width=True)
                provider_label = str(item.get("provider") or item.get("provider_used") or "-")
                fallback_used = bool(item.get("fallback_used"))
                if fallback_used:
                    st.warning(f"Fallback image: {item.get('fallback_reason') or item.get('error_type') or 'provider unavailable'}")
                else:
                    st.caption(f"Provider: {provider_label}")
                if index < len(image_results) - 1:
                    st.divider()
                if st.session_state.get("developer_mode") and item.get("safe_error_message"):
                    st.caption(str(item.get("safe_error_message")))
        if real_output:
            if st.button("Refresh TikTok Package", key="song_short_export_tiktok", use_container_width=True):
                package_result = export_tiktok_package(
                    project.get("title") or song.get("title") or title,
                    short_clip.get("hook_clip_package") or {},
                    real_output,
                )
                song.setdefault("short_clip", {})["tiktok_package"] = package_result.get("data", {})
                _save_project()
                st.success("TikTok package exported") if package_result.get("ok") else st.error(package_result.get("error") or package_result.get("message"))
                st.rerun()
        if st.session_state.get("developer_mode") and quick_data.get("manifest_path"):
            st.caption(f"Clip manifest: {quick_data.get('manifest_path')}")

        t1, t3, t4, t5, t6 = st.tabs(["Hook Details", "Suno Style", "Lyrics", "Save / Continue", "Draft History"])
        with t1:
            st.write("Title:", song.get("title", ""))
            st.write("Selected Hook:", song.get("selected_hook_text", ""))
            with st.expander("Hook candidates", expanded=False):
                st.dataframe(pd.DataFrame(song.get("hook_candidates", [])), use_container_width=True)
        with t3:
            st.write("Music Preset:", song.get("music_preset", DEFAULT_MUSIC_PRESET))
            st.write("Vocal Direction:", song.get("vocal_direction", DEFAULT_VOCAL_DIRECTION))
            st.code(song.get("music_style_prompt", ""), language="text")
            st.json(song.get("advanced_settings", {}), expanded=False)
            st.json({"artist_preset": song.get("artist_preset", "vela_moon"), "instrument_tags_language": song.get("instrument_tags_language", "English only")}, expanded=False)
        with t4:
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
        with t5:
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
            if st.session_state.get("developer_mode"):
                with st.expander("Advanced saved paths", expanded=False):
                    st.json({
                        "song_json": str(saved_folder / "song.json"),
                        "lyrics_txt": str(saved_folder / "lyrics.txt"),
                        "suno_full_package": str(saved_folder / "exports"),
                        "lyrics_only": str(saved_folder / "exports" / "lyrics_only.txt"),
                        "ready_for_hook_short_clip": bool(song.get("normalized_song_output") or song.get("complete_lyrics")),
                    }, expanded=False)
            _render_suno_downloads(project.get("title", title), song)
        with t6:
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
        if st.session_state.get("developer_mode"):
            with st.expander("TikTok Cut Recommendation", expanded=False):
                st.json(song.get("tiktok_clip_cut_recommendation", []), expanded=False)


_ensure_state()
_restore_local_api_state()
_sync_provider_runtime_state()
if not st.session_state.get("beta_runtime_prepared"):
    cleanup_old_temp_exports(ttl_hours=48)
    st.session_state.beta_runtime_prepared = True
project = _project()

st.title(f"🎬 {APP_TITLE}")
st.caption(f"{PRODUCT_TAGLINE} by {BRAND_NAME} | {build_label()}")
if str(getattr(settings, "velaflow_mode", "LOCAL")).upper() == "CLOUD":
    st.caption("☁️ Internal Cloud Mode")

PAGE_MODULES = {
    "Creator Dashboard": "creative_pack",
    "Idea": "creative_pack",
    "Generate Song": "creative_pack",
    "Generate Visual Pack": "creative_pack",
    "Export Release Pack": "creative_pack",
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
    st.header("VelaFlow V1")
    beta_profile = load_beta_access()
    st.info(
        f"VelaFlow Closed Beta\n\nFounding Creator Build\n\nVersion {APP_VERSION} · Build {BUILD_VERSION}\n\nStatus: {str(beta_profile.get('beta_status', 'active')).title()}",
        icon="✨",
    )
    with st.expander("Founding Member", expanded=False):
        creator_name = st.text_input("Creator Name", value=str(beta_profile.get("creator_name") or "Founding Creator"), key="beta_creator_name")
        creator_id = st.text_input("Creator ID", value=str(beta_profile.get("creator_id") or ""), key="beta_creator_id")
        st.caption(f"Joined: {beta_profile.get('joined_at', '-')}")
        st.caption(f"Total renders: {beta_profile.get('total_renders', 0)}")
        st.caption(f"Last active: {beta_profile.get('last_active', '-')}")
        if st.button("Save Founding Member", use_container_width=True, key="save_founding_member"):
            save_beta_access({"creator_name": creator_name, "creator_id": creator_id or safe_name(creator_name)})
            st.success("Founding member profile saved")
            st.rerun()
    if st.session_state.pop("force_developer_mode", False):
        st.session_state.developer_mode = True
    developer_mode = st.checkbox(
        "Advanced / Developer Mode",
        value=bool(st.session_state.get("developer_mode", False)),
        key="developer_mode",
        help="เปิดเฉพาะเมื่อต้องการ workflow เก่าหรือเครื่องมือ developer",
    )
    workflow_options = ["Song Studio Only"] if not developer_mode else ["Song Studio Only", "Full Pipeline", "Seller Studio (Beta)", "Podcast Studio (Beta)", "Viral Clips Studio (Beta)", "Hook Clip Studio (Beta)"]
    current_mode_for_select = st.session_state.get("workflow_mode", "Full Pipeline")
    if current_mode_for_select not in workflow_options:
        current_mode_for_select = "Song Studio Only"
    selected_mode = st.selectbox(
        "Workflow Mode",
        workflow_options,
        index=workflow_options.index(current_mode_for_select),
        key="workflow_mode_selector",
        format_func=lambda value: "AI Creative Pack Generator" if value == "Song Studio Only" else value,
        help="V1 = generate, organize, and export creative release packs. No rendering workflow is shown in normal mode.",
    )
    if selected_mode == "Song Studio Only":
        st.caption("AI Creative Pack Generator: idea → song → visual pack → release pack.")
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
    st.caption(f"VelaFlow Beta 0.1.0{cloud_label} · Review AI outputs before publishing")
    if developer_mode:
        st.caption("Developer workflows visible: Seller / Podcast / Viral / MV / Mock / Veo")
    if selected_mode != st.session_state.get("workflow_mode"):
        st.session_state.workflow_mode = selected_mode
        save_user_preferences({"workflow_mode": selected_mode})
        if not st.session_state.get("current_project") and _fix_display_text((st.session_state.project or {}).get("title", "")) in SONG_DEFAULT_TITLES:
            st.session_state.project = new_project(_workflow_default_name(selected_mode), DEFAULT_ARTIST, workflow_type_for_mode(selected_mode))
        if selected_mode == "Song Studio Only" and st.session_state.selected_page not in SONG_ONLY_ALLOWED_PAGES:
            st.session_state["pending_navigation"] = {"section": "CREATE", "page": "Creator Dashboard"}
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
    st.markdown("**Creator Navigation**")
    if not developer_mode:
        if st.button("Creator Dashboard", use_container_width=True, key="sidebar_nav_creator_dashboard"):
            go_to_page("CREATE", "Creator Dashboard")
        if st.button("Idea", use_container_width=True, key="sidebar_nav_idea"):
            go_to_page("CREATE", "Idea")
        if st.button("Generate Song", use_container_width=True, key="sidebar_nav_generate_song"):
            go_to_page("CREATE", "Generate Song")
        if st.button("Generate Visual Pack", use_container_width=True, key="sidebar_nav_generate_visual_pack"):
            go_to_page("CREATE", "Generate Visual Pack")
        if st.button("Export Release Pack", use_container_width=True, key="sidebar_nav_export_release_pack"):
            go_to_page("CREATE", "Export Release Pack")
    else:
        if st.button("Song Studio", use_container_width=True, key="sidebar_nav_song_studio"):
            go_to_page("SONG", "Song Studio")
        if st.button("Clip Studio", use_container_width=True, key="sidebar_nav_clip_studio"):
            go_to_page("PRODUCTION", "Hook Clip Studio")
        if st.button("Remaster Studio", use_container_width=True, key="sidebar_nav_remaster_studio"):
            go_to_page("PRODUCTION", "Remaster Studio")
        if st.button("🤖 VelaFlow Agent Studio", use_container_width=True, key="sidebar_nav_agent_studio"):
            go_to_page("START", "VelaFlow Agent Studio")
    group = st.selectbox("Section", list(MENU_GROUPS), key="selected_section")
    group_pages = MENU_GROUPS[group]
    if st.session_state.selected_page not in group_pages:
        st.session_state.selected_page = group_pages[0]
    page = st.radio("Menu", group_pages, label_visibility="collapsed", key="selected_page", format_func=page_label)
    if page == "VelaFlow Agent Studio":
        st.caption("Agent Studio Loaded")
    st.divider()
    st.write("Current Project")
    current_workflow_mode = st.session_state.get("workflow_mode", "Full Pipeline")
    current_session_label = session_label_for_mode(current_workflow_mode)
    all_managed_projects = list_managed_projects(workflow_mode=current_workflow_mode)
    managed_projects = filter_visible_projects(all_managed_projects, developer_mode=bool(developer_mode))
    prefs = load_user_preferences()
    favorite_paths = set(prefs.get("favorite_project_paths", []) or [])
    favorite_projects = [item for item in managed_projects if item.get("path") in favorite_paths]
    recent_projects = managed_projects[:5]
    if not developer_mode and not managed_projects and is_test_project_name(str((st.session_state.project or {}).get("title", ""))):
        clean_name = "เพลงใหม่ของฉัน"
        st.session_state.project = new_project(clean_name, DEFAULT_ARTIST, workflow_type_for_mode(current_workflow_mode))
        st.session_state.current_project = ""
        project = st.session_state.project
    selected_recent = current_session_label
    st.caption("Clean Project List")
    if favorite_projects:
        with st.expander("Favorite Projects", expanded=False):
            for item in favorite_projects[:5]:
                st.caption(f"{item.get('display_name')} · {item.get('last_modified', '')}")
    if recent_projects:
        with st.expander("Recent Projects", expanded=False):
            for item in recent_projects:
                st.caption(f"{item.get('display_name')} · {item.get('last_modified', '')}")
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
        if selected_recent != current_session_label:
            fav_label = "Unfavorite Project" if selected_recent in favorite_paths else "Favorite Project"
            if st.button(fav_label, use_container_width=True, key="sidebar_favorite_project_btn"):
                if selected_recent in favorite_paths:
                    favorite_paths.remove(selected_recent)
                else:
                    favorite_paths.add(selected_recent)
                save_user_preferences({"favorite_project_paths": sorted(favorite_paths)})
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
            if st.button("Duplicate Project", use_container_width=True, key="sidebar_duplicate_project_btn"):
                result = duplicate_project(st.session_state.project if st.session_state.get("current_project") == selected_recent else _safe("Load project", _load_managed_project, selected_recent), f"{selected_project_name} Copy")
                if result.get("ok"):
                    st.success("Project duplicated")
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
        runtime_keys = st.session_state.get("user_api_keys", {}) or {}
        st.success("Gemini configured") if runtime_keys.get("gemini") or settings.gemini_api_key else st.warning("Gemini not configured")
        st.success("OpenAI configured") if runtime_keys.get("openai") or settings.openai_api_key else st.warning("OpenAI not configured")
        st.success("xAI Grok configured") if runtime_keys.get("xai") or settings.xai_api_key else st.warning("xAI Grok not configured")
        resolved = _active_credential_status()
        st.caption(f"User Key: {'Provided' if resolved.get('user_key_present') else 'Missing'}")
        st.caption(f"VelaFlow Key: {'Configured' if resolved.get('velaflow_key_present') else 'Not configured'}")
        if not active_api_key:
            st.warning("Selected provider will use offline fallback")

def _render_agent_workspace_panel(active_workspace_name: str, state: dict[str, Any]) -> None:
    with st.container(border=True):
        st.markdown("### Project Workspace")
        try:
            active_summary = workspace_summary(active_workspace_name)
            st.caption("Workspace Summary")
            st.write(active_summary)
        except Exception as exc:
            st.caption("Workspace summary unavailable.")
            if st.session_state.get("developer_mode"):
                st.exception(exc)
        try:
            st.caption("Project Asset Summary")
            st.write(workspace_asset_summary(active_workspace_name))
        except Exception as exc:
            st.caption("Project asset summary unavailable.")
            if st.session_state.get("developer_mode"):
                st.exception(exc)
        try:
            active_workspace = load_workspace_project(active_workspace_name)
            with st.expander("Project Timeline", expanded=False):
                entries = active_workspace.get("workflow_history", [])[-5:]
                if entries:
                    for entry in entries:
                        st.write(f"- {entry.get('timestamp')} · {entry.get('event')}")
                else:
                    st.caption("No project history yet.")
        except Exception as exc:
            st.caption("Project timeline unavailable.")
            if st.session_state.get("developer_mode"):
                st.exception(exc)
        try:
            with st.expander("Asset Browser", expanded=False):
                assets = list_workspace_assets(active_workspace_name)
                if assets:
                    for asset in assets[-20:]:
                        st.write(f"- {asset.get('asset_type')} · {asset.get('filename')} · {', '.join(asset.get('tags', []))}")
                else:
                    st.caption("No assets yet. Generated prompts, covers, storyboards, and imported media will appear here.")
        except Exception as exc:
            st.caption("Asset Browser unavailable.")
            if st.session_state.get("developer_mode"):
                st.exception(exc)
        try:
            with st.expander("Media Timeline", expanded=False):
                pipeline_items = load_media_pipeline(active_workspace_name)
                if pipeline_items:
                    for item in pipeline_items:
                        st.write(f"- {item.get('pipeline_type')} · {item.get('title')} · {item.get('stage')}")
                else:
                    st.caption("No media pipeline items yet.")
        except Exception as exc:
            st.caption("Media Timeline unavailable.")
            if st.session_state.get("developer_mode"):
                st.exception(exc)
        try:
            with st.expander("Storyboard Viewer", expanded=False):
                demo_storyboard = create_storyboard(active_workspace_name, "Agent Studio Storyboard", "Cinematic continuity for the current creator idea")
                demo_storyboard = add_storyboard_scene(
                    demo_storyboard,
                    "Wide emotional opening shot",
                    "slow push-in",
                    "soft warm window light",
                    "melancholic",
                    4,
                    "single cinematic vertical frame, no text, emotional subject",
                )
                if st.button("Save Starter Storyboard", use_container_width=True, key="agent_workspace_save_storyboard"):
                    txt_storyboard = export_storyboard_txt(demo_storyboard, active_workspace_name)
                    json_storyboard = export_storyboard_json(demo_storyboard, active_workspace_name)
                    storyboard_asset = register_asset(txt_storyboard, "storyboards", active_workspace_name, "storyboard_manager", "MV Agent", ["storyboard"])
                    current_pipeline = load_media_pipeline(active_workspace_name)
                    current_pipeline.append({"pipeline_id": storyboard_asset["asset_id"], "pipeline_type": "storyboard", "asset_id": storyboard_asset["asset_id"], "title": "Starter Storyboard", "stage": "draft", "history": []})
                    save_media_pipeline(active_workspace_name, current_pipeline)
                    st.success(f"Storyboard saved: {Path(txt_storyboard).name}, {Path(json_storyboard).name}")
                st.text_area("Storyboard Preview", value="\n".join([scene["shot_description"] for scene in demo_storyboard.get("scenes", [])]), height=90, key="agent_workspace_storyboard_preview")
        except Exception as exc:
            st.caption("Storyboard Viewer unavailable.")
            if st.session_state.get("developer_mode"):
                st.exception(exc)
        try:
            with st.expander("Cover History", expanded=False):
                cover_prompt = st.text_area("Cover prompt", value=state.get("last_cover_prompt", ""), height=80, key="agent_workspace_cover_prompt")
                st.text_input("Asset Tags", value="cover, prompt", key="agent_workspace_cover_tags")
                if st.button("Save Cover Prompt Version", use_container_width=True, key="agent_workspace_save_cover"):
                    state["last_cover_prompt"] = cover_prompt
                    cover_asset = cover_prompt_history(active_workspace_name, cover_prompt, "MV Agent")
                    st.success(f"Cover prompt saved: {cover_asset.get('filename')}")
        except Exception as exc:
            st.caption("Cover History unavailable.")
            if st.session_state.get("developer_mode"):
                st.exception(exc)


def render_agent_studio(project: dict[str, Any] | None) -> None:
    if not isinstance(project, dict):
        project = new_project("Agent Studio Project", DEFAULT_ARTIST, workflow_type_for_mode(st.session_state.get("workflow_mode", "Song Studio Only")))
        st.session_state.project = project
    _page_header("VelaFlow Agent Studio", "Turn one raw idea into a complete creator package.", project)
    st.caption("Beginner-friendly creative assistant. No prompt engineering required.")
    state = project.setdefault("agent_studio", {})
    try:
        agent_memory = load_agent_memory()
    except Exception:
        agent_memory = {}
    with st.sidebar.expander("Project Sidebar", expanded=True):
        try:
            recent_projects = list_workspace_projects()
        except Exception:
            recent_projects = []
        project_names = [item.get("project_name", "") for item in recent_projects if item.get("project_name")]
        default_workspace_name = state.get("workspace_project") or (project_names[0] if project_names else "My_Creator_Project")
        workspace_project_name = st.text_input("Workspace Project", value=default_workspace_name, key="agent_workspace_project_name")
        if st.button("Create Project", use_container_width=True, key="agent_workspace_create"):
            created_workspace = create_workspace_project(workspace_project_name)
            state["workspace_project"] = created_workspace["project_name"]
            project["agent_studio"] = state
            _save_project()
            st.success("Project workspace created.")
            st.rerun()
        if project_names:
            selected_recent_project = st.selectbox("Recent Projects", project_names, index=project_names.index(default_workspace_name) if default_workspace_name in project_names else 0, key="agent_workspace_recent")
            if st.button("Continue Project", use_container_width=True, key="agent_workspace_continue"):
                loaded_workspace = load_workspace_project(selected_recent_project)
                state["workspace_project"] = loaded_workspace["project_name"]
                project["agent_studio"] = state
                _save_project()
                st.success("Project loaded.")
                st.rerun()
        active_workspace_name = state.get("workspace_project") or workspace_project_name
        export_workspace = st.button("Export ZIP", use_container_width=True, key="agent_workspace_export_zip")
        if export_workspace:
            try:
                zip_path = export_workspace_zip(active_workspace_name)
                st.download_button("Download Workspace ZIP", data=Path(zip_path).read_bytes(), file_name=Path(zip_path).name, mime="application/zip", use_container_width=True, key="agent_workspace_download_zip")
            except Exception as exc:
                st.caption("Workspace export unavailable.")
                if st.session_state.get("developer_mode"):
                    st.exception(exc)
        if st.button("Archive Project", use_container_width=True, key="agent_workspace_archive"):
            try:
                archive_workspace_project(active_workspace_name)
                st.success("Project archived.")
                st.rerun()
            except Exception as exc:
                st.caption("Project archive unavailable.")
                if st.session_state.get("developer_mode"):
                    st.exception(exc)
    _render_agent_workspace_panel(active_workspace_name, state)
    with st.container(border=True):
        user_idea = st.text_area("พิมพ์ไอเดียของคุณ", value=state.get("user_idea", ""), height=180, key="agent_studio_user_idea", help="ใส่ไอเดียเพลง สินค้า คลิป พอดแคสต์ หรือคอนเซ็ปต์สั้น ๆ")
        c1, c2, c3 = st.columns(3)
        project_type = c1.selectbox("Project type", AGENT_PROJECT_TYPES, index=AGENT_PROJECT_TYPES.index(state.get("project_type", AGENT_PROJECT_TYPES[0])) if state.get("project_type") in AGENT_PROJECT_TYPES else 0, key="agent_studio_project_type")
        language = c2.selectbox("Language", AGENT_LANGUAGES, index=AGENT_LANGUAGES.index(state.get("language", "Thai")) if state.get("language") in AGENT_LANGUAGES else 0, key="agent_studio_language")
        tone = c3.selectbox("Tone", AGENT_TONES, index=AGENT_TONES.index(state.get("tone", "Emotional")) if state.get("tone") in AGENT_TONES else 0, key="agent_studio_tone")
        c4, c5 = st.columns([2, 1])
        workflow_mode = c4.selectbox("Workflow mode", AGENT_WORKFLOW_MODES, index=AGENT_WORKFLOW_MODES.index(state.get("workflow_mode", "Quick Generate")) if state.get("workflow_mode") in AGENT_WORKFLOW_MODES else 0, key="agent_studio_workflow_mode")
        use_memory = c5.checkbox("Use Agent Memory", value=bool(state.get("use_memory", True)), key="agent_studio_use_memory")
        c6, c7 = st.columns([2, 1])
        ai_provider = c6.selectbox("AI Provider", AGENT_AI_PROVIDERS, index=AGENT_AI_PROVIDERS.index(state.get("ai_provider", "Auto")) if state.get("ai_provider") in AGENT_AI_PROVIDERS else 0, key="agent_studio_ai_provider")
        auto_workflow = c7.checkbox("Auto Workflow", value=bool(state.get("auto_workflow", workflow_mode == "Auto")), key="agent_studio_auto_workflow")
        multi_agent = st.checkbox("Multi-Agent Mode", value=bool(state.get("multi_agent", False)), key="agent_studio_multi_agent")
        with st.expander("Agent Memory", expanded=False):
            st.caption("VelaFlow remembers recent creative direction locally on this machine.")
            st.write(
                {
                    "recent_project_type": agent_memory.get("recent_project_type") or "-",
                    "recent_tone": agent_memory.get("recent_tone") or "-",
                    "recent_language": agent_memory.get("recent_language") or "-",
                    "recent_ideas": agent_memory.get("last_user_ideas", [])[-3:],
                    "recent_titles": agent_memory.get("last_generated_titles", [])[-3:],
                }
            )
            if st.button("Clear Agent Memory", use_container_width=True, key="agent_studio_clear_memory"):
                save_agent_memory({})
                st.success("Agent memory cleared.")
                st.rerun()
        generate_agent = st.button("Generate Agent Package", type="primary", use_container_width=True, disabled=not bool(user_idea.strip()), key="agent_studio_generate")
        if generate_agent:
            agent_provider_keys = {
                "gemini": _user_api_key("gemini") or getattr(settings, "gemini_api_key", ""),
                "openai": _user_api_key("openai") or getattr(settings, "openai_api_key", ""),
            }
            selected_provider_key = ""
            if ai_provider == "Gemini":
                selected_provider_key = agent_provider_keys.get("gemini", "")
            elif ai_provider == "OpenAI":
                selected_provider_key = agent_provider_keys.get("openai", "")
            with st.status("Agent is working...", expanded=True) as agent_status:
                st.write("analyzing idea")
                st.write("selecting workflow")
                st.write("generating package")
                result = run_agent_workflow(
                    user_idea,
                    workflow_mode,
                    use_memory=use_memory,
                    project_type=project_type,
                    language=language,
                    tone=tone,
                    provider_name=ai_provider,
                    provider_api_key=selected_provider_key,
                    provider_api_keys=agent_provider_keys,
                    auto_workflow=auto_workflow,
                    multi_agent=multi_agent,
                    project_name=state.get("workspace_project") or workspace_project_name,
                )
                st.write("exporting files")
                st.write("finalizing project")
                agent_status.update(label="Agent workflow complete", state="complete")
            package = result.get("output_package", {})
            state.update({
                "user_idea": user_idea,
                "project_type": project_type,
                "language": language,
                "tone": tone,
                "workflow_mode": workflow_mode,
                "use_memory": use_memory,
                "ai_provider": ai_provider,
                "auto_workflow": auto_workflow,
                "multi_agent": multi_agent,
                "workspace_project": (result.get("workspace_project") or {}).get("project_name") or state.get("workspace_project") or workspace_project_name,
                "package": package,
                "agent_result": result,
            })
            project["agent_studio"] = state
            _save_project()
            _log_beta_event("generate", workflow="agent_studio", metadata={"page": "VelaFlow Agent Studio", "project_type": project_type, "workflow_mode": workflow_mode, "ai_provider": ai_provider, "multi_agent": multi_agent})
            st.rerun()
    agent_package = state.get("package") or {}
    agent_result = state.get("agent_result") or {}
    if agent_package:
        st.success("Agent package ready.")
        if agent_result.get("workflow_summary"):
            st.info(agent_result["workflow_summary"])
        if agent_result.get("workspace_project"):
            st.caption(f"Workspace: {agent_result['workspace_project'].get('project_name')}")
        if agent_result.get("provider_warning"):
            st.warning(agent_result["provider_warning"])
        provider_diag = (agent_result.get("brain_analysis") or {}).get("provider") or {}
        if st.session_state.get("developer_mode") and provider_diag.get("provider") == "gemini" and provider_diag.get("last_error"):
            st.warning(f"Gemini error: {provider_diag.get('last_error')}")
        if agent_result.get("brain_analysis"):
            with st.expander("Brain Analysis", expanded=False):
                brain_analysis = agent_result.get("brain_analysis", {})
                st.write(
                    {
                        "provider": (brain_analysis.get("provider") or {}).get("provider"),
                        "model": (brain_analysis.get("provider") or {}).get("model"),
                        "api_response_status": (brain_analysis.get("provider") or {}).get("api_response_status"),
                        "selected_workflow": agent_result.get("selected_workflow"),
                        "selected_workflow_reason": agent_result.get("selected_workflow_reason"),
                        "goal": brain_analysis.get("goal", {}),
                    }
                )
        if agent_result.get("execution_plan"):
            with st.expander("Execution Plan", expanded=False):
                for step in agent_result.get("execution_plan", []):
                    st.write(f"- {step}")
        if agent_result.get("multi_agent"):
            with st.container(border=True):
                st.markdown("### Active Agents")
                st.write(", ".join(agent_result.get("active_agents", [])) or "Director Agent")
            with st.expander("Agent Collaboration Log", expanded=True):
                for item in agent_result.get("collaboration_log", []):
                    st.write(f"- {item}")
            with st.expander("Director Decisions", expanded=False):
                for decision in agent_result.get("director_decisions", []):
                    st.write(f"- {decision.get('agent', 'Agent')} → {decision.get('task')} ({decision.get('reason')})")
            if agent_result.get("section_sources"):
                with st.expander("Generated by Agent", expanded=False):
                    st.write(agent_result.get("section_sources"))
            if agent_result.get("agent_failures"):
                st.warning("One or more agents failed safely. Partial output is still available.")
                for failure in agent_result.get("agent_failures", []):
                    st.caption(failure)
        if agent_result.get("actions_performed"):
            with st.container(border=True):
                st.markdown("### Agent Actions")
                for action in agent_result.get("actions_performed", []):
                    st.write(f"- {action}")
        if agent_result.get("generated_files"):
            with st.container(border=True):
                st.markdown("### Generated Files")
                for file_index, file_name in enumerate(agent_result.get("generated_files", [])):
                    file_path = Path(file_name)
                    if file_path.is_file():
                        st.download_button(
                            f"Download {file_path.name}",
                            data=file_path.read_bytes(),
                            file_name=file_path.name,
                            mime="application/octet-stream",
                            use_container_width=True,
                            key=f"agent_studio_generated_file_{file_index}",
                        )
        if agent_result.get("errors"):
            st.warning("Some agent actions could not finish. Your text package is still available.")
            for error in agent_result.get("errors", []):
                st.caption(error)
        txt_payload = agent_package_to_text(agent_package)
        for index, (section, content) in enumerate(agent_package.items()):
            with st.container(border=True):
                st.markdown(f"### {section}")
                st.text_area(f"Copy {section}", value=content, height=130, key=f"agent_studio_section_{index}")
        st.download_button("Download Agent Package TXT", data=txt_payload.encode("utf-8-sig"), file_name="velaflow_agent_package.txt", mime="text/plain", use_container_width=True, key="agent_studio_download_txt")
    else:
        st.info("Start with one idea. VelaFlow will turn it into titles, script or lyrics, prompts, captions, hashtags, and next steps.")



if page == "Creator Dashboard":
    _render_creator_dashboard(project)

elif page in {"Idea", "Generate Song", "Generate Visual Pack", "Export Release Pack"}:
    _render_ai_creative_pack_generator(project, page)

elif page == "Dashboard":
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
        navs = [("Affiliate Studio", "Affiliate Studio"), ("Shorts Factory", "Shorts Factory"), ("Seller Studio", "Seller Studio"), ("System Health", "System Health"), ("AI Settings", "AI Settings")]
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

elif page == "Affiliate Studio":
    _render_affiliate_studio(project)

elif page == "VelaFlow Agent Studio":
    try:
        render_agent_studio(project)
    except Exception as exc:
        st.error("Agent Studio failed to initialize")
        if st.session_state.get("developer_mode"):
            st.exception(exc)

elif page == "Shorts Factory":
    _render_shorts_factory(project)

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
    st.caption("Cloud Beta: one-click vertical hook clips for TikTok / Reels / Shorts. Default flow uses images + motion + subtitles + voiceover fallback, not Veo.")
    creator_mode = st.radio(
        "Creator Mode",
        ["Basic Mode", "Advanced Mode"],
        horizontal=True,
        index=0,
        key="hook_clip_creator_mode",
        help="Basic Mode สำหรับสร้างคลิปเร็วที่สุด ส่วน Advanced Mode สำหรับปรับ scene/provider/debug",
    )
    sources = _hook_source_options(project)
    default_source = "Seller" if project.get("seller_studio") else "Podcast" if project.get("podcast_studio") else "Viral Clips" if project.get("viral_clips_studio") else "Music"
    source_label = default_source
    if creator_mode == "Advanced Mode":
        source_label = st.selectbox("Hook Source", list(sources), index=list(sources).index(default_source) if default_source in sources else 0, help="เลือกแหล่งไอเดีย ถ้าใส่ idea เอง ระบบจะใช้ idea นั้นก่อน")
    source_workflow = _hook_workflow_key(source_label)
    source_content = sources.get(source_label) or {}
    if creator_mode == "Basic Mode":
        with st.container(border=True):
            st.markdown("**Quick Hook Clip**")
            st.caption("ใส่ไอเดียสั้น ๆ แล้วกดปุ่มเดียว ระบบจะสร้าง hook, scenes, images, motion, voiceover/subtitles และ final_hook_clip.mp4")
            preset_items = list_presets()
            preset_labels = [item["label"] for item in preset_items]
            selected_preset_label = st.selectbox("🎨 Content Preset", preset_labels, index=0, key="quick_hook_content_preset", help="เลือกผลลัพธ์ที่อยากได้ ไม่ต้องตั้งค่ากล้อง/เสียง/จังหวะเอง")
            selected_preset = preset_items[preset_labels.index(selected_preset_label)] if preset_items else get_preset("viral_meme")
            st.info(selected_preset.get("description", "Creator outcome preset"))
            if selected_preset.get("preset_id") == "cute_character":
                st.caption("Cute Character examples: " + " · ".join(selected_preset.get("examples", [])[:6]))
            character_options = list(CHARACTER_TYPES)
            character_labels = [CHARACTER_TYPES[key]["label"] for key in character_options]
            selected_character_type = "banana"
            personality = "Funny"
            character_style = "Cute 3D"
            character_voice = "Cute"
            if selected_preset.get("preset_id") == "cute_character":
                with st.expander("Character options", expanded=False):
                    cc1, cc2 = st.columns(2)
                    selected_character_label = cc1.selectbox("🎭 Character Type", character_labels, index=0, key="quick_character_type", help="เลือกตัวละครหลัก ระบบจะล็อกหน้าตา สี และบุคลิกให้คงเดิมทุก scene")
                    selected_character_type = character_options[character_labels.index(selected_character_label)]
                    personality = cc2.selectbox("😄 Personality", list(PERSONALITY_PROMPTS), index=0, key="quick_character_personality", help="บุคลิกหลักของตัวละคร")
                    cs1, cs2 = st.columns(2)
                    character_style = cs1.selectbox("🎨 Character Style", list(STYLE_PROMPTS), index=0, key="quick_character_style", help="สไตล์ภาพของตัวละคร")
                    character_voice = cs2.selectbox("🎙 Voice Style", ["Cute", "Narrator", "Fast Meme", "Dramatic", "Calm", "Chaotic"], index=0, key="quick_character_voice", help="โทนเสียง/บทพูดของตัวละคร")
                    if st.button("⚡ Random Viral Character Idea", use_container_width=True, key="quick_random_character_idea"):
                        st.session_state["quick_hook_clip_idea"] = random_viral_character_idea(selected_character_type, personality)
                        st.rerun()
            quick_idea = st.text_area(
                "Idea / Hook / Product / Quote",
                value=st.session_state.get("quick_hook_clip_idea", ""),
                height=110,
                key="quick_hook_clip_idea",
                help="ใส่ไอเดียสั้น ๆ เช่น เรื่องเศร้า สินค้า ประโยคเด็ด หรือมุกไวรัล",
            )
            hook_clip_state = project.setdefault("hook_clip_studio", {})
            with st.expander("Upload Song Audio / Hook Audio", expanded=False):
                hook_clip_state = _render_hook_audio_controls(project.get("title") or _workflow_default_name("Hook Clip Studio (Beta)"), hook_clip_state, "hook_clip_basic", "clips")
                project["hook_clip_studio"] = hook_clip_state
                _save_project()
            quick_hook_audio_path = str(((hook_clip_state.get("hook_audio") or {}).get("path") or ""))
            quick_image_provider, quick_image_settings = _image_provider_controls("hook_clip_basic")
            ffmpeg_info = ffmpeg_version(settings.ffmpeg_path)
            if not ffmpeg_info.get("ok"):
                st.warning("⚠ FFmpeg runtime unavailable. VelaFlow can still generate the clip package, but MP4 export needs FFmpeg.")
            else:
                st.caption(f"✅ FFmpeg runtime ready: {ffmpeg_info.get('path')}")
            if st.button("⚡ Quick Generate Hook Clip", type="primary", use_container_width=True, disabled=not bool((quick_idea or source_content))):
                project_name = project.get("title") or _workflow_default_name("Hook Clip Studio (Beta)")
                idea_payload = quick_idea.strip() or json.dumps(source_content, ensure_ascii=False)[:400]
                apply_preset_to_project(project, selected_preset.get("preset_id", "viral_meme"))
                with st.spinner("Generating hook script, scenes, images, motion render, voiceover, subtitles, and MP4..."):
                    result = quick_generate_hook_clip(
                        project_name,
                        idea_payload,
                        source_workflow=source_workflow,
                        clip_mode="Fast Hook" if selected_preset.get("pace") in {"fast", "fun"} else "Story Clip",
                        image_provider=quick_image_provider,
                        image_settings=quick_image_settings,
                        preset_id=selected_preset.get("preset_id", "viral_meme"),
                        character_type=selected_character_type,
                        character_personality=personality,
                        character_style=character_style,
                        character_voice_style=character_voice,
                        voiceover_api_key=_user_api_key("openai"),
                        subtitle_preset="Cute Character Pop" if selected_preset.get("preset_id") == "cute_character" else "Fast Viral Caption",
                        hook_audio_path=quick_hook_audio_path,
                    )
                if result.get("data", {}).get("package"):
                    project.setdefault("hook_clip_studio", {})["hook_clip"] = result["data"]["package"]
                    project["hook_clip_studio"]["source"] = source_label
                    project["hook_clip_studio"]["quick_generate"] = result["data"]
                    project["hook_clip_studio"]["real_output"] = result["data"].get("render", {})
                    project["hook_clip_studio"]["voiceover_audio"] = result["data"].get("voiceover", {})
                    project["hook_clip_studio"]["creator_render_status"] = "completed" if result.get("ok") else "failed"
                    _save_project()
                    _log_beta_event("generate", workflow="hook_clip", preset_bundle=str(selected_preset.get("label", "Quick Generate")), metadata={"page": "Hook Clip Studio", "preset_id": selected_preset.get("preset_id")})
                if result.get("ok"):
                    st.success("final_hook_clip.mp4 generated.")
                else:
                    st.warning(result.get("error") or result.get("message") or "Quick generation finished with warnings.")
    else:
        manual_hook = st.text_area("Optional Hook / Quote Override", value="", height=90, help="ถ้ามีประโยคเด็ด ให้ใส่ตรงนี้ ระบบจะใช้แทนการ detect อัตโนมัติ")
        clip_mode = st.selectbox("Clip Mode", ["Fast Hook", "Viral Clip", "Story Clip"], index=0)
        duration = st.slider("Duration", 5, 10, 8)
        with st.expander("Advanced Character / Subtitle / Hook Controls", expanded=False):
            adv_seed = st.text_input("Character seed", value="", key="advanced_character_seed", help="เว้นว่างเพื่อสุ่ม seed ใหม่")
            adv_consistency = st.selectbox("Consistency strength", ["high", "medium"], index=0, key="advanced_consistency_strength")
            adv_subtitle_animation = st.selectbox("Subtitle animation", ["", "punch", "bounce", "emoji_pop", "karaoke", "dramatic", "meme_caption"], index=0, key="advanced_subtitle_animation")
            st.selectbox("Viral subtitle preset", list_viral_subtitle_presets(), index=3, key="advanced_viral_subtitle_preset")
            ac1, ac2, ac3 = st.columns(3)
            ac1.slider("Hook intensity", 0, 100, 75, key="advanced_hook_intensity")
            ac2.slider("Meme level", 0, 100, 70, key="advanced_meme_level")
            ac3.slider("Chaos level", 0, 100, 35, key="advanced_chaos_level")
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
        if creator_mode == "Basic Mode":
            _render_scene_preview_cards(project.get("title") or "hook_clip_project", hook_package, "hook_clip_studio")
            _render_final_downloads("hook_clip_studio", ((project.get("hook_clip_studio", {}) or {}).get("real_output") or {}))
            quick_data = ((project.get("hook_clip_studio", {}) or {}).get("quick_generate") or {})
            viral_metrics = quick_data.get("viral_metrics") or ((quick_data.get("package") or {}).get("viral_metrics") or {})
            thumbnail_quality = ((quick_data.get("thumbnail") or {}).get("score") or 0)
            timing_profile = (quick_data.get("beat_timing") or {}).get("timing_profile") or (quick_data.get("viral_timing_plan") or {}).get("timing_profile", "")
            if viral_metrics:
                st.markdown("**TikTok Optimization**")
                vm1, vm2, vm3, vm4 = st.columns(4)
                vm1.metric("Hook score", viral_metrics.get("hook_score", 0))
                vm2.metric("Emotional intensity", viral_metrics.get("emotional_impact", 0))
                vm3.metric("Viral pacing", viral_metrics.get("viral_pacing", 0))
                vm4.metric("Thumbnail quality", thumbnail_quality or "-")
                if timing_profile:
                    st.caption(f"Pacing profile: {timing_profile}")
            if quick_data.get("manifest_path"):
                st.caption(f"Quick manifest: {quick_data.get('manifest_path')}")
            _render_tiktok_package_downloads("hook_clip_studio", quick_data.get("tiktok_package") or {})
            if st.button("📦 Export TikTok Package", key="hook_clip_export_tiktok", use_container_width=True):
                package_result = export_tiktok_package(
                    project.get("title") or "hook_clip_project",
                    hook_package,
                    ((project.get("hook_clip_studio", {}) or {}).get("real_output") or {}),
                )
                project.setdefault("hook_clip_studio", {})["tiktok_package"] = package_result.get("data", {})
                _save_project()
                st.success("TikTok package exported") if package_result.get("ok") else st.error(package_result.get("error") or package_result.get("message"))
                st.rerun()
            with st.expander("Advanced files", expanded=False):
                for label, key_name, filename, mime in [
                    ("Download render_manifest.json", "render_manifest_path", "render_manifest.json", "application/json"),
                    ("Download scene_manifest.json", "scene_manifest_path", "scene_manifest.json", "application/json"),
                    ("Download character_profile.json", "character_profile_path", "character_profile.json", "application/json"),
                    ("Download hook_analysis.json", "hook_analysis_path", "hook_analysis.json", "application/json"),
                    ("Download viral_timing_plan.json", "viral_timing_plan_path", "viral_timing_plan.json", "application/json"),
                ]:
                    manifest_path = Path(str(quick_data.get(key_name) or ""))
                    if manifest_path.is_file():
                        st.download_button(label, data=manifest_path.read_bytes(), file_name=filename, mime=mime, use_container_width=True, key=f"hook_clip_{key_name}_download")
                styled_ass = Path(str((quick_data.get("styled_subtitles") or {}).get("ass") or ""))
                if styled_ass.is_file():
                    st.download_button("Download styled_subtitles.ass", data=styled_ass.read_bytes(), file_name="styled_subtitles.ass", mime="text/plain", use_container_width=True, key="hook_clip_styled_ass_download")
            voice_path = Path(str((quick_data.get("voiceover") or {}).get("audio_path") or ""))
            if voice_path.is_file():
                st.download_button("Download voiceover.mp3", data=voice_path.read_bytes(), file_name="voiceover.mp3", mime="audio/mpeg", use_container_width=True, key="hook_clip_quick_voiceover_download")
        t1, t2 = st.tabs(["Export", "Render" if creator_mode == "Advanced Mode" else "Advanced Render"])
        with t1:
            text = hook_clip_package_to_text(hook_package)
            export_data = ((project.get("hook_clip_studio", {}) or {}).get("export") or {})
            if export_data.get("txt_path"):
                st.caption(f"Hook package: {export_data.get('txt_path')}")
            st.download_button("Download hook_clip_package.txt", data=text.encode("utf-8"), file_name="hook_clip_package.txt", mime="text/plain", use_container_width=True)
            st.text_area("Copy-ready hook package", value=text, height=260)
        with t2:
            if creator_mode == "Advanced Mode":
                _render_package_preview({"package": hook_package.get("render_connector_package", {}), "export": hook_package.get("render_connector_export", {})})
                _render_real_clip_controls(project, "hook_clip_studio", hook_package, source_workflow, default_voice_style="meme voice" if source_workflow == "viral_clips" else "calm narrator")
                with st.expander("Advanced / Developer: Render Queue Metadata", expanded=False):
                    _render_queue_ui(project.get("title") or "hook_clip_project")
            else:
                st.info("Switch to Advanced Mode for provider payloads, scene-level controls, and developer queue metadata.")

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

elif page == "One Click Creator Flow":
    _render_one_click_creator_flow(project)

elif page == "Remaster Studio":
    _render_remaster_studio(project)

elif page == "Song Library":
    _page_header("Song Library", "Browse song projects, drafts, and Suno export readiness.", project)
    projects = filter_visible_projects(list_managed_projects(workflow_mode="Song Studio Only"), developer_mode=bool(st.session_state.get("developer_mode")))
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
    with st.expander("Advanced / Developer: Render Queue Metadata", expanded=False):
        _render_queue_ui(title or project.get("title") or "mv_project")
    storyboard_export = ((project.get("mv", {}) or {}).get("mv_storyboard_export") or {}).get("txt_path")
    if storyboard_export:
        st.caption(f"Latest storyboard export: {storyboard_export}")
    st.dataframe(pd.DataFrame((project.get("mv", {}) or {}).get("storyboard", []) or []), use_container_width=True, height=360)

elif page == "Video Prompt Studio":
    _page_header("Video Prompt Studio", "Plan AI video prompts for Whisk, Flow, Veo, Runway, Kling, Pika, and Luma.", project)
    st.caption("Lightweight prompt workflow only. No paid API call, no video rendering, no upload automation.")
    state = project.setdefault("video_prompt_studio", {})
    with st.container(border=True):
        st.markdown("### How to use")
        st.write("1. Paste lyrics or idea\n2. Choose video type\n3. Generate storyboard\n4. Copy prompt to Whisk / Flow / Veo / Runway\n5. Create short clips and edit later")
    preset_cols = st.columns(5)
    for idx, preset_name in enumerate(VIDEO_PROMPT_PRESETS):
        if preset_cols[idx % 5].button(preset_name, use_container_width=True, key=f"video_prompt_preset_{idx}"):
            state.update(VIDEO_PROMPT_PRESETS[preset_name])
            state["active_preset"] = preset_name
            project["video_prompt_studio"] = state
            _save_project()
            st.rerun()
    with st.container(border=True):
        c1, c2 = st.columns(2)
        project_type = c1.selectbox("Project type", VIDEO_PROMPT_PROJECT_TYPES, index=VIDEO_PROMPT_PROJECT_TYPES.index(state.get("project_type", VIDEO_PROMPT_PROJECT_TYPES[0])) if state.get("project_type") in VIDEO_PROMPT_PROJECT_TYPES else 0, key="video_prompt_project_type", help="เลือกประเภทวิดีโอที่อยากสร้าง")
        target_platform = c2.selectbox("Target platform", VIDEO_PROMPT_TARGET_PLATFORMS, index=VIDEO_PROMPT_TARGET_PLATFORMS.index(state.get("target_platform", "Multi Platform")) if state.get("target_platform") in VIDEO_PROMPT_TARGET_PLATFORMS else len(VIDEO_PROMPT_TARGET_PLATFORMS) - 1, key="video_prompt_target_platform", help="เลือกเครื่องมือปลายทาง เช่น Whisk, Flow, Veo, Runway")
        main_idea = st.text_area("Main idea or lyrics", value=state.get("main_idea", ""), height=170, key="video_prompt_main_idea", help="วางเนื้อเพลง ไอเดียสินค้า หรือคอนเซ็ปต์สั้นๆ")
        c3, c4 = st.columns(2)
        mood = c3.text_input("Mood", value=state.get("mood", "emotional cinematic"), key="video_prompt_mood", help="เช่น เศร้า อบอุ่น หรูหรา ตลก หรือดราม่า")
        clip_length = c4.selectbox("Clip length", VIDEO_PROMPT_CLIP_LENGTHS, index=VIDEO_PROMPT_CLIP_LENGTHS.index(state.get("clip_length", "15s")) if state.get("clip_length") in VIDEO_PROMPT_CLIP_LENGTHS else 2, key="video_prompt_clip_length")
        visual_style = st.text_input("Visual style", value=state.get("visual_style", "realistic cinematic vertical video"), key="video_prompt_visual_style", help="เช่น rainy window, UGC product close-up, cinematic apartment")
        reference_style_notes = st.text_area("Reference style notes", value=state.get("reference_style_notes", ""), height=90, key="video_prompt_reference_notes", help="ใส่ reference mood/style เช่น โทนสี แสง ห้อง เสื้อผ้า หรือภาพอ้างอิงที่อยากให้คงที่")
        generate_video_prompt = st.button("Generate Storyboard + AI Video Prompts", type="primary", use_container_width=True, disabled=not bool(main_idea.strip()), key="video_prompt_generate")
    if generate_video_prompt:
        package = build_video_prompt_package(
            project_type=project_type,
            main_idea=main_idea,
            mood=mood,
            visual_style=visual_style,
            target_platform=target_platform,
            clip_length=clip_length,
            reference_style_notes=reference_style_notes,
        )
        state.update(
            {
                "project_type": project_type,
                "target_platform": target_platform,
                "main_idea": main_idea,
                "mood": mood,
                "visual_style": visual_style,
                "clip_length": clip_length,
                "reference_style_notes": reference_style_notes,
                "package": package,
            }
        )
        project["video_prompt_studio"] = state
        _save_project()
        _log_beta_event("generate", workflow="video_prompt_studio", metadata={"page": "Video Prompt Studio", "target_platform": target_platform})
        st.rerun()
    package = state.get("package") or {}
    if package:
        st.markdown("## Video Prompt Package")
        st.success("Storyboard and prompts ready.")
        tabs = st.tabs(["Concept", "Storyboard", "Copy Prompts", "Download"])
        with tabs[0]:
            st.write(package.get("overall_video_concept", ""))
            st.text_area("Thai caption", value=package.get("thai_caption", ""), height=80, key="video_prompt_thai_caption")
            st.text_area("English caption", value=package.get("english_caption", ""), height=80, key="video_prompt_english_caption")
            st.write(" ".join(package.get("hashtags", [])))
        with tabs[1]:
            for scene in package.get("scene_list", []):
                with st.container(border=True):
                    st.markdown(f"**{scene.get('shot_id', '')}**")
                    st.write(f"Visual: {scene.get('visual_focus', '')}")
                    st.write(f"Camera movement: {scene.get('camera_movement', '')}")
                    st.write(f"Lighting and color tone: {scene.get('lighting', '')}")
                    st.text_area("Shot prompt", value=scene.get("prompt", ""), height=100, key=f"video_prompt_scene_{scene.get('shot_id', '')}")
        with tabs[2]:
            st.button("Copy Whisk Prompt", use_container_width=True, key="video_prompt_copy_whisk")
            st.text_area("Whisk Prompt", value=package.get("whisk_prompt", ""), height=130, key="video_prompt_whisk_prompt")
            st.button("Copy Video Prompt", use_container_width=True, key="video_prompt_copy_video")
            st.text_area("Video Prompt for Veo / Flow / Runway / Kling / Pika / Luma", value=package.get("video_prompt", ""), height=150, key="video_prompt_video_prompt")
            st.button("Copy Full Shot Package", use_container_width=True, key="video_prompt_copy_full")
            st.text_area("Full Shot Package", value=package.get("full_shot_package", ""), height=220, key="video_prompt_full_package")
            st.text_area("Negative prompt", value=package.get("negative_prompt", ""), height=90, key="video_prompt_negative_prompt")
        with tabs[3]:
            txt_payload = video_prompt_package_to_text(package)
            st.download_button("Download TXT", data=txt_payload.encode("utf-8-sig"), file_name="velaflow_video_prompt_package.txt", mime="text/plain", use_container_width=True, key="video_prompt_download_txt")
    else:
        st.info("Choose a preset or paste an idea to generate your first AI video prompt package.")

elif page == "Character Studio":
    _page_header("Character Studio", "Create reusable AI character prompts for Kling, Veo, Runway, Hailuo, PixVerse, and image tools.", project)
    st.info("Quick Start: 1) ใส่รายละเอียดตัวละคร 2) เลือกสไตล์/ฉาก/แพลตฟอร์ม 3) กด Generate Character Pack แล้ว copy prompt ไปใช้")

    state = project.setdefault("character_studio", {})
    saved_inputs = dict(DEFAULT_CHARACTER_INPUTS)
    saved_inputs.update(state.get("inputs") or {})

    with st.container(border=True):
        st.markdown("### Character Identity")
        c1, c2 = st.columns(2)
        saved_inputs["character_name"] = c1.text_input("ชื่อตัวละคร", value=saved_inputs.get("character_name", DEFAULT_CHARACTER_INPUTS["character_name"]), key="character_studio_name")
        saved_inputs["age_range"] = c2.text_input("อายุ / ประเภทตัวละคร", value=saved_inputs.get("age_range", DEFAULT_CHARACTER_INPUTS["age_range"]), key="character_studio_age")
        c3, c4 = st.columns(2)
        saved_inputs["gender_presentation"] = c3.text_input("เพศ / บุคลิกภาพ", value=saved_inputs.get("gender_presentation", DEFAULT_CHARACTER_INPUTS["gender_presentation"]), key="character_studio_gender")
        saved_inputs["country_culture"] = c4.text_input("ประเทศ / กลิ่นอายวัฒนธรรม", value=saved_inputs.get("country_culture", DEFAULT_CHARACTER_INPUTS["country_culture"]), key="character_studio_culture")
        saved_inputs["face_description"] = st.text_area("ใบหน้า / สีหน้า", value=saved_inputs.get("face_description", DEFAULT_CHARACTER_INPUTS["face_description"]), height=80, key="character_studio_face")
        c5, c6, c7 = st.columns(3)
        saved_inputs["hair_style"] = c5.text_input("ทรงผม", value=saved_inputs.get("hair_style", DEFAULT_CHARACTER_INPUTS["hair_style"]), key="character_studio_hair")
        saved_inputs["eye_style"] = c6.text_input("ดวงตา", value=saved_inputs.get("eye_style", DEFAULT_CHARACTER_INPUTS["eye_style"]), key="character_studio_eyes")
        saved_inputs["skin_tone"] = c7.text_input("สีผิว", value=saved_inputs.get("skin_tone", DEFAULT_CHARACTER_INPUTS["skin_tone"]), key="character_studio_skin")
        c8, c9 = st.columns(2)
        saved_inputs["outfit"] = c8.text_input("ชุดหลัก", value=saved_inputs.get("outfit", DEFAULT_CHARACTER_INPUTS["outfit"]), key="character_studio_outfit")
        saved_inputs["shoes_accessories"] = c9.text_input("รองเท้า / เครื่องประดับ", value=saved_inputs.get("shoes_accessories", DEFAULT_CHARACTER_INPUTS["shoes_accessories"]), key="character_studio_accessories")

    with st.container(border=True):
        st.markdown("### Prompt Setup")
        c1, c2 = st.columns(2)
        saved_inputs["character_style"] = c1.selectbox("Character style", CHARACTER_STYLES, index=CHARACTER_STYLES.index(saved_inputs.get("character_style")) if saved_inputs.get("character_style") in CHARACTER_STYLES else 0, key="character_studio_style")
        saved_inputs["scene_background"] = c2.selectbox("Scene background", SCENE_BACKGROUNDS, index=SCENE_BACKGROUNDS.index(saved_inputs.get("scene_background")) if saved_inputs.get("scene_background") in SCENE_BACKGROUNDS else 0, key="character_studio_background")
        c3, c4 = st.columns(2)
        saved_inputs["use_case"] = c3.selectbox("Use case", USE_CASES, index=USE_CASES.index(saved_inputs.get("use_case")) if saved_inputs.get("use_case") in USE_CASES else 0, key="character_studio_use_case")
        saved_inputs["platform"] = c4.selectbox("Platform", PLATFORMS, index=PLATFORMS.index(saved_inputs.get("platform")) if saved_inputs.get("platform") in PLATFORMS else 0, key="character_studio_platform")

    if st.button("Generate Character Pack", type="primary", use_container_width=True, key="character_studio_generate"):
        pack = generate_character_prompt_pack(**saved_inputs)
        state["inputs"] = saved_inputs
        state["pack"] = pack
        project["character_studio"] = state
        project["character"] = normalize_character(
            {
                "name": saved_inputs.get("character_name", ""),
                "gender": saved_inputs.get("gender_presentation", ""),
                "hair": saved_inputs.get("hair_style", ""),
                "outfit": saved_inputs.get("outfit", ""),
                "mood": saved_inputs.get("face_description", ""),
                "reference_notes": pack.get("sections", {}).get("Master Character Prompt", ""),
            }
        )
        _save_project()
        st.success("Character prompt pack ready.")
        st.rerun()

    pack = state.get("pack") or generate_character_prompt_pack(**saved_inputs)
    sections = pack.get("sections") or pack.get("outputs") or {}
    st.markdown("### Copy-Ready Prompts")
    for idx, section_name in enumerate(REQUIRED_CHARACTER_SECTIONS):
        height = 210 if section_name in {"Master Character Prompt", "Image Generation Prompt", "Image-to-Video Prompt"} else 130
        with st.container(border=True):
            st.button(f"Copy {section_name}", use_container_width=True, key=f"character_studio_copy_{idx}")
            st.text_area(section_name, value=sections.get(section_name, ""), height=height, key=f"character_studio_section_{idx}")

    txt_payload = character_prompt_pack_to_text(pack)
    st.download_button(
        "Download Character Pack TXT",
        data=txt_payload.encode("utf-8-sig"),
        file_name="velaflow_character_prompt_pack.txt",
        mime="text/plain",
        use_container_width=True,
        key="character_studio_download_txt",
    )

    with st.expander("Apply character to existing storyboard", expanded=False):
        st.code(build_character_prompt(project.get("character", {}) or {}), language="text")
        if st.button("Save Character / Apply To Storyboard", use_container_width=True, key="character_studio_apply_storyboard"):
            project["mv"] = apply_character_to_storyboard(project.get("mv", {}) or {}, project.get("character", {}) or {})
            _save_project()
            st.success("Character saved and applied to storyboard.")

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
    active_provider, active_api_key, _ = _active_text_credentials()
    st.json(
        run_healthcheck(
            settings,
            runtime_api_keys=_runtime_api_keys_for_health(),
            active_provider=active_provider,
            api_mode=st.session_state.get("api_mode", API_MODE_OWN_KEY),
        ),
        expanded=False,
    )
    _sync_provider_runtime_state()
    runtime = _provider_runtime_status(active_provider, active_api_key)
    st.info(f"Provider Runtime: {runtime['status']} · {runtime['message']}", icon="ℹ️")
    resolved = _active_credential_status()
    runtime_details = st.session_state.get("provider_runtime", {}) or {}
    st.json(
        {
            "Active Provider": provider_display_name(active_provider),
            "API Mode": resolved.get("api_mode"),
            "User Key": "Provided" if resolved.get("user_key_present") else "Missing",
            "VelaFlow Key": "Configured" if resolved.get("velaflow_key_present") else "Not configured",
            "Gemini runtime ready": runtime_details.get("gemini_runtime_ready", False),
            "Gemini client initialized": runtime_details.get("gemini_client_initialized", False),
            "Veo render capable": runtime_details.get("veo_render_capable", False),
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
        _sync_provider_runtime_state()
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
        _sync_provider_runtime_state()
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
            _sync_provider_runtime_state()
            st.success("API key saved on this device")
        else:
            st.warning("Paste an API key before saving.")
    if k2.button("Forget API Key", use_container_width=True):
        st.session_state.user_api_keys.pop(selected_provider, None)
        st.session_state[input_nonce_key] += 1
        st.session_state.api_mode = API_MODE_OWN_KEY
        st.session_state.api_storage_nonce += 1
        _forget_api_key_from_local_storage(selected_provider)
        _sync_provider_runtime_state()
        st.success("API key forgotten from this browser/device")
    resolved = resolve_provider_credentials(
        settings=settings,
        provider=selected_provider,
        api_mode=st.session_state.get("api_mode", API_MODE_OWN_KEY),
        user_api_keys=st.session_state.get("user_api_keys", {}),
    )
    _sync_provider_runtime_state()
    runtime = _provider_runtime_status(selected_provider, resolved.get("api_key", ""))
    runtime_details = st.session_state.get("provider_runtime", {}) or {}
    st.write(f"Active provider: {provider_label}")
    st.write(f"API Mode: {resolved.get('api_mode')}")
    st.info(f"Runtime status: {runtime['status']} · {runtime['message']}", icon="ℹ️")
    st.write("User Key:", mask_api_key(user_keys.get(selected_provider, "")))
    st.write("VelaFlow Key:", "Configured" if resolved.get("velaflow_key_present") else "Not configured")
    if selected_provider == "gemini":
        st.write("Gemini runtime ready:", bool(runtime_details.get("gemini_runtime_ready")))
        st.write("Gemini client initialized:", bool(runtime_details.get("gemini_client_initialized")))
        st.write("Veo render capable:", bool(runtime_details.get("veo_render_capable")))
    st.write(f"Gemini model: {settings.gemini_model}")
    st.write("Gemini configured:", bool((st.session_state.get("user_api_keys", {}) or {}).get("gemini") or settings.gemini_api_key))
    st.write(f"OpenAI GPT model: {settings.openai_text_model}")
    st.write("OpenAI configured:", bool((st.session_state.get("user_api_keys", {}) or {}).get("openai") or settings.openai_api_key))
    st.write(f"xAI Grok model: {settings.xai_text_model}")
    st.write("xAI Grok configured:", bool((st.session_state.get("user_api_keys", {}) or {}).get("xai") or settings.xai_api_key))
    st.caption("Environment variables: GEMINI_API_KEY, OPENAI_API_KEY, XAI_API_KEY, DEFAULT_AI_PROVIDER")
    st.caption("No payment, cloud sync, online license, full video AI, packaging, or watermark enforcement was added.")

elif page == "Artist Preset Manager":
    _render_artist_preset_manager()

