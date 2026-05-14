# Versioning

VelaFlow keeps project data backward compatible where possible.

## Product Version

The app title currently uses the `V7.8` product line while the product name has
changed to VelaFlow.

## Stable Candidate Freeze

V7.8 freezes `VelaFlow V7.7 Stable Candidate 1` as a rollback point before V8
or packaging work. Snapshot evidence is exported under
`outputs/stable_candidates/<project_name>/`.

## V7.8.1 Hotfix

V7.8.1 is **Artist Presets + English Instrument Tags Hotfix**. It adds the
Vela Moon artist preset and normalizes Suno instrument/production tags inside
parentheses to English while preserving Thai lyrics.

## V7.8.1b Hotfix

V7.8.1b is **Full UI Recovery**. It restores the full sidebar workflow after
the V7.8.1 Song Studio hotfix while preserving Artist Presets and English-only
instrument tag normalization.

## Project Compatibility

Older projects created under Vela AI Studio naming can still be loaded. New
project metadata should use VelaFlow naming.

## Future Versioning Goals

- Storyboard snapshots
- Render manifests
- Clip metadata history
- Final package manifests
- Project migration notes for major schema changes
