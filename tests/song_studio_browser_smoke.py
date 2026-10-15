"""Smoke test Streamlit rendering with desktop and phone-sized Chromium.

Not a substitute for an actual iOS Safari or full AI generation E2E test.
"""
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    artifact_dir = Path('test-artifacts/song-studio-browser')
    artifact_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for label, viewport in (
                ("desktop", {"width": 1440, "height": 900}),
                ("mobile", {"width": 390, "height": 844}),
            ):
                page = browser.new_page(viewport=viewport, device_scale_factor=1)
                errors: list[str] = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                response = page.goto("http://127.0.0.1:8502", wait_until="domcontentloaded", timeout=30000)
                assert response is not None and response.status == 200, (label, response)
                page.locator('[data-testid="stApp"]').wait_for(timeout=30000)
                page.wait_for_timeout(1800)
                assert not page.locator('[data-testid="stException"]').count(), (
                    label, page.locator('[data-testid="stException"]').all_text_contents()
                )
                assert not errors, (label, errors)
                page.mouse.wheel(0, 600)
                page.wait_for_timeout(350)
                assert page.locator('[data-testid="stApp"]').is_visible(), label
                sidebar_toggle = page.get_by_role("button", name="Open sidebar")
                if sidebar_toggle.count() and sidebar_toggle.first.is_visible():
                    sidebar_toggle.first.click()
                    page.wait_for_timeout(300)
                    assert not page.locator('[data-testid="stException"]').count(), label
                page.screenshot(path=str(artifact_dir / f"{label}.png"), full_page=True)
                assert not errors, (label, errors)
                print(f"{label} Streamlit rendering: PASS")
                page.close()
        finally:
            browser.close()


if __name__ == "__main__":
    main()
