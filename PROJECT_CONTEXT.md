# VelaFlow Project Context

## Vision
VelaFlow is a local-first creator workspace that turns raw creative ideas into release-ready packages for music, short-form video prompts, affiliate content, podcast ideas, and reusable AI character prompts. The core product should help non-technical creators move from idea to usable assets quickly without requiring render pipelines, cloud automation, or complex production tools.

## VelaLab Ecosystem
VelaFlow is part of the larger VelaLab creative ecosystem.

```text
VelaLab
├── Vela Moon
├── VelaFlow
└── Vela After Work
```

Tagline: Music. Software. Stories.

- **Vela Moon:** Music identity, emotional pop rock direction, artist presets, and release-ready song concepts.
- **VelaFlow:** Creative software for generating lyrics, prompts, packages, character prompts, affiliate scripts, and creator exports.
- **Vela After Work:** Storytelling, podcast, office-life concepts, and after-work creative media.

## Product Philosophy
- Generate, organize, polish, and export creator assets.
- Output Quality > Feature Count.
- Reduce clicks whenever possible.
- Prefer workflow simplification over feature expansion.
- Keep normal workflows understandable in one screen.
- Keep the normal user flow simple and creator-friendly.
- Treat rendering, cloud video generation, and automation bots as outside the V1 product boundary unless explicitly reintroduced with a stable reason.
- Preserve working flows before adding new ones.

## Ecosystem Structure
- **AI Creative Pack Generator:** Main V1 workflow for song ideas, titles, hooks, lyrics, producer prompts, captions, hashtags, cover prompts, storyboard prompts, and release packs.
- **Song Studio:** Deeper lyric, hook, Suno/Udio export, and release package workflow.
- **Video Prompt Studio / MV Director:** Prompt and storyboard planning for Whisk, Flow, Veo, Runway, Kling, Pika, Luma, and similar external tools.
- **Character Studio:** Reusable character identity prompts for image, image-to-video, lip sync, and TikTok/Reels workflows.
- **Affiliate Studio:** Lightweight product analysis, hook/script generation, trend ideas, and affiliate creator package export.
- **Agent Studio:** Assistant-style creative package generation with optional memory, tools, provider fallback, and multi-agent orchestration.
- **Optional Creator Mastering:** Local ffmpeg-based audio polish for AI-generated songs, kept out of the simple normal flow unless needed.

## UX Principles
- Default experience should be understandable in one screen.
- Normal mode should avoid developer wording, raw manifests, pipeline details, and debug panels.
- Use clear primary actions such as `Generate Full Release Pack`, `Generate Character Pack`, and `Download TXT/ZIP`.
- Keep copy-ready blocks visible for creators who use external tools.
- Mobile layouts should avoid horizontal overflow, giant prompt walls, and unnecessary scrolling.

## Workflow Philosophy
- Reduce clicks whenever possible.
- Prefer workflow simplification over feature expansion.
- Output Quality > Feature Count.
- Creator-first UX.
- Keep normal workflows understandable in one screen.

## Current Priorities
- Improve commercial quality of titles, hooks, lyrics, and producer-grade Suno/Udio prompts.
- Keep VelaFlow V1 focused as a Creative Pack Generator.
- Polish export TXT/ZIP structure and filenames.
- Stabilize creator tools without adding rendering complexity.

## Stable Modules
- Creative release pack generation.
- Song title, hook, lyric, and music style prompt generation.
- Suno/Udio TXT export and release package export.
- Video Prompt Studio.
- Character Studio.
- Affiliate Studio core package workflow.
- Optional local remaster/mastering exports.

## Beta Modules
- Agent Studio provider/agent/workspace layers.
- Affiliate Trend Finder.
- Project workspace and asset pipeline.
- Advanced legacy production/render sections visible only in advanced/developer contexts.

## Future Roadmap
- Better quality scoring for commercial Thai lyrics and hooks.
- Cleaner project organization and recent/favorite project UX.
- More creator-ready preset packs.
- Stronger package templates for Flow, Veo, Kling, Runway, Pika, CapCut, Suno, and Udio.
- Optional integrations only when they are reliable and do not complicate V1.

## Closed Beta Strategy
- Build for personal real-world use first.
- Stabilize through personal usage.
- Expand to 5-10 founding beta users.
- Collect real feedback.
- Improve based on real usage.
- Monetize only after proven value.

## Long-Term Product Direction
VelaFlow should evolve into a creator operating system for AI-native content creation while remaining simple, creator-friendly, and output-focused.

## Development Workflow
- Read this file before major architecture or workflow changes.
- Make focused changes.
- Run compile checks and smoke tests before commit.
- Commit with short production-style messages.
- Push to `origin main` after successful validation.
