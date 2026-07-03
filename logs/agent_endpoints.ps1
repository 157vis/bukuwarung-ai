param()
$ErrorActionPreference = "Continue"

function Probe {
    param([string]$Url, [string]$Name, [string]$Method = "GET", [int]$Timeout = 12)
    $start = Get-Date
    try {
        $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $Timeout -Method $Method
        $ms = ((Get-Date) - $start).TotalMilliseconds
        $body = $r.Content
        if ($body.Length -gt 80) { $body = $body.Substring(0,80) + "..." }
        $body = $body -replace "`n"," " -replace "`r"," "
        Write-Host ("[{0,-32}] {1,-6} {2,6} ms  {3}" -f $Name, $r.StatusCode, [int]$ms, $body)
    } catch {
        $ms = ((Get-Date) - $start).TotalMilliseconds
        $code = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { "ERR" }
        Write-Host ("[{0,-32}] {1,-6} {2,6} ms" -f $Name, $code, [int]$ms) -ForegroundColor Yellow
    }
}

Write-Host "=== Endpoints spesifik agen AI ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "[bukuwarung-ai (seharusnya webhook CS)]"
Probe "https://bukuwarung-ai-larisai.up.railway.app/" "bukuwarung-ai root"
Probe "https://bukuwarung-ai-larisai.up.railway.app/health" "/health"
Probe "https://bukuwarung-ai-larisai.up.railway.app/stats" "/stats"
Probe "https://bukuwarung-ai-larisai.up.railway.app/clients" "/clients"
Probe "https://bukuwarung-ai-larisai.up.railway.app/webhook-whatsapp" "/webhook-whatsapp" "POST"
Probe "https://bukuwarung-ai-larisai.up.railway.app/webhook/csat/test123" "/webhook/csat/{id}" "POST"

Write-Host ""
Write-Host "[kita-cuan-wa-bot (WA bot catat)]"
Probe "https://kita-cuan-wa-bot-larisai.up.railway.app/" "kita-cuan-wa-bot root"
Probe "https://kita-cuan-wa-bot-larisai.up.railway.app/health" "/health"
Probe "https://kita-cuan-wa-bot-larisai.up.railway.app/webhook" "/webhook" "POST"
Probe "https://kita-cuan-wa-bot-larisai.up.railway.app/webhook/test123" "/webhook/{id}" "POST"

Write-Host ""
Write-Host "[Streamlit app utama]"
Probe "https://larisai.my.id/" "larisai.my.id"
Probe "https://larisai.my.id/_stcore/health" "streamlit health"
Probe "https://larisai.my.id/?login=1" "login page"

Write-Host ""
Write-Host "[Landing]"
Probe "https://www.larisai.my.id/" "www.larisai.my.id"
Probe "https://www.larisai.my.id/laris-3d/koin_3d.html" "3D koin"
Probe "https://www.larisai.my.id/laris-3d/omzet_3d.html" "3D omzet"
