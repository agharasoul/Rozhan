# Run as Administrator!
Write-Host "=== Rozhan Mobile Setup ===" -ForegroundColor Cyan

# Get IP
$ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*Loopback*" -and $_.IPAddress -notlike "169.*" }).IPAddress | Select-Object -First 1
Write-Host "Your IP: $ip" -ForegroundColor Green

# Open firewall
Write-Host "Opening firewall..." -ForegroundColor Yellow
netsh advfirewall firewall delete rule name="Rozhan9999" 2>$null
netsh advfirewall firewall delete rule name="Rozhan3000" 2>$null
netsh advfirewall firewall add rule name="Rozhan9999" dir=in action=allow protocol=TCP localport=9999
netsh advfirewall firewall add rule name="Rozhan3000" dir=in action=allow protocol=TCP localport=3000

Write-Host ""
Write-Host "=== Done! ===" -ForegroundColor Green
Write-Host "Mobile URL: http://${ip}:3000" -ForegroundColor Cyan
Write-Host "API URL: http://${ip}:9999" -ForegroundColor Cyan
