# Changelog

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
