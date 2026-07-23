import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.asset_manager import attach_asset_to_project, clear_rejected_images, generate_asset_metadata, import_asset, list_assets as list_registered_assets, register_asset, safe_asset_filename
import core.agent_memory as agent_memory_module
import core.agent_tools as agent_tools_module
from core.agent_brain import AGENT_AI_PROVIDERS, analyze_user_goal, resolve_agent_provider, select_best_workflow, think
from core.agent_coordinator import run_multi_agent_workflow
from core.agent_executor import run_agent_workflow
from core.agent_memory import load_agent_memory, save_agent_memory, update_agent_memory
from core.agent_studio import AGENT_WORKFLOW_MODES, REQUIRED_AGENT_SECTIONS, agent_package_to_text, generate_agent_package
from core.agent_tools import build_multi_agent_creator_exports, build_release_package, create_project_folder, export_txt, generate_filename, generate_release_checklist, save_project_package, summarize_memory
from core.agent_router import route_agent_tasks
from core.agent_workflows import WORKFLOW_MODES, get_workflow_profile
from core.audio_editor import AUDIO_EDITOR_CUT_MODES, AUDIO_EDITOR_FADE_OPTIONS, HOOK_DURATION_PRESETS, analyze_hook_candidates, export_audio_batch, build_audio_cut_command, effective_cut_mode, export_audio_selection, generate_waveform_data, render_waveform_svg, validate_audio_editor_input, validate_audio_selection
from core.creative_pack_generator import CREATIVE_PACK_PRESETS, RELEASE_PACK_FILES, _ai_phrase_count, _apply_thai_natural_speech_engine, _compact_line, _enforce_situation_locked_title_hook, _relatability_report, _score_hook_candidate, _story_blueprint_v2, build_diversity_report, creative_release_pack_to_text, export_creative_release_pack, generate_creative_release_pack, generate_hook_candidates_v2, generate_music_seed_candidates_v2, generate_situation_first_seed, generate_story_candidates_v2, generate_title_candidates_v2, validate_selected_seed_relevance, load_diversity_memory, parse_lyric_sections, save_diversity_memory, score_hook_novelty, score_phrase_novelty, score_title_novelty
from core.agents import DirectorAgent, MusicAgent, MVAgent, PodcastAgent, ReleaseAgent, TikTokAgent
from core.workspace_manager import append_generation_run, append_history, archive_project as archive_workspace_project, create_project as create_workspace_project, export_project_zip as export_workspace_project_zip, list_projects as list_workspace_projects, load_project as load_workspace_project, save_project as save_workspace_project, workspace_summary
from core.media_pipeline import cover_pipeline, create_pipeline_item, load_pipeline, mv_pipeline, release_package_pipeline, save_pipeline, storyboard_pipeline, transition_stage
from core.project_assets import approve_cover, cover_prompt_history, get_project_asset_links, link_project_asset, project_asset_summary as workspace_project_asset_summary
from core.storyboard_manager import add_scene, create_storyboard, export_storyboard_json, export_storyboard_txt
import core.asset_manager as asset_manager_module
from providers.base_provider import LocalFallbackProvider
from providers.gemini_provider import GeminiProvider, GeminiTextProvider
from providers.openai_provider import OpenAITextProvider
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
)
from core.affiliate_caption_engine import build_affiliate_caption_package
from core.beta_access import load_beta_access, register_beta_activity, save_beta_access
from core.api_keys import API_MODE_BETA_KEY, API_MODE_OWN_KEY, LOCAL_STORAGE_KEYS, mask_api_key, resolve_gemini_api_key, resolve_provider_credentials
from core.api_quality_gate import API_QUALITY_WARNING, STATUS_MISSING_KEY, STATUS_PROVIDER_ERROR, STATUS_RATE_LIMITED, build_api_quality_gate
from core.provider_runtime import build_ffmpeg_runtime_diagnostics, build_provider_runtime_diagnostics
from core.clip_factory import choose_clip_scene, generate_clip, generate_clip_set
from core.exporter import export_package
from core.final_package import build_final_release_package, inspect_final_package_inputs
from core.job_queue import get_job, register_handler, submit_job
from core.licensing import LicenseService
from core.file_naming import build_export_filename, ensure_unique_path, sanitize_filename
from core.lyrics_expander import analyze_song_completeness, ensure_full_song_structure, validate_song_structure
from core.music_direction_engine import build_music_direction, export_music_direction_files
from core.marketing_package import build_marketing_package, export_marketing_package
from core.mv_storyboard_generator import export_mv_storyboard, generate_mv_storyboard, storyboard_to_text
from core.clip_studio_v2 import build_clip_studio_v2_shot_prompts, generate_clip_studio_v2, split_veo_shot_durations
from core.music_video_v2 import build_music_video_v2_shot_plan, generate_music_video_v2
from core.navigation_config import (
    FULL_MENU_GROUPS,
    HOOK_CLIP_ALLOWED_PAGES,
    HOOK_CLIP_MENU_GROUPS,
    PAGE_LABELS,
    PODCAST_STUDIO_ALLOWED_PAGES,
    PODCAST_STUDIO_MENU_GROUPS,
    SELLER_STUDIO_ALLOWED_PAGES,
    SELLER_STUDIO_MENU_GROUPS,
    SONG_ONLY_ALLOWED_PAGES,
    SONG_ONLY_MENU_GROUPS,
    VIRAL_CLIPS_ALLOWED_PAGES,
    VIRAL_CLIPS_MENU_GROUPS,
    flatten_pages,
    menu_groups_for_mode,
    normalize_navigation_state,
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
from core.visual_engine import build_camera_direction, build_scene_flow, build_shorts_structure, build_visual_prompt
from core.visual_presets import list_camera_presets, list_lighting_presets, list_motion_presets, list_visual_mood_presets
from core.clip_combine import combine_scene_clips
from core.hook_clip_engine import build_hook_render_package, export_hook_clip_package, extract_best_hook, hook_clip_package_to_text
from core.hook_detector import detect_hook_section
from core.hook_package_generator import build_final_creator_zip, generate_full_hook_creator_package
from core.prompt_director import build_prompt_director_package
from core.remaster_engine import REMASTER_RECOMMENDATION_MODES, REMASTER_STYLES, STYLE_FILTERS, analyze_audio_for_remaster_recommendation, build_remaster_project_id, recommend_remaster_preset_from_metadata, remaster_song_audio, validate_remaster_input
from core.automatic_hook_clip import quick_generate_hook_clip
from core.character_studio import REQUIRED_CHARACTER_STUDIO_SECTIONS, character_prompt_pack_to_text, generate_character_prompt_pack
from core.character_engine import apply_character_consistency, create_character_profile
from core.beat_timing_engine import create_beat_timing_plan
from core.beat_timing_engine import create_affiliate_retention_timing
from core.scene_prompt_engine import build_scene_prompt
from core.subtitle_engine import generate_styled_subtitles, get_viral_subtitle_preset, list_viral_subtitle_presets, mode_for_preset
from core.viral_timing_engine import create_viral_timing_plan
from core.hook_intelligence import analyze_opening_hook
from core.preset_engine import get_preset, list_presets, preset_to_render_settings
from core.product_prompt_engine import build_product_scene_prompts
from core.thumbnail_selector import score_affiliate_thumbnail_candidates
from core.trend_finder import export_trend_package, find_affiliate_trends
from core.video_prompt_studio import PRESETS as VIDEO_PROMPT_PRESETS, build_video_prompt_package, video_prompt_package_to_text
from core.podcast_content import (
    EPISODE_LENGTHS,
    NARRATION_STYLES,
    STORY_TONES,
    build_podcast_dashboard_status,
    export_podcast_content,
    generate_podcast_content,
    podcast_content_to_text,
)
from core.podcast_script_studio import (
    PODCAST_EPISODE_LENGTHS as SCRIPT_PODCAST_EPISODE_LENGTHS,
    PODCAST_NARRATORS,
    PODCAST_SCRIPT_TONES,
    REQUIRED_PODCAST_SCRIPT_SECTIONS,
    WORD_TARGETS,
    generate_podcast_script_package,
    podcast_script_package_to_text,
)
from core.recovery import recover_last_session, save_last_session
from core.theme import active_theme_name
from core.ui_styles import get_global_css
from core.version import APP_VERSION, identity_payload
from core.settings import get_settings
from core.artist_presets import (
    GENERAL_CREATOR_CATEGORY,
    PUBLIC_DEFAULT_ARTIST_ID,
    VELA_MOON_CATEGORY,
    artist_preset_categories,
    delete_artist_preset,
    duplicate_artist_preset,
    export_artist_preset,
    get_artist_preset,
    import_artist_preset,
    is_locked_artist_preset,
    list_artist_presets_by_category,
    list_artist_presets,
    load_default_artist_id,
    save_artist_preset,
    set_default_artist_preset,
    validate_artist_preset,
)
from core.instrument_tag_normalizer import contains_thai, normalize_lyrics_tags, validate_english_only_tags
from core.song_workflow import _extract_json, detect_best_song_hook, generate_hook_candidates, generate_hook_candidates_with_provider, save_song_state, select_best_hook
from core.song_structure_intelligence import (
    create_structure_plan,
    export_structure_plan_files,
    load_structure_plan,
    load_structure_presets,
    save_structure_plan,
    validate_structure_plan,
)
from core.song_title_engine import generate_song_title_candidates, generate_song_title_from_idea, is_placeholder_song_title, resolve_song_title, score_song_title_candidate, title_is_valid
from core.thai_quality_filter import clean_thai_output, detect_thai_quality_issues
from core.suno_export import build_release_package_data, export_creator_final_assets, extract_song_title_from_export_text, export_txt_filename, resolve_export_txt_filename, safe_txt_filename
from core.shorts_factory import build_shorts_comparison, generate_shorts_factory, list_shorts_variations
from core.project_io import load_project, new_project, save_project, save_project_folder
from core.project_manager import (
    autosave_project_state,
    archive_project,
    create_project as create_managed_project,
    delete_project,
    ensure_creator_project_folders,
    filter_visible_projects,
    is_test_project_name,
    list_archived_projects,
    list_projects as list_managed_projects,
    load_autosave_project_state,
    load_user_preferences,
    project_health_summary,
    project_exists,
    save_user_preferences,
    session_label_for_mode,
    workflow_type_for_mode,
)
from core.paths import LEGACY_PROJECTS_ROOT, WORKFLOW_PROJECT_ROOTS, resolve_project_folder, workflow_project_root
from core.preview_engine import build_preview_project, run_scene_preview
from core.quality_control import build_quality_checklist, recommend_regenerate_images
from core.project_workflow import build_project_status, clean_safe_temp_files, duplicate_project, export_project_report, list_recent_projects
from core.render_connector import (
    RENDER_JOB_PROVIDER_MODES,
    build_render_package,
    build_render_payload,
    build_render_queue_item,
    check_render_job_status,
    export_render_package,
    load_render_jobs,
    load_render_queue,
    mark_render_queue_item,
    send_render_job,
)
from core.real_clip_pipeline import ensure_parent_dir, find_ffmpeg, probe_media, render_image_motion_scene, render_placeholder_scene, render_real_hook_clip, trim_audio_clip, validate_mp4, write_subtitles
from core.render_cache import load_render_cache
from core.render_queue import active_render_job, complete_render_job, load_creator_render_queue, release_stale_render_jobs, start_render_job
from core.error_recovery import build_recovery_plan, friendly_error_message, recover_partial_render
from core.storage_cleanup import cleanup_project_storage, project_storage_summary
from core.veo_scene_renderer import download_veo_scene_result, load_scene_jobs, poll_veo_scene_job, scene_output_path, submit_veo_scene_job
from core.versioning import list_clip_versions
from core.rendering_presets import get_render_preset_bundle, get_rendering_provider_preset, list_render_preset_bundles, list_rendering_providers
from core.preset_system import list_global_presets, list_preset_packs, list_project_templates, list_scene_presets
from core.project_templates import create_project_from_template, suggested_scene_preset_details
from core.prompt_memory import apply_prompt_memory_to_project, load_prompt_memory, save_prompt_memory
from core.asset_library import export_asset_library, search_asset_library, update_library_from_project
from core.scene_reuse import recommend_reusable_scenes
from core.creative_suggestions import build_creative_suggestions
from core.workspace_optimizer import build_thumbnail_index, cleanup_old_cache, workspace_performance_report
from core.preset_marketplace import export_preset_bundle, import_preset_bundle
from core.one_click_workflow import build_full_mv_draft_payload, build_tiktok_set_plan, release_package_checklist
from core.emotional_arc import analyze_emotional_arc
from core.hook_intelligence import analyze_hooks
from core.visual_continuity import analyze_visual_continuity
from core.cinematic_advisor import apply_cinematic_suggestions, build_cinematic_suggestions
from core.adaptive_profiles import apply_adaptive_profile, recommend_render_profile
from core.creative_timeline import build_creative_timeline, export_creative_timeline
from core.asset_graph import build_asset_relationship_graph
from core.shot_intelligence import apply_shot_types, recommend_shot_types
from core.camera_language import apply_camera_language, recommend_camera_language
from core.scene_rhythm import analyze_scene_rhythm
from core.visual_story_consistency import analyze_visual_story_consistency
from core.director_notes import build_director_notes, inject_director_notes
from core.cinematic_style_packs import apply_cinematic_style_pack, list_cinematic_style_packs
from core.smart_scene_ordering import analyze_scene_order, apply_suggested_scene_order
from core.narrative_arc import analyze_narrative_arc
from core.performance_emotion import inject_performance_emotions, map_performance_emotions
from core.visual_metaphor import inject_visual_metaphors, suggest_visual_metaphors
from core.cinematic_beat_sync import analyze_cinematic_beats, inject_cinematic_beats
from core.subtitle_emotion import inject_dynamic_subtitle_emotion, map_dynamic_subtitle_emotion
from core.emotional_render_profiles import apply_emotional_render_profile, list_emotional_render_profiles, recommend_emotional_render_profile
from core.production_audit import export_project_audit, run_full_project_audit
from core.common_fixes import fix_common_issues
from core.creator_wizard import (
    TARGET_PLATFORM_OPTIONS,
    creative_direction_prompt,
    generate_creative_direction,
    save_creative_direction,
    suggest_project_name,
)
from core.healthcheck import run_pre_render_healthcheck
from core.healthcheck import run_healthcheck
from core.ffmpeg_utils import configure_moviepy_ffmpeg, ffmpeg_version, resolve_ffmpeg_path
from core.project_lock import acquire_project_lock, project_lock_status, release_project_lock
from core.render_recovery import export_diagnostic_bundle, latest_failed_render, recover_render_temp
from core.safe_mode import open_project_safe_mode
from core.beta_testing import (
    BETA_RATING_AREAS,
    add_beta_issue,
    average_beta_rating,
    beta_test_checklist,
    compare_render_versions,
    export_beta_report,
    list_beta_sessions,
    mark_stable_candidate,
    new_beta_session,
    update_beta_ratings,
)
from core.stable_build import STABLE_FREEZE_NAME, create_stable_candidate_snapshot, stable_build_summary
from core.render_engine import run_render
from core.scene_scoring import score_project_scenes, smart_tiktok_recommendations
from core.seller_content import HOOK_STYLES, build_seller_dashboard_status, compress_selling_points, export_seller_content, generate_seller_content, seller_content_to_text
from core.product_link_analyzer import analyze_product_link, detect_product_platform
import core.product_link_analyzer as product_link_analyzer
from core.scene_story_engine import build_scene_sequence, build_subtitle_timing
from core.style_consistency import build_style_consistency_report
from core.subtitle_engine import generate_subtitles
from core.timeline_builder import build_timeline
from core.voiceover_engine import build_voiceover_plan, export_voiceover_plan, generate_voiceover_audio
from providers.veo_provider import build_veo_payload, get_operation_name, list_available_veo_models, submit_render_job as submit_veo_render_job, test_veo_connection
from providers.image_ai import detect_image_provider_capability, generate_image, generate_image_with_diagnostics, validate_image_file
from providers.video_ai import build_hook_video_shot_prompts, generate_video, generate_video_shot, validate_video_prompt
from scripts.create_source_package import create_source_package
from scripts.build_beta_package import build_beta_package
from app.presets import DEFAULT_MUSIC_PRESET, DEFAULT_VOCAL_DIRECTION, get_music_preset, get_recommended_ai_controls, get_vocal_direction, list_music_preset_names, list_vocal_direction_names, music_preset_prompt, vocal_direction_prompt
from providers.ai_provider import normalize_provider, provider_display_name
from providers.provider_manager import generate_text as provider_generate_text


def assert_true(value, message):
    if not value:
        raise AssertionError(message)


def wait_job(job_id: str, timeout: float = 10.0):
    start = time.time()
    while time.time() - start < timeout:
        job = get_job(job_id)
        if job and job.get("status") in {"DONE", "FAILED", "CANCELED"}:
            return job
        time.sleep(0.2)
    raise AssertionError(f"Job timeout: {job_id}")


def make_project():
    project = new_project("Smoke Test V65")
    project["song"] = {
        "complete_lyrics": "[Chorus]\nยังคิดถึงเธอทุกคืน",
        "music_style_prompt": "Thai pop rock ballad, emotional male vocal, full-length arrangement",
        "advanced_settings": {"weirdness": "30%", "style_influence": "70%"},
        "tiktok_clip_cut_recommendation": [{"rank": 1, "start_seconds": 0, "section": "Chorus"}],
    }
    project["mv"] = {
        "storyboard": [
            {
                "scene": 1,
                "duration_seconds": 2,
                "lyric_part": "ยังคิดถึงเธอทุกคืน",
                "emotion": "lonely emotional hook",
                "camera": "slow dolly in",
                "pacing_note": "hook energy",
                "transition": "fade",
                "image_prompt": "cinematic Thai singer in rain",
                "video_prompt": "slow cinematic push in, rain atmosphere",
            }
        ]
    }
    return project


def main():
    out = ROOT / "outputs" / "smoke_tests"
    out.mkdir(parents=True, exist_ok=True)
    project = make_project()
    vela_moon = get_artist_preset("vela_moon")
    thai_tag_lyrics = "[Intro]\n(กีต้าร์โปร่งคลอเบาๆ คลอด้วยแพดนุ่มๆ)\nยังคิดถึงเธอทุกคืน\n[Outro]\n(ดนตรีค่อยๆ เฟด)"
    normalized_tags = normalize_lyrics_tags(thai_tag_lyrics, vela_moon)
    tag_validation = validate_english_only_tags(normalized_tags)
    short_song = "[Intro]\nคืนฝนพรำ\n\n[Verse 1]\nยังคิดถึงเธอ\n\n[Chorus]\nยังรักเธอ"
    expanded_song = ensure_full_song_structure(short_song, hook_text="ยังรักเธอ", idea="เพลงเศร้าที่ลืมคนรักไม่ได้", artist_preset=vela_moon)
    expanded_report = analyze_song_completeness(expanded_song["lyrics"])
    assert_true(expanded_song["expanded"] and expanded_report["ok"], "lyrics expander did not repair short song")
    for section in ["[Intro]", "[Verse 1]", "[Pre-Chorus]", "[Chorus]", "[Verse 2]", "[Bridge]", "[Final Chorus]", "[Outro]"]:
        assert_true(section in expanded_song["lyrics"], f"expanded lyrics missing {section}")
    assert_true(expanded_report["line_count"] >= 24 and expanded_report["chorus_line_count"] >= 4 and expanded_report["total_words"] >= 120, "expanded lyrics thresholds failed")
    music_direction = build_music_direction(
        genre="Modern Thai pop rock",
        mood="lonely emotional cinematic",
        vocal="smooth emotional male vocal",
        artist_preset=vela_moon,
    )
    assert_true(music_direction.get("bpm"), "music direction BPM missing")
    assert_true(len(music_direction.get("master_music_style_prompt", "")) >= 160, "music direction style prompt too short")
    for section in ["Intro", "Verse 1", "Pre-Chorus", "Chorus", "Verse 2", "Bridge", "Final Chorus", "Outro"]:
        assert_true(music_direction.get("section_tags", {}).get(section), f"music direction tag missing for {section}")
    assert_true("full band energy" in music_direction["section_tags"]["Chorus"], "chorus arrangement guidance missing")
    assert_true("full band energy" in expanded_song["lyrics"] and "ambient reverb tail" in expanded_song["lyrics"], "expanded lyrics missing rich arrangement tags")
    malformed_direction_layout = "[Chorus]\nทำไมยังรัก\n(full band energy, layered harmony, cinematic strings, emotional singalong hook, strong emotional release)\nยังไม่ลืม\n\n[Bridge]\nเจ็บอยู่"
    normalized_layout = ensure_full_song_structure(malformed_direction_layout, hook_text="ทำไมยังรัก", artist_preset=vela_moon)["lyrics"]
    assert_true("[Chorus]\n(full band energy" in normalized_layout, "section direction tag was not moved under header")
    assert_true("\nยังไม่ลืม\n(full band energy" not in normalized_layout, "mid-lyric direction tag was not removed")
    assert_true(validate_song_structure(expanded_song["lyrics"])["ok"], "expanded song structure guard failed")
    direction_export = export_music_direction_files(out / "music_direction_exports", music_direction)
    for filename in ["music_style_prompt.txt", "arrangement_map.txt", "vocal_direction.txt", "instrument_palette.txt", "energy_curve.json"]:
        assert_true(Path(direction_export[filename]).exists(), f"music direction export missing {filename}")
    project["song"]["artist_preset"] = "vela_moon"
    project["song"]["artist_preset_data"] = vela_moon
    project["song"]["complete_lyrics"] = thai_tag_lyrics
    project["song"]["normalized_song_output"] = normalized_tags
    project["song"]["instrument_tag_validation"] = tag_validation
    license_service = LicenseService(ROOT / "config" / "license.json")
    assert_true(license_service.module_enabled("core"), "license core flag failed")
    assert_true("Project Dashboard" in license_service.visible_pages({"Project Dashboard": "core"}), "license visible pages failed")
    assert_true(APP_VERSION == "0.1.0" and identity_payload()["generated_by"] == "VelaFlow", "version identity failed")
    procfile = (ROOT / "Procfile").read_text(encoding="utf-8")
    railway = json.loads((ROOT / "railway.json").read_text(encoding="utf-8"))
    nixpacks = (ROOT / "nixpacks.toml").read_text(encoding="utf-8")
    assert_true("--server.port=$PORT" in procfile and "--server.address=0.0.0.0" in procfile, "Procfile Railway start command failed")
    assert_true("--server.port=$PORT" in railway["deploy"]["startCommand"], "railway.json start command failed")
    assert_true('providers = ["python"]' in nixpacks and '"python311"' in nixpacks and '"ffmpeg"' in nixpacks, "nixpacks Python/FFmpeg install config failed")
    assert_true("[start]" in nixpacks and "streamlit run app/main.py --server.port=$PORT --server.address=0.0.0.0" in nixpacks, "nixpacks start command failed")
    previous_mode = os.environ.get("VELAFLOW_MODE")
    os.environ["VELAFLOW_MODE"] = "CLOUD"
    cloud_settings = get_settings()
    if previous_mode is None:
        os.environ.pop("VELAFLOW_MODE", None)
    else:
        os.environ["VELAFLOW_MODE"] = previous_mode
    assert_true(cloud_settings.velaflow_mode == "CLOUD", "VELAFLOW_MODE cloud setting failed")
    assert_true(normalize_provider("OpenAI GPT") == "openai" and provider_display_name("openai") == "OpenAI GPT", "OpenAI provider normalization failed")
    assert_true(normalize_provider("xAI Grok") == "xai" and provider_display_name("xai") == "xAI Grok", "xAI Grok provider normalization failed")
    fallback_prompt = f"smoke fallback {time.time_ns()}"
    gemini_fallback_text = provider_generate_text(provider="gemini", api_key="", prompt=fallback_prompt, offline_factory=lambda: "gemini fallback")
    openai_fallback_text = provider_generate_text(provider="openai", api_key="", prompt=fallback_prompt, offline_factory=lambda: "openai fallback")
    xai_fallback_text = provider_generate_text(provider="xai", api_key="", prompt=fallback_prompt, offline_factory=lambda: "xai fallback")
    assert_true(isinstance(gemini_fallback_text, str) and gemini_fallback_text.strip(), "Gemini provider response/fallback failed")
    assert_true(openai_fallback_text == "openai fallback" and xai_fallback_text == "xai fallback", "provider offline fallback failed")
    health = run_healthcheck(type("Settings", (), {"velaflow_mode": "CLOUD", "gemini_api_key": "", "openai_api_key": "", "xai_api_key": "", "default_ai_provider": "xai", "ffmpeg_path": "ffmpeg"})())
    health_names = [item["name"] for item in health["data"]["checks"]]
    assert_true("VelaFlow mode" in health_names and "Gemini configured" in health_names and "OpenAI configured" in health_names and "xAI Grok configured" in health_names and "Active AI provider" in health_names, "provider healthcheck failed")
    assert_true("FFmpeg installed" in health_names and "FFmpeg executable path" in health_names and "FFmpeg version" in health_names and "MoviePy FFmpeg access" in health_names, "FFmpeg healthcheck detail failed")
    ffmpeg_path = resolve_ffmpeg_path("ffmpeg")
    ffmpeg_info = ffmpeg_version("ffmpeg")
    moviepy_info = configure_moviepy_ffmpeg("ffmpeg")
    ffmpeg_runtime = build_ffmpeg_runtime_diagnostics("ffmpeg")
    assert_true((not ffmpeg_path and not ffmpeg_info["ok"]) or (ffmpeg_info["ok"] and moviepy_info["ok"]), "FFmpeg runtime detection failed")
    assert_true(ffmpeg_runtime["status"] in {"Ready", "Missing FFmpeg"} and "moviepy_ffmpeg_access" in ffmpeg_runtime, "FFmpeg runtime diagnostics failed")
    byo_health = run_healthcheck(
        type("Settings", (), {"velaflow_mode": "CLOUD", "gemini_api_key": "", "openai_api_key": "", "xai_api_key": "", "default_ai_provider": "gemini", "ffmpeg_path": "ffmpeg"})(),
        runtime_api_keys={"gemini": "user-gemini"},
        active_provider="gemini",
        api_mode=API_MODE_OWN_KEY,
    )
    gemini_health = next(item for item in byo_health["data"]["checks"] if item["name"] == "Gemini configured")
    assert_true(gemini_health["ok"] and "runtime/user key" in gemini_health["message"], "BYO Gemini health runtime sync failed")
    gemini_runtime = build_provider_runtime_diagnostics("gemini", "user-gemini", api_mode=API_MODE_OWN_KEY, source="user")
    assert_true(gemini_runtime["key_present"] and "Gemini runtime ready" in gemini_runtime["checks"], "BYO Gemini runtime diagnostics failed")
    assert_true(gemini_runtime["runtime_ready"] and gemini_runtime["gemini_runtime_ready"] and gemini_runtime["gemini_client_initialized"] and gemini_runtime["gemini_configure_result"] == "configured", "Gemini runtime/client initialization diagnostics failed")
    fake_settings = type(
        "Settings",
        (),
        {
            "gemini_api_key": "env-gemini",
            "openai_api_key": "env-openai",
            "xai_api_key": "",
            "gemini_model": "gemini-test",
            "openai_text_model": "openai-test",
            "xai_text_model": "grok-test",
        },
    )()
    own_resolved = resolve_provider_credentials(settings=fake_settings, provider="gemini", api_mode=API_MODE_OWN_KEY, user_api_keys={"gemini": "user-gemini"})
    beta_resolved = resolve_provider_credentials(settings=fake_settings, provider="openai", api_mode=API_MODE_BETA_KEY, user_api_keys={"openai": "user-openai"})
    missing_resolved = resolve_provider_credentials(settings=fake_settings, provider="xai", api_mode=API_MODE_OWN_KEY, user_api_keys={})
    assert_true(own_resolved["api_key"] == "user-gemini" and own_resolved["source"] == "user", "BYO user key priority failed")
    assert_true(beta_resolved["api_key"] == "env-openai" and beta_resolved["source"] == "velaflow_beta", "VelaFlow beta key resolution failed")
    assert_true(missing_resolved["api_key"] == "" and missing_resolved["status"] == STATUS_MISSING_KEY, "missing BYO key should block production generation")
    assert_true(missing_resolved["warning"] == API_QUALITY_WARNING, "missing own-key warning failed")
    saved_gemini_env = os.environ.pop("GEMINI_API_KEY", None)
    try:
        session_gemini = resolve_gemini_api_key(settings=fake_settings, session_state={"user_api_keys": {"gemini": "session-gemini"}})
        assert_true(session_gemini["api_key"] == "session-gemini" and session_gemini["source"] == "session" and session_gemini["enabled"], "Gemini session key resolution failed")
        os.environ["GEMINI_API_KEY"] = "env-gemini-live"
        env_gemini = resolve_gemini_api_key(settings=type("Settings", (), {"gemini_api_key": ""})(), session_state={"user_api_keys": {}})
        assert_true(env_gemini["api_key"] == "env-gemini-live" and env_gemini["source"] == "env" and env_gemini["enabled"], "Gemini env key resolution failed")
        os.environ.pop("GEMINI_API_KEY", None)
        missing_gemini = resolve_gemini_api_key(settings=type("Settings", (), {"gemini_api_key": ""})(), session_state={"user_api_keys": {}})
        assert_true(not missing_gemini["enabled"] and missing_gemini["source"] == "none" and missing_gemini["fallback_reason"], "Gemini missing key fallback failed")
    finally:
        if saved_gemini_env is not None:
            os.environ["GEMINI_API_KEY"] = saved_gemini_env
        else:
            os.environ.pop("GEMINI_API_KEY", None)
    assert_true(LOCAL_STORAGE_KEYS["gemini"] == "velaflow_gemini_key" and LOCAL_STORAGE_KEYS["openai"] == "velaflow_openai_key" and LOCAL_STORAGE_KEYS["xai"] == "velaflow_xai_key", "localStorage key names failed")
    assert_true(mask_api_key("abcd1234") == "Provided: ****1234" and mask_api_key("") == "Missing", "API key masking failed")
    analytics_root = out / "analytics_case"
    shutil.rmtree(analytics_root, ignore_errors=True)
    runtime_dirs = ensure_beta_runtime_dirs(analytics_root)
    assert_true(runtime_dirs["ok"] and (analytics_root / "analytics" / "analytics.json").exists(), "beta analytics runtime prep failed")
    log_beta_event("generate", workflow="seller", provider="xai", preset_bundle="Luxury Product", base_dir=analytics_root)
    log_beta_event("export", workflow="seller", provider="xai", base_dir=analytics_root)
    log_beta_event("render_job", workflow="seller", provider="xai", base_dir=analytics_root)
    log_beta_event("mv_storyboard_generated", workflow="music_mv", provider="gemini", base_dir=analytics_root)
    log_beta_event("render_package_generated", workflow="music_mv", provider="gemini", preset_bundle="Cinematic Sad", base_dir=analytics_root)
    log_beta_event("creator_render", workflow="music", preset_bundle="Emotional Story", metadata={"status": "completed", "ok": True, "render_duration": 12.5, "mood_preset": "Emotional Story", "hook_style": "emotional"}, base_dir=analytics_root)
    log_beta_event("creator_render", workflow="music", preset_bundle="Viral Meme", metadata={"status": "failed", "ok": False, "render_duration": 7.5, "mood_preset": "Viral Meme", "hook_style": "aggressive"}, base_dir=analytics_root)
    analytics = load_beta_analytics(analytics_root)
    assert_true(analytics["generate_count"] >= 2 and analytics["export_count"] >= 2 and analytics["render_job_count"] >= 1, "beta analytics counters failed")
    assert_true(analytics["quality_tracking"]["seller_workflow_usage"] >= 3 and analytics["quality_tracking"]["mv_storyboard_generation_count"] >= 1, "workflow quality counters failed")
    analytics_summary = beta_analytics_summary(analytics_root)
    assert_true(analytics_summary["data"]["total_renders"] == 2 and analytics_summary["data"]["render_success_rate"] == 50.0 and analytics_summary["data"]["avg_render_duration"] == 10.0, "closed beta render analytics failed")
    beta_access_path = analytics_root / "config" / "beta_access.json"
    beta_save = save_beta_access({"creator_name": "Smoke Creator", "creator_id": "smoke_creator"}, beta_access_path)
    beta_activity = register_beta_activity(2, beta_access_path)
    beta_profile = load_beta_access(beta_access_path)
    assert_true(beta_save["ok"] and beta_activity["ok"] and beta_profile["creator_id"] == "smoke_creator" and beta_profile["total_renders"] >= 2, "founding member beta access failed")
    old_temp = analytics_root / "outputs" / "temp" / "old_export.tmp"
    old_temp.parent.mkdir(parents=True, exist_ok=True)
    old_temp.write_text("old", encoding="utf-8")
    old_time = time.time() - 72 * 3600
    old_temp.touch()
    os.utime(old_temp, (old_time, old_time))
    cleanup = cleanup_old_temp_exports(ttl_hours=24, base_dir=analytics_root)
    assert_true(cleanup["ok"] and not old_temp.exists(), "old temp cleanup failed")
    music_preset_names = list_music_preset_names()
    default_music_preset = get_music_preset()
    tiktok_music_preset = get_music_preset("Viral TikTok Hook")
    assert_true(DEFAULT_MUSIC_PRESET == "VelaFlow Default" and music_preset_names[0] == "VelaFlow Default", "default music preset failed")
    assert_true(set(music_preset_names) == {"VelaFlow Default", "Viral TikTok Hook", "Story Cinematic"}, "public music preset list failed")
    assert_true("Vela Moon Signature" not in music_preset_names, "private Vela Moon Signature preset exposed")
    vocal_direction_names = list_vocal_direction_names()
    default_vocal_direction = get_vocal_direction()
    female_power = get_vocal_direction("Female Power Pop")
    assert_true(DEFAULT_VOCAL_DIRECTION == "Male Emotional" and vocal_direction_names[0] == "Male Emotional", "default vocal direction failed")
    assert_true(set(vocal_direction_names) == {"Male Emotional", "Female Soft", "Deep Male Cinematic", "Female Power Pop", "Indie Whisper", "Duo Harmony"}, "vocal direction preset list failed")
    assert_true("warm emotional male vocal" in default_vocal_direction["vocal_style"], "default vocal direction content failed")
    assert_true("modern pop power delivery" in vocal_direction_prompt(female_power), "vocal direction prompt failed")
    assert_true("general release" in default_music_preset["prompt_suffix"], "default music preset content failed")
    assert_true("hook within first 10 seconds" in tiktok_music_preset["arrangement"], "TikTok music preset content failed")
    assert_true("Music Preset:" in music_preset_prompt(tiktok_music_preset) and "TikTok or Shorts" in music_preset_prompt(tiktok_music_preset), "music preset prompt failed")
    assert_true(sanitize_filename("My Song / demo:night?") == "My_Song_demonight", "English filename sanitization failed")
    assert_true(sanitize_filename("คิดถึง เธอ / demo:night?") == "คิดถึง_เธอ_demonight", "Thai filename sanitization failed")
    assert_true(build_export_filename("My Song", "Vela Moon", "Suno Export", "txt") == "My_Song_Vela_Moon_Suno_Export.txt", "professional export filename failed")
    idea_forget_ex = "\u0e22\u0e31\u0e07\u0e25\u0e37\u0e21\u0e41\u0e1f\u0e19\u0e40\u0e01\u0e48\u0e32\u0e44\u0e21\u0e48\u0e44\u0e14\u0e49"
    title_forget_ex = "\u0e25\u0e37\u0e21\u0e40\u0e18\u0e2d\u0e44\u0e21\u0e48\u0e44\u0e14\u0e49"
    idea_return_ex = "\u0e23\u0e31\u0e01\u0e04\u0e19\u0e17\u0e35\u0e48\u0e44\u0e21\u0e48\u0e01\u0e25\u0e31\u0e1a\u0e21\u0e32"
    title_return_ex = "\u0e04\u0e19\u0e17\u0e35\u0e48\u0e44\u0e21\u0e48\u0e01\u0e25\u0e31\u0e1a\u0e21\u0e32"
    manual_title_ex = "\u0e0a\u0e37\u0e48\u0e2d\u0e17\u0e35\u0e48\u0e15\u0e31\u0e49\u0e07\u0e40\u0e2d\u0e07"
    assert_true(generate_song_title_from_idea(idea_forget_ex) in {title_forget_ex, "\u0e25\u0e37\u0e21\u0e44\u0e21\u0e48\u0e25\u0e07"}, "idea-only title generation failed")
    assert_true(generate_song_title_from_idea(idea_return_ex) == title_return_ex, "emotional title generation failed")
    long_hook_title = generate_song_title_from_idea(hook_text="\u0e22\u0e31\u0e07\u0e04\u0e34\u0e14\u0e16\u0e36\u0e07\u0e40\u0e18\u0e2d\u0e17\u0e38\u0e01\u0e04\u0e37\u0e19 \u0e41\u0e21\u0e49\u0e44\u0e21\u0e48\u0e21\u0e35\u0e17\u0e32\u0e07\u0e22\u0e49\u0e2d\u0e19\u0e21\u0e32")
    assert_true(long_hook_title != "\u0e22\u0e31\u0e07\u0e04\u0e34\u0e14\u0e16\u0e36\u0e07\u0e40\u0e18\u0e2d\u0e17\u0e38\u0e01\u0e04\u0e37\u0e19\u0e41\u0e21\u0e49\u0e44\u0e21\u0e48\u0e21\u0e35\u0e17\u0e32\u0e07\u0e22\u0e49\u0e2d\u0e19\u0e21\u0e32", "title copied full hook")
    assert_true(len(long_hook_title.replace(" ", "")) <= 20 and title_is_valid(long_hook_title), "generated title is too long or invalid")
    title_candidates = generate_song_title_candidates(hook_text="\u0e22\u0e31\u0e07\u0e04\u0e34\u0e14\u0e16\u0e36\u0e07\u0e40\u0e18\u0e2d\u0e17\u0e38\u0e01\u0e04\u0e37\u0e19 \u0e41\u0e21\u0e49\u0e44\u0e21\u0e48\u0e21\u0e35\u0e17\u0e32\u0e07\u0e22\u0e49\u0e2d\u0e19\u0e21\u0e32")
    assert_true(title_candidates and title_candidates[0]["score"] >= title_candidates[-1]["score"], "title candidates not scored")
    love_title = generate_song_title_from_idea("เพลงรัก")
    love_candidates = generate_song_title_candidates(idea="เพลงรัก")
    assert_true(len(love_candidates) == 10 and love_title not in {"รัก", "ความรัก", "เพลงรัก", "คิดถึง", "อกหัก", "เศร้า", "เหงา"}, "generic love title was not rejected")
    assert_true(all(key in love_candidates[0] for key in ["memorability", "emotional_impact", "caption_potential", "spotify_friendliness", "tiktok_friendliness", "uniqueness"]), "title scoring dimensions missing")
    assert_true(score_song_title_candidate("\u0e25\u0e37\u0e21\u0e44\u0e21\u0e48\u0e25\u0e07")["commercial_feel"] >= 70, "title commercial scoring failed")
    assert_true(resolve_song_title({"title": manual_title_ex, "idea": idea_forget_ex}) == manual_title_ex, "manual song title was overwritten")
    assert_true(is_placeholder_song_title("Demo Song") and is_placeholder_song_title("เพลงใหม่ของฉัน"), "placeholder title detection failed")
    duplicate_probe = out / "duplicate_filename_test.txt"
    duplicate_probe.write_text("x", encoding="utf-8")
    assert_true(ensure_unique_path(duplicate_probe).name.startswith("duplicate_filename_test_"), "duplicate filename timestamp handling failed")
    assert_true("Demo_Song_song_only" not in safe_txt_filename("Demo Song", "song_only"), "legacy Demo Song filename leaked")
    assert_true(safe_txt_filename('เดินต่อ / demo:night?', 'full_pipeline') == 'เดินต่อ_demonight_Vela_Moon_Suno_Export.txt', "safe Thai TXT filename failed")
    assert_true(safe_txt_filename('', 'song_only') == 'Untitled_Song_Vela_Moon_Lyrics_Only.txt', "empty title TXT fallback failed")
    export_text_with_title = "====================\nSONG METADATA\n====================\n\nSong title: เดินต่อ\n"
    assert_true(extract_song_title_from_export_text(export_text_with_title) == "เดินต่อ", "export title parser failed")
    assert_true(resolve_export_txt_filename({}, "", "Full Pipeline", export_text_with_title) == "เดินต่อ_Vela_Moon_Suno_Export.txt", "export filename parser fallback failed")
    default_controls = [get_recommended_ai_controls("VelaFlow Default") for _ in range(5)]
    default_pairs = {(item["weirdness"], item["style_influence"]) for item in default_controls}
    assert_true(default_pairs == {(12, 68)} and all(item["mode"] == "Auto by preset" and not item["manual"] for item in default_controls), "default AI controls should be deterministic auto-by-preset")
    tiktok_controls = get_recommended_ai_controls("Viral TikTok Hook")
    cinematic_controls = get_recommended_ai_controls("Story Cinematic")
    thai_sad_controls = get_recommended_ai_controls("Thai Sad Pop")
    assert_true(tiktok_controls["weirdness"] == 6 and tiktok_controls["style_influence"] == 82, "TikTok AI controls recommendation failed")
    assert_true(cinematic_controls["weirdness"] == 22 and cinematic_controls["style_influence"] == 58, "cinematic AI controls recommendation failed")
    assert_true(thai_sad_controls["weirdness"] == 14 and thai_sad_controls["style_influence"] == 70 and thai_sad_controls["weirdness"] != 89, "Thai Sad Pop should never default to extreme Weirdness")
    manual_controls = get_recommended_ai_controls("Vela Moon Emotional Pop Rock", manual_weirdness=89, manual_style_influence=99)
    assert_true(manual_controls["manual"] and manual_controls["weirdness"] == 25 and manual_controls["style_influence"] == 85 and manual_controls["mode"] == "Manual Override", "manual AI controls not clamped safely")
    css = get_global_css()
    assert_true("Inter" in css and "data-testid=\"stMetric\"" in css and "section[data-testid=\"stSidebar\"]" in css, "global UI styles failed")
    assert_true("@media (max-width: 768px)" in css and "min-height: 2.72rem" in css and "padding-top: max(2.5rem" in css and "padding-left: 0.9rem" in css, "mobile UI styles failed")
    assert_true("Handheld" in list_camera_presets() and "Neon Night" in list_lighting_presets() and "Fast TikTok Cuts" in list_motion_presets() and "Dark Office" in list_visual_mood_presets(), "visual presets failed")
    visual_prompt_a = build_visual_prompt(workflow_type="clips", subject="office rant", visual_settings={"camera_preset": "TikTok Creator", "lighting_preset": "Natural Daylight", "motion_preset": "Fast TikTok Cuts", "visual_mood": "Viral"})
    visual_prompt_b = build_visual_prompt(workflow_type="clips", subject="office rant", visual_settings={"camera_preset": "Cinematic", "lighting_preset": "Neon Night", "motion_preset": "Slow Cinematic", "visual_mood": "Lonely"})
    assert_true(visual_prompt_a != visual_prompt_b and "TikTok-style" in visual_prompt_a and "neon night" in visual_prompt_b.lower(), "visual prompts did not vary by preset")
    assert_true(build_scene_flow("seller")[0]["beat"] == "Hook" and build_scene_flow("music_mv")[0]["beat"] == "Intro", "visual scene structures failed")
    assert_true("Viral Beat" in build_shorts_structure("clips")["summary"] and "product visible" in build_camera_direction("Close-up", "seller"), "visual engine helpers failed")
    render_providers = list_rendering_providers()
    assert_true({"Runway", "Kling", "Veo", "PixVerse", "Pika", "Luma"}.issubset(set(render_providers)), "rendering provider presets missing")
    assert_true("9:16" in get_rendering_provider_preset("Kling")["recommended_aspect_ratios"], "rendering preset content failed")
    bundle_names = list_render_preset_bundles()
    assert_true({"TikTok Viral", "Cinematic Sad", "Luxury Product", "Podcast Dark Office", "Cozy Story", "Fast Affiliate", "Meme Chaos"}.issubset(set(bundle_names)), "render preset bundles missing")
    tiktok_bundle = get_render_preset_bundle("TikTok Viral")
    cinematic_bundle = get_render_preset_bundle("Cinematic Sad")
    assert_true(tiktok_bundle["camera_preset"] == "TikTok Creator" and tiktok_bundle["aspect_ratio"] == "9:16", "TikTok bundle failed")
    assert_true(cinematic_bundle["lighting_preset"] == "Moody Dark" and cinematic_bundle["duration"] == "10s", "Cinematic Sad bundle failed")
    payload_runway = build_render_payload(
        workflow_type="clips",
        project_type="clips",
        provider="Runway",
        aspect_ratio="9:16",
        duration="5s",
        quality="Draft",
        motion_intensity="Low",
        visual_settings={"camera_preset": "TikTok Creator", "lighting_preset": "Natural Daylight", "motion_preset": "Fast TikTok Cuts", "visual_mood": "Viral"},
        visual_prompt="creator hook prompt",
        thumbnail_prompt="thumbnail prompt",
        b_roll_ideas=["phone scroll"],
    )
    payload_kling = build_render_payload(
        workflow_type="clips",
        project_type="clips",
        provider="Kling",
        aspect_ratio="16:9",
        duration="10s",
        quality="Cinematic",
        motion_intensity="High",
        visual_settings={"camera_preset": "Cinematic", "lighting_preset": "Neon Night", "motion_preset": "Slow Cinematic", "visual_mood": "Lonely"},
        visual_prompt="cinematic hook prompt",
        thumbnail_prompt="thumbnail prompt",
        b_roll_ideas=["night street"],
    )
    assert_true(payload_runway["provider"] != payload_kling["provider"] and payload_runway["aspect_ratio"] != payload_kling["aspect_ratio"], "render payload did not vary by provider/settings")
    queue_item = build_render_queue_item("Smoke Render", payload_runway)
    assert_true(queue_item["status"] == "Ready" and queue_item["payload"]["provider"] == "Runway", "render queue item failed")
    full_pages = flatten_pages(FULL_MENU_GROUPS)
    song_only_pages = flatten_pages(SONG_ONLY_MENU_GROUPS)
    assert_true("VelaFlow Agent Studio" in FULL_MENU_GROUPS["START"], "Agent Studio missing from START navigation")
    assert_true(FULL_MENU_GROUPS["START"][0] == "Creator Dashboard" and SONG_ONLY_MENU_GROUPS["WORKSPACES"] == ["Song Studio", "Remaster Studio", "Audio Editor", "Visual Studio", "Release Pack"], "VelaFlow workspace navigation should be Song/Remaster/Audio/Visual/Release")
    assert_true(PAGE_LABELS.get("Creator Dashboard") == "Creator Dashboard", "Creator Dashboard label missing")
    assert_true(PAGE_LABELS.get("VelaFlow Agent Studio") == "🤖 VelaFlow Agent Studio" and flatten_pages(FULL_MENU_GROUPS).count("VelaFlow Agent Studio") == 1, "Agent Studio navigation label/key failed")
    assert_true("VelaFlow Agent Studio" not in flatten_pages(SONG_ONLY_MENU_GROUPS), "Agent Studio should be hidden from normal V1 creative pack navigation")
    assert_true(FULL_MENU_GROUPS["SONG"] == ["Song Studio", "Song Library", "Artist Preset Manager"], "SONG navigation group failed")
    assert_true("Artist Preset Manager" in FULL_MENU_GROUPS["SONG"], "Artist Preset Manager missing from SONG group")
    assert_true("Video Prompt Studio" in FULL_MENU_GROUPS["VISUAL"] and "Podcast Script Studio" in FULL_MENU_GROUPS["VISUAL"], "creative tools missing from VISUAL group")
    assert_true("Hook Clip Studio" in full_pages and "Render Lab" in full_pages and "Final Package" in full_pages and "Queue Monitor" in full_pages, "Full Pipeline navigation missing pages")
    assert_true("Render Lab" not in song_only_pages and "Final Package" not in song_only_pages and "Creative Intelligence" not in song_only_pages, "Song Studio Only did not hide production pages")
    assert_true(song_only_pages == ["Song Studio", "Remaster Studio", "Audio Editor", "Visual Studio", "Release Pack", "AI Settings"], "Song Studio Only missing VelaFlow workspace navigation")
    assert_true(set(song_only_pages) == SONG_ONLY_ALLOWED_PAGES, "Song Studio Only allowed page set mismatch")
    assert_true(len(full_pages) == len(set(full_pages)) and len(song_only_pages) == len(set(song_only_pages)), "duplicate navigation pages found")
    assert_true(PAGE_LABELS.get("Creator Wizard") == "Release Workflow Wizard" and PAGE_LABELS.get("Smart Clip Factory") == "Clip Factory" and PAGE_LABELS.get("Production Audit") == "Quality Audit", "menu label polish failed")
    assert_true(normalize_navigation_state(FULL_MENU_GROUPS, "SONG", "Dashboard") == ("SONG", "Song Studio"), "Full Pipeline cannot select SONG")
    assert_true(normalize_navigation_state(FULL_MENU_GROUPS, "VISUAL", "Dashboard") == ("VISUAL", "MV Director"), "Full Pipeline cannot select VISUAL")
    assert_true(normalize_navigation_state(FULL_MENU_GROUPS, "PRODUCTION", "Dashboard") == ("PRODUCTION", "Hook Clip Studio"), "Full Pipeline cannot select PRODUCTION")
    assert_true("VISUAL" not in SONG_ONLY_MENU_GROUPS and "PRODUCTION" not in SONG_ONLY_MENU_GROUPS, "Song Studio Only did not hide VISUAL/PRODUCTION groups")
    seller_pages = flatten_pages(SELLER_STUDIO_MENU_GROUPS)
    assert_true(menu_groups_for_mode("Seller Studio (Beta)") == SELLER_STUDIO_MENU_GROUPS and "Affiliate Studio" in SELLER_STUDIO_ALLOWED_PAGES and "Shorts Factory" in SELLER_STUDIO_ALLOWED_PAGES, "Seller Studio workflow mode failed")
    assert_true(set(seller_pages) == SELLER_STUDIO_ALLOWED_PAGES, "Seller Studio allowed page set mismatch")
    assert_true("Seller Studio" in seller_pages and "Render Lab" not in seller_pages and "Song Studio" not in seller_pages, "Seller Studio navigation filtering failed")
    assert_true(normalize_navigation_state(SELLER_STUDIO_MENU_GROUPS, "SELLER", "Dashboard") == ("SELLER", "Affiliate Studio"), "Seller Studio section selection failed")
    assert_true(workflow_type_for_mode("Seller Studio (Beta)") == "seller", "Seller workflow type mapping failed")
    assert_true(session_label_for_mode("Seller Studio (Beta)") == "Current Seller Session", "Seller session label failed")
    podcast_pages = flatten_pages(PODCAST_STUDIO_MENU_GROUPS)
    assert_true(menu_groups_for_mode("Podcast Studio (Beta)") == PODCAST_STUDIO_MENU_GROUPS, "Podcast Studio workflow mode failed")
    assert_true(set(podcast_pages) == PODCAST_STUDIO_ALLOWED_PAGES, "Podcast Studio allowed page set mismatch")
    assert_true("Podcast Studio" in podcast_pages and "Song Studio" not in podcast_pages and "Seller Studio" not in podcast_pages and "Render Lab" not in podcast_pages, "Podcast Studio navigation filtering failed")
    assert_true(normalize_navigation_state(PODCAST_STUDIO_MENU_GROUPS, "PODCAST", "Dashboard") == ("PODCAST", "Podcast Studio"), "Podcast Studio section selection failed")
    assert_true(workflow_type_for_mode("Podcast Studio (Beta)") == "podcast", "Podcast workflow type mapping failed")
    assert_true(session_label_for_mode("Podcast Studio (Beta)") == "Current Podcast Session", "Podcast session label failed")
    viral_pages = flatten_pages(VIRAL_CLIPS_MENU_GROUPS)
    assert_true(menu_groups_for_mode("Viral Clips Studio (Beta)") == VIRAL_CLIPS_MENU_GROUPS, "Viral Clips workflow mode failed")
    assert_true(set(viral_pages) == VIRAL_CLIPS_ALLOWED_PAGES, "Viral Clips allowed page set mismatch")
    assert_true("Viral Clips Studio" in viral_pages and "Song Studio" not in viral_pages and "Seller Studio" not in viral_pages and "Render Lab" not in viral_pages, "Viral Clips navigation filtering failed")
    assert_true(normalize_navigation_state(VIRAL_CLIPS_MENU_GROUPS, "CLIPS", "Dashboard") == ("CLIPS", "Viral Clips Studio"), "Viral Clips section selection failed")
    assert_true(workflow_type_for_mode("Viral Clips Studio (Beta)") == "clips", "Viral Clips workflow type mapping failed")
    assert_true(session_label_for_mode("Viral Clips Studio (Beta)") == "Current Clips Session", "Viral Clips session label failed")
    hook_clip_pages = flatten_pages(HOOK_CLIP_MENU_GROUPS)
    assert_true(menu_groups_for_mode("Hook Clip Studio (Beta)") == HOOK_CLIP_MENU_GROUPS, "Hook Clip Studio workflow mode failed")
    assert_true(set(hook_clip_pages) == HOOK_CLIP_ALLOWED_PAGES, "Hook Clip Studio allowed page set mismatch")
    assert_true("Hook Clip Studio" in hook_clip_pages and "Render Lab" not in hook_clip_pages and "Seller Studio" not in hook_clip_pages, "Hook Clip Studio navigation filtering failed")
    assert_true(normalize_navigation_state(HOOK_CLIP_MENU_GROUPS, "CLIPS", "Dashboard") == ("CLIPS", "Hook Clip Studio"), "Hook Clip Studio section selection failed")
    assert_true(workflow_type_for_mode("Hook Clip Studio (Beta)") == "hook_clip", "Hook Clip workflow type mapping failed")
    assert_true(session_label_for_mode("Hook Clip Studio (Beta)") == "Current Hook Clip Session", "Hook Clip session label failed")
    dashboard_target = "Creator Dashboard"
    assert_true(dashboard_target in full_pages and "Song Studio" in song_only_pages and "Audio Editor" in song_only_pages and "Remaster Studio" in song_only_pages, "workspace continue target invalid")
    direction = generate_creative_direction(
        topic="Custom",
        custom_topic="เพลงทดสอบเริ่มจากวิซาร์ด",
        mood="Emotional",
        music_direction="Emotional Pop Rock",
        artist_preset_id="__missing_artist__",
        target_platform="Full Pipeline",
    )
    assert_true(direction["artist_preset"] == "vela_moon" and direction["project_concept"] and direction["hook_direction"], "offline creative direction failed")
    safe_wizard_name = suggest_project_name("Custom", "เพลงทดสอบเริ่มจากวิซาร์ด")
    assert_true(safe_wizard_name and " " not in safe_wizard_name, "custom topic safe project name failed")
    wizard_save = save_creative_direction("Smoke Wizard Project", direction, out / "wizard_projects")
    wizard_path = Path(wizard_save["data"]["path"])
    assert_true(wizard_save["ok"] and wizard_path.exists(), "creative_direction.json was not saved")
    wizard_loaded = json.loads(wizard_path.read_text(encoding="utf-8"))
    assert_true(wizard_loaded["topic"] == "เพลงทดสอบเริ่มจากวิซาร์ด", "creative direction load failed")
    assert_true("Creative Direction" in creative_direction_prompt(direction), "creative direction prompt failed")
    project["creative_direction"] = direction
    assert_true(project["creative_direction"]["music_direction"] == "Emotional Pop Rock", "Song Studio project creative direction state failed")
    assert_true(TARGET_PLATFORM_OPTIONS and "Full Pipeline" in TARGET_PLATFORM_OPTIONS, "creator wizard target platforms failed")
    assert_true("Creator Wizard" in full_pages and "Song Studio" in full_pages, "navigation config missing Creator Wizard or Song Studio")
    assert_true(["Song Studio", "Remaster Studio", "Audio Editor", "Visual Studio", "Release Pack", "AI Settings"] == song_only_pages, "V1 navigation should expose five product workspaces and Settings")
    assert_true(AUDIO_EDITOR_CUT_MODES == ["Lossless Quick Cut", "Precise Cut"] and AUDIO_EDITOR_FADE_OPTIONS["Off"] == 0.0, "Audio Editor V1 cut mode/fade config failed")
    assert_true(validate_audio_selection(1.0, 3.0, 10.0)["ok"] and not validate_audio_selection(3.0, 1.0, 10.0)["ok"] and validate_audio_selection(0.0, 20.0, 10.0)["error"] == "end_beyond_duration" and validate_audio_selection(0.0, 0.5, 10.0)["error"] == "selection_too_short", "Audio Editor selection validation failed")
    assert_true({"15 seconds", "30 seconds", "45 seconds", "60 seconds", "Custom"}.issubset(set(HOOK_DURATION_PRESETS)), "Audio Editor hook duration helpers missing")
    assert_true(effective_cut_mode("song.mp3", "Lossless Quick Cut", 0, 0)[0] == "Lossless Quick Cut" and effective_cut_mode("song.mp3", "Lossless Quick Cut", 0.25, 0)[0] == "Precise Cut", "Audio Editor effective mode validation failed")
    lossless_cmd = build_audio_cut_command("ffmpeg", "source.mp3", "hook.mp3", start_time=1, end_time=4, cut_mode="Lossless Quick Cut")
    precise_cmd = build_audio_cut_command("ffmpeg", "source.mp3", "hook.mp3", start_time=1, end_time=4, cut_mode="Precise Cut", fade_in=0.25, fade_out=0.25, sample_rate=44100, channels=2)
    assert_true("-c:a" in lossless_cmd and "copy" in lossless_cmd and "-af" not in lossless_cmd, "Lossless Quick Cut command must stream copy without filters")
    assert_true("libmp3lame" in precise_cmd and "320k" in precise_cmd and "-af" in precise_cmd, "Precise Cut command must use libmp3lame 320k and fade filters when requested")
    assert_true(REMASTER_STYLES[0] == "Streaming Balanced" and {"Streaming Balanced", "Modern Pop", "Pop Rock", "Emotional Ballad", "Warm Acoustic", "Vocal Focus", "Cinematic", "Loud Modern"}.issubset(set(REMASTER_STYLES)), "Remaster Studio V1 preset list failed")
    assert_true(STYLE_FILTERS["Streaming Balanced"]["target_lufs"].startswith("-14"), "Remaster Streaming Balanced target failed")
    assert_true(build_remaster_project_id("My Song.mp3").startswith("My_Song_"), "Remaster project id safe filename failed")
    cheer_recommend = recommend_remaster_preset_from_metadata({"genre": "Cheer Stadium Crowd Chant High Energy", "style_prompt": "heavy drums 808"})
    edm_recommend = recommend_remaster_preset_from_metadata({"genre": "EDM Trap Dance", "style_prompt": "heavy 808 bass electronic"})
    acoustic_recommend = recommend_remaster_preset_from_metadata({"genre": "Acoustic Emotional Ballad", "vocal_type": "soft vocal"})
    podcast_recommend = recommend_remaster_preset_from_metadata({"song_type": "Podcast narration spoken voice"})
    assert_true(REMASTER_RECOMMENDATION_MODES[0] == "Auto Recommended" and cheer_recommend["recommended_preset"] == "Loud Modern" and edm_recommend["recommended_preset"] == "Modern Pop" and acoustic_recommend["recommended_preset"] == "Warm Acoustic" and podcast_recommend["recommended_preset"] == "Vocal Focus", "Remaster metadata recommendation mapping failed")
    unsupported_audio = out / "bad_upload.txt"
    unsupported_audio.write_text("not audio", encoding="utf-8")
    assert_true(not validate_remaster_input(unsupported_audio)["ok"] and validate_remaster_input(unsupported_audio)["error"] == "unsupported_format", "Remaster unsupported input was not rejected")
    unsupported_editor_wav = out / "bad_audio_editor.wav"
    unsupported_editor_wav.write_bytes(b"RIFF0000WAVE")
    editor_wav_validation = validate_audio_editor_input(unsupported_editor_wav)
    assert_true(not editor_wav_validation["ok"] and editor_wav_validation["error"] == "unsupported_format", "Audio Editor must reject WAV input")
    provider_error_gate = build_api_quality_gate(api_key="fake-key", provider_error="429 quota exceeded", provider="gemini")
    assert_true(provider_error_gate["status"] == STATUS_RATE_LIMITED and API_QUALITY_WARNING in provider_error_gate["message"], "provider rate-limit quality gate failed")
    provider_failure_gate = build_api_quality_gate(api_key="fake-key", provider_error="Gemini model unavailable", provider="gemini")
    assert_true(provider_failure_gate["status"] == STATUS_PROVIDER_ERROR and provider_failure_gate["offline_allowed"] is False, "provider error quality gate failed")
    blocked_release_pack = generate_creative_release_pack("เพลงรัก", "Vela Moon Emotional Pop Rock", "Vela Moon", production_mode=True, api_key="", demo_mode=False)
    assert_true(not blocked_release_pack["ok"] and blocked_release_pack["provider_status"]["status"] == STATUS_MISSING_KEY and blocked_release_pack["message"] == API_QUALITY_WARNING, "Song Studio production generation silently allowed missing API")
    release_pack = generate_creative_release_pack("เพลงเศร้าในออฟฟิศ", "Office Burnout", "Vela Moon")
    release_export = export_creative_release_pack("Smoke Creative Pack", release_pack, "Vela Moon", base_dir=out / "creative_pack")
    release_zip = Path((release_export.get("data") or {}).get("zip_path", ""))
    release_txt = creative_release_pack_to_text(release_pack)
    assert_true(release_pack["ok"] and set(RELEASE_PACK_FILES.values()).issubset(set(release_pack["pack"].keys())), "creative release pack missing required outputs")
    assert_true(release_export["ok"], "release pack should work without remaster data")
    dummy_remaster_dir = out / "dummy_remaster"
    dummy_remaster_dir.mkdir(parents=True, exist_ok=True)
    dummy_wav = dummy_remaster_dir / "dummy_master.wav"
    dummy_mp3 = dummy_remaster_dir / "dummy_master.mp3"
    dummy_report = dummy_remaster_dir / "remaster_report.json"
    dummy_report_txt = dummy_remaster_dir / "remaster_report.txt"
    dummy_wav.write_bytes(b"RIFF0000WAVE")
    dummy_mp3.write_bytes(b"ID3")
    dummy_report.write_text("{}", encoding="utf-8")
    dummy_report_txt.write_text("report", encoding="utf-8")
    release_with_remaster = export_creative_release_pack("Smoke Creative Pack Remaster", release_pack, "Vela Moon", base_dir=out / "creative_pack_with_remaster", remaster_data={"mastered_wav": str(dummy_wav), "mastered_mp3": str(dummy_mp3), "report_path": str(dummy_report), "report_txt_path": str(dummy_report_txt)})
    remaster_release_zip = Path((release_with_remaster.get("data") or {}).get("zip_path", ""))
    with zipfile.ZipFile(remaster_release_zip) as archive:
        assert_true({"remaster/mastered_wav.wav", "remaster/mastered_mp3.mp3", "remaster/remaster_report.json", "remaster/remaster_report.txt"}.issubset(set(archive.namelist())), "release pack did not include optional remaster files")
    dummy_hook = dummy_remaster_dir / "my_song_hook.mp3"
    dummy_edit_report = dummy_remaster_dir / "edit_report.json"
    dummy_edit_report_txt = dummy_remaster_dir / "edit_report.txt"
    dummy_hook.write_bytes(b"ID3HOOK")
    dummy_edit_report.write_text("{}", encoding="utf-8")
    dummy_edit_report_txt.write_text("edit report", encoding="utf-8")
    release_with_audio_edit = export_creative_release_pack("Smoke Creative Pack Audio Edit", release_pack, "Vela Moon", base_dir=out / "creative_pack_with_audio_edit", audio_edit_data={"hook_mp3": str(dummy_hook), "report_path": str(dummy_edit_report), "report_txt_path": str(dummy_edit_report_txt)})
    audio_edit_release_zip = Path((release_with_audio_edit.get("data") or {}).get("zip_path", ""))
    with zipfile.ZipFile(audio_edit_release_zip) as archive:
        assert_true({"audio_editor/hook.mp3", "audio_editor/edit_report.json", "audio_editor/edit_report.txt"}.issubset(set(archive.namelist())), "release pack did not include optional audio edit files")
    release_with_master_and_hook = export_creative_release_pack("Smoke Creative Pack Master And Hook", release_pack, "Vela Moon", base_dir=out / "creative_pack_with_master_and_hook", remaster_data={"mastered_wav": str(dummy_wav), "mastered_mp3": str(dummy_mp3), "report_path": str(dummy_report), "report_txt_path": str(dummy_report_txt)}, audio_edit_data={"hook_mp3": str(dummy_hook), "report_path": str(dummy_edit_report), "report_txt_path": str(dummy_edit_report_txt)})
    master_hook_zip = Path((release_with_master_and_hook.get("data") or {}).get("zip_path", ""))
    with zipfile.ZipFile(master_hook_zip) as archive:
        master_hook_names = set(archive.namelist())
    assert_true({"remaster/mastered_wav.wav", "remaster/mastered_mp3.mp3", "audio_editor/hook.mp3", "audio_editor/edit_report.json"}.issubset(master_hook_names), "release pack did not include master and hook outputs together")
    diversity_memory_path = out / "diversity_memory.json"
    saved_diversity_memory = save_diversity_memory(
        {
            "recent_titles": ["พักใจก่อน", "ใจยังไม่เลิกงาน", "คืนนี้ขอพัก"],
            "recent_hooks": ["นาฬิกาเลิกงาน แต่ใจยังไม่เลิกเหนื่อย\nเหนื่อยไหม\nพรุ่งนี้ค่อยว่ากัน"],
            "recent_opening_lines": ["นาฬิกาเลิกงาน แต่ใจยังไม่เลิกเหนื่อย"],
            "recent_story_types": ["Office Burnout"] * 8,
            "recent_phrases": ["เหนื่อยไหม", "ไม่เป็นไรนะ", "พรุ่งนี้ค่อยว่ากัน", "ถึงบ้านบอกด้วย", "มีบางอย่างในใจที่ยังไม่กล้าตอบ"],
        },
        diversity_memory_path,
    )
    loaded_diversity_memory = load_diversity_memory(diversity_memory_path)
    assert_true(loaded_diversity_memory["recent_titles"] == saved_diversity_memory["recent_titles"], "diversity memory file save/load failed")
    assert_true(all(key in loaded_diversity_memory for key in ["recent_specific_situations", "recent_main_objects", "recent_bridge_truths", "recent_final_payoff_lines"]), "diversity memory missing situation-first tracking keys")
    assert_true(score_title_novelty("พักใจก่อน", loaded_diversity_memory) < score_title_novelty("โต๊ะตัวเดิม", loaded_diversity_memory), "repeated titles were not penalized")
    assert_true(score_hook_novelty("นาฬิกาเลิกงาน แต่ใจยังไม่เลิกเหนื่อย\nเหนื่อยไหม\nพรุ่งนี้ค่อยว่ากัน", loaded_diversity_memory) < score_hook_novelty("แสงหน้าบ้านยังรอ\nให้ฉันวางวันที่หนักไว้\nคืนนี้แค่กลับไปเป็นคนธรรมดา", loaded_diversity_memory), "repeated hooks were not penalized")
    assert_true(score_phrase_novelty("เหนื่อยไหม\nไม่เป็นไรนะ\nพรุ่งนี้ค่อยว่ากัน", loaded_diversity_memory) < score_phrase_novelty("แสงหน้าบ้านยังเปิดรอ\nมือแม่ยังเก็บข้าวไว้\nคืนนี้ฉันอยากกลับไปพักจริง ๆ", loaded_diversity_memory), "repeated phrases were not penalized")
    diversity_report = build_diversity_report("พักใจก่อน", "นาฬิกาเลิกงาน แต่ใจยังไม่เลิกเหนื่อย", "เหนื่อยไหม\nพรุ่งนี้ค่อยว่ากัน", "Office Burnout", loaded_diversity_memory)
    assert_true("Overall Diversity Score" in diversity_report and diversity_report["Overall Diversity Score"] < 80, "diversity report scoring failed repeated content")
    assert_true("Diversity Report" in release_pack["pack"] and "Overall Diversity Score:" in release_pack["pack"]["Diversity Report"] and "DIVERSITY REPORT" in release_txt, "DIVERSITY REPORT missing from release pack")
    situation_seed = generate_situation_first_seed("เห็นเขาออนไลน์แต่ไม่ตอบเรา", "Vela Moon Emotional Pop Rock")
    assert_true("ออนไลน์" in situation_seed["Specific Situation"] and int(situation_seed["Specificity Score"]) >= 85, "Situation-First seed failed to extract a specific modern situation")
    assert_true(situation_seed["Scene Type"] != "office_life" and situation_seed["Main Object"], "Situation-First seed fell back to generic office/default data")
    situation_pack = generate_creative_release_pack("เห็นเขาออนไลน์แต่ไม่ตอบเรา", "Vela Moon Emotional Pop Rock", "Vela Moon")
    situation_report = situation_pack["pack"].get("Situation Specificity Report", "")
    situation_text = creative_release_pack_to_text(situation_pack)
    situation_quality = situation_pack["quality_report"].get("situation_first", {})
    situation_lyrics = situation_pack["pack"]["SUNO LYRICS FIELD"]
    situation_needles = [
        str(situation_quality.get("Main Object", "")),
        str(situation_quality.get("Modern Object", "")),
        str(situation_quality.get("Location", "")),
        str(situation_quality.get("Action", "")),
    ]
    assert_true("Specific Situation:" in situation_report and "Bridge Truth:" in situation_report and "Specificity Score:" in situation_report, "Situation Specificity Report missing required fields")
    assert_true("SITUATION SPECIFICITY REPORT" in situation_text and "Situation Specificity Report" in situation_pack["pack"], "Situation Specificity Report missing from release pack text")
    assert_true(any(item and item in situation_lyrics for item in situation_needles), "Situation-First seed did not influence lyrics")
    situation_target_listener = next((line for line in situation_pack["pack"]["Producer Brief"].splitlines() if line.startswith("Target Listener:")), "")
    assert_true("Specific Situation:" in situation_pack["pack"]["Producer Brief"] and "office workers" not in situation_target_listener.lower(), "Producer Brief was not derived from the specific situation")
    assert_true("Situation Score:" in situation_report and "Situation Objects:" in situation_report and "Specificity Score:" in situation_report, "Situation Lock V2 report missing score/object fields")
    situation_v2_cases = [
        "Read but not reply",
        "Old photo notification",
        "Boss says one more revision",
        "Waiting for someone who never replies",
        "เห็นเขาออนไลน์แต่ไม่ตอบเรา",
        "รูปเก่าเด้งขึ้นมาในโทรศัพท์ทุกปี",
        "หัวหน้าบอกแก้อีกนิด แต่กลายเป็นทั้งคืน",
        "เพื่อนยังอยู่ในกลุ่มไลน์ แต่ไม่เคยคุยกันแล้ว",
        "เงินเดือนออก แต่ใจยังว่างเปล่า",
        "พิมพ์แล้วลบ เพราะรู้ว่าเขาไม่อยากตอบ",
    ]
    verse_1_fingerprints: set[str] = set()
    for case in situation_v2_cases:
        case_pack = generate_creative_release_pack(case, "Vela Moon Emotional Pop Rock", "Vela Moon")
        case_lyrics = case_pack["pack"]["SUNO LYRICS FIELD"]
        case_seed = case_pack["quality_report"]["situation_first"]
        case_report = case_pack["pack"]["Situation Specificity Report"]
        case_sections = parse_lyric_sections(case_lyrics)
        case_objects = [item.strip() for item in str(case_report.split("Situation Objects:", 1)[1].splitlines()[0]).split(",") if item.strip()]
        verse_1 = "\n".join(case_sections.get("Verse 1", []))
        verse_2 = "\n".join(case_sections.get("Verse 2", []))
        thai_objects = [item for item in case_objects if not re.search(r"[A-Za-z]", item)]
        assert_true(int(case_seed.get("Specificity Score", 0)) >= 85 and int(case_seed.get("Situation Score", 0)) >= 70, f"Situation Lock V2 score too low for {case}")
        combined_verses = "\n".join([verse_1, verse_2])
        assert_true(any(obj in combined_verses for obj in thai_objects) or (verse_1.strip() and verse_2.strip()), f"Verse object lock failed for {case}")
        verse_1_fingerprints.add(_compact_line(verse_1)[:80])
    assert_true(len(verse_1_fingerprints) >= 5, "Situation Lock V2 generated indistinguishable Verse 1 openings")
    assert_true(release_pack["provider_status"]["status"] == "Offline Demo Mode" and "Demo / Offline Preview" in release_txt, "offline release pack is not clearly labeled as demo preview")
    assert_true("No video rendering" in release_pack["pack"]["Release notes"] and "PRODUCER NOTES" in release_txt and "Music style prompt for Suno/Udio" not in release_txt and "Suno Copy-Ready Block" not in release_txt, "creative release pack copy-ready text cleanup missing")
    assert_true("Weirdness:" in release_txt and "Style Influence:" in release_txt and "BPM:" in release_txt, "advanced Suno settings missing from release pack")
    assert_true("SUNO LYRICS FIELD" in release_txt and "SUNO STYLE OF MUSIC FIELD" in release_txt and release_pack["pack"]["SUNO LYRICS FIELD"].strip(), "Suno copy-ready fields missing")
    with zipfile.ZipFile(release_zip, "r") as release_archive:
        release_zip_names = set(release_archive.namelist())
        advanced_settings_zip_text = release_archive.read("advanced_suno_settings.txt").decode("utf-8-sig")
        lyrics_only_zip_text = release_archive.read("lyrics_only.txt").decode("utf-8-sig")
        suno_style_zip_text = release_archive.read("suno_style_prompt.txt").decode("utf-8-sig")
        producer_notes_zip_text = release_archive.read("producer_notes.txt").decode("utf-8-sig")
        clean_release_pack_zip_text = release_archive.read("release_pack.txt").decode("utf-8-sig")
    assert_true({"lyrics_only.txt", "suno_style_prompt.txt", "producer_notes.txt", "release_pack.txt", "advanced_suno_settings.txt", "lyrics_quality_report.txt", "diversity_report.txt", "situation_specificity_report.txt"}.issubset(release_zip_names), "release ZIP missing copy-ready Suno files")
    assert_true("Weirdness:" in advanced_settings_zip_text and "Style Influence:" in advanced_settings_zip_text and "[Verse 1]" in lyrics_only_zip_text and "CORE GENRE" not in suno_style_zip_text and "VOCAL DIRECTION" not in suno_style_zip_text and "CORE GENRE" in producer_notes_zip_text, "release ZIP copy-ready Suno content failed")
    assert_true(clean_release_pack_zip_text.count("[Verse 1]") == 1 and clean_release_pack_zip_text.count("PRODUCER NOTES") == 1, "release_pack.txt duplicated lyrics or producer notes")
    lyric_lower = release_pack["pack"]["Full lyrics"].lower()
    lyric_field_lower = release_pack["pack"]["SUNO LYRICS FIELD"].lower()
    hook_lower = release_pack["pack"]["Hook"].lower()
    release_quality = release_pack["quality_report"]["export_quality"]
    lyrics_quality = release_pack["quality_report"]["lyrics_quality_engine"]
    assert_true(release_quality["ok"] and not release_quality["duplicated_sections"] and not release_quality["meta_text_inside_lyrics"] and not release_quality["too_short_lyrics"], "creative release pack export quality gate failed")
    assert_true(release_quality["lyrics_line_stats"]["line_count"] >= 24 and release_quality["lyrics_line_stats"]["repeated_lines"] <= 8 and release_quality["final_chorus_has_payoff"], "creative release pack lyrics are too short, repetitive, or lack final payoff")
    assert_true(all(key in lyrics_quality["scores"] for key in ["Hook Score", "Emotional Score", "Commercial Score", "Repetition Score", "Singability Score"]), "lyrics quality engine scores missing")
    assert_true(lyrics_quality["copy_ready_for_suno"] and lyrics_quality["overall_score"] >= 60 and lyrics_quality["repeated_lines"] <= 6 and not lyrics_quality["weak_chorus"], f"lyrics quality engine failed copy-ready gate: {lyrics_quality}")
    assert_true("Lyrics Quality Engine" in release_pack["pack"]["Lyrics Quality Report"] and "LYRICS QUALITY REPORT" in release_txt, "lyrics quality report missing from release pack")
    forbidden_lyric_prompts = ["hook direction", "mood:", "lyrics direction:", "comforting emotional hook", "spotify-friendly", "tiktok hook friendly", "dynamic chorus lift", "easy to remember on tiktok"]
    assert_true(not any(item in lyric_lower for item in forbidden_lyric_prompts), "internal prompt text leaked into full lyrics")
    assert_true(not any(item in hook_lower for item in forbidden_lyric_prompts) and not any(item in lyric_field_lower for item in forbidden_lyric_prompts), "internal prompt text leaked into hook or Suno lyrics field")
    assert_true("เน€เธ" not in release_pack["pack"]["Hook"] and "เน€เธ" not in release_pack["pack"]["SUNO LYRICS FIELD"], "mojibake Thai text leaked into hook or Suno lyrics")
    love_release_pack = generate_creative_release_pack("เพลงรัก", "Vela Moon Emotional Pop Rock", "Vela Moon")
    love_pack = love_release_pack["pack"]
    love_hook_lines = [line for line in love_pack["Hook"].splitlines() if line.strip()]
    assert_true(love_pack["Suggested title"] not in {"รัก", "ความรัก", "เพลงรัก"} and len(love_hook_lines) >= 2, "creative pack generic title/hook quality failed")
    assert_true(len(love_hook_lines) <= 5 and "ให้ท่อนนี้" not in love_pack["Hook"] and "ร้องให้สุด" not in love_pack["Hook"], "creative pack hook contains meta text")
    assert_true(love_release_pack["quality_report"]["selected_title_score"]["score"] >= 60 and love_release_pack["quality_report"]["selected_hook_score"]["score"] >= 60, "creative pack quality report scoring failed")
    assert_true(3 <= len(love_hook_lines) <= 5 and love_release_pack["quality_report"]["export_quality"]["hook_is_copy_ready"], "creative pack hook is not singable/copy-ready")
    story_candidates = generate_story_candidates_v2("เพลงเศร้าในออฟฟิศ", "Office Burnout", mood="Bittersweet", story_type="Office Burnout")
    assert_true(len(story_candidates) == 5 and all(item.get("objects") and item.get("scenes") for item in story_candidates), "Music V2 story candidates failed")
    hook_candidates = generate_hook_candidates_v2("เพลงเศร้าในออฟฟิศ", story_candidates[0], "Office Burnout")
    assert_true(len(hook_candidates) == 5 and all(3 <= len(item.get("lines", [])) <= 5 for item in hook_candidates), "Music V2 hook candidates failed")
    title_candidates = generate_title_candidates_v2("เพลงเศร้าในออฟฟิศ", story_candidates[0], hook_candidates[0]["hook"], "Office Burnout")
    assert_true(len(title_candidates) == 5 and all(item.get("title") for item in title_candidates), "Music V2 title candidates failed")
    seed_bundle = generate_music_seed_candidates_v2("เพลงเศร้าในออฟฟิศ", "Office Burnout", mood="Bittersweet", story_type="Office Burnout")
    assert_true(len(seed_bundle["story_candidates"]) == 5 and len(seed_bundle["hook_candidates"]) == 5 and len(seed_bundle["title_candidates"]) == 5, "Music V2 seed bundle count failed")
    candidate_lock_cases = [
        ("รถคันแรกพัง", ["รถ", "กุญแจ", "เครื่องยนต์", "ถนน"]),
        ("แม่โทรมาตอนตีสอง", ["แม่", "โทร", "ตีสอง", "สาย", "โทรศัพท์"]),
        ("หมาที่เลี้ยงมา 12 ปีจากไป", ["หมา", "ปลอกคอ", "ชาม", "ประตู", "บ้าน"]),
        ("พ่อแก่ลงทุกปี", ["พ่อ", "มือ", "แก้วน้ำ", "โต๊ะกินข้าว", "เดินช้า"]),
    ]
    generic_bad_titles = {"พูดเบา ๆ แต่โดนใจ", "ความจริงเบา ๆ", "บอกตรง ๆ ได้ไหม", "คำที่ถนอม"}
    for lock_idea, required_terms in candidate_lock_cases:
        locked_bundle = generate_music_seed_candidates_v2(lock_idea, "Vela Moon Emotional Pop Rock")
        locked_story = locked_bundle["story_candidates"][0]
        locked_hook = locked_bundle["hook_candidates"][0]["hook"]
        locked_title = locked_bundle["title_candidates"][0]["title"]
        locked_story_text = "\n".join([str(locked_story.get("label", "")), str(locked_story.get("story_angle", "")), " ".join(locked_story.get("objects", []) or []), " ".join(locked_story.get("scenes", []) or [])])
        locked_combined = "\n".join([locked_story_text, locked_hook, locked_title])
        assert_true(any(term in locked_combined for term in required_terms), f"candidate lock failed for {lock_idea}")
        assert_true(locked_title not in generic_bad_titles and not any(bad in locked_hook for bad in generic_bad_titles), f"generic title/hook passed candidate lock for {lock_idea}")
        relevance = validate_selected_seed_relevance(
            lock_idea,
            {
                "story": locked_story,
                "hook": locked_hook,
                "title": locked_title,
                "producer_brief": locked_bundle["producer_brief"],
                "situation_first_seed": locked_bundle["situation_first_seed"],
            },
            "Vela Moon Emotional Pop Rock",
        )
        assert_true(relevance["ok"], f"selected seed relevance gate rejected a user-idea candidate for {lock_idea}: {relevance}")
        memory_pack = generate_creative_release_pack(lock_idea, "Vela Moon Emotional Pop Rock", "Vela Moon")
        memory_sections = parse_lyric_sections(memory_pack["pack"]["SUNO LYRICS FIELD"])
        memory_opening = "\n".join(memory_sections.get("Verse 1", [])[:4])
        assert_true(any(term in memory_opening for term in required_terms), f"Human Memory Engine did not place object memory in Verse 1 for {lock_idea}")
        assert_true(any(term in memory_opening for term in ["โต๊ะ", "บ้าน", "ประตู", "โรงรถ", "ห้อง", "ถนน", "หน้าจอ", "รถ", "อู่"]), f"Human Memory Engine did not place location in Verse 1 for {lock_idea}")
        assert_true(any(term in memory_opening for term in ["วาง", "ยื่น", "ตัก", "รอ", "เดิน", "วน", "บิด", "สตาร์ท", "รับ", "โทร", "มอง", "เปิด", "ปิด", "หยิบ", "จับ"]), f"Human Memory Engine did not place physical action in Verse 1 for {lock_idea}")
        abstract_opening_terms = ["เวลา", "ความทรงจำ", "เรื่องราว", "ชีวิต", "หัวใจ", "ความรู้สึก", "วันวาน", "ความคิดถึง"]
        assert_true(sum(1 for term in abstract_opening_terms if term in "\n".join(memory_sections.get("Verse 1", [])[:2])) <= 1, f"Verse 1 still opens like emotional summary for {lock_idea}")
        assert_true(memory_pack["quality_report"]["lyrics_quality_engine"]["scores"].get("Human Memory Score", 0) >= 85, f"Human Memory Score too low for {lock_idea}")
        assert_true(memory_pack["quality_report"].get("human_memory_engine", {}).get("Human Memory Score", 0) >= 85, f"Human Memory Engine report missing or low for {lock_idea}")
        verse_2_text = "\n".join(memory_sections.get("Verse 2", []))
        bridge_text = "\n".join(memory_sections.get("Bridge", []))
        final_chorus_text = "\n".join(memory_sections.get("Final Chorus", []))
        escalation_report = memory_pack["quality_report"].get("emotional_escalation_engine", {})
        quality_scores = memory_pack["quality_report"]["lyrics_quality_engine"]["scores"]
        assert_true(escalation_report.get("Narrative Progression Score", 0) >= 85, f"Narrative Progression Score too low for {lock_idea}: {escalation_report}")
        assert_true(quality_scores.get("Narrative Progression Score", 0) >= 85, f"Lyrics quality report missing narrative progression for {lock_idea}")
        assert_true(quality_scores.get("Memory Score", 0) >= 85, f"Lyrics quality report missing memory score for {lock_idea}")
        assert_true(quality_scores.get("Situation Alignment Score", 0) >= 70, f"Lyrics quality report missing situation alignment for {lock_idea}")
        assert_true(verse_2_text and bridge_text and final_chorus_text, f"Narrative progression sections missing for {lock_idea}")
        assert_true(verse_2_text != bridge_text and bridge_text != final_chorus_text and verse_2_text != final_chorus_text, f"Narrative sections repeat the same emotional point for {lock_idea}")
        assert_true(set(escalation_report.get("rewrote_sections", [])) >= {"Verse 2", "Bridge", "Final Chorus"}, f"Emotional Escalation Engine did not enforce change/truth/payoff for {lock_idea}: {escalation_report}")
        human_language_report = memory_pack["quality_report"].get("human_language_engine", {})
        assert_true(quality_scores.get("ShowDontTellScore", 0) >= 85, f"ShowDontTellScore missing or low for {lock_idea}: {quality_scores}")
        assert_true(quality_scores.get("MemoryDensityScore", 0) >= 85, f"MemoryDensityScore missing or low for {lock_idea}: {quality_scores}")
        assert_true(human_language_report.get("ShowDontTellScore", 0) >= 85 and human_language_report.get("MemoryDensityScore", 0) >= 85, f"Human Language Engine report missing or low for {lock_idea}: {human_language_report}")
        assert_true(human_language_report.get("Emotion Explanation Count", 99) <= 2, f"Human Language Engine left too many direct emotion explanations for {lock_idea}: {human_language_report}")
    bad_seed = {
        "story": {"label": "พิมพ์แล้วลบ เพราะรู้ว่าเขาไม่อยากตอบ", "story_angle": "chat silence", "objects": ["แชต", "อ่านแล้ว"], "scenes": ["หน้าจอโทรศัพท์"]},
        "hook": "บอกตรง ๆ ได้ไหม\nแต่อย่าให้คำมันผลักเราไกล",
        "title": "ความจริงเบา ๆ",
    }
    bad_relevance = validate_selected_seed_relevance("หมาที่เลี้ยงมา 12 ปีจากไป", bad_seed, "Vela Moon Emotional Pop Rock")
    assert_true(not bad_relevance["ok"], "unrelated old story seed was not rejected")
    assert_true(seed_bundle.get("producer_brief") and seed_bundle["producer_brief"].get("Target Listener") and seed_bundle["producer_brief"].get("Shareable Angle"), "Producer Engine V1 brief missing")
    assert_true(all(item.get("human_experiences") for item in seed_bundle["story_candidates"]), "Producer Engine V1 human experience seeds missing")
    hook_candidate_text = "\n".join(item["hook"] for item in seed_bundle["hook_candidates"])
    assert_true("นาฬิกาเลิกงาน" in hook_candidate_text or "เลิกงานแล้ว" in hook_candidate_text, "Producer Brief caption/shareable line did not enter hook candidates")
    assert_true(_score_hook_candidate("นาฬิกาเลิกงาน\nแต่ใจยังไม่เลิกเหนื่อย\nยิ้มมาทั้งวันจนลืมว่าข้างใน\nแค่อยากมีคืนหนึ่งที่ไม่ต้องไหว")["score"] > _score_hook_candidate("ทำไมโต๊ะเดิมถึงดูไกล\nงานไม่เคยพูดว่ารักกัน\nปลายทางว่างเปล่า\nใต้เงาของหัวใจ")["score"], "Hook Engine V2 did not prefer caption-like hook over abstract poetic hook")
    assert_true(not re.search(r"[A-Za-z]", seed_bundle["title_candidates"][0]["title"]) and seed_bundle["title_candidates"][0]["title"] not in {"รัก", "คิดถึง", "เหนื่อย", "ไม่ไหว", "ลืมไม่ลง", "เลิกงานแล้วยังเหนื่อย"}, "Title Engine V3 selected weak, literal, or English title")
    selected_seed = {
        "story": seed_bundle["story_candidates"][0],
        "hook": seed_bundle["hook_candidates"][0]["hook"],
        "title": seed_bundle["title_candidates"][0]["title"],
        "producer_brief": seed_bundle["producer_brief"],
    }
    seeded_pack = generate_creative_release_pack(
        "เพลงเศร้าในออฟฟิศ",
        "Office Burnout",
        "Vela Moon",
        creative_controls={"selected_seed": selected_seed, "story_type": "Office Burnout", "hook_style": "Question"},
    )
    seeded_lyrics = seeded_pack["pack"]["SUNO LYRICS FIELD"]
    seeded_hook_lines = [line for line in selected_seed["hook"].splitlines() if line.strip()]
    seeded_chorus = seeded_lyrics.split("[Chorus]", 1)[1].split("[Verse 2]", 1)[0]
    seeded_final_chorus = seeded_lyrics.split("[Final Chorus]", 1)[1].split("[Outro]", 1)[0]
    assert_true(all(line in seeded_chorus for line in seeded_hook_lines) and all(line in seeded_final_chorus for line in seeded_hook_lines), "selected hook was not preserved in chorus and final chorus")
    assert_true("Producer Brief" in seeded_pack["pack"] and "Target Listener:" in seeded_pack["pack"]["Producer Brief"], "release pack missing Producer Brief")
    assert_true("Starting Emotion:" in seeded_pack["pack"]["Producer Brief"] and "Final Payoff Line:" in seeded_pack["pack"]["Producer Brief"], "Producer Brief missing emotional arc fields")
    assert_true("Selected Story:" in seeded_pack["pack"]["Selected Seed Summary"] and "Selected Objects:" in seeded_pack["pack"]["Selected Seed Summary"], "release pack missing selected seed summary")
    assert_true(not any(item in seeded_lyrics.lower() for item in forbidden_lyric_prompts), "selected seed metadata leaked into Suno lyrics")
    seeded_text = creative_release_pack_to_text(seeded_pack)
    assert_true("Selected Seed Summary:" in seeded_text and "PRODUCER BRIEF" in seeded_text and "SUNO LYRICS FIELD" in seeded_text, "selected seed summary or producer brief missing from release pack text")
    authority_seed = {
        "story": {
            "label": "โต๊ะตัวเดิม",
            "story_angle": "A person faces being left alone after pretending to be fine at the same office desk.",
            "objects": ["coffee cup", "keyboard", "parking card"],
            "scenes": ["morning desk", "empty meeting room", "parking lot after work"],
            "emotional_arc": "alone -> collapse -> honest acceptance",
            "recommended_hook_direction": "question hook about having no one left",
        },
        "hook": "สุดท้ายไม่เหลือใคร\nโต๊ะตัวเดิมยังมองฉันอยู่\nยิ่งยิ้มเหมือนไหวเท่าไร\nข้างในยิ่งว่างเปล่า",
        "title": "โต๊ะตัวเดิม",
    }
    authority_pack = generate_creative_release_pack(
        "สุดท้ายไม่เหลือใคร",
        "Office Burnout",
        "Vela Moon",
        creative_controls={"selected_seed": authority_seed, "story_type": "Office Burnout", "hook_style": "Question"},
    )
    assert_true(not authority_pack.get("ok") and authority_pack.get("error") == "seed_relevance_failed", "unrelated selected seed should block final release export")
    english_title_seed = dict(authority_seed)
    english_title_seed["title"] = "coffee cup"
    english_title_pack = generate_creative_release_pack(
        "สุดท้ายไม่เหลือใคร",
        "Office Burnout",
        "Vela Moon",
        creative_controls={"selected_seed": english_title_seed, "story_type": "Office Burnout", "hook_style": "Question"},
    )
    assert_true(not english_title_pack.get("ok") and english_title_pack.get("error") == "seed_relevance_failed", "English/unrelated selected seed title should block final release export")
    advanced_controls_pack = generate_creative_release_pack(
        "พนักงานดีเด่น",
        "Vela Moon Emotional Pop Rock",
        "Vela Moon",
        creative_controls={
            "genre": "Thai Emotional Pop Rock",
            "mood": "Bittersweet",
            "story_type": "Office Burnout",
            "hook_style": "Question",
            "vocal_direction": "Thai male vocal, tired but honest office-worker tone",
            "style_influence": 73,
            "weirdness": 21,
            "commercial_direction": "quality-first Thai office-life pop rock, memorable social-caption hook",
        },
    )
    advanced_pack = advanced_controls_pack["pack"]
    advanced_lyrics = advanced_pack["SUNO LYRICS FIELD"]
    advanced_situation = advanced_controls_pack["quality_report"].get("situation_first", {})
    assert_true("ยิ้มทั้งวันแบบนี้เรียกว่าไหวไหม" not in advanced_pack["Hook"] and len([line for line in advanced_pack["Hook"].splitlines() if line.strip()]) >= 3, "question hook style reused a banned global starter hook")
    assert_true(any(obj and obj in advanced_lyrics for obj in [advanced_situation.get("Main Object"), advanced_situation.get("Modern Object")]) and "Style Influence: 73%" in advanced_pack["Advanced Suno Settings"] and "Weirdness: 21%" in advanced_pack["Advanced Suno Settings"], "advanced Song Studio controls did not influence lyrics/settings")
    assert_true(not any(line.strip().isdigit() for line in advanced_lyrics.splitlines()) and not re.search(r"\s(?:13|19)$", advanced_lyrics, re.MULTILINE), "numeric lyric artifacts were not removed")
    advanced_bridge = advanced_lyrics.split("[Bridge]", 1)[1].split("[Final Chorus]", 1)[0]
    advanced_non_chorus = re.sub(r"\[Chorus\].*?\[Verse 2\]", "[Verse 2]", advanced_lyrics, flags=re.S)
    assert_true("Human Experience Report" in advanced_pack and "Relatability Score:" in advanced_pack["Human Experience Report"], "Human Experience Report missing from release pack")
    assert_true("Emotional Arc Report" in advanced_pack and "Arc Score:" in advanced_pack["Emotional Arc Report"], "Emotional Arc Report missing from release pack")
    assert_true("Thai Natural Speech Report" in advanced_pack and "Human Speech Score:" in advanced_pack["Thai Natural Speech Report"], "Thai Natural Speech Report missing from release pack")
    assert_true("Caption Score:" in advanced_pack["Thai Natural Speech Report"], "Caption Score missing from Thai Natural Speech Report")
    assert_true("Relatability Report" in advanced_pack and "Relatability Score:" in advanced_pack["Relatability Report"], "Relatability Report missing from release pack")
    assert_true("Most Relatable Line:" in advanced_pack["Relatability Report"] and "Best Caption Line:" in advanced_pack["Relatability Report"] and "Best TikTok Line:" in advanced_pack["Relatability Report"], "Relatability Report missing line selections")
    assert_true("Top Captions:" in advanced_pack["Relatability Report"] and "1." in advanced_pack["Relatability Report"] and "2." in advanced_pack["Relatability Report"] and "3." in advanced_pack["Relatability Report"], "Relatability Report missing top captions")
    assert_true("Human Relatability Score:" in advanced_pack["Lyrics Quality Report"], "Human Relatability Score missing from lyrics quality report")
    assert_true("Emotional Arc Score:" in advanced_pack["Lyrics Quality Report"], "Emotional Arc Score missing from lyrics quality report")
    assert_true("Thai Naturalness Score:" in advanced_pack["Lyrics Quality Report"], "Thai Naturalness Score missing from lyrics quality report")
    assert_true("Relatability Score:" in advanced_pack["Lyrics Quality Report"], "Relatability Score missing from lyrics quality report")
    critic_report = advanced_controls_pack["quality_report"].get("critic_engine", {})
    rewrite_report = advanced_controls_pack["quality_report"].get("rewrite_engine", {})
    commercial_report = advanced_controls_pack["quality_report"].get("commercial_score_engine", {})
    authenticity_v2 = advanced_controls_pack["quality_report"].get("human_lyric_authenticity_v2", {})
    assert_true({"Hook Strength", "Title Quality", "Chorus Quality", "Emotional Arc", "Relatability"}.issubset((critic_report.get("scores") or {}).keys()), "Critic Engine report missing required score dimensions")
    assert_true(isinstance(rewrite_report.get("actions"), list) and rewrite_report.get("after", {}).get("overall", 0) >= rewrite_report.get("before", {}).get("overall", 0), "Rewrite Engine did not keep best version")
    assert_true({"Commercial Potential", "TikTok Potential", "Caption Potential", "Singability", "Emotional Impact", "Overall Commercial Score"}.issubset(commercial_report.keys()), "Commercial Score Engine missing required dimensions")
    assert_true(0 <= commercial_report.get("Overall Commercial Score", -1) <= 100, "Commercial Score Engine overall score out of range")
    lyrics_without_tags = re.sub(r"\[[^\]]+\]", "", advanced_lyrics)
    assert_true(not re.search(r"[A-Za-z]{3,}", lyrics_without_tags), "English scene/object leakage remained in SUNO lyrics")
    assert_true(not any(term in advanced_lyrics.lower() for term in ["quiet room", "rainy window", "open notebook"]), "known English scene leakage remained in lyrics")
    advanced_situation_report = advanced_pack.get("Situation Specificity Report", "")
    assert_true("Situation Score:" in advanced_situation_report and int(advanced_situation.get("Situation Score", 0)) >= 70, "Situation Lock did not dominate lyric direction")
    assert_true(any(obj and obj in advanced_lyrics for obj in [advanced_situation.get("Main Object"), advanced_situation.get("Modern Object")]), "Situation object did not influence lyrics")
    assert_true(not any(line in advanced_lyrics for line in ["เหนื่อยไหม", "ไม่เป็นไรนะ", "โต๊ะตัวเดิม", "รถคันเดิม", "คืนนี้เรานั่งเงียบกัน", "พรุ่งนี้ค่อยว่ากัน", "ถึงบ้านบอกด้วย"]), "unrelated generic phrase library leaked into lyrics")
    emergency_quality_ideas = [
        ("หมาที่เลี้ยงมา 12 ปีจากไป", ["ประตู", "ปลอกคอ", "วิ่ง", "ชาม"], ["อ่านแล้ว", "พิมพ์แล้วลบ", "แชต", "ออนไลน์"]),
        ("พ่อแก่ลงทุกปี", ["พ่อ", "มือ", "แก้วน้ำ", "โต๊ะกินข้าว"], ["อ่านแล้ว", "แชต", "ออนไลน์", "ปลอกคอ"]),
        ("แอบชอบเพื่อนสนิท", ["เพื่อน", "แก้วน้ำ", "ร้านข้าว", "ความลับ"], ["ปลอกคอ", "รถคันแรก", "ชุดครุย"]),
        ("อ่านแล้วไม่ตอบ", ["อ่านแล้ว", "แชต", "ออนไลน์", "ข้อความ"], ["ปลอกคอ", "พ่อ", "รถคันแรก"]),
        ("รูปเก่าเด้งขึ้นมา", ["รูป", "ปีก่อน", "อัลบั้ม", "หน้าจอ"], ["ปลอกคอ", "รถคันแรก", "กลุ่มไลน์"]),
        ("เพื่อนหายจากกลุ่มไลน์", ["กลุ่มไลน์", "เพื่อน", "สติ๊กเกอร์", "ทริป"], ["ปลอกคอ", "พ่อ", "ชุดครุย"]),
        ("รถคันแรกพัง", ["รถ", "กุญแจ", "เครื่องยนต์", "ข้างทาง"], ["อ่านแล้ว", "กลุ่มไลน์", "ปลอกคอ"]),
        ("ย้ายออกจากบ้าน", ["บ้าน", "กล่อง", "ประตู", "ห้อง"], ["อ่านแล้ว", "รถคันแรก", "ชุดครุย"]),
        ("ฝนตกวันรับปริญญา", ["ฝน", "ชุดครุย", "รับปริญญา", "มหาวิทยาลัย"], ["อ่านแล้ว", "ปลอกคอ", "กลุ่มไลน์"]),
        ("โทรศัพท์พังแต่รูปยังอยู่", ["โทรศัพท์", "รูป", "ร้านซ่อม", "หน้าจอ"], ["ปลอกคอ", "พ่อ", "รถคันแรก"]),
    ]
    banned_template_lines = [
        "ยิ้มทั้งวันแบบนี้เรียกว่าไหวไหม",
        "พรุ่งนี้ค่อยกลับไปเป็นคนเก่งอีกครั้ง",
        "คืนนี้ขอให้ใจเบาลง",
        "ไม่ได้ลืม แค่ไม่อยากรอแล้ว",
        "เงียบกว่าที่คิด",
        "ไม่รู้จะทักหาใคร",
    ]
    emergency_titles: set[str] = set()
    emergency_hook_openings: set[str] = set()
    emergency_verse_fingerprints: set[str] = set()
    for idea_text, expected_terms, forbidden_terms in emergency_quality_ideas:
        emergency_pack = generate_creative_release_pack(idea_text, "Vela Moon Emotional Pop Rock", "Vela Moon")
        emergency_data = emergency_pack["pack"]
        emergency_lyrics = emergency_data["SUNO LYRICS FIELD"]
        emergency_hook_first = next((line.strip() for line in emergency_data["Hook"].splitlines() if line.strip()), "")
        emergency_sections = parse_lyric_sections(emergency_lyrics)
        verse_one = "\n".join(emergency_sections.get("Verse 1", []))
        verse_two = "\n".join(emergency_sections.get("Verse 2", []))
        bridge = "\n".join(emergency_sections.get("Bridge", []))
        final_chorus = "\n".join(emergency_sections.get("Final Chorus", []))
        combined_story_text = "\n".join([emergency_lyrics, emergency_data.get("Caption", ""), emergency_data.get("Cover prompt", ""), emergency_data.get("MV storyboard prompt", "")])
        assert_true(emergency_hook_first and emergency_hook_first not in emergency_hook_openings, f"repeated hook opening for idea: {idea_text}")
        assert_true(emergency_data["Suggested title"] not in emergency_titles, f"repeated title pattern for idea: {idea_text}")
        assert_true(not any(banned in combined_story_text for banned in banned_template_lines), f"phrase-library contamination for idea: {idea_text}")
        assert_true(any(term in combined_story_text for term in expected_terms), f"story lock missing expected situation terms for idea: {idea_text}")
        assert_true(not any(term in emergency_lyrics for term in forbidden_terms), f"unrelated story leakage for idea: {idea_text}")
        assert_true(verse_one and verse_two and bridge and final_chorus, f"missing required lyric sections for idea: {idea_text}")
        emergency_titles.add(emergency_data["Suggested title"])
        emergency_hook_openings.add(emergency_hook_first)
        emergency_verse_fingerprints.add(_compact_line(verse_one)[:80])
    assert_true(len(emergency_verse_fingerprints) >= 9, "emergency story-lock songs were not clearly distinguishable")
    situation_title_hook_cases = [
        ("พ่อแก่ลงทุกปี", ["พ่อ", "มือ", "แก้วน้ำ", "โต๊ะ"], ["พูดเบา", "ความจริง", "บอกตรง"]),
        ("หมาที่เลี้ยงมา 12 ปีจากไป", ["ประตู", "ปลอกคอ", "ชาม", "หมา"], ["พูดเบา", "ความจริง", "บอกตรง"]),
        ("รถคันแรกพัง", ["รถ", "กุญแจ", "เครื่องยนต์", "คันแรก"], ["พูดเบา", "ความจริง", "บอกตรง"]),
    ]
    for idea_text, expected_terms, forbidden_terms in situation_title_hook_cases:
        locked_pack = generate_creative_release_pack(idea_text, "Vela Moon Emotional Pop Rock", "Vela Moon")
        locked_title = locked_pack["pack"]["Suggested title"]
        locked_hook = locked_pack["pack"]["Hook"]
        locked_summary = locked_pack["pack"]["Hook Quality Summary"]
        title_hook_text = "\n".join([locked_title, locked_hook])
        alignment = locked_pack["quality_report"].get("situation_alignment", {})
        assert_true(any(term in title_hook_text for term in expected_terms), f"situation-locked title/hook missed concrete situation for {idea_text}")
        assert_true(not any(term in title_hook_text for term in forbidden_terms), f"generic emotional title/hook leaked for {idea_text}")
        assert_true(alignment.get("Situation Alignment Score", 0) >= 70 and "Situation Alignment Score:" in locked_summary, f"situation alignment score missing/low for {idea_text}")
        first_two_hook_lines = "\n".join([line for line in locked_hook.splitlines() if line.strip()][:2])
        assert_true(any(term in first_two_hook_lines for term in expected_terms), f"hook did not use situation term in first two lines for {idea_text}")
    dog_blueprint = _story_blueprint_v2("หมาที่เลี้ยงมา 12 ปีจากไป")
    rejected_title, rejected_hook = _enforce_situation_locked_title_hook("ความจริงเบา ๆ", "บอกตรง ๆ ได้ไหม\nแต่อย่าให้คำมันผลักเราไกล", dog_blueprint)
    assert_true("ความจริง" not in rejected_title and any(term in "\n".join([rejected_title, rejected_hook]) for term in ["ปลอกคอ", "ประตู", "หมา", "วิ่ง"]), "situation enforcement did not reject generic title/hook")
    assert_true(sum(advanced_lyrics.count(phrase) for phrase in ["วันนี้เก่งมากแล้ว", "ถ้าคืนนี้ไม่ไหวก็ไม่ต้องฝืน", "ขอให้ฉันกลับมาเป็นฉันอีกครั้ง"]) <= 1, "phrase diversity engine allowed repeated fallback phrases")
    assert_true(advanced_controls_pack["quality_report"]["lyrics_quality_engine"]["scores"].get("Relatability Score", 0) >= 70, "Relatability score collapsed after removing phrase injection")
    assert_true(advanced_controls_pack["quality_report"]["lyrics_quality_engine"]["scores"].get("Thai Naturalness Score", 0) >= 70, "Thai Naturalness score collapsed after removing phrase injection")
    authentic_speech = authenticity_v2.get("authentic_thai_speech") or {}
    assert_true(not authentic_speech.get("english_leakage_lines") and not authentic_speech.get("translated_sounding_lines"), "Authentic Thai Speech Validator found leakage after phrase cleanup")
    assert_true(len([line for line in advanced_bridge.splitlines() if line.strip() and not line.strip().startswith("[")]) >= 2, "Bridge did not produce a hidden-truth section")
    final_chorus_text = advanced_lyrics.split("[Final Chorus]", 1)[1]
    assert_true(any(line.strip() and line.strip() in final_chorus_text for line in advanced_pack["Hook"].splitlines()), "Final Chorus missing selected hook")
    emotional_sections = [
        advanced_lyrics.split("[Verse 1]", 1)[1].split("[Pre-Chorus]", 1)[0],
        advanced_lyrics.split("[Pre-Chorus]", 1)[1].split("[Chorus]", 1)[0],
        advanced_lyrics.split("[Chorus]", 1)[1].split("[Verse 2]", 1)[0],
        advanced_lyrics.split("[Verse 2]", 1)[1].split("[Bridge]", 1)[0],
        advanced_bridge,
    ]
    assert_true(sum("เหนื่อย" in section for section in emotional_sections) < len(emotional_sections), "lyrics repeat the same emotional message in every section")
    assert_true(any(obj and obj in advanced_non_chorus for obj in [advanced_situation.get("Main Object"), advanced_situation.get("Modern Object"), advanced_situation.get("Location")]), "situation-specific detail missing outside chorus")
    assert_true(not any(term in advanced_lyrics for term in ["ไฟล์ Excel", "แก้วกาแฟ", "คีย์บอร์ด", "บัตรจอดรถ"]), "object narration still dominates lyrics")
    natural_sample = "[Verse 1]\nความเหนื่อยล้ากัดกินหัวใจ\nความทรงจำยังตราตรึง\nฉันต้องอดทนต่อไป\n[Chorus]\nนาฬิกาเลิกงาน\nแต่ใจยังไม่เลิกเหนื่อย\nยิ้มมาทั้งวันจนลืมว่าข้างใน\nแค่อยากมีคืนหนึ่งที่ไม่ต้องไหว"
    natural_rewrite, natural_report = _apply_thai_natural_speech_engine(natural_sample, "พนักงานดีเด่น", "Vela Moon Emotional Pop Rock", "นาฬิกาเลิกงาน\nแต่ใจยังไม่เลิกเหนื่อย")
    assert_true(_ai_phrase_count("ความทรงจำยังตราตรึงและกัดกินหัวใจ") >= 2, "AI phrase detection did not count literary phrases")
    assert_true("พรุ่งนี้ค่อยว่ากัน" not in natural_rewrite and "ตราตรึง" not in natural_rewrite, "Thai Natural Speech rewrite layer leaked generic fallback")
    assert_true("นาฬิกาเลิกงาน" in natural_rewrite and "แต่ใจยังไม่เลิกเหนื่อย" in natural_rewrite, "Thai Natural Speech rewrote protected hook")
    assert_true(natural_report["Human Rewrite Count"] >= 2 and natural_report["AI Phrase Count"] == 0, "Thai Natural Speech report did not record rewrites cleanly")
    relatable_report = _relatability_report(advanced_lyrics, advanced_pack["Hook"], "พนักงานดีเด่น", "Vela Moon Emotional Pop Rock")
    assert_true(relatable_report["Relatability Score"] > 0 and len(relatable_report["Top Captions"]) == 3, "Relatability Ranking Engine did not generate scores and top captions")
    assert_true(_score_hook_candidate("ยิ้มได้ ไม่ได้แปลว่าไหว\nไม่อยากลาออก แค่อยากพัก\nวันนี้เก่งมากแล้ว")["score"] > _score_hook_candidate("ความรู้สึกอันลึกซึ้งภายในใจ\nความทรงจำยังตราตรึงมิรู้เลือน")["score"], "Hook ranking did not prefer relatable caption-like hook")
    benchmark_controls = [
        ("กลับบ้านคนเดียว", "Family", "Hope", "บ้าน"),
        ("ขับรถตอนตีสอง", "Night Drive", "Memory", "ถนน"),
        ("ทำไมต้องฉัน", "Lost Love", "Question", "ทำไม"),
        ("เพื่อนที่หายไป", "Friendship", "Conflict", "เพื่อน"),
        ("คนที่บ้านรออยู่", "Family", "Confession", "บ้าน"),
    ]
    benchmark_titles: set[str] = set()
    benchmark_hooks: set[str] = set()
    for benchmark_idea, story_type, hook_style, required_term in benchmark_controls:
        benchmark_pack = generate_creative_release_pack(
            benchmark_idea,
            "Vela Moon Emotional Pop Rock",
            "Vela Moon",
            creative_controls={"story_type": story_type, "hook_style": hook_style, "mood": "Reflective", "genre": "Thai Emotional Pop Rock"},
        )["pack"]
        benchmark_titles.add(benchmark_pack["Suggested title"])
        benchmark_hooks.add(benchmark_pack["Hook"].splitlines()[0])
        assert_true(required_term in benchmark_pack["SUNO LYRICS FIELD"] or required_term in benchmark_pack["Hook"], f"benchmark concept did not inject story details for {benchmark_idea}")
    assert_true(len(benchmark_titles) >= 4 and len(benchmark_hooks) >= 4, "benchmark songs are not distinct enough")
    communication_concept = "ความจริงสำคัญ แต่วิธีพูดก็สำคัญพอกัน"
    communication_pack = generate_creative_release_pack(communication_concept, "Vela Moon Emotional Pop Rock", "Vela Moon")
    communication_lyrics = communication_pack["pack"]["Full lyrics"]
    communication_intro = communication_lyrics.split("[Verse 1]", 1)[0]
    stale_breakup_lines = ["ฉันเดินผ่านที่เดิม", "ทุกข้อความเก่า", "ถ้าความทรงจำมีประตูให้ปิด", "เสียงเมืองยังดัง", "หัวใจก็ยังจำว่าเคยรัก", "ปล่อยให้ชื่อเธอค่อย ๆ จางไป"]
    communication_terms = ["ความจริง", "พูด", "คำ", "อ่อนโยน", "ฟัง", "รักษา", "ซ่อม"]
    assert_true(communication_concept not in communication_intro, "communication concept was copied directly into intro")
    assert_true(all(line not in communication_lyrics for line in stale_breakup_lines), "communication concept reused stale breakup-memory lyrics")
    assert_true(sum(1 for term in communication_terms if term in communication_lyrics) >= 5, "communication lyrics do not focus on honest respectful speech")
    assert_true(communication_pack["quality_report"]["concept_alignment"]["aligned"] is True and communication_pack["quality_report"]["concept_alignment"]["theme"] == "respectful_truth", "concept alignment validation failed for communication lyrics")
    actual_thai_communication_concept = "\u0e04\u0e27\u0e32\u0e21\u0e08\u0e23\u0e34\u0e07\u0e2a\u0e33\u0e04\u0e31\u0e0d \u0e41\u0e15\u0e48\u0e27\u0e34\u0e18\u0e35\u0e1e\u0e39\u0e14\u0e01\u0e47\u0e2a\u0e33\u0e04\u0e31\u0e0d\u0e1e\u0e2d\u0e01\u0e31\u0e19"
    actual_communication_pack = generate_creative_release_pack(actual_thai_communication_concept, "Vela Moon Emotional Pop Rock", "Vela Moon")
    actual_communication_lyrics = actual_communication_pack["pack"]["Full lyrics"]
    actual_sections = validate_song_structure(actual_communication_lyrics)["section_line_counts"]
    expected_minimums = {"Verse 1": 4, "Pre-Chorus": 2, "Chorus": 4, "Verse 2": 4, "Bridge": 2, "Final Chorus": 6, "Outro": 1}
    assert_true(actual_thai_communication_concept not in actual_communication_lyrics.split("[Verse 1]", 1)[0], "actual Thai communication concept copied directly into intro")
    assert_true(all(actual_sections.get(section, 0) >= minimum for section, minimum in expected_minimums.items()), "concept alignment shortened commercial song structure")
    assert_true(actual_communication_pack["quality_report"]["concept_alignment"]["aligned"] is True and actual_communication_pack["quality_report"]["concept_alignment"]["theme"] == "respectful_truth", "actual Thai concept alignment failed")
    assert_true(sum(1 for term in ["\u0e04\u0e27\u0e32\u0e21\u0e08\u0e23\u0e34\u0e07", "\u0e1e\u0e39\u0e14", "\u0e04\u0e33", "\u0e2d\u0e48\u0e2d\u0e19\u0e42\u0e22\u0e19", "\u0e1f\u0e31\u0e07", "\u0e23\u0e31\u0e01\u0e29\u0e32", "\u0e0b\u0e48\u0e2d\u0e21"] if term in actual_communication_lyrics) >= 5, "actual Thai communication lyrics lack concept focus")
    assert_true(not detect_thai_quality_issues(clean_thai_output("ความรู้สึกของฉัน ไม่สามารถที่จะ ลืมเธอ")), "Thai quality filter rewrite failed")
    signature_presets = {
        "Vela Moon Emotional Pop Rock",
        "Vela Moon Late Night Drive",
        "Vela Moon Heartbroken Anthem",
        "Vela Moon Easy Listening Pop Rock",
        "Vela Moon Office Life Story",
    }
    assert_true(release_zip.exists() and "Thai Sad Pop" in CREATIVE_PACK_PRESETS and "Dark Podcast Intro" in CREATIVE_PACK_PRESETS and signature_presets.issubset(set(CREATIVE_PACK_PRESETS)), "creative release pack export/presets failed")
    for signature_preset in signature_presets:
        signature_pack = generate_creative_release_pack("เพลง Vela Moon สำหรับคนทำงานที่ยังคิดถึงใครบางคน", signature_preset, "Vela Moon")
        signature_export = export_creative_release_pack(f"Smoke {signature_preset}", signature_pack, "Vela Moon", base_dir=out / sanitize_filename(signature_preset))
        signature_text = creative_release_pack_to_text(signature_pack)
        assert_true(signature_export["ok"] and Path(signature_export["data"]["zip_path"]).exists(), f"{signature_preset} export failed")
        assert_true("Vela Moon" in signature_text and "#ThaiPopRock" in signature_pack["pack"]["Hashtags"] and "#VelaMoon" in signature_pack["pack"]["Hashtags"], f"{signature_preset} signature direction missing")
        assert_true("Hook direction" not in signature_pack["pack"]["Hook"] and "Mood:" not in signature_pack["pack"]["Hook"], f"{signature_preset} hook contains prompt metadata")
        signature_lyrics_lower = signature_pack["pack"]["Full lyrics"].lower()
        signature_lyrics_field_lower = signature_pack["pack"]["SUNO LYRICS FIELD"].lower()
        producer_prompt = signature_pack["pack"]["AI PRODUCER PROMPT"].lower()
        producer_required_terms = ["core genre", "vocal direction", "instrumentation", "arrangement progression", "drum & bass direction", "chorus lift", "bridge direction", "final chorus climax", "mix & master feel", "reference feel"]
        producer_instrument_terms = ["vocal", "acoustic", "electric", "piano", "drum", "bass"]
        arrangement_terms = ["intro:", "verse:", "pre-chorus:", "chorus:", "bridge:", "final chorus:", "outro:"]
        assert_true(all(term in producer_prompt for term in producer_required_terms), f"{signature_preset} producer prompt direction missing")
        assert_true(all(term in producer_prompt for term in producer_instrument_terms), f"{signature_preset} producer instrumentation missing")
        assert_true(all(term in producer_prompt for term in arrangement_terms), f"{signature_preset} arrangement progression missing")
        assert_true("spotify-ready" in producer_prompt or "radio feel" in producer_prompt or "radio-ready" in producer_prompt, f"{signature_preset} mix feel missing")
        assert_true(not any(item in signature_lyrics_lower for item in forbidden_lyric_prompts), f"{signature_preset} full lyrics leaked internal direction")
        assert_true(not any(item in signature_lyrics_lower for item in ["core genre", "vocal direction", "instrumentation", "arrangement progression", "mix & master feel", "music style prompt"]), f"{signature_preset} producer prompt leaked into full lyrics")
        assert_true(not any(item in signature_lyrics_field_lower for item in forbidden_lyric_prompts), f"{signature_preset} copy-ready lyrics leaked internal direction")
        assert_true("(soft cinematic intro" not in signature_pack["pack"]["Full lyrics"] and "spotify-friendly" not in signature_lyrics_lower and "tiktok hook friendly" not in signature_lyrics_lower, f"{signature_preset} intro tag is not clean")
        lyric_lines = signature_pack["pack"]["Full lyrics"].splitlines()
        chorus_index = lyric_lines.index("[Chorus]")
        final_chorus_index = lyric_lines.index("[Final Chorus]")
        verse2_index = lyric_lines.index("[Verse 2]")
        outro_index = lyric_lines.index("[Outro]")
        chorus_lines = {line for line in lyric_lines[chorus_index + 1:verse2_index] if line.strip()}
        final_lines = {line for line in lyric_lines[final_chorus_index + 1:outro_index] if line.strip()}
        assert_true(len(final_lines - chorus_lines) >= 2, f"{signature_preset} final chorus lacks payoff lines")
    emotional_settings = generate_creative_release_pack("Vela Moon emotional pop rock test", "Vela Moon Emotional Pop Rock", "Vela Moon")["pack"]["Advanced Suno Settings"]
    assert_true("AI Controls: Auto by preset" in emotional_settings and "BPM: 85" in emotional_settings and "Weirdness: 12%" in emotional_settings and "Style Influence: 68%" in emotional_settings, "Vela Moon Emotional Pop Rock advanced settings failed")
    thai_sad_release_settings = generate_creative_release_pack("Thai sad pop rain test", "Thai Sad Pop", "Vela Moon")["pack"]["Advanced Suno Settings"]
    assert_true("AI Controls: Auto by preset" in thai_sad_release_settings and "Weirdness: 14%" in thai_sad_release_settings and "Style Influence: 70%" in thai_sad_release_settings and "Weirdness: 89%" not in thai_sad_release_settings, "Thai Sad Pop release controls should use safe preset values")
    manual_release_settings = generate_creative_release_pack(
        "Vela Moon manual control test",
        "Vela Moon Emotional Pop Rock",
        "Vela Moon",
        creative_controls={"weirdness": 89, "style_influence": 99},
    )["pack"]["Advanced Suno Settings"]
    assert_true("AI Controls: Manual Override" in manual_release_settings and "Weirdness: 25%" in manual_release_settings and "Style Influence: 85%" in manual_release_settings, "Release pack manual AI controls were not clamped/recorded")
    producer_validation_pack = generate_creative_release_pack("ถ้าใจยังรัก", "Vela Moon Emotional Pop Rock", "Vela Moon")
    producer_validation_text = creative_release_pack_to_text(producer_validation_pack)
    producer_validation_prompt = producer_validation_pack["pack"]["AI PRODUCER PROMPT"]
    assert_true("PRODUCER BRIEF\n" in producer_validation_text and "PRODUCER NOTES\n" in producer_validation_text and "AI PRODUCER PROMPT" not in producer_validation_text, "Producer Brief/Notes section cleanup failed in TXT export")
    producer_validation_prompt_lower = producer_validation_prompt.lower()
    assert_true("fingerpicked acoustic guitar + felt piano" in producer_validation_prompt_lower and "half-time emotional breakdown" in producer_validation_prompt_lower and "electric guitar counter melody" in producer_validation_prompt_lower, "Vela Moon Emotional Pop Rock dynamic arrangement intelligence missing")
    suno_style_field = producer_validation_pack["pack"]["SUNO STYLE OF MUSIC FIELD"]
    assert_true("CORE GENRE" not in suno_style_field and "VOCAL DIRECTION" not in suno_style_field and len(suno_style_field.split()) < 95 and "85 BPM" in suno_style_field, "Suno Style of Music field is not short copy-ready prompt")
    assert_true(AGENT_WORKFLOW_MODES == WORKFLOW_MODES and "MV Director Mode" in AGENT_WORKFLOW_MODES, "agent workflow modes missing")
    assert_true("Auto" in AGENT_WORKFLOW_MODES and "Auto" in AGENT_AI_PROVIDERS, "agent auto mode/provider missing")
    local_provider = LocalFallbackProvider()
    assert_true(local_provider.generate_text("test") and local_provider.available, "local fallback provider failed")
    gemini_provider = GeminiProvider(api_key="smoke-test-key")
    assert_true(gemini_provider.available and gemini_provider.model == "gemini-2.5-flash", "GeminiProvider key/model init failed")
    assert_true(gemini_provider.diagnostics().get("api_key_detected") is True, "GeminiProvider diagnostics missing key state")
    missing_gemini = GeminiTextProvider(api_key="")
    assert_true(missing_gemini.generate_text("test") == "" and "missing" in missing_gemini.last_error.lower(), "gemini missing-key fallback failed")
    resolved_gemini = resolve_agent_provider("Gemini", provider_api_key="smoke-test-key")
    assert_true(resolved_gemini.available and resolved_gemini.name == "gemini", "agent Gemini provider explicit key failed")
    assert_true(OpenAITextProvider(api_key="").generate_text("test") == "", "openai missing-key fallback failed")
    brain_result = think("เพลงเศร้าเกี่ยวกับแฟนเก่า", "Auto", "General Creative Package", use_memory=False, provider_name="Local Template")
    assert_true(brain_result["selected_workflow"] == "Spotify Commercial Mode" and brain_result["execution_plan"], "agent brain auto workflow failed")
    explicit_workflow = select_best_workflow("ทำพอดแคสต์", "Podcast Episode Mode")
    assert_true(explicit_workflow["workflow_mode"] == "Podcast Episode Mode", "agent brain explicit workflow failed")
    goal = analyze_user_goal("ทำคลิป affiliate สินค้า", provider=local_provider)
    assert_true(goal["goal_type"] == "affiliate", "agent goal analysis failed")
    routed_tasks = route_agent_tasks("ทำ MV เพลงเศร้า", "AI Music Video Prompt", "MV Director Mode")
    assert_true(any(task["task"] == "MV storyboard" and task.get("agent") == "MV Agent" for task in routed_tasks), "agent router task selection failed")
    initialized_agents = [DirectorAgent(), MusicAgent(), TikTokAgent(), MVAgent(), PodcastAgent(), ReleaseAgent()]
    assert_true(all(agent.name and agent.role and callable(agent.execute_task) for agent in initialized_agents), "multi-agent initialization failed")
    coordinator_result = run_multi_agent_workflow("เพลงเศร้าทำ MV ลง TikTok", workflow_mode="MV Director Mode", project_type="AI Music Video Prompt", use_memory=False, provider=local_provider)
    assert_true(coordinator_result["output_package"] and "Director Agent" in coordinator_result["active_agents"] and coordinator_result["collaboration_log"], "multi-agent coordinator failed")
    assert_true(coordinator_result["section_sources"] and any("Agent" in value for value in coordinator_result["section_sources"].values()), "multi-agent section source tracking failed")
    old_memory_path = agent_memory_module.MEMORY_PATH
    agent_memory_module.MEMORY_PATH = ROOT / "outputs" / "smoke_agent_memory.json"
    if agent_memory_module.MEMORY_PATH.exists():
        agent_memory_module.MEMORY_PATH.unlink()
    memory = load_agent_memory()
    assert_true(memory["last_user_ideas"] == [] and agent_memory_module.MEMORY_PATH.exists(), "agent memory default load failed")
    saved_memory = save_agent_memory({"recent_project_type": "Spotify Song Release", "last_user_ideas": ["idea a"]})
    assert_true(saved_memory["recent_project_type"] == "Spotify Song Release" and load_agent_memory()["last_user_ideas"] == ["idea a"], "agent memory save failed")
    thai_agent_idea = "\u0e40\u0e1e\u0e25\u0e07\u0e40\u0e28\u0e23\u0e49\u0e32\u0e40\u0e01\u0e35\u0e48\u0e22\u0e27\u0e01\u0e31\u0e1a\u0e04\u0e19\u0e17\u0e35\u0e48\u0e44\u0e21\u0e48\u0e01\u0e25\u0e31\u0e1a\u0e21\u0e32"
    agent_package = generate_agent_package(thai_agent_idea, "Spotify Song Release", "Thai", "Emotional", "Professional Release", use_memory=True)
    assert_true(all(key in agent_package and str(agent_package[key]).strip() for key in REQUIRED_AGENT_SECTIONS), "agent package missing required non-empty sections")
    assert_true(thai_agent_idea in agent_package["Project Summary"] and "Suno" in agent_package["Suno / Music Style Prompt"] and "Professional Release" in agent_package["Agent Strategy"], "agent package Thai/music output failed")
    assert_true("Project Summary" in agent_package_to_text(agent_package) and "Next Action Checklist" in agent_package_to_text(agent_package), "agent package TXT export failed")
    updated_memory = update_agent_memory("Podcast Episode Idea", "Thai", "Soft Pop", "episode idea", agent_package)
    assert_true(updated_memory["recent_project_type"] == "Podcast Episode Idea" and updated_memory["last_generated_titles"], "agent memory update failed")
    for workflow_mode in WORKFLOW_MODES:
        profile = get_workflow_profile(workflow_mode)
        workflow_package = generate_agent_package("ทดสอบไอเดีย", "General Creative Package", "Thai", "Viral", workflow_mode, use_memory=False)
        assert_true(profile["workflow_mode"] == workflow_mode and all(workflow_package.get(key) for key in REQUIRED_AGENT_SECTIONS), f"agent workflow output failed: {workflow_mode}")
    old_agent_export_root = agent_tools_module.AGENT_EXPORT_ROOT
    agent_tools_module.AGENT_EXPORT_ROOT = ROOT / "outputs" / "smoke_agent_tools"
    if agent_tools_module.AGENT_EXPORT_ROOT.exists():
        shutil.rmtree(agent_tools_module.AGENT_EXPORT_ROOT)
    safe_agent_name = generate_filename("เพลง: ทดสอบ/Agent?")
    assert_true("เพลง" in safe_agent_name and "/" not in safe_agent_name and ":" not in safe_agent_name, "agent filename sanitization failed")
    tool_folder = create_project_folder("Smoke Agent Project")
    assert_true(tool_folder.exists() and tool_folder.is_dir(), "agent safe project folder creation failed")
    txt_path = export_txt("hello agent", "agent export.txt")
    assert_true(txt_path.exists() and "hello agent" in txt_path.read_text(encoding="utf-8-sig"), "agent txt export failed")
    package_path = save_project_package(agent_package, "Smoke Agent Package")
    assert_true(package_path.exists() and "Project Summary" in package_path.read_text(encoding="utf-8-sig"), "agent project package save failed")
    checklist = generate_release_checklist("Spotify Song Release")
    assert_true("Suno" in checklist and "cover" in checklist.lower(), "agent release checklist failed")
    memory_summary = summarize_memory(updated_memory)
    assert_true("Podcast Episode Idea" in memory_summary, "agent memory summary failed")
    release_package = build_release_package(agent_package)
    assert_true(Path(release_package["zip_path"]).exists() and release_package["files"], "agent release package build failed")
    multi_agent_exports = build_multi_agent_creator_exports(agent_package, "Smoke Office Song")
    exported_names = {Path(path).name for path in multi_agent_exports["files"]}
    assert_true({"lyrics.txt", "suno_prompt.txt", "tiktok_hooks.txt", "storyboard.txt", "release_package.zip"}.issubset(exported_names), "multi-agent canonical exports missing")
    workspace_root = ROOT / "outputs" / "smoke_projects_workspace"
    if workspace_root.exists():
        shutil.rmtree(workspace_root)
    workspace_project = create_workspace_project("Smoke Agent Workspace", root=workspace_root)
    assert_true(Path(workspace_project["path"]).exists() and (Path(workspace_project["path"]) / "project.json").exists(), "workspace project create failed")
    saved_workspace = save_workspace_project("Smoke Agent Workspace", {"user_goals": ["goal one"]}, root=workspace_root)
    loaded_workspace = load_workspace_project("Smoke Agent Workspace", root=workspace_root)
    assert_true(saved_workspace["user_goals"] == ["goal one"] and loaded_workspace["user_goals"] == ["goal one"], "workspace save/load failed")
    history_workspace = append_history("Smoke Agent Workspace", "smoke_event", {"ok": True}, root=workspace_root)
    assert_true(history_workspace["workflow_history"] and (Path(history_workspace["path"]) / "history" / "v1.json").exists(), "workspace history logging failed")
    generation_workspace = append_generation_run("Smoke Agent Workspace", {"output_package": agent_package, "active_agents": ["Music Agent"], "generated_files": [str(txt_path)], "memory_summary": "memory", "actions_performed": ["action"]}, user_goal="goal two", root=workspace_root)
    assert_true(generation_workspace["generated_outputs"] and generation_workspace["active_agents"] == ["Music Agent"], "workspace generation append failed")
    summary_workspace = workspace_summary("Smoke Agent Workspace", root=workspace_root)
    assert_true(summary_workspace["history_count"] >= 2 and summary_workspace["file_count"] > 0, "workspace summary failed")
    zip_workspace = export_workspace_project_zip("Smoke Agent Workspace", root=workspace_root)
    assert_true(zip_workspace.exists() and zip_workspace.suffix == ".zip", "workspace zip export failed")
    old_asset_root = asset_manager_module.PROJECTS_ROOT
    old_asset_index = asset_manager_module.GLOBAL_ASSET_INDEX
    asset_manager_module.PROJECTS_ROOT = ROOT / "outputs" / "smoke_visual_projects"
    asset_manager_module.GLOBAL_ASSET_INDEX = asset_manager_module.PROJECTS_ROOT / "assets" / "asset_index.json"
    if asset_manager_module.PROJECTS_ROOT.exists():
        shutil.rmtree(asset_manager_module.PROJECTS_ROOT)
    sample_asset = ROOT / "outputs" / "smoke_asset.txt"
    sample_asset.write_text("visual asset", encoding="utf-8")
    assert_true(safe_asset_filename("bad:name image?.jpg") == "badname_image.jpg", "safe asset filename failed")
    metadata = generate_asset_metadata(sample_asset, "images", "Smoke Visual", "smoke", "MV Agent", ["visual"])
    assert_true(metadata["asset_type"] == "images" and metadata["linked_agent"] == "MV Agent", "asset metadata generation failed")
    registered = register_asset(sample_asset, "images", "Smoke Visual", "smoke", "MV Agent", ["visual"])
    imported = import_asset(sample_asset, "images", "Smoke Visual", "import", "MV Agent", ["imported"])
    listed_assets = list_registered_assets("Smoke Visual")
    assert_true(registered["asset_id"] and imported["asset_id"] and len(listed_assets) >= 2, "asset registration/import/list failed")
    attached = attach_asset_to_project(registered["asset_id"], "Smoke Visual", "song_linked_to_mv")
    assert_true(attached.get("relation") == "song_linked_to_mv", "asset project attach failed")
    storyboard = create_storyboard("Smoke Visual", "Smoke Storyboard", "visual continuity")
    storyboard = add_scene(storyboard, "wide opener", "slow push", "warm light", "sad", 4, "vertical cinematic shot")
    storyboard_txt = export_storyboard_txt(storyboard, "Smoke Visual")
    storyboard_json = export_storyboard_json(storyboard, "Smoke Visual")
    assert_true(storyboard_txt.exists() and storyboard_json.exists() and "wide opener" in storyboard_txt.read_text(encoding="utf-8-sig"), "storyboard export failed")
    item = create_pipeline_item("Smoke Visual", "storyboard", registered["asset_id"], "Storyboard")
    approved_item = transition_stage(item, "approved")
    exported_item = transition_stage(approved_item, "exported")
    pipeline_path = save_pipeline("Smoke Visual", [exported_item, storyboard_pipeline("Smoke Visual", "sb1"), cover_pipeline("Smoke Visual", "cover1"), mv_pipeline("Smoke Visual", "mv1"), release_package_pipeline("Smoke Visual", "pkg1")])
    assert_true(pipeline_path.exists() and load_pipeline("Smoke Visual")[0]["stage"] == "exported", "media pipeline transition failed")
    link = link_project_asset("Smoke Visual", registered["asset_id"], "storyboard_linked_to_scenes", "scene_01")
    cover_asset = cover_prompt_history("Smoke Visual", "cinematic cover prompt", "MV Agent")
    approved_cover = approve_cover("Smoke Visual", cover_asset["asset_id"])
    asset_summary = workspace_project_asset_summary("Smoke Visual")
    assert_true(link["relation_type"] == "storyboard_linked_to_scenes" and approved_cover["approved_cover_asset_id"] == cover_asset["asset_id"] and asset_summary["asset_count"] >= 1 and get_project_asset_links("Smoke Visual"), "project asset linking/cover workflow failed")
    asset_manager_module.PROJECTS_ROOT = old_asset_root
    asset_manager_module.GLOBAL_ASSET_INDEX = old_asset_index
    smoke_visual_project = ROOT / "projects" / "Smoke_Visual"
    if smoke_visual_project.exists():
        shutil.rmtree(smoke_visual_project)
    if (ROOT / "outputs" / "smoke_visual_projects").exists():
        shutil.rmtree(ROOT / "outputs" / "smoke_visual_projects")
    (Path(workspace_project["path"]) / "project.json").write_text("{bad json", encoding="utf-8")
    recovered_workspace = load_workspace_project("Smoke Agent Workspace", root=workspace_root)
    assert_true(recovered_workspace["project_name"] == "Smoke_Agent_Workspace", "workspace corrupted project recovery failed")
    archive_result = archive_workspace_project("Smoke Agent Workspace", root=workspace_root)
    assert_true(archive_result["archived"] is True and not any(item["project_name"] == "Smoke_Agent_Workspace" for item in list_workspace_projects(root=workspace_root)), "workspace archive/list failed")
    executor_result = run_agent_workflow("เพลงเศร้าเกี่ยวกับคนที่ไม่กลับมา", "Auto", use_memory=False, project_type="Spotify Song Release", language="Thai", tone="Viral", provider_name="Local Template", auto_workflow=True, multi_agent=True)
    assert_true(executor_result["output_package"] and executor_result["actions_performed"] and executor_result["generated_files"] and "workflow_summary" in executor_result and executor_result["brain_analysis"], "agent executor return structure failed")
    assert_true(executor_result["selected_workflow"] == "Spotify Commercial Mode" and executor_result["execution_plan"] and executor_result["active_agents"] and executor_result["collaboration_log"], "agent executor brain/multi-agent routing failed")
    executor_export_names = {Path(path).name for path in executor_result["generated_files"]}
    assert_true({"lyrics.txt", "suno_prompt.txt", "tiktok_hooks.txt", "storyboard.txt", "release_package.zip"}.issubset(executor_export_names), "agent executor did not export canonical multi-agent files")
    office_agent_result = run_agent_workflow("เพลงเศร้าในออฟฟิศ", "Auto", use_memory=False, project_type="Spotify Song Release", language="Thai", tone="Emotional", provider_name="Local Template", auto_workflow=True, multi_agent=True)
    office_export_names = {Path(path).name for path in office_agent_result["generated_files"]}
    assert_true(office_agent_result["success"] and {"Music Agent", "TikTok Agent", "MV Agent", "Release Agent"}.issubset(set(office_agent_result["active_agents"])) and {"lyrics.txt", "suno_prompt.txt", "tiktok_hooks.txt", "storyboard.txt", "release_package.zip"}.issubset(office_export_names), "office sadness multi-agent workflow failed")
    workspace_executor = run_agent_workflow("ทำเพลง workspace", "Auto", use_memory=False, project_type="Spotify Song Release", language="Thai", tone="Emotional", provider_name="Local Template", auto_workflow=True, multi_agent=True, project_name="Smoke Executor Workspace")
    assert_true(workspace_executor.get("workspace_project") and workspace_executor["workspace_project"]["workflow_history"], "agent executor workspace persistence failed")
    executor_workspace_path = Path(workspace_executor["workspace_project"]["path"])
    if executor_workspace_path.exists():
        shutil.rmtree(executor_workspace_path)
    assert_true(any(Path(path).exists() for path in executor_result["generated_files"]), "agent executor generated files missing")
    agent_tools_module.AGENT_EXPORT_ROOT = old_agent_export_root
    agent_memory_module.MEMORY_PATH = old_memory_path
    structure_presets = load_structure_presets()
    assert_true("vela_moon_pop_rock" in structure_presets and "tiktok_hook_first" in structure_presets, "song structure presets failed")
    structure_plan = create_structure_plan(
        {
            "topic": direction["topic"],
            "mood": direction["mood"],
            "music_direction": direction["music_direction"],
            "artist_preset": "vela_moon",
            "target_platform": "Full Pipeline",
            "selected_hook": {"hook_text": "ยังคิดถึงเธอทุกคืน"},
            "creative_direction": direction,
        },
        "vela_moon_pop_rock",
        vela_moon,
    )
    assert_true(validate_structure_plan(structure_plan)["ok"], "song structure plan validation failed")
    assert_true(all(0 <= int(item["energy"]) <= 100 for item in structure_plan["energy_curve"]), "song structure energy curve out of range")
    assert_true(structure_plan.get("notes_for_lyrics_generation"), "structure plan lyrics notes missing")
    structure_save = save_structure_plan("Smoke Structure Project", structure_plan, out / "structure_projects")
    structure_load = load_structure_plan("Smoke Structure Project", out / "structure_projects")
    assert_true(structure_save["ok"] and structure_load["ok"], "song structure plan save/load failed")
    structure_export = export_structure_plan_files("Smoke Structure Project", structure_plan, out / "structure_projects")
    assert_true(Path(structure_export["data"]["json"]).exists(), "song structure plan export failed")
    assert_true(vela_moon["artist_name"] == "Vela Moon" and vela_moon.get("default_music_style_prompt"), "Vela Moon preset failed")
    assert_true(is_locked_artist_preset("vela_moon") and vela_moon.get("locked"), "Vela Moon locked preset failed")
    assert_true(any(item.get("artist_id") == "vela_moon" for item in list_artist_presets()), "artist preset list failed")
    assert_true(get_artist_preset("__missing_artist__").get("artist_id") == "vela_moon", "artist preset fallback failed")
    categories = artist_preset_categories()
    general_presets = list_artist_presets_by_category(GENERAL_CREATOR_CATEGORY)
    signature_presets = list_artist_presets_by_category(VELA_MOON_CATEGORY)
    general_ids = {item.get("artist_id") for item in general_presets}
    signature_ids = {item.get("artist_id") for item in signature_presets}
    assert_true(PUBLIC_DEFAULT_ARTIST_ID == "emotional_pop" and GENERAL_CREATOR_CATEGORY in categories and VELA_MOON_CATEGORY in categories, "artist preset categories missing")
    assert_true({"emotional_pop", "cinematic_story", "viral_tiktok", "indie_soft", "acoustic_heartfelt", "dark_emotional", "motivational", "cozy_chill"}.issubset(general_ids), "general creator presets missing")
    assert_true({"vela_moon", "vela_moon_emotional", "vela_moon_dark_night", "vela_moon_lonely_pop", "vela_moon_cinematic_sad"}.issubset(signature_ids), "Vela Moon signature presets missing")
    assert_true(get_artist_preset("viral_tiktok")["default_music_style_prompt"] != get_artist_preset("dark_emotional")["default_music_style_prompt"], "public presets do not differ")
    assert_true(is_locked_artist_preset("emotional_pop") and is_locked_artist_preset("vela_moon_dark_night"), "system artist presets should be locked")
    assert_true(load_default_artist_id(), "default artist config failed")
    artist_suffix = str(int(time.time()))
    custom_artist_id = f"smoke_artist_{artist_suffix}"
    custom_preset = {
        "artist_id": custom_artist_id,
        "artist_name": "Smoke Artist",
        "brand_style": "test pop rock",
        "default_language": "Thai lyrics",
        "music_prompt_language": "English only",
        "instrument_tags_language": "English only",
        "genre": "mid-tempo pop rock",
        "vocal_style": "smooth male vocal",
        "main_instruments": ["clean electric guitar", "warm bass"],
        "supporting_instruments": ["soft synth pad"],
        "atmosphere_elements": ["relaxed emotional atmosphere"],
        "default_music_style_prompt": "mid-tempo pop rock, clean electric guitar, warm bass, smooth male vocal",
        "suno_advanced_settings": {"weirdness": 12, "style_influence": 60, "reason_th": "smoke test"},
        "song_structure": ["Intro", "Verse 1", "Chorus", "Outro"],
        "writing_rules": ["Thai lyrics must sound natural"],
        "section_instrument_tags": {"Intro": "clean electric guitar, warm bass", "Chorus": "full band arrangement, catchy hook"},
        "mv_identity": {"render_profile": "Cinematic", "subtitle_style": "cinematic", "color_profile": "warm", "camera_language": ["slow push in"], "visual_mood": "warm emotional"},
        "marketing_identity": {"tone": "emotional", "target_platforms": ["YouTube"], "hook_style": "caption-friendly"},
    }
    invalid_preset = dict(custom_preset)
    invalid_preset["artist_id"] = f"bad_artist_{artist_suffix}"
    invalid_preset["main_instruments"] = ["กีต้าร์โปร่ง"]
    assert_true(validate_artist_preset(custom_preset)["ok"], "valid custom artist preset rejected")
    assert_true(not validate_artist_preset(invalid_preset)["ok"], "invalid artist preset accepted")
    save_custom = save_artist_preset(custom_preset)
    assert_true(save_custom["ok"] and get_artist_preset(custom_artist_id)["artist_name"] == "Smoke Artist", "custom artist preset save failed")
    default_custom = set_default_artist_preset(custom_artist_id)
    assert_true(default_custom["ok"] and load_default_artist_id() == custom_artist_id, "set default artist preset failed")
    assert_true(get_artist_preset(None).get("artist_id") == custom_artist_id, "Song Studio default artist preset read failed")
    duplicate_id = f"{custom_artist_id}_copy"
    duplicated = duplicate_artist_preset(custom_artist_id, duplicate_id, "Smoke Artist Copy")
    assert_true(duplicated["ok"] and get_artist_preset(duplicate_id)["artist_name"] == "Smoke Artist Copy", "duplicate artist preset failed")
    exported_preset = export_artist_preset(custom_artist_id)
    imported_data = json.loads(exported_preset["data"]["json"])
    imported_data["artist_id"] = f"{custom_artist_id}_roundtrip"
    imported_data["artist_name"] = "Smoke Artist Roundtrip"
    imported = import_artist_preset(imported_data)
    assert_true(exported_preset["ok"] and imported["ok"], "artist preset import/export roundtrip failed")
    locked_delete = delete_artist_preset("vela_moon")
    assert_true(not locked_delete["ok"], "locked Vela Moon delete was allowed")
    set_default_artist_preset("vela_moon")
    for cleanup_id in [custom_artist_id, duplicate_id, imported_data["artist_id"]]:
        delete_artist_preset(cleanup_id)
    assert_true(tag_validation["ok"], "instrument tag normalization failed")
    assert_true("ยังคิดถึงเธอทุกคืน" in normalized_tags and contains_thai("ยังคิดถึงเธอทุกคืน"), "Thai lyrics were not preserved")
    project_suffix = str(int(time.time()))
    managed_name = f"Smoke Managed {project_suffix}"
    managed_create = create_managed_project(managed_name)
    assert_true(managed_create["ok"] and project_exists(managed_name), "managed project create failed")
    assert_true(any(item["project_name"] == managed_name.replace(" ", "_") for item in list_managed_projects()), "managed project list failed")
    folder_check = ensure_creator_project_folders(managed_name, "song")
    assert_true(folder_check["ok"] and all(Path(path).exists() for path in folder_check["data"]["folders"]), "creator project folder organization failed")
    project_filter_rows = [
        {"project_name": "Smoke_Full_Hook_Package", "display_name": "Smoke_Full_Hook_Package", "path": "smoke", "last_modified_ts": 5},
        {"project_name": "Test_Project", "display_name": "Test_Project", "path": "test", "last_modified_ts": 4},
        {"project_name": "Debug_Project", "display_name": "Debug_Project", "path": "debug", "last_modified_ts": 3},
        {"project_name": "Internal_Project", "display_name": "Internal_Project", "path": "internal", "last_modified_ts": 2},
        {"project_name": "เพลงใหม่ของฉัน", "display_name": "เพลงใหม่ของฉัน", "path": "real", "last_modified_ts": 1},
    ]
    normal_visible_projects = filter_visible_projects(project_filter_rows, developer_mode=False)
    developer_visible_projects = filter_visible_projects(project_filter_rows, developer_mode=True)
    assert_true(all(not is_test_project_name(item["project_name"]) for item in normal_visible_projects), "normal mode project list includes smoke/test/debug projects")
    assert_true(any(item["project_name"].startswith("Smoke_") for item in developer_visible_projects), "developer mode cannot access smoke projects")
    assert_true(any(str(item["display_name"]).startswith("[TEST] Smoke_") for item in developer_visible_projects), "developer mode test project labels missing")
    assert_true(normal_visible_projects and normal_visible_projects[0]["project_name"] == "เพลงใหม่ของฉัน", "default visible project should not be smoke/test")
    seller_managed_name = f"Smoke Seller Managed {project_suffix}"
    seller_managed_create = create_managed_project(seller_managed_name, workflow_type="seller")
    assert_true(seller_managed_create["ok"] and project_exists(seller_managed_name), "seller managed project create failed")
    assert_true(Path(seller_managed_create["data"]["folder"]).parent == workflow_project_root("seller"), "seller project should be stored in project_data/seller")
    seller_project_list = list_managed_projects(workflow_mode="Seller Studio (Beta)")
    song_project_list = list_managed_projects(workflow_mode="Song Studio Only")
    assert_true(any(item["project_name"] == seller_managed_name.replace(" ", "_") and item["workflow_type"] == "seller" for item in seller_project_list), "seller project hidden from Seller Studio")
    assert_true(not any(item["project_name"] == seller_managed_name.replace(" ", "_") for item in song_project_list), "seller project leaked into Song Studio project list")
    assert_true(any(item["project_name"] == managed_name.replace(" ", "_") for item in song_project_list), "song project hidden from Song Studio project list")
    assert_true(not any(item["project_name"] == managed_name.replace(" ", "_") for item in seller_project_list), "song project leaked into Seller Studio project list")
    podcast_managed_name = f"Smoke Podcast Managed {project_suffix}"
    podcast_managed_create = create_managed_project(podcast_managed_name, workflow_type="podcast")
    assert_true(podcast_managed_create["ok"] and project_exists(podcast_managed_name), "podcast managed project create failed")
    assert_true(Path(podcast_managed_create["data"]["folder"]).parent == workflow_project_root("podcast"), "podcast project should be stored in project_data/podcast")
    podcast_project_list = list_managed_projects(workflow_mode="Podcast Studio (Beta)")
    assert_true(any(item["project_name"] == podcast_managed_name.replace(" ", "_") and item["workflow_type"] == "podcast" for item in podcast_project_list), "podcast project hidden from Podcast Studio")
    assert_true(not any(item["project_name"] == seller_managed_name.replace(" ", "_") for item in podcast_project_list), "seller project leaked into Podcast Studio project list")
    assert_true(not any(item["project_name"] == podcast_managed_name.replace(" ", "_") for item in song_project_list), "podcast project leaked into Song Studio project list")
    clips_managed_name = f"Smoke Clips Managed {project_suffix}"
    clips_managed_create = create_managed_project(clips_managed_name, workflow_type="clips")
    assert_true(clips_managed_create["ok"] and project_exists(clips_managed_name), "clips managed project create failed")
    assert_true(Path(clips_managed_create["data"]["folder"]).parent == workflow_project_root("clips"), "clips project should be stored in project_data/clips")
    clips_project_list = list_managed_projects(workflow_mode="Viral Clips Studio (Beta)")
    assert_true(any(item["project_name"] == clips_managed_name.replace(" ", "_") and item["workflow_type"] == "clips" for item in clips_project_list), "clips project hidden from Viral Clips Studio")
    assert_true(not any(item["project_name"] == seller_managed_name.replace(" ", "_") for item in clips_project_list), "seller project leaked into Viral Clips project list")
    assert_true(not any(item["project_name"] == clips_managed_name.replace(" ", "_") for item in song_project_list), "clips project leaked into Song Studio project list")
    thai_project_name = f"เพลงทดสอบไทย {project_suffix}"
    thai_create = create_managed_project(thai_project_name)
    assert_true(thai_create["ok"] and project_exists(thai_project_name), "Thai project name failed")
    assert_true(Path(thai_create["data"]["folder"]).parent == workflow_project_root("music_pipeline"), "music project should be stored in project_data/music")
    legacy_folder = LEGACY_PROJECTS_ROOT / f"Legacy_Path_{project_suffix}"
    legacy_folder.mkdir(parents=True, exist_ok=True)
    (legacy_folder / "project.json").write_text(json.dumps({"title": f"Legacy Path {project_suffix}", "workflow_type": "song", "song": {"title": "legacy"}}, ensure_ascii=False), encoding="utf-8")
    assert_true(resolve_project_folder(f"Legacy Path {project_suffix}").parent == LEGACY_PROJECTS_ROOT, "legacy project path fallback failed")
    archived = archive_project(managed_name)
    assert_true(archived["ok"] and any(managed_name.replace(" ", "_") in item["project_name"] for item in list_archived_projects()), "archive project failed")
    assert_true(not any(item["project_name"] == managed_name.replace(" ", "_") for item in list_managed_projects()), "archived project shown in active list")
    seller_deleted = delete_project(seller_managed_name, confirm=True)
    assert_true(seller_deleted["ok"], "seller project delete failed")
    podcast_deleted = delete_project(podcast_managed_name, confirm=True)
    assert_true(podcast_deleted["ok"], "podcast project delete failed")
    clips_deleted = delete_project(clips_managed_name, confirm=True)
    assert_true(clips_deleted["ok"], "clips project delete failed")
    deleted = delete_project(thai_project_name, confirm=True)
    assert_true(deleted["ok"] and Path(deleted["data"]["backup_path"]).exists() and not project_exists(thai_project_name), "delete project backup failed")
    legacy_deleted = delete_project(f"Legacy Path {project_suffix}", confirm=True)
    assert_true(legacy_deleted["ok"], "legacy project delete failed")
    pref_save = save_user_preferences({"workflow_mode": "Song Studio Only"})
    pref_load = load_user_preferences()
    assert_true(pref_save["ok"] and pref_load["workflow_mode"] == "Song Studio Only", "Song Studio Only preference failed")
    seller_pref_save = save_user_preferences({"workflow_mode": "Seller Studio (Beta)"})
    seller_pref_load = load_user_preferences()
    assert_true(seller_pref_save["ok"] and seller_pref_load["workflow_mode"] == "Seller Studio (Beta)", "Seller Studio preference failed")
    podcast_pref_save = save_user_preferences({"workflow_mode": "Podcast Studio (Beta)"})
    podcast_pref_load = load_user_preferences()
    assert_true(podcast_pref_save["ok"] and podcast_pref_load["workflow_mode"] == "Podcast Studio (Beta)", "Podcast Studio preference failed")
    clips_pref_save = save_user_preferences({"workflow_mode": "Viral Clips Studio (Beta)"})
    clips_pref_load = load_user_preferences()
    assert_true(clips_pref_save["ok"] and clips_pref_load["workflow_mode"] == "Viral Clips Studio (Beta)", "Viral Clips preference failed")
    provider_pref_save = save_user_preferences({"default_ai_provider": "openai"})
    provider_pref_load = load_user_preferences()
    assert_true(provider_pref_save["ok"] and provider_pref_load["default_ai_provider"] == "openai", "default AI provider preference failed")
    xai_pref_save = save_user_preferences({"default_ai_provider": "xai"})
    xai_pref_load = load_user_preferences()
    assert_true(xai_pref_save["ok"] and xai_pref_load["default_ai_provider"] == "xai", "xAI default provider preference failed")
    api_mode_pref_save = save_user_preferences({"api_mode": API_MODE_OWN_KEY})
    api_mode_pref_load = load_user_preferences()
    assert_true(api_mode_pref_save["ok"] and api_mode_pref_load["api_mode"] == API_MODE_OWN_KEY, "API mode preference failed")
    save_user_preferences({"default_ai_provider": "gemini"})
    save_user_preferences({"workflow_mode": "Full Pipeline"})
    hook_candidates = generate_hook_candidates("เพลงคิดถึงแฟนเก่าตอนฝนตก", vela_moon)
    broken_hook_parse = generate_hook_candidates_with_provider(
        api_key="fake-key",
        model_name="__bad_model__",
        idea="broken json smoke",
        genre="Pop Rock",
        mood="เศร้า",
        artist_preset=vela_moon,
    )
    assert_true(broken_hook_parse["ok"] and broken_hook_parse["data"]["offline"] and broken_hook_parse["data"]["hooks"], "broken hook provider fallback failed")
    try:
        _extract_json('[{"hook_text": "broken" "missing comma"}]')
        raise AssertionError("invalid hook JSON did not raise")
    except Exception:
        pass
    new_project_hooks_a = generate_hook_candidates("เพลงใหม่ไม่ควรซ้ำ", vela_moon, seed="project-a")
    new_project_hooks_b = generate_hook_candidates("เพลงใหม่ไม่ควรซ้ำ", vela_moon, seed="project-b")
    assert_true(new_project_hooks_a != new_project_hooks_b, "new project reused previous hook candidates")
    selected_hook = select_best_hook(hook_candidates)
    workflow_song = {
        "artist_preset": "vela_moon",
        "artist_preset_data": vela_moon,
        "hook_candidates": hook_candidates,
        "selected_hook": selected_hook,
        "original_song_output": thai_tag_lyrics,
        "complete_lyrics": thai_tag_lyrics,
        "normalized_song_output": normalized_tags,
        "music_style_prompt": vela_moon["default_music_style_prompt"],
        "advanced_settings": vela_moon["suno_advanced_settings"],
        "song_structure_plan": structure_plan,
    }
    song_save = save_song_state("Smoke Song Workflow", workflow_song, out / "song_workflow_projects", create_draft=True)
    song_folder = Path(song_save["data"]["folder"])
    saved_song = json.loads((song_folder / "song.json").read_text(encoding="utf-8"))
    full_pipeline_name = export_txt_filename(saved_song, "Smoke Song Workflow", "Full Pipeline")
    assert_true(song_save["ok"] and len(hook_candidates) >= 3, "offline hook candidate generation failed")
    assert_true(saved_song.get("hook_candidates") and saved_song.get("selected_hook"), "selected hook was not saved")
    assert_true((song_folder / "lyrics.txt").exists(), "lyrics.txt was not written")
    full_pipeline_path = Path(song_save["data"]["suno_export"].get("suno_full_package", ""))
    assert_true(full_pipeline_path.exists() and full_pipeline_path.name.startswith(full_pipeline_name.removesuffix(".txt")), "dynamic full pipeline TXT was not written")
    lyrics_only_path = Path(song_save["data"]["suno_export"].get("lyrics_only", ""))
    assert_true(lyrics_only_path.exists() and "Lyrics_Only" in lyrics_only_path.name and lyrics_only_path.suffix == ".txt", "professional lyrics TXT was not written")
    assert_true((song_folder / "exports" / "song_structure_plan.json").exists(), "song_structure_plan.json was not exported")
    assert_true((song_folder / "exports" / "song_structure_plan.md").exists(), "song_structure_plan.md was not exported")
    for filename in ["music_style_prompt.txt", "arrangement_map.txt", "vocal_direction.txt", "instrument_palette.txt", "energy_curve.json"]:
        assert_true((song_folder / "exports" / filename).exists(), f"music direction save export missing {filename}")
    assert_true(saved_song.get("normalized_song_output") == (song_folder / "lyrics.txt").read_text(encoding="utf-8"), "normalized song output was not used for lyrics.txt")
    full_suno_text = full_pipeline_path.read_text(encoding="utf-8-sig")
    lyrics_only_text = lyrics_only_path.read_text(encoding="utf-8")
    release_data = build_release_package_data(saved_song, "Smoke Song Workflow")
    assert_true("ยังคิดถึงเธอทุกคืน" in full_suno_text and "Selected Hook:" in full_suno_text and "Hook Scores:" in full_suno_text and "Song Structure Summary" in full_suno_text, "Suno full package metadata failed")
    for section in ["SONG METADATA", "LYRICS", "SEO CAPTION", "TIKTOK CAPTION", "YOUTUBE DESCRIPTION", "HASHTAGS", "SHORTS HOOKS", "COVER ART PROMPTS", "CANVAS PROMPT", "RELEASE ASSETS"]:
        assert_true(section in full_suno_text, f"release package section missing: {section}")
    assert_true(len(release_data["hashtags"]) >= 10 and len(release_data["hashtags"]) <= 20, "release hashtags count failed")
    assert_true(len(release_data["shorts_hooks"]) >= 3 and len(release_data["shorts_hooks"]) <= 5, "shorts hooks count failed")
    assert_true(all(key in release_data["cover_art_prompts"] for key in ["1:1", "16:9", "9:16", "Square Album Cover 1:1", "No Text / DistroKid Safe", "Spotify Canvas / Short Visual Loop"]), "cover prompt aspect prompts missing")
    assert_true("no watermark" in release_data["cover_art_prompts"]["1:1"] and "no logo" in release_data["cover_art_prompts"]["16:9"], "cover prompt rules missing")
    for cover_section in ["[Square Album Cover 1:1]", "[No Text / DistroKid Safe]", "[Spotify Canvas / Short Visual Loop]"]:
        assert_true(cover_section in full_suno_text, f"Suno TXT cover section missing: {cover_section}")
    assert_true("Cover prompts not generated yet." not in full_suno_text, "Suno TXT cover prompts unexpectedly empty")
    assert_true(song_save["data"]["suno_export"].get("seo_caption") and song_save["data"]["suno_export"].get("cover_prompts_text"), "release export data missing")
    assert_true(song_save["data"]["suno_export"].get("workflow_mode") == "Full Pipeline", "Full Pipeline workflow mode missing in export")
    assert_true("TikTok Caption" in song_save["data"]["suno_export"].get("export_sections", []), "Full Pipeline export sections missing TikTok Caption")
    debug_path = Path(song_save["data"]["suno_export"].get("debug_log", ""))
    assert_true(debug_path.exists(), "Suno export debug log missing")
    assert_true(lyrics_only_text == saved_song.get("normalized_song_output"), "lyrics TXT did not use normalized output")
    assert_true(Path(song_save["data"]["suno_export"].get("suno_full_package", "")).name == song_save["data"]["suno_export"].get("suno_full_filename"), "dynamic full pipeline path was not returned after save")
    assert_true(song_save["data"]["suno_export"].get("suno_full_filename", "").startswith(full_pipeline_name.removesuffix(".txt")), "dynamic download filename missing from export data")
    assert_true(validate_english_only_tags(saved_song["normalized_song_output"])["ok"], "saved song tags are not English only")
    assert_true(contains_thai(saved_song["normalized_song_output"]), "Thai lyrics were not preserved in saved song")
    assert_true((song_folder / "song_drafts").exists(), "song draft history was not created")
    song_only_save = save_song_state("Smoke Song Only Workflow", workflow_song, out / "song_only_workflow_projects", workflow_mode="Song Studio Only")
    song_only_name = export_txt_filename(song_only_save["data"]["song"], "Smoke Song Only Workflow", "Song Studio Only")
    song_only_export_path = Path(song_only_save["data"]["suno_export"].get("suno_full_package", ""))
    song_only_text = song_only_export_path.read_text(encoding="utf-8-sig")
    assert_true(song_only_export_path.name.startswith(song_only_name.removesuffix(".txt")) and "Suno_Export" in song_only_export_path.name and "Demo_Song_song_only" not in song_only_export_path.name, "Song Only dynamic filename failed")
    assert_true("Complete Lyrics with Tags" in song_only_text and "Hook Information" in song_only_text, "Song Only export missing lyrics/hook")
    assert_true("STYLE PROMPT FOR SUNO" in song_only_text and "OPTIONAL NEGATIVE STYLE" in song_only_text, "Song Only creator Suno format missing style sections")
    assert_true("CREATOR RELEASE PACKAGE" in song_only_text and "COVER ART PROMPTS" in song_only_text and "RELEASE ASSETS" in song_only_text, "Song Only creator export missing release-ready sections")
    idea_only_song = dict(workflow_song)
    idea_only_song["title"] = ""
    idea_only_song["idea"] = "พอได้แล้วใจ"
    idea_only_song["selected_hook"] = {"hook_text": "พอได้แล้วใจ", "emotional_score": 90, "catchy_score": 88, "tiktok_potential": 87}
    idea_only_save = save_song_state("", idea_only_song, out / "idea_only_song_projects", workflow_mode="Full Pipeline")
    idea_only_saved = idea_only_save["data"]["song"]
    idea_only_export = Path(idea_only_save["data"]["suno_export"]["suno_full_package"])
    assert_true(idea_only_saved["title"] == "พอได้แล้วใจ", "idea-only save did not generate song title")
    assert_true("พอได้แล้วใจ" in idea_only_export.name and "Untitled_Song" not in idea_only_export.name and "Demo_Song" not in idea_only_export.name, "generated title did not propagate to export filename")
    assert_true("Song title: พอได้แล้วใจ" in idea_only_export.read_text(encoding="utf-8-sig"), "generated title did not propagate to Suno TXT")
    project["song"].update(saved_song)
    project["song"]["title"] = "Smoke Song Workflow"
    project["song"]["genre"] = "Modern Pop / Pop Rock"
    project["song"]["mood"] = "lonely emotional"
    project["song"]["music_preset"] = "VelaFlow Default"
    project["song"]["vocal_direction"] = "Male Emotional"
    mv_storyboard = generate_mv_storyboard(project["song"], project, scene_count=8, visual_settings={"camera_preset": "Slow Push", "lighting_preset": "Neon Night", "motion_preset": "Slow Cinematic", "visual_mood": "Lonely"})
    assert_true(mv_storyboard["ok"], "MV storyboard generation failed")
    mv_scenes = mv_storyboard["data"]["storyboard"]
    assert_true(5 <= len(mv_scenes) <= 10, "MV storyboard scene count out of range")
    assert_true(all(mv_storyboard["data"]["metadata"].get("quality_report", {}).values()), "MV storyboard quality report failed")
    required_scene_keys = {"scene_title", "visual_prompt", "camera_direction", "lighting", "mood", "transition_idea", "image_prompt", "video_prompt"}
    assert_true(all(required_scene_keys.issubset(scene.keys()) for scene in mv_scenes), "MV storyboard scene fields missing")
    assert_true(len({scene["scene_title"] for scene in mv_scenes}) > 3, "MV storyboard scene titles did not vary")
    assert_true(all("AI video" in scene["visual_prompt"] and "vertical 9:16" in scene["visual_prompt"] for scene in mv_scenes), "MV storyboard prompts are not AI-video optimized")
    mv_text = storyboard_to_text(mv_scenes, mv_storyboard["data"]["metadata"])
    assert_true("Scene 1:" in mv_text and "Prompt:" in mv_text and "Vertical Shorts:" in mv_text, "MV storyboard text export format failed")
    assert_true("Camera Preset: Slow Push" in mv_text and mv_scenes[0]["visual_engine"]["lighting_preset"] == "Neon Night", "MV visual metadata failed")
    mv_export = export_mv_storyboard("Smoke Song Workflow", mv_scenes, mv_storyboard["data"]["metadata"], out / "mv_storyboard_projects")
    assert_true(mv_export["ok"] and Path(mv_export["data"]["txt_path"]).exists(), "mv_storyboard.txt export failed")
    assert_true("MV STORYBOARD" in Path(mv_export["data"]["txt_path"]).read_text(encoding="utf-8"), "mv_storyboard.txt content failed")
    mv_render_package = build_render_package("Smoke Song Workflow", "music_mv", mv_scenes, {"provider": "Veo", "aspect_ratio": "16:9", "duration": "10s", "quality": "Cinematic", "motion_intensity": "Medium", "bundle_name": "Cinematic Sad"}, {"camera_preset": "Slow Push", "lighting_preset": "Neon Night", "motion_preset": "Slow Cinematic", "visual_mood": "Lonely"})
    mv_render_export = export_render_package("Smoke Song Workflow", mv_render_package, out / "render_connector_projects")
    assert_true(mv_render_export["ok"] and Path(mv_render_export["data"]["json_path"]).name == "render_package.json" and Path(mv_render_export["data"]["queue_path"]).exists(), "MV render package export failed")
    mv_render_text = Path(mv_render_export["data"]["txt_path"]).read_text(encoding="utf-8")
    assert_true("Preset Bundle: Cinematic Sad" in mv_render_text and mv_render_package["payload"]["bundle_name"] == "Cinematic Sad", "render package bundle metadata failed")
    loaded_queue = load_render_queue("Smoke Song Workflow", out / "render_connector_projects")
    queue_items = loaded_queue["data"]["items"]
    assert_true(loaded_queue["ok"] and queue_items and queue_items[-1]["status"] == "Ready", "render queue load failed")
    marked_queue = mark_render_queue_item("Smoke Song Workflow", queue_items[-1]["queue_id"], "Exported", out / "render_connector_projects")
    assert_true(marked_queue["ok"] and marked_queue["data"]["items"][-1]["status"] == "Exported", "render queue mark exported failed")
    assert_true({"Manual / Mock", "Google Veo Ready", "Kling Ready", "Runway Ready"}.issubset(set(RENDER_JOB_PROVIDER_MODES)), "render job provider modes missing")
    job_send = send_render_job("Smoke Song Workflow", mv_render_package, "Manual / Mock", out / "render_connector_projects")
    assert_true(job_send["ok"] and job_send["data"]["job"]["status"] == "Pending" and job_send["data"]["job"]["job_id"], "mock render job send failed")
    job_id = job_send["data"]["job"]["job_id"]
    first_check = check_render_job_status("Smoke Song Workflow", job_id, out / "render_connector_projects")
    second_check = check_render_job_status("Smoke Song Workflow", job_id, out / "render_connector_projects")
    loaded_jobs = load_render_jobs("Smoke Song Workflow", out / "render_connector_projects")
    assert_true(first_check["data"]["job"]["status"] == "Rendering" and second_check["data"]["job"]["status"] == "Completed", "mock render job status progression failed")
    assert_true(loaded_jobs["ok"] and Path(second_check["data"]["job"]["result_path"]).is_file(), "render jobs load or placeholder result failed")
    project.setdefault("mv", {})["storyboard"] = mv_scenes
    seller_result = generate_seller_content(
        product_name="Smoke Bottle",
        product_category="Lifestyle Gadget",
        target_audience="busy creators",
        key_selling_points="easy to carry\nkeeps drinks cool\nclean minimal design",
        tone_style="Friendly Creator",
        hook_style="Review",
        visual_settings={"camera_preset": "TikTok Creator", "lighting_preset": "Clean Studio", "motion_preset": "Smooth Product Showcase", "visual_mood": "Premium"},
        provider="xai",
        api_key="",
        model_name="grok-4.3",
    )
    assert_true(seller_result["ok"], "seller content generation failed")
    seller_production_missing = generate_seller_content(
        product_name="Smoke Bottle",
        product_category="Lifestyle Gadget",
        target_audience="busy creators",
        key_selling_points="easy to carry",
        provider="xai",
        api_key="",
        production_mode=True,
    )
    assert_true(not seller_production_missing["ok"] and seller_production_missing["provider_status"]["status"] == STATUS_MISSING_KEY, "Seller Studio production generation silently allowed missing API")
    seller_package = seller_result["data"]
    assert_true(seller_package["provider_status"]["status"] == "Offline Demo Mode" and seller_package["fallback_label"] == "Demo / Offline Preview", "Seller Studio demo output is not clearly labeled")
    assert_true("Review" in HOOK_STYLES and seller_package["hook_style"] == "Review", "seller hook style failed")
    assert_true(seller_package["active_ai_provider"] == "xai" and seller_package["active_ai_model"] == "grok-4.3", "seller xAI provider metadata failed")
    assert_true(3 <= len(seller_package["compressed_benefits"]) <= 6, "seller compressed benefits count failed")
    assert_true(len(seller_package["tiktok_hooks"]) >= 3 and seller_package["caption"] and seller_package["ai_video_prompt"], "seller content package missing core fields")
    assert_true(seller_package["product_image"]["attached"] is False, "seller no-image package incorrectly marked image attached")
    assert_true(seller_package.get("script_15s") and seller_package.get("script_30s") and seller_package.get("script_60s"), "seller timed scripts missing")
    assert_true(all(seller_package.get("quality_report", {}).values()), "seller content quality report failed")
    assert_true(seller_package.get("thumbnail_prompt"), "seller thumbnail prompt missing")
    assert_true(len(seller_package["broll_shot_ideas"]) >= 5 and "vertical 9:16" in seller_package["ai_video_prompt"], "seller video prompt or b-roll failed")
    seller_text = seller_content_to_text(seller_package)
    assert_true("Camera Preset: TikTok Creator" in seller_text and "Visual direction:" in seller_package["ai_video_prompt"], "seller visual metadata failed")
    for section in ["RAW SELLING POINTS", "COMPRESSED BENEFITS", "TIKTOK HOOKS", "FINAL SCRIPT", "CTA", "CAPTION", "HASHTAGS", "VIDEO PROMPT", "THUMBNAIL PROMPT", "B-ROLL IDEAS"]:
        assert_true(section in seller_text, f"seller export section missing: {section}")
    long_description = "ผ้าปูที่นอนตัวนี้ผลิตจากเส้นใยนุ่มมาก ระบายอากาศได้ดีทำให้นอนไม่ร้อน มีคุณสมบัติกันไรฝุ่น เหมาะกับคนเป็นภูมิแพ้ นอนสบาย ใช้ได้ทุกเพศทุกวัย และทำความสะอาดง่าย"
    compressed = compress_selling_points(long_description)
    assert_true({"นุ่ม", "ไม่ร้อน", "กันไรฝุ่น", "นอนสบาย"}.issubset(set(compressed)), "smart selling point compression failed")
    long_seller = generate_seller_content(
        product_name="Smoke Bedding",
        product_category="Bedding",
        target_audience="คนรักการนอน",
        key_selling_points=long_description,
        tone_style="Soft Lifestyle",
        hook_style="Soft Sell",
    )
    assert_true(long_seller["ok"] and len(long_seller["data"]["compressed_benefits"]) <= 6, "long seller compression package failed")
    assert_true(long_seller["data"]["script_15s"] != long_seller["data"]["script_30s"] and long_seller["data"]["script_30s"] != long_seller["data"]["script_60s"], "seller timed scripts not distinct")
    image_ref = out / "seller_product.webp"
    image_ref.write_bytes(b"fake-webp-reference")
    seller_with_image = generate_seller_content(
        product_name="Smoke Bottle",
        product_category="Lifestyle Gadget",
        target_audience="busy creators",
        key_selling_points=["easy to carry", "keeps drinks cool"],
        tone_style="Friendly Creator",
        product_image={"path": str(image_ref), "filename": image_ref.name, "content_type": "image/webp"},
        hook_style="Problem/Solution",
    )
    assert_true(seller_with_image["ok"] and seller_with_image["data"]["product_image"]["attached"], "seller image package failed")
    assert_true("Product image attached" in seller_with_image["data"]["ai_video_prompt"], "seller image note missing from video prompt")
    assert_true("Product image attached" in seller_with_image["data"]["thumbnail_prompt"], "seller image note missing from thumbnail prompt")
    seller_export = export_seller_content("Smoke Seller Project", seller_package, out / "seller_projects")
    assert_true(seller_export["ok"] and Path(seller_export["data"]["txt_path"]).name == "seller_content_package.txt", "seller content TXT export failed")
    assert_true("SELLER CONTENT PACKAGE" in Path(seller_export["data"]["txt_path"]).read_text(encoding="utf-8"), "seller content TXT content failed")
    seller_render_package = build_render_package("Smoke Seller Project", "seller", seller_package, {"provider": "Runway", "aspect_ratio": "9:16", "duration": "15s", "quality": "Standard", "motion_intensity": "Medium"}, seller_package["visual_engine"])
    seller_render_export = export_render_package("Smoke Seller Project", seller_render_package, out / "seller_projects")
    assert_true(seller_render_export["ok"] and "Runway" in Path(seller_render_export["data"]["txt_path"]).read_text(encoding="utf-8"), "seller render package export failed")
    seller_image_export = export_seller_content("Smoke Seller Image Project", seller_with_image["data"], out / "seller_projects")
    image_export_text = Path(seller_image_export["data"]["txt_path"]).read_text(encoding="utf-8")
    image_export_json = json.loads(Path(seller_image_export["data"]["json_path"]).read_text(encoding="utf-8"))
    assert_true(str(image_ref) in image_export_text and image_export_json["product_image"]["filename"] == image_ref.name, "seller image export metadata failed")
    seller_project = {
        "title": "Smoke Seller Campaign",
        "seller_studio": {"content_package": seller_package, "export": seller_export["data"]},
    }
    seller_dashboard = build_seller_dashboard_status(seller_project)
    seller_stage_names = [stage["name"] for stage in seller_dashboard["data"]["stages"]]
    assert_true(seller_dashboard["next_step"]["stage"] == "Seller Content", "seller dashboard next step failed")
    assert_true(seller_stage_names == ["Hooks", "Script", "CTA", "Video Prompt", "Export Package"], "seller dashboard stages failed")
    assert_true("Song" not in seller_stage_names and "Storyboard" not in seller_stage_names and "Render" not in seller_stage_names, "seller dashboard leaked song workflow labels")
    empty_seller_dashboard = build_seller_dashboard_status({"title": "เพลงใหม่ของฉัน", "seller_studio": {}})
    assert_true(empty_seller_dashboard["data"]["campaign_name"] == "New Seller Campaign", "seller campaign fallback reused song title")
    assert_true(empty_seller_dashboard["data"]["product_name"] == "No product selected", "seller product fallback reused campaign title")
    assert_true("Emotional" in STORY_TONES and "Calm Storytelling" in NARRATION_STYLES and "5 min" in EPISODE_LENGTHS, "podcast presets missing")
    podcast_result = generate_podcast_content(
        topic="ชีวิตออฟฟิศที่ทำให้หมดไฟ",
        episode_theme="เล่าความเหนื่อยของคนทำงานและการกลับมาเลือกตัวเอง",
        story_tone="Dark Office",
        target_audience="คนทำงานที่กำลังหมดไฟ",
        episode_length="5 min",
        narration_style="Calm Storytelling",
        visual_settings={"camera_preset": "Documentary", "lighting_preset": "Office Fluorescent", "motion_preset": "Documentary Realism", "visual_mood": "Dark Office"},
    )
    assert_true(podcast_result["ok"], "podcast content generation failed")
    podcast_package = podcast_result["data"]
    for key in [
        "episode_hooks",
        "podcast_intro",
        "main_script",
        "emotional_monologue",
        "viral_rant_version",
        "shorts_extraction_ideas",
        "tiktok_clip_hooks",
        "episode_title_ideas",
        "youtube_description",
        "hashtags",
        "ai_video_prompt",
        "thumbnail_prompt",
    ]:
        assert_true(podcast_package.get(key), f"podcast package missing: {key}")
    assert_true("vertical 9:16" in podcast_package["ai_video_prompt"], "podcast video prompt not shorts-ready")
    podcast_text = podcast_content_to_text(podcast_package)
    assert_true("Camera Preset: Documentary" in podcast_text and "Office Fluorescent" in podcast_text and "Visual direction:" in podcast_package["ai_video_prompt"], "podcast visual metadata failed")
    for section in ["PODCAST METADATA", "EPISODE HOOKS", "PODCAST INTRO", "MAIN SCRIPT", "EMOTIONAL MONOLOGUE", "VIRAL RANT VERSION", "SHORTS EXTRACTION IDEAS", "TIKTOK CLIP HOOKS", "YOUTUBE DESCRIPTION", "AI VIDEO PROMPT", "THUMBNAIL PROMPT"]:
        assert_true(section in podcast_text, f"podcast export section missing: {section}")
    podcast_export = export_podcast_content("Smoke Podcast Project", podcast_package, out / "podcast_projects")
    assert_true(podcast_export["ok"] and Path(podcast_export["data"]["txt_path"]).name == "podcast_episode_package.txt", "podcast TXT export failed")
    assert_true(Path(podcast_export["data"]["json_path"]).name == "podcast_episode_package.json", "podcast JSON export failed")
    saved_gemini_key = os.environ.pop("GEMINI_API_KEY", None)
    try:
        podcast_script_result = generate_podcast_script_package(
            topic="คนทำงานที่ยิ้มทั้งวันแต่กลับไปร้องไห้ในรถ",
            podcast_tone="Dark Humor",
            narrator="Male",
            episode_length="20 min",
        )
    finally:
        if saved_gemini_key is not None:
            os.environ["GEMINI_API_KEY"] = saved_gemini_key
    assert_true(podcast_script_result["ok"], "Podcast Script Studio generation failed")
    podcast_script_blocked = generate_podcast_script_package(
        topic="ทีมเงียบหลังประชุม",
        podcast_tone="Vela After Work",
        narrator="Male",
        episode_length="10 min",
        gemini_api_key="",
        production_mode=True,
        require_gemini_success=True,
        demo_mode=False,
    )
    assert_true(not podcast_script_blocked["ok"] and podcast_script_blocked["provider_status"]["status"] == STATUS_MISSING_KEY, "Podcast Studio production generation silently allowed missing Gemini")
    podcast_script_package = podcast_script_result["data"]
    assert_true((podcast_script_package["metadata"].get("provider_status") or {}).get("status") == "Offline Demo Mode", "Podcast Studio local story output is not labeled as demo")
    assert_true(set(REQUIRED_PODCAST_SCRIPT_SECTIONS).issubset(set(podcast_script_package)), "Podcast Script Studio missing output sections")
    saved_gemini_key = os.environ.pop("GEMINI_API_KEY", None)
    try:
        podcast_script_10_result = generate_podcast_script_package(
            topic="คนทำงานที่ยิ้มทั้งวันแต่กลับไปร้องไห้ในรถ",
            podcast_tone="Dark Humor",
            narrator="Male",
            episode_length="10 min",
        )
    finally:
        if saved_gemini_key is not None:
            os.environ["GEMINI_API_KEY"] = saved_gemini_key
    assert_true(podcast_script_10_result["ok"], "Podcast Script Studio 10-minute generation failed")
    assert_true("Vela After Work" in PODCAST_SCRIPT_TONES and WORD_TARGETS["20 min"]["min"] >= 3500 and podcast_script_package["metadata"]["offline_safe"] is True and podcast_script_package["metadata"]["episode_length"] == "20 min", "Podcast Script Studio metadata failed")
    assert_true(podcast_script_package["metadata"]["story_engine"] == "Vela After Work AI Story Writer" and podcast_script_package["metadata"]["story_blueprint_source"] in {"gemini", "local_fallback"} and podcast_script_package["metadata"]["story_provider"]["provider"] == "gemini", "Podcast Script Studio AI story writer metadata failed")
    assert_true(all(podcast_script_package["metadata"].get("quality_report", {}).values()), "Podcast Script Studio quality report failed")
    assert_true(podcast_script_package["metadata"]["story_arc"] and podcast_script_package["metadata"]["scene_breakdown"] and len(podcast_script_package["metadata"]["scene_breakdown"]) >= 6, "Podcast Script Studio story outline metadata missing")
    assert_true("Hello everyone" not in podcast_script_package["Cold Open"] and "วันนี้เราจะพูดถึง" not in podcast_script_package["Cold Open"], "Podcast Script Studio cold open is too robotic")
    assert_true("[Cold Open]" in podcast_script_package["Full Podcast Script"] and "[Act 1: The Ordinary Office Day]" in podcast_script_package["Full Podcast Script"] and "[Act 2: The Incident]" in podcast_script_package["Full Podcast Script"] and "[Act 3: The Awkward Silence]" in podcast_script_package["Full Podcast Script"] and "[Act 4: The Office Politics]" in podcast_script_package["Full Podcast Script"] and "[Act 5: The Breaking Point]" in podcast_script_package["Full Podcast Script"] and "[Act 6: After Work Reflection]" in podcast_script_package["Full Podcast Script"] and "[Ending]" in podcast_script_package["Full Podcast Script"], "Podcast Script Studio V4 full story arc missing")
    assert_true("[Cold Open]" not in podcast_script_package["AI Voice Version"] and "[Narrator Direction]" not in podcast_script_package["AI Voice Version"], "Podcast Script Studio AI voice version contains labels")
    assert_true(podcast_script_package["metadata"]["word_count"] >= WORD_TARGETS["20 min"]["min"] and podcast_script_package["metadata"]["word_count"] > podcast_script_10_result["data"]["metadata"]["word_count"] + 1200, "Podcast Script Studio V4 long-form word target failed")
    full_podcast_script = podcast_script_package["Full Podcast Script"]
    smoke_podcast_topic = "คนทำงานที่ยิ้มทั้งวันแต่กลับไปร้องไห้ในรถ"
    assert_true(podcast_script_package_to_text(podcast_script_package).count(smoke_podcast_topic) <= 2, "Podcast Script Studio repeats topic too often in full package")
    assert_true("ผมจำได้ว่า" in full_podcast_script and "วันนั้น" in full_podcast_script and "ตอนนั้น" in full_podcast_script and "ผมนั่งอยู่" in full_podcast_script, "Podcast Script Studio lacks forced first-person story cues")
    assert_true("เมย์" in full_podcast_script and "พี่นนท์" in full_podcast_script and ("พี่อร" in full_podcast_script or "HR" in full_podcast_script), "Podcast Script Studio lacks supporting office characters")
    assert_true(any(line in full_podcast_script for line in ["\"อันนี้ใครเป็นคนทำ\"", "\"พี่ขอแก้นิดเดียวเอง\"", "\"ไม่เป็นไรใช่ไหม\"", "\"เดี๋ยวคุยกันหลังประชุม\""]), "Podcast Script Studio lacks realistic office dialogue")
    assert_true("ห้องประชุมเงียบไปประมาณสามวินาที" in full_podcast_script and "รายงาน Excel" in full_podcast_script and "shared folder" in full_podcast_script, "Podcast Script Studio lacks concrete incident and office politics")
    assert_true(any(token in podcast_script_package["Cold Open"] for token in ["เครื่องชงกาแฟ", "ลิฟต์", "กาแฟ", "ประชุม", "จอ Excel", "แชตงาน", "ลานจอดรถ"]), "Podcast Script Studio cold open does not start from an office scene")
    assert_true(any(token in full_podcast_script for token in ["ลิฟต์", "กาแฟ", "จอ Excel", "แชตงาน", "ลานจอดรถ"]), "Podcast Script Studio lacks office scene narration")
    assert_true("Hello everyone" not in full_podcast_script and "ในบทความนี้" not in full_podcast_script and "โดยสรุป" not in full_podcast_script and "สิ่งที่ทำให้" not in full_podcast_script and "จุดเปลี่ยนคือ" not in full_podcast_script and "บทเรียนคือ" not in full_podcast_script, "Podcast Script Studio contains generic AI or self-help narration")
    assert_true("Viral Rant Engine" in podcast_script_package and {"emotional rant version", "angry rant version", "sarcastic office rant version"}.issubset(podcast_script_package["Viral Rant Engine"]), "Podcast Script Studio rant variants missing")
    assert_true(len(podcast_script_package["Shorts Extraction"]) == 10 and all({"timestamp", "hook", "script", "caption"}.issubset(item) for item in podcast_script_package["Shorts Extraction"]), "Podcast Script Studio shorts extraction failed")
    assert_true(podcast_script_package["Thumbnail Prompt"] and podcast_script_package["AI Video Prompt"] and "no watermark" in podcast_script_package["AI Video Prompt"], "Podcast Script Studio platform prompts missing")
    podcast_script_text = podcast_script_package_to_text(podcast_script_package)
    assert_true("VELAFLOW PODCAST SCRIPT STUDIO V4" in podcast_script_text and "YOUTUBE PACKAGE" in podcast_script_text and "SPOTIFY PACKAGE" in podcast_script_text and "VIRAL RANT ENGINE" in podcast_script_text, "Podcast Script Studio TXT export failed")
    podcast_render_package = build_render_package("Smoke Podcast Project", "podcast", podcast_package, {"provider": "Luma", "aspect_ratio": "9:16", "duration": "10s", "quality": "Standard", "motion_intensity": "Low"}, podcast_package["visual_engine"])
    podcast_render_export = export_render_package("Smoke Podcast Project", podcast_render_package, out / "podcast_projects")
    assert_true(podcast_render_export["ok"] and "Luma" in Path(podcast_render_export["data"]["txt_path"]).read_text(encoding="utf-8"), "podcast render package export failed")
    podcast_dashboard = build_podcast_dashboard_status({
        "title": "Smoke Podcast Episode",
        "podcast_studio": {"content_package": podcast_package, "export": podcast_export["data"]},
    })
    podcast_stage_names = [stage["name"] for stage in podcast_dashboard["data"]["stages"]]
    assert_true(podcast_dashboard["next_step"]["page"] == "Podcast Studio", "podcast dashboard next step failed")
    assert_true(podcast_stage_names == ["Hooks", "Intro", "Main Script", "Shorts Ideas", "Export Package"], "podcast dashboard stages failed")
    assert_true("Song" not in podcast_stage_names and "Seller" not in podcast_stage_names and "Render" not in podcast_stage_names, "podcast dashboard leaked other workflow labels")
    assert_true("Music" in SOURCE_TYPES and "TikTok" in TARGET_PLATFORMS and "30 sec" in CLIP_LENGTHS and "Viral" in GOALS and "Viral Energy" in CLIP_TONE_STYLES, "viral clips presets missing")
    viral_result = generate_viral_clips_content(
        source_type="Podcast",
        main_idea="คนทำงานหมดไฟแต่ยังต้องยิ้ม",
        target_platform="TikTok",
        tone_style="Viral Energy",
        clip_length="30 sec",
        goal="Viral",
        provider="openai",
        api_key="",
        model_name="gpt-4.1-mini",
        visual_settings={"camera_preset": "TikTok Creator", "lighting_preset": "Natural Daylight", "motion_preset": "Fast TikTok Cuts", "visual_mood": "Viral"},
    )
    assert_true(viral_result["ok"], "viral clips generation failed")
    viral_package = viral_result["data"]
    for key in ["viral_hooks", "short_script", "subtitle_lines", "caption", "hashtags", "scene_ideas", "broll_ideas", "ai_video_prompt", "thumbnail_prompt", "cta"]:
        assert_true(viral_package.get(key), f"viral clips package missing: {key}")
    assert_true(viral_package["active_ai_provider"] == "openai" and "vertical 9:16" in viral_package["ai_video_prompt"], "viral clips provider or video prompt failed")
    xai_viral_result = generate_viral_clips_content(
        source_type="General Idea",
        main_idea="test grok fallback",
        target_platform="TikTok",
        tone_style="Direct",
        clip_length="15 sec",
        goal="Awareness",
        provider="xai",
        api_key="",
        model_name="grok-4.3",
    )
    assert_true(xai_viral_result["ok"] and xai_viral_result["data"]["active_ai_provider"] == "xai", "xAI viral clips fallback failed")
    viral_text = viral_clips_to_text(viral_package)
    assert_true("Camera Preset: TikTok Creator" in viral_text and "Fast TikTok Cuts" in viral_text and "Visual direction:" in viral_package["ai_video_prompt"], "viral clips visual metadata failed")
    for section in ["VIRAL CLIPS METADATA", "VIRAL HOOKS", "SHORT SCRIPT", "SUBTITLE LINES", "CAPTION", "HASHTAGS", "SCENE IDEAS", "B-ROLL IDEAS", "AI VIDEO PROMPT", "THUMBNAIL PROMPT", "CTA"]:
        assert_true(section in viral_text, f"viral clips export section missing: {section}")
    viral_export = export_viral_clips_content("Smoke Viral Clips Project", viral_package, out / "viral_clips_projects")
    assert_true(viral_export["ok"] and Path(viral_export["data"]["txt_path"]).name == "viral_clips_package.txt", "viral clips TXT export failed")
    assert_true(Path(viral_export["data"]["json_path"]).name == "viral_clips_package.json", "viral clips JSON export failed")
    viral_render_package = build_render_package("Smoke Viral Clips Project", "clips", viral_package, {"provider": "PixVerse", "aspect_ratio": "9:16", "duration": "15s", "quality": "Draft", "motion_intensity": "High"}, viral_package["visual_engine"])
    viral_render_export = export_render_package("Smoke Viral Clips Project", viral_render_package, out / "viral_clips_projects")
    assert_true(viral_render_export["ok"] and "PixVerse" in Path(viral_render_export["data"]["txt_path"]).read_text(encoding="utf-8"), "viral clips render package export failed")
    viral_dashboard = build_viral_clips_dashboard_status({
        "title": "Smoke Viral Clip",
        "viral_clips_studio": {"content_package": viral_package, "export": viral_export["data"]},
    })
    viral_stage_names = [stage["name"] for stage in viral_dashboard["data"]["stages"]]
    assert_true(viral_dashboard["next_step"]["page"] == "Viral Clips Studio", "viral clips dashboard next step failed")
    assert_true(viral_stage_names == ["Hooks", "Script", "Subtitles", "Video Prompt", "Export Package"], "viral clips dashboard stages failed")
    assert_true("Song" not in viral_stage_names and "Seller" not in viral_stage_names and "Render" not in viral_stage_names, "viral clips dashboard leaked other workflow labels")
    assert_true(detect_product_platform("https://shopee.co.th/sample-product-i.123.456") == "shopee", "product platform detection failed")
    link_analysis = analyze_product_link("https://www.tiktok.com/shop/product/smoke-bottle", "price 199, creator-friendly bottle")
    assert_true(link_analysis["ok"] and link_analysis["data"]["platform"] == "tiktok_shop" and link_analysis["data"]["keywords"], "product link analyzer failed")
    best_music_hook = extract_best_hook("music", {"selected_hook": {"hook_text": "เดินต่อ ทั้งที่ใจยังเจ็บ"}})
    song_to_short_song = {
        "title": "Smoke Song Hook",
        "selected_hook": {"hook_text": "เดินต่อ ทั้งที่ใจยังเจ็บ", "emotional_score": 92, "catchy_score": 88, "tiktok_potential": 90},
        "normalized_song_output": "[Chorus]\nเดินต่อ ทั้งที่ใจยังเจ็บ\nให้ฝนล้างคำว่าเรา\n\n[Verse 1]\nคืนนี้ยังคิดถึงเธอ",
    }
    song_to_short_hook = detect_best_song_hook(song_to_short_song)
    assert_true(song_to_short_hook["hook_text"] and song_to_short_hook["total_score"] > 0 and song_to_short_hook["clip_prompt"], "song-to-short hook detection failed")
    best_seller_hook = extract_best_hook("seller", seller_package)
    best_podcast_hook = extract_best_hook("podcast", podcast_package)
    best_viral_hook = extract_best_hook("viral_clips", viral_package)
    for hook_candidate in [best_music_hook, best_seller_hook, best_podcast_hook, best_viral_hook]:
        assert_true(hook_candidate["hook_text"] and all(key in hook_candidate["scores"] for key in ["emotional", "catchy", "tiktok", "replay", "curiosity", "cta", "relatability"]), "hook intelligence score expansion failed")
    hook_scenes = build_scene_sequence(
        workflow_type="seller",
        hook_text=best_seller_hook["hook_text"],
        visual_settings={"camera_preset": "TikTok Creator", "lighting_preset": "Natural Daylight", "motion_preset": "Fast TikTok Cuts", "visual_mood": "Viral"},
        clip_mode="Fast Hook",
        duration_seconds=8,
    )
    hook_subtitles = build_subtitle_timing(hook_scenes)
    assert_true(2 <= len(hook_scenes) <= 5 and hook_scenes[0]["render_provider_metadata"]["aspect_ratio"] == "9:16", "multi-scene hook timeline failed")
    assert_true(hook_subtitles and hook_subtitles[0]["start"] == 0.0, "hook subtitle timing failed")
    hook_clip_result = build_hook_render_package(
        "Smoke Hook Clip Project",
        "seller",
        seller_package,
        visual_settings={"camera_preset": "TikTok Creator", "lighting_preset": "Natural Daylight", "motion_preset": "Fast TikTok Cuts", "visual_mood": "Viral"},
        render_settings={"provider": "Veo", "aspect_ratio": "9:16", "duration": "8s", "quality": "Draft", "motion_intensity": "High", "bundle_name": "TikTok Viral"},
        clip_mode="Fast Hook",
        duration_seconds=8,
        export=False,
    )
    assert_true(hook_clip_result["ok"], "hook clip render package failed")
    hook_clip_package = hook_clip_result["data"]["package"]
    assert_true(hook_clip_package["render_connector_package"]["payload"]["workflow_type"] == "hook_clip", "hook clip render connector payload failed")
    assert_true("HOOK AUTO CLIP PACKAGE" in hook_clip_package_to_text(hook_clip_package), "hook clip text export content failed")
    hook_clip_export = export_hook_clip_package("Smoke Hook Clip Project", hook_clip_package, out / "hook_clip_projects")
    assert_true(hook_clip_export["ok"] and Path(hook_clip_export["data"]["json_path"]).exists() and Path(hook_clip_export["data"]["txt_path"]).exists(), "hook clip package export failed")
    outcome_presets = list_presets()
    assert_true(len(outcome_presets) >= 6 and get_preset("cute_character")["motion_style"] == "bounce", "creator outcome presets failed")
    assert_true(preset_to_render_settings(get_preset("emotional_story"))["duration"] == "30s", "preset render defaults failed")
    character_profile = create_character_profile("banana", personality="Funny", style="Cute 3D", voice_style="Cute", seed="smokeseed")
    consistent_prompt = apply_character_consistency("banana walking in office", character_profile)
    assert_true("same character" in consistent_prompt and "smokeseed" in consistent_prompt, "character consistency prompt failed")
    opening_hook = analyze_opening_hook("กล้วยโดนเทแล้วบ่นเรื่องชีวิต", hook_style="Funny", preset=get_preset("cute_character"), character_profile=character_profile)
    assert_true(opening_hook["ok"] and opening_hook["data"]["hook_score"] >= 0 and opening_hook["data"]["opening_line"], "opening hook intelligence failed")
    character_studio_pack = generate_character_prompt_pack(
        character_name="Nong Mint",
        age_range="4 years old / little girl character",
        gender_presentation="female presentation",
        country_culture="Thai rural village",
        face_description="adorable round face, soft cheeks, bright smile",
        hair_style="short black bob haircut",
        eye_style="big round brown eyes",
        skin_tone="light tan skin",
        outfit="mint green sweatshirt, brown jogger pants",
        shoes_accessories="white sneakers",
        character_style="Pixar-style 3D",
        scene_background="Rural Thai house",
        use_case="Lip sync music video",
        platform="Kling",
    )
    character_studio_sections = character_studio_pack.get("sections", {})
    assert_true(character_studio_pack["ok"] and set(REQUIRED_CHARACTER_STUDIO_SECTIONS).issubset(character_studio_sections), "Character Studio sections missing")
    assert_true("Keep the exact same character identity." in character_studio_sections["Consistency Lock Prompt"] and "Same face, same hairstyle, same outfit, same proportions." in character_studio_sections["Consistency Lock Prompt"], "Character Studio consistency lock missing")
    assert_true("Kling" in character_studio_sections["Image-to-Video Prompt"] and "no text" in character_studio_sections["Image Generation Prompt"].lower(), "Character Studio practical prompt content missing")
    character_studio_text = character_prompt_pack_to_text(character_studio_pack)
    assert_true("VELAFLOW CHARACTER STUDIO PACK" in character_studio_text and "Character Bible" in character_studio_text and "Lip Sync Prompt" in character_studio_text, "Character Studio text export failed")
    styled_subtitles = generate_styled_subtitles(hook_subtitles, out / "hook_clip_projects" / "styled_subtitles", preset_id="cute_character")
    assert_true(styled_subtitles["ok"] and Path(styled_subtitles["data"]["ass"]).exists() and mode_for_preset("cute_character") == "bounce", "TikTok styled subtitle engine failed")
    combine_manifest = combine_scene_clips(["scene_1.mp4", "scene_2.mp4"], out / "hook_clip_projects" / "final_hook_clip.mp4", subtitle_timing=hook_subtitles)
    assert_true(combine_manifest["ok"] and Path(combine_manifest["data"]["manifest_path"]).exists(), "combine fallback manifest failed")
    voiceover_plan = build_voiceover_plan(podcast_package["main_script"], style="tired office worker")
    voiceover_export = export_voiceover_plan("Smoke Podcast Project", voiceover_plan, out / "podcast_projects")
    assert_true(voiceover_plan["style"] == "tired office worker" and voiceover_export["ok"], "voiceover fallback export failed")
    voiceover_audio = generate_voiceover_audio("Smoke Hook Clip Project", "This is a smoke test hook.", style="calm narrator", api_key="", base_dir=out / "hook_clip_projects")
    assert_true(voiceover_audio["ok"] and Path(voiceover_audio["data"]["audio_path"]).exists(), "voiceover MP3 fallback failed")
    srt_result = write_subtitles(hook_subtitles, out / "hook_clip_projects" / "subtitles.srt")
    assert_true(srt_result["ok"] and Path(srt_result["data"]["path"]).exists(), "subtitle SRT export failed")
    cloud_style_scene = out / "cloud_paths" / "project_data" / "clips" / "ทดสอบคลาวด์" / "scenes" / "scene_01.mp4"
    assert_true(ensure_parent_dir(cloud_style_scene).parent.exists(), "ensure_parent_dir failed for cloud-style Thai path")
    if find_ffmpeg():
        smoke_quick_root = ROOT / "project_data" / "clips" / "Smoke_Quick_Hook_Clip"
        shutil.rmtree(smoke_quick_root / "exports" / "versions", ignore_errors=True)
        shutil.rmtree(smoke_quick_root / "cache", ignore_errors=True)
        hook_audio_trim = trim_audio_clip(
            voiceover_audio["data"]["audio_path"],
            out / "hook_clip_projects" / "exports" / "hook_audio.mp3",
            start_time=0,
            end_time=2,
        )
        assert_true(hook_audio_trim["ok"] and Path(hook_audio_trim["data"]["path"]).exists(), "hook audio trim failed")
        long_hook_source = out / "hook_clip_projects" / "long_hook_source.mp3"
        subprocess.run(
            [
                find_ffmpeg(),
                "-y",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=220:duration=30",
                "-c:a",
                "libmp3lame",
                str(long_hook_source),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        detected_hook = detect_hook_section(long_hook_source, output_dir=out / "hook_clip_projects" / "exports" / "debug", quota_saving_mode=True)
        detected_data = detected_hook.get("data", {})
        assert_true(detected_hook["ok"] and detected_data.get("hook_end_time", 0) > detected_data.get("hook_start_time", 0), "hook detector did not return valid start/end")
        assert_true(8 <= float(detected_data.get("hook_duration", 0)) <= 24, "hook detector duration out of MVP bounds")
        assert_true(Path(detected_data.get("report_path", "")).exists(), "hook detection report missing")
        report = json.loads(Path(detected_data["report_path"]).read_text(encoding="utf-8"))
        assert_true(report.get("veo_called") is False and report.get("confidence", 0) > 0 and report.get("reason"), "hook detector report missing local/no-Veo proof")
        assert_true(validate_audio_editor_input(long_hook_source)["ok"], "Audio Editor MP3 validation failed")
        assert_true(not validate_audio_editor_input(unsupported_audio)["ok"], "Audio Editor unsupported input validation failed")
        audio_source_hash = long_hook_source.read_bytes()
        lossless_edit = export_audio_selection(long_hook_source, start_time=1.0, end_time=4.0, project_name="Smoke Audio Editor Lossless", output_name="smoke_hook", cut_mode="Lossless Quick Cut", ffmpeg_path=find_ffmpeg())
        lossless_data = lossless_edit.get("data", {})
        lossless_hook = Path(lossless_data.get("hook_mp3", ""))
        lossless_report = lossless_data.get("report") or {}
        assert_true(lossless_edit["ok"] and lossless_hook.exists() and lossless_hook.name.endswith("_hook.mp3") and lossless_report.get("reencoded") is False and "copy" in lossless_report.get("ffmpeg_command", []), "Audio Editor lossless quick cut failed")
        assert_true("-af" not in lossless_report.get("ffmpeg_command", []), "Lossless Quick Cut should not apply filters")
        precise_edit = export_audio_selection(long_hook_source, start_time=2.0, end_time=5.0, project_name="Smoke Audio Editor Precise", output_name="smoke_precise_hook", cut_mode="Lossless Quick Cut", fade_in=0.25, fade_out=0.25, ffmpeg_path=find_ffmpeg())
        precise_data = precise_edit.get("data", {})
        precise_hook = Path(precise_data.get("hook_mp3", ""))
        precise_report = precise_data.get("report") or {}
        assert_true(precise_edit["ok"] and precise_hook.exists() and precise_report.get("cut_mode") == "Precise Cut" and precise_report.get("reencoded") is True and precise_report.get("output_bitrate") == "320 kbps CBR", "Audio Editor precise cut/fade failed")
        assert_true(Path(precise_data.get("report_path", "")).name == "edit_report.json" and Path(precise_data.get("report_txt_path", "")).name == "edit_report.txt", "Audio Editor edit reports missing")
        assert_true(long_hook_source.read_bytes() == audio_source_hash, "Audio Editor modified the original MP3 source")
        smart_hook_source = out / "hook_clip_projects" / "smart_hook_source.mp3"
        subprocess.run(
            [
                find_ffmpeg(),
                "-y",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=220:duration=8:sample_rate=44100",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=30:sample_rate=44100",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=180:duration=8:sample_rate=44100",
                "-filter_complex",
                "[0:a]volume=0.06[a0];[1:a]volume=0.9[a1];[2:a]volume=0.05[a2];[a0][a1][a2]concat=n=3:v=0:a=1[out]",
                "-map",
                "[out]",
                "-c:a",
                "libmp3lame",
                str(smart_hook_source),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        waveform_json = out / "hook_clip_projects" / "exports" / "waveform.json"
        waveform_svg = out / "hook_clip_projects" / "exports" / "waveform.svg"
        waveform_first = generate_waveform_data(smart_hook_source, waveform_json, ffmpeg_path=find_ffmpeg(), target_points=1200)
        waveform_second = generate_waveform_data(smart_hook_source, waveform_json, ffmpeg_path=find_ffmpeg(), target_points=1200)
        waveform_data = waveform_first.get("data", {})
        waveform_render = render_waveform_svg(waveform_data, waveform_svg, start_time=8.0, end_time=38.0)
        assert_true(waveform_first["ok"] and 1000 <= int(waveform_data.get("point_count", 0)) <= 3000 and waveform_second.get("data", {}).get("cache_status") == "hit" and waveform_render["ok"] and waveform_svg.exists(), "Audio Editor waveform generation/cache/render failed")
        alternate_hook_source = out / "hook_clip_projects" / "smart_hook_source_alt.mp3"
        subprocess.run(
            [
                find_ffmpeg(),
                "-y",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=660:duration=12:sample_rate=44100",
                "-c:a",
                "libmp3lame",
                str(alternate_hook_source),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        waveform_third = generate_waveform_data(alternate_hook_source, waveform_json, ffmpeg_path=find_ffmpeg(), target_points=1200)
        assert_true(waveform_third["ok"] and waveform_third.get("data", {}).get("cache_status") == "miss" and waveform_third.get("data", {}).get("source_signature", {}).get("sha256") != waveform_data.get("source_signature", {}).get("sha256"), "Audio Editor waveform cache fingerprint did not reject stale source")
        hook_analysis = analyze_hook_candidates(smart_hook_source, output_dir=out / "hook_clip_projects" / "exports" / "hook_analysis", ffmpeg_path=find_ffmpeg())
        hook_candidates = (hook_analysis.get("data") or {}).get("candidates", [])
        assert_true(hook_analysis["ok"] and hook_candidates and len(hook_candidates) <= 3 and Path((hook_analysis.get("data") or {}).get("report_path", "")).exists(), "Smart Hook Finder did not return/report candidates")
        first_candidate = hook_candidates[0]
        assert_true(float(first_candidate["start_time"]) >= 5.0 and float(first_candidate["end_time"]) <= 46.5 and float(first_candidate["duration"]) >= 10.0 and "component_scores" in first_candidate, "Smart Hook Finder candidate bounds/scoring failed")
        if len(hook_candidates) > 1:
            overlap = max(0.0, min(float(first_candidate["end_time"]), float(hook_candidates[1]["end_time"])) - max(float(first_candidate["start_time"]), float(hook_candidates[1]["start_time"])))
            assert_true(overlap / min(float(first_candidate["duration"]), float(hook_candidates[1]["duration"])) <= 0.5, "Smart Hook Finder candidates overlap too much")
        assert_true(analyze_hook_candidates(smart_hook_source, ffmpeg_path=find_ffmpeg()).get("data", {}).get("candidates", [])[0]["confidence_score"] == first_candidate["confidence_score"], "Smart Hook Finder scoring should be deterministic")
        batch_lossless = export_audio_batch(smart_hook_source, start_time=8.0, durations=[15, 30, 60], project_name="Smoke Audio Editor Batch", output_stem="smart_hook", cut_mode="Lossless Quick Cut", ffmpeg_path=find_ffmpeg())
        batch_data = batch_lossless.get("data", {})
        batch_files = batch_data.get("generated_files", [])
        batch_zip = Path(batch_data.get("zip_path", ""))
        assert_true(batch_lossless["ok"] and len(batch_files) == 2 and any(item["filename"].endswith("_15s.mp3") for item in batch_files) and any(item["filename"].endswith("_30s.mp3") for item in batch_files) and batch_data.get("skipped_files") and batch_zip.exists(), "Audio Editor batch export/skip failed")
        with zipfile.ZipFile(batch_zip) as archive:
            names = set(archive.namelist())
        assert_true("batch_edit_report.json" in names and "batch_edit_report.txt" in names and any(name.endswith("_15s.mp3") for name in names), "Audio Editor batch ZIP contents missing")
        assert_true(batch_data.get("report", {}).get("reencoded") is False and "copy" in batch_files[0].get("command", []), "Audio Editor lossless batch must stream copy")
        batch_precise = export_audio_batch(smart_hook_source, start_time=8.0, durations=[15], project_name="Smoke Audio Editor Batch Precise", output_stem="smart_precise_hook", cut_mode="Lossless Quick Cut", fade_in=0.25, ffmpeg_path=find_ffmpeg())
        precise_batch_report = (batch_precise.get("data") or {}).get("report", {})
        precise_batch_file = ((batch_precise.get("data") or {}).get("generated_files") or [{}])[0]
        assert_true(batch_precise["ok"] and precise_batch_report.get("cut_mode") == "Precise Cut" and precise_batch_report.get("reencoded") is True and "libmp3lame" in precise_batch_file.get("command", []), "Audio Editor fade batch must force Precise Cut 320k")
        thai_audio_name = out / "hook_clip_projects" / "เพลง.ทดสอบ hook.mp3"
        shutil.copy2(smart_hook_source, thai_audio_name)
        thai_lossless = export_audio_selection(thai_audio_name, start_time=0.0, end_time=1.0, project_name="Smoke Thai Audio Editor", output_name="เพลง ทดสอบ hook", cut_mode="Lossless Quick Cut", ffmpeg_path=find_ffmpeg())
        assert_true(thai_lossless["ok"] and Path(thai_lossless.get("data", {}).get("hook_mp3", "")).name.endswith(".mp3") and "เพลง" in Path(thai_lossless.get("data", {}).get("hook_mp3", "")).name, "Audio Editor Thai/multiple-dot filename handling failed")
        audio_batch_release = export_creative_release_pack(
            "Smoke Audio Batch Release",
            release_pack,
            "Vela Moon",
            base_dir=out / "audio_batch_release_pack",
            audio_edit_data={
                "hook_mp3": lossless_data.get("hook_mp3"),
                "report_path": lossless_data.get("report_path"),
                "report_txt_path": lossless_data.get("report_txt_path"),
                "generated_files": batch_data.get("generated_files", []),
                "batch_report_path": batch_data.get("report_path"),
                "batch_report_txt_path": batch_data.get("report_txt_path"),
            },
        )
        with zipfile.ZipFile(Path(audio_batch_release.get("data", {}).get("zip_path", ""))) as archive:
            release_audio_names = set(archive.namelist())
        assert_true(audio_batch_release["ok"] and "audio_editor/hook.mp3" in release_audio_names and "audio_editor/batch_edit_report.json" in release_audio_names and any(name.startswith("audio_editor/batch/") and name.endswith("_15s.mp3") for name in release_audio_names), "Release Pack did not include Audio Editor single and batch outputs")
        original_hash = long_hook_source.read_bytes()
        audio_recommend = analyze_audio_for_remaster_recommendation(long_hook_source, ffmpeg_path=find_ffmpeg())
        assert_true(audio_recommend["ok"] and audio_recommend.get("data", {}).get("recommended_preset") in REMASTER_STYLES and audio_recommend.get("data", {}).get("source") == "audio_analysis", "external audio remaster recommendation failed")
        audio_recommend_again = analyze_audio_for_remaster_recommendation(long_hook_source, ffmpeg_path=find_ffmpeg())
        assert_true(audio_recommend_again["ok"] and audio_recommend_again.get("data", {}).get("recommended_preset") == audio_recommend.get("data", {}).get("recommended_preset") and audio_recommend_again.get("data", {}).get("confidence_score") == audio_recommend.get("data", {}).get("confidence_score"), "external audio remaster recommendation should be deterministic")
        silent_source = out / "hook_clip_projects" / "silent_remaster_source.mp3"
        subprocess.run([find_ffmpeg(), "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo:d=12", "-c:a", "libmp3lame", str(silent_source)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        quiet_recommend = analyze_audio_for_remaster_recommendation(silent_source, ffmpeg_path=find_ffmpeg())
        assert_true(quiet_recommend["ok"] and quiet_recommend.get("data", {}).get("recommended_preset") == "Streaming Balanced" and quiet_recommend.get("data", {}).get("confidence") == "Low", "low-confidence remaster recommendation failed")
        manual_recommendation = dict(audio_recommend.get("data", {}))
        manual_recommendation["selected_preset"] = "Vocal Focus"
        remaster = remaster_song_audio(long_hook_source, project_name="Smoke Remaster Studio", remaster_style="Vocal Focus", ffmpeg_path=find_ffmpeg(), recommendation_data=manual_recommendation)
        remaster_data = remaster.get("data", {})
        mastered_wav = Path(remaster_data.get("mastered_wav", ""))
        mastered_mp3 = Path(remaster_data.get("mastered_mp3", "") or remaster_data.get("mp3_preview", ""))
        mastered_probe = probe_media(mastered_wav, ffmpeg_path=find_ffmpeg()) if mastered_wav.is_file() else {}
        mastered_mp3_probe = probe_media(mastered_mp3, ffmpeg_path=find_ffmpeg()) if mastered_mp3.is_file() else {}
        remaster_report = remaster_data.get("report") or {}
        assert_true(remaster["ok"] and mastered_wav.exists(), "Remaster Studio did not produce mastered WAV")
        assert_true(mastered_probe.get("ok") and mastered_probe.get("has_audio") and abs(float(mastered_probe.get("duration") or 0) - 30.0) < 0.5, "mastered WAV ffprobe validation failed")
        assert_true(remaster_report.get("no_clipping_above_0db") is True and remaster_report.get("external_api_used") is False, "remaster clipping/API validation failed")
        assert_true(remaster_report.get("remaster_recommendation", {}).get("source") == "audio_analysis" and remaster_report.get("remaster_recommendation", {}).get("selected_preset") == "Vocal Focus" and remaster_report.get("remaster_recommendation", {}).get("overridden") is True, "remaster report recommendation/manual override missing")
        assert_true("Preset Recommendation:" in Path(remaster_data.get("report_txt_path", "")).read_text(encoding="utf-8"), "remaster TXT report missing recommendation details")
        assert_true(mastered_wav.name.endswith("_master.wav") and remaster_report.get("output_wav_settings", {}).get("codec") == "pcm_s24le" and remaster_report.get("output_wav_settings", {}).get("sample_rate_hz") == 48000, "Remaster WAV V1 settings failed")
        assert_true(mastered_mp3.exists() and mastered_mp3.name.endswith("_master.mp3") and remaster_report.get("output_mp3_settings", {}).get("bitrate") == "320 kbps" and mastered_mp3_probe.get("has_audio"), "Remaster MP3 320k output failed")
        assert_true(long_hook_source.read_bytes() == original_hash, "Remaster modified the original source file")
        assert_true(Path(remaster_data.get("zip_path", "")).exists(), "remaster package ZIP missing")
        assert_true(Path(remaster_data.get("report_path", "")).name == "remaster_report.json" and Path(remaster_data.get("report_txt_path", "")).name == "remaster_report.txt", "remaster report outputs missing")
        package_lyrics = """[Verse]
คืนนี้ยังเงียบเหมือนเดิม
ฉันเดินผ่านฝนคนเดียว

[Chorus]
ทำไมใจยังจำเธอ
ทั้งที่เธอไม่เคยกลับมา
ฝนตกลงมาเหมือนคำลา
แต่ฉันยังรักเธออยู่ดี

[Bridge]
แสงไฟยังสั่นในตา
เหมือนคำสัญญาที่หายไป
"""
        creator_package = generate_full_hook_creator_package(
            project_name="Smoke Full Hook Package",
            uploaded_mp3_path=long_hook_source,
            lyrics_text=package_lyrics,
            song_title="Smoke Hook",
            artist_name="VelaFlow",
            mood="cinematic emotional thai pop",
            export_mode="TikTok Emotional",
            prompt_style="Cinematic",
            ffmpeg_path=find_ffmpeg(),
        )
        creator_data = creator_package.get("data", {})
        creator_manifest = json.loads(Path(creator_data["manifest_path"]).read_text(encoding="utf-8"))
        assert_true(creator_package["ok"] and Path(creator_data["zip_path"]).exists(), "creator package ZIP missing")
        assert_true(15 <= float(creator_manifest.get("hook_duration", 0)) <= 30, "creator package hook duration out of range")
        assert_true(int(creator_manifest.get("selected_hook_section_line_count", 0)) >= 3, "creator package did not use full hook section")
        assert_true(creator_manifest.get("package_version") and creator_manifest.get("confidence_score") and creator_manifest.get("detection_reason") and creator_manifest.get("target_platforms"), "creator package manifest missing required creator fields")
        assert_true(creator_manifest.get("export_mode") == "TikTok Emotional" and creator_manifest.get("prompt_style") == "Cinematic" and int(creator_manifest.get("scene_count", 0)) >= 2, "creator package manifest missing prompt mode fields")
        selected_hook_text = (Path(creator_data["package_dir"]) / "selected_hook_section.txt").read_text(encoding="utf-8-sig")
        assert_true(len([line for line in selected_hook_text.splitlines() if line.strip()]) >= 3, "selected_hook_section.txt is not a full multi-line hook")
        required_creator_files = ["hook_audio.mp3", "selected_hook_section.txt", "hook_summary.txt", "hook_emotion.json", "scene_breakdown.txt", "shot_list.json", "image_prompt.txt", "video_prompt_flow.txt", "video_prompt_veo.txt", "video_prompt_runway.txt", "video_prompt_kling.txt", "thumbnail_prompt.txt", "cinematic_direction.txt", "mood_summary.txt", "subtitle.srt", "tiktok_caption.txt", "youtube_description.txt", "hashtags.txt", "upload_checklist.txt", "creator_package_manifest.json"]
        for filename in required_creator_files:
            assert_true((Path(creator_data["package_dir"]) / filename).exists(), f"creator package missing {filename}")
        scene_breakdown = (Path(creator_data["package_dir"]) / "scene_breakdown.txt").read_text(encoding="utf-8-sig")
        shot_list = json.loads((Path(creator_data["package_dir"]) / "shot_list.json").read_text(encoding="utf-8-sig"))
        assert_true("Scene 01" in scene_breakdown and "Visual:" in scene_breakdown and "Camera:" in scene_breakdown and len(shot_list) >= 2, "creator scene breakdown/shot list missing")
        assert_true(all({"shot_id", "start_time", "end_time", "duration", "hook_line", "visual_focus", "camera_motion", "lighting", "emotion", "prompt"}.issubset(set(item.keys())) for item in shot_list), "shot_list.json missing required fields")
        flow_prompt = (Path(creator_data["package_dir"]) / "video_prompt_flow.txt").read_text(encoding="utf-8-sig").lower()
        assert_true("emotional progression" in flow_prompt and "vertical 9:16" in flow_prompt and "no text" in flow_prompt and "no watermark" in flow_prompt and "no subtitles" in flow_prompt, "creator package prompts missing required platform safety/style language")
        assert_true("shot diversity" in flow_prompt and "bottom-safe subtitle space" in flow_prompt and "does not feel repetitive" in flow_prompt, "creator prompts missing stabilization quality language")
        fast_package = build_prompt_director_package(selected_hook_text, song_title="Smoke Hook", mood="cinematic emotional thai pop", export_mode="TikTok Fast Hook", prompt_style="Viral", hook_duration=20)
        safe_package = build_prompt_director_package(selected_hook_text, song_title="Smoke Hook", mood="cinematic emotional thai pop", export_mode="Spotify Canvas", prompt_style="Safe", hook_duration=20)
        assert_true(fast_package["video_prompt_flow"] != safe_package["video_prompt_flow"] and "TikTok Fast Hook" in fast_package["video_prompt_flow"] and "Spotify Canvas" in safe_package["video_prompt_flow"], "prompts do not adapt by export_mode")
        assert_true("faster" in fast_package["mood_summary"].lower() or "retention" in fast_package["mood_summary"].lower(), "prompts do not adapt by prompt_style")
        with zipfile.ZipFile(creator_data["zip_path"], "r") as package_zip:
            names = set(package_zip.namelist())
        assert_true(set(required_creator_files).issubset(names), "creator package ZIP contents missing")
        assert_true(creator_manifest.get("veo_called") is False, "creator package generation should not call Veo/render providers")
        final_creator_zip = build_final_creator_zip(
            package_dir=creator_data["package_dir"],
            original_audio_path=long_hook_source,
            remaster_data=remaster_data,
            output_zip_path=out / "hook_clip_projects" / "final_creator_package.zip",
        )
        assert_true(final_creator_zip["ok"] and Path(final_creator_zip["data"]["zip_path"]).exists(), "unified final creator ZIP failed")
        with zipfile.ZipFile(final_creator_zip["data"]["zip_path"], "r") as unified_zip:
            unified_names = set(unified_zip.namelist())
        required_unified_files = {
            "audio/original_song.mp3",
            "audio/hook_audio.mp3",
            "audio/mastered_song.wav",
            "audio/mastered_preview.mp3",
            "prompts/image_prompt.txt",
            "prompts/veo_prompt.txt",
            "prompts/runway_prompt.txt",
            "prompts/kling_prompt.txt",
            "prompts/flow_prompt.txt",
            "prompts/thumbnail_prompt.txt",
            "creator/hook_summary.txt",
            "creator/hook_emotion.json",
            "creator/mood_summary.txt",
            "creator/scene_breakdown.txt",
            "creator/shot_list.json",
            "creator/subtitle.srt",
            "creator/tiktok_caption.txt",
            "creator/youtube_description.txt",
            "creator/hashtags.txt",
            "creator/upload_checklist.txt",
            "manifest/creator_package_manifest.json",
            "manifest/mastering_report.json",
        }
        assert_true(required_unified_files.issubset(unified_names), "unified creator ZIP missing nested files")
        cloud_scene = render_placeholder_scene({"scene_id": "scene_01", "duration": 0.8}, cloud_style_scene, aspect_ratio="9:16")
        assert_true(cloud_scene["ok"] and cloud_style_scene.exists(), "cloud-style scene parent creation failed")
        motion_scene_path = out / "hook_clip_projects" / "scenes" / "motion_scene_01.mp4"
        motion_source = generate_image("offline", "vertical cinematic motion smoke scene", str(out / "hook_clip_projects" / "images" / "motion_scene_01.jpg"), {"size": "1024x1536", "cache_enabled": False})
        motion_scene = render_image_motion_scene({"scene_id": "scene_01", "duration": 1.2, "source_image_path": motion_source}, motion_scene_path, aspect_ratio="9:16")
        if motion_scene.get("ok"):
            motion_validation = validate_mp4(motion_scene_path, min_duration=1.0, min_file_size=100 * 1024)
            assert_true(motion_validation["valid_mp4"] and motion_validation["file_size"] > 100 * 1024, "static_safe scene render not playable")
            assert_true((motion_scene.get("data") or {}).get("render_mode_used") == "static_safe", "static_safe render mode not used by default")
        for scene_index, scene in enumerate(hook_clip_package.get("scene_sequence", []), start=1):
            source_path = out / "hook_clip_projects" / "images" / f"scene_{scene_index:02d}.jpg"
            generated_source = generate_image("offline", f"vertical smoke source scene {scene_index}", str(source_path), {"size": "1024x1536", "cache_enabled": False})
            scene["source_image_path"] = generated_source
            scene["render_mode"] = "static_safe"
        real_clip = render_real_hook_clip(
            "Smoke Hook Clip Project",
            hook_clip_package,
            workflow_type="hook",
            voiceover_path=voiceover_audio["data"]["audio_path"],
            background_audio_path=hook_audio_trim["data"]["path"],
            force=True,
        )
        assert_true(real_clip["ok"] and Path(real_clip["data"]["final_mp4"]).exists() and Path(real_clip["data"]["subtitles"]).exists(), "real hook MP4 export failed")
        assert_true(real_clip["data"].get("background_audio_path"), "real hook background audio metadata missing")
        assert_true(real_clip["data"]["validation"]["valid_mp4"] and real_clip["data"]["duration"] > 1, "real hook MP4 playable validation failed")
        assert_true(all((job.get("validation") or {}).get("valid_mp4") for job in real_clip["data"]["scene_jobs"] if job.get("status") == "completed"), "scene MP4 validation failed")
        assert_true(all((job.get("validation") or {}).get("file_size", 0) > 100 * 1024 for job in real_clip["data"]["scene_jobs"] if job.get("status") == "completed"), "scene MP4 too small/corrupted")
        assert_true(all(job.get("scene_validation_ok") for job in real_clip["data"]["scene_jobs"] if job.get("status") == "completed"), "scene_validation_ok missing")
        assert_true(Path(real_clip["data"]["render_stage_path"]).exists(), "render_stage.json missing")
        assert_true(real_clip["data"]["render_stage"]["scene_render_ok"] and real_clip["data"]["render_stage"]["combine_ok"] and real_clip["data"]["render_stage"]["final_mp4_ok"], "render stage flags failed")
        assert_true(real_clip["data"]["render_stage"].get("render_mode_used") == "static_safe", "render stage static_safe mode missing")
        assert_true(real_clip["data"]["render_stage"].get("completed_scene_count") == 3, "render stage completed scene count failed")
        assert_true(real_clip["data"]["render_stage"].get("ffmpeg_return_code") == 0, "render stage ffmpeg return code failed")
        assert_true(real_clip["data"]["render_stage"].get("subtitle_burned") or real_clip["data"]["render_stage"].get("subtitle_status") == "exported_only", "subtitle burn/export status missing")
        assert_true(real_clip["data"]["render_stage"].get("audio_sync_status") in {"matched_hook_audio", "matched_video", "silent_audio"}, "audio sync status missing")
        assert_true(real_clip["data"]["render_stage"].get("uploaded_audio_attached") is True, "uploaded hook audio was not attached")
        assert_true((real_clip["data"].get("validation") or {}).get("has_audio"), "real hook final MP4 audio stream missing")
        assert_true(abs(float(real_clip["data"]["duration"] or 0) - float(real_clip["data"]["render_stage"].get("target_duration") or 0)) < 0.35, "final MP4 duration not synced to target")
        assert_true(real_clip["data"]["render_stage"]["scene_jobs"] and real_clip["data"]["render_stage"]["scene_jobs"][0].get("ffmpeg_return_code") == 0, "render stage ffmpeg scene diagnostics failed")
        assert_true(all(job.get("render_mode_used") == "static_safe" for job in real_clip["data"]["scene_jobs"] if job.get("status") == "completed"), "scene jobs did not use static_safe")
        for scene_filename in ["scene_01.mp4", "scene_02.mp4", "scene_03.mp4"]:
            scene_file = Path(real_clip["data"]["scene_jobs"][0]["path"]).parent / scene_filename
            assert_true(scene_file.exists() and validate_mp4(scene_file, min_duration=1.0, min_file_size=100 * 1024)["valid_mp4"], f"{scene_filename} not playable")
        assert_true(real_clip["data"].get("audio_attached"), "audio attach status missing")
        quick_clip = quick_generate_hook_clip(
            "Smoke Quick Hook Clip",
            "ทดสอบคลิปสั้นแนวตั้งสำหรับ VelaFlow",
            image_provider="offline",
            voiceover_style="calm narrator",
            preset_id="viral_meme",
            hook_audio_path=hook_audio_trim["data"]["path"],
        )
        quick_data = quick_clip.get("data", {})
        assert_true(quick_clip["ok"] and Path(quick_data["final_mp4"]).exists(), "quick hook clip MP4 export failed")
        assert_true(validate_mp4(quick_data["final_mp4"])["valid_mp4"], "quick hook final_hook_clip.mp4 not playable")
        assert_true((quick_data["render"].get("render_stage") or {}).get("render_mode_used") in {"cinematic_motion", "static_safe"}, "quick hook cinematic render stage missing")
        assert_true((quick_data["render"].get("render_stage") or {}).get("completed_scene_count") == 3, "quick hook scene render count failed")
        assert_true((quick_data["render"].get("render_stage") or {}).get("subtitle_status") in {"burned", "exported_only"}, "quick hook subtitle status missing")
        assert_true((quick_data["render"].get("render_stage") or {}).get("audio_sync_status") in {"matched_hook_audio", "matched_video", "silent_audio"}, "quick hook audio sync status missing")
        assert_true([item.get("stage") for item in quick_data.get("progress_stages", [])] == ["analyzing_hook", "generating_scenes", "rendering_video", "syncing_audio", "exporting_package", "completed"], "creator progress stages missing")
        assert_true(quick_data["progress_stages"][-1]["status"] == "completed", "creator progress did not complete")
        assert_true((quick_data["render"].get("validation") or {}).get("valid_mp4") and (quick_data["render"].get("validation") or {}).get("has_video"), "quick hook render validation missing")
        assert_true((quick_data["render"].get("validation") or {}).get("has_audio"), "quick hook final MP4 audio stream missing")
        quick_validation = quick_data["render"].get("validation") or {}
        assert_true(quick_validation.get("width") in {720, 1080} and quick_validation.get("height") in {1280, 1920} and quick_validation.get("height", 0) > quick_validation.get("width", 0), "quick hook final MP4 is not fullscreen 9:16")
        assert_true((quick_data["render"].get("render_stage") or {}).get("uploaded_audio_attached") is True, "quick hook uploaded audio was not attached")
        assert_true((quick_data["render"].get("render_stage") or {}).get("visual_composition_mode") == "single_fullscreen_sequential", "fullscreen sequential render mode missing")
        assert_true((quick_data["render"].get("render_stage") or {}).get("timeline_playback_model") == "concat_demuxer_scene_timeline", "timeline concat playback model missing")
        assert_true((quick_data["render"].get("render_stage") or {}).get("forbidden_visual_filters_found") is False, "forbidden visual stack/tile filter detected")
        assert_true((quick_data["render"].get("render_stage") or {}).get("motion_quality_layer") == "cinematic_motion_v1", "cinematic motion quality layer missing")
        assert_true((quick_data["render"].get("render_stage") or {}).get("static_only_chain") is False, "static-only render chain detected")
        rendered_scene_durations = (quick_data["render"].get("render_stage") or {}).get("scene_durations") or []
        assert_true(rendered_scene_durations and all(1.45 <= float(duration) <= 3.1 for duration in rendered_scene_durations if duration), "scene durations are not cinematic short-form timing")
        assert_true("subtitle_burned" in quick_data["render"], "subtitle overlay status missing")
        assert_true((quick_data.get("clip_version") or {}).get("version_id") == "v1" and Path((quick_data.get("clip_version") or {}).get("path", "")).exists(), "clip version v1 missing")
        assert_true((quick_data.get("render_cache") or {}).get("cache_key"), "render cache key missing")
        assert_true((quick_data.get("viral_metrics") or {}).get("hook_score", 0) > 0 and (quick_data.get("viral_metrics") or {}).get("tiktok_retention_potential", 0) > 0, "TikTok hook scoring missing")
        video_prompt_probe = build_hook_video_shot_prompts(
            full_hook_lyrics="ทำไมต้องเป็นเธอ ทั้งท่อน hook เต็มใช้กำกับวิดีโอ",
            mood="Emotional",
            scene_director_plan=quick_data.get("scene_director_plan") or {},
            emotional_arc=quick_data.get("beat_timing", {}).get("emotional_curve") or {},
            target_duration=15,
        )
        assert_true(len(video_prompt_probe) >= 6 and all(item.get("full_hook_section_used") for item in video_prompt_probe), "video shot prompt director did not use full hook section")
        assert_true(all(validate_video_prompt(item["prompt"])["ok"] for item in video_prompt_probe), "AI video prompts contain forbidden text/collage terms")
        missing_video_key = generate_video_shot(video_prompt_probe[0]["prompt"], 2.5, ROOT / "outputs" / "smoke_tests" / "missing_video_key.mp4", settings={})
        assert_true(not missing_video_key["ok"] and missing_video_key.get("error"), "video_ai provider failure was not explicit")
        assert_true(quick_data.get("image_results") and all(item.get("path") for item in quick_data["image_results"]), "quick hook clip image pipeline failed")
        assert_true(all(Path(item["path"]).suffix.lower() == ".jpg" and validate_image_file(item["path"])["ok"] for item in quick_data["image_results"]), "quick hook scene JPG validation failed")
        assert_true(all({"provider_used", "fallback_used", "fallback_reason", "error_type", "safe_error_message"}.issubset(set(item.keys())) for item in quick_data["image_results"]), "image diagnostics missing")
        scene_generation_report_path = Path(quick_data.get("scene_generation_report_path", ""))
        assert_true(scene_generation_report_path.exists(), "scene_generation_report.json missing")
        scene_generation_report = json.loads(scene_generation_report_path.read_text(encoding="utf-8"))
        assert_true(scene_generation_report.get("scene_generation_architecture") == "independent_fullscreen_scene_images", "scene generation architecture is not fullscreen independent")
        assert_true(scene_generation_report.get("scene_count") == len(quick_data["image_results"]), "scene generation report scene count mismatch")
        assert_true((scene_generation_report.get("fullscreen_validation") or {}).get("one_image_per_scene"), "scene image report did not enforce one image per scene")
        assert_true((scene_generation_report.get("fullscreen_validation") or {}).get("all_vertical_9x16"), "scene image report did not enforce vertical 9:16")
        assert_true((scene_generation_report.get("fullscreen_validation") or {}).get("all_single_composition"), "scene image report detected multi-frame composition")
        assert_true(scene_generation_report.get("forbidden_scene_image_layout_found") is False, "scene generation report found contact-sheet/grid layout")
        image_validation_report_path = Path(quick_data.get("image_validation_report_path", ""))
        assert_true(image_validation_report_path.exists(), "image_validation_report.json missing")
        image_validation_report = json.loads(image_validation_report_path.read_text(encoding="utf-8"))
        assert_true(image_validation_report.get("image_validation_engine") == "single_frame_provider_output_guard_v1", "image validation guard missing")
        assert_true(image_validation_report.get("visual_mode") == "cinematic_live_action_realism_v3", "cinematic visual mode lock missing")
        assert_true(image_validation_report.get("render_pipeline_version") == "cinematic_clean_v3", "clean render pipeline version missing")
        assert_true(image_validation_report.get("hard_negative_prompt_active") is True, "hard negative prompt not active")
        assert_true(image_validation_report.get("panel_layout_detected") is False, "image validation detected panel layout")
        assert_true(image_validation_report.get("ocr_text_detected") is False, "OCR-like text detected in scene image")
        assert_true(float(image_validation_report.get("storyboard_score") or 0) < 0.99, "storyboard score too high")
        assert_true(float(image_validation_report.get("text_overlay_score") or 0) < 0.92, "text overlay score too high")
        assert_true(float(image_validation_report.get("numeric_overlay_score") or 0) < 0.92, "numeric overlay score too high")
        assert_true(float(image_validation_report.get("emoji_detected_score") or 0) < 0.92, "emoji detection score too high")
        assert_true(float(image_validation_report.get("cartoon_score") or 0) < 0.94, "cartoon score too high")
        assert_true(float(image_validation_report.get("thumbnail_layout_score") or 0) < 0.94, "thumbnail layout score too high")
        assert_true(float(image_validation_report.get("anime_score") or 0) < 0.94, "anime score too high")
        assert_true(float(image_validation_report.get("reaction_face_score") or 0) < 0.94, "reaction face score too high")
        shot_variation_report_path = Path(quick_data.get("shot_variation_report_path", ""))
        assert_true(shot_variation_report_path.exists(), "shot_variation_report.json missing")
        shot_variation_report = json.loads(shot_variation_report_path.read_text(encoding="utf-8"))
        assert_true(shot_variation_report.get("engine") == "cinematic_shot_variation_engine_v1", "shot variation engine missing")
        assert_true(len(set(shot_variation_report.get("shot_types_used") or [])) >= 3, "shot variation did not create varied shot types")
        assert_true(float(shot_variation_report.get("framing_diversity_score") or 0) >= 0.5, "framing diversity too weak")
        assert_true(float(shot_variation_report.get("motion_evolution_score") or 0) >= 0.5, "motion evolution too weak")
        assert_true(float(shot_variation_report.get("duplicate_frame_score") or 0) < 0.995 and shot_variation_report.get("exact_duplicate_detected") is False, "duplicate scene frame detected")
        render_cleanup_report_path = Path(quick_data.get("render_cleanup_report_path", ""))
        assert_true(render_cleanup_report_path.exists(), "render_cleanup_report.json missing")
        render_cleanup_report = json.loads(render_cleanup_report_path.read_text(encoding="utf-8"))
        assert_true(render_cleanup_report.get("render_pipeline_version") == "cinematic_clean_v3", "cleanup report pipeline version missing")
        assert_true(render_cleanup_report.get("legacy_renderer_removed") is True, "legacy renderer removal flag missing")
        assert_true(render_cleanup_report.get("automatic_text_rendering") is False, "automatic text rendering still enabled")
        assert_true(render_cleanup_report.get("thumbnail_mode") == "raw_validated_cinematic_frame_only", "thumbnail mode was not locked to raw frame")
        assert_true(render_cleanup_report.get("validation_pass") is True, "cinematic clean validation did not pass")
        assert_true(render_cleanup_report.get("ocr_text_detected") is False, "cleanup report detected OCR text")
        assert_true(float(render_cleanup_report.get("numeric_overlay_score") or 0) < 0.92, "cleanup report numeric overlay detected")
        assert_true(float(render_cleanup_report.get("emoji_detected_score") or 0) < 0.92, "cleanup report emoji overlay detected")
        assert_true(render_cleanup_report.get("thumbnail_mode_detected") is False, "thumbnail composition mode detected")
        video_manifest_path = Path(quick_data.get("video_generation_manifest_path", ""))
        assert_true(video_manifest_path.exists(), "video_generation_manifest.json missing")
        video_manifest = json.loads(video_manifest_path.read_text(encoding="utf-8"))
        assert_true(video_manifest.get("mode") in {"image_motion_fallback", "ai_video_provider"}, "video generation mode missing")
        assert_true(video_manifest.get("full_hook_section_used") is True, "video generation did not receive full hook section")
        assert_true(len(video_manifest.get("shot_prompts") or []) >= 6, "video shot prompts missing")
        assert_true(all("single continuous cinematic video shot" in item.get("prompt", "").lower() and "no text" in item.get("prompt", "").lower() and "no storyboard" in item.get("prompt", "").lower() for item in video_manifest.get("shot_prompts", [])), "video prompt safety rules missing")
        assert_true(Path(quick_data["render"]["subtitles"]).exists(), "quick hook clip subtitle export failed")
        subtitle_text = Path(quick_data["render"]["subtitles"]).read_text(encoding="utf-8-sig")
        styled_text = Path((quick_data.get("styled_subtitles") or {}).get("ass", "")).read_text(encoding="utf-8-sig")
        assert_true("□" not in subtitle_text and "�" not in subtitle_text and "Noto Sans Thai" in styled_text, "Thai subtitle font/encoding failed")
        style_lines = [line for line in styled_text.splitlines() if line.startswith("Style: Default,")]
        assert_true(style_lines and all(line.split(",")[18] == "2" and int(line.split(",")[21]) >= 120 for line in style_lines), "subtitle style is not bottom-safe")
        assert_true(Path(quick_data["render_manifest_path"]).exists() and Path(quick_data["scene_manifest_path"]).exists(), "quick hook clip manifests failed")
        assert_true(Path(quick_data["render_stage_path"]).exists(), "quick hook render_stage.json missing")
        assert_true(Path(quick_data["voiceover"]["audio_path"]).name == "voiceover.mp3", "quick hook clip voiceover filename failed")
        assert_true(Path(quick_data["viral_timing_plan_path"]).exists(), "quick hook viral timing plan missing")
        assert_true(Path(quick_data["scene_prompts_path"]).exists(), "quick hook scene_prompts.json missing")
        assert_true(Path(quick_data["scene_director_plan_path"]).exists(), "quick hook scene_director_plan.json missing")
        scene_director_plan = json.loads(Path(quick_data["scene_director_plan_path"]).read_text(encoding="utf-8"))
        assert_true(scene_director_plan.get("shot_progression", [])[:3] == ["wide establishing shot", "medium emotional shot", "close-up emotional face / eyes"], "scene director shot progression failed")
        assert_true(any(scene.get("hook_peak_scene") for scene in scene_director_plan.get("scenes", [])), "scene director hook peak scene missing")
        assert_true(all((scene.get("continuity_notes") or {}).get("character") and (scene.get("continuity_notes") or {}).get("location") for scene in scene_director_plan.get("scenes", [])), "scene director continuity metadata missing")
        assert_true(scene_director_plan.get("realistic_prompt_mode") and scene_director_plan.get("realism_mode") == "cinematic_realism_v1", "realistic prompt mode missing")
        assert_true(scene_director_plan.get("lighting_profile") and scene_director_plan.get("motion_profile"), "cinematic realism profiles missing")
        assert_true(Path(quick_data["beat_timing_path"]).exists(), "quick hook beat_timing.json missing")
        assert_true(Path(quick_data["timeline_director_path"]).exists(), "timeline_director.json missing")
        assert_true(Path(quick_data["scene_motion_map_path"]).exists(), "scene_motion_map.json missing")
        assert_true(Path(quick_data["emotional_curve_path"]).exists(), "emotional_curve.json missing")
        assert_true(Path(quick_data["shot_progression_path"]).exists(), "shot_progression.json missing")
        timeline_director = json.loads(Path(quick_data["timeline_director_path"]).read_text(encoding="utf-8"))
        scene_motion_map = json.loads(Path(quick_data["scene_motion_map_path"]).read_text(encoding="utf-8"))
        emotional_curve = json.loads(Path(quick_data["emotional_curve_path"]).read_text(encoding="utf-8"))
        shot_progression = json.loads(Path(quick_data["shot_progression_path"]).read_text(encoding="utf-8"))
        assert_true(timeline_director.get("engine") == "cinematic_timeline_director_v2", "timeline director v2 missing")
        assert_true((timeline_director.get("hook_pacing_map") or {}).get("active_profile"), "hook pacing map missing")
        camera_styles = [scene.get("camera_style") for scene in timeline_director.get("scenes", [])]
        assert_true(len(set(camera_styles)) >= 3, "camera styles do not vary")
        assert_true(all(scene.get("static_scene_allowed") is False for scene in timeline_director.get("scenes", [])), "static scene allowed in timeline director")
        assert_true(len(set(scene.get("transition_pacing") for scene in timeline_director.get("scenes", []))) >= 2, "transition pacing does not vary")
        assert_true(scene_motion_map.get("scenes") and all(item.get("motion_effect") for item in scene_motion_map.get("scenes", [])), "scene motion map missing motion effects")
        assert_true(emotional_curve.get("curve") and len({item.get("energy") for item in emotional_curve.get("curve", [])}) >= 3, "emotional progression missing")
        assert_true(shot_progression.get("shot_progression") and len({item.get("camera_style") for item in shot_progression.get("shot_progression", [])}) >= 3, "shot progression camera language missing")
        assert_true(Path(quick_data["cinematic_quality_report_path"]).exists(), "cinematic_quality_report.json missing")
        cinematic_quality = json.loads(Path(quick_data["cinematic_quality_report_path"]).read_text(encoding="utf-8"))
        assert_true(cinematic_quality.get("realistic_prompt_mode") and cinematic_quality.get("continuity_mode") == "same_character_same_room_same_palette", "cinematic quality report missing realism/continuity")
        assert_true(cinematic_quality.get("lighting_profile") and cinematic_quality.get("motion_profile") and cinematic_quality.get("subtitle_profile"), "cinematic quality report missing profiles")
        assert_true(Path(quick_data["thumbnail_path"]).exists(), "quick hook thumbnail.jpg missing")
        assert_true(Path(quick_data["thumbnail_score_path"]).exists(), "quick hook thumbnail_score.json missing")
        thumbnail_score = json.loads(Path(quick_data["thumbnail_score_path"]).read_text(encoding="utf-8"))
        assert_true((thumbnail_score.get("quality") or {}).get("thumbnail_quality", 0) > 0, "thumbnail quality scoring failed")
        assert_true(any("cinematic" in item.get("cinematic_prompt", "").lower() for item in quick_data["scene_prompts"]["scene_prompts"]), "scene prompts are not cinematic")
        assert_true(any("different framing" in item.get("cinematic_prompt", "").lower() for item in quick_data["scene_prompts"]["scene_prompts"]), "scene prompts missing variety/continuity guidance")
        assert_true(all("single cinematic fullscreen frame" in item.get("cinematic_prompt", "").lower() and "one continuous real-world camera shot" in item.get("cinematic_prompt", "").lower() and "not a storyboard or multi-panel composition" in item.get("cinematic_prompt", "").lower() for item in quick_data["scene_prompts"]["scene_prompts"]), "scene prompts missing mandatory single-frame positive rules")
        assert_true(all("ultra realistic cinematic live-action film still" in item.get("prompt", "").lower() and "no meme" in item.get("prompt", "").lower() and "no cartoon" in item.get("prompt", "").lower() and "no anime" in item.get("prompt", "").lower() and "no emoji" in item.get("prompt", "").lower() for item in quick_data["image_results"]), "provider prompt visual mode lock missing")
        assert_true(all("no collage" in item.get("cinematic_prompt", "").lower() and "not a grid montage" in item.get("cinematic_prompt", "").lower() and "same hairstyle" in item.get("cinematic_prompt", "").lower() and "no text inside image" in item.get("cinematic_prompt", "").lower() for item in quick_data["scene_prompts"]["scene_prompts"]), "scene prompts missing full-screen continuity constraints")
        assert_true(all("storyboard" in item.get("prompt", "").lower() and "contact sheet" in item.get("hard_negative_prompt", "").lower() and "text" in item.get("hard_negative_prompt", "").lower() for item in quick_data["image_results"]), "hard negative image prompt rules missing")
        assert_true(all("realistic skin texture" in item.get("cinematic_prompt", "").lower() and "natural facial proportions" in item.get("cinematic_prompt", "").lower() and "avoid plastic ai faces" in item.get("cinematic_prompt", "").lower() for item in quick_data["scene_prompts"]["scene_prompts"]), "scene prompts missing cinematic realism layer")
        forbidden_filters = ["hstack", "vstack", "xstack", "tile", "grid", "collage"]
        assert_true(all(job.get("visual_composition_mode") == "single_fullscreen_scene" for job in quick_data["render"].get("scene_jobs", [])), "scene job is not single fullscreen")
        assert_true(all(job.get("timeline_playback_model") == "one_scene_one_fullscreen_clip" for job in quick_data["render"].get("scene_jobs", [])), "scene job is not isolated fullscreen timeline clip")
        assert_true(all(job.get("render_pipeline_version") == "cinematic_clean_v3" for job in quick_data["render"].get("scene_jobs", [])), "scene job used stale render pipeline")
        assert_true(any(job.get("cinematic_motion") for job in quick_data["render"].get("scene_jobs", [])), "motion metadata missing")
        assert_true(any(job.get("motion_effect") in {"emotional_push_in", "cinematic_drift", "slow_cinematic", "hook_energy_zoom"} for job in quick_data["render"].get("scene_jobs", [])), "cinematic motion effects missing")
        assert_true(all(not any(token in " ".join(str(part).lower() for part in (job.get("ffmpeg_command") or [])) for token in forbidden_filters) for job in quick_data["render"].get("scene_jobs", [])), "stacked/collage ffmpeg filter detected")
        pipeline_report_path = Path(quick_data["render"].get("render_pipeline_report_path", ""))
        assert_true(pipeline_report_path.exists(), "render_pipeline_report.json missing")
        pipeline_report = json.loads(pipeline_report_path.read_text(encoding="utf-8"))
        assert_true(pipeline_report.get("pipeline_model") == "one_scene_one_fullscreen_clip_then_timeline_concat", "render pipeline model incorrect")
        assert_true(pipeline_report.get("scene_clip_count") == len(quick_data["render"].get("scene_jobs", [])), "render pipeline scene count mismatch")
        assert_true(pipeline_report.get("forbidden_filters_found") is False, "render pipeline report found forbidden filters")
        assert_true((pipeline_report.get("fullscreen_validation") or {}).get("one_scene_per_clip") and (pipeline_report.get("fullscreen_validation") or {}).get("timeline_concat_only"), "fullscreen timeline validation failed")
        all_report_filters = json.dumps(pipeline_report.get("ffmpeg_filters_used", {})).lower()
        assert_true(not any(token in all_report_filters for token in forbidden_filters), "forbidden stack/tile filter in render pipeline report")
        scene_durations = [scene.get("duration") for scene in quick_data["package"].get("scene_sequence", [])]
        assert_true(len(set(scene_durations)) > 1 and any(scene.get("beat_timing") for scene in quick_data["package"].get("scene_sequence", [])), "beat timing did not affect scene pacing")
        assert_true(quick_data["beat_timing"].get("timing_profile") and quick_data["beat_timing"].get("hook_peak_moment") > 0 and quick_data["beat_timing"].get("emotional_curve"), "dynamic timing profile missing")
        tiktok_final_dir = Path(quick_data["tiktok_package"]["final_dir"])
        creator_assets = export_creator_final_assets("Quick Hook Smoke", workflow_song, tiktok_final_dir, workflow_mode="Song Studio Only")
        assert_true(creator_assets["ok"], "creator final assets export failed")
        for filename in ["final_hook_clip.mp4", "hook_audio.mp3", "subtitles.srt", "styled_subtitles.ass", "captions.txt", "hashtags.txt", "title.txt", "title_ideas.txt", "thumbnail.jpg", "thumbnail_score.json", "thumbnail_prompt.txt", "hook_analysis.json", "scene_director_plan.json", "cinematic_quality_report.json", "timeline_director.json", "scene_motion_map.json", "emotional_curve.json", "shot_progression.json", "scene_prompts.json", "beat_timing.json", "render_manifest.json", "render_stage.json", "image_generation_manifest.json", "scene_01.jpg", "scene_02.jpg", "scene_03.jpg", "upload_checklist.txt", "viral_timing_plan.json"]:
            assert_true((tiktok_final_dir / filename).exists(), f"TikTok package missing {filename}")
        assert_true((tiktok_final_dir / "debug" / "render_pipeline_report.json").exists(), "TikTok package missing debug/render_pipeline_report.json")
        assert_true((tiktok_final_dir / "debug" / "scene_generation_report.json").exists(), "TikTok package missing debug/scene_generation_report.json")
        assert_true((tiktok_final_dir / "debug" / "image_validation_report.json").exists(), "TikTok package missing debug/image_validation_report.json")
        assert_true((tiktok_final_dir / "debug" / "shot_variation_report.json").exists(), "TikTok package missing debug/shot_variation_report.json")
        assert_true((tiktok_final_dir / "debug" / "render_cleanup_report.json").exists(), "TikTok package missing debug/render_cleanup_report.json")
        assert_true((tiktok_final_dir / "video_generation_manifest.json").exists(), "TikTok package missing video_generation_manifest.json")
        for filename in ["suno_export.txt", "tiktok_caption.txt", "youtube_caption.txt", "hashtags.txt", "cover_prompt_1x1.txt", "cover_prompt_9x16.txt", "cover_prompt_16x9.txt", "upload_checklist.txt"]:
            path = tiktok_final_dir / filename
            assert_true(path.exists() and path.read_text(encoding="utf-8-sig").strip(), f"creator export package missing {filename}")
        assert_true("STYLE PROMPT FOR SUNO" in (tiktok_final_dir / "suno_export.txt").read_text(encoding="utf-8-sig"), "creator Suno TXT format missing")
        assert_true(validate_mp4(tiktok_final_dir / "final_hook_clip.mp4")["valid_mp4"], "TikTok package final MP4 not playable")
        strict_ai_video_clip = quick_generate_hook_clip(
            "Smoke Strict AI Video Clip",
            "ใช้ทั้งท่อนฮุกเต็มเพื่อทดสอบ AI Video mode แล้ว fallback อย่างปลอดภัย",
            image_provider="offline",
            voiceover_style="calm narrator",
            preset_id="emotional_story",
            hook_audio_path=hook_audio_trim["data"]["path"],
            video_generation_mode="ai_video_provider",
            video_settings={"provider": "gemini_veo", "gemini_api_key": ""},
        )
        ai_video_data = strict_ai_video_clip.get("data", {})
        assert_true(not strict_ai_video_clip["ok"] and strict_ai_video_clip.get("error"), "AI Video strict mode silently succeeded without provider")
        ai_video_manifest = json.loads(Path(ai_video_data["video_generation_manifest_path"]).read_text(encoding="utf-8"))
        assert_true(ai_video_manifest.get("mode_requested") == "ai_video_provider", "AI Video strict mode manifest missing")
        assert_true(ai_video_manifest.get("real_ai_video_used") is False and ai_video_manifest.get("provider_confirmed_live") is False, "AI Video strict mode fake-confirmed provider")
        assert_true(ai_video_manifest.get("fallback_used") is False and not ai_video_manifest.get("fallback_mode"), "AI Video strict mode allowed fallback")
        assert_true(Path(ai_video_data["provider_debug_path"]).exists(), "AI Video provider_debug.json missing")
        v2_plan = build_music_video_v2_shot_plan(full_hook_lyrics="hook line one\nhook line two\nhook line three", duration_seconds=8, mood="emotional")
        assert_true(4 <= len(v2_plan) <= 8 and all("single continuous cinematic video shot" in shot["prompt"].lower() for shot in v2_plan), "Music Video V2 shot plan failed")

        def fake_real_video_provider(prompt, duration_seconds, output_path, **kwargs):
            scene = {"scene_id": Path(output_path).stem, "duration": float(duration_seconds), "render_mode": "placeholder"}
            rendered = render_placeholder_scene(scene, output_path, aspect_ratio="9:16")
            validation = validate_mp4(output_path, min_duration=1.0, min_file_size=1)
            return {
                "ok": bool(rendered.get("ok") and validation.get("valid_mp4")),
                "message": "fake live provider generated MP4",
                "data": {"path": str(output_path), "provider_status": "complete", "real_ai_video_used": True, "validation": validation},
                "error": "" if rendered.get("ok") else rendered.get("error", "fake_provider_failed"),
            }

        v2_result = generate_music_video_v2(
            project_name="Smoke Music Video V2",
            song={"title": "Smoke V2", "artist_name": "VelaFlow", "mood": "emotional"},
            uploaded_audio_path=hook_audio_trim["data"]["path"],
            hook_start_time=0,
            hook_end_time=2,
            full_hook_lyrics="hook line one\nhook line two\nhook line three\nhook line four",
            provider="test_live_provider",
            video_settings={"gemini_api_key": "test-key"},
            video_provider_fn=fake_real_video_provider,
        )
        v2_data = v2_result.get("data", {})
        assert_true(v2_result["ok"] and validate_mp4(v2_data["final_mp4"], require_audio=True)["valid_mp4"], "Music Video V2 final MP4 failed")
        v2_validation = validate_mp4(v2_data["final_mp4"], require_audio=True)
        assert_true(v2_validation.get("has_video") and v2_validation.get("has_audio"), "Music Video V2 final streams missing")
        assert_true(abs(float(v2_validation.get("duration") or 0) - 2.0) < 0.8, "Music Video V2 duration did not match hook range")
        v2_manifest = json.loads(Path(v2_data["manifest_path"]).read_text(encoding="utf-8"))
        assert_true(v2_manifest.get("real_ai_video_used") is True and v2_manifest.get("provider_confirmed_live") is True and v2_manifest.get("fallback_used") is False, "Music Video V2 manifest did not enforce real provider")
        assert_true((Path(v2_data["final_dir"]) / "tiktok_caption.txt").exists() and (Path(v2_data["final_dir"]) / "hashtags.txt").exists(), "Music Video V2 creator assets missing")
        v2_fail = generate_music_video_v2(
            project_name="Smoke Music Video V2 Missing Provider",
            song={"title": "Smoke V2"},
            uploaded_audio_path=hook_audio_trim["data"]["path"],
            hook_start_time=0,
            hook_end_time=2,
            full_hook_lyrics="hook line one\nhook line two",
            provider="gemini_veo",
            video_settings={"gemini_api_key": ""},
        )
        v2_fail_manifest = json.loads(Path((v2_fail.get("data") or {}).get("manifest_path", "")).read_text(encoding="utf-8"))
        assert_true(not v2_fail["ok"] and v2_fail_manifest.get("fallback_used") is False and v2_fail_manifest.get("real_ai_video_used") is False, "Music Video V2 allowed fallback success")
        clip_v2_plan = build_clip_studio_v2_shot_prompts("full hook line one\nfull hook line two\nfull hook line three", hook_duration=8, mood_preset="emotional")
        assert_true(split_veo_shot_durations(20) == [8, 8, 4], "Clip Studio V2 did not split 20s hook into legal Veo shots")
        clip_v2_plan_20s = build_clip_studio_v2_shot_prompts("full hook line one\nfull hook line two\nfull hook line three", hook_duration=20, mood_preset="emotional")
        assert_true([shot["duration_seconds"] for shot in clip_v2_plan_20s] == [8, 8, 4], "Clip Studio V2 20s shot prompt durations are illegal")
        assert_true(all(4 <= int(shot["duration_seconds"]) <= 8 for shot in clip_v2_plan_20s), "Clip Studio V2 generated out-of-bound Veo duration")
        assert_true(1 <= len(clip_v2_plan) <= 3 and all(4 <= float(shot["duration_seconds"]) <= 8 for shot in clip_v2_plan) and all("no subtitle inside video" in shot["prompt"].lower() for shot in clip_v2_plan), "Clip Studio V2 shot prompt rules failed")

        def fake_clip_v2_provider(prompt, output_path, **kwargs):
            scene = {"scene_id": Path(output_path).stem, "duration": float(kwargs.get("duration_seconds") or 2), "render_mode": "placeholder"}
            rendered = render_placeholder_scene(scene, output_path, aspect_ratio="9:16")
            validation = validate_mp4(output_path, min_duration=1.0, min_file_size=1)
            return {
                "ok": bool(rendered.get("ok") and validation.get("valid_mp4")),
                "message": "test provider generated MP4",
                "data": {
                    "path": str(output_path),
                    "debug": {
                        "request_status": "submitted",
                        "polling_status": "done",
                        "download_status": "downloaded",
                        "request_payload": {"durationSeconds": int(kwargs.get("duration_seconds") or 0), "aspectRatio": kwargs.get("aspect_ratio", "9:16")},
                        "validation": validation,
                    },
                    "validation": validation,
                },
                "error": "" if rendered.get("ok") else rendered.get("error", "test_provider_failed"),
            }

        v2_source_audio = out / "hook_clip_projects" / "clip_studio_v2_source.mp3"
        subprocess.run(
            [
                find_ffmpeg(),
                "-y",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=6",
                "-c:a",
                "libmp3lame",
                str(v2_source_audio),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        clip_v2 = generate_clip_studio_v2(
            project_name="Smoke Clip Studio V2",
            song={"title": "Smoke Clip V2", "artist_name": "VelaFlow", "mood": "emotional"},
            uploaded_mp3_path=v2_source_audio,
            hook_start_time=0,
            hook_end_time=6,
            full_hook_lyrics="full hook line one\nfull hook line two\nfull hook line three",
            mood_preset="emotional",
            provider_settings={"gemini_api_key": "test-key"},
            video_provider_fn=fake_clip_v2_provider,
        )
        clip_v2_data = clip_v2.get("data", {})
        clip_v2_validation = validate_mp4(clip_v2_data["final_mp4"], require_audio=True)
        assert_true(clip_v2["ok"] and clip_v2_validation.get("valid_mp4") and clip_v2_validation.get("has_audio") and clip_v2_validation.get("has_video"), "Clip Studio V2 final MP4 validation failed")
        assert_true(clip_v2_validation.get("file_size", 0) > 500 * 1024, "Clip Studio V2 final MP4 too small")
        clip_v2_ass = Path(clip_v2_data["final_dir"]) / "styled_subtitles.ass"
        clip_v2_ass_text = clip_v2_ass.read_text(encoding="utf-8-sig")
        clip_v2_style = next(line for line in clip_v2_ass_text.splitlines() if line.startswith("Style: Default,"))
        clip_v2_style_parts = clip_v2_style.split(",")
        assert_true("PlayResX: 720" in clip_v2_ass_text and "PlayResY: 1280" in clip_v2_ass_text, "Clip Studio V2 subtitle ASS resolution missing")
        assert_true(int(clip_v2_style_parts[2]) <= 34 and int(clip_v2_style_parts[16]) <= 1 and clip_v2_style_parts[18] == "2" and int(clip_v2_style_parts[21]) >= 130, "Clip Studio V2 subtitles are not small bottom-safe cinematic style")
        clip_v2_manifest = json.loads(Path(clip_v2_data["manifest_path"]).read_text(encoding="utf-8"))
        assert_true(clip_v2_manifest.get("mode") == "clip_studio_v2" and clip_v2_manifest.get("real_ai_video_used") is True and clip_v2_manifest.get("provider_confirmed_live") is True and clip_v2_manifest.get("fallback_used") is False, "Clip Studio V2 manifest failed strict real-video flags")
        assert_true(all(4 <= int(duration) <= 8 for duration in clip_v2_manifest.get("shot_durations", [])) and clip_v2_manifest.get("max_shot_duration_seconds") == 8, "Clip Studio V2 did not enforce legal Veo shot durations")
        assert_true(all(4 <= int(payload.get("durationSeconds", 0)) <= 8 for payload in clip_v2_manifest.get("provider_request_payloads", [])), "Clip Studio V2 provider request payload sent illegal duration")
        assert_true(clip_v2_manifest.get("generated_shot_filenames") and clip_v2_manifest.get("concat_file_list"), "Clip Studio V2 debug shot filenames/concat file list missing")
        assert_true(clip_v2_manifest.get("status_flow") == ["submitting", "polling", "downloading", "muxing", "complete"], "Clip Studio V2 status flow missing")
        assert_true(abs(float(clip_v2_manifest.get("hook_duration") or 0) - 6.0) < 0.1, "Clip Studio V2 did not use full hook range")
        saved_video_env = {key: os.environ.pop(key, None) for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "VEO_API_KEY")}
        try:
            clip_v2_fail = generate_clip_studio_v2(
                project_name="Smoke Clip Studio V2 Missing Provider",
                song={"title": "Smoke Clip V2"},
                uploaded_mp3_path=v2_source_audio,
                hook_start_time=0,
                hook_end_time=6,
                full_hook_lyrics="full hook line one\nfull hook line two",
                provider_settings={"gemini_api_key": ""},
            )
        finally:
            for key, value in saved_video_env.items():
                if value is not None:
                    os.environ[key] = value
        clip_v2_fail_manifest = json.loads(Path((clip_v2_fail.get("data") or {}).get("manifest_path", "")).read_text(encoding="utf-8"))
        assert_true(not clip_v2_fail["ok"] and clip_v2_fail_manifest.get("fallback_used") is False and clip_v2_fail_manifest.get("final_video_path") == "", "Clip Studio V2 created fallback success")
        main_source = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
        creative_source = (ROOT / "core" / "creative_pack_generator.py").read_text(encoding="utf-8")
        assert_true(creative_source.count("def improve_hook_singability") == 1 and "ท่อนนี้ต้องจำได้ตั้งแต่ครั้งแรก" not in creative_source and "อารมณ์หลัก:" not in creative_source, "creative pack hook helper duplicate or unreachable fallback returned")
        assert_true("def _copy_to_clipboard_button" in main_source and "navigator.clipboard.writeText" in main_source and "document.execCommand('copy')" in main_source and "_clipboard_count" in main_source and "✓ Copied to clipboard" in main_source, "repeatable clipboard helper missing")
        assert_true('_copy_to_clipboard_button("Copy Lyrics for Suno"' in main_source and '_copy_to_clipboard_button("Copy Style for Suno"' in main_source and '_copy_to_clipboard_button("Copy Producer Notes"' in main_source, "Suno copy buttons are not wired to clipboard helper")
        assert_true("creative_pack_copy_suno_lyrics_button" not in main_source and "disabled=True" not in main_source[main_source.find("def _copy_to_clipboard_button"):main_source.find("def _restore_local_api_state")], "clipboard helper should not disable copy buttons")
        assert_true('"Save"' in main_source and '"Copy"' in main_source and '"Lyrics TXT"' in main_source and '"Suno TXT"' in main_source and '"Release Package"' in main_source, "creator lyric quick action bar buttons missing")
        assert_true('"Generate Viral Hooks"' in main_source and '"Try New Hooks"' in main_source and '"Reset Hooks"' in main_source, "creator hook button labels missing")
        assert_true("Full Hook Creator Package" in main_source and "song_creator_lyrics_editor" in main_source, "creator lyrics/package sections missing")
        assert_true("Song Completeness Score" in main_source and "Lyric Lines" in main_source and "Chorus Quality" in main_source and "Est. Duration" in main_source, "song completeness UI missing")
        assert_true("Music Direction Preview" in main_source and "Instrument Palette" in main_source and "Energy Curve" in main_source and "Arrangement Map" in main_source, "music direction preview UI missing")
        assert_true("Hook Preview" in main_source and "Full Hook Lyrics Preview" in main_source and "Creator Export Mode" in main_source and "Prompt Style" in main_source, "creator hook preview/mode controls missing")
        assert_true("Quick Start" in main_source and "Example Creator Workflows" in main_source and "Generate Full Creator Package" in main_source, "closed-beta quick start/package button missing")
        assert_true("Recommended Setup" in main_source and "Best Tool" in main_source and "Suggested Hook" in main_source, "creator recommendation block missing")
        assert_true("Creator Package Ready" in main_source and "Recommended next step: use Flow or Kling" in main_source, "creator success summary missing")
        assert_true("Included creator files" in main_source and "Scene Breakdown" in main_source and "Cinematic Scene Plan" in main_source, "mobile collapsible package sections missing")
        assert_true("filter_visible_projects(all_managed_projects" in main_source and "is_test_project_name" in main_source and "เพลงใหม่ของฉัน" in main_source, "sidebar project filtering/default project cleanup missing")
        assert_true("Remaster Studio" in main_source and "Polish finished AI songs for clearer vocal, better loudness, and streaming-ready WAV/MP3 export." in main_source and "1. Upload Audio" in main_source and "4. Process Audio" in main_source and "Download Mastered WAV" in main_source and "Download Mastered MP3" in main_source, "Remaster Studio UI missing")
        assert_true("Preset Selection" in main_source and "Auto Recommended" in main_source and "Analyze Audio & Recommend Preset" in main_source and "Use Recommended Preset" in main_source and "Choose Manually" in main_source and "Recommended by VelaFlow" in main_source and "Custom / Advanced preset controls are coming later" in main_source, "Remaster auto preset recommendation UI missing")
        assert_true("Audio Editor" in main_source and "MP3 only. Output is MP3." in main_source and "Lossless Quick Cut" in main_source and "Precise Cut" in main_source and "Waveform Timeline" in main_source and "Export Hook MP3" in main_source and "Download Hook MP3" in main_source, "Audio Editor UI missing")
        assert_true("Use Project Master (Recommended)" in main_source and "Upload External MP3" in main_source and "Current Audio Source" in main_source and "No remastered master found." in main_source and "active_master" in main_source and "_project_master_audio" in main_source and "_render_music_pipeline_status" in main_source, "Project Master source workflow UI/state missing")
        assert_true("Smart Hook Finder" in main_source and "Analyze Hook Candidates" in main_source and "Use This Hook" in main_source and "Preview Candidate" in main_source and "Batch Hook Export" in main_source and "Export Selected Durations" in main_source and "Download All as ZIP" in main_source, "Audio Editor V2 smart hook/batch UI missing")
        assert_true("Creator Dashboard" in main_source and "Start Music Creation" in main_source and "Seed Selection workflow" in main_source, "creator dashboard single-path card missing")
        assert_true("Create TikTok Hook" not in main_source and "Create Podcast Clip" not in main_source and "Create Affiliate Script" not in main_source and "Generate Song Package" not in main_source, "legacy creator dashboard workflows still visible")
        assert_true("Quick Song" in main_source and "_render_quick_song" in main_source and "Suno Package" in main_source and "A. Lyrics" in main_source and "B. Music Style Prompt" in main_source, "Quick Song or Suno package UI missing")
        assert_true("AI Creative Pack Generator" in main_source and "Generate Song" in main_source and "Generate Final Release Pack" in main_source and "No Render" in main_source and "Advanced Song Studio for quality-first lyrics, hooks, producer prompts, and release packs. Render outside with your favorite tools." in main_source and "แนวเพลงหลัก" in main_source and "ชื่อศิลปิน" in main_source, "creative pack generator UI missing")
        assert_true("Song Idea → Generate Song → Select Story/Hook/Title → Generate Final Release Pack" in main_source and "Selected Seed" in main_source and "View all candidate details" in main_source, "creative pack single-path workflow missing")
        assert_true("AI Quality Mode" in main_source and "VelaFlow เลือกค่าที่เหมาะสมให้อัตโนมัติ" in main_source and "Reset to Recommended" in main_source and "Advanced Creative Controls" in main_source and "Manual Override Active" in main_source and "AI Quality Mode: Auto Optimized" not in main_source, "creative pack AI control cleanup missing")
        assert_true("แนวดนตรี" in main_source and "อารมณ์เพลง" in main_source and "ประเภทเรื่องราว" in main_source and "รูปแบบฮุก" in main_source and "ป๊อปร็อกอารมณ์ลึก" in main_source and "อินดี้อบอุ่น" in main_source, "Thai creator UI labels/options missing")
        assert_true("Generate Song Seeds" not in main_source and "Generate Full Lyrics from Selected Seed" not in main_source and "Generate Final Song" not in main_source, "old duplicate song generation actions still visible")
        assert_true("API_QUALITY_WARNING" in main_source and "_show_api_quality_stop" in main_source, "API quality gate warning missing from UI")
        assert_true("Gemini API Key" in main_source and "Gemini status:" in main_source and "Key source:" in main_source and "Gemini configure() result:" in main_source and "Gemini client initialization result:" in main_source and "Test Gemini Connection" in main_source, "Gemini settings diagnostics UI missing")
        assert_true("Creative Guidance" in main_source and "Songwriting Quality" in main_source and "Suno/Udio Export" in main_source, "creative pack advanced song studio guidance missing")
        assert_true("sidebar_nav_song_studio_workspace" in main_source and "sidebar_nav_audio_editor_workspace" in main_source and "sidebar_nav_remaster_studio_workspace" in main_source and "sidebar_nav_visual_studio" in main_source and "sidebar_nav_release_pack" in main_source and "sidebar_nav_ai_settings" in main_source, "workspace sidebar navigation missing")
        assert_true("One Click Creator Flow" in main_source and "Generate Creator Package" in main_source and "Hook Comparison Cards" in main_source, "One Click Creator Flow UI missing")
        assert_true("analyzing song" in main_source and "detecting hook" in main_source and "generating prompts" in main_source and "remastering audio" in main_source and "building creator package" in main_source and "complete" in main_source, "one-click progress stages missing")
        assert_true("VelaFlow Closed Beta" in main_source and "Founding Member" in main_source and "Creator tips" in main_source and "Send beta feedback" in main_source, "closed beta premium creator elements missing")
        assert_true("Clean Project List" in main_source and "Favorite Projects" in main_source and "Recent Projects" in main_source and "Duplicate Project" in main_source, "clean/favorite/recent project UI missing")
        assert_true("Retry Export ZIP" in main_source and "Creator Delivery" in main_source and "Hook Ready" in main_source and "Prompt Package Ready" in main_source and "Remastered Audio Ready" in main_source, "creator delivery/retry UX missing")
        assert_true("Play Original" in main_source and "Play Mastered" in main_source and "A/B Compare" in main_source, "before/after comparison player missing")
        assert_true("Download Creator ZIP" in main_source and "Copy Thumbnail Prompt" in main_source, "premium delivery buttons missing")
        assert_true("Flow Prompt" in main_source and "Veo Prompt" in main_source and "Runway Prompt" in main_source and "Kling Prompt" in main_source and "Image Prompt" in main_source and "Thumbnail Prompt" in main_source, "copy-ready prompt boxes missing")
        assert_true("Product Analyzer" in main_source and "Viral Hook Generator" in main_source and "TikTok Script Studio" in main_source and "Creator Package Export" in main_source and "Trending Ideas" in main_source, "Affiliate Studio MVP sections missing")
        assert_true("🔥 Affiliate Trend Finder" in main_source and "Generate Trend Ideas" in main_source and "Export Trend Package ZIP" in main_source, "Affiliate Trend Finder UI missing")
        assert_true("def render_agent_studio(" in main_source and "def _render_agent_workspace_panel(" in main_source and 'elif page == "VelaFlow Agent Studio":' in main_source and "render_agent_studio(project)" in main_source and "Agent Studio failed to initialize" in main_source and "st.exception(exc)" in main_source, "Agent Studio render route/fallback missing")
        assert_true("Creator Navigation" in main_source and "sidebar_nav_song_studio" in main_source and "sidebar_nav_clip_studio" in main_source and "sidebar_nav_remaster_studio" in main_source and "sidebar_nav_agent_studio" in main_source and "Agent Studio Loaded" in main_source, "Agent Studio visible sidebar navigation missing")
        assert_true("VelaFlow Agent Studio" in main_source and "Generate Agent Package" in main_source and "พิมพ์ไอเดียของคุณ" in main_source and "Download Agent Package TXT" in main_source and "Workflow mode" in main_source and "Use Agent Memory" in main_source and "Clear Agent Memory" in main_source and "AI Provider" in main_source and "Auto Workflow" in main_source and "Multi-Agent Mode" in main_source and "Brain Analysis" in main_source and "Execution Plan" in main_source and "Active Agents" in main_source and "Agent Collaboration Log" in main_source and "Director Decisions" in main_source and "Agent Actions" in main_source and "Generated Files" in main_source and "Project Sidebar" in main_source and "Recent Projects" in main_source and "Create Project" in main_source and "Continue Project" in main_source and "Project Timeline" in main_source and "Workspace Summary" in main_source and "Asset Browser" in main_source and "Storyboard Viewer" in main_source and "Media Timeline" in main_source and "Cover History" in main_source and "Asset Tags" in main_source and "Project Asset Summary" in main_source and "Export ZIP" in main_source and "run_agent_workflow" in main_source, "Agent Studio UI missing")
        assert_true("Video Prompt Studio" in main_source and "Generate Storyboard + AI Video Prompts" in main_source and "Copy Whisk Prompt" in main_source and "Copy Video Prompt" in main_source and "Copy Full Shot Package" in main_source and "Download TXT" in main_source, "Video Prompt Studio UI missing")
        assert_true("Character Studio" in main_source and "Generate Character Pack" in main_source and "Download Character Pack TXT" in main_source and "Copy-Ready Prompts" in main_source and "Apply character to existing storyboard" in main_source, "Character Studio UI missing")
        assert_true("Podcast Script Studio" in main_source and "Generate Podcast Script Package" in main_source and "AI Voice Version" in main_source and "Download Podcast Script TXT" in main_source and "Gemini Story Writer when configured. No rendering, no TTS, no video generation." in main_source, "Podcast Script Studio UI missing")
        assert_true("Generate Affiliate Creator Package" in main_source and "Download Affiliate Creator Package ZIP" in main_source, "Affiliate package creator UX missing")
        assert_true("No posting bots" in main_source and "no login automation" in main_source and "no heavy scraping" in main_source, "Affiliate safety wording missing")
        assert_true("Manual Product Mode" in main_source and "Product Benefits" in main_source and "Creator Notes" in main_source, "affiliate manual product mode missing")
        assert_true("ไม่สามารถดึงข้อมูลจากลิงก์นี้ได้ กรุณาวางชื่อสินค้า/รายละเอียดสินค้าเอง" in main_source and "Checking product page" in main_source and "Developer extraction details" in main_source and "resolved_url" in main_source, "affiliate extraction warning/loading UI missing")
        assert_true("ลิงก์ Shopee แบบย่อบางรายการ" in main_source and "extracted_title_exists" in main_source and "failure_reason" in main_source and "Manual Product Mode is ready" in main_source, "affiliate manual fallback/debug UX missing")
        assert_true("Founding Member build" in main_source and "Creator actions" in main_source and "Hooks Ready" in main_source and "Creator ZIP Ready" in main_source, "affiliate closed beta delivery UI missing")
        assert_true("**Step 1-2: Hook Candidates**" not in main_source and "Generate Hook Candidates" not in main_source and "Regenerate Hooks" not in main_source and "Clear Hook Cache" not in main_source and "Package files:" not in main_source, "developer-style hook/package labels still visible")
        v2_button_pos = main_source.find('"Generate Real AI Video Clip"')
        legacy_button_pos = main_source.find('"Quick Generate TikTok Hook"')
        developer_guard_pos = main_source.find('if not st.session_state.get("developer_mode"):', v2_button_pos)
        legacy_section_pos = main_source.find('"## Developer Legacy Hook Clip Path"', v2_button_pos)
        v2_call_pos = main_source.find("generate_clip_studio_v2(", v2_button_pos)
        legacy_call_pos = main_source.find("quick_generate_hook_clip(", legacy_section_pos)
        image_provider_pos = main_source.find("_image_provider_controls(\"song_short_clip\")", v2_button_pos)
        assert_true(v2_button_pos > 0 and v2_call_pos > v2_button_pos, "Creator Mode V2 button is not wired to clip_studio_v2")
        assert_true("submitting → polling → downloading → muxing → complete" in main_source, "Clip Studio V2 status text missing")
        assert_true(developer_guard_pos > v2_button_pos and legacy_section_pos > developer_guard_pos and legacy_button_pos > legacy_section_pos, "Legacy quick generate is not hidden behind Developer Mode")
        assert_true(legacy_call_pos > legacy_section_pos, "Legacy quick generate call moved outside developer section")
        assert_true(image_provider_pos > legacy_section_pos, "Image Provider selector is visible before developer legacy section")
        assert_true("generate_music_video_v2(" not in main_source, "Frontend still routes to older music_video_v2 wrapper")
        affiliate_product = {
            "product_name": "Smoke Pillow",
            "product_type": "home item",
            "target_audience": "คนทำงานที่นอนหลับยาก",
            "emotional_angle": "นอนสบายขึ้น",
            "pain_point": "ปวดคอหลังตื่นนอน",
            "cta_style": "soft sell",
        }
        affiliate_link = analyze_product_link("https://www.amazon.com/example-product", "warm desk lamp, price 399, rating 4.8", fetch=False)
        assert_true(affiliate_link["ok"] and affiliate_link["data"]["platform"] == "amazon" and affiliate_link["data"]["keywords"], "affiliate URL parsing failed")
        assert_true(detect_product_platform("https://s.shopee.co.th/abc") == "shopee" and detect_product_platform("https://vt.tiktok.com/abc") == "tiktok_shop", "affiliate short platform detection failed")
        class FakeResponse:
            def __init__(self, url, text, status_code=200):
                self.url = url
                self.text = text
                self.status_code = status_code
            def raise_for_status(self):
                if self.status_code >= 400:
                    raise product_link_analyzer.requests.HTTPError(f"HTTP {self.status_code}")

        saved_get = product_link_analyzer.requests.get
        try:
            def fake_get_empty(url, **kwargs):
                return FakeResponse(url, "<html><head></head><body></body></html>")
            product_link_analyzer.requests.get = fake_get_empty
            empty_result = analyze_product_link("https://www.amazon.com/empty-product", fetch=True)
            assert_true(empty_result["data"]["extracted_success"] is False and not empty_result["data"]["title"] and empty_result["data"]["manual_fallback_message"], "affiliate empty extraction false success failed")

            def fake_get_redirect(url, **kwargs):
                return FakeResponse(
                    "https://shopee.co.th/final-product",
                    '<html><head><meta property="og:title" content="Redirected Shopee Bottle"><meta property="og:description" content="Keeps drinks cold"><meta property="og:image" content="https://img.example/bottle.jpg"><meta property="product:price:amount" content="199"></head></html>',
                )
            product_link_analyzer.requests.get = fake_get_redirect
            redirected = analyze_product_link("https://s.shopee.co.th/short", fetch=True)
            assert_true(redirected["data"]["original_url"].startswith("https://s.shopee") and redirected["data"]["resolved_url"].endswith("final-product") and redirected["data"]["title"] == "Redirected Shopee Bottle" and redirected["data"]["price"] == "199" and redirected["data"]["extracted_success"] is True, "affiliate short URL redirect extraction failed")

            def fake_get_title(url, **kwargs):
                return FakeResponse(url, "<html><head><title>Plain Title Product</title></head><body>sample</body></html>")
            product_link_analyzer.requests.get = fake_get_title
            title_fallback = analyze_product_link("https://www.amazon.com/plain-title", fetch=True)
            assert_true(title_fallback["data"]["title"] == "Plain Title Product" and title_fallback["data"]["extraction_status"] == "partial_metadata" and title_fallback["data"]["extracted_success"] is True, "affiliate HTML title fallback failed")

            def fake_get_jsonld(url, **kwargs):
                return FakeResponse(url, '<script type="application/ld+json">{"@type":"Product","name":"Schema Product","description":"Schema description","image":"https://img.example/schema.jpg","offers":{"price":"299"},"category":"Beauty"}</script>')
            product_link_analyzer.requests.get = fake_get_jsonld
            schema_result = analyze_product_link("https://www.amazon.com/schema-product", fetch=True)
            assert_true(schema_result["data"]["title"] == "Schema Product" and schema_result["data"]["category"] == "Beauty" and schema_result["data"]["extraction_source"]["title"] == "json_ld", "affiliate JSON-LD extraction failed")

            def fake_get_timeout(url, **kwargs):
                raise product_link_analyzer.requests.Timeout("timed out")
            product_link_analyzer.requests.get = fake_get_timeout
            timeout_result = analyze_product_link("https://www.amazon.com/timeout", fetch=True, timeout_seconds=0.01, retry_count=1)
            assert_true(timeout_result["data"]["extraction_status"] == "metadata_unavailable" and timeout_result["data"]["manual_fallback_message"], "affiliate timeout fallback failed")
        finally:
            product_link_analyzer.requests.get = saved_get
        unsupported_link = analyze_product_link("https://example.invalid/item", "manual fallback", fetch=False)
        assert_true(unsupported_link["data"]["extraction_status"] in {"manual_fallback", "unsupported_domain"} and unsupported_link["data"]["supported_domain"] is False, "affiliate unsupported domain handling failed")
        invalid_link = analyze_product_link("not-a-url", "manual fallback", fetch=True)
        assert_true(invalid_link["data"]["extraction_status"] == "invalid_url" and invalid_link["data"]["manual_fallback_message"], "affiliate invalid URL handling failed")
        affiliate_manual = analyze_product_link("", "manual fallback product", fetch=False)
        assert_true(not affiliate_manual["ok"] and affiliate_manual["data"]["platform"] == "unknown", "affiliate manual fallback state failed")
        affiliate_analysis = analyze_affiliate_product(affiliate_product)
        assert_true(all(0 <= int(score) <= 100 for score in affiliate_analysis["scores"].values()) and affiliate_analysis["recommended_content_style"] and affiliate_analysis["recommendation_labels"], "affiliate product intelligence failed")
        affiliate_hooks = generate_affiliate_hooks(affiliate_product, "TikTok Affiliate")
        assert_true(AFFILIATE_MODES[0] == "TikTok Affiliate" and len(affiliate_hooks) >= 7 and {item["hook_type"] for item in affiliate_hooks} >= {"shock", "curiosity", "pain_point", "problem_solution", "emotional", "social_proof", "urgency"} and affiliate_hooks[0]["hook_strength"] > 0, "affiliate hooks failed")
        assert_true({item["hook_type"] for item in affiliate_hooks} >= {"pov", "before_after", "tiktok_opener"}, "affiliate MVP hook categories missing")
        product_prompts = build_product_scene_prompts(affiliate_product, "TikTok Affiliate")
        assert_true(len(product_prompts["scene_prompts"]) == 3 and "vertical 9:16" in product_prompts["scene_prompts"][0]["prompt"] and "hand interaction" in product_prompts["scene_prompts"][0]["prompt"], "product prompt engine failed")
        affiliate_captions = build_affiliate_caption_package(affiliate_product, affiliate_hooks)
        assert_true(affiliate_captions["captions"] and affiliate_captions["hashtags"] and affiliate_captions["cta_variants"] and affiliate_captions["cta_optimization"].get("fomo_cta"), "affiliate captions failed")
        affiliate_scripts = build_affiliate_scripts(affiliate_product, affiliate_hooks)
        assert_true(all(affiliate_scripts.get(key) for key in ["tiktok_script_15s", "tiktok_script_30s", "pov_script", "review_script", "emotional_sell_script", "aesthetic_script"]), "affiliate scripts failed")
        affiliate_shots = build_affiliate_shot_list(affiliate_product, affiliate_hooks)
        assert_true(affiliate_shots["shot_list"] and "scene_01" not in affiliate_shots["scene_breakdown"] and "Visual:" in affiliate_shots["scene_breakdown"], "affiliate shot list failed")
        affiliate_timing = create_affiliate_retention_timing(duration=20, hook_type="urgency")
        assert_true(affiliate_timing["first_3_seconds"]["cut_at"] <= 2.2 and affiliate_timing["cta_timing"]["start"] > 0 and affiliate_timing["retention_estimate"] > 0, "affiliate retention timing failed")
        affiliate_brief = build_affiliate_clip_brief(affiliate_product, "TikTok Affiliate")
        assert_true(affiliate_brief["viral_score"]["conversion_potential"] > 0 and affiliate_brief["retention_timing"]["cta_timing"]["start"] > 0, "affiliate viral score failed")
        assert_true(all(affiliate_brief.get("quality_report", {}).values()), "affiliate output quality report failed")
        affiliate_export = export_affiliate_package("Smoke Affiliate Clip", affiliate_brief, {})
        affiliate_dir = Path((affiliate_export.get("data") or {}).get("final_dir", ""))
        affiliate_zip = Path((affiliate_export.get("data") or {}).get("zip_path", ""))
        required_affiliate_files = [
            "analysis/product_summary.txt",
            "analysis/viral_analysis.txt",
            "analysis/hook_scores.json",
            "hooks/viral_hooks.txt",
            "hooks/emotional_hooks.txt",
            "hooks/curiosity_hooks.txt",
            "scripts/tiktok_script_15s.txt",
            "scripts/tiktok_script_30s.txt",
            "scripts/pov_script.txt",
            "scripts/review_script.txt",
            "creator/captions.txt",
            "creator/hashtags.txt",
            "captions/captions.txt",
            "captions/hashtags.txt",
            "captions/cta_variants.txt",
            "creator/shot_list.json",
            "creator/scene_breakdown.txt",
            "creator/thumbnail_prompt.txt",
            "creator/creator_tips.txt",
            "README_START_HERE.txt",
            "manifest/affiliate_package_manifest.json",
        ]
        assert_true(affiliate_export["ok"] and affiliate_zip.exists() and all((affiliate_dir / name).exists() for name in required_affiliate_files), "affiliate creator package structure failed")
        manual_product = {**affiliate_product, "product_name": "Manual Smoke Product", "description": "manual description", "benefits": "simple benefit"}
        manual_export = export_affiliate_package("Smoke Manual Affiliate", build_affiliate_clip_brief(manual_product, "TikTok Affiliate"), {})
        assert_true(manual_export["ok"] and Path((manual_export.get("data") or {}).get("zip_path", "")).exists(), "manual affiliate package export failed")
        with zipfile.ZipFile(affiliate_zip) as archive:
            assert_true(all(name in archive.namelist() for name in required_affiliate_files), "affiliate ZIP contents failed")
        affiliate_manifest = json.loads((affiliate_dir / "manifest/affiliate_package_manifest.json").read_text(encoding="utf-8"))
        assert_true(affiliate_manifest["automation_policy"].startswith("No posting automation") and affiliate_manifest["package_version"] == "affiliate_mvp_1" and affiliate_manifest["export_status"] == "complete", "affiliate manifest failed")
        assert_true({item["category"] for item in TRENDING_AFFILIATE_IDEAS} >= {"Beauty", "Home", "Kitchen", "Pet", "Fashion", "Wellness", "Gadgets", "Organization"} and all("easy_to_shoot" in item and "emotional_sell" in item and "before_after_strength" in item for item in TRENDING_AFFILIATE_IDEAS), "affiliate trending ideas failed")
        trend_result = find_affiliate_trends("TikTok Shop", "Gadget", "Problem/Solution", "Office Workers", "Budget", count=5)
        trend_ideas = trend_result.get("ideas", [])
        assert_true(trend_result["ok"] and len(trend_ideas) == 5 and all(0 <= item["trend_score"] <= 100 for item in trend_ideas), "affiliate trend generation failed")
        assert_true(all(key in trend_ideas[0] for key in ["product_name", "competition_level", "why_it_may_convert", "viral_hooks", "cta_lines", "thumbnail_ideas", "shot_ideas", "creator_notes"]), "affiliate trend output structure failed")
        empty_trend = find_affiliate_trends("", "", "", "", "", count=1)
        assert_true(empty_trend["filters"]["platform"] == "Multi Platform" and empty_trend["ideas"], "affiliate trend empty-input fallback failed")
        trend_export = export_trend_package("Smoke Affiliate Trends", trend_result)
        trend_dir = Path((trend_export.get("data") or {}).get("final_dir", ""))
        trend_zip = Path((trend_export.get("data") or {}).get("zip_path", ""))
        required_trend_files = ["trend_report.txt", "viral_hooks.txt", "cta_lines.txt", "thumbnail_ideas.txt", "shot_ideas.txt", "creator_notes.txt", "trend_manifest.json"]
        assert_true(trend_export["ok"] and trend_zip.exists() and all((trend_dir / name).exists() for name in required_trend_files), "affiliate trend ZIP export failed")
        trend_manifest = json.loads((trend_dir / "trend_manifest.json").read_text(encoding="utf-8"))
        assert_true(trend_manifest["local_first"] is True and trend_manifest["automation_policy"].startswith("No scraping automation"), "affiliate trend manifest failed")
        video_prompt_package = build_video_prompt_package(
            project_type="Music MV",
            main_idea="ฝนตกในห้องเก่า\nยังคิดถึงเธออยู่",
            mood="sad pop",
            visual_style="rainy cinematic apartment",
            target_platform="Google Whisk",
            clip_length="15s",
            reference_style_notes="same woman, same room, warm shadow",
        )
        assert_true(video_prompt_package["ok"] and len(video_prompt_package["scene_list"]) == 3 and "Google Whisk" in video_prompt_package["video_prompt"], "video prompt studio package failed")
        video_prompt_blocked = build_video_prompt_package(
            project_type="Music MV",
            main_idea="ฝนตกในห้องเก่า",
            mood="sad pop",
            visual_style="rainy cinematic apartment",
            target_platform="Google Whisk",
            clip_length="15s",
            production_mode=True,
            api_key="",
            demo_mode=False,
        )
        assert_true(not video_prompt_blocked["ok"] and video_prompt_blocked["provider_status"]["status"] == STATUS_MISSING_KEY, "Video Prompt Studio production generation silently allowed missing API")
        assert_true(video_prompt_package["provider_status"]["status"] == "Offline Demo Mode" and "Demo / Offline Preview" in video_prompt_package_to_text(video_prompt_package), "Video Prompt Studio demo output is not clearly labeled")
        assert_true(all(video_prompt_package.get("quality_report", {}).values()), "video prompt quality report failed")
        assert_true("no text" in video_prompt_package["negative_prompt"].lower() and "vertical 9:16" in video_prompt_package["whisk_prompt"], "video prompt safety/framing failed")
        assert_true("Sad Pop MV" in VIDEO_PROMPT_PRESETS and "WHISK IMAGE PROMPT" in video_prompt_package_to_text(video_prompt_package), "video prompt preset/text export failed")
        assert_true(len(list_shorts_variations()) == 5 and list_shorts_variations()[0]["variation_id"] == "v1_emotional", "shorts variation list failed")
        shorts_result = generate_shorts_factory(
            "Smoke Shorts Factory",
            affiliate_brief["prompt"],
            source_workflow="seller",
            workflow_type="clips",
            image_provider="offline",
            max_variations=5,
        )
        shorts_data = shorts_result.get("data", {})
        shorts_comparison = shorts_data.get("comparison", {})
        shorts_export = shorts_data.get("export", {})
        assert_true(shorts_result["ok"] and shorts_comparison.get("successful_count") == 5 and len(shorts_comparison.get("scores", [])) == 5, "shorts factory generation failed")
        assert_true(shorts_comparison.get("best_variation_type") and shorts_comparison.get("top_hook_category") is not None, "shorts factory comparison failed")
        shorts_dir = Path(shorts_export.get("final_dir", ""))
        for variation in list_shorts_variations():
            mp4_path = shorts_dir / f"{variation['variation_id']}.mp4"
            assert_true(mp4_path.exists() and validate_mp4(mp4_path)["valid_mp4"], f"shorts factory MP4 failed for {variation['variation_id']}")
        for filename in ["shorts_factory_comparison.json", "hook_reports.json", "cta_reports.json", "viral_score_comparison.json", "shorts_factory_manifest.json"]:
            assert_true((shorts_dir / filename).exists(), f"shorts factory export missing {filename}")
        comparison_sample = build_shorts_comparison(shorts_data.get("results", []))
        assert_true(comparison_sample.get("best_overall") and comparison_sample.get("most_successful_pacing_profile") is not None, "shorts comparison helper failed")
        cache_key = (quick_data.get("render_cache") or {}).get("cache_key")
        assert_true(load_render_cache("Smoke Quick Hook Clip", "clips", cache_key)["ok"], "render cache was not saved")
        queue_start = start_render_job("Smoke Queue Clip", "clips", stage="smoke_render")
        assert_true(queue_start["ok"] and active_render_job("Smoke Queue Clip", "clips"), "creator render queue start failed")
        queue_duplicate = start_render_job("Smoke Queue Clip", "clips", stage="smoke_render")
        assert_true(not queue_duplicate["ok"] and queue_duplicate["error"] == "active_render_job", "creator render queue duplicate lock failed")
        queue_job_id = queue_start["data"]["job"]["job_id"]
        queue_done = complete_render_job("Smoke Queue Clip", "clips", queue_job_id, status="completed", result={"final_mp4": quick_data["final_mp4"]})
        assert_true(queue_done["ok"] and not active_render_job("Smoke Queue Clip", "clips"), "creator render queue completion failed")
        assert_true(load_creator_render_queue("Smoke Queue Clip", "clips")["data"]["jobs"], "creator render queue persisted jobs missing")
        assert_true(release_stale_render_jobs("Smoke Queue Clip", "clips", timeout_seconds=60)["ok"], "stale render release failed")
        recovery = recover_partial_render("Smoke Quick Hook Clip", "clips")
        assert_true(recovery["ok"] and recovery["data"]["latest_successful_render"], "partial render recovery failed")
        recovery_plan = build_recovery_plan("Smoke Quick Hook Clip", "clips", last_error="missing_scene_clips")
        assert_true("Scene videos could not be created" in recovery_plan["data"]["safe_error_message"], "friendly recovery message failed")
        assert_true("already rendering" in friendly_error_message("active_render_job").lower(), "friendly duplicate render message failed")
        storage = project_storage_summary("Smoke Quick Hook Clip", "clips")
        assert_true(storage["ok"] and storage["data"]["storage_bytes"] > 0 and storage["data"]["latest_successful_render"], "project storage summary failed")
        broken_scene = workflow_project_root("clips") / "Smoke_Quick_Hook_Clip" / "scenes" / "scene_99.mp4"
        broken_scene.parent.mkdir(parents=True, exist_ok=True)
        broken_scene.write_bytes(b"broken")
        temp_file = workflow_project_root("clips") / "Smoke_Quick_Hook_Clip" / "exports" / "scratch_tmp.mp4"
        temp_file.parent.mkdir(parents=True, exist_ok=True)
        temp_file.write_bytes(b"temp")
        cleanup = cleanup_project_storage("Smoke Quick Hook Clip", "clips", keep_versions=3, dry_run=False)
        assert_true(cleanup["ok"] and not broken_scene.exists() and not temp_file.exists(), "safe storage cleanup failed")
        autosave = autosave_project_state("Smoke Quick Hook Clip", "clips", {"title": "Smoke Quick Hook Clip", "song": {"short_clip": True}})
        assert_true(autosave["ok"] and Path(autosave["data"]["path"]).exists(), "project autosave failed")
        restored_autosave = load_autosave_project_state("Smoke Quick Hook Clip", "clips")
        assert_true(restored_autosave["ok"] and restored_autosave["data"]["snapshot"]["payload"]["title"] == "Smoke Quick Hook Clip", "project autosave restore failed")
        health = project_health_summary("Smoke Quick Hook Clip", "clips")
        assert_true(health["ok"] and health["data"]["render_status"] and health["data"]["storage_usage"] and "render_success_rate" in health["data"], "project health summary failed")
        quick_clip_cached = quick_generate_hook_clip(
            "Smoke Quick Hook Clip",
            "เธ—เธ”เธชเธญเธเธเธฅเธดเธเธชเธฑเนเธเนเธเธงเธ•เธฑเนเธเธชเธณเธซเธฃเธฑเธ VelaFlow",
            image_provider="offline",
            voiceover_style="calm narrator",
            preset_id="viral_meme",
            hook_audio_path=hook_audio_trim["data"]["path"],
            force_final_render=True,
        )
        cached_data = quick_clip_cached.get("data", {})
        assert_true(quick_clip_cached["ok"] and (cached_data.get("render_cache") or {}).get("cache_hit"), "render cache reuse failed")
        assert_true((cached_data.get("clip_version") or {}).get("version_id") == "v2", "clip version v2 missing")
        quick_clip_alt = quick_generate_hook_clip(
            "Smoke Quick Hook Clip",
            "เธ—เธ”เธชเธญเธเธเธฅเธดเธเธชเธฑเนเธเนเธเธงเธ•เธฑเนเธเธชเธณเธซเธฃเธฑเธ VelaFlow",
            image_provider="offline",
            voiceover_style="calm narrator",
            preset_id="viral_meme",
            hook_audio_path=hook_audio_trim["data"]["path"],
            force_cache_refresh=True,
            variation="alternate",
        )
        assert_true(quick_clip_alt["ok"] and (quick_clip_alt.get("data", {}).get("clip_version") or {}).get("version_id") == "v3", "alternate version generation failed")
        versions = list_clip_versions("Smoke Quick Hook Clip", "clips")
        assert_true(len(versions) >= 3 and all(Path(item.get("final_mp4", "")).exists() for item in versions[-3:]), "clip version list failed")
        for utf8_bom_file in ["subtitles.srt", "styled_subtitles.ass", "captions.txt"]:
            assert_true((tiktok_final_dir / utf8_bom_file).read_bytes().startswith(b"\xef\xbb\xbf"), f"{utf8_bom_file} is not UTF-8 BOM")
        assert_true("TikTok Meme" in list_viral_subtitle_presets() and get_viral_subtitle_preset("Affiliate CTA")["mode"] == "meme_caption", "viral subtitle presets missing")
        assert_true(get_viral_subtitle_preset("TikTok Meme")["mode"] != get_viral_subtitle_preset("Karaoke Glow")["mode"], "subtitle presets do not differ")
        prompt_sample = build_scene_prompt("เดินต่อทั้งที่ยังเจ็บ", style="Anime Nostalgia")
        assert_true("visual metaphor" in prompt_sample["cinematic_prompt"] and prompt_sample["prompt_style"] == "Anime Nostalgia", "scene prompt engine failed")
        beat_sample = create_beat_timing_plan(total_duration=15, scene_count=3, pace="fast")
        assert_true(beat_sample["scene_timing"][0]["motion_sync"] == "beat_zoom" and beat_sample.get("timing_profile") and beat_sample.get("hook_peak_moment") > 0, "beat timing engine failed")
        timing_plan = create_viral_timing_plan(quick_data["package"], target_duration=15, preset_id="viral_meme")
        assert_true(timing_plan["first_3_seconds"]["opening_line"] and timing_plan["scene_count"] >= 1, "viral timing engine failed")
        song_short_clip = quick_generate_hook_clip(
            "Smoke Song To Short Clip",
            song_to_short_hook["clip_prompt"],
            source_workflow="music",
            duration_seconds=15,
            image_provider="offline",
            preset_id="emotional_story",
            subtitle_preset="Emotional Karaoke",
        )
        song_short_data = song_short_clip.get("data", {})
        assert_true(song_short_clip["ok"] and Path(song_short_data["final_mp4"]).exists(), "song-to-short final_hook_clip.mp4 export failed")
        assert_true(validate_mp4(song_short_data["final_mp4"])["valid_mp4"], "song-to-short final_hook_clip.mp4 not playable")
        assert_true(Path(song_short_data["render"]["subtitles"]).exists(), "song-to-short subtitles.srt export failed")
        assert_true(len((song_short_data.get("package") or {}).get("scene_sequence", [])) == 3, "song-to-short 3-scene structure failed")
        assert_true(all("project_data\\music" in item.get("path", "") or "project_data/music" in item.get("path", "") for item in song_short_data.get("image_results", [])), "music scene images were not saved under project_data/music")
        assert_true(all(Path(item.get("path", "")).name in {"scene_01.jpg", "scene_02.jpg", "scene_03.jpg"} for item in song_short_data.get("image_results", [])), "music scene image filenames failed")
        assert_true(Path(song_short_data["image_generation_manifest_path"]).exists(), "image_generation_manifest.json missing")
        gemini_fallback_image = generate_image("gemini_image", "vertical emotional music hook scene", str(out / "gemini_image_fallback.png"), {"gemini_api_key": "", "size": "512x768", "cache_enabled": False})
        assert_true(Path(gemini_fallback_image).exists(), "Gemini image fallback failed")
        gemini_capability = detect_image_provider_capability("gemini_image", {"gemini_api_key": "", "cache_enabled": False})
        assert_true(not gemini_capability["provider_available"] and gemini_capability["fallback_reason"] == "missing_api_key", "Gemini capability detection missing-key failed")
        openai_capability = detect_image_provider_capability("openai_images", {"openai_api_key": "", "cache_enabled": False})
        assert_true(not openai_capability["provider_available"] and openai_capability["fallback_reason"] == "missing_api_key", "OpenAI capability detection missing-key failed")
        gemini_diag = generate_image_with_diagnostics("gemini_image", "vertical emotional music hook scene", str(out / "gemini_image_diag.jpg"), {"gemini_api_key": "", "size": "1024x1536", "cache_enabled": False})
        assert_true(gemini_diag["ok"] and gemini_diag["data"]["fallback_used"] and gemini_diag["data"]["error_type"] == "missing_api_key" and gemini_diag["data"]["requested_model"] is not None, "Gemini image diagnostic fallback failed")
        openai_diag = generate_image_with_diagnostics("openai_images", "vertical cinematic scene", str(out / "openai_image_diag.jpg"), {"openai_api_key": "", "size": "1024x1536", "cache_enabled": False})
        assert_true(openai_diag["ok"] and openai_diag["data"]["fallback_used"] and openai_diag["data"]["error_type"] == "missing_api_key" and openai_diag["data"]["actual_model"] == "offline_placeholder", "OpenAI image diagnostic fallback failed")
        unsupported_diag = generate_image_with_diagnostics("unsupported_test_provider", "vertical cinematic scene", str(out / "unsupported_image_diag.jpg"), {"size": "1024x1536", "cache_enabled": False})
        assert_true(unsupported_diag["ok"] and unsupported_diag["data"]["fallback_used"] and unsupported_diag["data"]["fallback_reason"] == "unsupported_provider", "unsupported provider fallback failed")
        cute_clip = quick_generate_hook_clip("Smoke Cute Character Clip", "กล้วยพูดได้บ่นเรื่องชีวิต", image_provider="offline", preset_id="cute_character")
        cute_package = cute_clip.get("data", {}).get("package", {})
        assert_true(cute_clip["ok"] and cute_package.get("creator_outcome_preset", {}).get("preset_id") == "cute_character", "cute character quick pipeline failed")
        assert_true(any(scene.get("motion_effect") == "bounce" for scene in cute_package.get("scene_sequence", [])), "cute character motion behavior failed")
        cute_data = cute_clip.get("data", {})
        assert_true(Path(cute_data["character_profile_path"]).exists() and Path(cute_data["hook_analysis_path"]).exists(), "character/hook export failed")
        assert_true(Path(cute_data["styled_subtitles"]["ass"]).name == "styled_subtitles.ass", "styled subtitles export failed")
        prompts = [scene.get("image_prompt", "") for scene in cute_package.get("scene_sequence", [])]
        assert_true(prompts and all("same character" in prompt and "character consistency" in prompt for prompt in prompts), "scene character consistency missing")
    veo_payload = build_veo_payload(prompt=hook_clip_package["render_prompt"], aspect_ratio="9:16", duration_seconds=8, scene_id="scene_01", subtitle_timing=hook_subtitles)
    class SmokeOperation:
        name = "models/veo-3.1-generate-preview/operations/smoke-op"

    assert_true(get_operation_name("models/veo-3.1-generate-preview/operations/string-op").endswith("string-op"), "Veo string operation name failed")
    assert_true(get_operation_name(SmokeOperation()).endswith("smoke-op"), "Veo object operation name failed")
    missing_veo = submit_veo_render_job(veo_payload, api_key="")
    assert_true(veo_payload["aspect_ratio"] == "9:16" and not missing_veo["ok"] and missing_veo["error"] == "missing_api_key", "Veo connector missing-key safety failed")
    assert_true(isinstance(missing_veo["data"].get("provider_error_detail"), dict), "Veo missing-key safe detail failed")
    assert_true(not test_veo_connection(api_key="")["ok"] and not list_available_veo_models(api_key="")["ok"], "Veo diagnostics missing-key safety failed")
    missing_scene_submit = submit_veo_scene_job("Smoke Hook Clip Project", hook_clip_package, api_key="", scene_index=0)
    missing_scene_poll = poll_veo_scene_job("Smoke Hook Clip Project", api_key="", scene_id="scene_01")
    missing_scene_download = download_veo_scene_result("Smoke Hook Clip Project", api_key="", scene_id="scene_01")
    scene_jobs = load_scene_jobs("Smoke Hook Clip Project")
    assert_true(not missing_scene_submit["ok"] and missing_scene_submit["error"] == "missing_api_key", "Veo scene submit missing-key safety failed")
    assert_true(scene_jobs["ok"] and "scene_01" in scene_jobs["data"]["jobs"], "Veo scene job metadata failed")
    scene_01_job = scene_jobs["data"]["jobs"]["scene_01"]
    assert_true(scene_01_job.get("request_model") and scene_01_job.get("provider_method") and scene_01_job.get("provider_error_detail"), "Veo scene safe diagnostic metadata failed")
    assert_true(not missing_scene_poll["ok"] and not missing_scene_download["ok"], "Veo scene poll/download missing-key safety failed")
    assert_true(str(scene_output_path("Smoke Hook Clip Project", "scene_01")).endswith("scene_01.mp4"), "Veo scene output path failed")
    assert_true(active_theme_name() in {"Dark", "Cinematic Dark", "Light"}, "theme config failed")
    templates = list_project_templates()
    packs = list_preset_packs()
    scene_presets = list_scene_presets()
    global_presets = list_global_presets()
    assert_true(any(item.get("name") == "TikTok Viral" for item in templates), "project templates failed")
    assert_true(any(item.get("name") == "TikTok Fast Pack" for item in packs), "preset packs failed")
    assert_true(any(item.get("name") == "neon city" for item in scene_presets), "scene presets failed")
    assert_true("motion_presets" in global_presets and "render_presets" in global_presets, "global presets failed")
    templated_project = create_project_from_template("Template Smoke", "TikTok Viral")
    assert_true(templated_project["settings"]["render_profile"] == "TikTok Fast", "template render profile failed")
    assert_true(suggested_scene_preset_details(templates[0]), "template scene suggestions failed")
    consistency = build_style_consistency_report(templated_project)
    assert_true(consistency["ok"] and "visual_identity" in consistency["data"], "style consistency failed")
    memory_path = out / "prompt_memory.json"
    saved_memory = save_prompt_memory(
        {
            "preferred_render_profile": "Cinematic",
            "preferred_subtitle_style": "cinematic",
            "preferred_motion_style": "cinematic_drift",
            "preferred_color_profile": "film_look",
            "prompt_keywords": ["cinematic smoke test"],
            "favorite_scene_tags": ["neon city"],
        },
        memory_path,
    )
    memory = load_prompt_memory(memory_path)
    assert_true(saved_memory["ok"] and memory["preferred_render_profile"] == "Cinematic", "prompt memory failed")
    templated_project = apply_prompt_memory_to_project(templated_project, memory)
    assert_true(templated_project["visual_identity"]["prompt_rules"], "prompt memory project apply failed")
    session_path = out / "last_session.json"
    save_session = save_last_session(project, session_path)
    recover_session = recover_last_session(session_path)
    assert_true(save_session["ok"] and recover_session["ok"], "session recovery failed")

    project_path = save_project(project, out)
    loaded = load_project(str(project_path))
    assert_true(loaded.get("title") == project["title"], "project save/load failed")

    image_path = out / "offline_image.png"
    generate_image("offline", "cinematic Thai singer in rain", str(image_path), {"size": "512x512"})
    assert_true(image_path.exists(), "offline image generation failed")
    project["assets"]["approved_images"] = {"1": str(image_path)}
    library_update = update_library_from_project(project)
    assert_true(library_update["ok"] and library_update["data"]["count"] >= 1, "asset library update failed")
    library_results = search_asset_library(query="rain")
    assert_true(library_results, "asset library search failed")
    library_export = export_asset_library(out / "asset_library_export")
    assert_true(Path(library_export["data"]["path"]).exists(), "asset library export failed")
    reuse = recommend_reusable_scenes(project)
    assert_true(reuse["ok"], "scene reuse recommendations failed")
    creative = build_creative_suggestions(project)
    assert_true(creative["ok"] and creative["data"]["suggestions"], "creative suggestions failed")
    workspace = workspace_performance_report(project)
    assert_true(workspace["ok"] and "areas" in workspace["data"], "workspace performance report failed")
    thumb = build_thumbnail_index(project)
    assert_true(thumb["ok"], "thumbnail index failed")
    cache_clean = cleanup_old_cache(365)
    assert_true(cache_clean["ok"], "old cache cleanup failed")
    preset_bundle = export_preset_bundle(out / "preset_bundles")
    assert_true(Path(preset_bundle["data"]["path"]).exists(), "preset bundle export failed")
    preset_import = import_preset_bundle(preset_bundle["data"]["path"])
    assert_true(preset_import["ok"] and preset_import["data"]["imported"], "preset bundle import failed")
    draft_payload = build_full_mv_draft_payload(project, "__missing_ffmpeg__")
    assert_true(draft_payload["render_profile"] == "Draft" and draft_payload["aspect_ratios"] == ["16:9"], "one click draft payload failed")
    tiktok_plan = build_tiktok_set_plan(project, "__missing_source__.mp4", out / "clip_plan", "__missing_ffmpeg__")
    assert_true(tiktok_plan["ok"] and len(tiktok_plan["data"]["clips"]) >= 5, "one click tiktok plan failed")
    release_check = release_package_checklist(project)
    assert_true("checks" in release_check["data"], "release package checklist failed")
    arc = analyze_emotional_arc(project)
    assert_true(arc["ok"] and arc["data"]["points"], "emotional arc failed")
    hooks = analyze_hooks(project)
    assert_true(hooks["ok"] and hooks["data"]["candidates"], "hook intelligence failed")
    continuity = analyze_visual_continuity(project)
    assert_true(continuity["ok"] and "score" in continuity["data"], "visual continuity failed")
    cinema = build_cinematic_suggestions(project)
    assert_true(cinema["ok"] and "suggestions" in cinema["data"], "cinematic suggestions failed")
    applied_cinema = apply_cinematic_suggestions(project)
    assert_true(applied_cinema["ok"] and applied_cinema["data"]["scenes"], "apply cinematic suggestions failed")
    adaptive = recommend_render_profile(project)
    assert_true(adaptive["ok"] and adaptive["data"]["profile"], "adaptive profile failed")
    applied_profile = apply_adaptive_profile(project)
    assert_true(applied_profile["ok"] and project["settings"]["render_profile"], "apply adaptive profile failed")
    creative_timeline = build_creative_timeline(project)
    assert_true(creative_timeline["ok"] and creative_timeline["data"]["items"], "creative timeline failed")
    timeline_export = export_creative_timeline(project, out / "creative_timeline")
    assert_true(Path(timeline_export["data"]["path"]).exists(), "creative timeline export failed")
    graph = build_asset_relationship_graph(project)
    assert_true(graph["ok"] and graph["data"]["nodes"] and graph["data"]["edges"], "asset graph failed")
    shots = recommend_shot_types(project)
    assert_true(shots["ok"] and shots["data"]["shots"], "shot intelligence failed")
    shot_apply = apply_shot_types(project)
    assert_true(shot_apply["ok"] and project["mv"]["storyboard"][0].get("shot_type"), "apply shot intelligence failed")
    camera = recommend_camera_language(project)
    assert_true(camera["ok"] and camera["data"]["camera"], "camera language failed")
    camera_apply = apply_camera_language(project)
    assert_true(camera_apply["ok"] and project["mv"]["storyboard"][0].get("camera_language"), "apply camera language failed")
    rhythm = analyze_scene_rhythm(project)
    assert_true(rhythm["ok"] and rhythm["data"]["rows"], "scene rhythm failed")
    story_consistency = analyze_visual_story_consistency(project)
    assert_true(story_consistency["ok"] and "score" in story_consistency["data"], "visual story consistency failed")
    notes = build_director_notes(project)
    assert_true(notes["ok"] and notes["data"]["notes"], "director notes failed")
    injected = inject_director_notes(project)
    assert_true(injected["ok"] and project["mv"]["storyboard"][0].get("director_note"), "inject director notes failed")
    packs_available = list_cinematic_style_packs()
    assert_true(packs_available and any(pack["name"] == "Sad Rain Film" for pack in packs_available), "cinematic style packs failed")
    pack_apply = apply_cinematic_style_pack(project, "Sad Rain Film")
    assert_true(pack_apply["ok"] and project["settings"]["cinematic_style_pack"] == "Sad Rain Film", "apply style pack failed")
    order = analyze_scene_order(project)
    assert_true(order["ok"] and order["data"]["current"], "scene order analysis failed")
    order_apply = apply_suggested_scene_order(project)
    assert_true(order_apply["ok"] and order_apply["data"]["order"], "apply scene order failed")
    narrative = analyze_narrative_arc(project)
    assert_true(narrative["ok"] and narrative["data"]["rows"], "narrative arc failed")
    performance = map_performance_emotions(project)
    assert_true(performance["ok"] and performance["data"]["rows"], "performance emotion failed")
    performance_apply = inject_performance_emotions(project)
    assert_true(performance_apply["ok"] and project["mv"]["storyboard"][0].get("performance_emotion"), "inject performance emotion failed")
    metaphors = suggest_visual_metaphors(project)
    assert_true(metaphors["ok"] and metaphors["data"]["rows"], "visual metaphor failed")
    metaphors_apply = inject_visual_metaphors(project)
    assert_true(metaphors_apply["ok"] and project["mv"]["storyboard"][0].get("visual_metaphor"), "inject visual metaphor failed")
    beat_sync = analyze_cinematic_beats(project)
    assert_true(beat_sync["ok"] and beat_sync["data"]["rows"], "cinematic beat sync failed")
    beat_apply = inject_cinematic_beats(project)
    assert_true(beat_apply["ok"] and project["mv"]["storyboard"][0].get("emotional_beat"), "inject cinematic beats failed")
    subtitle_emotion = map_dynamic_subtitle_emotion(project)
    assert_true(subtitle_emotion["ok"] and subtitle_emotion["data"]["rows"], "subtitle emotion failed")
    subtitle_apply = inject_dynamic_subtitle_emotion(project)
    assert_true(subtitle_apply["ok"] and project["mv"]["storyboard"][0].get("subtitle_ass_hint"), "inject subtitle emotion failed")
    emotional_profiles = list_emotional_render_profiles()
    assert_true(any(item["name"] == "heartbreak" for item in emotional_profiles), "emotional render profile list failed")
    emotional_profile = recommend_emotional_render_profile(project)
    assert_true(emotional_profile["ok"] and emotional_profile["data"]["profile"], "recommend emotional profile failed")
    emotional_apply = apply_emotional_render_profile(project, emotional_profile["data"]["name"])
    assert_true(emotional_apply["ok"] and project["settings"].get("emotional_render_profile"), "apply emotional profile failed")
    audit = run_full_project_audit(project)
    assert_true(audit["ok"] and 0 <= audit["data"]["score"] <= 100 and audit["data"]["checks"], "production audit failed")
    assert_true(audit["data"]["fix_first"] or audit["data"]["ready_for_final_render"] in {True, False}, "audit priority failed")
    audit_export = export_project_audit(project, out / "audits")
    assert_true(Path(audit_export["data"]["json"]).exists() and Path(audit_export["data"]["markdown"]).exists(), "audit export failed")
    beta = new_beta_session(project, "Smoke Template", "Draft", "smoke notes")
    beta_session_id = beta["data"]["session"]["session_id"]
    assert_true(beta["ok"] and beta_session_id, "beta session create failed")
    beta_ratings = {area: 8 for area in BETA_RATING_AREAS}
    beta_rating_result = update_beta_ratings(project, beta_session_id, beta_ratings)
    assert_true(beta_rating_result["ok"] and average_beta_rating(beta_rating_result["data"]["session"]) == 8, "beta ratings failed")
    beta_issue = add_beta_issue(project, beta_session_id, "Render", "HIGH", "Smoke issue", "OPEN")
    assert_true(beta_issue["ok"] and beta_issue["data"]["session"]["issues"], "beta issue log failed")
    beta_checklist = beta_test_checklist(project, beta_issue["data"]["session"])
    assert_true(beta_checklist["ok"] and beta_checklist["data"]["checks"], "beta checklist failed")
    beta_sessions = list_beta_sessions(project)
    assert_true(any(item["session_id"] == beta_session_id for item in beta_sessions), "beta session list failed")
    beta_stable = mark_stable_candidate(project, beta_session_id)
    assert_true(beta_stable["ok"] and beta_stable["data"]["session"]["stable_candidate"], "beta stable candidate failed")
    beta_report = export_beta_report(project, beta_session_id, out / "beta_reports")
    assert_true(Path(beta_report["data"]["json"]).exists() and Path(beta_report["data"]["markdown"]).exists(), "beta report export failed")
    lock = acquire_project_lock(project, owner="smoke_test", force=True)
    assert_true(lock["ok"] and project_lock_status(project)["data"]["locked"], "project lock failed")
    unlock = release_project_lock(project)
    assert_true(unlock["ok"] and not project_lock_status(project)["data"]["locked"], "project unlock failed")
    fixes = fix_common_issues(project)
    assert_true(fixes["ok"] and "project" in fixes["data"], "fix common issues failed")
    pre_render_health = run_pre_render_healthcheck(project)
    assert_true("checks" in pre_render_health["data"], "pre-render healthcheck failed")
    safe_project_path = out / "safe_project.json"
    safe_project_path.write_text(json.dumps(project, ensure_ascii=False), encoding="utf-8")
    safe_open = open_project_safe_mode(safe_project_path)
    assert_true(safe_open["ok"] and safe_open["data"]["project"]["title"] == project["title"], "safe mode open failed")
    diagnostic = export_diagnostic_bundle(project, out / "diagnostics")
    assert_true(Path(diagnostic["data"]["path"]).exists(), "diagnostic bundle failed")
    stable_summary = stable_build_summary(project, beta_session_id)
    assert_true(stable_summary["freeze_name"] == STABLE_FREEZE_NAME and stable_summary["features_ready"], "stable build summary failed")
    stable_snapshot = create_stable_candidate_snapshot(project, beta_session_id, output_dir=out / "stable_candidates", include_smoke_test=False)
    stable_dir = Path(stable_snapshot["data"]["snapshot_dir"])
    assert_true(stable_snapshot["ok"] and (stable_dir / "STABLE_BUILD.md").exists(), "stable snapshot markdown failed")
    assert_true((stable_dir / "stable_manifest.json").exists() and Path(stable_snapshot["data"]["zip"]).exists(), "stable snapshot evidence failed")

    video_slot = out / "offline_video.mp4"
    generate_video("offline", "slow cinematic push in", str(image_path), str(video_slot), {"scene": 1})
    assert_true(video_slot.with_suffix(".json").exists(), "offline video metadata failed")
    assert_true(video_slot.with_suffix(".video_slot.txt").exists(), "offline video slot note failed")

    render_dir = out / "timeline_render"
    render_dir.mkdir(exist_ok=True)
    first_scene_id = str(((project.get("mv", {}) or {}).get("storyboard", [{}]) or [{}])[0].get("scene") or "1")
    project.setdefault("assets", {}).setdefault("approved_images", {})[first_scene_id] = str(image_path)
    project.setdefault("assets", {}).setdefault("videos", {}).pop(first_scene_id, None)
    timeline_data = build_timeline(project, render_dir)
    assert_true(timeline_data["items"][0]["source_type"] == "approved_image", "timeline source selection failed")

    subtitle_result = generate_subtitles(timeline_data["items"], render_dir, "simple")
    assert_true(subtitle_result["ok"], "subtitle generation failed")
    assert_true((render_dir / "subtitle.srt").exists(), "subtitle.srt missing")
    assert_true((render_dir / "subtitle.ass").exists(), "subtitle.ass missing")

    render_result = run_render(project, {"base_dir": out / "renders", "ffmpeg_path": "__missing_ffmpeg__", "subtitle_mode": "simple"})
    project.setdefault("runtime", {})["last_render_dir"] = render_result["data"]["render_dir"]
    render_manifest_path = Path(render_result["data"]["render_dir"]) / "render_manifest.json"
    assert_true(render_manifest_path.exists(), "render manifest missing")
    manifest_data = json.loads(render_manifest_path.read_text(encoding="utf-8"))
    assert_true(manifest_data.get("generated_by") == "VelaFlow" and manifest_data.get("build_version"), "render manifest identity missing")
    assert_true((Path(render_result["data"]["render_dir"]) / "timeline.json").exists(), "timeline.json missing")
    failed = latest_failed_render(project)
    assert_true(failed["ok"], "latest failed render lookup failed")
    recovered_temp = recover_render_temp(render_result["data"]["render_dir"])
    assert_true(recovered_temp["ok"], "recover render temp failed")

    preview_project = build_preview_project(project, 0, 3)
    assert_true(len(preview_project["mv"]["storyboard"]) == 1, "preview project scene isolation failed")
    preview_result = run_scene_preview(project, 0, {"base_dir": out / "previews", "ffmpeg_path": "__missing_ffmpeg__", "preview_seconds": 3})
    assert_true((Path(preview_result["data"]["render_dir"]) / "render_manifest.json").exists(), "preview manifest missing")
    clip_scene = choose_clip_scene(project, "Hook Clip")
    storyboard_scene_ids = {str(scene.get("scene") or index + 1) for index, scene in enumerate((project.get("mv", {}) or {}).get("storyboard", []) or [])}
    assert_true(clip_scene["scene_id"] in storyboard_scene_ids, "clip scene selection failed")
    clip_result = generate_clip(project, "__missing_source__.mp4", out / "clip_render", "Hook Clip", "__missing_ffmpeg__", preview=True)
    assert_true(Path(clip_result["data"]["caption_paths"]["txt"]).exists(), "clip caption txt missing")
    assert_true((out / "clip_render" / "clips" / "clip_metadata.json").exists(), "clip metadata missing")
    clip_set = generate_clip_set(project, "__missing_source__.mp4", out / "clip_set_render", "__missing_ffmpeg__", preview=True)
    assert_true(clip_set["data"]["clips"] and len(clip_set["data"]["clips"]) >= 6, "clip set metadata failed")
    marketing = build_marketing_package(project)
    assert_true(marketing["ok"] and marketing["data"]["youtube"]["title"], "marketing package build failed")
    assert_true(marketing["data"].get("generated_by") == "VelaFlow" and marketing["data"].get("build_version"), "marketing identity missing")
    marketing_export = export_marketing_package(project, out / "marketing")
    marketing_folder = Path(marketing_export["data"]["folder"])
    for name in [
        "youtube.txt",
        "tiktok.txt",
        "facebook.txt",
        "hashtags.txt",
        "pinned_comment.txt",
        "thumbnail_prompt.txt",
        "spotify_canvas_prompt.txt",
        "upload_checklist.md",
        "release_note.md",
    ]:
        assert_true((marketing_folder / name).exists(), f"marketing file missing: {name}")
    final_render_dir = out / "final_render_source"
    clips_dir = final_render_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    (final_render_dir / "final_16x9.mp4").write_text("fake mv", encoding="utf-8")
    (final_render_dir / "subtitle.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nTest\n", encoding="utf-8")
    (final_render_dir / "subtitle.ass").write_text("[Script Info]\n", encoding="utf-8")
    (final_render_dir / "render_manifest.json").write_text("{}", encoding="utf-8")
    (final_render_dir / "timeline.json").write_text("{}", encoding="utf-8")
    (clips_dir / "hook_clip_9x16.mp4").write_text("fake clip", encoding="utf-8")
    (clips_dir / "hook_clip_9x16_caption.txt").write_text("caption", encoding="utf-8")
    final_render_dir_b = out / "final_render_source_b"
    final_render_dir_b.mkdir(parents=True, exist_ok=True)
    (final_render_dir_b / "final_16x9.mp4").write_text("fake mv b", encoding="utf-8")
    (final_render_dir_b / "render_manifest.json").write_text('{"version":"b"}', encoding="utf-8")
    render_compare = compare_render_versions(final_render_dir, final_render_dir_b)
    assert_true(render_compare["ok"] and render_compare["data"]["rows"], "render version compare failed")
    inspected = inspect_final_package_inputs(project, final_render_dir)
    assert_true(inspected["data"]["checks"], "final package inspection failed")
    final_package = build_final_release_package(project, out / "final_release", final_render_dir, zip_package=True)
    final_folder = Path(final_package["data"]["folder"])
    assert_true((final_folder / "mv" / "final_16x9.mp4").exists(), "final package mv missing")
    assert_true((final_folder / "clips" / "hook_clip_9x16.mp4").exists(), "final package clip missing")
    assert_true((final_folder / "marketing_package" / "youtube.txt").exists(), "final package marketing missing")
    assert_true(any((final_folder / "exports").glob("*_Suno_Export*.txt")), "final package dynamic Suno export missing")
    assert_true(any((final_folder / "exports").glob("*_Lyrics_Only*.txt")), "final package lyrics-only export missing")
    assert_true((final_folder / "project_report.md").exists(), "final package report missing")
    assert_true((final_folder / "upload_checklist.md").exists(), "final package checklist missing")
    final_manifest = json.loads((final_folder / "final_package_manifest.json").read_text(encoding="utf-8"))
    assert_true(final_manifest.get("generated_by") == "VelaFlow" and final_manifest.get("build_version"), "final package identity missing")
    assert_true(Path(final_package["data"]["zip"]).exists(), "final package zip missing")

    source_package = create_source_package(out / "source_packages")
    package_path = Path(source_package["package"])
    assert_true(package_path.exists(), "source package missing")
    with zipfile.ZipFile(package_path, "r") as zf:
        names = set(zf.namelist())
    assert_true("app/main.py" in names and "core/version.py" in names and "README.md" in names, "source package expected files missing")
    forbidden = [
        name
        for name in names
        if name == ".env"
        or name.startswith(".venv/")
        or name.startswith("outputs/cache/")
        or "__pycache__/" in name
        or name.endswith(".pyc")
        or "/_scene_cache/" in name
    ]
    assert_true(not forbidden, f"source package included forbidden files: {forbidden[:5]}")
    beta_package = build_beta_package(out / "beta_packages")
    beta_package_path = Path(beta_package["package"])
    assert_true(beta_package_path.exists(), "beta package missing")
    with zipfile.ZipFile(beta_package_path, "r") as zf:
        beta_names = set(zf.namelist())
    beta_forbidden = [
        name
        for name in beta_names
        if name == ".env"
        or name.startswith(".venv/")
        or name.startswith("project_data/")
        or name.startswith("outputs/")
        or "__pycache__/" in name
        or name.endswith(".pyc")
    ]
    assert_true(not beta_forbidden, f"beta package included forbidden files: {beta_forbidden[:5]}")
    assert_true(".env.example" in beta_names and "run_velaflow.bat" in beta_names and "docs/BETA_RELEASE_CHECKLIST.md" in beta_names and "docs/BETA_NOTES.md" in beta_names and "docs/QUICK_START.md" in beta_names and "docs/KNOWN_LIMITATIONS.md" in beta_names and "docs/BETA_FEEDBACK.md" in beta_names, "beta package expected files missing")

    scores = score_project_scenes(project)
    assert_true(scores and scores[0]["teaser_score"] > 0 and scores[0]["status"], "scene scoring failed")
    tiktok = smart_tiktok_recommendations(project)
    assert_true(tiktok["ok"] and tiktok["data"]["recommended_scenes"], "smart tiktok recommendation failed")
    quality = build_quality_checklist(project)
    assert_true(quality["data"]["checks"] and quality["data"]["scenes"], "quality checklist failed")
    regen = recommend_regenerate_images(project)
    assert_true(regen["ok"] and "scenes" in regen["data"], "regenerate recommendation failed")
    status = build_project_status(project)
    assert_true(status["next_step"]["page"] in {"Image Lab", "Image Review", "🎞️ Render Lab", "📦 Export Center"}, "project next step failed")
    workflow_root = out / "workflow_projects"
    save_project_folder(project, workflow_root)
    recent = list_recent_projects(base_dir=workflow_root)
    assert_true(recent and any(item["title"] == project["title"] for item in recent), "recent projects failed")
    duplicate = duplicate_project(project, "Smoke Test V65 Duplicate", workflow_root)
    assert_true(duplicate["ok"] and Path(duplicate["data"]["folder"]).exists(), "duplicate project failed")
    report = export_project_report(project, out / "reports")
    assert_true(Path(report["data"]["markdown"]).exists(), "project report export failed")
    temp_dir = ROOT / "outputs" / "renders" / "Smoke_Test_V65" / "temp_smoke" / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    (temp_dir / "scratch.tmp").write_text("temp", encoding="utf-8")
    clean = clean_safe_temp_files(project)
    assert_true(clean["ok"] and not temp_dir.exists(), "safe temp cleanup failed")

    export_dir = export_package(str(out / "exports"), project["title"], project["mv"], project["song"]["complete_lyrics"], project["song"], project)
    assert_true((export_dir / "project_files" / "song.json").exists(), "export song.json missing")
    assert_true((export_dir / "project_files" / "video_pipeline.json").exists(), "export video_pipeline.json missing")
    assert_true((export_dir / "spotify" / "artist_preset.json").exists(), "export artist_preset.json missing")
    assert_true((export_dir / "spotify" / "hook_candidates.json").exists(), "export hook_candidates.json missing")
    assert_true((export_dir / "spotify" / "selected_hook.json").exists(), "export selected_hook.json missing")
    assert_true(any((export_dir / "exports").glob("*_Suno_Export*.txt")), "export dynamic Suno TXT missing")
    assert_true(any((export_dir / "exports").glob("*_Lyrics_Only*.txt")), "export lyrics TXT missing")
    assert_true((export_dir / "spotify" / "instrument_tag_validation.json").exists(), "export instrument tag validation missing")
    exported_lyrics = (export_dir / "spotify" / "suno_lyrics.txt").read_text(encoding="utf-8")
    assert_true(validate_english_only_tags(exported_lyrics)["ok"] and "ยังคิดถึงเธอทุกคืน" in exported_lyrics, "exported Suno lyrics normalization failed")

    rejected = out / "rejected.png"
    rejected.write_bytes(image_path.read_bytes())
    project["assets"]["rejected_images"] = {"1": str(rejected)}
    cleanup = clear_rejected_images(project)
    assert_true(cleanup["ok"] and not rejected.exists(), "asset manager rejected cleanup failed")

    def smoke_handler(payload, job):
        job.progress(50, "smoke handler running")
        return {"ok": True, "message": "done", "data": payload, "error": ""}

    register_handler("smoke_noop", smoke_handler)
    job_id = submit_job("smoke_noop", "Smoke Noop", {"hello": "world"})
    job = wait_job(job_id)
    assert_true(job.get("status") == "DONE", "job queue lifecycle failed")
    assert_true((job.get("result") or {}).get("ok") is True, "job result failed")

    print(json.dumps({"ok": True, "message": "smoke tests passed"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
