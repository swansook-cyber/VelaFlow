# VelaFlow V7.5 Production Review & Final Quality Gate

V7.5 adds a final offline project audit before final render/export. The goal is
to make VelaFlow behave more like a producer/director review system, not only a
content generator.

## Module

`core/production_audit.py`

## Audit Areas

- Narrative consistency check
- Character consistency check
- Subtitle readability check
- Hook clip readiness
- Render readiness
- Missing asset check
- TikTok package readiness
- YouTube package readiness
- Final package checklist

## Output

`run_full_project_audit(project)` returns:

- total score `0-100`
- producer verdict
- ready for final render flag
- all quality gate checks
- prioritized `fix_first` list

`export_project_audit(project)` writes:

- `production_audit_<timestamp>.json`
- `production_audit_<timestamp>.md`

## UI

Audit results are visible in:

- Project Dashboard snapshot
- Creative Intelligence / Production Audit tab
- Quality Checklist page

This layer is offline-first and does not call paid providers.
