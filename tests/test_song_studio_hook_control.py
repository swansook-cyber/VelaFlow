"""Offline regression tests for Creator Mode saved hook control and editor safety."""
from __future__ import annotations

import unittest

from core.song_editor_state import (
    commit_song_editor_values,
    resolve_song_editor_values,
    song_editor_dirty_fields,
    stage_song_editor_draft,
)
from core.song_workflow import choose_existing_hook


class SongStudioHookControlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.hooks = [
            {"hook_text": "ปล่อยก็เจ็บ รั้งก็ปวด", "catchy_score": 85},
            {"hook_text": "จะอยู่ก็ปวด จะไปก็เจ็บ", "catchy_score": 72},
        ]

    def test_selects_explicit_hook_without_rewriting_candidates(self) -> None:
        selected = choose_existing_hook(self.hooks, 1)
        self.assertEqual(selected["hook_text"], self.hooks[1]["hook_text"])
        selected["hook_text"] = "edited"
        self.assertNotEqual(selected["hook_text"], self.hooks[1]["hook_text"])

    def test_invalid_selection_does_not_choose_a_hook(self) -> None:
        for index in (-1, 2, None, True, "0"):
            self.assertIsNone(choose_existing_hook(self.hooks, index))
        self.assertIsNone(choose_existing_hook([{"hook_text": "   "}], 0))

    def test_draft_remains_recoverable_until_explicit_commit(self) -> None:
        song = {
            "complete_lyrics": "[Chorus]\nคำเดิม",
            "normalized_song_output": "[Chorus]\nคำเดิม",
            "music_style_prompt": "Thai pop",
            "selected_hook_text": "คำเดิม",
            "hook_candidates": self.hooks,
        }
        staged = stage_song_editor_draft(song, "[Chorus]\nแก้เอง", "Pop rock")
        self.assertEqual(song["complete_lyrics"], "[Chorus]\nคำเดิม")
        self.assertEqual(staged["complete_lyrics"], "[Chorus]\nคำเดิม")
        self.assertEqual(resolve_song_editor_values(staged)["lyrics"], "[Chorus]\nแก้เอง")
        self.assertEqual(set(song_editor_dirty_fields(staged, "[Chorus]\nแก้เอง", "Pop rock")), {"lyrics", "style_prompt"})
        committed = commit_song_editor_values(staged, "[Chorus]\nแก้เอง", "Pop rock")
        self.assertNotIn("creator_editor_draft", committed)
        self.assertEqual(committed["selected_hook_text"], "คำเดิม")
        self.assertEqual(committed["complete_lyrics"], "[Chorus]\nแก้เอง")


if __name__ == "__main__":
    unittest.main()
