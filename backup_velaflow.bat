@echo off
title VelaFlow Backup System

set PROJECT_DIR=D:\Project AI\vela_ai_studio_v5
set BACKUP_ROOT=D:\Project AI\vela_ai_studio_v5\manual_backups

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm-ss"') do set DATETIME=%%i

set BACKUP_NAME=velaflow_backup_%DATETIME%
set BACKUP_PATH=%BACKUP_ROOT%\%BACKUP_NAME%

echo.
echo ==========================================
echo Creating Backup...
echo ==========================================
echo.

mkdir "%BACKUP_PATH%"

echo Copying core files...

xcopy "%PROJECT_DIR%\app" "%BACKUP_PATH%\app" /E /I /Y
xcopy "%PROJECT_DIR%\core" "%BACKUP_PATH%\core" /E /I /Y
xcopy "%PROJECT_DIR%\providers" "%BACKUP_PATH%\providers" /E /I /Y
xcopy "%PROJECT_DIR%\config" "%BACKUP_PATH%\config" /E /I /Y
xcopy "%PROJECT_DIR%\docs" "%BACKUP_PATH%\docs" /E /I /Y
xcopy "%PROJECT_DIR%\tests" "%BACKUP_PATH%\tests" /E /I /Y

copy "%PROJECT_DIR%\README.md" "%BACKUP_PATH%"
copy "%PROJECT_DIR%\MASTER_CONTEXT.md" "%BACKUP_PATH%"
copy "%PROJECT_DIR%\CHANGELOG.md" "%BACKUP_PATH%"

echo.
echo ==========================================
echo Backup Complete
echo ==========================================
echo.
echo Backup saved to:
echo %BACKUP_PATH%
echo.

pause