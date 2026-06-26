@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  py merge_parts.py
) else (
  python merge_parts.py
)

echo.
pause
