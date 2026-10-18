"""Exercise the optional UI without running unrelated app startup/services."""
import unittest
import tempfile
from pathlib import Path

from streamlit.testing.v1 import AppTest


class StemUITests(unittest.TestCase):
    def test_empty_uploads_cannot_render_and_gains_rerun(self):
        root = Path(__file__).resolve().parents[1]
        script = ('from app.stem_mix_ui import render_stem_mixer\n'
                  'render_stem_mixer({"title": "Test"}, ffmpeg_ready=True, max_upload_mb=200)\n')
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / 'stem_ui.py'
            fixture.write_text(script, encoding='utf-8')
            app = AppTest.from_file(str(fixture)).run()
            self.assertEqual(len(app.exception), 0)
            self.assertTrue(app.button[0].disabled)
            self.assertEqual([s.value for s in app.slider], [-6.0, -6.0])
            app.slider[0].set_value(-12.0).run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(app.slider[0].value, -12.0)
            self.assertTrue(app.button[0].disabled)
