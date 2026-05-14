# VelaFlow — Master Context

VelaFlow is an AI Content Automation Pipeline by VelaLab.

The workflow is:

Song -> Storyboard -> Image -> Motion -> Render -> Clips -> Canvas -> Marketing -> Final Package

Core principles:

- Keep the app local-first and offline-safe.
- Never auto upload.
- Keep existing project workflows backward compatible.
- Prefer modular architecture without rewriting working features.
- Keep provider, queue, render, and manual fallback systems stable.
- Prepare for future modular licensing without adding payment/auth/server code now.

VelaFlow remains a single application today. The module and license structure is
an internal architecture foundation for future packaging.

Current hotfix:

- V7.8.1 Artist Presets + English Instrument Tags Hotfix
- V7.8.1b Full UI Recovery restores all main sidebar workflows.
- V7.8.1c UI Polish Pass restores a cleaner grouped sidebar and production workflow feel.
- V7.8.2 adds production hygiene and source packaging prep without packaging the app.
- V7.8.3 restores Song Studio's multi-hook creator workflow, clear Save Lyrics flow, draft history, and Continue to MV Director action.
- V7.8.3a fixes Streamlit navigation state so continue buttons switch sidebar section and page reliably.
- V7.8.3b adds safe project cleanup, Song Library, archive/delete backups, and Song Studio Only mode.
- V7.8.3c polishes delete UX, hook cards, sidebar project info, empty states, and Song Studio Only navigation.
- V7.8.3d fixes Streamlit navigation state by deferring post-widget page changes through pending_navigation.
- Default artist identity is Vela Moon.
- Song Studio should generate Thai lyrics with English-only Music Style Prompt.
- Text inside Suno parentheses must be English-only production/instrument tags.
- Thai lyrics outside parentheses must not be translated.

