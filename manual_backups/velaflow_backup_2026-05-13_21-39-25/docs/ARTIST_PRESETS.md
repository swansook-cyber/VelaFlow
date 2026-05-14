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
- `load_default_artist_id()`
- `set_default_artist_preset(artist_id)`
- `duplicate_artist_preset(source_artist_id, new_artist_id, new_artist_name)`
- `delete_artist_preset(artist_id)`
- `export_artist_preset(artist_id)`
- `import_artist_preset(preset, overwrite=False, save_as_copy=False)`

If a preset is missing or corrupted, VelaFlow falls back to Vela Moon.

## V7.8.4 Artist Preset Manager

V7.8.4 adds a local Artist Preset Manager page. It can create, edit, duplicate,
import, export, set default, and delete custom artist presets without adding
cloud sync or marketplace behavior.

Default artist selection is stored in:

```text
config/artist_presets/default_artist.json
```

Vela Moon is a locked system preset:

- it can be viewed, used, exported, and duplicated
- it cannot be deleted
- it cannot be overwritten directly
- customize it by duplicating it first

Custom presets must keep instrument fields and `section_instrument_tags` in
English only. Thai lyrics remain Thai in Song Studio output; only production
tags inside parentheses are normalized.

## Import / Export

Use Artist Preset Manager -> Import / Export to download or upload a preset
JSON file. If an imported preset ID already exists, VelaFlow can save it as a
new copy or overwrite an unlocked custom preset. Locked Vela Moon is never
overwritten by import.

## Song Studio Workflow

V7.8.3 uses the selected artist preset during the two-step Song Studio flow:

1. Generate hook candidates from the song idea and preset identity.
2. Select a hook manually or let VelaFlow choose the highest total score.
3. Generate full Thai lyrics using the selected hook.
4. Normalize all instrument and production tags inside parentheses to English.
5. Save `song.json`, `lyrics.txt`, and optional `song_drafts/` entries.

The Vela Moon preset supplies the default music style prompt, Suno settings,
and section-level English arrangement tags.

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
