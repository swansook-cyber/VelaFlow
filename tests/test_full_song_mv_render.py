from __future__ import annotations

import copy
import json
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from PIL import Image

from core.full_song_mv import create_full_song_storyboard, probe_song_audio
from core.full_song_mv_production import _digest, import_scene_media, inspect_media, qc_scene_asset
from core.full_song_mv_render import prepare_full_song_render, render_full_song
from core.render_engine import _scene_cache_key
from core.render_profiles import get_render_profile


def make_project(root: Path, duration: int) -> dict:
    audio = root / "song.mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=16000",
                    "-t", str(duration), "-c:a", "libmp3lame", "-q:a", "8", str(audio)], check=True)
    image = root / "landscape.png"
    Image.new("RGB", (1280, 720), "#345678").save(image)
    video = root / "shot.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=blue:s=854x480:r=8",
                    "-t", "3", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video)], check=True)
    project = {"title": "Synthetic full song", "mv": {}}
    measured_duration = probe_song_audio(audio)["duration_seconds"]
    scenes = create_full_song_storyboard({}, project, measured_duration, 2)["scenes"]
    for index, scene in enumerate(scenes):
        scene["approval_status"] = "Approved"
        paths = [video, image] if index == 0 else [image]
        assets = []
        for shot, path in enumerate(paths):
            kind = "video" if path == video else "image"
            media = inspect_media(path, kind)
            record = {"asset_id": f"asset_{index}_{shot}", "scene_id": scene["scene_id"],
                      "scene_revision": scene["revision"], "qc_revision": scene["revision"],
                      "kind": kind, "path": str(path), "provider": "external_import",
                      "provider_status": "imported", "status": "Accepted",
                      "shot_duration_seconds": 3 if kind == "video" else 0,
                      "qc_result": {"passed": True, "human_accepted": True, "file_sha256": _digest(path),
                                    "target_aspect_ratio": "16:9"}, **{key: media[key] for key in ("width", "height", "aspect_ratio", "duration_seconds")}}
            assets.append(record)
        scene["production"] = {"assets": assets, "active_asset_id": assets[-1]["asset_id"],
                               "render_asset_ids": [row["asset_id"] for row in assets]}
        scene["asset_path"] = assets[-1]["path"]
    project["mv"]["full_song"] = {"audio": {"path": str(audio), "duration_seconds": measured_duration},
                                    "scenes": scenes, "target_aspect_ratio": "16:9"}
    return project


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg tools required")
class FullSongRenderTests(unittest.TestCase):
    def test_preflight_180_240_and_rejections(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for duration in (180, 240):
                project = make_project(root, duration)
                ready = prepare_full_song_render(project)
                self.assertTrue(ready["ok"], ready)
                self.assertEqual(ready["scene_count"], 2)
                self.assertEqual(len(ready["timeline"]), 3)
                self.assertAlmostEqual(ready["timeline"][-1]["end_time"], ready["duration_seconds"], places=2)
                self.assertFalse(any(row["source_type"] == "placeholder" for row in ready["timeline"]))
                scenes = project["mv"]["full_song"]["scenes"]
                changed = copy.deepcopy(project)
                changed["mv"]["full_song"]["scenes"][1]["approval_status"] = "Needs Revision"
                self.assertEqual(prepare_full_song_render(changed)["missing_scenes"][0]["scene_id"], scenes[1]["scene_id"])
                changed = copy.deepcopy(project)
                changed["mv"]["full_song"]["scenes"][0]["production"]["assets"][0]["qc_revision"] = 0
                self.assertIn("stale", prepare_full_song_render(changed)["missing_scenes"][0]["reason"])
                changed = copy.deepcopy(project)
                changed["mv"]["full_song"]["scenes"][0]["production"]["assets"][0]["path"] = str(root / "missing.mp4")
                self.assertIn("missing", prepare_full_song_render(changed)["missing_scenes"][0]["reason"])
                changed = copy.deepcopy(project)
                changed["mv"]["full_song"]["scenes"][0]["production"]["render_asset_ids"] = ["asset_0_0"]
                self.assertIn("shorter", prepare_full_song_render(changed)["missing_scenes"][0]["reason"])
                changed["mv"]["full_song"]["scenes"][0]["production"]["hold_last_frame"] = True
                self.assertEqual(prepare_full_song_render(changed)["timeline"][0]["video_fill_mode"], "hold")
                changed["mv"]["full_song"]["scenes"][0]["production"].pop("hold_last_frame")
                changed["mv"]["full_song"]["scenes"][0]["production"]["allow_video_loop"] = True
                self.assertEqual(prepare_full_song_render(changed)["timeline"][0]["video_fill_mode"], "loop")
                self.assertEqual(scenes[0]["production"]["assets"][0]["qc_result"]["file_sha256"], _digest(root / "shot.mp4"))

    def test_landscape_qc_and_cache_asset_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = make_project(Path(temp), 180)
            scenes = project["mv"]["full_song"]["scenes"]
            item = prepare_full_song_render(project)["timeline"][0]
            asset = scenes[1]["production"]["assets"][0]
            asset["status"] = "Needs QC"
            qc = qc_scene_asset(scenes, scenes[1]["scene_id"], asset["asset_id"], "16:9")
            self.assertTrue(qc["ok"], qc)
            self.assertEqual(qc["qc_result"]["target_aspect_ratio"], "16:9")
            imported = import_scene_media(scenes, scenes[0]["scene_id"], "shot.mp4",
                                          (Path(temp) / "shot.mp4").read_bytes(), Path(temp) / "imports")
            self.assertTrue(imported["ok"])
            self.assertTrue(qc_scene_asset(imported["scenes"], scenes[0]["scene_id"], imported["asset_id"], "16:9")["ok"])
            key = _scene_cache_key(item, "16:9", 320, 180, 8, get_render_profile("Draft"))
            self.assertNotEqual(key, _scene_cache_key({**item, "asset_sha256": "changed"}, "16:9", 320, 180, 8, get_render_profile("Draft")))

    def test_real_180_second_mp4(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = make_project(root, 180)
            before = copy.deepcopy(project["mv"]["full_song"]["scenes"])
            started = time.perf_counter()
            result = render_full_song(project, options={"base_dir": root / "renders", "render_profile": "Draft",
                                                        "scale_factor": 1 / 6, "fps": 8})
            elapsed = time.perf_counter() - started
            self.assertTrue(result["ok"], result.get("error") or result)
            qc = result["final_qc"]
            self.assertEqual((qc["width"], qc["height"]), (320, 180))
            self.assertTrue(all(qc["checks"].values()), qc)
            self.assertEqual(project["mv"]["full_song"]["scenes"], before)
            timeline = json.loads(Path(result["data"]["timeline_path"]).read_text(encoding="utf-8"))["items"]
            self.assertEqual([row["parent_scene_id"] for row in timeline], ["scene_001", "scene_001", "scene_002"])
            manifest = json.loads(Path(result["data"]["manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["render_status"], "DONE")
            self.assertTrue(Path(result["data"]["outputs"]["16:9"]).is_file())
            temporary_bytes = sum(path.stat().st_size for path in (root / "renders").rglob("*") if path.is_file())
            print("SYNTHETIC_RENDER_METRICS=" + json.dumps({"seconds": round(elapsed, 2),
                  "output_bytes": qc["size_bytes"], "temporary_bytes": temporary_bytes,
                  "duration_seconds": qc["duration_seconds"], "audio_duration_seconds": qc["audio_duration_seconds"],
                  "width": qc["width"], "height": qc["height"],
                  "video_codec": qc["video_codec"], "audio_codec": qc["audio_codec"]}))


if __name__ == "__main__":
    unittest.main()
