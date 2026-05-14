# Changelog

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
