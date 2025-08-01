# Django External Access Server Starter
Write-Host "Starting Django Development Server for External Access" -ForegroundColor Green
Write-Host ""
Write-Host "Server will be accessible on:" -ForegroundColor Yellow
Write-Host "- Local: http://localhost:8000" -ForegroundColor Cyan
Write-Host "- Local: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "- Network: http://192.168.1.2:8000" -ForegroundColor Cyan
Write-Host ""
Write-Host "Note: Make sure Windows Firewall allows Python/Django on port 8000" -ForegroundColor Red
Write-Host ""

# Change to src directory
Set-Location -Path (Join-Path $PSScriptRoot "src")

# Check if Windows Firewall rule exists for Django
$firewallRule = Get-NetFirewallRule -DisplayName "Django Development Server" -ErrorAction SilentlyContinue
if (-not $firewallRule) {
    Write-Host "Windows Firewall rule not found. You may need to create one manually." -ForegroundColor Yellow
    Write-Host "Or run this script as Administrator to create the rule automatically." -ForegroundColor Yellow
    Write-Host ""
}

# Start the Django server
Write-Host "Starting server..." -ForegroundColor Green
uv run manage.py runserver 0.0.0.0:8000
