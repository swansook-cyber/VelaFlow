from __future__ import annotations

import base64
import hashlib
import io
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from core.full_song_mv import create_full_song_storyboard
from core.full_song_mv_production import (
    begin_generation, load_character_references, qc_scene_asset, request_scene_retry, run_generation,
    generate_scene_010_concept_preview, SCENE_010_CONCEPT_PROMPT,
)
from core.project_io import new_project, read_project_json, save_project_folder
from providers.image_ai import _openai_image, generate_image_with_diagnostics


class CharacterReferenceTests(unittest.TestCase):
    def _reference(self, root: Path) -> dict:
        folder = root / "assets" / "character_references" / "vela_moon_master_v1_0"
        folder.mkdir(parents=True)
        images = {}
        for n in range(1, 5):
            name = f"0{n}_view.png"
            path = folder / name
            Image.new("RGB", (64, 64), (n * 30, 50, 80)).save(path)
            data = path.read_bytes()
            images[name] = {"path": str(path), "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                            "width": 64, "height": 64}
        return {"character_name": "Vela Moon", "version": "1.0", "source_zip_sha256": "source-v1",
                "creative_design_status": "Approved by User", "reference_asset_status": "Imported / Pending Technical Validation",
                "images": images}

    def _scenes(self) -> list[dict]:
        scenes = create_full_song_storyboard({}, {"title": "Test"}, 120, 20)["scenes"]
        scenes[9]["approval_status"] = "Approved"
        return scenes

    def test_concept_preview_is_separate_from_planned_scene_and_restores(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            record = self._reference(root)
            project = new_project("Concept Preview Test", "Vela Moon")
            project["assets"]["character_references"] = {"vela_moon_master_v1_0": record}
            scenes = create_full_song_storyboard({}, project, 120, 20)["scenes"]
            project["mv"]["full_song"] = {"scenes": scenes, "audio": {"duration_seconds": 120}}
            before = deepcopy(project)
            with patch("core.full_song_mv_production.generate_image_with_diagnostics") as provider:
                dry = generate_scene_010_concept_preview(root, record)
            provider.assert_not_called()
            self.assertTrue(dry["ok"], dry)
            self.assertTrue(dry["dry_run"])
            self.assertEqual(dry["plan"]["reference_count"], 4)
            self.assertEqual(dry["plan"]["prompt"], SCENE_010_CONCEPT_PROMPT)
            self.assertFalse((root / "assets" / "concept_previews").exists())
            self.assertFalse(generate_scene_010_concept_preview(root, record, dry_run=False)["ok"])

            def fake(provider, prompt, path, settings):
                self.assertEqual(provider, "openai_images")
                self.assertEqual(prompt, SCENE_010_CONCEPT_PROMPT)
                self.assertEqual(settings["openai_image_model"], "gpt-image-2.6-sunburst")
                self.assertEqual(settings["size"], "1536x864")
                self.assertEqual(settings["quality"], "medium")
                refs = settings["reference_images"]
                self.assertEqual(len(refs), 4)
                for item in refs:
                    self.assertTrue(item["content"].startswith(b"\x89PNG"))
                    self.assertEqual(hashlib.sha256(item["content"]).hexdigest(), item["sha256"])
                image_path = Path(path)
                image_path.parent.mkdir(parents=True)
                Image.new("RGB", (1536, 864), "#334455").save(image_path)
                return {"ok": True, "data": {"path": str(image_path), "fallback_used": False,
                        "reference_sent_to_provider": True,
                        "reference_sha256s": [item["sha256"] for item in refs]}}

            result = generate_scene_010_concept_preview(root, record, api_key="mock-only", confirmed=True,
                                                        dry_run=False, image_generator=fake)
            self.assertTrue(result["ok"], result)
            self.assertTrue(Path(result["path"]).is_relative_to(root / "assets" / "concept_previews" / "scene_010"))
            self.assertFalse(result["scene_asset_created"])
            self.assertEqual(project, before)
            self.assertEqual(scenes[9]["approval_status"], "Planned")
            self.assertEqual(scenes[9]["revision"], before["mv"]["full_song"]["scenes"][9]["revision"])
            self.assertNotIn("production", scenes[9])
            folder = save_project_folder(project, root / "projects")
            restored = read_project_json(folder / "project.json")
            self.assertTrue(restored["ok"])
            self.assertEqual(restored["project"]["mv"]["full_song"], before["mv"]["full_song"])
            self.assertEqual(restored["project"]["assets"]["character_references"]["vela_moon_master_v1_0"], record)

    def test_concept_preview_rejects_changed_reference_before_request(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            record = self._reference(root)
            next(iter(record["images"].values()))["sha256"] = "0" * 64
            with patch("core.full_song_mv_production.generate_image_with_diagnostics") as provider:
                result = generate_scene_010_concept_preview(root, record, api_key="mock-only", confirmed=True,
                                                            dry_run=False)
            provider.assert_not_called()
            self.assertFalse(result["ok"])
            self.assertFalse((root / "assets" / "concept_previews").exists())

    def test_reference_payload_retry_restore_and_qc_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            record = self._reference(root)
            checked = load_character_references(record, root)
            self.assertTrue(checked["ok"], checked)
            self.assertEqual(len(checked["images"]), 4)
            scenes = self._scenes()
            before = deepcopy(scenes)
            scene_id = scenes[9]["scene_id"]
            begun = begin_generation(scenes, scene_id, "image", "openai_images", confirmed=True, configured=True,
                                     reference_record=record, reference_root=root)
            self.assertTrue(begun["ok"], begun)
            self.assertIn("Wardrobe Look B", begun["scenes"][9]["production"]["attempts"][0]["prompt_used"])

            seen = []
            def fake(provider, prompt, path, settings):
                images = settings["reference_images"]
                self.assertEqual(provider, "openai_images")
                self.assertEqual(settings["target_aspect_ratio"], "16:9")
                self.assertEqual(len(images), 4)
                for item in images:
                    self.assertTrue(item["content"].startswith(b"\x89PNG"))
                    self.assertEqual(hashlib.sha256(item["content"]).hexdigest(), item["sha256"])
                seen.extend(item["sha256"] for item in images)
                Image.new("RGB", (1536, 864), "#334455").save(path)
                return {"ok": True, "data": {"path": path, "provider_used": provider,
                        "fallback_used": False, "reference_sent_to_provider": True,
                        "reference_sha256s": seen.copy(), "actual_model": "mock-image"}}

            generated = run_generation(begun["scenes"], scene_id, begun["attempt_id"], root / "output",
                                       {"openai_api_key": "mock-only", "target_aspect_ratio": "16:9"}, image_generator=fake)
            self.assertTrue(generated["ok"], generated)
            result_scene = generated["scenes"][9]
            self.assertEqual(result_scene["approval_status"], "Approved")
            self.assertEqual(result_scene["production"]["assets"][0]["status"], "Needs QC")
            self.assertTrue(result_scene["production"]["assets"][0]["reference_sent_to_provider"])
            qc = qc_scene_asset(generated["scenes"], scene_id, generated["asset_id"], "16:9")
            self.assertTrue(qc["ok"], qc)
            self.assertFalse(qc["scenes"][9]["production"]["assets"][0]["qc_result"]["human_accepted"])
            self.assertEqual(generated["scenes"][8], before[8])

            project = new_project("Reference Restore", "Vela Moon")
            project["assets"]["character_references"] = {"vela_moon_master_v1_0": record}
            project["mv"]["full_song"] = {"scenes": generated["scenes"], "audio": {"duration_seconds": 120}}
            folder = save_project_folder(project, root / "projects")
            restored = read_project_json(folder / "project.json")
            self.assertTrue(restored["ok"])
            self.assertEqual(restored["project"]["assets"]["character_references"]["vela_moon_master_v1_0"], record)
            self.assertEqual(restored["project"]["mv"]["full_song"]["scenes"][9]["production"]["attempts"][0]["reference_snapshot"]["version"], "1.0")

            retry = request_scene_retry(generated["scenes"], scene_id)
            self.assertTrue(retry["ok"], retry)
            altered = deepcopy(record)
            altered["source_zip_sha256"] = "source-v2"
            self.assertFalse(begin_generation(retry["scenes"], scene_id, "image", "openai_images", confirmed=True,
                                              configured=True, reference_record=altered, reference_root=root)["ok"])
            again = begin_generation(retry["scenes"], scene_id, "image", "openai_images", confirmed=True,
                                     configured=True, reference_record=record, reference_root=root)
            self.assertTrue(again["ok"], again)
            self.assertEqual(again["scenes"][9]["production"]["attempts"][-1]["reference_snapshot"]["version"], "1.0")

    def test_missing_corrupt_and_escaped_paths_stop_before_provider(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            record = self._reference(root)
            scenes = self._scenes()
            scene_id = scenes[9]["scene_id"]
            for changed in ("missing", "sha", "outside", "mime"):
                candidate = deepcopy(record)
                first = next(iter(candidate["images"].values()))
                if changed == "missing":
                    first["path"] = str(root / "missing.png")
                elif changed == "sha":
                    first["sha256"] = "0" * 64
                elif changed == "outside":
                    first["path"] = str(Path(__file__).resolve())
                else:
                    first["width"] = 999
                self.assertFalse(load_character_references(candidate, root)["ok"], changed)
                self.assertFalse(begin_generation(scenes, scene_id, "image", "openai_images", confirmed=True,
                                                  configured=True, reference_record=candidate, reference_root=root)["ok"])
            self.assertFalse(begin_generation(scenes, scene_id, "image", "gemini_image", confirmed=True,
                                              configured=True, reference_record=record, reference_root=root)["ok"])
            self.assertEqual(scenes[9]["approval_status"], "Approved")
            self.assertNotIn("production", scenes[9])

    def test_reference_changed_after_confirmation_never_calls_provider(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            record = self._reference(root)
            scenes = self._scenes()
            scene_id = scenes[9]["scene_id"]
            begun = begin_generation(scenes, scene_id, "image", "openai_images", confirmed=True,
                                     configured=True, reference_record=record, reference_root=root)
            self.assertTrue(begun["ok"])
            first = next(iter(record["images"].values()))
            Path(first["path"]).write_bytes(b"changed")
            with patch("core.full_song_mv_production.generate_image_with_diagnostics") as provider:
                result = run_generation(begun["scenes"], scene_id, begun["attempt_id"], root / "output",
                                        {"openai_api_key": "mock-only"}, image_generator=provider)
            provider.assert_not_called()
            self.assertFalse(result["ok"])
            self.assertEqual(result["error"], "reference_validation_failed")
            self.assertEqual(result["scenes"][9]["approval_status"], "Approved")
            self.assertEqual(result["scenes"][9]["production"]["assets"], [])

    def test_openai_adapter_sends_four_real_multipart_images(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            refs = load_character_references(self._reference(root), root)["images"]
            image = io.BytesIO()
            Image.new("RGB", (64, 64), "#334455").save(image, format="PNG")
            response_data = {"data": [{"b64_json": base64.b64encode(image.getvalue()).decode("ascii")}]}
            class FakeResponse:
                def raise_for_status(self): pass
                def json(self): return response_data
            with patch("providers.image_ai.requests.post", return_value=FakeResponse()) as post:
                path, model = _openai_image("test", root / "edited.raw", {"openai_api_key": "mock-only",
                       "openai_image_model": "gpt-image-1.5", "strict_image_model": True, "size": "1536x1024",
                       "reference_images": refs})
            self.assertEqual(model, "gpt-image-1.5")
            self.assertTrue(Path(path).is_file())
            args, kwargs = post.call_args
            self.assertEqual(args[0], "https://api.openai.com/v1/images/edits")
            self.assertNotIn("json", kwargs)
            self.assertEqual(len(kwargs["files"]), 4)
            self.assertEqual([part[1][1] for part in kwargs["files"]], [item["content"] for item in refs])
            self.assertEqual(kwargs["data"]["size"], "1536x1024")
            self.assertEqual(kwargs["data"]["input_fidelity"], "high")
            unsupported = generate_image_with_diagnostics("gemini_image", "test", str(root / "unsupported.jpg"),
                                                           {"reference_images": refs})
            self.assertFalse(unsupported["ok"])
            self.assertFalse(unsupported["data"]["reference_sent_to_provider"])

    def test_reference_diagnostic_returns_landscape_without_text_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            refs = load_character_references(self._reference(root), root)["images"]
            image = io.BytesIO()
            Image.new("RGB", (1536, 1024), "#334455").save(image, format="PNG")
            response_data = {"data": [{"b64_json": base64.b64encode(image.getvalue()).decode("ascii")}]}
            class FakeResponse:
                def raise_for_status(self): pass
                def json(self): return response_data
            with patch("providers.image_ai.requests.post", return_value=FakeResponse()) as post:
                result = generate_image_with_diagnostics("openai_images", "cinematic band performance",
                         str(root / "scene.jpg"), {"openai_api_key": "mock-only", "openai_image_model": "gpt-image-1.5",
                         "strict_image_model": True, "reference_images": refs,
                         "size": "1536x1024", "target_aspect_ratio": "16:9"})
            self.assertTrue(result["ok"], result)
            self.assertTrue(result["data"]["reference_sent_to_provider"])
            self.assertEqual(result["data"]["reference_sha256s"], [item["sha256"] for item in refs])
            self.assertEqual(post.call_args.args[0], "https://api.openai.com/v1/images/edits")
            with Image.open(result["data"]["path"]) as output:
                self.assertEqual(output.size, (1536, 864))
            sidecar = (root / "scene.json").read_text(encoding="utf-8")
            self.assertNotIn("mock-only", sidecar)
            self.assertNotIn("reference_images", sidecar)

    def test_sunburst_keeps_four_views_and_direct_16_by_9(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            refs = load_character_references(self._reference(root), root)["images"]
            image = io.BytesIO()
            Image.new("RGB", (1536, 864), "#334455").save(image, format="PNG")
            response_data = {"data": [{"b64_json": base64.b64encode(image.getvalue()).decode("ascii")}]}
            class FakeResponse:
                def raise_for_status(self): pass
                def json(self): return response_data
            with patch("providers.image_ai.requests.post", return_value=FakeResponse()) as post:
                result = generate_image_with_diagnostics("openai_images", "band performance",
                    str(root / "scene.jpg"), {"openai_api_key": "mock-only",
                    "openai_image_model": "gpt-image-2.6-sunburst", "strict_image_model": True,
                    "reference_images": refs, "size": "1536x864", "target_aspect_ratio": "16:9"})
            self.assertTrue(result["ok"], result)
            self.assertEqual(post.call_count, 1)
            self.assertEqual(len(post.call_args.kwargs["files"]), 4)
            self.assertEqual(post.call_args.kwargs["data"]["size"], "1536x864")
            self.assertNotIn("input_fidelity", post.call_args.kwargs["data"])
            self.assertEqual(result["data"]["reference_sha256s"], [item["sha256"] for item in refs])
            with Image.open(result["data"]["path"]) as output:
                self.assertEqual(output.size, (1536, 864))

    def test_sunburst_rejects_unexpected_size_without_cropping(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            refs = load_character_references(self._reference(root), root)["images"]
            image = io.BytesIO()
            Image.new("RGB", (1536, 1024), "#334455").save(image, format="PNG")
            response_data = {"data": [{"b64_json": base64.b64encode(image.getvalue()).decode("ascii")}]}
            class FakeResponse:
                def raise_for_status(self): pass
                def json(self): return response_data
            with patch("providers.image_ai.requests.post", return_value=FakeResponse()):
                result = generate_image_with_diagnostics("openai_images", "band performance",
                    str(root / "scene.jpg"), {"openai_api_key": "mock-only",
                    "openai_image_model": "gpt-image-2.6-sunburst", "strict_image_model": True,
                    "reference_images": refs, "size": "1536x864", "target_aspect_ratio": "16:9"})
            self.assertFalse(result["ok"])
            self.assertEqual(result["error"], "unexpected_image_dimensions")
            self.assertFalse((root / "scene.jpg").exists())

    def test_reference_provider_error_does_not_retry_models_or_make_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            refs = load_character_references(self._reference(root), root)["images"]
            with patch("providers.image_ai.requests.post", side_effect=RuntimeError("mock provider failure")) as post:
                result = generate_image_with_diagnostics("openai_images", "test", str(root / "failed.jpg"),
                        {"openai_api_key": "mock-only", "openai_image_model": "gpt-image-1.5",
                         "reference_images": refs, "size": "1536x1024", "target_aspect_ratio": "16:9"})
            self.assertFalse(result["ok"])
            self.assertEqual(post.call_count, 1)
            self.assertFalse((root / "failed.jpg").exists())
            self.assertFalse(result["data"]["reference_sent_to_provider"])


if __name__ == "__main__":
    unittest.main()
