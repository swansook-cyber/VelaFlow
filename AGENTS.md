# Agent Guidance

## Before Major Work
- Read `PROJECT_CONTEXT.md`.
- Check the current git status.
- Understand the existing workflow before editing.
- Preserve existing Song Studio, Creative Pack, Affiliate Studio, Video Prompt Studio, Agent Studio, Character Studio, and optional Mastering behavior unless the task explicitly changes them.

## Product Priorities
- Prioritize output quality, clarity, and creator usability.
- Output Quality > Feature Count.
- Reduce clicks whenever possible.
- Prefer workflow simplification over feature expansion.
- Avoid feature bloat.
- Protect creator usability.
- Keep VelaFlow V1 focused on Generate / Organize / Export.
- Avoid workflow bloat, extra dashboards, unnecessary menus, and duplicate buttons.
- Do not add rendering, video encoding, lip sync, upload automation, browser automation, or heavy scraping unless explicitly requested.

## Implementation Rules
- Prefer existing patterns and helper modules.
- Add new modules only when they clearly isolate stable product logic.
- Keep normal mode clean; put technical details behind developer/advanced areas.
- Do not silently fake success.
- Do not overwrite user project data unless the requested workflow requires it.

## Validation
- Run compile checks after code changes.
- Run smoke tests after functional changes.
- Fix failures caused by the current task.
- If a dependency-specific runtime is needed, use the project `.venv` when available.

## Project Memory
- Update `PROJECT_CONTEXT.md` when product architecture, major workflows, or module ownership changes.
- Keep these context files concise and practical.

## Git Workflow
- After successful validation:
  - `git add .`
  - `git commit -m "<short production message>"`
  - `git push origin main`
- If push fails, retry once and report the clean error summary.
