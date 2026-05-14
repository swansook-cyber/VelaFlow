# Project Management

VelaFlow V7.8.3b adds local project cleanup tools for users who create many
Song Studio drafts.

## Project Library

Active projects live under:

```text
project_data/projects/<project_name>/
```

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
project_data/projects/<project_name>/
```

to:

```text
project_data/archive/<project_name>_<timestamp>/
```

Delete requires explicit confirmation and only deletes inside
`project_data/projects/<project_name>/`. Before deletion, VelaFlow creates a
backup copy under:

```text
project_data/deleted_backups/<project_name>_<timestamp>/
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
