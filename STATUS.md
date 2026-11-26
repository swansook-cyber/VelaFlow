# VelaFlow development status

- Development branch: `feature/full-song-mv-planning-20261126`; draft PR #4. This work is not merged or deployed.
- Full-song MV: approved scene planning, revision-bound asset QC, and opt-in local FFmpeg rendering are implemented on this branch. New plans default to 16:9; 9:16 remains selectable.
- Render preflight requires every scene and selected asset to be approved, current, readable, and compatible with the target aspect. The existing render engine assembles shots without changing storyboard timing and FFprobe checks the final H.264/AAC MP4.
- Validation: 23 focused planning, production, render, export, and Song Studio tests passed locally, including a low-resolution synthetic 180-second MP4. Full 1080p rendering with the real Vela Moon song and live provider availability remain unverified. The broad smoke test was interrupted after it stalled; draft PR CI is pending for this commit.
