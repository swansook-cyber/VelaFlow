# Project Management

VelaFlow V7.8.3b adds local project cleanup tools for users who create many
Song Studio drafts.

## Project Library

Active projects live under:

```text
project_data/music/<project_name>/
project_data/seller/<project_name>/
project_data/podcast/<project_name>/
project_data/clips/<project_name>/
project_data/mv/<project_name>/
```

Legacy projects under `project_data/projects/<project_name>/` are still
loaded through fallback handling.

The sidebar Current Project panel lists only active projects. Archived projects
are excluded from the dropdown, and the list is sorted by last modified time.

## Song Library

The Song Library page focuses on song-only projects and drafts. It shows:

- project name
- song title
- artist preset
- selected hook
- last modified time
- lyrics/storyboard/render readiness

Actions include opening the project in Song Studio, continuing to MV Director,
archiving, deleting with confirmation, exporting lyrics, and viewing drafts.

## Archive vs Delete

Archive is preferred. It moves an active project from:

```text
project_data/<workflow>/<project_name>/
```

to:

```text
project_data/archive/<workflow>/<project_name>_<timestamp>/
```

Delete requires explicit confirmation and only deletes inside
`project_data/<workflow>/<project_name>/` or legacy `project_data/projects/`.
Before deletion, VelaFlow creates a backup copy under:

```text
project_data/deleted_backups/<workflow>/<project_name>_<timestamp>/
```

Delete never targets application folders such as `app/`, `core/`, `providers/`,
`config/`, `docs/`, `tests/`, or `backups/`.

## Song Studio Only Mode

Workflow mode is saved in:

```text
config/user_preferences.json
```

Modes:

- Full Pipeline
- Song Studio Only

Song Studio Only keeps Dashboard, Song Studio, Song Library, and AI Settings
visible while hiding the heavier image/video/render/marketing workflow menus.
