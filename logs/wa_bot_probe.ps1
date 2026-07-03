param()
$ErrorActionPreference = "Continue"

function Probe {
    param([string]$Url, [string]$Name, [string]$Method = "GET", [int]$Timeout = 12)
    $start = Get-Date
    try {
        $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $Timeout -Method $Method
        $ms = ((Get-Date) - $start).TotalMilliseconds
        $body = $r.Content
        if ($body.Length -gt 200) { $body = $body.Substring(0,200) + "..." }
        $body = $body -replace "`n"," " -replace "`r"," "
        Write-Host ("[{0,-32}] {1,-6} {2,6} ms  {3}" -f $Name, $r.StatusCode, [int]$ms, $body)
    } catch {
        $ms = ((Get-Date) - $start).TotalMilliseconds
        $code = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { "ERR" }
        $body = ""
        try {
            $stream = $_.Exception.Response.GetResponseStream()
            $reader = New-Object System.IO.StreamReader($stream)
            $body = $reader.ReadToEnd()
            if ($body.Length -gt 100) { $body = $body.Substring(0,100) + "..." }
            $body = $body -replace "`n"," " -replace "`r"," "
        } catch {}
        Write-Host ("[{0,-32}] {1,-6} {2,6} ms  {3}" -f $Name, $code, [int]$ms, $body) -ForegroundColor Yellow
    }
}

Write-Host "=== bukuwarung-ai (CS webhook) ===" -ForegroundColor Cyan
Probe "https://bukuwarung-ai-larisai.up.railway.app/" "/"
Probe "https://bukuwarung-ai-larisai.up.railway.app/health" "/health"
Probe "https://bukuwarung-ai-larisai.up.railway.app/stats" "/stats"
Probe "https://bukuwarung-ai-larisai.up.railway.app/clients" "/clients"
Probe "https://bukuwarung-ai-larisai.up.railway.app/docs" "/docs"

Write-Host ""
Write-Host "=== kita-cuan-wa-bot (WA catat) ===" -ForegroundColor Cyan
Probe "https://kita-cuan-wa-bot-larisai.up.railway.app/" "/"
Probe "https://kita-cuan-wa-bot-larisai.up.railway.app/health" "/health"
Probe "https://kita-cuan-wa-bot-larisai.up.railway.app/docs" "/docs"

Write-Host ""
Write-Host "=== Test POST webhook (dummy) ===" -ForegroundColor Cyan
$payload = @{
    phone = "628112345678"
    message = "test pesan"
} | ConvertTo-Json
Probe "https://bukuwarung-ai-larisai.up.railway.app/webhook-whatsapp" "POST webhook" "POST"
Probe "https://bukuwarung-ai-larisai.up.railway.app/webhook/csat/test" "POST webhook/csat" "POST"
Probe "https://kita-cuan-wa-bot-larisai.up.railway.app/webhook" "POST webhook catat" "POST"
