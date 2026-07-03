param()
$ErrorActionPreference = "Continue"

function Probe {
    param([string]$Url, [string]$Name, [int]$Timeout = 10)
    $start = Get-Date
    try {
        $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $Timeout -MaximumRedirection 0
        $ms = ((Get-Date) - $start).TotalMilliseconds
        $body = $r.Content
        $firstLine = ($body -split "`n" | Select-Object -First 1).Trim()
        if ($firstLine.Length -gt 80) { $firstLine = $firstLine.Substring(0,80) + "..." }
        $kind = if ($body -match 'streamlit|StreamlitInc') { "STREAMLIT" }
                elseif ($body -match 'FastAPI|status|bot_logic') { "FASTAPI" }
                else { "HTML" }
        Write-Host ("[{0,-22}] {1,4}  {2,5} ms  {3,-10}  {4}" -f $Name, $r.StatusCode, [int]$ms, $kind, $firstLine)
    } catch {
        $ms = ((Get-Date) - $start).TotalMilliseconds
        $code = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { "ERR" }
        Write-Host ("[{0,-22}] {1,4}  {2,5} ms" -f $Name, $code, [int]$ms) -ForegroundColor Yellow
    }
}

Write-Host "=== Status semua service Railway + Cloudflare ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "[Landing Pages]"
Probe "https://www.larisai.my.id/" "www.larisai.my.id"
Probe "https://www.larisai.my.id/fitur/" "/fitur/"
Probe "https://www.larisai.my.id/harga/" "/harga/"
Probe "https://www.larisai.my.id/robots.txt" "robots.txt"
Probe "https://www.larisai.my.id/sitemap.xml" "sitemap.xml"
Probe "https://www.larisai.my.id/laris-3d/koin_3d.html" "3D koin"

Write-Host ""
Write-Host "[Streamlit Dashboard]"
Probe "https://larisai.my.id/" "larisai.my.id"
Probe "https://larisai.my.id/_stcore/health" "streamlit health"
Probe "https://larisai.my.id/?login=1" "login page"

Write-Host ""
Write-Host "[Railway - CS Webhook]"
Probe "https://bukuwarung-ai-larisai.up.railway.app/" "root"
Probe "https://bukuwarung-ai-larisai.up.railway.app/health" "/health"
Probe "https://bukuwarung-ai-larisai.up.railway.app/stats" "/stats"

Write-Host ""
Write-Host "[Railway - WA Catat]"
Probe "https://kita-cuan-wa-bot-larisai.up.railway.app/" "root"
Probe "https://kita-cuan-wa-bot-larisai.up.railway.app/health" "/health"
Probe "https://kita-cuan-wa-bot-larisai.up.railway.app/webhook" "/webhook" 8
