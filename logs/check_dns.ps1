param()
$ErrorActionPreference = "Continue"

# Cek DNS record
Write-Host "================================================================"
Write-Host "CEK 2: DNS records untuk larisai.my.id"
Write-Host "================================================================"
$dnsTargets = @("www.larisai.my.id", "larisai.my.id")
foreach ($host in $dnsTargets) {
    try {
        $ips = [System.Net.Dns]::GetHostAddresses($host) | ForEach-Object { $_.IPAddressToString }
        Write-Host "$host -> $($ips -join ', ')"
    } catch {
        Write-Host "$host -> ERR: $($_.Exception.Message)"
    }
}

Write-Host ""
Write-Host "================================================================"
Write-Host "CEK 3: HTTP headers www.larisai.my.id (cari cf-worker, cf-cache, dll)"
Write-Host "================================================================"
try {
    $r = Invoke-WebRequest -Uri "https://www.larisai.my.id/" -Headers @{"User-Agent"="Mozilla/5.0"} -UseBasicParsing -TimeoutSec 15
    foreach ($k in $r.Headers.Keys) {
        $v = $r.Headers[$k] -join ", "
        Write-Host "$k : $v"
    }
} catch {
    Write-Host "ERR: $($_.Exception.Message)"
    if ($_.Exception.Response) {
        foreach ($k in $_.Exception.Response.Headers.Keys) {
            $v = $_.Exception.Response.Headers[$k] -join ", "
            Write-Host "$k : $v"
        }
    }
}

Write-Host ""
Write-Host "================================================================"
Write-Host "CEK 4: HTTP headers laris-landing.pages.dev (bandingkan)"
Write-Host "================================================================"
try {
    $r = Invoke-WebRequest -Uri "https://laris-landing.pages.dev/" -Headers @{"User-Agent"="Mozilla/5.0"} -UseBasicParsing -TimeoutSec 15
    foreach ($k in $r.Headers.Keys) {
        $v = $r.Headers[$k] -join ", "
        Write-Host "$k : $v"
    }
} catch {
    Write-Host "ERR: $($_.Exception.Message)"
}
