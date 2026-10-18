"""Real existing Cut/Join/Remaster functions, confined to generated fixtures."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import core.audio_editor as editor
import core.audio_intelligence as intelligence
import core.remaster_engine as master
from core.real_clip_pipeline import find_ffmpeg, probe_media
from qa_support import tone


class AudioPipelineRegressionTests(unittest.TestCase):
    def test_cut_join_remaster_preserve_sources(self):
        with tempfile.TemporaryDirectory(prefix='vela-pipeline-') as tmp:
            root = Path(tmp)
            a = tone(root / 'a.wav', duration=4)
            b = tone(root / 'b.wav', duration=3, frequency=880)
            hashes = [hashlib.sha256(p.read_bytes()).hexdigest() for p in (a, b)]
            ffmpeg = find_ffmpeg()
            with patch.object(editor, 'ROOT', root), patch.object(master, 'ROOT', root), \
                    patch.object(intelligence, 'DEFAULT_CACHE_ROOT', root / 'cache'):
                cut = editor.export_audio_selection(a, start_time=1, end_time=3, cut_mode='Precise Cut',
                                                     output_format='wav', ffmpeg_path=ffmpeg)
                self.assertTrue(cut['ok'], cut)
                self.assertAlmostEqual(probe_media(cut['data']['output_audio'], ffmpeg_path=ffmpeg)['duration'], 2, places=2)
                tracks = [{'path': str(p), 'start': 0, 'end': duration} for p, duration in ((a, 4), (b, 3))]
                joined = editor.join_audio_tracks(tracks, output_format='wav', output_dir=root / 'joined', ffmpeg_path=ffmpeg)
                self.assertTrue(joined['ok'], joined)
                self.assertAlmostEqual(joined['data']['output_duration'], 7, places=2)
                remastered = master.remaster_song_audio(a, project_name='QA synthetic master', ffmpeg_path=ffmpeg)
                self.assertTrue(remastered['ok'], remastered)
                self.assertEqual(remastered['data']['report']['output_validation']['overall_status'], 'success')
                self.assertLessEqual(remastered['data']['report']['peak_result'], -1)
            self.assertEqual(hashes, [hashlib.sha256(p.read_bytes()).hexdigest() for p in (a, b)])
