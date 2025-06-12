$ErrorActionPreference = 'Stop'

python -m venv .venv

& .\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -e .

Write-Host "`n✅ Environment created. Activate it with `.\.venv\Scripts\Activate.ps1`" -ForegroundColor Green
