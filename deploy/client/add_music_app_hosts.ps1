$HostName = "music-app.example.local"
$IpAddress = "PYTHON_EC2_PUBLIC_IP"
$HostsPath = "$env:WINDIR\System32\drivers\etc\hosts"
$Line = "$IpAddress $HostName"

$Current = Get-Content -Path $HostsPath -ErrorAction Stop
if ($Current -notmatch [regex]::Escape($HostName)) {
    Add-Content -Path $HostsPath -Value $Line
    Write-Host "Added: $Line"
} else {
    Write-Host "$HostName already exists in hosts file."
}
