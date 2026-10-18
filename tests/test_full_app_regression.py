"""Boot the actual app in a disposable source/config copy, without user data."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from qa_support import offline_env, stage_app


class FullAppRegressionTests(unittest.TestCase):
    def test_existing_studios_and_audio_modes(self):
        script = '''
from streamlit.testing.v1 import AppTest
a = AppTest.from_file('app/main.py', default_timeout=60).run()
assert not a.exception, [e.message for e in a.exception]
for page in ('Audio Editor', 'Remaster Studio', 'Song Studio'):
    nav = next(r for r in a.radio if r.label == 'Navigation')
    nav.set_value(page).run()
    assert not a.exception, (page, [e.message for e in a.exception])
    if page == 'Audio Editor':
        assert a.radio(key='audio_editor_mode').value == 'Cut'
        for mode in ('Join', 'Mix stems', 'Cut'):
            a.radio(key='audio_editor_mode').set_value(mode).run()
            assert not a.exception, (mode, [e.message for e in a.exception])
        assert a.radio(key='audio_editor_mode').value == 'Cut'
print('PASS actual app: Home, Audio Editor Cut/Join/Mix, Remaster Studio, Song Studio')
'''
        with tempfile.TemporaryDirectory(prefix='vela-app-regression-') as tmp:
            root = stage_app(Path(tmp) / 'app-copy')
            result = subprocess.run([sys.executable, '-c', script], cwd=root, env=offline_env(),
                                    capture_output=True, timeout=180)
            self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace')[-5000:])
