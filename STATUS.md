# VelaFlow development status

- Development branch: `feature/full-song-mv-planning-20261126`; draft PR #4. This work is not merged or deployed.
- Full-song MV: approved scene planning, revision-bound asset QC, and opt-in local FFmpeg rendering are implemented on this branch. New plans default to 16:9; 9:16 remains selectable.
- Render preflight requires every scene and selected asset to be approved, current, readable, and compatible with the target aspect. The existing render engine assembles shots without changing storyboard timing and FFprobe checks the final H.264/AAC MP4.
- Validation: 23 focused planning, production, render, export, and Song Studio tests and PR CI passed for `bdd09ad`, including a low-resolution synthetic 180-second MP4. The broad smoke test was interrupted after it stalled.
- First real MV audit (2026-11-26): Vela Moon project "รอยยิ้มเธอ" has a readable 209.84-second MP3, but no saved full-song scene manifest or accepted visual assets. An in-memory 35-scene storyboard covers the audio; all 35 scene asset assignments and human approvals are pending. No real render or 1080p test was started. Preserve the original project and audio; import/reuse 16:9 visuals and complete per-scene approval and QC first.
