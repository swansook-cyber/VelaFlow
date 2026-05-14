# VelaFlow Closed Beta Release Checklist

Use this checklist before sharing a closed beta build.

## Workflow Tests

- [ ] Music workflow test: create project, generate hooks, generate lyrics, save/export Suno package
- [ ] Seller workflow test: create seller campaign, generate seller content, export TXT/JSON
- [ ] Podcast workflow test: create podcast episode, generate package, export TXT/JSON
- [ ] Viral Clips workflow test: create clips project, generate package, export TXT/JSON
- [ ] Render Job mock test: generate render package, send mock job, check status to Completed, download placeholder
- [ ] Export TXT/JSON test: verify files open with UTF-8 Thai text intact
- [ ] Mobile UI test: open on phone-width viewport, confirm headers, spacing, and buttons are usable
- [ ] Provider health test: confirm Gemini/OpenAI/xAI configured or clearly marked not configured
- [ ] Legacy project fallback test: confirm old `project_data/projects/` projects still load

## Build Validation

- [ ] Run compile:
  `python -m compileall -q app core providers tests`
- [ ] Run smoke test:
  `python tests/smoke_test.py`
- [ ] Build closed beta package:
  `python scripts/build_beta_package.py`
- [ ] Confirm beta zip excludes `.env`, `.venv/`, `project_data/`, caches, logs, and generated exports
- [ ] Launch app:
  `python -m streamlit run app/main.py --server.port 8502`

## Release Notes

- [ ] Review `docs/BETA_NOTES.md`
- [ ] Confirm README run/test commands are current
- [ ] Confirm no real video rendering/API render calls are implied
