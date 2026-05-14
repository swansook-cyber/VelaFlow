# VelaFlow V7.7 Stable Candidate 1

V7.8 introduces the Stable Candidate Freeze workflow. The freeze target is:

```text
VelaFlow V7.7 Stable Candidate 1
```

## Freeze Policy

After this freeze point, the core pipeline should not be changed except for
bug fixes. New V8 or packaging work should have a rollback point through the
stable candidate snapshot.

## Features Ready

- Song Studio and MV Director workflow
- Character Studio and character lock prompt injection
- Image Lab and Image Review approval workflow
- Video Lab with manual/offline placeholder providers
- Queue Monitor and persistent job state
- Render Lab with FFmpeg pipeline, subtitles, motion, profiles, and recovery
- Clip Factory, Marketing Package, and Final Package exports
- Asset Manager, System Logs, System Health, Safe Mode, and diagnostics
- Beta Test Mode with ratings, issue log, reports, and stable candidate marker

## Known Issues

Known issues are project-specific and should be captured in each Stable
Candidate Snapshot from the current production audit and beta issue log.

## Not Done

- No online activation/payment/subscription system
- No cloud sync or team collaboration
- No full AI video generation by default
- No auto upload
- No installer, EXE launcher, or hidden CMD packaging yet

## Release Evidence

Use **Create Stable Candidate Snapshot** inside VelaFlow to export:

- Diagnostic bundle
- Production audit
- Beta test report
- Optional smoke test result
- Project snapshot
- Stable manifest
- Zipped release evidence folder
