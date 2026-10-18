# Mix Stems QA follow-up

Baseline: b67a9ae80163fe0b06d1bbace1719cfa58b395c6 on
feature/song-studio-myvintagemix-analysis; remote HEAD matched after fetch.
Review addressed: https://github.com/swansook-cyber/VelaFlow/pull/3#issuecomment-6246883097.
Date: 2026-10-18, Asia/Bangkok. PR stays Draft; no main merge/deployment.

This document supersedes the initial analysis report's pending upload/download,
focused full-app regression and retention gates. Reference-site unknowns remain unknown.

## Storage and memory changes

* The actual Audio Editor now delegates its optional mixer view to app/stem_mix_ui.py.
  Original Cut/Join dispatch and the existing mastering pipeline remain unchanged.
* core/stem_uploads.py copies upload buffers directly into a newly created private
  TemporaryDirectory for each request. It removes that directory, including both
  generated source copies and render output, when the request succeeds, rejects, times
  out or raises an ordinary I/O error. There is no new persistent stem export tree.
* The low-level mix_stems API still returns a generated artifact to its caller on
  success; callers own its lifecycle. On failure it removes only the output filename
  and empty UUID directory created by that invocation. The browser workflow wraps all
  calls in a request-owned temporary context. No old exports or user directories are
  scanned, migrated or deleted, including files retained by the previous implementation.
* Limits: 64 MiB per stem, 300 seconds, up to 8 input channels/192 kHz, 96 MiB encoded
  output, two active renders per process. FFmpeg has explicit time/output-size bounds,
  constrained local input protocols, and decoding of the declared WAV/MP3 format.
  A disk-free preflight budgets actual uploads, maximum output and 64 MiB headroom.
* Uploaded filenames cannot choose disk paths: generated stem_0/stem_1 names are used.
  FFprobe validates durations before mixing and codec/24-bit/48k/stereo/duration after.
  No permissive FFmpeg fallback is accepted when FFprobe is unavailable.
* Existing measure_remaster_artifact validates decoded output rail hits, integrated
  LUFS and true peak. Non-silent results require finite LUFS and <= -1 dBTP. Silence
  remains explicitly labeled with undefined loudness; it is not reported as 0 LUFS.
* Completed WAV bytes are bounded and read once, not read from disk on every slider
  rerun. A process-local DownloadStore retains at most 192 MiB/four results, replaces
  the same owner's previous result and rejects new capacity requests rather than
  evicting another user's current result. Session state keeps metadata and a random
  token, not WAV bytes or a temporary path. Tokens require the original random session
  owner to retrieve data through this store. Expiry is 10 minutes; expired entries are
  purged on access and the active download fragment refreshes every 60 seconds.
* Input/gain/project changes invalidate the old download; a Clear temporary mix action
  releases the owner's result. Immutable Streamlit upload IDs replace repeated large
  buffer hashes. Uploader/gain widgets remain scoped to the project within the session.

## Actual automated validation

Local Windows Python 3.12 / Edge headless, real FFmpeg and FFprobe:

| Gate | Actual result |
|---|---|
| unittest discovery | 19 tests passed, no skips |
| Existing Song Studio/Suno tests | Passed as part of discovery |
| Actual app boot/navigation | Home, Audio Editor Cut/Join/Mix, Remaster Studio, Song Studio passed |
| Existing audio operations | Real Cut 2 s, Join 7 s and validated Remaster WAV/MP3 passed; source hashes unchanged |
| Full-app browser E2E | Actual app in disposable source/config copy, real file input uploads and HTTP browser download passed |
| Browser scenarios | Unequal lengths, silence, repeated download, clear/regenerate, corrupt input/stale-result invalidation, two separate browser contexts and real >64 MiB upload rejection passed |
| Output bytes | Downloaded WAVs independently FFprobed: pcm_s24le, 24-bit, 48000 Hz, 2 channels, 3.0 s |
| Non-silent mix | Integrated -25.49 LUFS, true peak -22.37 dBTP, sample peak -22.36785 dBFS, rail_hits=0 |
| Silent WAV | Effectively silent, integrated LUFS/true peak undefined, rail_hits=0 |
| Repeat/regenerated output | Byte-identical with same fixtures/settings |
| Cleanup | Zero request-owned scratch directories after E2E; no exports/stem_mixes directory created |
| Failure/resource tests | Corrupt/oversize/overduration, low disk, upload I/O error, simulated FFmpeg timeout with partial output, third busy render, capacity/TTL/owner isolation and filename traversal passed |
| Memory: Python allocation | 16 MiB synthetic export peaked at 16,802,801 traced bytes (<20 MiB gate) |
| Memory: full app | Sampled server peak RSS 384,712,704 bytes (~367 MiB) with two browser sessions and >64 MiB rejected upload; <1 GiB QA ceiling |
| Responsive browser | 390px mobile and 1440px desktop; mobile horizontal-overflow assertion passed |
| compileall / diff check | Passed |
| Listening QA | NOT PERFORMED; checklist remains Pending |

Early browser test selected a visually hidden radio input; the fixture was corrected to
use the existing visible Home action and mode label. Early remaster assertion used a
wrong result key; it now asserts the actual output_validation report. Final checks above
passed. Tests copy application/config/assets into disposable directories without copying
credentials or user project folders. Real-source hashes and a sentinel old-export file
are checked for preservation. The broad legacy tests/smoke_test.py is not run against
user data; targeted full-app and real audio regressions replace that unsafe invocation.

## CI and reproduction

The Song Studio workflow now runs two jobs: Python/FFmpeg unit + actual-app/audio
regression gates, and a real Chromium upload/download E2E job. Both compile/test
production Python dependencies. The E2E job installs Playwright 1.62.1 into RUNNER_TEMP
as a test-only browser driver; no runtime Python dependency or production Node bundle
was added. JSON results, downloaded synthetic WAVs, server/browser logs and screenshots
are uploaded as a CI artifact, including on failure. Hosted CI status is checked after
the branch push and reported in the PR; local success alone is not a CI success claim.

Commands:

```text
python -m compileall -q core app tests
python -m unittest discover -s tests -p "test_*.py"
python tests/run_mix_e2e.py --output outputs/mix-e2e
```

E2E needs Node with test-only playwright on NODE_PATH and its installed Chromium.
VELA_QA_BROWSER optionally selects an existing Chromium/Edge executable for local QA.
Production app uses neither the driver nor that environment variable.

## Remaining limits and acceptance

* Listening is not automated: sync/drift/phase, limiter artifacts and musical balance
  need legally supplied paired stems and the separate listening checklist before signoff.
* RSS is sampled for the app process and two synthetic browser sessions. It excludes
  browser/FFmpeg child RSS and does not prove an arbitrary-concurrency or maximum-duration
  load bound. The traced allocation test isolates Python copy cost, not total process RSS.
* Streamlit owns its upload buffers and registered download-media copies. Its global
  upload widget still advertises the existing app-wide 200 MB limit; this feature rejects
  >64 MiB after upload and before processing. Our render/store quotas do not replace
  deployment-level connection, upstream request or total-memory limits. Those unrelated
  global settings and Login were not changed. Persistent results expire at the feature
  layer; this is not a revocation guarantee for a browser that already downloaded bytes.
* Quotas/owner tokens are process-local. This does not convert the app's pre-existing
  single-user/global project model into multi-tenant project isolation. Multi-worker
  deployments need an explicit shared resource policy; no production deployment changed.
* Normal completion, ordinary exceptions and controlled FFmpeg timeout are covered. A
  hard OS/process kill can leave an OS temporary directory; old user files are never
  swept automatically. Operational cleanup of crash leftovers requires a separately
  reviewed ownership/lease policy. Disk preflight cannot reserve space against unrelated
  processes; write failures are caught and request cleanup is attempted.
* The mixer protects peaks, but does not normalize to a target LUFS. It uses the existing
  mastering tools explicitly afterwards. Very short non-silent files without measurable
  integrated loudness are rejected. Intersample overshoot is rejected instead of claiming
  success or silently changing gains.
* Tested browsers are local Edge and CI Chromium, not every Safari/mobile device.

Automated checks can be accepted independently of the pending listening signoff. Keep
the PR Draft until the reviewer completes the remaining acceptance decision.
