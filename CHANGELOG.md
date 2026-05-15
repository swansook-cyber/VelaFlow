# Changelog

## VelaFlow Beta 0.1.0 - Railway Internal Cloud Prep

- Updated Railway/Procfile Streamlit start command to use `--server.port=$PORT --server.address=0.0.0.0`.
- Added `VELAFLOW_MODE` setting and Internal Cloud Mode label.
- Added `docs/RAILWAY_DEPLOY.md` with deploy steps, required env vars, BYO API key flow, FFmpeg notes, and internal test checklist.
- Kept Cloud Beta default API mode as Bring Your Own API Key with no owner/admin key requirement.

## VelaFlow Beta 0.1.0 - Real Scene Rendering v1

- Added `core/veo_scene_renderer.py` for scene-level Veo job metadata, submit, poll, and download flow.
- Hook Clip Studio now exposes `Render Scene 1 with Veo`, `Poll Status`, and `Download Scene 1` controls.
- Veo scene rendering uses only the user's BYO Gemini/Veo key from runtime session state; keys are never saved to project files or exports.
- Existing local placeholder scene rendering remains available when Veo is missing, unsupported, or fails.
- The final MP4 combine pipeline now preserves an existing `scene_01.mp4` instead of overwriting a real provider-rendered scene.

## VelaFlow Beta 0.1.0 - First Real Output Pipeline

- Added `providers/veo_provider.py` with BYO-key Veo payload, submit, poll, and download connector functions.
- Added `core/real_clip_pipeline.py` for real local vertical MP4 output using FFmpeg scene clips, SRT subtitles, optional voiceover audio, and final clip combine.
- Upgraded `core/voiceover_engine.py` with OpenAI TTS support and FFmpeg silent-MP3 fallback when TTS is unavailable.
- Added Real Output Mode controls to Hook Clip Studio plus Seller, Podcast, and Viral hook clip previews.
- Smoke tests now verify SRT export, MP3 fallback, scene MP4 rendering, final hook MP4 export, and Veo missing-key safety.

## VelaFlow Beta 0.1.0 - Hook Clip Factory Foundation

- Added Hook Clip Studio (Beta) as a focused 5-10 second vertical clip workflow.
- Added `core/hook_clip_engine.py` and `core/scene_story_engine.py` for hook scoring, multi-scene clip planning, subtitle timing, thumbnail prompts, captions, hashtags, and render-ready payloads.
- Added local-only product link analyzer foundation for Shopee/TikTok Shop links without scraping or automation.
- Added lightweight voiceover timing plan export for podcast-style hook clips without calling real TTS providers.
- Added combine-pipeline fallback manifests so scene packages can be prepared even when MoviePy/FFmpeg/video clips are unavailable.
- Integrated hook clip generation into Seller Studio, Podcast Studio, Viral Clips Studio, and the new Hook Clip Studio page.

## VelaFlow Beta 0.1.0 - Online Beta Prep

- Updated release identity and sidebar build label to `VelaFlow Beta 0.1.0`.
- Kept Bring Your Own API Key as the default API mode for beta testers.
- Added browser localStorage persistence for user API keys while keeping runtime copies in Streamlit session state only.
- Confirmed user API keys are not written to project data, analytics, logs, exports, packages, or server JSON files.
- Added a clean `.env.example` with empty key placeholders only.
- Kept Song Studio generation logic unchanged for this release prep pass.

## VelaFlow V7.8.6a - Song Structure Intelligence v1

- Added `core/song_structure_intelligence.py` for lightweight producer-style structure planning.
- Added `config/presets/song_structure_presets.json` with Vela Moon Pop Rock, Standard Pop, TikTok Hook First, Emotional Ballad, Cinematic Story, and Viral Short Form presets.
- Added Creator Wizard structure selection and preview.
- Added Song Studio structure plan preview, refresh, and prompt context for hooks and full lyrics.
- Exports `song_structure_plan.json` and `song_structure_plan.md` with Suno files.
- Preserved Thai lyrics and English-only instrument tag rules.

## VelaFlow V7.8.6 - Creator Wizard Guided Setup

- Upgraded Creator Wizard into a five-step local guided creative setup.
- Added offline Creative Direction generation for topic, mood, music direction, artist preset, and target platform.
- Saves `creative_direction.json` under the project folder and passes direction context into Song Studio.
- Preserved the old template loader under `Advanced: Apply Project Template`.
- Song Studio now displays loaded Creative Direction and can clear it.

## VelaFlow V7.8.5b - Section Selector Reset Fix

- Fixed sidebar section changes snapping back to START when the previous page belonged to another group.
- Navigation validation now keeps a valid selected section and moves the selected page to that section's first page.
- Added smoke checks for selecting SONG, VISUAL, and PRODUCTION in Full Pipeline and hiding VISUAL/PRODUCTION in Song Studio Only.

## VelaFlow V7.8.5a - Visual Polish Pass

- Added `core/ui_styles.py` with global Streamlit CSS helpers.
- Improved font rendering, typography weight, caption contrast, and page spacing.
- Improved sidebar contrast, expander borders, metric/KPI card hierarchy, button consistency, and table framing.
- Kept navigation, render, provider, export, hook, and artist preset logic unchanged.

## VelaFlow V7.8.5 - Navigation & Layout Organization Pass

- Reorganized sidebar groups into START, SONG, VISUAL, PRODUCTION, INTELLIGENCE, and SYSTEM.
- Moved Artist Preset Manager into the SONG workflow group.
- Updated Song Studio Only navigation to show only Dashboard, Song Studio, Song Library, Artist Preset Manager, AI Settings, and System Health.
- Added concise menu labels for Clip Factory, Quality Audit, and Recovery Tools while keeping internal page keys backward compatible.
- Polished dashboard hierarchy and standardized headers on key pages.

## VelaFlow V7.8.4 - Artist Preset Manager

- Added local Artist Preset Manager UI for create/edit/duplicate/import/export/default preset workflows.
- Added `config/artist_presets/default_artist.json` for the default artist preset.
- Locked Vela Moon as a protected system preset that can be viewed, exported, used, and duplicated but not overwritten or deleted.
- Added stronger artist preset validation for required fields, English-only instrument tags, and Suno setting ranges.
- Updated Song Studio to load the configured default artist preset.

## VelaFlow V7.8.3f - Hook Variety + Suno Export Visibility Fix

- Hook candidate generation now uses the active Gemini text provider when an API key exists.
- Hook prompts include theme, mood, genre, artist preset, timestamp, and random seed.
- Added Regenerate Hooks and Clear Hook Cache controls.
- Added offline fallback warning for hook generation.
- Made Suno full package path and exports folder path visible after Save Lyrics.
- Song Library now shows Suno TXT readiness.

## VelaFlow V7.8.3e - Suno Export & Download Flow

- Added `core/suno_export.py` for full Suno TXT and lyrics-only exports.
- Save Lyrics now creates `exports/suno_full_package.txt` and `exports/lyrics_only.txt`.
- Added Song Studio download buttons and copy-ready lyrics block after save.
- Added Suno export files to Export Package and Final Package outputs.

## VelaFlow V7.8.3d - Streamlit Navigation State Fix

- Added `pending_navigation` to safely defer section/page updates until before sidebar widgets render.
- Updated `go_to_page()` to avoid mutating `selected_section` and `selected_page` after widget creation.
- Updated Song Studio Only mode navigation fallback to use pending navigation.

## VelaFlow V7.8.3c - UX Polish & Cleanup Pass

- Simplified delete UX to checkbox confirmation only while preserving deleted backups.
- Replaced raw hook candidate views with readable cards, score bars, and selected badges.
- Added compact sidebar project info and grouped license status.
- Tightened Song Studio Only navigation to show only Dashboard, Song Studio, Song Library, and AI Settings.
- Improved empty states and feedback messages for daily usage.

## VelaFlow V7.8.3b - Project Cleanup & Song Library

- Added `core/project_manager.py` for safe local project management.
- Added sidebar actions for Load, New, Rename, Archive, Delete, and Refresh.
- Added Song Library page for song-only projects and drafts.
- Added Song Studio Only workflow mode saved in `config/user_preferences.json`.
- Delete now requires confirmation and creates a deleted backup before removal.

## VelaFlow V7.8.3a - Navigation Flow Fix

- Added centralized Streamlit navigation helper `go_to_page(section, page)`.
- Bound sidebar section/page widgets to `selected_section` and `selected_page`.
- Fixed Song Studio `Save Lyrics & Continue to MV Director` rerun navigation.
- Updated dashboard quick navigation and Render Lab shortcut to use the same helper.

## VelaFlow V7.8.3 - Song Studio Workflow Restoration

- Restored multi-hook candidate workflow in Song Studio.
- Added selected-hook save metadata and lightweight song draft history.
- Restored clear Save Lyrics, Save Draft, Load Last Saved Lyrics, and Save Lyrics & Continue flow.
- Kept Vela Moon Artist Preset and English-only instrument tag normalization active.
- Added hook metadata to Song Studio exports and final package song files.
