@echo off
setlocal
set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

if not exist ".venv" (
  python -m venv .venv
)
call .venv\Scripts\activate

pip install -r requirements.txt
if exist "app.db" del /f /q "app.db"
flask --app app.py initdb

set "FLASK_RUN_HOST=0.0.0.0"
set "FLASK_RUN_PORT=5000"
python app.py
