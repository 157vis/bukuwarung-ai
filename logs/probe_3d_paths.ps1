param()
$ErrorActionPreference = "Continue"
function Get-Size {
    param([string]$Url)
    try {
        $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10
        $title = ""
        if ($r.Content -match '<title>([^<]+)</title>') { $title = $matches[1] }
        return "$($r.StatusCode) | $($r.RawContentLength) B | $title"
    } catch {
        return "ERR | $($_.Exception.Message.Substring(0,60))"
    }
}

Write-Host "=== Path attempts for 3D file ==="
$urls = @(
    "https://www.larisai.my.id/static/laris-3d/koin_3d.html",
    "https://www.larisai.my.id/static/laris-3d/alur_3d.html",
    "https://www.larisai.my.id/static/laris-3d/stok_3d.html",
    "https://www.larisai.my.id/static/laris-3d/omzet_3d.html",
    "https://www.larisai.my.id/laris-3d/koin_3d.html"
)
foreach ($u in $urls) { Write-Host "  $u"; Write-Host "    -> $(Get-Size $u)" }
