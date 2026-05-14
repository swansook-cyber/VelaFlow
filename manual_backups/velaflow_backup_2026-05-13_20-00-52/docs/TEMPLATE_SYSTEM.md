# VelaFlow Template System

VelaFlow V7.0 adds a creator-facing template layer so a new project can start
with consistent render, motion, subtitle, color, prompt, and scene defaults.
This is a local configuration system only. It does not add cloud sync,
marketplace downloads, payment, or subscription logic.

## Files

- `config/presets/project_templates.json`: project templates such as Emotional
  Pop Rock, Sad Cinematic, TikTok Viral, Night Drive, Isaan Indie, and Acoustic
  Heartbreak.
- `config/presets/preset_packs.json`: reusable workflow packs such as TikTok
  Fast Pack and Cinematic Pack.
- `config/presets/scene_presets.json`: visual scene vocabulary for storyboard
  consistency.
- `config/presets/global_presets.json`: shared motion, subtitle, render, and
  prompt preset names.

## Core Modules

- `core/preset_system.py` loads preset JSON files with safe fallbacks.
- `core/project_templates.py` creates or updates a project from a template and
  writes the visual identity block used by later workflow steps.
- `core/style_consistency.py` checks whether the project has enough visual
  identity metadata and highlights scenes that may need prompt review.

## Creator Wizard

The `Creator Wizard` page is the workflow entry point.

In V7.8.6, the default view is a guided creative setup:

1. Song Topic
2. Mood
3. Music Direction
4. Artist Preset
5. Target Platform

It generates a local/offline Creative Direction and saves it as
`project_data/projects/<project>/creative_direction.json`, then passes it to
Song Studio. The wizard does not replace Song Studio; it prepares direction for
hook and lyric writing.

The original V7.0 template workflow is preserved under
`Advanced: Apply Project Template`:

1. Choose Template
2. Song Style
3. Generate Lyrics
4. Generate Storyboard
5. Character Setup
6. Image Review
7. Render Draft
8. Clip Factory
9. Final Package

The wizard can create a new project from a template or apply a template to the
current project after creating a backup.

## Design Rules

- Templates preload workflow defaults but do not overwrite provider secrets.
- Presets are local JSON and should stay human-readable.
- Scene presets are a consistency vocabulary, not a rigid storyboard generator.
- Marketplace, online subscription, cloud sync, and collaborative editing are
  intentionally out of scope for V7.0.
