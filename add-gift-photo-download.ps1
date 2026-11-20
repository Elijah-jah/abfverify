# ============================================================================
# ABFverify - Gift order photos: Download-all button (v1)
# ============================================================================
# WHAT IT DOES
#   On Finance -> Gift Orders, every order that has customer pictures now
#   shows a "Download all" button beside the pictures. One click downloads
#   every photo of that order as a single ZIP file named
#   "<order-id>-photos.zip". Works with Cloudinary and with local storage.
#
#   1. finance\views.py        -> new gift_order_images_download view
#   2. finance\urls.py         -> new .../gift-orders/<id>/download/ route
#   3. templates\finance\gift_orders.html -> the Download all button
#   4. static\css\finance.css -> button styles
#
# Safe to re-run: every step checks first and skips what is already done.
#
# HOW TO RUN
#   1. Copy this file into your project folder (next to manage.py).
#   2. In PowerShell, from that folder:
#        powershell -ExecutionPolicy Bypass -File .\add-gift-photo-download.ps1
#   3. Then:
#        git add .
#        git commit -m "gift order photo download"
#        git push
#   4. After Render shows "Deploy live", open the Render Shell and run:
#        python manage.py collectstatic --noinput
#      (No "migrate" needed - no database changes.)
# ============================================================================

$ErrorActionPreference = "Stop"

function Read-Utf8([string]$p)  { [IO.File]::ReadAllText($p) }
function Write-Utf8([string]$p, [string]$c) {
    [IO.File]::WriteAllText($p, $c, (New-Object System.Text.UTF8Encoding($false)))
}
function Decode([string]$b64) { [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b64)) }
function Backup-Once([string]$p) {
    $bak = "$p.bak-dl"
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
Write-Host "UPDATE VERSION: v1 (gift photo download)" -ForegroundColor Magenta

$DL_VIEW_B64 = "CgojIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLQojIEdpZnQgb3JkZXIgcGhvdG9zOiBkb3dubG9hZCBldmVyeSBjdXN0b21lciBwaWN0dXJlIG9mIG9uZSBvcmRlciBhcyBhIFpJUAojIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLQoKQHN0YWZmX21lbWJlcl9yZXF1aXJlZApkZWYgZ2lmdF9vcmRlcl9pbWFnZXNfZG93bmxvYWQocmVxdWVzdCwgcGspOgogICAgIiIiQnVuZGxlIGFsbCBjdXN0b21lciBwaG90b3Mgb2YgYSBnaWZ0IG9yZGVyIGludG8gb25lIFpJUCBkb3dubG9hZC4iIiIKICAgIGltcG9ydCBpbwogICAgaW1wb3J0IG9zCiAgICBpbXBvcnQgemlwZmlsZQoKICAgIGltcG9ydCByZXF1ZXN0cwogICAgZnJvbSBkamFuZ28uaHR0cCBpbXBvcnQgSHR0cFJlc3BvbnNlCiAgICBmcm9tIGRqYW5nby5zaG9ydGN1dHMgaW1wb3J0IGdldF9vYmplY3Rfb3JfNDA0CiAgICBmcm9tIGRqYW5nby51cmxzIGltcG9ydCByZXZlcnNlCgogICAgZnJvbSBnaWZ0cy5tb2RlbHMgaW1wb3J0IEdpZnRPcmRlcgoKICAgIG9yZGVyID0gZ2V0X29iamVjdF9vcl80MDQoR2lmdE9yZGVyLCBwaz1waykKICAgIGJ1ZmZlciA9IGlvLkJ5dGVzSU8oKQogICAgYWRkZWQgPSAwCiAgICB3aXRoIHppcGZpbGUuWmlwRmlsZShidWZmZXIsICJ3IiwgemlwZmlsZS5aSVBfREVGTEFURUQpIGFzIHpmOgogICAgICAgIGZvciBpbWcgaW4gb3JkZXIuaW1hZ2VzLmFsbCgpOgogICAgICAgICAgICBkYXRhID0gTm9uZQogICAgICAgICAgICAjIExvY2FsIHN0b3JhZ2UgZmlyc3QgKGRldiAvIGRpc2sgc2V0dXBzKS4KICAgICAgICAgICAgdHJ5OgogICAgICAgICAgICAgICAgaW1nLmltYWdlLm9wZW4oInJiIikKICAgICAgICAgICAgICAgIGRhdGEgPSBpbWcuaW1hZ2UucmVhZCgpCiAgICAgICAgICAgICAgICBpbWcuaW1hZ2UuY2xvc2UoKQogICAgICAgICAgICBleGNlcHQgRXhjZXB0aW9uOgogICAgICAgICAgICAgICAgZGF0YSA9IE5vbmUKICAgICAgICAgICAgIyBSZW1vdGUgc3RvcmFnZSBmYWxsYmFjayAoZS5nLiBDbG91ZGluYXJ5KTogZmV0Y2ggdGhlIHB1YmxpYyBVUkwuCiAgICAgICAgICAgIGlmIG5vdCBkYXRhOgogICAgICAgICAgICAgICAgdHJ5OgogICAgICAgICAgICAgICAgICAgIHJlc3AgPSByZXF1ZXN0cy5nZXQoaW1nLmltYWdlLnVybCwgdGltZW91dD0zMCkKICAgICAgICAgICAgICAgICAgICBpZiByZXNwLnN0YXR1c19jb2RlID09IDIwMDoKICAgICAgICAgICAgICAgICAgICAgICAgZGF0YSA9IHJlc3AuY29udGVudAogICAgICAgICAgICAgICAgZXhjZXB0IEV4Y2VwdGlvbjoKICAgICAgICAgICAgICAgICAgICBkYXRhID0gTm9uZQogICAgICAgICAgICBpZiBub3QgZGF0YToKICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgIGV4dCA9IG9zLnBhdGguc3BsaXRleHQoaW1nLmltYWdlLm5hbWUgb3IgIiIpWzFdIG9yICIuanBnIgogICAgICAgICAgICBhZGRlZCArPSAxCiAgICAgICAgICAgIHpmLndyaXRlc3RyKGYie29yZGVyLm9yZGVyX2lkfV9waG90b197YWRkZWR9e2V4dH0iLCBkYXRhKQoKICAgIGlmIGFkZGVkID09IDA6CiAgICAgICAgbWVzc2FnZXMuZXJyb3IocmVxdWVzdCwgZiJObyBwaG90b3MgY291bGQgYmUgZG93bmxvYWRlZCBmb3Igb3JkZXIge29yZGVyLm9yZGVyX2lkfS4iKQogICAgICAgIGJhc2UgPSByZXZlcnNlKCJmaW5hbmNlX2dpZnRfb3JkZXJzIikKICAgICAgICByZXR1cm4gcmVkaXJlY3QoZiJ7YmFzZX0/b3Blbj17b3JkZXIucGt9I29yZGVyLXtvcmRlci5wa30iKQoKICAgIHJlc3BvbnNlID0gSHR0cFJlc3BvbnNlKGJ1ZmZlci5nZXR2YWx1ZSgpLCBjb250ZW50X3R5cGU9ImFwcGxpY2F0aW9uL3ppcCIpCiAgICByZXNwb25zZVsiQ29udGVudC1EaXNwb3NpdGlvbiJdID0gZidhdHRhY2htZW50OyBmaWxlbmFtZT0ie29yZGVyLm9yZGVyX2lkfS1waG90b3MuemlwIicKICAgIHJldHVybiByZXNwb25zZQo="
$DL_URL_A_B64 = "ICAgIHBhdGgoImdpZnQtb3JkZXJzLzxpbnQ6cGs+L3VwZGF0ZS8iLCB2aWV3cy5naWZ0X29yZGVyX3VwZGF0ZSwgbmFtZT0iZmluYW5jZV9naWZ0X29yZGVyX3VwZGF0ZSIpLA=="
$DL_URL_R_B64 = "ICAgIHBhdGgoImdpZnQtb3JkZXJzLzxpbnQ6cGs+L3VwZGF0ZS8iLCB2aWV3cy5naWZ0X29yZGVyX3VwZGF0ZSwgbmFtZT0iZmluYW5jZV9naWZ0X29yZGVyX3VwZGF0ZSIpLAogICAgcGF0aCgiZ2lmdC1vcmRlcnMvPGludDpwaz4vZG93bmxvYWQvIiwgdmlld3MuZ2lmdF9vcmRlcl9pbWFnZXNfZG93bmxvYWQsIG5hbWU9ImZpbmFuY2VfZ2lmdF9vcmRlcl9kb3dubG9hZCIpLA=="
$DL_TPL_A_B64 = "ICAgICAgICAgICAgICAgIDxkaXYgY2xhc3M9ImdvLXBob3RvcyI+CiAgICAgICAgICAgICAgICAgICAgPHNwYW4gY2xhc3M9ImdvLXBob3Rvcy1sYWJlbCI+Q3VzdG9tZXIgcGljdHVyZXMgKHt7IG9yZGVyLmltYWdlcy5jb3VudCB9fSk8L3NwYW4+"
$DL_TPL_R_B64 = "ICAgICAgICAgICAgICAgIDxkaXYgY2xhc3M9ImdvLXBob3RvcyI+CiAgICAgICAgICAgICAgICAgICAgPGRpdiBjbGFzcz0iZ28tcGhvdG9zLWhlYWQiPgogICAgICAgICAgICAgICAgICAgICAgICA8c3BhbiBjbGFzcz0iZ28tcGhvdG9zLWxhYmVsIj5DdXN0b21lciBwaWN0dXJlcyAoe3sgb3JkZXIuaW1hZ2VzLmNvdW50IH19KTwvc3Bhbj4KICAgICAgICAgICAgICAgICAgICAgICAgPGEgY2xhc3M9ImJ0bi1wcmltYXJ5IGdvLWRvd25sb2FkLWJ0biIKICAgICAgICAgICAgICAgICAgICAgICAgICAgaHJlZj0ieyUgdXJsICdmaW5hbmNlX2dpZnRfb3JkZXJfZG93bmxvYWQnIG9yZGVyLnBrICV9IgogICAgICAgICAgICAgICAgICAgICAgICAgICB0aXRsZT0iRG93bmxvYWQgYWxsIHt7IG9yZGVyLmltYWdlcy5jb3VudCB9fSBwaWN0dXJlcyBhcyBvbmUgWklQIGZpbGUiPgogICAgICAgICAgICAgICAgICAgICAgICAgICAgPHN2ZyB2aWV3Qm94PSIwIDAgMjQgMjQiIGZpbGw9Im5vbmUiIHN0cm9rZT0iY3VycmVudENvbG9yIiBzdHJva2Utd2lkdGg9IjIiCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIgYXJpYS1oaWRkZW49InRydWUiPgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIDxwYXRoIGQ9Ik0yMSAxNXY0YTIgMiAwIDAgMS0yIDJINWEyIDIgMCAwIDEtMi0ydi00Ii8+CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgPHBvbHlsaW5lIHBvaW50cz0iNyAxMCAxMiAxNSAxNyAxMCIvPgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIDxsaW5lIHgxPSIxMiIgeTE9IjE1IiB4Mj0iMTIiIHkyPSIzIi8+CiAgICAgICAgICAgICAgICAgICAgICAgICAgICA8L3N2Zz4KICAgICAgICAgICAgICAgICAgICAgICAgICAgIERvd25sb2FkIGFsbAogICAgICAgICAgICAgICAgICAgICAgICA8L2E+CiAgICAgICAgICAgICAgICAgICAgPC9kaXY+"
$DL_CSS_B64 = "CgovKiBHaWZ0IG9yZGVyIHBob3RvczogaGVhZGVyIHJvdyB3aXRoIHRoZSBkb3dubG9hZC1hbGwgYnV0dG9uICovCi5nby1waG90b3MtaGVhZCB7CiAgICBkaXNwbGF5OiBmbGV4OwogICAgYWxpZ24taXRlbXM6IGNlbnRlcjsKICAgIGp1c3RpZnktY29udGVudDogc3BhY2UtYmV0d2VlbjsKICAgIGdhcDogMTJweDsKICAgIGZsZXgtd3JhcDogd3JhcDsKICAgIG1hcmdpbi1ib3R0b206IDhweDsKfQoKLmdvLXBob3Rvcy1oZWFkIC5nby1waG90b3MtbGFiZWwgeyBtYXJnaW4tYm90dG9tOiAwOyB9CgouZ28tZG93bmxvYWQtYnRuIHsKICAgIGRpc3BsYXk6IGlubGluZS1mbGV4OwogICAgYWxpZ24taXRlbXM6IGNlbnRlcjsKICAgIGdhcDogN3B4OwogICAgbWFyZ2luLXRvcDogMDsKICAgIHBhZGRpbmc6IDdweCAxNHB4OwogICAgZm9udC1zaXplOiAuNzhyZW07CiAgICB0ZXh0LWRlY29yYXRpb246IG5vbmU7Cn0KCi5nby1kb3dubG9hZC1idG4gc3ZnIHsgd2lkdGg6IDE0cHg7IGhlaWdodDogMTRweDsgfQo="

# ---------- 1) finance/views.py: the download view ----------
Write-Host "`n[1/4] Adding the ZIP download view..." -ForegroundColor Green
$fvPath = Join-Path $root "finance\views.py"
if (-not (Test-Path $fvPath)) {
    Write-Host "  WARNING: finance\views.py not found - skipping." -ForegroundColor Yellow
} else {
    $fv = Read-Utf8 $fvPath
    if ($fv.Contains("def gift_order_images_download")) {
        Write-Host "  already present, skipping" -ForegroundColor DarkGray
    } else {
        Backup-Once $fvPath
        if (-not $fv.EndsWith("`n")) { $fv += "`r`n" }
        $fv += (Decode $DL_VIEW_B64).Replace("`n", "`r`n")
        Write-Utf8 $fvPath $fv
        Write-Host "  gift_order_images_download view added" -ForegroundColor DarkGray
    }
}

# ---------- 2) finance/urls.py: the download route ----------
Write-Host "`n[2/4] Adding the download route..." -ForegroundColor Green
$fuPath = Join-Path $root "finance\urls.py"
if (-not (Test-Path $fuPath)) {
    Write-Host "  WARNING: finance\urls.py not found - skipping." -ForegroundColor Yellow
} else {
    $hadCrlf = (Read-Utf8 $fuPath).Contains("`r`n")
    $fu = (Read-Utf8 $fuPath).Replace("`r`n", "`n")
    if ($fu.Contains("finance_gift_order_download")) {
        Write-Host "  route already present, skipping" -ForegroundColor DarkGray
    } else {
        $a = Decode $DL_URL_A_B64
        if ((Count-Occurrences $fu $a) -ne 1) {
            Write-Host "  WARNING: gift-order update route not found in finance\urls.py." -ForegroundColor Yellow
            Write-Host "  Run the gifts installer (v4) first, then this one again." -ForegroundColor Yellow
        } else {
            Backup-Once $fuPath
            $fu = $fu.Replace($a, (Decode $DL_URL_R_B64))
            if ($hadCrlf) { $fu = $fu.Replace("`n", "`r`n") }
            Write-Utf8 $fuPath $fu
            Write-Host "  route added: gift-orders/<id>/download/" -ForegroundColor DarkGray
        }
    }
}

# ---------- 3) gift_orders.html: the Download all button ----------
Write-Host "`n[3/4] Adding the Download all button..." -ForegroundColor Green
$goPath = Join-Path $root "templates\finance\gift_orders.html"
if (-not (Test-Path $goPath)) {
    Write-Host "  WARNING: templates\finance\gift_orders.html not found - skipping." -ForegroundColor Yellow
} else {
    $hadCrlf = (Read-Utf8 $goPath).Contains("`r`n")
    $go = (Read-Utf8 $goPath).Replace("`r`n", "`n")
    if ($go.Contains("go-download-btn")) {
        Write-Host "  button already present, skipping" -ForegroundColor DarkGray
    } else {
        $a = Decode $DL_TPL_A_B64
        if ((Count-Occurrences $go $a) -ne 1) {
            Write-Host "  WARNING: pictures block not found in gift_orders.html - no changes made." -ForegroundColor Yellow
        } else {
            Backup-Once $goPath
            $go = $go.Replace($a, (Decode $DL_TPL_R_B64))
            if ($hadCrlf) { $go = $go.Replace("`n", "`r`n") }
            Write-Utf8 $goPath $go
            Write-Host "  Download all button added beside the customer pictures" -ForegroundColor DarkGray
        }
    }
}

# ---------- 4) finance.css: button styles ----------
Write-Host "`n[4/4] Adding the button styles..." -ForegroundColor Green
$fcPath = Join-Path $root "static\css\finance.css"
if (-not (Test-Path $fcPath)) {
    Write-Host "  WARNING: static\css\finance.css not found - skipping." -ForegroundColor Yellow
} else {
    $fc = Read-Utf8 $fcPath
    if ($fc.Contains("go-photos-head")) {
        Write-Host "  styles already present, skipping" -ForegroundColor DarkGray
    } else {
        Backup-Once $fcPath
        $fc = $fc.TrimEnd() + (Decode $DL_CSS_B64)
        Write-Utf8 $fcPath $fc
        Write-Host "  styles appended" -ForegroundColor DarkGray
    }
}

# ---------- done ----------
Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host " Done! Next steps:" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Check the changes:" -ForegroundColor White
Write-Host "     findstr /C:""gift_order_images_download"" finance\views.py" -ForegroundColor Gray
Write-Host "     findstr /C:""finance_gift_order_download"" finance\urls.py" -ForegroundColor Gray
Write-Host "     findstr /C:""go-download-btn"" templates\finance\gift_orders.html" -ForegroundColor Gray
Write-Host "   Each command should print a line." -ForegroundColor Gray
Write-Host ""
Write-Host "2. Publish to Render:" -ForegroundColor White
Write-Host "     git add ." -ForegroundColor Gray
Write-Host "     git commit -m ""gift order photo download""" -ForegroundColor Gray
Write-Host "     git push" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Wait until Render shows 'Deploy live', then in the Render Shell run:" -ForegroundColor White
Write-Host "     python manage.py collectstatic --noinput" -ForegroundColor Gray
Write-Host "   (No migrate needed - no database changes in this update.)" -ForegroundColor Gray
Write-Host ""
Write-Host "Then open Finance -> Gift Orders, expand an order with pictures, and" -ForegroundColor White
Write-Host "the Download all button beside the pictures saves every photo of that" -ForegroundColor White
Write-Host "order as one ZIP file." -ForegroundColor White
