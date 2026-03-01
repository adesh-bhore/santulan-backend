@echo off
echo ========================================
echo PMPML Backend Server Startup
echo ========================================
echo.

echo Checking Python installation...
python --version
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)
echo.

echo Starting backend server...
echo Server will be available at: http://localhost:8000
echo API Documentation: http://localhost:8000/docs
echo Health Check: http://localhost:8000/health
echo.
echo Press CTRL+C to stop the server
echo.

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause
