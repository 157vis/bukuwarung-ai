param()
$ErrorActionPreference = "Continue"

# Test kirim payload webhook langsung (simulasi Fonnte)
$body = @'
{
  "device": "test",
  "sender": "628112345678",
  "name": "Test User",
  "message": "jual kopi 50000"
}
'@

Write-Host "=== Test webhook bukuwarung-ai-larisai ===" -ForegroundColor Cyan
try {
    $r = Invoke-WebRequest -Uri "https://bukuwarung-ai-larisai.up.railway.app/webhook-whatsapp" `
        -UseBasicParsing -TimeoutSec 15 -Method POST -ContentType "application/json" -Body $body
    Write-Host "  Status: $($r.StatusCode)"
    Write-Host "  Body: $($r.Content.Substring(0, [Math]::Min(300, $r.Content.Length)))"
} catch {
    $code = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { "ERR" }
    Write-Host "  Status: $code" -ForegroundColor Yellow
    Write-Host "  Err: $($_.Exception.Message.Substring(0, 100))"
}

Write-Host ""
Write-Host "=== Test webhook kita-cuan-wa-bot ===" -ForegroundColor Cyan
try {
    $r = Invoke-WebRequest -Uri "https://kita-cuan-wa-bot-larisai.up.railway.app/webhook" `
        -UseBasicParsing -TimeoutSec 15 -Method POST -ContentType "application/json" -Body $body
    Write-Host "  Status: $($r.StatusCode)"
    Write-Host "  Body: $($r.Content.Substring(0, [Math]::Min(300, $r.Content.Length)))"
} catch {
    $code = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { "ERR" }
    Write-Host "  Status: $code" -ForegroundColor Yellow
    Write-Host "  Err: $($_.Exception.Message.Substring(0, 100))"
}
