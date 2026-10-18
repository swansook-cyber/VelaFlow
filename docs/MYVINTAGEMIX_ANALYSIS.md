# MyVintageMIX investigation and safe first implementation

Date: 2026-10-18 (Asia/Bangkok). Reference: https://myvintagemix.netlify.app/.

## Repository baseline

Fresh clone of swansook-cyber/VelaFlow into this task's work directory. Initial status clean,
main tracking origin/main, HEAD ff4f9a04ba8d008f8bd6860ebc33ec3ae25d6ac3
(`fix(song-studio): correct pre-intro production instruction regex`). Created
feature/song-studio-myvintagemix-analysis from that commit. No existing checkout or
uncommitted work was modified. User branch/no-production instructions override the
repository's generic push-to-main instruction.

Architecture inspected: Streamlit app/main.py; Python core modules; optional local
FFmpeg/FFprobe processing. Song Studio owns lyric/hook/production and Suno exports.
Audio Editor owns cutting, musical hook selection, joining, previews and audio exports.
app/components/waveform_selector/index.html uses locally vendored WaveSurfer 7.12.11
and Regions for playback/selection; it is not the mastering engine.
core/audio_intelligence.py runs loudnorm/PCM analysis with caching/source identity;
core/remaster_engine.py owns presets, custom EQ/dynamics/width/ceiling, reference-guided
mastering, safe output rendering, PCM24 WAV and MP3 measurement/validation.
No pre-existing .github/workflows directory was present.

## REA method and evidence

Read installed C:/Users/ADMIN/.agents/skills/reverse-engineer-anything/SKILL.md and
references/runtime-observation.md. Actual connected MCP tools were available; no setup,
configuration changes or package installation required. Used capture_browser_scenario
with Edge launch/headless, fresh empty storage, declared wait actions and explicit
viewport/capture options; export_evidence_bundle preserved complete records.
Initial schema validation attempts returned errors before execution; corrected requests
captured successfully. No login, Pro entry, paywall circumvention, private APIs or
reference audio upload was attempted. Public page startup made its own review/stats/
visit requests; those were observed, not manually replayed.

Evidence IDs:

* R1 desktop 1440x1000 DOM/accessibility/network:
  ev_406b5600749625b60a34e18f51c9f536c35835bc6045d2f9ff1407bb42310650
* R2 mobile 390x844 accessibility/screenshot:
  ev_9a3282b8cdcb5453dfee1844d8ec0e48e796b73b48f40c095886a578b9271175
* V1 isolated VelaFlow mixer UI mobile screenshot/accessibility:
  ev_bbec9544c0d2e9b2500fb065bdcb7ec5bebaba9ed8e2971585e2830d90fe0474
* V2 isolated VelaFlow mixer UI desktop screenshot/accessibility:
  ev_1358c770e7b00e4793d6bc5e0067ca42c46a34cba6c8422bd8d93ad2fbd8a5a1

Complete evidence bundle is delivered separately, not copied into application source.
The desktop DOM contained inline shipped JavaScript; it was inspected as evidence only.
No reference code, visual assets, branding, preset coefficients or DSP implementation
was copied into VelaFlow. REA's empty unknown ledger is not a claim that investigation
unknowns are resolved; the explicit unknowns below remain open.

## Findings: Confirmed

R1/R2 confirm visible UI, labels and available options, not successful DSP execution:

* Thai single-page workspace: overview, audio adjustments, Formula/LUT Pro, export,
  skins, six-step onboarding, transport/timeline, before/after selection.
* Single-song mode and vocal+music mode labeled Pro. No authenticated stem workflow tested.
* Bass 120 Hz, mid 1 kHz, high 8 kHz controls; compressor enable, threshold, ratio,
  attack/release; dry/wet, early reflections, tail/diffusion, pan; output gain,
  limiter and ceiling UI. These establish exposed controls only.
* Clip indicator, peak readout, approximate middle-of-song loudness, last-three-second
  LUFS wording and whole-song measurement button. No audio loaded: values unmeasured.
* Six style choices: gentle polish, vocal clarity, warmth, brightness, YouTube loudness,
  harshness reduction; loudness-matched comparison checkbox. Auto style marked Pro.
* Export UI: as-mixed, YouTube -14 LUFS; Spotify/Apple/TikTok choices labeled Pro;
  WAV24/WAV16/MP3 320k choices; WAV24 stereo 48 kHz wording. Export disabled with no file.
* Reference UI describes a -1 dBFS ceiling. This is NOT evidence of true-peak compliance.
* LUT appears as a way to save audio settings, not evidence of video color processing.
  Saving/loading/serialization was not exercised.
* Mobile screenshot shows bottom navigation, top controls, stacked content and onboarding
  overlay. Desktop accessibility inventory exposes sidebar navigation. No exhaustive
  breakpoint or desktop pixel audit was performed.
* Shipped inline code includes React 18.3.1 and AudioContext, OfflineAudioContext,
  BiquadFilter/DynamicsCompressor and createGain identifiers. Presence is static evidence,
  not proof those paths executed. Supabase review/stat/visit requests observed on startup.

## Findings: Inferred

* Live/offline browser audio graphs likely support preview/render based on the shipped
  Web Audio identifiers and UI. Exact topology, coefficients, execution and parity unknown.
* LUT likely means a reusable audio setting snapshot based on onboarding wording.
* Keeping audio local is the site's UI claim; startup traffic without any audio input
  does not verify that claim across upload/export/authenticated workflows.

## Findings: Unknown

Actual stem mixing/alignment, any source separation, audible preset effects, EQ response,
compressor/limiter transfer curves, LUFS gating/calibration, oversampled true peak,
clipping detector accuracy, export bytes/dither/normalization, YouTube target attainment,
preview/export parity, LUT schema/round-trip, Pro entitlements, full dependencies/versions,
worker responsibilities, WASM use and large-file performance remain unverified.
No reference export or reference audio processing test was run. No absence claim is made
from a missing string or from the bounded startup network observation.

## Feature gap matrix

| Feature | Existing VelaFlow evidence | Classification | Value / complexity / risk | Decision |
|---|---|---|---|---|
| Vocal/instrumental simultaneous mix | No amix/stem workflow in inspected editor/master modules | Missing Features | High / medium / medium | P1 optional supplied-stem mix; no separation claim |
| EQ/compression/limiter | remaster_engine custom config + safe rendering | Already Implemented | High / low / medium | Reuse; do not replace |
| Mastering presets | REMASTER_STYLES, recommendation/reference-guided logic | Already Implemented | High / low / medium | Keep current presets and coefficients |
| LUFS/true peak | audio_intelligence loudnorm, measure_remaster_artifact | Already Implemented | High / medium / medium | Reuse measured output, distinguish targets from results |
| Clip reporting | decoded PCM rail count and true-peak validation | Needs Improvement | High / medium / medium | Expose existing measurement for new mix; broader calibration later |
| WAV export | Editor and remaster export pipelines | Already Implemented | High / low / low | Add measured PCM24 mix artifact |
| Responsive mix UI | Existing Streamlit and responsive WaveSurfer | Needs Improvement | Medium / low / low | Stack optional controls; isolated browser checks |
| Saved audio LUT | Custom mastering settings persisted; no verified LUT interchange | Needs Improvement | Medium / medium / medium | Defer interchange until round-trip design/test |
| Loudness-matched preview | Existing remaster A/B previews; exact matching not established here | Needs Improvement | Medium / medium / medium | Audit before extending |
| Real-time browser DSP rewrite | Current authoritative processing is FFmpeg | Not Recommended | Low / high / high | Avoid duplicate processing engines |
| Automatic stem separation | Not confirmed in reference | Not Recommended | Uncertain / high / high | Out of first implementation |
| Clone skins/paywall/branding | Unrelated to audio quality | Not Recommended | Low / medium / high | Do not copy |

## Implementation and plan

Implemented first safe increment: Audio Editor gains an explicit third mode, Mix stems;
Cut remains default, Join remains separate, Song Studio generation and existing mastering
paths untouched. User supplies two pre-aligned WAV/MP3 stems beginning at 0:00. Independent
-24..+6 dB gains default -6 dB. FFmpeg resamples to stereo 48 kHz, mixes without automatic
amix normalization, uses a conservative -2 dBFS sample limiter, and encodes PCM24 WAV.
Existing remaster measurement must report success, no rail hits and <= -1 dBTP (or
verified effective silence) before the UI offers download. Rejection is explicit, not
a success. This is peak protection, not a guarantee of a requested integrated LUFS.
Longer stem sets duration. Unique output directories and -n avoid overwriting artifacts.
Sources are retained unchanged; no automatic project master replacement. UI results
are invalidated by changed upload content/gain, with project-scoped widget keys.

No runtime dependency added. Existing presets/EQ/compression remain in Remaster Studio:
download the mix and use that existing upload workflow. Next increments should validate
the integrated app on representative projects, then consider explicit handoff to existing
mastering, measured level-matched previews and versioned settings round-trip. Do not add
unverified reference features or new DSP engines merely for feature parity.

## Changed files

* core/stem_mixer.py: isolated local render/measurement service.
* app/main.py: optional supplied-stem UI and mode dispatch.
* tests/test_stem_mixer.py: real audio/export/source preservation and failure tests.
* tests/test_stem_ui.py: Streamlit isolated widget/gain rerun smoke test.
* .github/workflows/song-studio.yml: Python 3.12, FFmpeg, compile and unittest gates.
* docs/MYVINTAGEMIX_ANALYSIS.md: this findings/gap/implementation/validation report.
* PROJECT_CONTEXT.md: ownership of optional supplied-stem mixing.

## Actual validation results

* python -m unittest discover -s tests -p 'test_*.py': PASS, 10 tests, no skips on this host.
  Includes existing Song Studio/Suno regressions; real dual-tone mix, both frequencies
  retained, longer duration, stereo/48k/24-bit RIFF header, unchanged source hashes,
  distinct export paths, measured true peak/no rail hits, overloaded inputs, corrupt
  file failure, nonfinite/out-of-range gain rejection and missing-input failure.
* Streamlit AppTest: isolated actual mixer function renders, disabled empty-input action,
  default gains and gain-change rerun pass. Initial test harness BOM/Windows encoding
  failures were fixed; final run above passed. Bare-mode context warning is nonfatal.
* python -m compileall -q core app: PASS.
* git diff --check: PASS.
* REA browser captures of isolated actual mixer function at 390x844 and 1440x1000:
  controls visible/stacked and accessibility includes both uploaders/sliders and disabled
  render button. Mobile uses vertical scrolling. This is NOT a full-app navigation or
  upload/download end-to-end test and not a device compatibility guarantee.
* Full tests/smoke_test.py NOT RUN: contains broad persistent fixture/data mutations and
  deletion routines. Focused read-only-to-source regression gates above were used.
* GitHub Actions configured; hosted execution status must be checked after push. No
  claim that hosted CI passed until an actual completed successful run is observed.

## Remaining risks

* Supplied stems must be aligned; no offset/sync/separation support. Mixing correlated
  stems can change phase/tone. Listening QA with representative creator material pending.
* Peak validation may reject intersample overshoot instead of automatically retrying;
  reduce stem levels and render again. No LUFS normalization in the new mixing stage.
* Browser upload sizes are capped, but duration is not; FFmpeg/measurement timeouts apply.
  UI hashes uploaded buffers on reruns; very large files can consume time/memory. Retained
  source/intermediate artifacts consume disk; no automatic deletion was added.
* UI filesystem errors before rendering can surface through Streamlit; full-app integration,
  project switching and uploaded-file end-to-end verification remain pending.
* Existing dependency pins include Streamlit 1.41.1; some existing app container APIs may
  require compatibility review. Isolated tests do not prove unrelated startup/navigation.
* No production deployment, main merge, main push, reference code copying or Pro bypass.
