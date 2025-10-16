# Start Sign Detection System (Windows)

Write-Host "===================================" -ForegroundColor Cyan
Write-Host "Sign Detection System" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan

# Navigate to project root
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

# Activate virtual environment if it exists
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & .\venv\Scripts\Activate.ps1
} else {
    Write-Host "Warning: No virtual environment found" -ForegroundColor Yellow
    Write-Host "Run: python -m venv venv; .\venv\Scripts\Activate.ps1; pip install -r backend\requirements.txt"
}

# Create necessary directories
New-Item -ItemType Directory -Force -Path "data\logs" | Out-Null
New-Item -ItemType Directory -Force -Path "data\captures" | Out-Null
New-Item -ItemType Directory -Force -Path "backend\models" | Out-Null

# Start the server
Write-Host ""
Write-Host "Starting server..." -ForegroundColor Green
Write-Host "Access the app at: http://localhost:5000" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop" -ForegroundColor Green
Write-Host ""

Set-Location backend
python main.py
