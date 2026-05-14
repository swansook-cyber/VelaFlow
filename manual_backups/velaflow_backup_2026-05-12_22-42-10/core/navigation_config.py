from __future__ import annotations


PAGE_LABELS = {
    "Creator Wizard": "Release Workflow Wizard",
    "Smart Clip Factory": "Clip Factory",
    "Production Audit": "Quality Audit",
    "Release Hardening Tools": "Recovery Tools",
}

FULL_MENU_GROUPS = {
    "START": ["Dashboard", "Creator Wizard"],
    "SONG": ["Song Studio", "Song Library", "Artist Preset Manager"],
    "VISUAL": ["MV Director", "Character Studio", "Image Lab", "Image Review", "Video Lab"],
    "PRODUCTION": ["Render Lab", "Smart Clip Factory", "Marketing Package", "Final Package"],
    "INTELLIGENCE": ["Creative Intelligence", "Production Audit", "Beta Test Mode", "Asset Intelligence"],
    "SYSTEM": ["Queue Monitor", "System Health", "Release Hardening Tools", "AI Settings"],
}

SONG_ONLY_MENU_GROUPS = {
    "START": ["Dashboard"],
    "SONG": ["Song Studio", "Song Library", "Artist Preset Manager"],
    "SYSTEM": ["AI Settings", "System Health"],
}

SONG_ONLY_ALLOWED_PAGES = {page for pages in SONG_ONLY_MENU_GROUPS.values() for page in pages}


def page_label(page_name: str) -> str:
    return PAGE_LABELS.get(page_name, page_name)


def flatten_pages(menu_groups: dict[str, list[str]]) -> list[str]:
    return [page_name for pages in menu_groups.values() for page_name in pages]


def menu_groups_for_mode(workflow_mode: str) -> dict[str, list[str]]:
    return SONG_ONLY_MENU_GROUPS if workflow_mode == "Song Studio Only" else FULL_MENU_GROUPS


def normalize_navigation_state(
    menu_groups: dict[str, list[str]],
    selected_section: str | None,
    selected_page: str | None,
) -> tuple[str, str]:
    if selected_section not in menu_groups:
        selected_section = next(iter(menu_groups), "START")
    section_pages = menu_groups.get(selected_section, [])
    if selected_page not in section_pages:
        selected_page = section_pages[0] if section_pages else "Dashboard"
    return selected_section, selected_page
