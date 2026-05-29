from __future__ import annotations


PAGE_LABELS = {
    "Creator Dashboard": "Creator Dashboard",
    "Idea": "Idea",
    "Generate Song": "Generate Song",
    "Generate Visual Pack": "Generate Visual Pack",
    "Export Release Pack": "Export Release Pack",
    "VelaFlow Agent Studio": "🤖 VelaFlow Agent Studio",
    "Creator Wizard": "Release Workflow Wizard",
    "Hook Clip Studio": "Clip Studio",
    "Smart Clip Factory": "Clip Factory",
    "Production Audit": "Quality Audit",
    "Release Hardening Tools": "Recovery Tools",
}

FULL_MENU_GROUPS = {
    "START": ["Creator Dashboard", "Idea", "Generate Song", "Generate Visual Pack", "Export Release Pack", "Dashboard", "One Click Creator Flow", "VelaFlow Agent Studio", "Creator Wizard"],
    "SONG": ["Song Studio", "Song Library", "Artist Preset Manager"],
    "VISUAL": ["MV Director", "Video Prompt Studio", "Character Studio", "Image Lab", "Image Review", "Video Lab"],
    "PRODUCTION": ["Hook Clip Studio", "Remaster Studio", "Affiliate Studio", "Shorts Factory", "Render Lab", "Smart Clip Factory", "Marketing Package", "Final Package"],
    "INTELLIGENCE": ["Creative Intelligence", "Production Audit", "Beta Test Mode", "Asset Intelligence"],
    "SYSTEM": ["Queue Monitor", "System Health", "Release Hardening Tools", "AI Settings"],
}

SONG_ONLY_MENU_GROUPS = {
    "CREATE": ["Creator Dashboard", "Idea", "Generate Song", "Generate Visual Pack", "Export Release Pack"],
}

SELLER_STUDIO_MENU_GROUPS = {
    "START": ["Dashboard"],
    "SELLER": ["Affiliate Studio", "Shorts Factory", "Seller Studio", "Hook Clip Studio"],
    "SYSTEM": ["AI Settings", "System Health"],
}

PODCAST_STUDIO_MENU_GROUPS = {
    "START": ["Dashboard"],
    "PODCAST": ["Podcast Studio", "Hook Clip Studio"],
    "SYSTEM": ["AI Settings", "System Health"],
}

VIRAL_CLIPS_MENU_GROUPS = {
    "START": ["Dashboard"],
    "CLIPS": ["Viral Clips Studio", "Hook Clip Studio"],
    "SYSTEM": ["AI Settings", "System Health"],
}

HOOK_CLIP_MENU_GROUPS = {
    "START": ["Dashboard"],
    "CLIPS": ["Hook Clip Studio", "Viral Clips Studio"],
    "SYSTEM": ["AI Settings", "System Health", "Queue Monitor"],
}

SONG_ONLY_ALLOWED_PAGES = {page for pages in SONG_ONLY_MENU_GROUPS.values() for page in pages}
SELLER_STUDIO_ALLOWED_PAGES = {page for pages in SELLER_STUDIO_MENU_GROUPS.values() for page in pages}
PODCAST_STUDIO_ALLOWED_PAGES = {page for pages in PODCAST_STUDIO_MENU_GROUPS.values() for page in pages}
VIRAL_CLIPS_ALLOWED_PAGES = {page for pages in VIRAL_CLIPS_MENU_GROUPS.values() for page in pages}
HOOK_CLIP_ALLOWED_PAGES = {page for pages in HOOK_CLIP_MENU_GROUPS.values() for page in pages}


def page_label(page_name: str) -> str:
    return PAGE_LABELS.get(page_name, page_name)


def flatten_pages(menu_groups: dict[str, list[str]]) -> list[str]:
    return [page_name for pages in menu_groups.values() for page_name in pages]


def menu_groups_for_mode(workflow_mode: str) -> dict[str, list[str]]:
    if workflow_mode == "Song Studio Only":
        return SONG_ONLY_MENU_GROUPS
    if workflow_mode == "Seller Studio (Beta)":
        return SELLER_STUDIO_MENU_GROUPS
    if workflow_mode == "Podcast Studio (Beta)":
        return PODCAST_STUDIO_MENU_GROUPS
    if workflow_mode == "Viral Clips Studio (Beta)":
        return VIRAL_CLIPS_MENU_GROUPS
    if workflow_mode == "Hook Clip Studio (Beta)":
        return HOOK_CLIP_MENU_GROUPS
    return FULL_MENU_GROUPS


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
