# UI Flow Checklist

VelaFlow V7.8.1b restores the full sidebar workflow after the V7.8.1 Song
Studio hotfix.

| Page | Status | Notes |
|---|---|---|
| Dashboard | PASS | Project status, quick navigation, recent projects, diagnostics |
| Creator Wizard | PASS | Template selection and project creation flow |
| Song Studio | PASS | Artist Preset, Vela Moon, English instrument tags, auto-fix tags |
| MV Director | PASS | Lyrics input and storyboard generation flow |
| Character Studio | PASS | Character profile and apply-to-storyboard action |
| Image Lab | PASS | Scene image prompt and placeholder generation |
| Image Review | PASS | Approve/reject image state |
| Video Lab | PASS | Manual/offline video slot generation |
| Render Lab | PASS | Render profile, aspect ratios, healthcheck, render action, temp recovery |
| Smart Clip Factory | PASS | Clip type selection, preview, clip set generation |
| Marketing Package | PASS | Build and export marketing package |
| Final Package | PASS | Inspect inputs and build final release package |
| Creative Intelligence | PASS | Scene scores, hooks, arc, suggestions, TikTok recommendations |
| Production Audit | PASS | Full project audit and export |
| Beta Test Mode | PASS | Sessions, checklist, ratings, issues, render compare, reports, stable snapshot |
| Asset Intelligence | PASS | Disk usage and safe cleanup buttons |
| Queue Monitor | PASS | Jobs table, clear finished, cancel job |
| System Health | PASS | Healthcheck and Safe Mode entry |
| Release Hardening Tools | PASS | Lock, release lock, common fixes, diagnostics, safe temp cleanup, duplicate |
| AI Settings | PASS | Provider/key status and safety note |

Validation:

- `python tests/smoke_test.py` passes.
- `python -m compileall -q app core providers tests` passes.
- App launches on `http://localhost:8501/`.
