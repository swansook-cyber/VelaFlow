# Brand Migration

## Old Name

- Vela AI Studio
- Vela Moon AI Studio
- Legacy local workspace names from earlier VelaFlow/Vela AI Studio builds

## New Name

- Program Name: VelaFlow
- Folder Slug: `velaflow`
- Product Tagline: AI Content Automation Pipeline
- Company/Brand: VelaLab

## Backward Compatibility

Existing local folders and project files can still load. The code keeps legacy
name replacement constants in `core/branding.py` so old metadata can be
normalized without breaking saved projects.

Public-beta project storage now prefers workflow-specific folders:

- `project_data/music/`
- `project_data/seller/`
- `project_data/podcast/`
- `project_data/clips/`
- `project_data/mv/`

Legacy `project_data/projects/` folders are scanned as fallback.

## Launcher Changes

- New launcher: `run_velaflow.bat`
- Legacy launcher: `run_vela.bat`

`run_vela.bat` remains as a wrapper for users who already have shortcuts.

## Future Rename Plan

1. Keep current working folder stable during active beta work.
2. Use `velaflow` in docs, generated package names, and new install paths.
3. Prefer workflow-specific project folders for new projects.
4. Keep old project JSON and output folders readable after migration.

## Not Done Yet

- No destructive folder rename has been performed.
- No cloud account, payment, or online license migration exists yet.
