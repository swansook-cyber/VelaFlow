# Project Structure

Recommended folder name for new installs:

```text
velaflow/
  app/
  core/
  providers/
  config/
  docs/
  tests/
  project_data/
  outputs/
```

Current code remains backward compatible when launched from an older local
folder name, but new docs, packages, and scripts use `velaflow`.

## Important Paths

- `app/main.py`: Streamlit application shell
- `core/branding.py`: product name, slug, tagline, brand constants
- `core/licensing.py`: local LicenseService
- `core/feature_flags.py`: default package and feature flag definitions
- `config/license.json`: local mock license config
- `project_data/music/`: music and full-pipeline projects
- `project_data/seller/`: Seller Studio campaigns
- `project_data/podcast/`: Podcast Studio episodes
- `project_data/clips/`: Viral Clips Studio projects
- `project_data/mv/`: MV-only project folders
- `project_data/projects/`: legacy project folders, still readable
- `outputs/renders/`: render outputs
- `outputs/final_packages/`: release-ready final packages
