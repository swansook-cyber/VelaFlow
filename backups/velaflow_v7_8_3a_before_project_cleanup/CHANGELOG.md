# Changelog

## VelaFlow V7.8.3a - Navigation Flow Fix

- Added centralized Streamlit navigation helper `go_to_page(section, page)`.
- Bound sidebar section/page widgets to `selected_section` and `selected_page`.
- Fixed Song Studio `Save Lyrics & Continue to MV Director` rerun navigation.
- Updated dashboard quick navigation and Render Lab shortcut to use the same helper.

## VelaFlow V7.8.3 - Song Studio Workflow Restoration

- Restored multi-hook candidate workflow in Song Studio.
- Added selected-hook save metadata and lightweight song draft history.
- Restored clear Save Lyrics, Save Draft, Load Last Saved Lyrics, and Save Lyrics & Continue flow.
- Kept Vela Moon Artist Preset and English-only instrument tag normalization active.
- Added hook metadata to Song Studio exports and final package song files.
