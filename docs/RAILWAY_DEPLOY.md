# VelaFlow Railway Internal Cloud Deploy

VelaFlow Cloud Beta is for internal testing only. It does not require owner API
keys and defaults to Bring Your Own API Key inside the browser.

## Deploy Files

- `Procfile`
  - `web: streamlit run app/main.py --server.port=$PORT --server.address=0.0.0.0`
- `railway.json`
  - Uses Nixpacks and the same Streamlit start command.
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

Real local MP4 output requires FFmpeg. If Railway/Nixpacks does not provide
FFmpeg, VelaFlow shows a warning in System Health and keeps provider/render
package exports available. Configure `FFMPEG_PATH` if a custom binary path is
available.

## Internal Test Checklist

- App opens in cloud mode.
- Sidebar shows `Internal Cloud Mode`.
- AI Settings defaults to `Use My Own API Key`.
- Browser localStorage restores a saved user key after refresh.
- Missing API key shows a warning and does not crash.
- Hook Clip Studio can generate a hook clip package.
- Placeholder/FFmpeg real output works if FFmpeg is available.
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
