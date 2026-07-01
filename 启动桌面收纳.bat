@echo off
cd /d "%~dp0"
echo Starting...
"C:\Users\15549\AppData\Local\Programs\Python\Python312\python.exe" main.py
echo.
echo Exit: %errorlevel%
if exist crash.log (
    echo === crash.log ===
    type crash.log
)
pause
