# VelaFlow V7.7 Beta Test Mode

V7.7 adds a local workflow for testing real songs in a repeatable way before
moving toward V8 or packaging.

## Purpose

Beta Test Mode helps a creator record what was tested, rate each production
area, log issues, compare render versions, and decide whether a build is a
stable candidate.

## Systems

| System | File | Purpose |
|---|---|---|
| Beta Session | `core/beta_testing.py` | record song, template, render profile, notes, ratings, issues, and audit score |
| Beta Checklist | `core/beta_testing.py` | confirm Song, Storyboard, Image, Motion, Subtitle, Render, Clips, and Marketing were reviewed |
| Issue Log | `core/beta_testing.py` | keep project-level bug notes with area, severity, status, and description |
| Render Compare | `core/beta_testing.py` | compare key files and sizes between two render folders |
| Stable Candidate | `core/beta_testing.py` | mark a tested session as the current stable candidate for the project |
| Beta Report Export | `core/beta_testing.py` | export JSON and Markdown test reports |

## Storage

Beta sessions are stored locally:

```text
project_data/beta_tests/<project_name>/beta_*.json
```

Reports export to:

```text
outputs/beta_reports/<project_name>/
```

## UI

The Streamlit sidebar now includes `Beta Test Mode`. The page includes:

- New Beta Session
- Ratings
- Bug / Issue Log
- Beta Test Checklist
- Compare 2 Render Versions
- Export Beta Test Report
- Mark Build as Stable Candidate

## Offline Rule

Beta Test Mode is offline-first. It does not call paid providers, upload files,
or require online license/payment systems.
