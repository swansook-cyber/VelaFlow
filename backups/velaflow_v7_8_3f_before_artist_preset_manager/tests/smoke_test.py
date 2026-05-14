import json
import sys
import time
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.asset_manager import clear_rejected_images
from core.clip_factory import choose_clip_scene, generate_clip, generate_clip_set
from core.exporter import export_package
from core.final_package import build_final_release_package, inspect_final_package_inputs
from core.job_queue import get_job, register_handler, submit_job
from core.licensing import LicenseService
from core.marketing_package import build_marketing_package, export_marketing_package
from core.recovery import recover_last_session, save_last_session
from core.theme import active_theme_name
from core.version import APP_VERSION, identity_payload
from core.artist_presets import get_artist_preset, list_artist_presets
from core.instrument_tag_normalizer import contains_thai, normalize_lyrics_tags, validate_english_only_tags
from core.song_workflow import generate_hook_candidates, save_song_state, select_best_hook
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
)
from core.preview_engine import build_preview_project, run_scene_preview
from core.quality_control import build_quality_checklist, recommend_regenerate_images
from core.project_workflow import build_project_status, clean_safe_temp_files, duplicate_project, export_project_report, list_recent_projects
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
from core.healthcheck import run_pre_render_healthcheck
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
from core.style_consistency import build_style_consistency_report
from core.subtitle_engine import generate_subtitles
from core.timeline_builder import build_timeline
from providers.image_ai import generate_image
from providers.video_ai import generate_video
from scripts.create_source_package import create_source_package


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
    assert_true(APP_VERSION == "7.8.3f" and identity_payload()["generated_by"] == "VelaFlow", "version identity failed")
    assert_true(vela_moon["artist_name"] == "Vela Moon" and vela_moon.get("default_music_style_prompt"), "Vela Moon preset failed")
    assert_true(any(item.get("artist_id") == "vela_moon" for item in list_artist_presets()), "artist preset list failed")
    assert_true(get_artist_preset("__missing_artist__").get("artist_id") == "vela_moon", "artist preset fallback failed")
    assert_true(tag_validation["ok"], "instrument tag normalization failed")
    assert_true("ยังคิดถึงเธอทุกคืน" in normalized_tags and contains_thai("ยังคิดถึงเธอทุกคืน"), "Thai lyrics were not preserved")
    project_suffix = str(int(time.time()))
    managed_name = f"Smoke Managed {project_suffix}"
    managed_create = create_managed_project(managed_name)
    assert_true(managed_create["ok"] and project_exists(managed_name), "managed project create failed")
    assert_true(any(item["project_name"] == managed_name.replace(" ", "_") for item in list_managed_projects()), "managed project list failed")
    thai_project_name = f"เพลงทดสอบไทย {project_suffix}"
    thai_create = create_managed_project(thai_project_name)
    assert_true(thai_create["ok"] and project_exists(thai_project_name), "Thai project name failed")
    archived = archive_project(managed_name)
    assert_true(archived["ok"] and any(managed_name.replace(" ", "_") in item["project_name"] for item in list_archived_projects()), "archive project failed")
    assert_true(not any(item["project_name"] == managed_name.replace(" ", "_") for item in list_managed_projects()), "archived project shown in active list")
    deleted = delete_project(thai_project_name, confirm=True)
    assert_true(deleted["ok"] and Path(deleted["data"]["backup_path"]).exists() and not project_exists(thai_project_name), "delete project backup failed")
    pref_save = save_user_preferences({"workflow_mode": "Song Studio Only"})
    pref_load = load_user_preferences()
    assert_true(pref_save["ok"] and pref_load["workflow_mode"] == "Song Studio Only", "Song Studio Only preference failed")
    save_user_preferences({"workflow_mode": "Full Pipeline"})
    hook_candidates = generate_hook_candidates("เพลงคิดถึงแฟนเก่าตอนฝนตก", vela_moon)
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
    }
    song_save = save_song_state("Smoke Song Workflow", workflow_song, out / "song_workflow_projects", create_draft=True)
    song_folder = Path(song_save["data"]["folder"])
    saved_song = json.loads((song_folder / "song.json").read_text(encoding="utf-8"))
    assert_true(song_save["ok"] and len(hook_candidates) >= 3, "offline hook candidate generation failed")
    assert_true(saved_song.get("hook_candidates") and saved_song.get("selected_hook"), "selected hook was not saved")
    assert_true((song_folder / "lyrics.txt").exists(), "lyrics.txt was not written")
    assert_true((song_folder / "exports" / "suno_full_package.txt").exists(), "suno_full_package.txt was not written")
    assert_true((song_folder / "exports" / "lyrics_only.txt").exists(), "lyrics_only.txt was not written")
    assert_true(saved_song.get("normalized_song_output") == (song_folder / "lyrics.txt").read_text(encoding="utf-8"), "normalized song output was not used for lyrics.txt")
    full_suno_text = (song_folder / "exports" / "suno_full_package.txt").read_text(encoding="utf-8")
    lyrics_only_text = (song_folder / "exports" / "lyrics_only.txt").read_text(encoding="utf-8")
    assert_true("ยังคิดถึงเธอทุกคืน" in full_suno_text and "Selected Hook:" in full_suno_text and "Hook Scores:" in full_suno_text, "Suno full package metadata failed")
    assert_true(lyrics_only_text == saved_song.get("normalized_song_output"), "lyrics_only.txt did not use normalized output")
    assert_true(song_save["data"]["suno_export"].get("suno_full_package", "").endswith("suno_full_package.txt"), "suno_full_package path was not returned after save")
    assert_true(validate_english_only_tags(saved_song["normalized_song_output"])["ok"], "saved song tags are not English only")
    assert_true(contains_thai(saved_song["normalized_song_output"]), "Thai lyrics were not preserved in saved song")
    assert_true((song_folder / "song_drafts").exists(), "song draft history was not created")
    project["song"].update(saved_song)
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
    assert_true(clip_scene["scene_id"] == "1", "clip scene selection failed")
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
    assert_true((final_folder / "exports" / "suno_full_package.txt").exists(), "final package Suno export missing")
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
    assert_true(recent and recent[0]["title"] == project["title"], "recent projects failed")
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
    assert_true((export_dir / "exports" / "suno_full_package.txt").exists(), "export suno_full_package.txt missing")
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
