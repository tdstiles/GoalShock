@echo off
REM ========================================
REM GoalShock Backend - One-Click Setup
REM ========================================

echo.
echo ==========================================
echo   GoalShock Trading Bot - Auto Setup
echo ==========================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo [1/5] Python detected
python --version
echo.

REM Check if virtual environment exists
if exist venv (
    echo [2/5] Virtual environment found
) else (
    echo [2/5] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo      Virtual environment created successfully
)
echo.

REM Activate virtual environment
echo [3/5] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo      Virtual environment activated
echo.

REM Check if .env exists
if exist .env (
    echo [4/5] Configuration file found
) else (
    echo [4/5] Creating configuration file...
    copy .env.example .env >nul
    echo      Created .env from .env.example
    echo      Using DEMO_MODE (safe for testing)
)
echo.

REM Install/upgrade dependencies
echo [5/5] Installing dependencies...
echo      This may take a few minutes on first run...
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    echo Trying verbose install...
    pip install -r requirements.txt
    pause
    exit /b 1
)
echo      All dependencies installed successfully
echo.

REM Create logs directory
if not exist logs mkdir logs

echo ==========================================
echo   Setup Complete!
echo ==========================================
echo.
echo Starting GoalShock Trading Bot...
echo.
echo Server will be available at:
echo   - API: http://localhost:8000
echo   - Docs: http://localhost:8000/docs
echo   - WebSocket: ws://localhost:8000/ws
echo.
echo Press Ctrl+C to stop the server
echo.
echo ==========================================
echo.

REM Start the server
python main.py

REM If server exits, pause so user can see any error messages
if errorlevel 1 (
    echo.
    echo Server stopped with errors. Check the output above.
    pause
)
