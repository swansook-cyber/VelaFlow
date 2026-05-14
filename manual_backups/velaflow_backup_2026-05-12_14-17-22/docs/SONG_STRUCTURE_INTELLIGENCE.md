# Song Structure Intelligence

VelaFlow V7.8.6a adds a lightweight Song Structure Intelligence layer.

This is not a DAW, MIDI engine, chord engine, or music theory workstation. It is
a producer-style planning step that helps VelaFlow understand the whole song
flow before lyrics are generated.

## Workflow

The flow is:

1. Brief / Creative Direction
2. Song Structure Preset
3. Section Purpose
4. Energy Curve
5. Emotional Arc
6. Hook Placement
7. Lyrics Generation

## Presets

Preset file:

```text
config/presets/song_structure_presets.json
```

Included presets:

- Vela Moon Pop Rock
- Standard Pop
- TikTok Hook First
- Emotional Ballad
- Cinematic Story
- Viral Short Form

Each section tracks:

- section name
- energy 0-100
- purpose
- emotional role
- hook role
- lyric density
- arrangement density
- suggested English instrument tag

## Project Output

When saved, the plan is stored at:

```text
project_data/projects/<project>/song_structure_plan.json
```

Song Studio exports also include:

```text
project_data/projects/<project>/exports/song_structure_plan.json
project_data/projects/<project>/exports/song_structure_plan.md
```

## Song Studio

Song Studio can generate or refresh a structure plan, preview the energy curve,
and include the plan in hook and full lyric prompts.

Language rules remain unchanged:

- Thai lyrics remain Thai.
- Music style prompt stays English only.
- Production and instrument tags inside parentheses stay English only.

## Future Use

The structure plan can later feed MV Director, subtitle timing, render pacing,
clip selection, and marketing angle decisions without requiring online services.
