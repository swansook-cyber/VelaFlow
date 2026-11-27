from __future__ import annotations

import json
import tempfile
import unittest
import wave
from copy import deepcopy
from pathlib import Path

from streamlit.testing.v1 import AppTest

from core.full_song_mv import create_full_song_storyboard


class FullSongReviewUITests(unittest.TestCase):
    def test_navigation_guards_edits_and_does_not_save_or_change_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            audio = Path(temp) / "song.wav"
            with wave.open(str(audio), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(8000)
                output.writeframes(b"\0\0" * 8000 * 18)
            project = {"title": "UI review copy", "mv": {}}
            scenes = create_full_song_storyboard({}, project, 18, 3)["scenes"]
            project["mv"]["full_song"] = {
                "audio": {"path": str(audio), "duration_seconds": 18},
                "scenes": scenes, "target_aspect_ratio": "16:9",
            }
            before = deepcopy(project["mv"]["full_song"])
            saved_path = Path(temp) / "saved_manifest.json"
            app = AppTest.from_string("""
import json
import streamlit as st
from pathlib import Path
from app.full_song_mv_ui import render_full_song_planner
def save():
    Path(st.session_state.saved_path).write_text(json.dumps(st.session_state.project['mv']['full_song']))
    st.session_state.save_count = st.session_state.get('save_count', 0) + 1
    return {'ok': True}
render_full_song_planner(st.session_state.project, save, lambda *a, **k: {'ok': False})
""")
            app.session_state["project"] = project
            app.session_state["saved_path"] = str(saved_path)
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["mv_full_active_scene"], "scene_001")
            self.assertNotIn("save_count", app.session_state)

            next(box for box in app.text_input if box.label == "Scene description").set_value("Unsaved edit")
            app.run()
            next(button for button in app.button if button.label == "Next scene").click()
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["mv_full_active_scene"], "scene_001")
            self.assertTrue(any("unsaved changes" in warning.value.lower() for warning in app.warning))
            self.assertNotIn("save_count", app.session_state)
            next(button for button in app.button if button.label == "Stay here").click()
            app.run()
            self.assertEqual(next(box for box in app.text_input if box.label == "Scene description").value, "Unsaved edit")

            next(button for button in app.button if button.label == "Next scene").click()
            app.run()
            next(button for button in app.button if button.label == "Discard and switch").click()
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["mv_full_active_scene"], "scene_002")
            self.assertEqual(next(box for box in app.text_input if box.label == "Scene description").value,
                             scenes[1]["scene_description"])
            self.assertNotIn("save_count", app.session_state)
            next(box for box in app.selectbox if box.label == "Jump to scene").set_value("scene_003")
            app.run()
            next(button for button in app.button if button.label == "Go").click()
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["mv_full_active_scene"], "scene_003")
            next(button for button in app.button if button.label == "Previous scene").click()
            app.run()
            self.assertEqual(app.session_state["mv_full_active_scene"], "scene_002")
            self.assertEqual(project["mv"]["full_song"], before)

            next(box for box in app.text_input if box.label == "Scene description").set_value("Saved edit")
            app.run()
            next(button for button in app.button if button.label == "Next scene").click()
            app.run()
            next(button for button in app.button if button.label == "Save and switch").click()
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["mv_full_active_scene"], "scene_003")
            self.assertEqual(app.session_state["save_count"], 1)
            self.assertEqual(project["mv"]["full_song"]["scenes"][1]["scene_description"], "Saved edit")
            self.assertEqual(project["mv"]["full_song"]["scenes"][0]["approval_status"], "Planned")
            restored = json.loads(saved_path.read_text())
            self.assertEqual(restored, project["mv"]["full_song"])
            self.assertEqual([item["scene_id"] for item in restored["scenes"]], ["scene_001", "scene_002", "scene_003"])


if __name__ == "__main__":
    unittest.main()
