# VelaFlow

**VelaFlow** is an **AI Content Automation Pipeline** by **VelaLab**.

It helps produce music content workflows from song planning through storyboard,
image/motion review, render, short clips, marketing copy, and final release
packages. It is still one local Streamlit application, with a modular
architecture prepared for future feature-based licensing.

## Modules

- Core: config, project management, storage paths, app state, shared utilities
- Director: song analysis, lyrics analysis, scene plan, storyboard, emotion map
- Motion: camera movement, zoom, pan, cinematic movement
- Render: render queue, export, encode, cache, failed-job recovery foundation
- Clips: shorts generation, hook detection, vertical crop, caption-ready output
- Canvas: Spotify Canvas and short loop export foundation
- Marketing: title, description, caption, hashtags, SEO/release metadata
- Assets: images, audio, video, thumbnails, generated files
- Providers: Gemini, image/video providers, local fallback, abstraction layer
- Licensing: local mock license package and feature flags

## V7.0 Creator Experience

VelaFlow includes a local template and preset system for faster project starts:

- Project Templates: Emotional Pop Rock, Sad Cinematic, TikTok Viral, Night
  Drive, Isaan Indie, Acoustic Heartbreak
- Preset Packs: TikTok Fast Pack and Cinematic Pack
- Scene Preset Library: reusable visual scenes for storyboard consistency
- Creator Wizard: step-by-step workflow from template selection to final package

Preset files live in `config/presets/`. See `docs/TEMPLATE_SYSTEM.md` for the
implementation map.

## V7.1 Creator Productivity

VelaFlow now includes local creator velocity tools:

- Smart Asset Library for reusable images, prompts, hooks, characters, and video slots
- Prompt Memory for preferred cinematic style, subtitles, motion, and color
- Scene Reuse recommendations for consistency across projects
- Offline Creative Suggestions for subtitle, motion, color, prompt, and hook checks
- Workspace Performance tools for cache reports and thumbnail indexing
- Offline Preset Bundle import/export
- One-click workflow buttons for draft MV, TikTok set, and release package flow

See `docs/CREATOR_PRODUCTIVITY.md` for details.

## V7.2 Creative Intelligence

VelaFlow now includes offline-first creative analysis:

- Emotional Arc Analyzer
- Hook Intelligence
- Visual Continuity Analyzer
- Auto Cinematic Suggestions
- Adaptive Render Profiles
- Creative Timeline View
- Asset Relationship Graph

See `docs/CREATIVE_INTELLIGENCE.md` for details.

## V7.3 Cinematic Director

VelaFlow now adds offline cinematic direction:

- Shot Type Intelligence
- Camera Language Engine
- Scene Rhythm Analyzer
- Visual Story Consistency
- Director Notes injection
- Cinematic Style Packs
- Smart Scene Ordering

See `docs/CINEMATIC_DIRECTOR.md` for details.

## V7.4 Narrative & Performance

VelaFlow now understands more story and performance language:

- Narrative Arc Engine
- Performance Emotion Mapping
- Scene Role Classification
- Visual Metaphor Suggestions
- Cinematic Beat Sync
- Dynamic Subtitle Emotion
- Emotional Render Profiles

See `docs/NARRATIVE_PERFORMANCE.md` for details.

## V7.5 Production Review

VelaFlow now includes a final quality gate:

- Full Project Audit score 0-100
- Narrative, character, subtitle, asset, render, hook, TikTok, YouTube, and final package checks
- Producer-style verdict
- Prioritized fixes before final render/export

See `docs/PRODUCTION_AUDIT.md` for details.

## V7.6 Release Hardening

VelaFlow now includes local stability tools:

- Render failure recovery and render state files
- Resume-friendly scene cache tracking
- Diagnostic bundle export
- Local project lock files
- Safe Mode for damaged project JSON
- Pre-render healthcheck
- Offline Fix Common Issues
- Backups before audit and final package builds

See `docs/RELEASE_HARDENING.md` for details.

## V7.7 Beta Test Mode

VelaFlow now includes a structured real-project beta testing workflow:

- Beta Test Sessions with song, template, render profile, and notes
- Ratings for Song, Storyboard, Image, Motion, Subtitle, Render, Clips, and Marketing
- Per-project bug/issue log
- Beta Test Checklist
- Compare two render versions
- Export Beta Test Report
- Mark a build as Stable Candidate

See `docs/BETA_TEST_MODE.md` for details.

## V7.8 Stable Candidate Freeze

VelaFlow now includes a freeze workflow before V8 or packaging:

- Freeze target: `VelaFlow V7.7 Stable Candidate 1`
- `STABLE_BUILD.md` release summary
- Stable Candidate Snapshot export
- Diagnostic bundle + production audit + beta report in one evidence folder
- Optional smoke test result captured as release evidence
- ZIP archive for rollback/review
- Freeze policy: no core pipeline changes after freeze except bug fixes

See `docs/STABLE_CANDIDATE_FREEZE.md` for details.

## V7.8.1 Artist Presets + English Instrument Tags Hotfix

Song Studio now has a Vela Moon artist identity layer:

- Default artist preset: Vela Moon
- Thai lyrics remain Thai
- Music Style Prompt is English only
- Instrument and production tags inside parentheses are normalized to English
- Suno exports include `artist_preset.json` and `instrument_tag_validation.json`

See `docs/ARTIST_PRESETS.md` and `docs/PROMPT_RULES.md`.

## V7.8.1b Full UI Recovery

The full VelaFlow sidebar workflow has been restored after the Song Studio
hotfix. See `docs/UI_FLOW_CHECKLIST.md` for page-level status.

## V7.8.1c UI Polish Pass

The restored UI now groups sidebar navigation, keeps project/status panels
readable, improves the dashboard audit/next-step snapshot, and keeps Song
Studio Artist Preset and English tag controls visible.

## V7.8.2 Production Hygiene

VelaFlow now includes source packaging prep:

- `.gitignore`
- `.packageignore`
- `scripts/create_source_package.py`
- `docs/PACKAGING_NOTES.md`

The source package excludes `.env`, `.venv/`, caches, render temp files,
`__pycache__/`, and `*.pyc`.

## V7.8.3 Song Studio Workflow Restoration

Song Studio restores the creator flow from earlier VelaFlow builds:

- generate 3-5 hook candidates before full lyrics
- select a hook with emotional, catchy, and TikTok scores
- generate full lyrics from the selected hook and Vela Moon artist preset
- normalize instrument/production tags inside parentheses to English
- save lyrics clearly to `song.json` and `lyrics.txt`
- keep lightweight draft history under `song_drafts/`
- continue directly to MV Director after saving

## V7.8.3a Navigation Flow Fix

VelaFlow now uses centralized Streamlit navigation state:

- `selected_section`
- `selected_page`

The Song Studio button `Save Lyrics & Continue to MV Director` now saves first,
switches the sidebar to `Creation`, and opens `MV Director` after rerun.

## V7.8.3b Project Cleanup & Song Library

VelaFlow now includes safer local project cleanup:

- Current Project sidebar management: New, Rename, Archive, Delete, Refresh
- Song Library page for song-only projects and drafts
- Archive moves projects to `project_data/archive/`
- Delete requires confirmation and creates a backup under `project_data/deleted_backups/`
- Song Studio Only mode hides heavier pipeline menus without removing features

See `docs/PROJECT_MANAGEMENT.md`.

## V7.8.3c UX Polish & Cleanup Pass

This pass smooths daily usage before real project testing:

- Delete now needs only a confirm checkbox while keeping backup-before-delete
- Hook candidates render as readable cards with score bars and selected badge
- Sidebar project info shows status, workflow mode, modified time, and preset
- Song Studio Only mode fully hides image/video/render/marketing navigation
- Empty states guide first-time song/project creation

## V7.8.3d Streamlit Navigation State Fix

Navigation now uses `pending_navigation` for page changes triggered after
sidebar widgets are created. The pending target is applied before the next
sidebar render, preventing Streamlit session-state mutation crashes.

## Run

```powershell
cd "D:\Project AI\velaflow"
.\.venv\Scripts\activate
python -m streamlit run app/main.py --server.port 8501
```

Backward-compatible note: if your local folder is still named
`vela_ai_studio_v5`, the app continues to run from that folder. New docs and
paths use the product slug `velaflow`.

## Test

```powershell
cd "D:\Project AI\velaflow"
.\.venv\Scripts\python.exe tests\smoke_test.py
```

## Identity

Current app identity is defined in `core/version.py` and `core/branding.py`.
Exports and manifests include `generated_by`, `app_version`, and
`build_version`.

## Licensing Foundation

VelaFlow currently uses a local mock license file at `config/license.json`.
There is no payment, auth, server activation, or online license check yet.
Application modules should ask `LicenseService` for feature access instead of
hard-coding plan checks throughout the codebase.

## Theme and Export Policy

- Theme config: `config/theme.json`
- Watermark/export policy: `config/export.json`

## Safety

- No auto upload
- Offline/manual fallback remains supported
- Provider failures should not hard-crash the app
- Existing projects remain backward compatible where possible
