# VelaFlow V7.1 Creator Productivity

V7.1 focuses on creator velocity instead of adding heavier AI generation. The
goal is to make repeated work faster, improve consistency, and keep larger
projects manageable.

## Smart Asset Library

Module: `core/asset_library.py`

The library indexes reusable project assets:

- approved images
- generated image versions
- video slots
- favorite characters
- reusable hook metadata

Assets can be searched by mood, color, genre, emotion, project, kind, camera,
and prompt text. The library is stored locally at
`project_data/asset_library.json`.

## Prompt Memory

Module: `core/prompt_memory.py`

Prompt memory stores local creator preferences:

- render profile
- subtitle style
- motion style
- color profile
- prompt keywords
- favorite scene tags

The default config lives at `config/prompt_memory.json`.

## Scene Reuse

Module: `core/scene_reuse.py`

The scene reuse engine recommends assets or prompts from the Smart Asset
Library for current storyboard scenes. This helps maintain visual consistency
across projects without requiring new provider calls.

## Creative Suggestions

Module: `core/creative_suggestions.py`

Suggestions are offline heuristics. They flag issues such as long subtitles,
weak visual quality, missing prompts, color mismatches, and hook scenes that may
need stronger motion.

## Workspace Optimization

Module: `core/workspace_optimizer.py`

This module reports workspace size, builds a lightweight thumbnail index, and
cleans old cache files by TTL.

## Offline Preset Marketplace Foundation

Module: `core/preset_marketplace.py`

This exports and imports preset bundles as local ZIP files. It is intentionally
offline only: no marketplace, login, payment, cloud sync, or subscription logic.

## One Click Workflow

Module: `core/one_click_workflow.py`

The one-click layer prepares job payloads for:

- Generate Full MV Draft
- Generate TikTok Set
- Generate Release Package readiness checks

It reuses the existing queue, render, clip, and package systems instead of
creating a parallel workflow engine.
