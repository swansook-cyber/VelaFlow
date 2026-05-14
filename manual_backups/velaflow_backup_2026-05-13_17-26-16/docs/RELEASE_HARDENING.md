# VelaFlow V7.6 Release Readiness & Usage Hardening

V7.6 focuses on stability for real local use before V8 or packaging work.

## Systems

| System | File | Purpose |
|---|---|---|
| Render Recovery | `core/render_recovery.py` | save render state, locate failed/partial renders, recover temp scene clips |
| Diagnostic Bundle | `core/render_recovery.py` | export logs, manifests, render state, config, and project snapshot as ZIP |
| Project Lock | `core/project_lock.py` | create local project lock files to avoid accidental parallel editing |
| Safe Mode | `core/safe_mode.py` | open damaged project JSON as a safe placeholder and preserve a broken backup |
| Common Fixes | `core/common_fixes.py` | repair missing project keys, defaults, stale approved assets, and subtitle fallbacks |
| Pre-render Healthcheck | `core/healthcheck.py` | verify render-critical state before queueing expensive work |

## UI

- Project Dashboard: Release Hardening Tools
- Render Lab: Pre-render Healthcheck, failed render lookup, temp recovery, diagnostics
- Quality Checklist: audit remains available before final render
- Final Package: creates backup before package build
- System Health: detailed healthcheck, safe mode, diagnostics, common fixes

## Offline Rule

All hardening tools are local/offline. They do not call paid providers or upload
project data.
