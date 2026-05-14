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

Current code remains backward compatible if the local folder is still named
`vela_ai_studio_v5`.

## Important Paths

- `app/main.py`: Streamlit application shell
- `core/branding.py`: product name, slug, tagline, brand constants
- `core/licensing.py`: local LicenseService
- `core/feature_flags.py`: default package and feature flag definitions
- `config/license.json`: local mock license config
- `project_data/projects/`: persistent project folders
- `outputs/renders/`: render outputs
- `outputs/final_packages/`: release-ready final packages
