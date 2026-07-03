param()
$ErrorActionPreference = "Continue"
function Get-Info {
    param([string]$Url)
    try {
        $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 15
        $title = ""
        if ($r.Content -match '<title>([^<]+)</title>') { $title = $matches[1] }
        $redir = $r.Headers["Location"]
        return "HTTP=$($r.StatusCode) BYTES=$($r.RawContentLength) TITLE=$title LOC=$redir"
    } catch {
        $code = $null
        if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
        return "ERR=$code $($_.Exception.Message.Substring(0,60))"
    }
}

Write-Host "=== Direct file URL ==="
$urls = @(
    "https://www.larisai.my.id/laris-3d/koin_3d.html",
    "https://www.larisai.my.id/laris-3d/alur_3d.html",
    "https://www.larisai.my.id/laris-3d/stok_3d.html",
    "https://www.larisai.my.id/laris-3d/omzet_3d.html"
)
foreach ($u in $urls) {
    Write-Host "$u"
    Write-Host "  -> $(Get-Info $u)"
}
