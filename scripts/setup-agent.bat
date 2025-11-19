@echo off
setlocal enabledelayedexpansion
REM Navigate to the agent directory
cd /d "%~dp0\..\agent" || exit /b 1

REM Function to check Python version (must be 3.10+)
echo Checking for Python 3.10 or higher...

REM Try common Python commands
set PYTHON_CMD=
for %%p in (python3.12 python3.11 python3.10 python3 python) do (
    where %%p >nul 2>&1
    if !errorlevel! equ 0 (
        for /f "tokens=2 delims= " %%v in ('%%p --version 2^>^&1') do (
            for /f "tokens=1,2 delims=." %%a in ("%%v") do (
                if "%%a"=="3" (
                    if %%b geq 10 (
                        set PYTHON_CMD=%%p
                        goto :found_python
                    )
                )
            )
        )
    )
)

:found_python
if "%PYTHON_CMD%"=="" (
    echo ERROR: Python 3.10 or higher is required but not found.
    echo.
    echo Please install Python 3.10+ from:
    echo   https://www.python.org/downloads/
    echo.
    echo After installing, run this script again.
    exit /b 1
)

echo Using %PYTHON_CMD%
%PYTHON_CMD% --version

REM Check if existing virtual environment uses old Python version
if exist ".venv\Scripts\python.exe" (
    for /f "tokens=2 delims= " %%v in ('.venv\Scripts\python.exe --version 2^>^&1') do (
        for /f "tokens=1,2 delims=." %%a in ("%%v") do (
            if "%%a"=="3" (
                if %%b lss 10 (
                    echo Warning: Existing virtual environment uses Python %%v (requires 3.10+)
                    echo Removing old virtual environment...
                    rmdir /s /q .venv
                )
            )
        )
    )
)

REM Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo Creating virtual environment with %PYTHON_CMD%...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 exit /b 1
)

REM Activate the virtual environment
call .venv\Scripts\activate.bat

REM Install requirements using pip
pip install -r requirements.txt 