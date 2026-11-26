from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from core.full_song_mv import create_full_song_storyboard, edit_scene, validate_storyboard
from core.full_song_mv_production import (
    accept_scene_asset, begin_generation, import_scene_media, inspect_media, qc_scene_asset,
    request_scene_retry, run_generation,
)
from core.project_io import read_project_json, save_project_folder


class FullSongMVProductionTests(unittest.TestCase):
    def _scenes(self) -> list[dict]:
        scenes = create_full_song_storyboard({}, {"title": "Production Test"}, 180, 30)["scenes"]
        scenes[0]["approval_status"] = "Approved"
        scenes[1]["approval_status"] = "Approved"
        return scenes

    def _image(self, folder: Path, name: str = "shot.png") -> Path:
        path = folder / name
        Image.new("RGB", (540, 960), "#223344").save(path)
        return path

    def _video(self, folder: Path, name: str = "shot.mp4", seconds: int = 5) -> Path:
        path = folder / name
        result = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                                 f"color=c=black:s=540x960:d={seconds}", "-c:v", "mpeg4", "-y", str(path)],
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        return path

    def test_import_qc_accept_revision_and_manifest_restore(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = self._image(root)
            scenes = self._scenes()
            scene_id = scenes[0]["scene_id"]
            self.assertFalse(import_scene_media(scenes, scenes[2]["scene_id"], original.name, original.read_bytes(), root)["ok"])
            self.assertFalse(import_scene_media(scenes, scene_id, "broken.png", b"not an image", root)["ok"])
            square = root / "square.png"
            Image.new("RGB", (512, 512), "#334455").save(square)
            square_import = import_scene_media(scenes, scene_id, square.name, square.read_bytes(), root / "assets")
            self.assertTrue(square_import["ok"])
            square_qc = qc_scene_asset(square_import["scenes"], scene_id, square_import["asset_id"])
            self.assertFalse(square_qc["ok"])
            self.assertFalse(square_qc["qc_result"]["checks"]["aspect_ratio_9_16"])
            imported = import_scene_media(scenes, scene_id, original.name, original.read_bytes(), root / "assets")
            self.assertTrue(imported["ok"], imported)
            scenes = imported["scenes"]
            record = scenes[0]["production"]["assets"][0]
            self.assertNotEqual(Path(record["path"]), original)
            self.assertEqual(record["status"], "Needs QC")
            self.assertEqual(original.read_bytes(), Path(record["path"]).read_bytes())
            self.assertFalse(accept_scene_asset(scenes, scene_id, record["asset_id"])["ok"])
            checked = qc_scene_asset(scenes, scene_id, record["asset_id"])
            self.assertTrue(checked["ok"], checked)
            self.assertFalse(checked["qc_result"]["human_accepted"])
            Image.new("RGB", (540, 960), "#445566").save(record["path"])
            self.assertFalse(accept_scene_asset(checked["scenes"], scene_id, record["asset_id"])["ok"])
            checked = qc_scene_asset(checked["scenes"], scene_id, record["asset_id"])
            self.assertTrue(checked["ok"])
            accepted = accept_scene_asset(checked["scenes"], scene_id, record["asset_id"])
            self.assertTrue(accepted["ok"])
            scenes = accepted["scenes"]
            self.assertEqual(scenes[0]["asset_path"], record["path"])
            self.assertTrue(scenes[0]["production"]["assets"][0]["qc_result"]["human_accepted"])
            repeated_qc = qc_scene_asset(scenes, scene_id, record["asset_id"])
            self.assertTrue(repeated_qc["ok"])
            self.assertEqual(repeated_qc["scenes"][0]["production"]["assets"][0]["status"], "Accepted")
            self.assertTrue(repeated_qc["scenes"][0]["production"]["assets"][0]["qc_result"]["human_accepted"])
            self.assertEqual(scenes[0]["revision"], record["scene_revision"])
            unchanged = edit_scene(scenes, scene_id, {"visual_prompt": scenes[0]["visual_prompt"]}, 180)
            self.assertEqual(unchanged["scenes"][0]["revision"], record["scene_revision"])
            revised = edit_scene(scenes, scene_id, {"visual_prompt": "New rainy window"}, 180)
            self.assertTrue(revised["ok"])
            self.assertEqual(revised["scenes"][0]["qc_status"], "Needs Revision")
            reapproved = edit_scene(revised["scenes"], scene_id, {"approval_status": "Approved"}, 180)
            self.assertTrue(reapproved["ok"])
            self.assertEqual(reapproved["scenes"][0]["revision"], record["scene_revision"] + 1)
            stale = qc_scene_asset(reapproved["scenes"], scene_id, record["asset_id"])
            self.assertFalse(stale["ok"])
            self.assertFalse(stale["qc_result"]["checks"]["current_scene_revision"])
            historical = stale["scenes"][0]["production"]["assets"][0]
            self.assertEqual(historical["status"], "Accepted")
            self.assertTrue(historical["qc_result"]["passed"])
            self.assertTrue(historical["qc_result"]["human_accepted"])
            self.assertFalse(accept_scene_asset(stale["scenes"], scene_id, record["asset_id"])["ok"])
            self.assertTrue(Path(record["path"]).is_file())
            project = {"title": "Production Test", "workflow_type": "song", "mv": {"full_song": {"audio": {"duration_seconds": 180}, "scenes": stale["scenes"]}}}
            folder = save_project_folder(project, root / "projects")
            manifest = json.loads((folder / "full_song_scene_manifest.json").read_text(encoding="utf-8"))
            restored = read_project_json(folder / "project.json")
            self.assertTrue(restored["ok"])
            self.assertEqual(restored["project"]["mv"]["full_song"], manifest)
            self.assertTrue(validate_storyboard(manifest["scenes"], 180)["ok"])

    def test_video_qc_checks_duration_resolution_and_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = self._video(root)
            scenes = self._scenes()
            scene_id = scenes[0]["scene_id"]
            imported = import_scene_media(scenes, scene_id, video.name, video.read_bytes(), root / "assets")
            self.assertTrue(imported["ok"])
            record = imported["scenes"][0]["production"]["assets"][0]
            checked = qc_scene_asset(imported["scenes"], scene_id, record["asset_id"])
            self.assertTrue(checked["ok"], checked)
            self.assertTrue(checked["qc_result"]["checks"]["duration"])
            accepted = accept_scene_asset(checked["scenes"], scene_id, record["asset_id"])
            self.assertTrue(accepted["ok"])
            Path(record["path"]).unlink()
            self.assertFalse(inspect_media(record["path"], "video")["ok"])
            self.assertFalse(accept_scene_asset(checked["scenes"], scene_id, record["asset_id"])["ok"])
            missing_qc = qc_scene_asset(accepted["scenes"], scene_id, record["asset_id"])
            self.assertFalse(missing_qc["ok"])
            self.assertEqual(missing_qc["scenes"][0]["production"]["assets"][0]["status"], "Accepted")
            self.assertEqual(missing_qc["scenes"][0]["qc_status"], "Missing Asset")
            timeline = validate_storyboard(accepted["scenes"], 180)
            self.assertTrue(timeline["ok"])
            self.assertEqual(timeline["missing_assets"], [scene_id])
            long_video = self._video(root, "long.mp4", 11)
            bad_duration = import_scene_media(scenes, scene_id, long_video.name, long_video.read_bytes(), root / "assets")
            self.assertTrue(bad_duration["ok"])
            record2 = bad_duration["scenes"][0]["production"]["assets"][0]
            failed = qc_scene_asset(bad_duration["scenes"], scene_id, record2["asset_id"])
            self.assertFalse(failed["ok"])
            self.assertFalse(failed["qc_result"]["checks"]["duration"])

    def test_duration_change_keeps_old_file_but_requires_new_revision_qc(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = self._image(root)
            scenes = self._scenes()
            scene_id = scenes[0]["scene_id"]
            imported = import_scene_media(scenes, scene_id, image.name, image.read_bytes(), root / "assets")
            asset_id = imported["asset_id"]
            checked = qc_scene_asset(imported["scenes"], scene_id, asset_id)
            accepted = accept_scene_asset(checked["scenes"], scene_id, asset_id)
            old_path = accepted["scenes"][0]["asset_path"]
            changed = edit_scene(accepted["scenes"], scene_id, {"duration_seconds": 7.5}, 180)
            self.assertTrue(changed["ok"])
            self.assertEqual(changed["scenes"][0]["qc_status"], "Needs Revision")
            self.assertEqual(changed["scenes"][1]["approval_status"], "Needs Revision")
            approved = edit_scene(changed["scenes"], scene_id, {"approval_status": "Approved"}, 180)
            self.assertFalse(qc_scene_asset(approved["scenes"], scene_id, asset_id)["ok"])
            self.assertEqual(approved["scenes"][0]["asset_path"], old_path)
            self.assertTrue(Path(old_path).is_file())
            self.assertTrue(validate_storyboard(approved["scenes"], 180)["ok"])

    def test_mock_provider_failure_retry_and_asset_preservation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scenes = self._scenes()
            scene_id = scenes[0]["scene_id"]
            other = dict(scenes[1])
            self.assertFalse(begin_generation(scenes, scenes[2]["scene_id"], "image", "openai_images", confirmed=True, configured=True)["ok"])
            self.assertFalse(begin_generation(scenes, scene_id, "image", "openai_images", confirmed=False, configured=True)["ok"])
            begun = begin_generation(scenes, scene_id, "image", "openai_images", confirmed=True, configured=True)
            self.assertTrue(begun["ok"])
            self.assertFalse(begin_generation(begun["scenes"], scene_id, "image", "openai_images", confirmed=True, configured=True)["ok"])
            called = []
            def fallback(provider, prompt, path, settings):
                called.append(scene_id)
                self._image(Path(path).parent, Path(path).name)
                return {"ok": True, "data": {"path": path, "provider_used": "offline", "fallback_used": True}}
            failed = run_generation(begun["scenes"], scene_id, begun["attempt_id"], root / "assets",
                                    {"openai_api_key": "mock-key"}, image_generator=fallback)
            self.assertFalse(failed["ok"])
            self.assertEqual(called, [scene_id])
            self.assertEqual(failed["scenes"][1], other)
            self.assertFalse(failed["scenes"][0].get("asset_path"))
            self.assertEqual(failed["scenes"][0]["production"]["assets"], [])
            retried = request_scene_retry(failed["scenes"], scene_id)
            self.assertTrue(retried["ok"])
            begun2 = begin_generation(retried["scenes"], scene_id, "image", "openai_images", confirmed=True, configured=True)
            self.assertTrue(begun2["ok"])
            def success(provider, prompt, path, settings):
                self._image(Path(path).parent, Path(path).name)
                return {"ok": True, "data": {"path": path, "provider_used": provider, "actual_model": "mock-model", "fallback_used": False}}
            generated = run_generation(begun2["scenes"], scene_id, begun2["attempt_id"], root / "assets",
                                       {"openai_api_key": "mock-key"}, image_generator=success)
            self.assertTrue(generated["ok"], generated)
            record = generated["scenes"][0]["production"]["assets"][0]
            accepted = accept_scene_asset(qc_scene_asset(generated["scenes"], scene_id, record["asset_id"])["scenes"], scene_id, record["asset_id"])
            self.assertTrue(accepted["ok"])
            old_path = accepted["scenes"][0]["asset_path"]
            retry2 = request_scene_retry(accepted["scenes"], scene_id)
            begun3 = begin_generation(retry2["scenes"], scene_id, "image", "openai_images", confirmed=True, configured=True)
            failed_again = run_generation(begun3["scenes"], scene_id, begun3["attempt_id"], root / "assets",
                                          {"openai_api_key": "mock-key"}, image_generator=fallback)
            self.assertFalse(failed_again["ok"])
            self.assertEqual(failed_again["scenes"][0]["asset_path"], old_path)
            self.assertEqual(failed_again["scenes"][0]["production"]["assets"][0]["status"], "Accepted")
            self.assertTrue(Path(old_path).is_file())
            self.assertEqual(failed_again["scenes"][1], other)
            self.assertTrue(validate_storyboard(failed_again["scenes"], 180)["ok"])
            project = {"title": "Retry Test", "workflow_type": "song", "mv": {"full_song": {
                "audio": {"duration_seconds": 180}, "scenes": failed_again["scenes"]}}}
            folder = save_project_folder(project, root / "projects")
            restored = read_project_json(folder / "project.json")
            self.assertTrue(restored["ok"])
            self.assertEqual(restored["project"]["mv"]["full_song"],
                             json.loads((folder / "full_song_scene_manifest.json").read_text(encoding="utf-8")))
            self.assertEqual(len(restored["project"]["mv"]["full_song"]["scenes"][0]["production"]["attempts"]), 3)
            last_retry = request_scene_retry(failed_again["scenes"], scene_id)
            self.assertTrue(last_retry["ok"])
            self.assertFalse(request_scene_retry(last_retry["scenes"], scene_id)["ok"])

    def test_mock_veo_job_creates_reviewable_shot_without_touching_other_scenes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self._video(root)
            scenes = self._scenes()
            other = dict(scenes[1])
            scene_id = scenes[0]["scene_id"]
            begun = begin_generation(scenes, scene_id, "video", "gemini_veo", confirmed=True,
                                     configured=True, shot_duration=5)
            self.assertTrue(begun["ok"])
            def mock_veo(prompt, duration, output, **kwargs):
                self.assertIn("single continuous cinematic video shot", prompt)
                self.assertEqual(duration, 5)
                shutil.copy2(source, output)
                return {"ok": True, "data": {"path": str(output), "provider_status": "complete",
                                             "real_ai_video_used": True, "job_id": "mock-job-1",
                                             "payload": {"model": "mock-veo"}}}
            generated = run_generation(begun["scenes"], scene_id, begun["attempt_id"], root / "assets",
                                       {"gemini_api_key": "mock-key"}, video_generator=mock_veo)
            self.assertTrue(generated["ok"], generated)
            self.assertEqual(generated["scenes"][1], other)
            record = generated["scenes"][0]["production"]["assets"][0]
            self.assertEqual((record["job_id"], record["model"], record["scene_revision"]),
                             ("mock-job-1", "mock-veo", scenes[0]["revision"]))
            self.assertTrue(qc_scene_asset(generated["scenes"], scene_id, record["asset_id"])["ok"])

    def test_provider_claim_without_file_is_not_an_asset(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            scenes = self._scenes()
            scene_id = scenes[0]["scene_id"]
            begun = begin_generation(scenes, scene_id, "image", "openai_images", confirmed=True, configured=True)
            self.assertTrue(begun["ok"])
            def no_file(provider, prompt, path, settings):
                return {"ok": True, "data": {"path": path, "provider_used": provider, "fallback_used": False}}
            result = run_generation(begun["scenes"], scene_id, begun["attempt_id"], Path(temp) / "assets",
                                    {"openai_api_key": "mock-key"}, image_generator=no_file)
            self.assertFalse(result["ok"])
            self.assertEqual(result["scenes"][0]["production"]["assets"], [])
            self.assertEqual(result["scenes"][0]["production"]["attempts"][0]["status"], "Failed")
