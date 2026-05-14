# UI Flow Checklist

VelaFlow V7.8.1b restores the full sidebar workflow after the V7.8.1 Song
Studio hotfix.

| Page | Status | Notes |
|---|---|---|
| Dashboard | PASS | Project status, quick navigation, recent projects, diagnostics |
| Creator Wizard | PASS | Template selection and project creation flow |
| Song Studio | PASS | Artist Preset, Vela Moon, English instrument tags, auto-fix tags |
| MV Director | PASS | Lyrics input and storyboard generation flow |
| Character Studio | PASS | Character profile and apply-to-storyboard action |
| Image Lab | PASS | Scene image prompt and placeholder generation |
| Image Review | PASS | Approve/reject image state |
| Video Lab | PASS | Manual/offline video slot generation |
| Render Lab | PASS | Render profile, aspect ratios, healthcheck, render action, temp recovery |
| Smart Clip Factory | PASS | Clip type selection, preview, clip set generation |
| Marketing Package | PASS | Build and export marketing package |
| Final Package | PASS | Inspect inputs and build final release package |
| Creative Intelligence | PASS | Scene scores, hooks, arc, suggestions, TikTok recommendations |
| Production Audit | PASS | Full project audit and export |
| Beta Test Mode | PASS | Sessions, checklist, ratings, issues, render compare, reports, stable snapshot |
| Asset Intelligence | PASS | Disk usage and safe cleanup buttons |
| Queue Monitor | PASS | Jobs table, clear finished, cancel job |
| System Health | PASS | Healthcheck and Safe Mode entry |
| Release Hardening Tools | PASS | Lock, release lock, common fixes, diagnostics, safe temp cleanup, duplicate |
| AI Settings | PASS | Provider/key status and safety note |
| Artist Preset Manager | PASS | Local preset create/edit/duplicate/import/export/default management |

Validation:

- `python tests/smoke_test.py` passes.
- `python -m compileall -q app core providers tests` passes.
- App launches on `http://localhost:8501/`.

## V7.8.1c UI Polish Result

| Page | Status | Notes |
|---|---|---|
| Dashboard | PASS | Cleaner overview, next step, project status, audit snapshot, recent projects |
| Creator Wizard | PASS | Template flow remains available |
| Song Studio | PASS | Artist Preset, Vela Moon, Use Preset, Force English Tags, Auto Fix, normalized output |
| MV Director | PASS | Lyrics input and storyboard generation remain visible |
| Character Studio | PASS | Character profile controls remain available |
| Image Lab | PASS | Scene prompt and image generation controls remain available |
| Image Review | PASS | Approve/reject state remains available |
| Video Lab | PASS | Offline/manual video slot workflow remains available |
| Render Lab | PASS | Render profile, aspect ratios, subtitle mode, healthcheck, preview/advanced controls |
| Smart Clip Factory | PASS | Clip and clip-set generation remain available |
| Marketing Package | PASS | Build/export marketing package remains available |
| Final Package | PASS | Preflight status and backup-before-build behavior visible |
| Creative Intelligence | PASS | Emotional Arc, Hook Intelligence, Cinematic Director, Narrative & Performance, Production Audit |
| Production Audit | PASS | Full audit and export report remain available |
| Beta Test Mode | PASS | Sessions, ratings, issues, compare, report/freeze remain available |
| Asset Intelligence | PASS | Disk usage and safe cleanup remain available |
| Queue Monitor | PASS | Jobs table, clear finished, cancel remain available |
| System Health | PASS | Healthcheck and Safe Mode remain available |
| Release Hardening Tools | PASS | Diagnostics, project lock, common fixes, recovery tools remain available |
| AI Settings | PASS | Provider/key status and safety note remain available |

Partial items: none recorded in this pass.

## V7.8.3 Song Studio Workflow Restoration

| Page | Status | Notes |
|---|---|---|
| Dashboard | PASS | Existing overview and navigation preserved |
| Creator Wizard | PASS | Existing template flow preserved |
| Song Studio | PASS | Multi-hook candidates, selected hook, full lyrics generation, Auto Fix Tags, Save Lyrics, Save Draft, Load Last Saved Lyrics, Continue to MV Director |
| MV Director | PASS | Lyrics continue to flow from normalized Song Studio output |
| Character Studio | PASS | No workflow change |
| Image Lab | PASS | No workflow change |
| Image Review | PASS | No workflow change |
| Video Lab | PASS | No workflow change |
| Render Lab | PASS | No workflow change |
| Smart Clip Factory | PASS | No workflow change |
| Marketing Package | PASS | Song hook metadata remains available for captions |
| Final Package | PASS | Song package includes hook metadata |
| Creative Intelligence | PASS | No workflow change |
| Production Audit | PASS | No workflow change |
| Beta Test Mode | PASS | No workflow change |
| Asset Intelligence | PASS | No workflow change |
| Queue Monitor | PASS | No workflow change |
| System Health | PASS | No workflow change |
| Release Hardening Tools | PASS | No workflow change |
| AI Settings | PASS | No workflow change |

Validation:

- `python -m compileall -q app core providers tests` passes.
- `python tests/smoke_test.py` passes.

## V7.8.3e Suno Export & Download Flow

| Page / Flow | Status | Notes |
|---|---|---|
| Save Lyrics | PASS | Creates Suno full package and lyrics-only export |
| Download Suno TXT | PASS | Streamlit download button available after save |
| Download Lyrics Only | PASS | Streamlit download button available after save |
| Copy Lyrics for Suno | PASS | Copy-ready lyrics text area available |
| Song Studio Status | PASS | Shows hook, lyrics, saved, and Suno TXT readiness |
| Export Package | PASS | Includes `exports/suno_full_package.txt` and `exports/lyrics_only.txt` |
| Final Package | PASS | Includes Suno export files under `exports/` |
| Empty State | PASS | Shows "No lyrics available yet." when no lyrics exist |

Validation:

- `python -m compileall -q app core providers tests` passes.
- `python tests/smoke_test.py` passes.

## V7.8.3c UX Polish & Cleanup Pass

| Page / Flow | Status | Notes |
|---|---|---|
| Delete UX | PASS | Checkbox-only confirmation, backup-before-delete preserved |
| Hook Candidate Cards | PASS | Hook text, scores, reason, usage, progress bars, selected badge |
| Current Project Info | PASS | Shows active/session status, workflow mode, modified time, artist preset |
| Feedback Messages | PASS | Save, draft, hook select, archive, delete, rename use clear feedback |
| Empty States | PASS | Friendly onboarding shown when no projects/songs exist |
| Song Studio Only Mode | PASS | Hides Image/Video/Render/Clips/Marketing/Final Package navigation |
| Sidebar Compactness | PASS | Project info and license status are grouped in expanders |

Validation:

- `python -m compileall -q app core providers tests` passes.
- `python tests/smoke_test.py` passes.

## V7.8.3b Project Cleanup & Song Library

| Page / Flow | Status | Notes |
|---|---|---|
| Sidebar Current Project | PASS | Active projects only, sorted by modified time, Load/New/Rename/Archive/Delete/Refresh |
| Song Library | PASS | Lists song projects with hook, preset, lyrics/storyboard/render readiness |
| Open in Song Studio | PASS | Loads selected project and navigates to Song Studio |
| Continue to MV Director | PASS | Loads selected project and switches to Full Pipeline if needed |
| Archive Project | PASS | Moves active project to `project_data/archive/` |
| Delete Project | PASS | Requires confirmation and creates `project_data/deleted_backups/` backup |
| Song Studio Only Mode | PASS | Keeps Dashboard, Song Studio, Song Library, AI Settings visible |
| Existing Menus | PASS | Full Pipeline mode keeps all restored VelaFlow menus |

Validation:

- `python -m compileall -q app core providers tests` passes.
- `python tests/smoke_test.py` passes.

## V7.8.3a Navigation Flow Fix

| Flow | Status | Notes |
|---|---|---|
| Sidebar Section Selector | PASS | Bound to `selected_section` |
| Sidebar Page Selector | PASS | Bound to `selected_page` |
| Song Studio -> MV Director | PASS | Save Lyrics & Continue sets `Creation` + `MV Director` before rerun |
| Dashboard Continue | PASS | Uses centralized `go_to_page()` helper |
| Dashboard Quick Nav | PASS | Song Studio, MV Director, Image Review, Render Lab, Final Package use centralized helper |
| Render Lab -> Smart Clip Factory | PASS | Uses centralized helper |
| Duplicate Sidebar Entries | PASS | No extra menu entries added |

Validation:

- `python -m compileall -q app core providers tests` passes.
- `python tests/smoke_test.py` passes.

## V7.8.4 Artist Preset Manager

| Page / Flow | Status | Notes |
|---|---|---|
| Artist Preset Manager | PASS | Added to System navigation and Song Studio Only mode |
| Vela Moon Locked Preset | PASS | Can view/export/duplicate, cannot edit/delete/overwrite |
| Custom Preset Editing | PASS | Basic, song, instruments, Suno, MV, and marketing fields visible |
| Default Artist Preset | PASS | Stored in `config/artist_presets/default_artist.json` and used by Song Studio |
| Import / Export | PASS | JSON download/upload with validation and locked-preset protection |
| Song Studio Integration | PASS | Dropdown loads all presets with default/locked/custom labels |

Validation:

- `python -m compileall -q app core providers tests` passes.
- `python tests/smoke_test.py` passes.

## V7.8.5 Navigation & Layout Organization

| Page / Flow | Status | Notes |
|---|---|---|
| START group | PASS | Dashboard, Creator Wizard |
| SONG group | PASS | Song Studio, Song Library, Artist Preset Manager |
| VISUAL group | PASS | MV Director, Character Studio, Image Lab, Image Review, Video Lab |
| PRODUCTION group | PASS | Render Lab, Clip Factory, Marketing Package, Final Package |
| INTELLIGENCE group | PASS | Creative Intelligence, Quality Audit, Beta Test Mode, Asset Intelligence |
| SYSTEM group | PASS | Queue Monitor, System Health, Recovery Tools, AI Settings |
| Full Pipeline menus | PASS | All existing pages remain visible with no duplicate page keys |
| Song Studio Only menus | PASS | Shows only Dashboard, Song Studio, Song Library, Artist Preset Manager, AI Settings, System Health |
| Dashboard quick navigation | PASS | Buttons target visible pages only in the active workflow mode |
| Song Studio continue | PASS | Continue to MV Director switches back to Full Pipeline when needed |
| Artist Preset Manager access | PASS | Accessible from the SONG group |
| Page headers | PASS | Key pages show title, subtitle, and current project context |

Validation:

- `python -m compileall -q app core providers tests` passes.
- `python tests/smoke_test.py` passes.
- App opens on `http://localhost:8501/`.

## V7.8.5a Visual Polish Pass

| Area | Status | Notes |
|---|---|---|
| Global CSS helper | PASS | `core/ui_styles.py` applies font, contrast, card, button, and table styles |
| Typography | PASS | Stronger title/page hierarchy and readable body/caption contrast |
| Sidebar | PASS | Higher contrast background, clearer labels, and stronger expander borders |
| Dashboard KPI cards | PASS | Metric cards use near-white panels, border, radius, shadow, and padding |
| Song Studio status/cards | PASS | Workflow metrics and hook containers inherit clearer card styling |
| Buttons | PASS | Primary and secondary buttons have consistent height, radius, border, and hover clarity |
| Tables | PASS | Dataframe/table containers have clearer border and readable framing |
| Navigation safety | PASS | No navigation state logic changed |

Validation:

- `python -m compileall -q app core providers tests` passes.
- `python tests/smoke_test.py` passes.
- App opens on `http://localhost:8501/`.

## V7.8.5b Section Selector Reset Fix

| Flow | Status | Notes |
|---|---|---|
| Full Pipeline selects SONG | PASS | Invalid previous page changes to `Song Studio` without resetting section |
| Full Pipeline selects VISUAL | PASS | Invalid previous page changes to `MV Director` without resetting section |
| Full Pipeline selects PRODUCTION | PASS | Invalid previous page changes to `Render Lab` without resetting section |
| Song Studio Only groups | PASS | Only START, SONG, SYSTEM are selectable |
| Hidden heavy groups | PASS | VISUAL and PRODUCTION are hidden in Song Studio Only mode |
| pending_navigation | PASS | Button-driven navigation architecture unchanged |

Validation:

- `python -m compileall -q app core providers tests` passes.
- `python tests/smoke_test.py` passes.

## V7.8.6 Creator Wizard Guided Setup

| Flow | Status | Notes |
|---|---|---|
| 5-step guided setup | PASS | Topic, mood, music direction, artist preset, target platform |
| Offline creative direction | PASS | Generates project concept, hook direction, lyric direction, style, arc, visual mood, template, render/subtitle profile, marketing angle |
| Save direction | PASS | Writes `project_data/projects/<project>/creative_direction.json` |
| Song Studio handoff | PASS | Sets session/project context and navigates to Song Studio via existing navigation |
| Song Studio card | PASS | Shows Creative Direction Loaded and Clear Creative Direction |
| Hook/lyrics context | PASS | Creative Direction is included in hook and lyric generation prompts |
| Template loader | PASS | Preserved under `Advanced: Apply Project Template` |

Validation:

- `python -m compileall -q app core providers tests` passes.
- `python tests/smoke_test.py` passes.
- App opens on `http://localhost:8502/`.
