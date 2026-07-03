param()
$ErrorActionPreference = "Continue"

function Get-PageInfo {
    param([string]$Url)
    try {
        $r = Invoke-WebRequest -Uri $Url -Headers @{"User-Agent"="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"} -UseBasicParsing -TimeoutSec 20
        $title = ""
        if ($r.Content -match '<title>([^<]+)</title>') { $title = $matches[1] }
        $hasWorker = ($r.Headers["Server-Timing"] -match 'cfWorker')
        return [PSCustomObject]@{
            URL = $Url
            Status = $r.StatusCode
            Bytes = $r.RawContentLength
            Title = $title
            CfWorker = $hasWorker
            ServerTiming = $r.Headers["Server-Timing"]
        }
    } catch {
        return [PSCustomObject]@{
            URL = $Url
            Status = "ERR"
            Bytes = 0
            Title = $_.Exception.Message.Substring(0, [Math]::Min(60, $_.Exception.Message.Length))
            CfWorker = "?"
            ServerTiming = ""
        }
    }
}

$urls = @(
    "https://www.larisai.my.id/",
    "https://www.larisai.my.id/laris-3d/koin_3d.html",
    "https://www.larisai.my.id/laris-3d/stok_3d.html",
    "https://www.larisai.my.id/laris-3d/omzet_3d.html",
    "https://www.larisai.my.id/artikel/cara-mencatat-keuangan-warung/",
    "https://laris-landing.pages.dev/laris-3d/koin_3d.html",
    "https://laris-landing.pages.dev/laris-3d/stok_3d.html"
)

Write-Host "================================================================"
Write-Host "RE-VERIFY setelah fix"
Write-Host "================================================================"
foreach ($u in $urls) {
    $info = Get-PageInfo -Url $u
    $titleShort = if ($info.Title.Length -gt 60) { $info.Title.Substring(0, 60) + "..." } else { $info.Title }
    Write-Host ""
    Write-Host "[$($info.Status)] $($info.Bytes) B  $titleShort"
    Write-Host "  URL: $($info.URL)"
    Write-Host "  cfWorker: $($info.CfWorker)   Server-Timing: $($info.ServerTiming)"
}
