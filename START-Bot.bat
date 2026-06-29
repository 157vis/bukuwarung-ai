@echo off
REM laris.AI — Bot WA lokal dari USB (double-click)
cd /d "%~dp0\kita-cuan-wa-bot"
set PYTHONPATH=%~dp0
call ..\.venv\Scripts\activate.bat
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
