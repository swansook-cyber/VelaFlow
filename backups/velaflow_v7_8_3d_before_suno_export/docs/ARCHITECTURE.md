# VelaFlow Architecture

VelaFlow is a single local Streamlit application organized as modular internal
systems. The product goal is an AI Content Automation Pipeline for music,
music videos, shorts, Spotify Canvas, marketing assets, and final release
packages.

## Layers

- App UI: Streamlit pages in `app/main.py`
- Core services: project IO, settings, job queue, healthcheck, licensing
- Domain modules: Director, Motion, Render, Clips, Canvas, Marketing, Assets
- Provider layer: text/image/video/local fallback providers
- Output layer: renders, clips, marketing packages, final packages

## Compatibility

VelaFlow replaces the old Vela AI Studio naming. Existing local folders and
projects can still be loaded; new documentation and generated names should use
`VelaFlow` and `velaflow`.
