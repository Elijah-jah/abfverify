# ============================================================================
# ABFverify - Restore dark admin (/semilore/) (v1)
# ============================================================================
# WHAT IT DOES
#   Puts the admin back to dark:
#     - "theme" back to "darkly" (the dark skin)
#     - adds "default_theme_mode": "dark" so the NEW Jazzmin keeps the
#       admin dark (the old dark_mode_theme setting is deprecated and
#       ignored by the new Jazzmin - that is the warning in your logs)
#     - removes the deprecated "dark_mode_theme" line if it is still there
#
#   Your customer-facing pages are NOT touched - the site keeps the
#   light default. This only changes the admin at /semilore/.
#
# Safe to re-run: it checks first and skips what is already done.
#
# HOW TO RUN
#   1. Copy this file into your project folder (next to manage.py).
#   2. In PowerShell, from that folder:
#        powershell -ExecutionPolicy Bypass -File .\restore-dark-admin.ps1
#   3. Then:
#        git add .
#        git commit -m "restore dark admin"
#        git push
#   4. Wait for Render "Deploy live" - done. No shell commands needed.
# ============================================================================

$ErrorActionPreference = "Stop"

function Read-Utf8([string]$p)  { [IO.File]::ReadAllText($p) }
function Write-Utf8([string]$p, [string]$c) {
    [IO.File]::WriteAllText($p, $c, (New-Object System.Text.UTF8Encoding($false)))
}
function Backup-Once([string]$p) {
    $bak = "$p.bak-darkadmin"
    if (-not (Test-Path $bak)) { Copy-Item $p $bak }
}
function Count-Occurrences([string]$hay, [string]$needle) {
    $n = 0; $i = 0
    while (($i = $hay.IndexOf($needle, $i)) -ge 0) { $n++; $i += $needle.Length }
    return $n
}

# ---------- locate the project root ----------
$root = (Get-Location).Path
if (-not (Test-Path (Join-Path $root "manage.py"))) {
    Write-Host "ERROR: manage.py not found here." -ForegroundColor Red
    Write-Host "cd into your project folder (the one that contains manage.py) and run again." -ForegroundColor Yellow
    exit 1
}
Write-Host "Project root: $root" -ForegroundColor Cyan
Write-Host "UPDATE VERSION: v1 (restore dark admin)" -ForegroundColor Magenta

# ---------- config/settings.py ----------
Write-Host "`n[1/1] Restoring the dark admin theme..." -ForegroundColor Green
$setPath = Join-Path $root "config\settings.py"
if (-not (Test-Path $setPath)) {
    Write-Host "  ERROR: config\settings.py not found - nothing changed." -ForegroundColor Red
    exit 1
}

$hadCrlf = (Read-Utf8 $setPath).Contains("`r`n")
$st = (Read-Utf8 $setPath).Replace("`r`n", "`n")
$changed = $false

$themeDefault = '    "theme": "default",' + "`n"
$themeDarkly  = '    "theme": "darkly",' + "`n"
$darkModeLine = '    "dark_mode_theme": "darkly",' + "`n"
$modeDark     = '    "default_theme_mode": "dark",' + "`n"
$modeLight    = '    "default_theme_mode": "light",' + "`n"
$modeAuto     = '    "default_theme_mode": "auto",' + "`n"

# 1. theme back to darkly
if ($st.Contains($themeDefault)) {
    $st = $st.Replace($themeDefault, $themeDarkly)
    $changed = $true
    Write-Host "  theme: default -> darkly" -ForegroundColor DarkGray
} elseif ($st.Contains($themeDarkly)) {
    Write-Host "  theme already darkly" -ForegroundColor DarkGray
} else {
    Write-Host "  WARNING: no jazzmin theme line found in settings.py - no changes made." -ForegroundColor Yellow
    Write-Host "  Send me the output so I can adjust the patch." -ForegroundColor Yellow
    exit 1
}

# 2. remove deprecated dark_mode_theme (the log warning)
if ($st.Contains($darkModeLine)) {
    $st = $st.Replace($darkModeLine, "")
    $changed = $true
    Write-Host "  deprecated dark_mode_theme line removed" -ForegroundColor DarkGray
}

# 3. force dark mode in the new jazzmin
if ($st.Contains($modeDark)) {
    Write-Host "  default_theme_mode already dark" -ForegroundColor DarkGray
} else {
    if ($st.Contains($modeLight)) { $st = $st.Replace($modeLight, $modeDark); $changed = $true }
    if ($st.Contains($modeAuto))  { $st = $st.Replace($modeAuto,  $modeDark); $changed = $true }
    if (-not $st.Contains('"default_theme_mode"')) {
        if ((Count-Occurrences $st $themeDarkly) -ne 1) {
            Write-Host "  WARNING: could not find a place to insert default_theme_mode - skipped." -ForegroundColor Yellow
        } else {
            $st = $st.Replace($themeDarkly, $themeDarkly + $modeDark)
            $changed = $true
        }
    }
    Write-Host "  default_theme_mode: dark set" -ForegroundColor DarkGray
}

if ($changed) {
    Backup-Once $setPath
    if ($hadCrlf) { $st = $st.Replace("`n", "`r`n") }
    Write-Utf8 $setPath $st
    Write-Host "  settings.py updated" -ForegroundColor DarkGray
} else {
    Write-Host "  nothing to change" -ForegroundColor DarkGray
}

# ---------- done ----------
Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host " Done! Next steps:" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Check it:" -ForegroundColor White
Write-Host "     findstr /C:""default_theme_mode"" config\settings.py" -ForegroundColor Gray
Write-Host "   It should print:    ""default_theme_mode"": ""dark""," -ForegroundColor Gray
Write-Host ""
Write-Host "2. Publish to Render:" -ForegroundColor White
Write-Host "     git add ." -ForegroundColor Gray
Write-Host "     git commit -m ""restore dark admin""" -ForegroundColor Gray
Write-Host "     git push" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Wait for Render 'Deploy live', then hard-refresh the admin" -ForegroundColor White
Write-Host "   (Ctrl+Shift+R). No migrate or collectstatic needed." -ForegroundColor White
Write-Host ""
Write-Host "Your website stays light-default - only the admin goes back to dark." -ForegroundColor White
