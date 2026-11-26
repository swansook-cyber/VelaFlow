from __future__ import annotations

import json
import tempfile
import unittest
import wave
from pathlib import Path

from core.full_song_mv import attach_approved_asset, create_full_song_storyboard, edit_scene, move_scene, probe_song_audio, validate_storyboard
from core.project_io import read_project_json, save_project_folder


class FullSongMVTest(unittest.TestCase):
    def _wav(self, root: Path, seconds: int) -> Path:
        path = root / f"song_{seconds}.wav"
        with wave.open(str(path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(8000)
            silent_second = b"\0\0" * 8000
            for _ in range(seconds):
                output.writeframesraw(silent_second)
        return path

    def test_full_song_audio_and_timeline_180_and_240(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            song = {"normalized_song_output": "[Intro]\n[Verse 1]\nคืนที่ฝนตก\n[Chorus]\nฉันยังคิดถึงเธอ\n[Bridge]\nอยากกลับไป\n[Outro]"}
            for seconds, count in ((180, 30), (240, 40)):
                audio = self._wav(root, seconds)
                probe = probe_song_audio(audio)
                self.assertTrue(probe["ok"], probe)
                self.assertAlmostEqual(probe["duration_seconds"], seconds, places=2)
                plan = create_full_song_storyboard(song, {"title": "Test Song", "character": {"name": "Vela Moon"}}, probe["duration_seconds"], count)
                self.assertTrue(plan["ok"], plan)
                scenes = plan["scenes"]
                self.assertEqual(len(scenes), count)
                self.assertEqual(scenes[0]["start_seconds"], 0)
                self.assertEqual(scenes[-1]["end_seconds"], seconds)
                self.assertTrue(validate_storyboard(scenes, seconds)["ok"])
                self.assertIn("Chorus", {scene["song_section"] for scene in scenes})
                self.assertTrue(all(scene["asset_path"] == "" and scene["approval_status"] == "Planned" for scene in scenes))

    def test_edit_approval_reorder_and_restore_preserve_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            audio = self._wav(root, 180)
            asset = root / "approved.png"
            asset.write_bytes(b"approved test asset")
            project = {"title": "MV Test", "workflow_type": "song", "song": {"normalized_song_output": "[Verse]\nคืนฝนตก"},
                       "assets": {"approved_images": {"1": str(asset)}}, "mv": {}}
            planned = create_full_song_storyboard(project["song"], project, 180, 30)
            scenes = planned["scenes"]
            first_id, second_id = scenes[0]["scene_id"], scenes[1]["scene_id"]
            attached = attach_approved_asset(scenes, first_id, str(asset), 180)
            self.assertTrue(attached["ok"])
            edited = edit_scene(attached["scenes"], first_id,
                                {"visual_prompt": "Revised visual", "duration_seconds": 7.5, "approval_status": "Approved", "reference_asset": str(asset)}, 180)
            self.assertTrue(edited["ok"], edited)
            moved = move_scene(edited["scenes"], first_id, 1, 180)
            self.assertTrue(moved["ok"], moved)
            final = moved["scenes"]
            self.assertEqual(final[1]["scene_id"], first_id)
            self.assertEqual(final[0]["scene_id"], second_id)
            self.assertEqual(final[1]["asset_path"], str(asset))
            self.assertEqual(final[1]["approval_status"], "Approved")
            self.assertEqual(final[0]["approval_status"], "Planned")
            self.assertTrue(validate_storyboard(final, 180)["ok"])
            revised = edit_scene(final, first_id, {"visual_prompt": "Different visual"}, 180)
            self.assertTrue(revised["ok"])
            self.assertEqual(revised["scenes"][1]["approval_status"], "Needs Revision")
            self.assertEqual(revised["scenes"][1]["asset_path"], str(asset))
            project["mv"]["full_song"] = {"audio": {"path": str(audio), "duration_seconds": 180}, "scenes": final}
            folder = save_project_folder(project, root / "projects")
            self.assertTrue((folder / "full_song_scene_manifest.json").is_file())
            restored = read_project_json(folder / "project.json")
            self.assertTrue(restored["ok"])
            restored_scenes = restored["project"]["mv"]["full_song"]["scenes"]
            self.assertEqual(restored_scenes[1]["visual_prompt"], "Revised visual")
            self.assertEqual(restored_scenes[1]["duration_seconds"], 7.5)
            self.assertEqual(json.loads((folder / "full_song_scene_manifest.json").read_text(encoding="utf-8"))["scenes"], restored_scenes)

    def test_invalid_audio_and_missing_asset_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertFalse(probe_song_audio(root / "missing.mp3")["ok"])
            fake_audio = root / "broken.mp3"
            fake_audio.write_bytes(b"not audio")
            self.assertFalse(probe_song_audio(fake_audio)["ok"])
            scenes = create_full_song_storyboard({}, {"title": "Test"}, 180, 30)["scenes"]
            self.assertFalse(attach_approved_asset(scenes, scenes[0]["scene_id"], str(root / "missing.png"), 180)["ok"])
            broken = [dict(scene) for scene in scenes]
            broken[2]["start_seconds"] += 1
            self.assertFalse(validate_storyboard(broken, 180)["ok"])

    def test_song_structure_plan_supplies_sections_without_lyric_headers(self) -> None:
        song = {"normalized_song_output": "คืนที่ฝนตก", "song_structure_plan": {"sections": [
            {"section": "Intro", "weight": 1}, {"section": "Verse 1", "weight": 2},
            {"section": "Instrumental", "weight": 1}, {"section": "Outro", "weight": 1},
        ]}}
        result = create_full_song_storyboard(song, {"title": "Test"}, 180, 30)
        self.assertTrue(result["ok"])
        self.assertEqual(result["scenes"][0]["song_section"], "Intro")
        self.assertEqual(result["scenes"][-1]["song_section"], "Outro")
        self.assertIn("Instrumental", {scene["song_section"] for scene in result["scenes"]})


if __name__ == "__main__":
    unittest.main()
