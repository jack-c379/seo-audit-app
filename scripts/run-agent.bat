@echo off
setlocal enabledelayedexpansion
REM Navigate to the agent directory
cd /d %~dp0\..\agent

REM Check if virtual environment exists
if not exist ".venv" (
    echo ERROR: Virtual environment not found. Please run the setup script first:
    echo   npm run install:agent
    echo   or
    echo   scripts\setup-agent.bat
    exit /b 1
)

REM Check Python version in virtual environment
if exist ".venv\Scripts\python.exe" (
    for /f "tokens=2 delims= " %%v in ('.venv\Scripts\python.exe --version 2^>^&1') do (
        for /f "tokens=1,2 delims=." %%a in ("%%v") do (
            if "%%a"=="3" (
                if %%b lss 10 (
                    echo ERROR: Virtual environment uses Python %%v, but Python 3.10+ is required.
                    echo Please recreate the virtual environment:
                    echo   rmdir /s /q .venv
                    echo   npm run install:agent
                    exit /b 1
                )
            )
        )
    )
)

REM Activate the virtual environment
call .venv\Scripts\activate.bat

REM Run the agent
.venv\Scripts\python.exe agent.py 