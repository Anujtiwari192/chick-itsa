param(
  [int]$Port = 5000
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (-not (Test-Path ".venv")) {
  python -m venv .venv
}

& .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
if (Test-Path "app.db") {
  Remove-Item -Force "app.db"
}
flask --app app.py initdb

$env:FLASK_RUN_HOST = "0.0.0.0"
$env:FLASK_RUN_PORT = "$Port"
python app.py
