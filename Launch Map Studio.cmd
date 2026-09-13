@echo off
setlocal
if exist "%~dp0dist\bin\RhythiaMapStudio\RhythiaMapStudio.exe" (
    if exist "%~dp0separation\backend.json" set "RHYTHIA_SEPARATOR_CONFIG=%~dp0separation\backend.json"
    start "" "%~dp0dist\bin\RhythiaMapStudio\RhythiaMapStudio.exe"
    exit /b
)
if exist "%~dp0.venv\Scripts\pythonw.exe" (
    start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0run_studio.py"
    exit /b
)
echo Follow the development setup in README.md or run build.ps1.
pause
