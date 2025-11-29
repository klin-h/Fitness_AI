@echo off
echo Starting FitnessAI Application...

:: Check if we are in the correct directory
if not exist "frontend" (
    echo Error: Please run this script from the project root directory
    pause
    exit /b 1
)
if not exist "backend" (
    echo Error: Please run this script from the project root directory  
    pause
    exit /b 1
)

:: Install basic Python dependencies
echo Installing Python dependencies...
pip install flask flask-cors

:: Start the application
echo Starting FitnessAI server...
echo Frontend: http://localhost:8000
echo Demo: http://localhost:8000/demo
echo API: http://localhost:8000/api

python app.py

pause 