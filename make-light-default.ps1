<#
=====================================================================
 ABFverify - Make LIGHT the default theme
 ---------------------------------------------------------------------
 WHAT IT DOES
   1. Flips every "apply light only if saved" pre-paint script across
      all templates (site pages, accounts pages, dashboard, website)
      so LIGHT is applied unless the visitor explicitly chose dark.
   2. dashboard_base.js: removes the "follow system dark mode" branch
      - first-time visitors always get light.
   3. landing.js: the theme toggle icon now matches the light default.
   4. settings.py: switches the admin (jazzmin) from "darkly" to the
      light "default" theme so the admin panel is light too.

   Anyone who already picked dark mode keeps their choice - this only
   changes what NEW visitors (and cleared browsers) see first.
   The theme toggle buttons keep working exactly as before.

 HOW TO RUN (from the project root, next to manage.py):
   powershell -ExecutionPolicy Bypass -File .\make-light-default.ps1

 A .bak-light backup is kept next to every patched file.
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

function Read-Utf8([string]$path) {
    return [IO.File]::ReadAllText($path, (New-Object Text.UTF8Encoding($false)))
}
function Write-Utf8([string]$path, [string]$content) {
    [IO.File]::WriteAllText($path, $content, (New-Object Text.UTF8Encoding($false)))
}
function Backup-Once([string]$path) {
    $bak = "$path.bak-light"
    if ((Test-Path $path) -and -not (Test-Path $bak)) {
        Copy-Item $path $bak
        Write-Host "  backup -> $bak" -ForegroundColor DarkGray
    }
}

# ---------- 1) templates: light unless the visitor chose dark ----------
Write-Host "`n[1/4] Patching templates..." -ForegroundColor Green
$r1  = 'if (localStorage.getItem("theme") === "light") {'
$r1n = 'if (localStorage.getItem("theme") !== "dark") {'
$r2  = 'if (t === "light") {'
$r2n = 'if (t !== "dark") {'
$tplCount = 0
Get-ChildItem -Path (Join-Path $root "templates") -Recurse -Filter *.html | ForEach-Object {
    $c = Read-Utf8 $_.FullName
    if ($c.Contains($r1) -or $c.Contains($r2)) {
        Backup-Once $_.FullName
        $c = $c.Replace($r1, $r1n).Replace($r2, $r2n)
        Write-Utf8 $_.FullName $c
        $tplCount++
        Write-Host "  patched $($_.Name)" -ForegroundColor DarkGray
    }
}
Write-Host "  $tplCount template(s) now default to light" -ForegroundColor DarkGray

# ---------- 2) dashboard_base.js: first visit is always light ----------
Write-Host "`n[2/4] Patching static\js\dashboard_base.js..." -ForegroundColor Green
$dbjPath = Join-Path $root "static\js\dashboard_base.js"
if (Test-Path $dbjPath) {
    $dbj = (Read-Utf8 $dbjPath).Replace("`r`n", "`n")
    $r3 = "    } else if (window.matchMedia && window.matchMedia(`"(prefers-color-scheme: dark)`").matches) {`n        setTheme(false);`n    } else {"
    if ($dbj.Contains($r3)) {
        Backup-Once $dbjPath
        $dbj = $dbj.Replace($r3, "    } else {")
        Write-Utf8 $dbjPath $dbj
        Write-Host "  first-time visitors now always get light" -ForegroundColor DarkGray
    } else {
        Write-Host "  already patched (or system-dark branch not found), skipping" -ForegroundColor DarkGray
    }
} else {
    Write-Host "  WARNING: static\js\dashboard_base.js not found - skipping." -ForegroundColor Yellow
}

# ---------- 3) landing.js: toggle icon matches the light default ----------
Write-Host "`n[3/4] Patching static\js\landing.js..." -ForegroundColor Green
$ljPath = Join-Path $root "static\js\landing.js"
if (Test-Path $ljPath) {
    $lj = Read-Utf8 $ljPath
    $r4  = 'storedIsLight = localStorage.getItem("theme") === "light";'
    $r4n = 'storedIsLight = localStorage.getItem("theme") !== "dark";'
    if ($lj.Contains($r4)) {
        Backup-Once $ljPath
        $lj = $lj.Replace($r4, $r4n)
        Write-Utf8 $ljPath $lj
        Write-Host "  toggle initial state now light" -ForegroundColor DarkGray
    } else {
        Write-Host "  already patched, skipping" -ForegroundColor DarkGray
    }
} else {
    Write-Host "  WARNING: static\js\landing.js not found - skipping." -ForegroundColor Yellow
}

# ---------- 4) settings.py: admin panel light too ----------
Write-Host "`n[4/4] Patching config\settings.py (admin theme)..." -ForegroundColor Green
$settingsPath = Join-Path $root "config\settings.py"
$s = Read-Utf8 $settingsPath
$r5  = '    "theme": "darkly",'
$r5n = '    "theme": "default",'
if ($s.Contains($r5)) {
    Backup-Once $settingsPath
    $s = $s.Replace($r5, $r5n)
    Write-Utf8 $settingsPath $s
    Write-Host "  admin panel theme switched darkly -> default (light)" -ForegroundColor DarkGray
} else {
    Write-Host "  admin theme already light (or setting not found), skipping" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Green
Write-Host " LIGHT IS NOW THE DEFAULT THEME" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Commit + push:"
Write-Host "       git add ."
Write-Host "       git commit -m `"light theme default`""
Write-Host "       git push"
Write-Host "  2. Wait for Render 'Deploy live', then in the Render shell run:"
Write-Host "       python manage.py collectstatic --noinput"
Write-Host "  3. Hard-refresh your browser (Ctrl+Shift+R) or clear the cache"
Write-Host "     on your phone to see it."
Write-Host ""
Write-Host "Notes:" -ForegroundColor Cyan
Write-Host "  - Visitors who already chose dark mode keep dark mode."
Write-Host "  - The toggle buttons still work - anyone can switch themes."
Write-Host "  - YOUR browser may have saved 'dark' earlier: use the theme"
Write-Host "    toggle once (or clear site data) to see the light default."
Write-Host "  - To keep the ADMIN dark instead, open config\settings.py and"
Write-Host "    change `"theme`": `"default`", back to `"theme`": `"darkly`",."
Write-Host ""
Write-Host "Backups were saved as .bak-light next to each patched file." -ForegroundColor DarkGray
