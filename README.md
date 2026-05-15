# VelaFlow

**VelaFlow** is an **AI Content Automation Pipeline** by **VelaLab**.

Current beta release: **VelaFlow Beta 0.1.0**.

It is evolving into an **AI Automatic Creator Workflow** for short-form content:
hooks, seller clips, podcast clips, viral character ideas, render-ready scene
packages, and export bundles. It is still one local Streamlit application, with
a modular architecture prepared for future feature-based licensing.

## Cloud Beta Focus

VelaFlow Beta 0.1.0 focuses on hook-first vertical workflows instead of full MV
production:

- Hook Clip Studio (Beta): turn a music, seller, podcast, or viral idea hook
  into a 5-10 second multi-scene vertical clip package.
- Real Scene Rendering v1: Hook Clip Studio can submit Scene 1 to Google Veo
  with the user's own Gemini/Veo key, poll status, download `scene_01.mp4`,
  then combine it into the final hook clip.
- Seller Studio: product/campaign inputs, optional product image, product-link
  analyzer foundation, creator scripts, and hook clip preview.
- Podcast Studio: emotional storytelling scripts, quote hooks, voiceover timing
  plan export, and hook clip preview.
- Viral Clips Studio: short-form scripts and viral character/meme-style clip
  direction.
- Rendering Connector: provider-ready packages and mock job flow. VelaFlow can
  render local placeholder scene clips, but does not call external video
  rendering APIs unless a BYO provider connector is explicitly used.
- First Real Output Pipeline: Hook Clip Studio can now generate scene MP4s,
  combine them into a vertical `final_hook_clip.mp4`, export `subtitles.srt`,
  and create a voiceover MP3 fallback when OpenAI TTS is unavailable.

Deployment foundation files are included for closed beta hosting:

- `Procfile` starts Streamlit with the platform-provided `$PORT`.
- `railway.json` uses a Nixpacks build and the same Streamlit start command.
- `nixpacks.toml` installs FFmpeg for Railway local MP4 render support.
- `runtime.txt` pins the intended cloud Python runtime.

For internal Railway testing, set `VELAFLOW_MODE=CLOUD`. See
`docs/RAILWAY_DEPLOY.md`.

## Modules

- Core: config, project management, storage paths, app state, shared utilities
- Director: song analysis, lyrics analysis, scene plan, storyboard, emotion map
- Motion: camera movement, zoom, pan, cinematic movement
- Render: render queue, export, encode, cache, failed-job recovery foundation
- Clips: shorts generation, hook detection, vertical crop, caption-ready output
- Canvas: Spotify Canvas and short loop export foundation
- Marketing: title, description, caption, hashtags, SEO/release metadata
- Assets: images, audio, video, thumbnails, generated files
- Providers: Gemini, OpenAI GPT, xAI Grok, image/video providers, local fallback, abstraction layer
- Licensing: local mock license package and feature flags

## AI Providers

VelaFlow supports Gemini, OpenAI GPT, and xAI Grok through the shared provider interface:

- `GEMINI_API_KEY`
- `OPENAI_API_KEY`
- `XAI_API_KEY`
- `DEFAULT_AI_PROVIDER=gemini`, `openai`, or `xai`

The provider can also be selected inside **AI Settings**. If the selected
provider has no API key, VelaFlow shows a warning and keeps offline fallback
behavior instead of crashing.

Cloud Beta supports **Bring Your Own API Key** from AI Settings:

- API Mode defaults to `Use My Own API Key`, so beta tester usage belongs to
  the tester's selected provider account.
- `Use VelaFlow Beta Key` uses environment keys such as `GEMINI_API_KEY`,
  `OPENAI_API_KEY`, or `XAI_API_KEY` when configured.
- User-entered API keys are stored in browser `localStorage` for this
  device/browser and mirrored into Streamlit `session_state` at runtime. They
  are never written to `project_data`, analytics, logs, exports, package files,
  or server JSON files.
- Local storage keys are `velaflow_api_mode`, `velaflow_ai_provider`,
  `velaflow_gemini_key`, `velaflow_openai_key`, and `velaflow_xai_key`.
- Use **Forget API Key** to remove the selected provider key from both
  `localStorage` and the current Streamlit session. Do not use shared devices
  for personal API keys.

xAI Grok uses the OpenAI-compatible endpoint `https://api.x.ai/v1` with the
default text model `grok-4.3`.

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

## V7.8.3e Suno Export & Download Flow

After saving lyrics, Song Studio now creates ready-to-use Suno files:

- `exports/suno_full_package.txt`
- `exports/lyrics_only.txt`

The Save flow shows download buttons, a copy-ready lyrics block, and a direct
Continue to MV Director action. Export packages and final packages also include
the Suno text exports.

## V7.8.3f Hook Variety + Suno Export Visibility Fix

Song Studio hook generation now calls the active text provider when a Gemini key
is available, includes mood/genre/theme/preset/seed context to reduce repeated
hooks, and warns when offline fallback hooks are used. The Suno export path and
exports folder path are shown directly after Save Lyrics.

## V7.8.4 Artist Preset Manager

VelaFlow now includes a local Artist Preset Manager for Song Studio:

- create, edit, duplicate, import, export, and delete custom artist presets
- set the default artist preset in `config/artist_presets/default_artist.json`
- keep Vela Moon locked as the protected system preset
- validate English-only instrument lists and section arrangement tags
- load the configured default preset automatically in Song Studio

This remains offline-first. No cloud sync, payment, marketplace, or online
license flow was added.

## V7.8.5 Navigation & Layout Organization Pass

The sidebar is organized for daily use:

- START: Dashboard, Creator Wizard
- SONG: Song Studio, Song Library, Artist Preset Manager
- VISUAL: MV Director, Character Studio, Image Lab, Image Review, Video Lab
- PRODUCTION: Render Lab, Clip Factory, Marketing Package, Final Package
- INTELLIGENCE: Creative Intelligence, Quality Audit, Beta Test Mode, Asset Intelligence
- SYSTEM: Queue Monitor, System Health, Recovery Tools, AI Settings

Song Studio Only mode now hides the heavier visual, production, export, and
intelligence pages while keeping Dashboard, Song Studio, Song Library, Artist
Preset Manager, AI Settings, and System Health available.

## V7.8.5a Visual Polish Pass

VelaFlow now applies a global visual polish layer from `core/ui_styles.py`:

- sharper font rendering with Inter, Segoe UI, Arial, sans-serif
- stronger sidebar contrast and expander borders
- clearer KPI cards, hook cards, and dashboard hierarchy
- more consistent button sizing, borders, and hover feedback
- framed tables/dataframes with better readability

This pass only changes visual styling. Navigation, providers, render/export
systems, Song Studio workflow, Artist Presets, and English tag normalization are
unchanged.

## V7.8.5b Section Selector Reset Fix

The sidebar Section dropdown now keeps the selected group instead of snapping
back to START. If the old page does not belong to the newly selected section,
VelaFlow automatically opens the first page in that section.

## V7.8.6 Creator Wizard Guided Setup

Creator Wizard now helps start a project even when the idea is still fuzzy:

- choose song topic, mood, music direction, artist preset, and target platform
- generate a local/offline Creative Direction summary
- save `creative_direction.json` inside the project folder
- pass the direction into Song Studio for hook and lyric generation
- keep the old template loader under `Advanced: Apply Project Template`

The wizard prepares direction only. Song Studio remains the lyrics and Suno
workflow page.

## V7.8.6a Song Structure Intelligence v1

Song Studio now understands the producer-level song flow before generating
lyrics:

- choose a structure preset such as Vela Moon Pop Rock, TikTok Hook First, or
  Cinematic Story
- preview section order, energy curve, emotional arc, and hook placement
- save `song_structure_plan.json` inside the project folder
- include the structure plan in hook and full lyric prompts
- export `song_structure_plan.json` and `song_structure_plan.md` with Suno files

This is a lightweight planning layer. It is not a DAW, MIDI/chord engine, or
complex music theory system.

## How to Run Locally

1. Create and activate a virtual environment.

```powershell
cd path\to\velaflow
python -m venv .venv
.\.venv\Scripts\activate
```

2. Install dependencies.

```powershell
pip install -r requirements.txt
```

3. Optional: copy `.env.example` to `.env` for local environment keys. For
beta testing, users can also paste their own Gemini/OpenAI/xAI key in
**AI Settings**. User-entered keys are stored only in that browser/device via
`localStorage` and are not written to project files, analytics, logs, exports,
or package files.

4. Run the app.

```powershell
python -m streamlit run app/main.py --server.port 8502
```

Backward-compatible note: the app can still run from an older local folder, but
new startup scripts, docs, and package names use the product slug `velaflow`.

New public-beta project folders are workflow-specific:

- `project_data/music/`
- `project_data/seller/`
- `project_data/podcast/`
- `project_data/clips/`
- `project_data/mv/`

Legacy projects under `project_data/projects/` remain readable.

## Beta Deployment Notes

- Current release label: **VelaFlow Beta 0.1.0**.
- Do not commit `.env`, `.venv/`, runtime folders, generated exports, analytics
  data, logs, or project output folders.
- `.env.example` intentionally contains empty placeholders only. Never add real
  API keys to repository files.
- Default API mode is **Use My Own API Key**, so beta tester provider usage
  belongs to each tester.
- Rendering jobs are currently mock/local metadata flows. They do not call real
  video rendering APIs yet.
- AI outputs should be reviewed before publishing.
- For online deployment, configure provider keys through the deployment
  platform's secret/environment variable system only when using
  **Use VelaFlow Beta Key**.

## Test

```powershell
cd path\to\velaflow
.\.venv\Scripts\python.exe -m compileall -q app core providers tests
.\.venv\Scripts\python.exe tests\smoke_test.py
```

Generic command:

```powershell
python tests/smoke_test.py
```

## Closed Beta Package

```powershell
python scripts/build_beta_package.py
```

The package script creates `outputs/beta_packages/velaflow_closed_beta_<version>.zip`
and excludes `.env`, `.venv/`, `project_data/`, caches, logs, temp files, and
generated outputs. See `docs/BETA_RELEASE_CHECKLIST.md` and `docs/BETA_NOTES.md`.

## Identity

Current app identity is defined in `core/version.py` and `core/branding.py`.
Exports and manifests include `generated_by`, `app_version`, `build_version`,
and release-channel metadata where applicable.

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
