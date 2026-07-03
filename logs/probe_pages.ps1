param()
$ErrorActionPreference = "Continue"
$r = Invoke-WebRequest -Uri "https://laris-landing.pages.dev/" -UseBasicParsing -TimeoutSec 15
$content = $r.Content
Write-Host "Content length: $($r.RawContentLength)"
Write-Host "=== iframe 3D di HTML ==="
$matches = [regex]::Matches($content, '(src|href)="(laris-3d[^"]+)"')
$matches | ForEach-Object { $_.Value } | Sort-Object -Unique
Write-Host "=== Path /static ada? ==="
$stc = ([regex]::Matches($content, '/static/')).Count
Write-Host "/static/ count = $stc"
Write-Host "=== Robots & sitemap link ==="
$rb = ([regex]::Matches($content, 'robots\.txt')).Count
$sm = ([regex]::Matches($content, 'sitemap\.xml')).Count
Write-Host "robots.txt refs = $rb"
Write-Host "sitemap.xml refs = $sm"
