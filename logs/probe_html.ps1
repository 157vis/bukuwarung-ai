param()
$ErrorActionPreference = "Continue"
$r = Invoke-WebRequest -Uri "https://laris-landing.pages.dev/" -UseBasicParsing -TimeoutSec 15
$content = $r.Content
Write-Host "=== Cek elemen penting di HTML yang disajikan ==="
$checks = @(
  '3D Knowledge Lab','Alur Data 3D','Rak Stok 3D','Grafik Omzet 3D',
  'koin_3d.html','alur_3d.html','stok_3d.html','omzet_3d.html',
  'robots.txt','sitemap.xml','Cara Mencatat Keuangan','Baca Artikel UMKM',
  'Tombol','/laris-3d/'
)
foreach ($c in $checks) {
  $n = ([regex]::Matches($content, [regex]::Escape($c))).Count
  "  '{0,-35}' = {1}" -f $c, $n
}
Write-Host "=== Total length ==="
Write-Host "len(content) = $($content.Length)"
Write-Host "rawContentLength = $($r.RawContentLength)"
Write-Host "=== Snippet awal (head 800 char) ==="
Write-Host $content.Substring(0, [Math]::Min(800, $content.Length))
