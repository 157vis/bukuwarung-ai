@echo off
REM laris.AI — Dashboard dari USB (double-click)
cd /d "%~dp0"
call .venv\Scripts\activate.bat
streamlit run app.py
pause
