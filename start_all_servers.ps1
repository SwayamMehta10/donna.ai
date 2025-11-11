$ErrorActionPreference = "Stop"

Write-Host "Starting Donna.ai 3-Server Architecture..." -ForegroundColor Green
Write-Host ""

# Start Web Portal (Port 8020)
Write-Host "Starting Web Portal (Port 8020)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd D:\GitHub\donna.ai; .\myENV\Scripts\Activate.ps1; Write-Host 'WEB PORTAL - Port 8020' -ForegroundColor Yellow; python main.py"

# Wait 2 seconds
Start-Sleep -Seconds 2

# Start Context Fetcher (Port 8000)
Write-Host "Starting Context Fetcher (Port 8000)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd D:\GitHub\donna.ai; .\myENV\Scripts\Activate.ps1; Write-Host 'CONTEXT FETCHER - Port 8000' -ForegroundColor Yellow; python src/main.py"

# Wait 2 seconds
Start-Sleep -Seconds 2

# Start Telephony Server (Port 8021)
Write-Host "Starting Telephony Server (Port 8021)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd D:\GitHub\donna.ai; .\myENV\Scripts\Activate.ps1; Write-Host 'TELEPHONY SERVER - Port 8021' -ForegroundColor Yellow; python telephony_server.py"

# Wait a moment for servers to start
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "All servers started successfully!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "URLs:" -ForegroundColor Yellow
Write-Host "  Web Portal:      http://localhost:8020" -ForegroundColor Cyan
Write-Host "  Context Fetcher: http://localhost:8000" -ForegroundColor Cyan
Write-Host "  Telephony:       http://localhost:8021" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Open http://localhost:8020 in your browser" -ForegroundColor White
Write-Host "  2. Login with Google" -ForegroundColor White
Write-Host "  3. Add your phone number" -ForegroundColor White
Write-Host "  4. Click 'Call Me Now' button" -ForegroundColor White
Write-Host ""
Write-Host "To stop all servers, close all PowerShell windows or run:" -ForegroundColor Yellow
Write-Host "  Get-Process python | Stop-Process -Force" -ForegroundColor Gray
Write-Host ""
