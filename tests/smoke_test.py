import json
import os
import sys
import time
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.asset_manager import clear_rejected_images
from core.analytics import cleanup_old_temp_exports, ensure_beta_runtime_dirs, load_beta_analytics, log_beta_event
from core.api_keys import API_MODE_BETA_KEY, API_MODE_OWN_KEY, LOCAL_STORAGE_KEYS, mask_api_key, resolve_provider_credentials
from core.provider_runtime import build_provider_runtime_diagnostics
from core.clip_factory import choose_clip_scene, generate_clip, generate_clip_set
from core.exporter import export_package
from core.final_package import build_final_release_package, inspect_final_package_inputs
from core.job_queue import get_job, register_handler, submit_job
from core.licensing import LicenseService
from core.marketing_package import build_marketing_package, export_marketing_package
from core.mv_storyboard_generator import export_mv_storyboard, generate_mv_storyboard, storyboard_to_text
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
from core.podcast_content import (
    EPISODE_LENGTHS,
    NARRATION_STYLES,
    STORY_TONES,
    build_podcast_dashboard_status,
    export_podcast_content,
    generate_podcast_content,
    podcast_content_to_text,
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
from core.song_workflow import _extract_json, generate_hook_candidates, generate_hook_candidates_with_provider, save_song_state, select_best_hook
from core.song_structure_intelligence import (
    create_structure_plan,
    export_structure_plan_files,
    load_structure_plan,
    load_structure_presets,
    save_structure_plan,
    validate_structure_plan,
)
from core.suno_export import build_release_package_data, extract_song_title_from_export_text, export_txt_filename, resolve_export_txt_filename, safe_txt_filename
from core.project_io import load_project, new_project, save_project, save_project_folder
from core.project_manager import (
    archive_project,
    create_project as create_managed_project,
    delete_project,
    list_archived_projects,
    list_projects as list_managed_projects,
    load_user_preferences,
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
from core.real_clip_pipeline import find_ffmpeg, render_real_hook_clip, write_subtitles
from core.veo_scene_renderer import download_veo_scene_result, load_scene_jobs, poll_veo_scene_job, scene_output_path, submit_veo_scene_job
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
from core.scene_story_engine import build_scene_sequence, build_subtitle_timing
from core.style_consistency import build_style_consistency_report
from core.subtitle_engine import generate_subtitles
from core.timeline_builder import build_timeline
from core.voiceover_engine import build_voiceover_plan, export_voiceover_plan, generate_voiceover_audio
from providers.veo_provider import build_veo_payload, submit_render_job as submit_veo_render_job
from providers.image_ai import generate_image
from providers.video_ai import generate_video
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
    assert_true('providers = ["python"]' in nixpacks and 'nixPkgs = ["ffmpeg"]' in nixpacks, "nixpacks Python/FFmpeg install config failed")
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
    assert_true((not ffmpeg_path and not ffmpeg_info["ok"]) or (ffmpeg_info["ok"] and moviepy_info["ok"]), "FFmpeg runtime detection failed")
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
    assert_true(missing_resolved["api_key"] == "" and missing_resolved["status"] == "Offline Fallback", "missing BYO key fallback failed")
    assert_true(missing_resolved["warning"] == "Please add your own API key in AI Settings.", "missing own-key warning failed")
    assert_true(LOCAL_STORAGE_KEYS["gemini"] == "velaflow_gemini_key" and LOCAL_STORAGE_KEYS["openai"] == "velaflow_openai_key" and LOCAL_STORAGE_KEYS["xai"] == "velaflow_xai_key", "localStorage key names failed")
    assert_true(mask_api_key("abcd1234") == "Provided: ****1234" and mask_api_key("") == "Missing", "API key masking failed")
    analytics_root = out / "analytics_case"
    runtime_dirs = ensure_beta_runtime_dirs(analytics_root)
    assert_true(runtime_dirs["ok"] and (analytics_root / "analytics" / "analytics.json").exists(), "beta analytics runtime prep failed")
    log_beta_event("generate", workflow="seller", provider="xai", preset_bundle="Luxury Product", base_dir=analytics_root)
    log_beta_event("export", workflow="seller", provider="xai", base_dir=analytics_root)
    log_beta_event("render_job", workflow="seller", provider="xai", base_dir=analytics_root)
    log_beta_event("mv_storyboard_generated", workflow="music_mv", provider="gemini", base_dir=analytics_root)
    log_beta_event("render_package_generated", workflow="music_mv", provider="gemini", preset_bundle="Cinematic Sad", base_dir=analytics_root)
    analytics = load_beta_analytics(analytics_root)
    assert_true(analytics["generate_count"] >= 2 and analytics["export_count"] >= 2 and analytics["render_job_count"] >= 1, "beta analytics counters failed")
    assert_true(analytics["quality_tracking"]["seller_workflow_usage"] >= 3 and analytics["quality_tracking"]["mv_storyboard_generation_count"] >= 1, "workflow quality counters failed")
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
    assert_true(safe_txt_filename('เดินต่อ / demo:night?', 'full_pipeline') == 'เดินต่อ_demonight_full_pipeline.txt', "safe Thai TXT filename failed")
    assert_true(safe_txt_filename('', 'song_only') == 'velaflow_export.txt', "empty title TXT fallback failed")
    export_text_with_title = "====================\nSONG METADATA\n====================\n\nSong title: เดินต่อ\n"
    assert_true(extract_song_title_from_export_text(export_text_with_title) == "เดินต่อ", "export title parser failed")
    assert_true(resolve_export_txt_filename({}, "", "Full Pipeline", export_text_with_title) == "เดินต่อ_full_pipeline.txt", "export filename parser fallback failed")
    default_controls = [get_recommended_ai_controls("VelaFlow Default") for _ in range(5)]
    default_pairs = {(item["weirdness"], item["style_influence"]) for item in default_controls}
    assert_true(len(default_pairs) > 1, "recommended AI controls did not vary")
    assert_true(all(8 <= item["weirdness"] <= 14 and 55 <= item["style_influence"] <= 68 for item in default_controls), "default AI controls out of range")
    tiktok_controls = get_recommended_ai_controls("Viral TikTok Hook")
    cinematic_controls = get_recommended_ai_controls("Story Cinematic")
    assert_true(3 <= tiktok_controls["weirdness"] <= 8 and 70 <= tiktok_controls["style_influence"] <= 85, "TikTok AI controls out of range")
    assert_true(15 <= cinematic_controls["weirdness"] <= 25 and 45 <= cinematic_controls["style_influence"] <= 60, "cinematic AI controls out of range")
    manual_controls = get_recommended_ai_controls("VelaFlow Default", manual_weirdness=11, manual_style_influence=66)
    assert_true(manual_controls["manual"] and manual_controls["weirdness"] == 11 and manual_controls["style_influence"] == 66, "manual AI controls not respected")
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
    assert_true(FULL_MENU_GROUPS["SONG"] == ["Song Studio", "Song Library", "Artist Preset Manager"], "SONG navigation group failed")
    assert_true("Artist Preset Manager" in FULL_MENU_GROUPS["SONG"], "Artist Preset Manager missing from SONG group")
    assert_true("Hook Clip Studio" in full_pages and "Render Lab" in full_pages and "Final Package" in full_pages and "Queue Monitor" in full_pages, "Full Pipeline navigation missing pages")
    assert_true("Render Lab" not in song_only_pages and "Final Package" not in song_only_pages and "Creative Intelligence" not in song_only_pages, "Song Studio Only did not hide production pages")
    assert_true(set(song_only_pages) == SONG_ONLY_ALLOWED_PAGES, "Song Studio Only allowed page set mismatch")
    assert_true(len(full_pages) == len(set(full_pages)) and len(song_only_pages) == len(set(song_only_pages)), "duplicate navigation pages found")
    assert_true(PAGE_LABELS.get("Creator Wizard") == "Release Workflow Wizard" and PAGE_LABELS.get("Smart Clip Factory") == "Clip Factory" and PAGE_LABELS.get("Production Audit") == "Quality Audit", "menu label polish failed")
    assert_true(normalize_navigation_state(FULL_MENU_GROUPS, "SONG", "Dashboard") == ("SONG", "Song Studio"), "Full Pipeline cannot select SONG")
    assert_true(normalize_navigation_state(FULL_MENU_GROUPS, "VISUAL", "Dashboard") == ("VISUAL", "MV Director"), "Full Pipeline cannot select VISUAL")
    assert_true(normalize_navigation_state(FULL_MENU_GROUPS, "PRODUCTION", "Dashboard") == ("PRODUCTION", "Hook Clip Studio"), "Full Pipeline cannot select PRODUCTION")
    assert_true("VISUAL" not in SONG_ONLY_MENU_GROUPS and "PRODUCTION" not in SONG_ONLY_MENU_GROUPS, "Song Studio Only did not hide VISUAL/PRODUCTION groups")
    seller_pages = flatten_pages(SELLER_STUDIO_MENU_GROUPS)
    assert_true(menu_groups_for_mode("Seller Studio (Beta)") == SELLER_STUDIO_MENU_GROUPS, "Seller Studio workflow mode failed")
    assert_true(set(seller_pages) == SELLER_STUDIO_ALLOWED_PAGES, "Seller Studio allowed page set mismatch")
    assert_true("Seller Studio" in seller_pages and "Render Lab" not in seller_pages and "Song Studio" not in seller_pages, "Seller Studio navigation filtering failed")
    assert_true(normalize_navigation_state(SELLER_STUDIO_MENU_GROUPS, "SELLER", "Dashboard") == ("SELLER", "Seller Studio"), "Seller Studio section selection failed")
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
    dashboard_target = "Song Studio"
    assert_true(dashboard_target in full_pages and dashboard_target in song_only_pages, "Dashboard continue target invalid")
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
    assert_true((song_folder / "exports" / full_pipeline_name).exists(), "dynamic full pipeline TXT was not written")
    assert_true((song_folder / "exports" / "lyrics_only.txt").exists(), "lyrics_only.txt was not written")
    assert_true((song_folder / "exports" / "song_structure_plan.json").exists(), "song_structure_plan.json was not exported")
    assert_true((song_folder / "exports" / "song_structure_plan.md").exists(), "song_structure_plan.md was not exported")
    assert_true(saved_song.get("normalized_song_output") == (song_folder / "lyrics.txt").read_text(encoding="utf-8"), "normalized song output was not used for lyrics.txt")
    full_suno_text = (song_folder / "exports" / full_pipeline_name).read_text(encoding="utf-8")
    lyrics_only_text = (song_folder / "exports" / "lyrics_only.txt").read_text(encoding="utf-8")
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
    assert_true(lyrics_only_text == saved_song.get("normalized_song_output"), "lyrics_only.txt did not use normalized output")
    assert_true(song_save["data"]["suno_export"].get("suno_full_package", "").endswith(full_pipeline_name), "dynamic full pipeline path was not returned after save")
    assert_true(song_save["data"]["suno_export"].get("suno_full_filename") == full_pipeline_name, "dynamic download filename missing from export data")
    assert_true(validate_english_only_tags(saved_song["normalized_song_output"])["ok"], "saved song tags are not English only")
    assert_true(contains_thai(saved_song["normalized_song_output"]), "Thai lyrics were not preserved in saved song")
    assert_true((song_folder / "song_drafts").exists(), "song draft history was not created")
    song_only_save = save_song_state("Smoke Song Only Workflow", workflow_song, out / "song_only_workflow_projects", workflow_mode="Song Studio Only")
    song_only_name = export_txt_filename(song_only_save["data"]["song"], "Smoke Song Only Workflow", "Song Studio Only")
    song_only_text = (Path(song_only_save["data"]["folder"]) / "exports" / song_only_name).read_text(encoding="utf-8")
    assert_true(song_only_name.endswith("_song_only.txt"), "Song Only dynamic filename failed")
    assert_true("Complete Lyrics with Tags" in song_only_text and "Hook Information" in song_only_text, "Song Only minimal export missing lyrics/hook")
    assert_true("SEO CAPTION" not in song_only_text and "COVER ART PROMPTS" not in song_only_text and "RELEASE ASSETS" not in song_only_text, "Song Only export included Full Pipeline sections")
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
    seller_package = seller_result["data"]
    assert_true("Review" in HOOK_STYLES and seller_package["hook_style"] == "Review", "seller hook style failed")
    assert_true(seller_package["active_ai_provider"] == "xai" and seller_package["active_ai_model"] == "grok-4.3", "seller xAI provider metadata failed")
    assert_true(3 <= len(seller_package["compressed_benefits"]) <= 6, "seller compressed benefits count failed")
    assert_true(len(seller_package["tiktok_hooks"]) >= 3 and seller_package["caption"] and seller_package["ai_video_prompt"], "seller content package missing core fields")
    assert_true(seller_package["product_image"]["attached"] is False, "seller no-image package incorrectly marked image attached")
    assert_true(seller_package.get("script_15s") and seller_package.get("script_30s") and seller_package.get("script_60s"), "seller timed scripts missing")
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
    combine_manifest = combine_scene_clips(["scene_1.mp4", "scene_2.mp4"], out / "hook_clip_projects" / "final_hook_clip.mp4", subtitle_timing=hook_subtitles)
    assert_true(combine_manifest["ok"] and Path(combine_manifest["data"]["manifest_path"]).exists(), "combine fallback manifest failed")
    voiceover_plan = build_voiceover_plan(podcast_package["main_script"], style="tired office worker")
    voiceover_export = export_voiceover_plan("Smoke Podcast Project", voiceover_plan, out / "podcast_projects")
    assert_true(voiceover_plan["style"] == "tired office worker" and voiceover_export["ok"], "voiceover fallback export failed")
    voiceover_audio = generate_voiceover_audio("Smoke Hook Clip Project", "This is a smoke test hook.", style="calm narrator", api_key="", base_dir=out / "hook_clip_projects")
    assert_true(voiceover_audio["ok"] and Path(voiceover_audio["data"]["audio_path"]).exists(), "voiceover MP3 fallback failed")
    srt_result = write_subtitles(hook_subtitles, out / "hook_clip_projects" / "subtitles.srt")
    assert_true(srt_result["ok"] and Path(srt_result["data"]["path"]).exists(), "subtitle SRT export failed")
    if find_ffmpeg():
        real_clip = render_real_hook_clip(
            "Smoke Hook Clip Project",
            hook_clip_package,
            workflow_type="hook",
            voiceover_path=voiceover_audio["data"]["audio_path"],
        )
        assert_true(real_clip["ok"] and Path(real_clip["data"]["final_mp4"]).exists() and Path(real_clip["data"]["subtitles"]).exists(), "real hook MP4 export failed")
    veo_payload = build_veo_payload(prompt=hook_clip_package["render_prompt"], aspect_ratio="9:16", duration_seconds=8, scene_id="scene_01", subtitle_timing=hook_subtitles)
    missing_veo = submit_veo_render_job(veo_payload, api_key="")
    assert_true(veo_payload["aspect_ratio"] == "9:16" and not missing_veo["ok"] and missing_veo["error"] == "missing_api_key", "Veo connector missing-key safety failed")
    missing_scene_submit = submit_veo_scene_job("Smoke Hook Clip Project", hook_clip_package, api_key="", scene_index=0)
    missing_scene_poll = poll_veo_scene_job("Smoke Hook Clip Project", api_key="", scene_id="scene_01")
    missing_scene_download = download_veo_scene_result("Smoke Hook Clip Project", api_key="", scene_id="scene_01")
    scene_jobs = load_scene_jobs("Smoke Hook Clip Project")
    assert_true(not missing_scene_submit["ok"] and missing_scene_submit["error"] == "missing_api_key", "Veo scene submit missing-key safety failed")
    assert_true(scene_jobs["ok"] and "scene_01" in scene_jobs["data"]["jobs"], "Veo scene job metadata failed")
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
    assert_true(any((final_folder / "exports").glob("*_full_pipeline.txt")), "final package dynamic Suno export missing")
    assert_true((final_folder / "exports" / "lyrics_only.txt").exists(), "final package lyrics-only export missing")
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
    assert_true(".env.example" in beta_names and "run_velaflow.bat" in beta_names and "docs/BETA_RELEASE_CHECKLIST.md" in beta_names and "docs/BETA_NOTES.md" in beta_names, "beta package expected files missing")

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
    assert_true(any((export_dir / "exports").glob("*_full_pipeline.txt")), "export dynamic Suno TXT missing")
    assert_true((export_dir / "exports" / "lyrics_only.txt").exists(), "export lyrics_only.txt missing")
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
