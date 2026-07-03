param()
$ErrorActionPreference = "Continue"

function Probe-Url {
    param([string]$Url, [string]$Name)
    $start = Get-Date
    try {
        $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 12 -Method GET
        $ms = ((Get-Date) - $start).TotalMilliseconds
        $code = $r.StatusCode
        $bytes = $r.RawContentLength
        $title = ""
        if ($r.Content -match '<title>([^<]+)</title>') { $title = $matches[1] }
        Write-Host ("[{0,-22}] {1,-6} {2,7} B  {3,6} ms  {4}" -f $Name, $code, $bytes, [int]$ms, $title)
    } catch {
        $ms = ((Get-Date) - $start).TotalMilliseconds
        $code = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { "ERR" }
        $msg = $_.Exception.Message
        if ($msg.Length -gt 60) { $msg = $msg.Substring(0,60) + "..." }
        Write-Host ("[{0,-22}] {1,-6} {2,7} B  {3,6} ms  {4}" -f $Name, $code, "-", [int]$ms, $msg) -ForegroundColor Yellow
    }
}

Write-Host "=== HEALTH CHECK SEMUA AGEN AI ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "[Domain Landing]"
Probe-Url "https://www.larisai.my.id/" "www.larisai.my.id"
Probe-Url "https://www.larisai.my.id/robots.txt" "robots.txt"
Probe-Url "https://www.larisai.my.id/sitemap.xml" "sitemap.xml"

Write-Host ""
Write-Host "[Domain App Streamlit]"
Probe-Url "https://larisai.my.id/" "larisai.my.id"
Probe-Url "https://larisai.my.id/?login=1" "login page"
Probe-Url "https://larisai.my.id/_stcore/health" "streamlit health"

Write-Host ""
Write-Host "[Railway Services]"
Probe-Url "https://bukuwarung-ai-larisai.up.railway.app/" "bukuwarung-ai root"
Probe-Url "https://bukuwarung-ai-larisai.up.railway.app/health" "bukuwarung-ai health"
Probe-Url "https://bukuwarung-ai-larisai.up.railway.app/docs" "bukuwarung-ai docs"
Probe-Url "https://kita-cuan-wa-bot-larisai.up.railway.app/" "kita-cuan-wa-bot root"
Probe-Url "https://kita-cuan-wa-bot-larisai.up.railway.app/health" "kita-cuan-wa-bot health"
Probe-Url "https://kita-cuan-wa-bot-larisai.up.railway.app/docs" "kita-cuan-wa-bot docs"
