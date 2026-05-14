# Packaging Notes

VelaFlow V7.8.2 adds source-package hygiene before any future installer or EXE
work.

## Source Package Script

Run:

```powershell
python scripts/create_source_package.py
```

The package is created under:

```text
outputs/source_packages/
```

## Included Paths

- `app/`
- `core/`
- `providers/`
- `config/`
- `docs/`
- `tests/`
- `README.md`
- `MASTER_CONTEXT.md`
- `CHANGELOG.md`
- `TODO_NEXT.md`
- `requirements.txt`
- `.env.example`
- `run_velaflow.bat`

## Always Excluded

- `.env`
- `.venv/`
- `outputs/cache/`
- `outputs/renders/_scene_cache/`
- `__pycache__/`
- `*.pyc`
- heavy temporary render/audio/video files

## Rule

The source package is whitelist-based. It does not include `outputs/`,
`project_data/`, local secrets, virtual environments, render caches, or generated
media unless explicitly added to the whitelist in the future.
