# Creator Wizard

VelaFlow V7.8.6 upgrades Creator Wizard into a guided creative setup for users
who do not have a clear song idea yet.

Creator Wizard is for starting direction. Song Studio is still the place where
hooks, lyrics, Suno formatting, and English-only instrument tag normalization
happen.

## Guided Steps

1. Song Topic
2. Mood
3. Music Direction
4. Artist Preset
5. Target Platform

The wizard uses local/offline rules first. It does not require a paid API and
does not add cloud, payment, online license, marketplace, or video AI behavior.

## Output

The wizard creates a structured `creative_direction` object with:

- `project_concept`
- `hook_direction`
- `lyric_direction`
- `music_style_direction`
- `emotional_arc`
- `visual_mood`
- `suggested_template`
- `suggested_render_profile`
- `suggested_subtitle_style`
- `suggested_marketing_angle`

When applied, it writes:

```text
project_data/projects/<project>/creative_direction.json
```

## Song Studio Integration

Song Studio shows a small "Creative Direction Loaded" card when direction data
exists. Hook generation and full lyric generation include the creative direction
as extra context while keeping:

- Thai lyrics
- English-only music style prompt
- English-only production tags inside parentheses
- selected Artist Preset behavior

The direction can be cleared from Song Studio without deleting the project.

## Template Loader

The old template loader is preserved under:

```text
Advanced: Apply Project Template
```
