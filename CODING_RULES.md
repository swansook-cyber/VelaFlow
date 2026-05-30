# VelaFlow Coding Rules

## Validation Workflow
- Run compile checks after code changes:
  - `python -m compileall -q app core providers tests`
- Run smoke tests after functional changes:
  - `python tests/smoke_test.py`
- Use the project `.venv` if the system Python lacks project dependencies.
- Run package/build scripts when the task asks for them.

## Testing Requirements
- Add or update smoke tests for new modules, exports, and core workflows.
- Test that new output includes required sections.
- Test that existing stable workflows still import and run.
- Avoid tests that require paid APIs, browser automation, cloud rendering, or real external services unless explicitly requested.

## Git Workflow
- Check `git status --short` before and after work.
- Do not revert unrelated user changes.
- After successful validation:
  - `git add .`
  - `git commit -m "<short production message>"`
  - `git push origin main`
- Keep the working tree clean after completed tasks.

## UI/UX Rules
- Normal mode should be simple, creator-first, and mobile-friendly.
- Hide debug, manifests, raw JSON, provider internals, and developer wording from normal users.
- Do not add unnecessary menus or duplicate actions.
- Prefer one clear primary action per workflow.
- Keep copy-ready text blocks and download buttons easy to find.

## Refactoring Rules
- Keep edits scoped to the requested workflow.
- Preserve backward compatibility where possible.
- Prefer small helper modules over large rewrites.
- Do not introduce heavy dependencies without explicit approval.
- Do not add render, video encoding, lip sync, upload automation, or scraping-heavy systems unless explicitly requested.

## Output Quality Rules
- Lyrics must be lyrics, not prompt instructions.
- Music direction belongs in style prompts or arrangement sections, not Lyrics Only.
- Titles should be commercial, memorable, and not generic placeholders.
- Hooks should be singable, emotionally strong, and copy-ready.
- Prompt packs should separate identity, scene/action, negative prompt, and consistency rules.
- Release packs should be clean enough to paste into Suno/Udio or external creative tools immediately.
