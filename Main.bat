@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launcher.ps1"
if errorlevel 1 (
  echo.
  echo Setup failed. Press any key to exit.
  pause >nul
)
