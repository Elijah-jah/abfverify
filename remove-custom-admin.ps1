<#
=====================================================================
 ABFverify - Remove the custom admin landing page
 ---------------------------------------------------------------------
 Deletes ONLY templates/admin/index.html so that /semilore/ goes back
 to the default Django admin (the app list that updates itself when
 you add new models, logs, etc.).

 KEPT UNTOUCHED:
   - Finance pages (dashboard, analytics, inventory, rewards, gift orders)
   - The glowing gift bell on finance pages
   - Logo upload (Site Settings app) - it will show inside the default
     admin app list, and your uploaded logo keeps working site-wide
   - Gift sales recording in the finance totals

 HOW TO RUN (from the project root, next to manage.py):
   powershell -ExecutionPolicy Bypass -File .\remove-custom-admin.ps1
=====================================================================
#>

$ErrorActionPreference = "Stop"

$root = Get-Location
if (-not (Test-Path (Join-Path $root "manage.py"))) {
    Write-Host "ERROR: manage.py not found." -ForegroundColor Red
    Write-Host "cd into your project root (next to manage.py) and run again." -ForegroundColor Yellow
    exit 1
}
Write-Host "Project root: $root" -ForegroundColor Cyan

$target = Join-Path $root "templates\admin\index.html"
if (Test-Path $target) {
    Remove-Item $target -Force
    Write-Host "  deleted templates\admin\index.html" -ForegroundColor Green
} else {
    Write-Host "  templates\admin\index.html not found - already removed, nothing to do." -ForegroundColor DarkGray
}

# Remove the now-empty templates\admin folder if nothing else lives in it.
$adminDir = Join-Path $root "templates\admin"
if ((Test-Path $adminDir) -and -not (Get-ChildItem $adminDir -Force)) {
    Remove-Item $adminDir -Force
    Write-Host "  removed the empty templates\admin folder" -ForegroundColor Green
}

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Green
Write-Host " CUSTOM ADMIN PAGE REMOVED" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Commit + push the deletion:"
Write-Host "       git add ."
Write-Host "       git commit -m `"remove custom admin page`""
Write-Host "       git push"
Write-Host "  2. Wait for Render to finish deploying (Events tab -> 'Deploy live')."
Write-Host "  3. /semilore/ will show the default Django admin app list again."
Write-Host "     (Site Settings / logo upload is listed there under 'Site Settings'.)"
Write-Host ""
Write-Host "NOTE: if you ever re-run install_gifts.ps1 it will recreate the custom" -ForegroundColor DarkGray
Write-Host "admin page - just run this script again afterwards to remove it." -ForegroundColor DarkGray
