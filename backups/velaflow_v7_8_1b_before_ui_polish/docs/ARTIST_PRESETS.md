# Artist Presets

VelaFlow V7.8.1 adds an offline artist identity layer for Song Studio.

## Default Preset

The default preset is **Vela Moon**:

- emotional easy-listening Thai pop rock
- Thai lyrics
- English-only music style prompt
- English-only instrument and production tags inside parentheses
- clean electric guitar, acoustic strumming, warm bass, soft drum kit
- smooth emotional male vocal

Preset file:

```text
config/artist_presets/vela_moon.json
```

## Module

File: `core/artist_presets.py`

Functions:

- `load_artist_presets()`
- `get_artist_preset(artist_id)`
- `list_artist_presets()`
- `save_artist_preset(preset)`
- `validate_artist_preset(preset)`

If a preset is missing or corrupted, VelaFlow falls back to Vela Moon.

## Add A New Preset

Create a JSON file under:

```text
config/artist_presets/<artist_id>.json
```

Required fields:

- `artist_id`
- `artist_name`
- `default_music_style_prompt`
- `section_instrument_tags`

Keep `music_prompt_language` and `instrument_tags_language` as `English only`
when the target output is for Suno-style production tags.
