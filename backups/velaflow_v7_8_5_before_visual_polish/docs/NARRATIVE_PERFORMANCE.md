# VelaFlow V7.4 Narrative & Performance Intelligence

V7.4 adds an offline-first story and performance layer. It helps VelaFlow
understand narrative roles, performance emotion, visual metaphors, emotional
beats, subtitle emotion, and render profiles without adding full AI actors,
lip sync, generated video scenes, cloud collaboration, or realtime multi-user
features.

## Modules

| Module | File | Purpose |
|---|---|---|
| Narrative Arc Engine | `core/narrative_arc.py` | analyzes beginning, tension, emotional peak, release, ending, and scene roles |
| Performance Emotion Mapping | `core/performance_emotion.py` | maps restrained sadness, emotional explosion, silent regret, and hopeful ending |
| Visual Metaphor Suggestions | `core/visual_metaphor.py` | suggests rain, neon, empty roads, mirrors, shadows, and light metaphors |
| Cinematic Beat Sync | `core/cinematic_beat_sync.py` | maps emotional beat, lyric beat, visual beat, and sync actions |
| Dynamic Subtitle Emotion | `core/subtitle_emotion.py` | recommends hook glow, large chorus, whisper, soft warm, and restrained subtitles |
| Emotional Render Profiles | `core/emotional_render_profiles.py` | maps heartbreak, nostalgic, uplifting, lonely night, and emotional explosion profiles |

## UI

The `Creative Intelligence` page includes:

- Narrative Arc
- Performance
- Metaphors
- Beat Sync
- Subtitle Emotion
- Emotional Profiles

The main `Apply Narrative Intelligence` action injects performance emotion,
visual metaphors, cinematic beats, subtitle emotion, and an emotional render
profile after creating a backup.

## Offline Rule

All analysis is local heuristic metadata. It improves prompts, motion notes,
subtitle behavior, and render choices before any expensive provider or video
generation step.
