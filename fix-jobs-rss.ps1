#Requires -Version 5.1
<#
    ABFverify - Fix scheduler after RSS switch (v1)
    ===============================================
    accounts/jobs.py still imports GoodLuckBoostHub, which no longer exists,
    so APScheduler fails to start (order status sync + expiry jobs stopped).
    This renames the last 3 references to ReallySimpleSocial.
#>

$ErrorActionPreference = 'Stop'

Write-Host ""
Write-Host "======================================================" -ForegroundColor Magenta
Write-Host "   ABFverify - Fix accounts\jobs.py provider refs  v1" -ForegroundColor Magenta
Write-Host "======================================================" -ForegroundColor Magenta
Write-Host ""

# Encoding-safe reader (handles UTF-8, UTF-16 with/without BOM)
function Read-Any([string]$Path) {
    $bytes = [IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -ge 2) {
        if ($bytes[0] -eq 0xFF -and $bytes[1] -eq 0xFE) {
            return [Text.Encoding]::Unicode.GetString($bytes, 2, $bytes.Length - 2)
        }
        if ($bytes[0] -eq 0xFE -and $bytes[1] -eq 0xFF) {
            return [Text.Encoding]::BigEndianUnicode.GetString($bytes, 2, $bytes.Length - 2)
        }
        if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
            return [Text.Encoding]::UTF8.GetString($bytes, 3, $bytes.Length - 3)
        }
    }
    $probe = [Math]::Min($bytes.Length, 400)
    $nuls = 0
    for ($i = 0; $i -lt $probe; $i++) { if ($bytes[$i] -eq 0) { $nuls++ } }
    if ($probe -gt 0 -and $nuls -gt ($probe / 4)) {
        return [Text.Encoding]::Unicode.GetString($bytes, 0, $bytes.Length)
    }
    return [Text.Encoding]::UTF8.GetString($bytes, 0, $bytes.Length)
}

$root = (Get-Location).Path
$jobsPath = Join-Path $root 'accounts\jobs.py'
if (-not (Test-Path $jobsPath)) { throw "accounts\jobs.py not found - run from the project root." }

$jobs = Read-Any $jobsPath
if (-not $jobs.Contains('GoodLuckBoostHub')) {
    Write-Host "  [SKIP] accounts\jobs.py has no GoodLuckBoostHub references - already fixed" -ForegroundColor DarkGray
} else {
    Copy-Item $jobsPath "$jobsPath.bak-jobs" -Force
    $jobs = $jobs.Replace('GoodLuckBoostHub', 'ReallySimpleSocial').Replace('GLBH_API_KEY', 'RSS_API_KEY')
    [IO.File]::WriteAllText($jobsPath, $jobs, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "  [OK] accounts\jobs.py now uses ReallySimpleSocial" -ForegroundColor Green

    Write-Host ""
    Write-Host "Committing and pushing..." -ForegroundColor Cyan
    git add -A
    git commit -m "Fix scheduler: point accounts/jobs.py at ReallySimpleSocial"
    git push
}

Write-Host ""
Write-Host "DONE. After Render redeploys, the APScheduler error will be gone and" -ForegroundColor Green
Write-Host "boost order status sync will run every 5 minutes again." -ForegroundColor Green
Write-Host "You can confirm in the Render logs: no more 'APScheduler failed to start'." -ForegroundColor Green
Write-Host ""
