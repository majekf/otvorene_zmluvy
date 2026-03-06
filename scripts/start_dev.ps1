# Start GovLens development servers (backend + frontend) on Windows.
# Usage: .\scripts\start_dev.ps1

Write-Host "=== GovLens Development Server ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Backend API:  http://localhost:8000"
Write-Host "  Frontend Dev: http://localhost:5173"
Write-Host "  API Docs:     http://localhost:8000/docs"
Write-Host ""

$rootDir = Split-Path -Parent $PSScriptRoot

# Activate virtual environment if available
$venvActivate = Join-Path $rootDir ".venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    & $venvActivate
}

# Start backend
Write-Host "[1/2] Starting backend (FastAPI + Uvicorn)..." -ForegroundColor Yellow
$backend = Start-Process -PassThru -NoNewWindow -FilePath "python" -ArgumentList "-m", "uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000", "--reload" -WorkingDirectory $rootDir

# Start frontend
Write-Host "[2/2] Starting frontend (Vite dev server)..." -ForegroundColor Yellow
$frontendDir = Join-Path $rootDir "frontend"
$frontend = Start-Process -PassThru -NoNewWindow -FilePath "npm" -ArgumentList "run", "dev" -WorkingDirectory $frontendDir

Write-Host ""
Write-Host "Press Ctrl+C to stop both servers." -ForegroundColor Gray

try {
    # Wait for either process to exit
    while (-not $backend.HasExited -and -not $frontend.HasExited) {
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Host "Shutting down..." -ForegroundColor Yellow
    if (-not $backend.HasExited) { Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue }
    if (-not $frontend.HasExited) { Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue }
}
