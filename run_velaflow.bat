@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  set "PYTHON=.venv\Scripts\python.exe"
) else (
  set "PYTHON=python"
)

start http://localhost:8502
"%PYTHON%" -m streamlit run app\main.py --server.port 8502
