# Quick Restart Script for Donna.AI Servers# Quick Restart Script for Donna.AI Servers

# Run this after making code changes# Run this after making code changes



Write-Host ""Write-Host "`n================================================" -ForegroundColor Cyan

Write-Host "================================================" -ForegroundColor CyanWrite-Host "   RESTART INSTRUCTIONS FOR DONNA.AI SERVERS" -ForegroundColor Yellow

Write-Host "   RESTART INSTRUCTIONS FOR DONNA.AI SERVERS" -ForegroundColor YellowWrite-Host "================================================`n" -ForegroundColor Cyan

Write-Host "================================================" -ForegroundColor Cyan

Write-Host ""Write-Host "CHANGES MADE:" -ForegroundColor Green

Write-Host "  ✓ Reduced agent startup wait from 3s to 2s" -ForegroundColor White

Write-Host "CHANGES MADE:" -ForegroundColor GreenWrite-Host "  ✓ Increased telephony API timeout to 45s" -ForegroundColor White

Write-Host "  * Reduced agent startup wait from 3s to 2s" -ForegroundColor WhiteWrite-Host "  ✓ Increased web portal timeout to 90s" -ForegroundColor White

Write-Host "  * Increased telephony API timeout to 45s" -ForegroundColor WhiteWrite-Host "`n"

Write-Host "  * Increased web portal timeout to 90s" -ForegroundColor White

Write-Host ""Write-Host "TO RESTART SERVERS:" -ForegroundColor Yellow

Write-Host "`n1️⃣  Stop all servers (press Ctrl+C in each terminal)`n" -ForegroundColor Cyan

Write-Host "TO RESTART SERVERS:" -ForegroundColor Yellow

Write-Host ""Write-Host "2️⃣  Or use the automated script:`n" -ForegroundColor Cyan

Write-Host "1. Stop all servers (press Ctrl+C in each terminal)" -ForegroundColor CyanWrite-Host "    .\start_all_servers.ps1`n" -ForegroundColor Green

Write-Host ""

Write-Host "3️⃣  Or start manually in 3 separate terminals:`n" -ForegroundColor Cyan

Write-Host "2. Or use the automated script:" -ForegroundColor CyanWrite-Host "    Terminal 1: myENV\Scripts\python.exe main.py" -ForegroundColor White

Write-Host ""Write-Host "    Terminal 2: myENV\Scripts\python.exe src\main.py" -ForegroundColor White

Write-Host "    .\start_all_servers.ps1" -ForegroundColor GreenWrite-Host "    Terminal 3: myENV\Scripts\python.exe telephony_server.py" -ForegroundColor White

Write-Host ""

Write-Host "`n================================================" -ForegroundColor Cyan

Write-Host "3. Or start manually in 3 separate terminals:" -ForegroundColor CyanWrite-Host "After restarting, test with 'Call Me Now' button!" -ForegroundColor Yellow

Write-Host ""Write-Host "================================================`n" -ForegroundColor Cyan

Write-Host "    Terminal 1: myENV\Scripts\python.exe main.py" -ForegroundColor White
Write-Host "    Terminal 2: myENV\Scripts\python.exe src\main.py" -ForegroundColor White
Write-Host "    Terminal 3: myENV\Scripts\python.exe telephony_server.py" -ForegroundColor White
Write-Host ""

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "After restarting, test with Call Me Now button!" -ForegroundColor Yellow
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
