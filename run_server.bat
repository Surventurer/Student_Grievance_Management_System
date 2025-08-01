@echo off
echo Starting Django Development Server for External Access
echo.
echo Server will be accessible on:
echo - Local: http://localhost:8000
echo - Local: http://127.0.0.1:8000
echo - Network: http://192.168.1.2:8000
echo.
echo Note: Make sure Windows Firewall allows Python/Django on port 8000
echo.
cd /d "%~dp0src"
uv run manage.py runserver 0.0.0.0:8000
pause
