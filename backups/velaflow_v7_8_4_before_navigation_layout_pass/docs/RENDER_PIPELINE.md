# Render Pipeline

The VelaFlow render module turns approved storyboard assets into final video
outputs.

## Responsibilities

- Build timeline data
- Select approved video/image/placeholder sources
- Render scene clips with FFmpeg
- Reuse scene cache when possible
- Concatenate scene clips
- Add subtitles and optional audio
- Export 16:9, 9:16, and 1:1 outputs
- Write manifests, logs, assets-used files, and final package inputs

Render access is represented by the `render_enabled` feature flag.
