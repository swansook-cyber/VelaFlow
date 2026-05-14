# Prompt Rules

## V7.8.1 Song Studio Language Rule

- Lyrics must be Thai.
- Music Style Prompt must be English only.
- Instrument tags, arrangement notes, production notes, vocal notes, mood notes,
  and all text inside parentheses must be English only.
- Do not write Thai inside parentheses.
- Do not translate Thai lyrics into English.
- Keep Thai lyrics natural and conversational.
- Use the selected Artist Preset as the main style identity.

## Vela Moon Style Rule

- Use mid-tempo easy-listening Thai pop rock.
- Use smooth emotional male vocal.
- Use clean electric guitar and acoustic strumming.
- Use warm bass and soft drum kit.
- Add light rhodes piano or soft pad when needed.
- Keep the melody catchy, relaxed, and emotional.
- Build a full song structure, not a short demo.
- Make the hook memorable and caption-friendly.

## V7.8.3 Song Studio Output Rule

Song Studio prompt output should follow this order:

1. Song Title
2. Target Audience + Hook Strategy
3. Candidate Hooks, 3-5 options
4. Instrument Selection
5. Music Style Prompt, English only
6. Advanced Settings for Suno
7. Complete Lyrics with Tags
8. TikTok Clip Cut Recommendation

Each hook candidate should include hook text, emotional score, catchy score,
TikTok potential, Thai reason, and suggested usage. The selected hook should be
used as the main chorus or strongest memorable line when generating full lyrics.

## Validation

File: `core/instrument_tag_normalizer.py`

Use:

- `normalize_lyrics_tags(full_lyrics, artist_preset)`
- `validate_english_only_tags(full_lyrics)`

The normalizer only changes text inside parentheses. Thai lyrics outside
parentheses must remain Thai.

## V7.8.4 Preset Editing Rule

Artist Preset Manager validates custom presets before saving:

- `artist_id`, `artist_name`, `default_music_style_prompt`, and `vocal_style`
  are required.
- Instrument lists and section-level arrangement tags must be English only.
- Suno `weirdness` and `style_influence` must stay between 0 and 100.
- Vela Moon is locked. Duplicate it before editing.

Song Studio loads the configured default artist preset automatically, then saves
the selected artist preset into `song.json` when lyrics are generated or saved.

## V7.8.6a Song Structure Rule

When a Song Structure Plan is enabled, hook and full lyric prompts should include:

- selected structure preset
- recommended hook placement
- section order
- purpose of each section
- energy curve 0-100
- emotional arc
- English-only suggested instrument tags
- notes for lyrics generation

The structure plan guides the whole song flow before lyrics are generated. It
does not generate chords, MIDI, or DAW data.
