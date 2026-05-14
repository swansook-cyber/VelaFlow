# VelaFlow V7.3 Cinematic Director System

V7.3 adds an offline-first cinematic director layer. It focuses on film
language, story rhythm, shot choices, style consistency, and reusable director
notes. It does not add full AI actors, lip sync, realtime collaboration, cloud
rendering, online marketplace, or payment.

## Modules

| Module | File | Purpose |
|---|---|---|
| Shot Type Intelligence | `core/shot_intelligence.py` | recommends close-up, medium, wide, over-shoulder, silhouette, and handheld shots |
| Camera Language Engine | `core/camera_language.py` | maps scene emotion to slow push in, emotional drift, static tension, whip transition, floating motion, and handheld intimacy |
| Scene Rhythm Analyzer | `core/scene_rhythm.py` | checks cut density, pacing balance, chorus intensity, and emotional breathing room |
| Visual Story Consistency | `core/visual_story_consistency.py` | checks character, color, emotional, and lighting continuity |
| Director Notes | `core/director_notes.py` | creates notes and injects them into prompt, motion, subtitle, and render metadata |
| Cinematic Style Packs | `core/cinematic_style_packs.py` | applies local inspired style packs from `config/presets/cinematic_style_packs.json` |
| Smart Scene Ordering | `core/smart_scene_ordering.py` | detects abrupt emotion flow and proposes a smoother order |

## Style Packs

Included local style packs:

- Neon Night Drive
- Sad Rain Film
- Indie Handheld
- Dreamy Soft Focus
- Silhouette Stage

These are broad inspired style directions, not exact recreations of a protected
artist or filmmaker.

## UI

The `Creative Intelligence` page now includes:

- Director System tab
- Style Packs tab
- Scene Ordering tab

All apply actions create a project backup before changing scene metadata.
