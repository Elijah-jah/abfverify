#Requires -Version 5.1
<#
    ABFverify - Fix boost migration conflict (v1)
    =============================================
    The repo already had boost/migrations/0007_alter_boostservice_rate_and_more.py
    and the RSS installer added 0007_alter_boostsettings_exchange_rate_and_more.py
    -> two 0007s = "multiple leaf nodes" error, deploy fails.

    Fix:
      1. delete the installer's 0007 (it only changed field help text - no DB schema)
      2. regenerate it properly as 0008 on top of YOUR existing 0007 via makemigrations
      3. run migrate locally to prove it applies
      4. commit + push so Render deploys cleanly
#>

$ErrorActionPreference = 'Stop'

Write-Host ""
Write-Host "======================================================" -ForegroundColor Magenta
Write-Host "   ABFverify - Fix boost migration conflict  v1" -ForegroundColor Magenta
Write-Host "======================================================" -ForegroundColor Magenta
Write-Host ""

$root = (Get-Location).Path
$migDir = Join-Path $root 'boost\migrations'
$mine   = Join-Path $migDir '0007_alter_boostsettings_exchange_rate_and_more.py'

if (-not (Test-Path (Join-Path $root 'manage.py'))) {
    Write-Host "Run this from the project root (where manage.py is)." -ForegroundColor Red
    exit 1
}

# --- 1. remove the installer's conflicting 0007 -------------------------
if (Test-Path $mine) {
    $c = [IO.File]::ReadAllText($mine)
    if ($c.Contains('Switches boost pricing labels to USD')) {
        Remove-Item $mine -Force
        Write-Host "  [OK] removed conflicting 0007_alter_boostsettings_exchange_rate_and_more.py" -ForegroundColor Green
    } else {
        throw "$mine exists but is not the installer file - not touching it. Send me the file list of boost\migrations."
    }
} else {
    Write-Host "  [SKIP] conflicting file already gone" -ForegroundColor DarkGray
}

# --- 2. regenerate the label migration on top of the real chain --------
Write-Host ""
Write-Host "Regenerating the migration with your own Django..." -ForegroundColor Cyan
python manage.py makemigrations boost
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "makemigrations failed. Make sure your venv is active (you should see (venv)" -ForegroundColor Yellow
    Write-Host "in front of the prompt), then re-run this script." -ForegroundColor Yellow
    exit 1
}

# --- 3. prove it applies ------------------------------------------------
Write-Host ""
Write-Host "Applying migrations locally to verify..." -ForegroundColor Cyan
python manage.py migrate
if ($LASTEXITCODE -ne 0) {
    Write-Host "migrate failed locally - paste the error to me before pushing." -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] migrations apply cleanly" -ForegroundColor Green

# --- 4. commit + push ---------------------------------------------------
Write-Host ""
Write-Host "Committing and pushing..." -ForegroundColor Cyan
git add -A
git commit -m "Fix boost migration conflict: regenerate label migration on top of existing 0007"
git push

Write-Host ""
Write-Host "DONE. Render will redeploy automatically - the site should come back up." -ForegroundColor Green
Write-Host "Watch the Render logs; 'python manage.py migrate' should pass this time." -ForegroundColor Green
Write-Host ""
