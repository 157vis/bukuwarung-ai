param()
$ErrorActionPreference = "Continue"
function Get-Info {
    param([string]$Url)
    try {
        $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 15
        $title = ""
        if ($r.Content -match '<title>([^<]+)</title>') { $title = $matches[1] }
        return "HTTP=$($r.StatusCode) BYTES=$($r.RawContentLength) TITLE=$title"
    } catch {
        return "ERR=$($_.Exception.Message.Substring(0,60))"
    }
}

Write-Host "=== Final verification ==="
$urls = @(
    "https://www.larisai.my.id/",
    "https://www.larisai.my.id/laris-3d/koin_3d.html",
    "https://www.larisai.my.id/laris-3d/alur_3d.html",
    "https://www.larisai.my.id/laris-3d/stok_3d.html",
    "https://www.larisai.my.id/laris-3d/omzet_3d.html",
    "https://www.larisai.my.id/robots.txt",
    "https://www.larisai.my.id/sitemap.xml",
    "https://www.larisai.my.id/artikel/cara-mencatat-keuangan-warung/"
)
foreach ($u in $urls) {
    Write-Host ""
    Write-Host "URL: $u"
    Write-Host "  -> $(Get-Info $u)"
}
