# VelaFlow Closed Beta Notes

VelaFlow Closed Beta is a local-first AI Content Automation Pipeline for
creator workflows.

## Current Beta Features

- Music workflow: Creator Wizard, Song Studio, hook candidates, lyrics, Suno TXT export, artist presets
- Seller Studio: product/campaign content, hooks, scripts, CTA, captions, hashtags, prompts
- Podcast Studio: episode hooks, intro, main script, monologue, rant version, Shorts ideas
- Viral Clips Studio: short-form hooks, script, subtitles, captions, hashtags, prompts
- Visual Workflow Engine: camera, lighting, motion, and visual mood presets
- Rendering Connector: render packages, render queue, mock render job lifecycle
- Provider foundation: Gemini, OpenAI GPT, xAI Grok, plus offline fallback behavior
- Project folders: workflow-specific `project_data/music`, `seller`, `podcast`, `clips`, and `mv`

## Known Limitations

- No real video rendering yet.
- Render jobs are mock/local only. They create a fake job id and placeholder result.
- Google Veo, Kling, Runway, and similar provider modes are readiness labels only.
- External AI APIs depend on configured keys in `.env`.
- Missing API keys should show warnings and fall back safely where supported.
- Outputs should be reviewed by the user before publishing.
- No auto upload, scraping, payment, cloud sync, online licensing, or browser automation is included.

## Beta Guidance

- Use port `8502` for local testing.
- Keep `.env` private.
- Do not include `project_data/` in shared packages unless intentionally sharing sample projects.
- Test each workflow with short real-world prompts before sharing the build.
