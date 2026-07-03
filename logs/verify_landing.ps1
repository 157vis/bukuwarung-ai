param()
$ErrorActionPreference = "Continue"

function Get-PageInfo {
    param([string]$Url)
    try {
        $r = Invoke-WebRequest -Uri $Url -Headers @{"User-Agent"="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"} -UseBasicParsing -TimeoutSec 20
        $title = ""
        if ($r.Content -match '<title>([^<]+)</title>') { $title = $matches[1] }
        $desc = ""
        if ($r.Content -match '<meta\s+name="description"\s+content="([^"]+)"') { $desc = $matches[1] }
        $canon = ""
        if ($r.Content -match '<link rel="canonical" href="([^"]+)"') { $canon = $matches[1] }
        return [PSCustomObject]@{
            URL = $Url
            Status = $r.StatusCode
            Bytes = $r.RawContentLength
            Title = $title
            Desc = $desc
            Canonical = $canon
        }
    } catch {
        return [PSCustomObject]@{
            URL = $Url
            Status = "ERR"
            Bytes = 0
            Title = $_.Exception.Message
            Desc = ""
            Canonical = ""
        }
    }
}

$urls = @(
    "https://www.larisai.my.id/",
    "https://www.larisai.my.id/laris-3d/koin_3d.html",
    "https://www.larisai.my.id/laris-3d/alur_3d.html",
    "https://www.larisai.my.id/laris-3d/stok_3d.html",
    "https://www.larisai.my.id/laris-3d/omzet_3d.html",
    "https://www.larisai.my.id/robots.txt",
    "https://www.larisai.my.id/sitemap.xml",
    "https://www.larisai.my.id/artikel/cara-mencatat-keuangan-warung/",
    "https://laris-landing.pages.dev/laris-3d/koin_3d.html",
    "https://laris-landing.pages.dev/laris-3d/stok_3d.html",
    "https://laris-landing.pages.dev/laris-3d/omzet_3d.html"
)

Write-Host "================================================================"
Write-Host "CEK 1: URL utama + size + title"
Write-Host "================================================================"
foreach ($u in $urls) {
    $info = Get-PageInfo -Url $u
    $titleShort = if ($info.Title.Length -gt 70) { $info.Title.Substring(0, 70) + "..." } else { $info.Title }
    Write-Host ("[{0}] {1,-6} {2,7} B  {3}" -f $info.Status, $info.Status, $info.Bytes, $u)
    if ($info.Title) { Write-Host "    title: $titleShort" }
    if ($info.Canonical) { Write-Host "    canon: $($info.Canonical)" }
}
