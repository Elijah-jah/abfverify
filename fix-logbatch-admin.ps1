# ============================================================================
# ABFverify - FIX: admin Log Batch page 500 error (v1)
# ============================================================================
# WHAT IT FIXES
#   The /semilore/finance/logbatch/ admin page crashes with:
#     TypeError: args or kwargs must be provided.  (format_html)
#   Newer Django versions no longer allow format_html() with only a
#   string and no values. finance\admin.py does exactly that in the
#   status_badge column. This script rewrites both calls so the page
#   loads again.
#
#   It also removes the deprecated "dark_mode_theme" line from the
#   Jazzmin settings (that line is why you see the JAZZMIN_UI_TWEAKS
#   warning in the logs - it is ignored by the new Jazzmin anyway).
#
# Safe to re-run: every step checks first and skips what is already done.
#
# HOW TO RUN
#   1. Copy this file into your project folder (next to manage.py).
#   2. In PowerShell, from that folder:
#        powershell -ExecutionPolicy Bypass -File .\fix-logbatch-admin.ps1
#   3. Then:
#        git add .
#        git commit -m "fix logbatch admin 500"
#        git push
#   4. Wait for Render "Deploy live" - done. No shell commands needed
#      (no database changes, no static files).
# ============================================================================

$ErrorActionPreference = "Stop"

function Read-Utf8([string]$p)  { [IO.File]::ReadAllText($p) }
function Write-Utf8([string]$p, [string]$c) {
    [IO.File]::WriteAllText($p, $c, (New-Object System.Text.UTF8Encoding($false)))
}
function Decode([string]$b64) { [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b64)) }
function Backup-Once([string]$p) {
    $bak = "$p.bak-fix500"
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
Write-Host "UPDATE VERSION: v1 (logbatch admin 500 fix)" -ForegroundColor Magenta

$ADM_A1_B64 = "ICAgICAgICAgICAgcmV0dXJuIGZvcm1hdF9odG1sKCc8c3BhbiBzdHlsZT0iY29sb3I6IzI4YTc0NTtmb250LXdlaWdodDpib2xkIj5DT05GSVJNRUQ8L3NwYW4+Jyk="
$ADM_R1_B64 = "ICAgICAgICAgICAgcmV0dXJuIGZvcm1hdF9odG1sKCc8c3BhbiBzdHlsZT0iY29sb3I6IzI4YTc0NTtmb250LXdlaWdodDpib2xkIj57fTwvc3Bhbj4nLCAiQ09ORklSTUVEIik="
$ADM_A2_B64 = "ICAgICAgICByZXR1cm4gZm9ybWF0X2h0bWwoJzxzcGFuIHN0eWxlPSJjb2xvcjojZmZjMTA3O2ZvbnQtd2VpZ2h0OmJvbGQiPlBFTkRJTkc8L3NwYW4+Jyk="
$ADM_R2_B64 = "ICAgICAgICByZXR1cm4gZm9ybWF0X2h0bWwoJzxzcGFuIHN0eWxlPSJjb2xvcjojZmZjMTA3O2ZvbnQtd2VpZ2h0OmJvbGQiPnt9PC9zcGFuPicsICJQRU5ESU5HIik="
$SET_A_B64 = "ICAgICJkYXJrX21vZGVfdGhlbWUiOiAiZGFya2x5IiwK"

# ---------- 1) finance/admin.py: fix the two format_html calls ----------
Write-Host "`n[1/2] Fixing finance\admin.py..." -ForegroundColor Green
$admPath = Join-Path $root "finance\admin.py"
if (-not (Test-Path $admPath)) {
    Write-Host "  WARNING: finance\admin.py not found - skipping." -ForegroundColor Yellow
} else {
    $hadCrlf = (Read-Utf8 $admPath).Contains("`r`n")
    $adm = (Read-Utf8 $admPath).Replace("`r`n", "`n")
    if ($adm.Contains('font-weight:bold">{}</span>')) {
        Write-Host "  already fixed, skipping" -ForegroundColor DarkGray
    } else {
        $a1 = Decode $ADM_A1_B64
        $a2 = Decode $ADM_A2_B64
        if ((Count-Occurrences $adm $a1) -ne 1 -or (Count-Occurrences $adm $a2) -ne 1) {
            Write-Host "  WARNING: expected code not found in finance\admin.py - no changes made." -ForegroundColor Yellow
            Write-Host "  Send me the output so I can adjust the patch." -ForegroundColor Yellow
        } else {
            Backup-Once $admPath
            $adm = $adm.Replace($a1, (Decode $ADM_R1_B64))
            $adm = $adm.Replace($a2, (Decode $ADM_R2_B64))
            if ($hadCrlf) { $adm = $adm.Replace("`n", "`r`n") }
            Write-Utf8 $admPath $adm
            Write-Host "  status_badge format_html calls fixed" -ForegroundColor DarkGray
        }
    }
}

# ---------- 2) config/settings.py: drop deprecated dark_mode_theme ----------
Write-Host "`n[2/2] Removing the deprecated jazzmin dark_mode_theme line..." -ForegroundColor Green
$setPath = Join-Path $root "config\settings.py"
if (-not (Test-Path $setPath)) {
    Write-Host "  WARNING: config\settings.py not found - skipping." -ForegroundColor Yellow
} else {
    $hadCrlf = (Read-Utf8 $setPath).Contains("`r`n")
    $st = (Read-Utf8 $setPath).Replace("`r`n", "`n")
    $a = Decode $SET_A_B64
    if ((Count-Occurrences $st $a) -eq 0) {
        Write-Host "  dark_mode_theme line not present, skipping" -ForegroundColor DarkGray
    } else {
        Backup-Once $setPath
        $st = $st.Replace($a, "")
        if ($hadCrlf) { $st = $st.Replace("`n", "`r`n") }
        Write-Utf8 $setPath $st
        Write-Host "  dark_mode_theme line removed (warning will stop)" -ForegroundColor DarkGray
    }
}

# ---------- done ----------
Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host " Done! Next steps:" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Check the fix:" -ForegroundColor White
Write-Host "     findstr /C:""CONFIRMED"""" finance\admin.py" -ForegroundColor Gray
Write-Host "   It should show the new line with {} in it." -ForegroundColor Gray
Write-Host ""
Write-Host "2. Publish to Render:" -ForegroundColor White
Write-Host "     git add ." -ForegroundColor Gray
Write-Host "     git commit -m ""fix logbatch admin 500""" -ForegroundColor Gray
Write-Host "     git push" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Wait for Render 'Deploy live' - that is all. No migrate, no" -ForegroundColor White
Write-Host "   collectstatic needed. Then open /semilore/finance/logbatch/ again." -ForegroundColor White
