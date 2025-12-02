@echo off
echo ================================================================================
echo GoalShock - One-Click Startup
echo ================================================================================
echo.

echo Starting Backend with API Verification...
echo.

cd backend
start "GoalShock Backend" cmd /k "python start_with_verification.py"

timeout /t 5

echo Starting Frontend...
echo.

cd ..\app
start "GoalShock Frontend" cmd /k "npm run dev"

echo.
echo ================================================================================
echo GoalShock Started!
echo ================================================================================
echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo.
echo Check the terminal windows for status
echo Press any key to exit this window...
pause > nul
