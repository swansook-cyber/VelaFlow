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

## Validation

File: `core/instrument_tag_normalizer.py`

Use:

- `normalize_lyrics_tags(full_lyrics, artist_preset)`
- `validate_english_only_tags(full_lyrics)`

The normalizer only changes text inside parentheses. Thai lyrics outside
parentheses must remain Thai.
