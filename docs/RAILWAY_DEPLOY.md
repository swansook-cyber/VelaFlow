# VelaFlow Railway Internal Cloud Deploy

VelaFlow Cloud Beta is for internal testing only. It does not require owner API
keys and defaults to Bring Your Own API Key inside the browser.

## Deploy Files

- `Procfile`
  - `web: streamlit run app/main.py --server.port=$PORT --server.address=0.0.0.0`
- `railway.json`
  - Uses Nixpacks and the same Streamlit start command.
- `nixpacks.toml`
  - Installs the Railway runtime FFmpeg package with `nixPkgs = ["ffmpeg"]`.
- `runtime.txt`
  - Pins Python runtime.
- `requirements.txt`
  - Installs Streamlit, provider SDKs, and helper libraries.

## Railway Environment Variables

Required:

```text
VELAFLOW_MODE=CLOUD
```

Optional:

```text
DEFAULT_AI_PROVIDER=gemini
FFMPEG_PATH=ffmpeg
```

Do not set owner/admin provider keys for internal tester usage unless you
intentionally want to test the `Use VelaFlow Beta Key` mode. The default user
flow is:

1. Open VelaFlow.
2. Go to AI Settings.
3. Select `Use My Own API Key`.
4. Select Gemini, OpenAI GPT, or xAI Grok.
5. Save the key on this device.

User keys are stored only in browser `localStorage` and Streamlit session state.
They are not written to project files, exports, logs, analytics, render
packages, or server JSON files.

## Cloud-Safe Runtime Paths

VelaFlow writes runtime outputs under the app workspace:

- `project_data/clips/<project>/scenes/`
- `project_data/clips/<project>/exports/`
- `project_data/seller/`
- `project_data/podcast/`
- `outputs/temp/`
- `outputs/jobs/`
- `outputs/beta_packages/`

These are runtime artifacts and should not be committed to GitHub. On Railway,
they should be treated as ephemeral unless a persistent volume is configured.

## FFmpeg

Real local MP4 output requires FFmpeg. Railway/Nixpacks should install it from
`nixpacks.toml`:

```toml
[phases.setup]
nixPkgs = ["ffmpeg"]
```

At runtime VelaFlow detects FFmpeg from `FFMPEG_PATH`, the system `PATH`, and
legacy local Windows folders. On Railway, the expected path is usually the
Nix-provided `ffmpeg` executable on `PATH`.

System Health reports:

- FFmpeg installed
- FFmpeg executable path
- FFmpeg version
- MoviePy FFmpeg access

If FFmpeg is missing, VelaFlow shows a clear warning and disables local MP4
buttons such as Render Scene 1, Render All Scenes, and Combine Final Clip.
Provider packages, render queue metadata, and BYO Veo scene job submission
remain available. Configure `FFMPEG_PATH` only if a custom binary path is needed.

## Internal Test Checklist

- App opens in cloud mode.
- Sidebar shows `Internal Cloud Mode`.
- AI Settings defaults to `Use My Own API Key`.
- Browser localStorage restores a saved user key after refresh.
- Missing API key shows a warning and does not crash.
- Hook Clip Studio can generate a hook clip package.
- Placeholder/FFmpeg real output works if FFmpeg is available.
- Render Scene 1, Render All Scenes, and Combine Final Clip are enabled when
  FFmpeg is detected.
- If FFmpeg is missing, local render buttons are disabled and the warning is
  visible in Hook Clip Studio / MV Director.
- Google Veo Scene 1 flow shows missing-key errors safely without exposing keys.
- Exports download correctly on desktop and mobile.
- System Health shows FFmpeg status and provider configuration status.

## Local Cloud-Mode Test

PowerShell:

```powershell
$env:VELAFLOW_MODE="CLOUD"
.\.venv\Scripts\python.exe -m streamlit run app/main.py --server.port=8502 --server.address=0.0.0.0
```

Validation:

```powershell
.\.venv\Scripts\python.exe -m compileall -q app core providers tests scripts
.\.venv\Scripts\python.exe tests\smoke_test.py
.\.venv\Scripts\python.exe scripts\build_beta_package.py
```
