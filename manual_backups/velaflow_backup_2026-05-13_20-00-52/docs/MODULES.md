# VelaFlow Modules

VelaFlow is one application with modular internal capabilities. The modules are
not separate products yet, but every module has a feature flag so it can become
part of a package plan later.

| Module | Description | Feature Flag | Depends On | Future Plans |
|---|---|---|---|---|
| Core | Base systems: config, project management, storage, app state, utilities, healthcheck, reports | `core_enabled` | none | project migrations, stronger recovery, shared service registry |
| Director | Song analysis, lyrics analysis, scene plan, storyboard, emotion map | `director_enabled` | Core, Providers | richer scene scoring, arrangement-aware planning |
| Motion | Image motion, camera movement, zoom, pan, cinematic drift | `motion_enabled` | Core, Render | parallax, motion curves, beat-reactive tuning |
| Render | FFmpeg render pipeline, queue, encode, cache, manifests, resume foundation | `render_enabled` | Core, Motion, Assets | failed render resume, render farm readiness |
| Clips | Shorts, hook detection, vertical crop, caption-ready clip outputs | `clips_enabled` | Core, Render, Marketing | batch clip strategy, platform-specific presets |
| Canvas | Spotify Canvas and loop-oriented short motion exports | `canvas_enabled` | Core, Motion, Clips | seamless loop scoring, canvas preview wall |
| Marketing | YouTube/TikTok/Facebook copy, hashtags, SEO metadata, post plan | `marketing_enabled` | Core, Director, Clips | campaign calendar, A/B copy sets |
| Assets | Images, audio, video, thumbnails, generated files, cache, cleanup | `assets_enabled` | Core | asset provenance, archive lifecycle, dedupe |
| Providers | Gemini, image providers, video providers, local fallback, abstraction | `providers_enabled` | Core | provider marketplace, quota dashboards |
| Licensing | Local license service, package flags, module visibility | `licensing_enabled` | Core | online activation, team/cloud plans later |

## V7.0 Creator Experience Layer

The Creator Experience layer lives inside Core for now. It is not a separate
licensed module yet, but it prepares the product for faster project startup and
consistent output.

| System | File | Purpose |
|---|---|---|
| Project Templates | `config/presets/project_templates.json` | preload render, subtitle, motion, color, prompt, and song structure defaults |
| Preset Packs | `config/presets/preset_packs.json` | bundle workflow choices for common outputs such as TikTok Fast and Cinematic |
| Scene Presets | `config/presets/scene_presets.json` | provide reusable visual vocabulary for storyboard consistency |
| Global Presets | `config/presets/global_presets.json` | central list of shared motion, subtitle, render, and prompt preset names |
| Creator Wizard | `app/main.py` | step-by-step project start and workflow navigation |
| Style Consistency | `core/style_consistency.py` | local quality check for visual identity continuity |

## V7.1 Creator Productivity Layer

| System | File | Purpose |
|---|---|---|
| Smart Asset Library | `core/asset_library.py` | index, search, export, import, and reuse project assets |
| Prompt Memory | `core/prompt_memory.py` | remember creator style preferences and preload project settings |
| Scene Reuse | `core/scene_reuse.py` | recommend previous assets/prompts for current scenes |
| Creative Suggestions | `core/creative_suggestions.py` | offline quality heuristics for motion, subtitles, hooks, color, and prompts |
| Workspace Optimizer | `core/workspace_optimizer.py` | workspace size reports, thumbnail index, cache TTL cleanup |
| Preset Bundle Import/Export | `core/preset_marketplace.py` | offline preset pack portability without online marketplace logic |
| One Click Workflow | `core/one_click_workflow.py` | queue-ready plans for draft MV, TikTok set, and release package flow |

## V7.2 Creative Intelligence Layer

| System | File | Purpose |
|---|---|---|
| Emotional Arc Analyzer | `core/emotional_arc.py` | understand intro mood, rise, climax, ending tone, pacing, transition, color, and motion |
| Hook Intelligence | `core/hook_intelligence.py` | detect sticky lines, subtitle emphasis, and shorts-ready scenes |
| Visual Continuity | `core/visual_continuity.py` | detect inconsistent color, motion, and subtitle style |
| Cinematic Advisor | `core/cinematic_advisor.py` | recommend cinematic camera, motion, color, and subtitle decisions |
| Adaptive Profiles | `core/adaptive_profiles.py` | choose Draft/Standard/TikTok Fast/Cinematic from creative signals |
| Creative Timeline | `core/creative_timeline.py` | visual table of scenes, beat feel, lyrics, motion, subtitles, transitions, and color |
| Asset Graph | `core/asset_graph.py` | map prompt, scene, asset, and motion relationships |

## V7.3 Cinematic Director Layer

| System | File | Purpose |
|---|---|---|
| Shot Type Intelligence | `core/shot_intelligence.py` | recommend close-up, medium, wide, over-shoulder, silhouette, and handheld framing |
| Camera Language Engine | `core/camera_language.py` | translate emotion into cinematic camera language and motion hints |
| Scene Rhythm Analyzer | `core/scene_rhythm.py` | evaluate cut density, pacing balance, chorus intensity, and breathing room |
| Visual Story Consistency | `core/visual_story_consistency.py` | check character, color, emotional, and lighting continuity |
| Director Notes | `core/director_notes.py` | inject director notes into prompt, motion, subtitle, and render metadata |
| Cinematic Style Packs | `core/cinematic_style_packs.py` | apply local inspired cinematic packs from config presets |
| Smart Scene Ordering | `core/smart_scene_ordering.py` | analyze emotion flow and propose smoother scene order |

## V7.4 Narrative & Performance Layer

| System | File | Purpose |
|---|---|---|
| Narrative Arc Engine | `core/narrative_arc.py` | classify beginning, tension, emotional peak, release, ending, and scene roles |
| Performance Emotion Mapping | `core/performance_emotion.py` | inject restrained sadness, emotional explosion, silent regret, and hopeful ending |
| Visual Metaphor Suggestions | `core/visual_metaphor.py` | add rain, neon, empty road, mirror, shadow, and light metaphors from emotion |
| Cinematic Beat Sync | `core/cinematic_beat_sync.py` | map emotional beat, lyric beat, visual beat, and sync actions |
| Dynamic Subtitle Emotion | `core/subtitle_emotion.py` | recommend chorus size, hook glow, whisper, soft warm, or restrained subtitle behavior |
| Emotional Render Profiles | `core/emotional_render_profiles.py` | choose heartbreak, nostalgic, uplifting, lonely night, or emotional explosion render settings |

## V7.5 Production Review Layer

| System | File | Purpose |
|---|---|---|
| Full Project Audit | `core/production_audit.py` | score the project 0-100 before final render/export |
| Final Quality Gate | `core/production_audit.py` | check narrative, character, subtitles, hooks, render, assets, platform packages, and final package readiness |
| Producer Fix List | `core/production_audit.py` | prioritize what to fix before final render |

## V7.6 Release Hardening Layer

| System | File | Purpose |
|---|---|---|
| Render Recovery | `core/render_recovery.py` | track render state, failed scenes, temp clips, and diagnostic bundles |
| Project Lock | `core/project_lock.py` | prevent accidental parallel local edits |
| Safe Mode | `core/safe_mode.py` | open damaged project files without hard crashing |
| Common Fixes | `core/common_fixes.py` | repair common missing keys/defaults/stale asset paths offline |
| Pre-render Healthcheck | `core/healthcheck.py` | verify FFmpeg, writable paths, storyboard, assets, audio, and render output before render |

## V7.7 Beta Test Layer

| System | File | Purpose |
|---|---|---|
| Beta Test Session | `core/beta_testing.py` | record real project test runs with song, template, render profile, notes, ratings, and audit score |
| Beta Checklist | `core/beta_testing.py` | verify Song, Storyboard, Image, Motion, Subtitle, Render, Clips, and Marketing have been reviewed |
| Issue Log | `core/beta_testing.py` | track project-level bugs by area, severity, status, and description |
| Render Version Compare | `core/beta_testing.py` | compare key output files between two render folders |
| Stable Candidate Marker | `core/beta_testing.py` | mark a session/build as a stable candidate after real project testing |
| Beta Report Export | `core/beta_testing.py` | export JSON and Markdown reports for review history |

## V7.8 Stable Candidate Freeze Layer

| System | File | Purpose |
|---|---|---|
| Stable Build Summary | `core/stable_build.py` | summarize ready features, known issues, not-done items, and freeze policy |
| Stable Candidate Snapshot | `core/stable_build.py` | export rollback evidence with audit, diagnostics, beta report, project snapshot, and manifest |
| Optional Smoke Evidence | `core/stable_build.py` | run `tests/smoke_test.py` and save the result into release evidence |
| Freeze Documentation | `STABLE_BUILD.md` | define the stable candidate target and rule that core pipeline changes are bug-fix only |

## V7.8.1 Artist Preset Hotfix Layer

| System | File | Purpose |
|---|---|---|
| Artist Presets | `core/artist_presets.py` | load, validate, save, list, and fallback artist identity presets |
| Vela Moon Preset | `config/artist_presets/vela_moon.json` | default emotional easy-listening Thai pop rock identity |
| Instrument Tag Normalizer | `core/instrument_tag_normalizer.py` | normalize Thai text inside parentheses into English-only production tags |
| Song Export Metadata | `core/exporter.py` | export normalized Suno lyrics, artist preset JSON, and validation JSON |

## Additional Feature Flags

- `batch_render_enabled`: allow batch render/export workflows
- `export_without_watermark`: allow clean commercial exports
- `commercial_use`: mark package as commercially usable

## Rule

UI and workflow code should ask `LicenseService` whether a module or feature is
enabled. Do not scatter `if premium` or package-name checks throughout the app.
