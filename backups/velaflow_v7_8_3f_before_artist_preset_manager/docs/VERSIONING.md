# Versioning

VelaFlow keeps project data backward compatible where possible.

## Product Version

The app title currently uses the `V7.8` product line while the product name has
changed to VelaFlow.

## Stable Candidate Freeze

V7.8 freezes `VelaFlow V7.7 Stable Candidate 1` as a rollback point before V8
or packaging work. Snapshot evidence is exported under
`outputs/stable_candidates/<project_name>/`.

## V7.8.1 Hotfix

V7.8.1 is **Artist Presets + English Instrument Tags Hotfix**. It adds the
Vela Moon artist preset and normalizes Suno instrument/production tags inside
parentheses to English while preserving Thai lyrics.

## V7.8.1b Hotfix

V7.8.1b is **Full UI Recovery**. It restores the full sidebar workflow after
the V7.8.1 Song Studio hotfix while preserving Artist Presets and English-only
instrument tag normalization.

## V7.8.1c Hotfix

V7.8.1c is **UI Polish Pass / UI Regression Restoration**. It keeps the full
V7.8.1b menu recovery, groups sidebar navigation, restores a cleaner dashboard
overview, and improves Song Studio/Render/Creative/Final Package layout without
changing core provider, render, export, cloud, payment, or licensing logic.

## V7.8.2 Hygiene

V7.8.2 is **Production Hygiene & Safe Packaging Prep**. It adds source packaging
rules, `.gitignore`, `.packageignore`, and a whitelist-based source package
script that excludes secrets, virtual environments, caches, render temp files,
and compiled bytecode.

## V7.8.3 Workflow Restoration

V7.8.3 is **Song Studio Workflow Restoration**. It restores the multi-step
creator flow for Song Studio: generate hook candidates, select a hook, generate
full lyrics from the selected hook and artist preset, normalize English-only
instrument tags, save lyrics, keep draft history, and continue to MV Director.

## V7.8.3a Hotfix

V7.8.3a is **Navigation Flow Fix**. It centralizes Streamlit navigation around
`selected_section` and `selected_page`, synchronizes sidebar section/page
widgets, and fixes `Save Lyrics & Continue to MV Director` so it opens the
Creation section and MV Director page after rerun.

## V7.8.3b Hotfix

V7.8.3b is **Project Cleanup & Song Library**. It adds safe local project
management, active/archived project separation, delete backups, a Song Library
page, and Song Studio Only workflow mode saved in `config/user_preferences.json`.

## V7.8.3c Polish

V7.8.3c is **UX Polish & Cleanup Pass**. It simplifies delete confirmation while
keeping backup-before-delete, renders Hook Candidates as cards, adds clearer
sidebar project info, tightens Song Studio Only navigation, and improves empty
states and success feedback.

## V7.8.3d Hotfix

V7.8.3d is **Streamlit Navigation State Fix**. It keeps centralized navigation
but routes post-widget page changes through `pending_navigation`, applying the
target section/page before sidebar widgets are created on the next rerun.

## V7.8.3e Hotfix

V7.8.3e is **Suno Export & Download Flow**. It creates `suno_full_package.txt`
and `lyrics_only.txt` after Save Lyrics, adds download/copy controls in Song
Studio, and includes the same files in export/final package outputs.

## V7.8.3f Hotfix

V7.8.3f is **Hook Variety + Suno Export Visibility Fix**. It routes hook
candidate generation through the active text provider when available, clears
old hooks before regenerate, warns on offline fallback hooks, and makes the
Suno full package path visible after Save Lyrics.

## Project Compatibility

Older projects created under Vela AI Studio naming can still be loaded. New
project metadata should use VelaFlow naming.

## Future Versioning Goals

- Storyboard snapshots
- Render manifests
- Clip metadata history
- Final package manifests
- Project migration notes for major schema changes
