# VelaFlow V7.2 Creative Intelligence

V7.2 adds an offline-first creative analysis layer. It does not add cloud,
payment, online collaboration, marketplace networking, auto-upload, or heavy AI
video generation.

## Modules

| Module | File | Purpose |
|---|---|---|
| Emotional Arc Analyzer | `core/emotional_arc.py` | estimates intro mood, emotional rise, climax, ending tone, pacing, transitions, color, and motion |
| Hook Intelligence | `core/hook_intelligence.py` | scores lyric/subtitle lines for hook potential and shorts readiness |
| Visual Continuity Analyzer | `core/visual_continuity.py` | checks color, motion, and subtitle style consistency |
| Cinematic Advisor | `core/cinematic_advisor.py` | suggests close-up, handheld, bridge restraint, and final chorus motion boosts |
| Adaptive Profiles | `core/adaptive_profiles.py` | recommends render profile from song/storyboard signals |
| Creative Timeline | `core/creative_timeline.py` | builds a visual timeline table with scenes, lyrics, energy, motion, subtitles, transitions, and color |
| Asset Graph | `core/asset_graph.py` | maps prompts, assets, scenes, and motion relationships |

## UI

The `Creative Intelligence` page provides:

- Emotional Arc
- Hook Intelligence
- Visual Continuity
- Auto Cinematic Suggestions
- Creative Timeline View
- Asset Relationship Graph

The page includes safe apply actions for cinematic suggestions and adaptive
render profile. The app creates a backup before changing project state.

## Offline Rules

All V7.2 analysis uses local heuristic logic. It is designed to make better
creative decisions from existing project metadata before spending money on
provider calls or video generation.
