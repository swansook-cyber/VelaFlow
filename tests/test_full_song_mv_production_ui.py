from __future__ import annotations

import tempfile
import unittest
import wave
from pathlib import Path

from PIL import Image
from streamlit.testing.v1 import AppTest

from core.full_song_mv import create_full_song_storyboard
from core.full_song_mv_production import import_scene_media


class FullSongMVProductionUITests(unittest.TestCase):
    def test_review_qc_accept_without_cloud_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            audio = root / "song.wav"
            with wave.open(str(audio), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(8000)
                for _ in range(180):
                    output.writeframesraw(b"\0\0" * 8000)
            image = root / "shot.png"
            Image.new("RGB", (540, 960), "#223344").save(image)
            project = {"title": "UI QC test", "mv": {}}
            scenes = create_full_song_storyboard({}, project, 180, 30)["scenes"]
            scenes[0]["approval_status"] = "Approved"
            imported = import_scene_media(scenes, scenes[0]["scene_id"], image.name, image.read_bytes(), root / "assets")
            self.assertTrue(imported["ok"])
            project["mv"]["full_song"] = {"audio": {"path": str(audio), "duration_seconds": 180}, "scenes": imported["scenes"]}
            script = """
import streamlit as st
from app.full_song_mv_ui import render_full_song_planner
def save(): return {'ok': True}
def save_audio(*args, **kwargs): raise AssertionError('Unexpected audio import')
render_full_song_planner(st.session_state.project, save, save_audio, lambda provider: st.session_state.get('mock_key', ''))
"""
            app = AppTest.from_string(script)
            app.session_state["project"] = project
            app.run()
            self.assertFalse(app.exception)
            self.assertTrue(next(button for button in app.button if button.label == "Generate this shot").disabled)
            self.assertTrue(next(button for button in app.button if button.label == "Accept this asset").disabled)
            next(button for button in app.button if button.label == "Run file QC").click()
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["project"]["mv"]["full_song"]["scenes"][0]["production"]["assets"][0]["status"], "QC Passed")
            next(box for box in app.checkbox if box.label.startswith("I reviewed this shot")).set_value(True)
            app.run()
            next(button for button in app.button if button.label == "Accept this asset").click()
            app.run()
            self.assertFalse(app.exception)
            scene = app.session_state["project"]["mv"]["full_song"]["scenes"][0]
            self.assertEqual(scene["production"]["assets"][0]["status"], "Accepted")
            self.assertTrue(Path(scene["asset_path"]).is_file())
            app.session_state["mock_key"] = "mock-key"
            app.run()
            self.assertTrue(next(button for button in app.button if button.label == "Generate this shot").disabled)
            next(box for box in app.checkbox if box.label.startswith("I confirm one provider request")).set_value(True)
            app.run()
            self.assertFalse(next(button for button in app.button if button.label == "Generate this shot").disabled)
            next(box for box in app.selectbox if box.label == "Review scene").set_value("scene_002")
            app.run()
            self.assertTrue(next(button for button in app.button if button.label == "Generate this shot").disabled)
