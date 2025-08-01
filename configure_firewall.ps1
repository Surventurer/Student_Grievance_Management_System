# Configure Windows Firewall for Django Development Server
# Run this script as Administrator

Write-Host "Configuring Windows Firewall for Django Development Server" -ForegroundColor Green
Write-Host ""

# Check if running as Administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click and select 'Run as Administrator'" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

try {
    # Create inbound rule for Django development server
    New-NetFirewallRule -DisplayName "Django Development Server" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Any
    Write-Host "✓ Inbound firewall rule created for port 8000" -ForegroundColor Green
    
    # Create outbound rule for Django development server
    New-NetFirewallRule -DisplayName "Django Development Server" -Direction Outbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Any
    Write-Host "✓ Outbound firewall rule created for port 8000" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "Windows Firewall configured successfully!" -ForegroundColor Green
    Write-Host "You can now access your Django server from other devices on the network." -ForegroundColor Cyan
    
} catch {
    Write-Host "Error configuring firewall: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Manual configuration steps:" -ForegroundColor Yellow
    Write-Host "1. Open Windows Defender Firewall with Advanced Security" -ForegroundColor White
    Write-Host "2. Click 'Inbound Rules' -> 'New Rule'" -ForegroundColor White
    Write-Host "3. Select 'Port' -> 'TCP' -> 'Specific Local Ports' -> Enter '8000'" -ForegroundColor White
    Write-Host "4. Select 'Allow the connection'" -ForegroundColor White
    Write-Host "5. Apply to all profiles (Domain, Private, Public)" -ForegroundColor White
    Write-Host "6. Name it 'Django Development Server'" -ForegroundColor White
}

Write-Host ""
Read-Host "Press Enter to exit"
