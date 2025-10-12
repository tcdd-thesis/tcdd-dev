# PowerShell development start script for Windows
# Runs all services locally

Write-Host "Starting Sign Detection System in Development Mode" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

$jobs = @()

# Start Python camera server
Write-Host "Starting Python camera server on port 5001..." -ForegroundColor Blue
$pythonJob = Start-Job -ScriptBlock {
    Set-Location "$using:PWD\backend\python"
    python camera_server.py
}
$jobs += $pythonJob
Write-Host "Python server started (Job ID: $($pythonJob.Id))" -ForegroundColor Green

# Wait for Python server to initialize
Start-Sleep -Seconds 3

# Start Node.js backend
Write-Host "Starting Node.js backend on port 5000..." -ForegroundColor Blue
$nodeJob = Start-Job -ScriptBlock {
    Set-Location "$using:PWD\backend"
    npm start
}
$jobs += $nodeJob
Write-Host "Node.js backend started (Job ID: $($nodeJob.Id))" -ForegroundColor Green

# Wait for backend to initialize
Start-Sleep -Seconds 2

# Start React frontend
Write-Host "Starting React frontend on port 3000..." -ForegroundColor Blue
$reactJob = Start-Job -ScriptBlock {
    Set-Location "$using:PWD\frontend"
    npm start
}
$jobs += $reactJob
Write-Host "React frontend started (Job ID: $($reactJob.Id))" -ForegroundColor Green

Write-Host ""
Write-Host "All services started!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Python Camera Server: http://localhost:5001"
Write-Host "Node.js Backend:      http://localhost:5000"
Write-Host "React Frontend:       http://localhost:3000"
Write-Host ""
Write-Host "To view output: Get-Job | Receive-Job -Keep"
Write-Host "To stop all: Get-Job | Stop-Job; Get-Job | Remove-Job"
Write-Host ""

# Keep script running and show job status
try {
    while ($true) {
        Start-Sleep -Seconds 5
        $runningJobs = Get-Job | Where-Object { $_.State -eq 'Running' }
        if ($runningJobs.Count -lt 3) {
            Write-Host "Some services stopped. Check with: Get-Job | Receive-Job" -ForegroundColor Yellow
        }
    }
}
finally {
    Write-Host "Stopping all services..." -ForegroundColor Yellow
    Get-Job | Stop-Job
    Get-Job | Remove-Job
    Write-Host "All services stopped." -ForegroundColor Green
}
