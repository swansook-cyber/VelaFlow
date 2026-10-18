"""Real full-app browser upload/download, FFprobe and mastering measurement gates.

Run: python tests/run_mix_e2e.py --output <artifact directory>
Requires Node + test-only Playwright (available through NODE_PATH in CI).
"""
import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

from qa_support import ROOT, offline_env, stage_app, tone

sys.path.insert(0, str(ROOT))
from core.remaster_engine import measure_remaster_artifact
from core.real_clip_pipeline import find_ffmpeg
from core.stem_mixer import probe_stem


def rss_bytes(pid):
    if sys.platform != 'win32':
        for line in Path(f'/proc/{pid}/status').read_text().splitlines():
            if line.startswith('VmRSS:'):
                return int(line.split()[1]) * 1024
        return 0
    import ctypes
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ('PeakWorkingSetSize', 'WorkingSetSize', 'QuotaPeakPagedPoolUsage',
                'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage', 'QuotaNonPagedPoolUsage',
                'PagefileUsage', 'PeakPagefileUsage')]
    kernel = ctypes.windll.kernel32
    kernel.OpenProcess.restype = wintypes.HANDLE
    handle = kernel.OpenProcess(0x410, False, pid)
    if not handle:
        return 0
    try:
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        if not ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            raise OSError('Unable to measure app RSS')
        return counters.WorkingSetSize
    finally:
        kernel.CloseHandle(handle)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = {'passed': False, 'listening_qa': 'NOT PERFORMED'}
    with tempfile.TemporaryDirectory(prefix='vela-mix-e2e-') as tmp:
        root = Path(tmp)
        app = stage_app(root / 'app-copy')
        scratch = root / 'scratch'
        scratch.mkdir()
        fixtures = root / 'fixtures'
        fixtures.mkdir()
        tone(fixtures / 'vocal.wav', duration=2)
        tone(fixtures / 'instrumental.wav', duration=3, frequency=880)
        tone(fixtures / 'silence.wav', duration=3, silent=True)
        (fixtures / 'corrupt.wav').write_bytes(b'corrupt WAV fixture')
        with (fixtures / 'oversized.wav').open('wb') as stream:
            stream.truncate(64 * 1024 * 1024 + 1)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        env = offline_env()
        # All request-owned temporary audio remains inside this disposable sandbox.
        env.update({'TMP': str(scratch), 'TEMP': str(scratch), 'TMPDIR': str(scratch), 'PYTHONUTF8': '1'})
        command = [sys.executable, '-m', 'streamlit', 'run', 'app/main.py', '--server.headless', 'true',
                   '--server.address', '127.0.0.1', '--server.port', str(port), '--browser.gatherUsageStats', 'false']
        with (output / 'server.log').open('wb') as logs:
            server = subprocess.Popen(command, cwd=app, env=env, stdout=logs, stderr=subprocess.STDOUT,
                                      creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
            stop = threading.Event()
            peak = [0]
            def sample():
                while not stop.wait(0.2):
                    try:
                        peak[0] = max(peak[0], rss_bytes(server.pid))
                    except (OSError, ProcessLookupError):
                        pass
            monitor = threading.Thread(target=sample, daemon=True)
            monitor.start()
            try:
                url = f'http://127.0.0.1:{port}'
                for _ in range(120):
                    if server.poll() is not None:
                        raise RuntimeError('Streamlit server exited; inspect server.log')
                    try:
                        urllib.request.urlopen(url + '/_stcore/health', timeout=1).close()
                        break
                    except OSError:
                        time.sleep(0.25)
                else:
                    raise TimeoutError('Streamlit did not start')
                browser = subprocess.run(['node', str(ROOT / 'tests/mix_stems.e2e.cjs'), url, str(fixtures), str(output)],
                                         env=env, capture_output=True, timeout=240)
                (output / 'browser.log').write_bytes(browser.stdout + browser.stderr)
                if browser.returncode:
                    raise RuntimeError(browser.stderr.decode('utf-8', errors='replace'))
                report['browser'] = json.loads(browser.stdout.decode().strip().splitlines()[-1])
                ffmpeg = find_ffmpeg()
                report['outputs'] = {}
                for name, silent in (('mix.wav', False), ('mix-repeat.wav', False), ('silent.wav', True),
                                     ('mix-regenerated.wav', False), ('silent-after-other-session-clear.wav', True)):
                    path = output / name
                    probe = probe_stem(path, ffmpeg)
                    measurement = measure_remaster_artifact(path, ffmpeg)
                    assert probe['codec_name'] == 'pcm_s24le' and int(probe['bits_per_raw_sample']) == 24
                    assert int(probe['sample_rate']) == 48000 and int(probe['channels']) == 2
                    assert abs(probe['duration'] - 3) < 0.01
                    assert measurement['ok'] and measurement['rail_hits'] == 0
                    if silent:
                        assert measurement['effectively_silent'] and measurement['integrated_lufs'] is None
                    else:
                        assert measurement['integrated_lufs'] is not None and measurement['true_peak_dbtp'] <= -1
                    report['outputs'][name] = {'ffprobe': probe, 'measurement': measurement}
                assert not list(scratch.glob('velaflow-stem-*')), 'request-owned scratch files leaked'
                assert not (app / 'exports/stem_mixes').exists(), 'mix uploads persisted in exports'
                assert 0 < peak[0] < 1024 * 1024 * 1024, 'server RSS missing or above 1 GiB QA ceiling'
                report.update(passed=True, server_peak_rss_bytes=peak[0], scratch_directories_remaining=0)
            finally:
                stop.set()
                monitor.join(timeout=2)
                server.terminate()
                try:
                    server.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()
                (output / 'e2e-results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
