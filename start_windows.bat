@echo off
setlocal EnableExtensions EnableDelayedExpansion
title CoolRoute - Local server
cd /d "%~dp0"

REM Keep Python temporary files inside this project workspace.
if not exist ".tmp" mkdir ".tmp"
set "TEMP=%CD%\.tmp"
set "TMP=%CD%\.tmp"

REM Prefer the Python launcher, then use python.exe if the launcher is unavailable.
set "PYTHON_RUN="
where py >nul 2>&1
if not errorlevel 1 (
    py -3 --version >nul 2>&1
    if not errorlevel 1 set "PYTHON_RUN=py -3"
)
if not defined PYTHON_RUN (
    python --version >nul 2>&1
    if not errorlevel 1 set "PYTHON_RUN=python"
)
if not defined PYTHON_RUN (
    echo ERROR: Python 3.10+ was not found. Install Python and try again.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating the local Python environment...
    !PYTHON_RUN! -m venv .venv
    if errorlevel 1 (
        echo ERROR: Could not create the Python environment.
        pause
        exit /b 1
    )
) else (
    echo [1/3] Local Python environment found.
)

if not exist ".venv\Scripts\pip.exe" (
    echo Preparing pip...
    .venv\Scripts\python.exe -m ensurepip --upgrade
    if errorlevel 1 (
        echo ERROR: Could not prepare pip. Check that this folder is writable.
        pause
        exit /b 1
    )
)

echo [2/3] Checking Starlette and Uvicorn...
.venv\Scripts\python.exe -c "import starlette, uvicorn" >nul 2>&1
if errorlevel 1 (
    echo Installing required Python packages...
    if exist ".tmp\wheels\starlette-1.8.0-py3-none-any.whl" (
        .venv\Scripts\python.exe -m pip install --quiet --no-index --find-links ".tmp\wheels" -r requirements.txt
    ) else (
        .venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
    )
    if errorlevel 1 (
        echo ERROR: Dependency installation failed. Check your internet connection.
        pause
        exit /b 1
    )
) else (
    echo Required packages are already installed.
)

echo [3/3] Starting CoolRoute.
echo Keep this window open. Press Ctrl+C to stop the server.
.venv\Scripts\python.exe run_local.py
pause
