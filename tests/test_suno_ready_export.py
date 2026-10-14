"""Regression checks for the separate Suno paste-ready text downloads."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.suno_export import export_suno_files


class SunoReadyExportTests(unittest.TestCase):
    def test_style_is_separate_and_legacy_package_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lyrics = "[Intro]\n(Acoustic guitar)\n[Verse 1]\nฉันยังจำเธอได้\n[Chorus]\nไม่อยากปล่อยมือ"
            style = "Thai pop rock, warm piano, 94 BPM, male vocal"
            song = {
                "title": "ทดสอบเพลง",
                "artist_name": "Vela Test",
                "complete_lyrics": lyrics,
                "music_style_prompt": style,
            }
            response = export_suno_files("Suno Ready Test", song, base_dir=tmp, workflow_mode="Song Studio Only")
            self.assertTrue(response["ok"], response.get("error"))
            data = response["data"]
            self.assertEqual(data["lyrics_only_text"], lyrics)
            self.assertEqual(data["suno_style_only_text"], style)
            self.assertEqual(Path(data["suno_style_only"]).read_text(encoding="utf-8"), style)
            self.assertIn("STYLE PROMPT FOR SUNO", data["suno_full_text"])
            self.assertIn("CREATOR RELEASE PACKAGE", data["suno_full_text"])
            self.assertNotIn("CREATOR RELEASE PACKAGE", data["suno_style_only_text"])
            self.assertFalse(data["pre_intro_direction_warning"])

    def test_pre_intro_production_instruction_is_advisory_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lyrics = "(Electric guitar solo)\n[Intro]\n(Soft piano)\n[Verse 1]\nฉันยังรอ"
            response = export_suno_files(
                "Suno Direction Test",
                {"title": "ทดสอบ", "complete_lyrics": lyrics, "music_style_prompt": "Pop Rock"},
                base_dir=tmp,
                workflow_mode="Song Studio Only",
            )
            self.assertTrue(response["ok"], response.get("error"))
            data = response["data"]
            self.assertTrue(data["pre_intro_direction_warning"])
            self.assertEqual(data["lyrics_only_text"], lyrics)


if __name__ == "__main__":
    unittest.main()
