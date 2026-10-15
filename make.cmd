@echo off
if exist "%~dp0recovery.local.json" (
 if "%1"=="all" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\build-desktop-recovery.ps1"
  exit /b
 )
 if "%1"=="test" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\verify-desktop-recovery.ps1"
  exit /b
 )
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0make.ps1" %*
