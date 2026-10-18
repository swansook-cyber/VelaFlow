import io
import subprocess
import tempfile
import threading
import tracemalloc
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core.stem_mixer import MAX_STEM_BYTES
from core.stem_uploads import DOWNLOADS, DownloadStore, render_uploaded_stems
from qa_support import tone


class Upload(io.BytesIO):
    def __init__(self, path):
        super().__init__(Path(path).read_bytes())
        self.name = Path(path).name
        self.size = len(self.getbuffer())


class UploadTests(unittest.TestCase):
    def test_success_silence_repeated_export_cleanup_and_ffprobe(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scratch = root / 'scratch'
            scratch.mkdir()
            unrelated = scratch / 'existing-user-export.wav'
            unrelated.write_bytes(b'preserve')
            vocal = Upload(tone(root / 'v.wav', duration=2, silent=True))
            music = Upload(tone(root / 'i.wav', duration=3, silent=True))
            for _ in range(3):
                result = render_uploaded_stems(vocal, music, scratch_root=scratch)
                self.assertTrue(result['ok'], result)
                self.assertNotIn('path', result)
                self.assertEqual(result['probe']['codec_name'], 'pcm_s24le')
                self.assertEqual(int(result['probe']['bits_per_raw_sample']), 24)
                self.assertEqual(result['probe']['duration'], 3)
                self.assertTrue(result['measurement']['effectively_silent'])
                self.assertIsNone(result['measurement']['integrated_lufs'])
                self.assertEqual(result['measurement']['rail_hits'], 0)
                self.assertEqual(list(scratch.iterdir()), [unrelated])
            self.assertEqual(unrelated.read_bytes(), b'preserve')

    def test_corrupt_oversize_duration_and_timeout_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scratch = root / 'scratch'
            scratch.mkdir()
            good = Upload(tone(root / 'good.wav'))
            bad_path = root / 'bad.wav'
            bad_path.write_bytes(b'not audio')
            self.assertFalse(render_uploaded_stems(good, Upload(bad_path), scratch_root=scratch)['ok'])
            good.size = MAX_STEM_BYTES + 1
            with patch.object(good, 'getbuffer', side_effect=AssertionError('must reject before reading')):
                self.assertFalse(render_uploaded_stems(good, good, scratch_root=scratch)['ok'])
            good.size = len(good.getbuffer())
            with patch('core.stem_mixer.MAX_DURATION_SECONDS', 1):
                self.assertFalse(render_uploaded_stems(good, good, scratch_root=scratch)['ok'])
            # Allow FFprobe, then force an actual render timeout at the subprocess boundary.
            real_run = subprocess.run
            def timeout_render(args, **kwargs):
                if '-filter_complex' in args:
                    Path(args[-1]).write_bytes(b'partial output')
                    raise subprocess.TimeoutExpired(args, 180)
                return real_run(args, **kwargs)
            with patch('core.stem_mixer.subprocess.run', side_effect=timeout_render):
                self.assertFalse(render_uploaded_stems(good, good, scratch_root=scratch)['ok'])
            self.assertEqual(list(scratch.iterdir()), [])

    def test_two_concurrent_sessions_and_third_busy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scratch = root / 'scratch'
            scratch.mkdir()
            upload = Upload(tone(root / 'tone.wav'))
            barrier = threading.Barrier(3)
            release = threading.Event()
            folders = []
            def blocked_mix(v, i, folder, **kwargs):
                folders.append(Path(folder))
                barrier.wait(timeout=10)
                release.wait(timeout=10)
                return {'ok': False, 'error': 'synthetic render failure'}
            with patch('core.stem_uploads.mix_stems', side_effect=blocked_mix), ThreadPoolExecutor(2) as pool:
                jobs = [pool.submit(render_uploaded_stems, upload, upload, scratch_root=scratch) for _ in range(2)]
                try:
                    barrier.wait(timeout=10)
                    busy = render_uploaded_stems(upload, upload, scratch_root=scratch)
                    self.assertIn('already processing', busy['error'])
                finally:
                    release.set()
                for job in jobs:
                    self.assertFalse(job.result()['ok'])
            self.assertEqual(len(set(folders)), 2)
            self.assertEqual(list(scratch.iterdir()), [])

    def test_bounded_download_memory_and_owner_isolation(self):
        clock = [0]
        store = DownloadStore(max_bytes=10, max_entries=2, ttl=5, clock=lambda: clock[0])
        token = store.put('session-a', b'12345')
        self.assertIsNone(store.get('session-b', token))
        self.assertEqual(store.get('session-a', token), b'12345')
        store.put('session-b', b'67890')
        with self.assertRaises(ValueError):
            store.put('session-c', b'!')
        with self.assertRaises(ValueError):
            store.put('session-a', b'x' * 11)
        self.assertIsNotNone(store.get('session-a', token))
        new = store.put('session-a', b'x')
        self.assertIsNone(store.get('session-a', token))
        store.discard('session-b')
        self.assertIsNotNone(store.get('session-a', new))
        clock[0] = 5
        self.assertIsNone(store.get('session-a', new))

    def test_low_disk_and_io_failure_leave_no_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            upload = Upload(tone(root / 'tone.wav'))
            scratch = root / 'scratch'
            scratch.mkdir()
            with patch('core.stem_uploads.shutil.disk_usage', return_value=SimpleNamespace(free=0)):
                self.assertIn('disk space', render_uploaded_stems(upload, upload, scratch_root=scratch)['error'])
            with patch.object(upload, 'getbuffer', side_effect=OSError('synthetic read failure')):
                self.assertFalse(render_uploaded_stems(upload, upload, scratch_root=scratch)['ok'])
            self.assertEqual(list(scratch.iterdir()), [])

    def test_uploaded_filename_cannot_select_a_disk_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            upload = Upload(tone(root / 'tone.wav'))
            upload.name = '../../do-not-write-here.wav'
            scratch = root / 'scratch'
            scratch.mkdir()
            result = render_uploaded_stems(upload, upload, scratch_root=scratch)
            self.assertTrue(result['ok'], result)
            self.assertEqual(list(scratch.iterdir()), [])
            self.assertFalse((root / 'do-not-write-here.wav').exists())

    def test_upload_buffer_is_not_copied_before_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            upload = Upload(tone(root / 'tone.wav'))
            # A 16 MiB synthetic export isolates Python allocation cost from external FFmpeg.
            def fake_mix(v, i, folder, **kwargs):
                output = Path(folder) / 'synthetic.wav'
                with output.open('wb') as f:
                    for _ in range(16):
                        f.write(b'x' * (1024 * 1024))
                return {'ok': True, 'path': str(output)}
            tracemalloc.start()
            try:
                with patch('core.stem_uploads.mix_stems', side_effect=fake_mix):
                    result = render_uploaded_stems(upload, upload, scratch_root=root)
                _, peak = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
            self.assertTrue(result['ok'])
            self.assertLess(peak, 20 * 1024 * 1024)
            print(f'Python allocation peak for 16 MiB synthetic export: {peak} bytes')
