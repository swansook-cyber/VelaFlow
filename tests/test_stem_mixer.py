"""Real FFmpeg checks for optional stem mixing, plus input validation."""
import hashlib
import math
import shutil
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

from core.stem_mixer import build_stem_mix_filter, mix_stems


class StemMixTests(unittest.TestCase):
    def test_invalid_gains(self):
        for gain in (float('nan'), float('inf'), -25, 7):
            with self.assertRaises(ValueError):
                build_stem_mix_filter(gain, 0)

    def test_missing_inputs(self):
        self.assertFalse(mix_stems('missing.wav', 'missing.mp3', '.')['ok'])

    @unittest.skipUnless(shutil.which('ffmpeg'), 'FFmpeg required')
    def test_overloaded_stems_are_limited_and_corrupt_input_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'hot.wav'
            subprocess.run([shutil.which('ffmpeg'), '-v', 'error', '-f', 'lavfi', '-i',
                            'sine=frequency=997:duration=2', '-af', 'volume=7',
                            '-c:a', 'pcm_s24le', str(source)], check=True)
            result = mix_stems(source, source, root / 'out', vocal_db=6, instrumental_db=6)
            self.assertTrue(result['ok'], result)
            self.assertEqual(result['measurement']['rail_hits'], 0)
            self.assertLessEqual(result['measurement']['true_peak_dbtp'], -1)
            bad = root / 'corrupt.wav'
            bad.write_bytes(b'not audio')
            self.assertFalse(mix_stems(source, bad, root / 'out')['ok'])

    @unittest.skipUnless(shutil.which('ffmpeg'), 'FFmpeg required')
    def test_real_mix_export_and_source_preservation(self):
        ffmpeg = shutil.which('ffmpeg')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = []
            for index, (frequency, duration) in enumerate(((440, 2), (880, 3))):
                path = root / f'{index}.wav'
                subprocess.run([ffmpeg, '-v', 'error', '-f', 'lavfi', '-i',
                                f'sine=frequency={frequency}:duration={duration}',
                                '-c:a', 'pcm_s24le', str(path)], check=True)
                paths.append(path)
            before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
            result = mix_stems(*paths, root / 'out')
            self.assertTrue(result['ok'], result)
            data = Path(result['path']).read_bytes()
            self.assertEqual(data[:4], b'RIFF')
            self.assertEqual(data[8:12], b'WAVE')
            fmt = data.index(b'fmt ')
            self.assertEqual(struct.unpack_from('<H', data, fmt + 10)[0], 2)
            self.assertEqual(struct.unpack_from('<I', data, fmt + 12)[0], 48000)
            self.assertEqual(struct.unpack_from('<H', data, fmt + 22)[0], 24)
            pcm = subprocess.run([ffmpeg, '-v', 'error', '-i', result['path'],
                                  '-f', 'f32le', '-c:a', 'pcm_f32le', '-'],
                                 capture_output=True, check=True).stdout
            samples = struct.unpack(f'<{len(pcm)//4}f', pcm)
            self.assertAlmostEqual(len(samples) / 96000, 3, places=2)
            # Both supplied tones must survive simultaneous mixing.
            for frequency in (440, 880):
                projection = sum(samples[2*n] * math.sin(2*math.pi*frequency*n/48000)
                                 for n in range(48000)) / 24000
                self.assertGreater(abs(projection), 0.04)
            self.assertEqual(before, [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])
            self.assertEqual(result['measurement']['rail_hits'], 0)
            self.assertLessEqual(result['measurement']['true_peak_dbtp'], -1)
            self.assertNotEqual(mix_stems(*paths, root / 'out')['path'], result['path'])


if __name__ == '__main__':
    unittest.main()
