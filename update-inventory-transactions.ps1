# ============================================================================
# ABFverify - Sales Inventory gift orders + Transactions page redesign (v1)
# ============================================================================
# WHAT IT DOES
#   1. finance\services.py
#      Sales Inventory now also records GIFT ORDERS: a Gift Orders stat
#      card, a per-gift-product sales table, and gift revenue is included
#      in the "Total Recorded Sales Value".
#   2. templates\finance\inventory.html
#      Adds a "Back to Admin" button, the Gift Orders card and the gift
#      sales table.
#   3. templates\panel\transactions.html
#      The transactions page now uses the same row style as the dashboard
#      "Recent Transactions" list (icon, description, +/- amount, status
#      badge). The summary cards show Total Deposits and Total Spent.
#   4. static\css\transactions.css
#      Styles for the new dashboard-style list.
#   5. accounts\views.py
#      Feeds the new list: credit/debit direction, descriptions and the
#      total-deposits figure.
#
# Safe to re-run: every step checks first and skips what is already done.
#
# HOW TO RUN
#   1. Copy this file into your project folder (next to manage.py).
#   2. In PowerShell, from that folder:
#        powershell -ExecutionPolicy Bypass -File .\update-inventory-transactions.ps1
#   3. Then:
#        git add .
#        git commit -m "inventory gift orders + transactions redesign"
#        git push
#   4. After Render shows "Deploy live", open the Render Shell and run:
#        python manage.py collectstatic --noinput
#      (No "migrate" needed - this update has no database changes.)
# ============================================================================

$ErrorActionPreference = "Stop"

function Read-Utf8([string]$p)  { [IO.File]::ReadAllText($p) }
function Write-Utf8([string]$p, [string]$c) {
    [IO.File]::WriteAllText($p, $c, (New-Object System.Text.UTF8Encoding($false)))
}
function Decode([string]$b64) { [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b64)) }
function Backup-Once([string]$p) {
    $bak = "$p.bak-invtx"
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
Write-Host "UPDATE VERSION: v1 (inventory gift orders + transactions redesign)" -ForegroundColor Magenta

$TX_HTML_B64 = "eyUgZXh0ZW5kcyAicGFuZWwvZGFzaGJvYXJkX2Jhc2UuaHRtbCIgJX0KeyUgbG9hZCBodW1hbml6ZSAlfQp7JSBsb2FkIHN0YXRpYyAlfQoKeyUgYmxvY2sgdGl0bGUgJX1UcmFuc2FjdGlvbnN7JSBlbmRibG9jayAlfQp7JSBibG9jayBwYWdlX3RpdGxlICV9VHJhbnNhY3Rpb25zeyUgZW5kYmxvY2sgJX0KeyUgYmxvY2sgc2VjdGlvbl90aXRsZSAlfVRyYW5zYWN0aW9uc3slIGVuZGJsb2NrICV9Cgp7JSBibG9jayBjb250ZW50ICV9Cgo8bGluayByZWw9InN0eWxlc2hlZXQiIGhyZWY9InslIHN0YXRpYyAnY3NzL3RyYW5zYWN0aW9ucy5jc3MnICV9P3Y9MiI+Cgo8ZGl2IGNsYXNzPSJ0cmFuc2FjdGlvbnMtY29udGFpbmVyIj4KCiAgICA8IS0tIEhFQURFUiAtLT4KICAgIDxkaXYgY2xhc3M9InRyYW5zYWN0aW9ucy1oZWFkZXIiPgogICAgICAgIDxkaXY+CiAgICAgICAgICAgIDxoMiBjbGFzcz0idHJhbnNhY3Rpb25zLXRpdGxlIj5UcmFuc2FjdGlvbnM8L2gyPgogICAgICAgICAgICA8cCBjbGFzcz0idHJhbnNhY3Rpb25zLXN1YnRpdGxlIj5BbGwgeW91ciBkZXBvc2l0cywgcHVyY2hhc2VzLCBhbmQgcmVmdW5kczwvcD4KICAgICAgICA8L2Rpdj4KICAgICAgICA8ZGl2IGNsYXNzPSJ0cmFuc2FjdGlvbnMtYmFkZ2UiPgogICAgICAgICAgICBUb3RhbDoge3sgdHJhbnNhY3Rpb25zfGxlbmd0aCB9fQogICAgICAgIDwvZGl2PgogICAgPC9kaXY+CgogICAgPCEtLSBTVU1NQVJZIC0tPgogICAgPGRpdiBjbGFzcz0idHJhbnNhY3Rpb25zLXN1bW1hcnkiPgogICAgICAgIDxkaXYgY2xhc3M9InRyYW5zYWN0aW9ucy1jYXJkIj4KICAgICAgICAgICAgPGgzPlRvdGFsIERlcG9zaXRzPC9oMz4KICAgICAgICAgICAgPHA+JiM4MzU4O3t7IHRvdGFsX2RlcG9zaXR8ZmxvYXRmb3JtYXQ6MnxpbnRjb21tYSB9fTwvcD4KICAgICAgICA8L2Rpdj4KICAgICAgICA8ZGl2IGNsYXNzPSJ0cmFuc2FjdGlvbnMtY2FyZCI+CiAgICAgICAgICAgIDxoMz5Ub3RhbCBTcGVudDwvaDM+CiAgICAgICAgICAgIDxwPiYjODM1ODt7eyB0b3RhbF9zcGVudHxmbG9hdGZvcm1hdDoyfGludGNvbW1hIH19PC9wPgogICAgICAgIDwvZGl2PgogICAgPC9kaXY+CgogICAgPCEtLSBUUkFOU0FDVElPTiBMSVNUIChzYW1lIHN0eWxlIGFzIGRhc2hib2FyZCBSZWNlbnQgVHJhbnNhY3Rpb25zKSAtLT4KICAgIDxkaXYgY2xhc3M9InRyYW5zYWN0aW9ucy1saXN0LWNhcmQiPgogICAgICAgIHslIGZvciB0eCBpbiB0cmFuc2FjdGlvbnMgJX0KICAgICAgICA8ZGl2IGNsYXNzPSJkYXNoLXJvdyI+CgogICAgICAgICAgICB7JSBpZiB0eC50eG5fdHlwZSA9PSAnY3JlZGl0JyAlfQogICAgICAgICAgICA8c3BhbiBjbGFzcz0iZGFzaC1yb3ctaWNvbiByb3ctZ3JlZW4iPgogICAgICAgICAgICAgICAgPGkgY2xhc3M9ImZhLXNvbGlkIGZhLWFycm93LWRvd24iPjwvaT4KICAgICAgICAgICAgPC9zcGFuPgogICAgICAgICAgICB7JSBlbHNlICV9CiAgICAgICAgICAgIDxzcGFuIGNsYXNzPSJkYXNoLXJvdy1pY29uIHJvdy1yZWQiPgogICAgICAgICAgICAgICAgPGkgY2xhc3M9ImZhLXNvbGlkIGZhLWFycm93LXVwIj48L2k+CiAgICAgICAgICAgIDwvc3Bhbj4KICAgICAgICAgICAgeyUgZW5kaWYgJX0KCiAgICAgICAgICAgIDxkaXYgY2xhc3M9ImRhc2gtcm93LWluZm8iPgogICAgICAgICAgICAgICAgPHAgY2xhc3M9ImRhc2gtcm93LXRpdGxlIj57eyB0eC5kZXNjcmlwdGlvbnxkZWZhdWx0OiJUcmFuc2FjdGlvbiIgfX08L3A+CiAgICAgICAgICAgICAgICA8cCBjbGFzcz0iZGFzaC1yb3ctc3ViIj57eyB0eC5jcmVhdGVkX2F0fGRhdGU6Ik0gaiwgWSDCtyBIOmkiIH19PC9wPgogICAgICAgICAgICA8L2Rpdj4KCiAgICAgICAgICAgIDxkaXYgY2xhc3M9ImRhc2gtcm93LXN0YXRlIHR4LXN0YXRlIj4KCiAgICAgICAgICAgICAgICA8cCBjbGFzcz0idHgtYW1vdW50IHslIGlmIHR4LnR4bl90eXBlID09ICdjcmVkaXQnICV9dHgtY3JlZGl0eyUgZWxzZSAlfXR4LWRlYml0eyUgZW5kaWYgJX0iPgogICAgICAgICAgICAgICAgICAgIHslIGlmIHR4LnR4bl90eXBlID09ICdjcmVkaXQnICV9K3slIGVsc2UgJX0teyUgZW5kaWYgJX0mIzgzNTg7e3sgdHguYW1vdW50fGZsb2F0Zm9ybWF0OjJ8aW50Y29tbWEgfX0KICAgICAgICAgICAgICAgIDwvcD4KCiAgICAgICAgICAgICAgICA8c3BhbiBjbGFzcz0idHgtYmFkZ2UgdHgte3sgdHguc3RhdHVzfGRlZmF1bHQ6J3N1Y2Nlc3NmdWwnIH19Ij57eyB0eC5zdGF0dXN8ZGVmYXVsdDoic3VjY2Vzc2Z1bCJ8dGl0bGUgfX08L3NwYW4+CgogICAgICAgICAgICA8L2Rpdj4KCiAgICAgICAgPC9kaXY+CiAgICAgICAgeyUgZW1wdHkgJX0KICAgICAgICA8ZGl2IGNsYXNzPSJkYXNoLWVtcHR5Ij4KICAgICAgICAgICAgPGkgY2xhc3M9ImZhLXNvbGlkIGZhLXJlY2VpcHQiPjwvaT4KICAgICAgICAgICAgPHA+Tm8gdHJhbnNhY3Rpb25zIHlldC48L3A+CiAgICAgICAgICAgIDxhIGhyZWY9InslIHVybCAnd2FsbGV0JyAlfSIgY2xhc3M9ImRhc2gtZW1wdHktYnRuIj5GdW5kIHdhbGxldDwvYT4KICAgICAgICA8L2Rpdj4KICAgICAgICB7JSBlbmRmb3IgJX0KICAgIDwvZGl2PgoKPC9kaXY+Cgp7JSBlbmRibG9jayAlfQo="
$TX_CSS_B64 = "CgovKiA9PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT0KICAgREFTSEJPQVJELVNUWUxFIFRSQU5TQUNUSU9OIExJU1QgKHYyKQogICBNaXJyb3JzIHRoZSBkYXNoYm9hcmQgUmVjZW50IFRyYW5zYWN0aW9ucyByb3dzLgogICA9PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT0gKi8KCi50cmFuc2FjdGlvbnMtbGlzdC1jYXJkIHsKICAgIGJhY2tncm91bmQ6IHZhcigtLWNhcmQpOwogICAgYm9yZGVyOiAxcHggc29saWQgdmFyKC0tYm9yZGVyKTsKICAgIGJvcmRlci1yYWRpdXM6IDE0cHg7CiAgICBwYWRkaW5nOiA2cHggMTRweDsKfQoKLnRyYW5zYWN0aW9ucy1saXN0LWNhcmQgLmRhc2gtcm93IHsKICAgIGRpc3BsYXk6IGZsZXg7CiAgICBhbGlnbi1pdGVtczogY2VudGVyOwogICAgZ2FwOiAxM3B4OwogICAgcGFkZGluZzogMTNweCA2cHg7CiAgICBib3JkZXItYm90dG9tOiAxcHggc29saWQgdmFyKC0tYm9yZGVyKTsKICAgIHRyYW5zaXRpb246IGJhY2tncm91bmQgMC4ycyBlYXNlOwp9CgoudHJhbnNhY3Rpb25zLWxpc3QtY2FyZCAuZGFzaC1yb3c6bGFzdC1jaGlsZCB7IGJvcmRlci1ib3R0b206IG5vbmU7IH0KLnRyYW5zYWN0aW9ucy1saXN0LWNhcmQgLmRhc2gtcm93OmhvdmVyIHsgYmFja2dyb3VuZDogdmFyKC0tYmcpOyB9CgoudHJhbnNhY3Rpb25zLWxpc3QtY2FyZCAuZGFzaC1yb3ctaWNvbiB7CiAgICB3aWR0aDogMzhweDsKICAgIGhlaWdodDogMzhweDsKICAgIG1pbi13aWR0aDogMzhweDsKICAgIGRpc3BsYXk6IGZsZXg7CiAgICBhbGlnbi1pdGVtczogY2VudGVyOwogICAganVzdGlmeS1jb250ZW50OiBjZW50ZXI7CiAgICBib3JkZXItcmFkaXVzOiAxMXB4OwogICAgZm9udC1zaXplOiAxNHB4Owp9CgoudHJhbnNhY3Rpb25zLWxpc3QtY2FyZCAucm93LWdyZWVuIHsgYmFja2dyb3VuZDogcmdiYSgzNCwgMTk3LCA5NCwgMC4xMyk7IGNvbG9yOiAjMjJjNTVlOyB9Ci50cmFuc2FjdGlvbnMtbGlzdC1jYXJkIC5yb3ctcmVkICAgeyBiYWNrZ3JvdW5kOiByZ2JhKDIzOSwgNjgsIDY4LCAwLjEyKTsgY29sb3I6ICNlZjQ0NDQ7IH0KCi50cmFuc2FjdGlvbnMtbGlzdC1jYXJkIC5kYXNoLXJvdy1pbmZvIHsgZmxleDogMTsgbWluLXdpZHRoOiAwOyB9CgoudHJhbnNhY3Rpb25zLWxpc3QtY2FyZCAuZGFzaC1yb3ctdGl0bGUgewogICAgZm9udC1zaXplOiAxMy41cHg7CiAgICBmb250LXdlaWdodDogNjAwOwogICAgY29sb3I6IHZhcigtLXRleHQpOwogICAgbWFyZ2luOiAwOwogICAgd2hpdGUtc3BhY2U6IG5vd3JhcDsKICAgIG92ZXJmbG93OiBoaWRkZW47CiAgICB0ZXh0LW92ZXJmbG93OiBlbGxpcHNpczsKfQoKLnRyYW5zYWN0aW9ucy1saXN0LWNhcmQgLmRhc2gtcm93LXN1YiB7CiAgICBmb250LXNpemU6IDEycHg7CiAgICBjb2xvcjogdmFyKC0tbXV0ZWQpOwogICAgbWFyZ2luOiAycHggMCAwOwp9CgoudHJhbnNhY3Rpb25zLWxpc3QtY2FyZCAuZGFzaC1yb3ctc3RhdGUgewogICAgZGlzcGxheTogZmxleDsKICAgIGFsaWduLWl0ZW1zOiBjZW50ZXI7CiAgICBnYXA6IDhweDsKICAgIGZsZXgtc2hyaW5rOiAwOwp9CgoudHJhbnNhY3Rpb25zLWxpc3QtY2FyZCAudHgtc3RhdGUgewogICAgZmxleC1kaXJlY3Rpb246IGNvbHVtbjsKICAgIGFsaWduLWl0ZW1zOiBmbGV4LWVuZDsKICAgIGdhcDogM3B4Owp9CgoudHJhbnNhY3Rpb25zLWxpc3QtY2FyZCAudHgtYW1vdW50IHsKICAgIGZvbnQtc2l6ZTogMTMuNXB4OwogICAgZm9udC13ZWlnaHQ6IDcwMDsKICAgIG1hcmdpbjogMDsKICAgIGNvbG9yOiB2YXIoLS10ZXh0KTsKfQoKLnRyYW5zYWN0aW9ucy1saXN0LWNhcmQgLnR4LWNyZWRpdCB7IGNvbG9yOiAjMjJjNTVlOyB9Ci50cmFuc2FjdGlvbnMtbGlzdC1jYXJkIC50eC1kZWJpdCAgeyBjb2xvcjogI2VmNDQ0NDsgfQoKLnRyYW5zYWN0aW9ucy1saXN0LWNhcmQgLnR4LWJhZGdlIHsKICAgIHBhZGRpbmc6IDJweCA5cHg7CiAgICBib3JkZXItcmFkaXVzOiA5OTlweDsKICAgIGZvbnQtc2l6ZTogMTAuNXB4OwogICAgZm9udC13ZWlnaHQ6IDcwMDsKICAgIGxldHRlci1zcGFjaW5nOiAwLjRweDsKICAgIHRleHQtdHJhbnNmb3JtOiB1cHBlcmNhc2U7Cn0KCi50cmFuc2FjdGlvbnMtbGlzdC1jYXJkIC50eC1zdWNjZXNzZnVsLAoudHJhbnNhY3Rpb25zLWxpc3QtY2FyZCAudHgtY29tcGxldGVkIHsgY29sb3I6ICMxNmEzNGE7IGJhY2tncm91bmQ6IHJnYmEoMzQsIDE5NywgOTQsIDAuMTMpOyB9Ci50cmFuc2FjdGlvbnMtbGlzdC1jYXJkIC50eC1wZW5kaW5nICAgIHsgY29sb3I6ICNkOTc3MDY7IGJhY2tncm91bmQ6IHJnYmEoMjQ1LCAxNTgsIDExLCAwLjEzKTsgfQoudHJhbnNhY3Rpb25zLWxpc3QtY2FyZCAudHgtZmFpbGVkICAgICB7IGNvbG9yOiAjZWY0NDQ0OyBiYWNrZ3JvdW5kOiByZ2JhKDIzOSwgNjgsIDY4LCAwLjEyKTsgfQoKLnRyYW5zYWN0aW9ucy1saXN0LWNhcmQgLmRhc2gtZW1wdHkgewogICAgZGlzcGxheTogZmxleDsKICAgIGZsZXgtZGlyZWN0aW9uOiBjb2x1bW47CiAgICBhbGlnbi1pdGVtczogY2VudGVyOwogICAgZ2FwOiA4cHg7CiAgICBwYWRkaW5nOiAyOHB4IDEwcHg7CiAgICB0ZXh0LWFsaWduOiBjZW50ZXI7Cn0KCi50cmFuc2FjdGlvbnMtbGlzdC1jYXJkIC5kYXNoLWVtcHR5IGkgewogICAgZm9udC1zaXplOiAyNnB4OwogICAgY29sb3I6IHZhcigtLW11dGVkKTsKICAgIG9wYWNpdHk6IDAuNjsKfQoKLnRyYW5zYWN0aW9ucy1saXN0LWNhcmQgLmRhc2gtZW1wdHkgcCB7CiAgICBmb250LXNpemU6IDEzLjVweDsKICAgIGNvbG9yOiB2YXIoLS1tdXRlZCk7CiAgICBtYXJnaW46IDA7Cn0KCi50cmFuc2FjdGlvbnMtbGlzdC1jYXJkIC5kYXNoLWVtcHR5LWJ0biB7CiAgICBtYXJnaW4tdG9wOiA0cHg7CiAgICBwYWRkaW5nOiA5cHggMTZweDsKICAgIGJvcmRlci1yYWRpdXM6IDEwcHg7CiAgICBmb250LXNpemU6IDEzcHg7CiAgICBmb250LXdlaWdodDogNjAwOwogICAgY29sb3I6ICNmZmZmZmY7CiAgICB0ZXh0LWRlY29yYXRpb246IG5vbmU7CiAgICBiYWNrZ3JvdW5kOiBsaW5lYXItZ3JhZGllbnQoMTM1ZGVnLCAjMjU2M2ViLCAjMWQ0ZWQ4KTsKICAgIHRyYW5zaXRpb246IGZpbHRlciAwLjJzIGVhc2UsIHRyYW5zZm9ybSAwLjJzIGVhc2U7Cn0KCi50cmFuc2FjdGlvbnMtbGlzdC1jYXJkIC5kYXNoLWVtcHR5LWJ0bjpob3ZlciB7CiAgICBmaWx0ZXI6IGJyaWdodG5lc3MoMS4wOCk7CiAgICB0cmFuc2Zvcm06IHRyYW5zbGF0ZVkoLTFweCk7Cn0KCkBtZWRpYSAobWF4LXdpZHRoOiA0ODBweCkgewogICAgLnRyYW5zYWN0aW9ucy1saXN0LWNhcmQgeyBwYWRkaW5nOiA0cHggMTBweDsgfQogICAgLnRyYW5zYWN0aW9ucy1saXN0LWNhcmQgLmRhc2gtcm93IHsgZ2FwOiAxMHB4OyBwYWRkaW5nOiAxMnB4IDJweDsgfQp9Cg=="
$SVC_A1_B64 = "ICAgICAgICAub3JkZXJfYnkoInNlcnZpY2VfX2NhdGVnb3J5IiwgInNlcnZpY2VfX25hbWUiKQogICAgKQoKICAgIHRvdGFscyA9IHs="
$SVC_R1_B64 = "ICAgICAgICAub3JkZXJfYnkoInNlcnZpY2VfX2NhdGVnb3J5IiwgInNlcnZpY2VfX25hbWUiKQogICAgKQoKICAgICMgR2lmdCBvcmRlcnMgKGdpZnRzIGFwcCkgLSBldmVyeSBwYWlkIGdpZnQgb3JkZXIgY291bnRzIGFzIGEgc2FsZSwKICAgICMgZ3JvdXBlZCBieSB0aGUgZ2lmdCBwcm9kdWN0IHNuYXBzaG90IG5hbWUuCiAgICBmcm9tIGdpZnRzLm1vZGVscyBpbXBvcnQgR2lmdE9yZGVyCiAgICBnaWZ0X3NhbGVzID0gX2JldHdlZW4oR2lmdE9yZGVyLm9iamVjdHMuYWxsKCksIHN0YXJ0LCBlbmQpCiAgICBnaWZ0X3Jvd3MgPSBsaXN0KAogICAgICAgIGdpZnRfc2FsZXMKICAgICAgICAudmFsdWVzKCJncm91cF9uYW1lIikKICAgICAgICAuYW5ub3RhdGUoCiAgICAgICAgICAgIG9yZGVycz1Db3VudCgiaWQiKSwKICAgICAgICAgICAgcmV2ZW51ZT1TdW0oInByaWNlIiksCiAgICAgICAgICAgIGxhc3Rfb3JkZXJlZD1NYXgoImNyZWF0ZWRfYXQiKSwKICAgICAgICApCiAgICAgICAgLm9yZGVyX2J5KCItb3JkZXJzIiwgImdyb3VwX25hbWUiKQogICAgKQoKICAgIHRvdGFscyA9IHs="
$SVC_A2_B64 = "ICAgICAgICAiYm9vc3RfdmFsdWUiOiBfcShfc3VtKGJvb3N0X3NhbGVzLCAicHJpY2UiKSksCiAgICB9"
$SVC_R2_B64 = "ICAgICAgICAiYm9vc3RfdmFsdWUiOiBfcShfc3VtKGJvb3N0X3NhbGVzLCAicHJpY2UiKSksCiAgICAgICAgImdpZnRfb3JkZXJzIjogc3VtKHJvd1sib3JkZXJzIl0gZm9yIHJvdyBpbiBnaWZ0X3Jvd3MpLAogICAgICAgICJnaWZ0X3JldmVudWUiOiBfcShfc3VtKGdpZnRfc2FsZXMsICJwcmljZSIpKSwKICAgIH0="
$SVC_A3_B64 = "ICAgIHRvdGFsc1sic2FsZXNfdmFsdWUiXSA9IF9xKAogICAgICAgIHRvdGFsc1sibG9nc19yZXZlbnVlIl0KICAgICAgICArIHRvdGFsc1sic21zX3JldmVudWUiXQogICAgICAgICsgdG90YWxzWyJib29zdF92YWx1ZSJdCiAgICAp"
$SVC_R3_B64 = "ICAgIHRvdGFsc1sic2FsZXNfdmFsdWUiXSA9IF9xKAogICAgICAgIHRvdGFsc1sibG9nc19yZXZlbnVlIl0KICAgICAgICArIHRvdGFsc1sic21zX3JldmVudWUiXQogICAgICAgICsgdG90YWxzWyJib29zdF92YWx1ZSJdCiAgICAgICAgKyB0b3RhbHNbImdpZnRfcmV2ZW51ZSJdCiAgICAp"
$SVC_A4_B64 = "ICAgICAgICAiYm9vc3Rfcm93cyI6IGJvb3N0X3Jvd3MsCiAgICAgICAgImludmVudG9yeV90b3RhbHMiOiB0b3RhbHMsCiAgICB9"
$SVC_R4_B64 = "ICAgICAgICAiYm9vc3Rfcm93cyI6IGJvb3N0X3Jvd3MsCiAgICAgICAgImdpZnRfcm93cyI6IGdpZnRfcm93cywKICAgICAgICAiaW52ZW50b3J5X3RvdGFscyI6IHRvdGFscywKICAgIH0="
$INV_I1A_B64 = "ICAgICAgICA8YSBjbGFzcz0iYnRuLWJhY2siIGhyZWY9InslIHVybCAnZmluYW5jZV9hbmFseXRpY3MnICV9Ij5SZXZlbnVlIEFuYWx5dGljczwvYT4="
$INV_I1R_B64 = "ICAgICAgICA8YSBjbGFzcz0iYnRuLWJhY2siIGhyZWY9InslIHVybCAnZmluYW5jZV9hbmFseXRpY3MnICV9Ij5SZXZlbnVlIEFuYWx5dGljczwvYT4KICAgICAgICA8YSBjbGFzcz0iYnRuLWJhY2siIGhyZWY9Ii9zZW1pbG9yZS8iPkJhY2sgdG8gQWRtaW48L2E+"
$INV_I2A_B64 = "ICAgICAgICAgICAgPGFydGljbGUgY2xhc3M9InN0YXQtY2FyZCI+CiAgICAgICAgICAgICAgICA8c3BhbiBjbGFzcz0iY2FyZC1sYWJlbCI+Qm9vc3QgT3JkZXJzPC9zcGFuPgogICAgICAgICAgICAgICAgPHNwYW4gY2xhc3M9ImNhcmQtdmFsdWUgdHh0LXllbGxvdyI+e3sgaW52ZW50b3J5X3RvdGFscy5ib29zdF9vcmRlcnN8aW50Y29tbWEgfX08L3NwYW4+CiAgICAgICAgICAgICAgICA8c3BhbiBjbGFzcz0iY2FyZC1jYXB0aW9uIj57eyBpbnZlbnRvcnlfdG90YWxzLmJvb3N0X3VuaXRzfGludGNvbW1hIH19IHRvdGFsIGZvbGxvd2VycywgbGlrZXMsIHZpZXdzLCBvciBvdGhlciB1bml0czwvc3Bhbj4KICAgICAgICAgICAgPC9hcnRpY2xlPg=="
$INV_I2R_B64 = "ICAgICAgICAgICAgPGFydGljbGUgY2xhc3M9InN0YXQtY2FyZCI+CiAgICAgICAgICAgICAgICA8c3BhbiBjbGFzcz0iY2FyZC1sYWJlbCI+Qm9vc3QgT3JkZXJzPC9zcGFuPgogICAgICAgICAgICAgICAgPHNwYW4gY2xhc3M9ImNhcmQtdmFsdWUgdHh0LXllbGxvdyI+e3sgaW52ZW50b3J5X3RvdGFscy5ib29zdF9vcmRlcnN8aW50Y29tbWEgfX08L3NwYW4+CiAgICAgICAgICAgICAgICA8c3BhbiBjbGFzcz0iY2FyZC1jYXB0aW9uIj57eyBpbnZlbnRvcnlfdG90YWxzLmJvb3N0X3VuaXRzfGludGNvbW1hIH19IHRvdGFsIGZvbGxvd2VycywgbGlrZXMsIHZpZXdzLCBvciBvdGhlciB1bml0czwvc3Bhbj4KICAgICAgICAgICAgPC9hcnRpY2xlPgogICAgICAgICAgICA8YXJ0aWNsZSBjbGFzcz0ic3RhdC1jYXJkIj4KICAgICAgICAgICAgICAgIDxzcGFuIGNsYXNzPSJjYXJkLWxhYmVsIj5HaWZ0IE9yZGVyczwvc3Bhbj4KICAgICAgICAgICAgICAgIDxzcGFuIGNsYXNzPSJjYXJkLXZhbHVlIHR4dC1waW5rIj57eyBpbnZlbnRvcnlfdG90YWxzLmdpZnRfb3JkZXJzfGludGNvbW1hIH19PC9zcGFuPgogICAgICAgICAgICAgICAgPHNwYW4gY2xhc3M9ImNhcmQtY2FwdGlvbiI+4oKme3sgaW52ZW50b3J5X3RvdGFscy5naWZ0X3JldmVudWV8ZmxvYXRmb3JtYXQ6MnxpbnRjb21tYSB9fSBpbiBnaWZ0IHB1cmNoYXNlczwvc3Bhbj4KICAgICAgICAgICAgPC9hcnRpY2xlPg=="
$INV_I3A_B64 = "TG9ncyArIGZ1bGZpbGxlZCBTTVMgKyBub24tY2FuY2VsbGVkIGJvb3N0IG9yZGVycw=="
$INV_I3R_B64 = "TG9ncyArIGZ1bGZpbGxlZCBTTVMgKyBub24tY2FuY2VsbGVkIGJvb3N0IG9yZGVycyArIGdpZnQgb3JkZXJz"
$INV_I4A_B64 = "ICAgIDwvc2VjdGlvbj4KPC9tYWluPg=="
$INV_I4R_B64 = "ICAgIDwvc2VjdGlvbj4KCiAgICA8IS0tIEdpZnQgb3JkZXJzIGdyb3VwZWQgYnkgZ2lmdCBwcm9kdWN0IC0tPgogICAgPHNlY3Rpb24gY2xhc3M9InN0YXQtc2VjdGlvbiIgYXJpYS1sYWJlbGxlZGJ5PSJnaWZ0LW9yZGVycy1oZWFkaW5nIj4KICAgICAgICA8ZGl2IGNsYXNzPSJzZWN0aW9uLWhlYWRpbmctcm93Ij4KICAgICAgICAgICAgPGRpdj4KICAgICAgICAgICAgICAgIDxzcGFuIGNsYXNzPSJzZWN0aW9uLWV5ZWJyb3ciPkdpZnQgU2VuZGluZzwvc3Bhbj4KICAgICAgICAgICAgICAgIDxoMiBpZD0iZ2lmdC1vcmRlcnMtaGVhZGluZyIgY2xhc3M9InNlY3Rpb24taGVhZGluZyI+R2lmdCBPcmRlcnMg4oCUIHt7IHJhbmdlX2xhYmVsIH19PC9oMj4KICAgICAgICAgICAgPC9kaXY+CiAgICAgICAgICAgIDxzcGFuIGNsYXNzPSJpbnZlbnRvcnktY291bnQiPnt7IGludmVudG9yeV90b3RhbHMuZ2lmdF9vcmRlcnN8aW50Y29tbWEgfX0gb3JkZXJzPC9zcGFuPgogICAgICAgIDwvZGl2PgogICAgICAgIDxkaXYgY2xhc3M9InRhYmxlLXdyYXAgaW52ZW50b3J5LXNhbGVzLXRhYmxlIj4KICAgICAgICAgICAgPHRhYmxlPgogICAgICAgICAgICAgICAgPHRoZWFkPgogICAgICAgICAgICAgICAgICAgIDx0cj4KICAgICAgICAgICAgICAgICAgICAgICAgPHRoPkdpZnQgUHJvZHVjdDwvdGg+CiAgICAgICAgICAgICAgICAgICAgICAgIDx0aD5PcmRlcnM8L3RoPgogICAgICAgICAgICAgICAgICAgICAgICA8dGg+U2FsZXMgUmV2ZW51ZTwvdGg+CiAgICAgICAgICAgICAgICAgICAgICAgIDx0aD5MYXRlc3QgT3JkZXI8L3RoPgogICAgICAgICAgICAgICAgICAgIDwvdHI+CiAgICAgICAgICAgICAgICA8L3RoZWFkPgogICAgICAgICAgICAgICAgPHRib2R5PgogICAgICAgICAgICAgICAgICAgIHslIGZvciByb3cgaW4gZ2lmdF9yb3dzICV9CiAgICAgICAgICAgICAgICAgICAgPHRyPgogICAgICAgICAgICAgICAgICAgICAgICA8dGQgZGF0YS1sYWJlbD0iR2lmdCBQcm9kdWN0Ij48c3Ryb25nPnt7IHJvdy5ncm91cF9uYW1lIH19PC9zdHJvbmc+PC90ZD4KICAgICAgICAgICAgICAgICAgICAgICAgPHRkIGRhdGEtbGFiZWw9Ik9yZGVycyIgY2xhc3M9InF1YW50aXR5LWNlbGwiPnt7IHJvdy5vcmRlcnN8aW50Y29tbWEgfX08L3RkPgogICAgICAgICAgICAgICAgICAgICAgICA8dGQgZGF0YS1sYWJlbD0iU2FsZXMgUmV2ZW51ZSIgY2xhc3M9InRhYmxlLWVtcGhhc2lzIj7igqZ7eyByb3cucmV2ZW51ZXxmbG9hdGZvcm1hdDoyfGludGNvbW1hIH19PC90ZD4KICAgICAgICAgICAgICAgICAgICAgICAgPHRkIGRhdGEtbGFiZWw9IkxhdGVzdCBPcmRlciI+e3sgcm93Lmxhc3Rfb3JkZXJlZHxkYXRlOiJNIGQsIFkgSDppIiB9fTwvdGQ+CiAgICAgICAgICAgICAgICAgICAgPC90cj4KICAgICAgICAgICAgICAgICAgICB7JSBlbXB0eSAlfQogICAgICAgICAgICAgICAgICAgIDx0cj4KICAgICAgICAgICAgICAgICAgICAgICAgPHRkIGNvbHNwYW49IjQiIGNsYXNzPSJ0YWJsZS1lbXB0eSI+Tm8gZ2lmdCBvcmRlcnMgd2VyZSBwbGFjZWQgZHVyaW5nIHt7IHJhbmdlX2xhYmVsfGxvd2VyIH19LjwvdGQ+CiAgICAgICAgICAgICAgICAgICAgPC90cj4KICAgICAgICAgICAgICAgICAgICB7JSBlbmRmb3IgJX0KICAgICAgICAgICAgICAgIDwvdGJvZHk+CiAgICAgICAgICAgICAgICB7JSBpZiBnaWZ0X3Jvd3MgJX0KICAgICAgICAgICAgICAgIDx0Zm9vdD4KICAgICAgICAgICAgICAgICAgICA8dHIgY2xhc3M9InRhYmxlLXRvdGFsIj4KICAgICAgICAgICAgICAgICAgICAgICAgPHRkIGRhdGEtbGFiZWw9IlRvdGFsIj5BbGwgZ2lmdCBwcm9kdWN0czwvdGQ+CiAgICAgICAgICAgICAgICAgICAgICAgIDx0ZCBkYXRhLWxhYmVsPSJPcmRlcnMiPnt7IGludmVudG9yeV90b3RhbHMuZ2lmdF9vcmRlcnN8aW50Y29tbWEgfX08L3RkPgogICAgICAgICAgICAgICAgICAgICAgICA8dGQgZGF0YS1sYWJlbD0iU2FsZXMgUmV2ZW51ZSI+4oKme3sgaW52ZW50b3J5X3RvdGFscy5naWZ0X3JldmVudWV8ZmxvYXRmb3JtYXQ6MnxpbnRjb21tYSB9fTwvdGQ+CiAgICAgICAgICAgICAgICAgICAgICAgIDx0ZCBkYXRhLWxhYmVsPSJQZXJpb2QiPnt7IHJhbmdlX2xhYmVsIH19PC90ZD4KICAgICAgICAgICAgICAgICAgICA8L3RyPgogICAgICAgICAgICAgICAgPC90Zm9vdD4KICAgICAgICAgICAgICAgIHslIGVuZGlmICV9CiAgICAgICAgICAgIDwvdGFibGU+CiAgICAgICAgPC9kaXY+CiAgICA8L3NlY3Rpb24+CjwvbWFpbj4="
$ACCT_A_B64 = "ICAgICMgQUREIGJvdGggc28gZXZlcnl0aGluZyBjb3VudHMKICAgIHRvdGFsX3NwZW50ID0gdG90YWxfc3BlbnRfdHJhbnNhY3Rpb25zICsgdG90YWxfc3BlbnRfb3JkZXJzCgogICAgcmV0dXJuIHJlbmRlcigKICAgICAgICByZXF1ZXN0LAogICAgICAgICJwYW5lbC90cmFuc2FjdGlvbnMuaHRtbCIsCiAgICAgICAgewogICAgICAgICAgICAidHJhbnNhY3Rpb25zIjogdHJhbnNhY3Rpb25zLAogICAgICAgICAgICAidXNlcl93YWxsZXQiOiB1c2VyX3dhbGxldCwKICAgICAgICAgICAgInRvdGFsX3NwZW50IjogdG90YWxfc3BlbnQsCiAgICAgICAgfQogICAgKQ=="
$ACCT_R_B64 = "ICAgICMgQUREIGJvdGggc28gZXZlcnl0aGluZyBjb3VudHMKICAgIHRvdGFsX3NwZW50ID0gdG90YWxfc3BlbnRfdHJhbnNhY3Rpb25zICsgdG90YWxfc3BlbnRfb3JkZXJzCgogICAgIyBTdWNjZXNzZnVsIGRlcG9zaXRzIChtb25leSBpbikKICAgIHRvdGFsX2RlcG9zaXQgPSBUcmFuc2FjdGlvbi5vYmplY3RzLmZpbHRlcigKICAgICAgICB1c2VyPXJlcXVlc3QudXNlciwKICAgICAgICB0cmFuc2FjdGlvbl90eXBlPSJkZXBvc2l0IiwKICAgICAgICBzdGF0dXM9InN1Y2Nlc3NmdWwiLAogICAgKS5hZ2dyZWdhdGUodG90YWw9U3VtKCJhbW91bnQiKSlbInRvdGFsIl0gb3IgMAoKICAgICMgRGFzaGJvYXJkLXN0eWxlIHJvd3M6IGNyZWRpdC9kZWJpdCBkaXJlY3Rpb24gKyBkZXNjcmlwdGlvbiB0ZXh0CiAgICB0eF9yb3dzID0gW10KICAgIGZvciB0eCBpbiB0cmFuc2FjdGlvbnM6CiAgICAgICAgdHhfcm93cy5hcHBlbmQoewogICAgICAgICAgICAidHhuX3R5cGUiOiAiY3JlZGl0IiBpZiB0eC50cmFuc2FjdGlvbl90eXBlIGluICgKICAgICAgICAgICAgICAgICJkZXBvc2l0IiwgInJlZnVuZCIsICJyZWZlcnJhbCIsICJyZWRlZW0iLAogICAgICAgICAgICAgICAgImZ1bmRpbmciLCAiY3JlZGl0IiwgIndhbGxldF9mdW5kaW5nIiwKICAgICAgICAgICAgKSBlbHNlICJkZWJpdCIsCiAgICAgICAgICAgICJkZXNjcmlwdGlvbiI6IGdldGF0dHIodHgsICJkZXNjcmlwdGlvbiIsICIiKQogICAgICAgICAgICAgICAgICAgICAgICAgICBvciB0eC50cmFuc2FjdGlvbl90eXBlLnJlcGxhY2UoIl8iLCAiICIpLnRpdGxlKCksCiAgICAgICAgICAgICJjcmVhdGVkX2F0IjogdHguY3JlYXRlZF9hdCwKICAgICAgICAgICAgImFtb3VudCI6IHR4LmFtb3VudCwKICAgICAgICAgICAgInN0YXR1cyI6IHR4LnN0YXR1cywKICAgICAgICB9KQoKICAgIHJldHVybiByZW5kZXIoCiAgICAgICAgcmVxdWVzdCwKICAgICAgICAicGFuZWwvdHJhbnNhY3Rpb25zLmh0bWwiLAogICAgICAgIHsKICAgICAgICAgICAgInRyYW5zYWN0aW9ucyI6IHR4X3Jvd3MsCiAgICAgICAgICAgICJ1c2VyX3dhbGxldCI6IHVzZXJfd2FsbGV0LAogICAgICAgICAgICAidG90YWxfc3BlbnQiOiB0b3RhbF9zcGVudCwKICAgICAgICAgICAgInRvdGFsX2RlcG9zaXQiOiB0b3RhbF9kZXBvc2l0LAogICAgICAgIH0KICAgICk="


# ---------- 1) finance/services.py: gift orders in the sales inventory ----------
Write-Host "`n[1/5] Recording gift orders in the Sales Inventory totals..." -ForegroundColor Green
$svcPath = Join-Path $root "finance\services.py"
if (-not (Test-Path $svcPath)) {
    Write-Host "  WARNING: finance\services.py not found - skipping." -ForegroundColor Yellow
} else {
    Backup-Once $svcPath
    $hadCrlf = (Read-Utf8 $svcPath).Contains("`r`n")
    $svc = (Read-Utf8 $svcPath).Replace("`r`n", "`n")
    if ($svc.Contains('"gift_rows"')) {
        Write-Host "  already patched, skipping" -ForegroundColor DarkGray
    } else {
        $pairs = @(
            @((Decode $SVC_A1_B64), (Decode $SVC_R1_B64)),
            @((Decode $SVC_A2_B64), (Decode $SVC_R2_B64)),
            @((Decode $SVC_A3_B64), (Decode $SVC_R3_B64)),
            @((Decode $SVC_A4_B64), (Decode $SVC_R4_B64))
        )
        $ok = $true
        foreach ($pr in $pairs) {
            if ((Count-Occurrences $svc $pr[0]) -ne 1) { $ok = $false }
        }
        if (-not $ok) {
            Write-Host "  WARNING: expected code not found in finance\services.py - no changes made." -ForegroundColor Yellow
            Write-Host "  Send me the output so I can adjust the patch." -ForegroundColor Yellow
        } else {
            foreach ($pr in $pairs) { $svc = $svc.Replace($pr[0], $pr[1]) }
            if ($hadCrlf) { $svc = $svc.Replace("`n", "`r`n") }
            Write-Utf8 $svcPath $svc
            Write-Host "  gift orders now counted in the Sales Inventory" -ForegroundColor DarkGray
        }
    }
}

# ---------- 2) templates/finance/inventory.html ----------
Write-Host "`n[2/5] Updating the Sales Inventory page..." -ForegroundColor Green
$invPath = Join-Path $root "templates\finance\inventory.html"
if (-not (Test-Path $invPath)) {
    Write-Host "  WARNING: templates\finance\inventory.html not found - skipping." -ForegroundColor Yellow
} else {
    Backup-Once $invPath
    $hadCrlf = (Read-Utf8 $invPath).Contains("`r`n")
    $inv = (Read-Utf8 $invPath).Replace("`r`n", "`n")
    $changed = $false

    # Back to Admin button
    if ($inv.Contains("Back to Admin")) {
        Write-Host "  Back to Admin button already present" -ForegroundColor DarkGray
    } else {
        $a = Decode $INV_I1A_B64
        if ((Count-Occurrences $inv $a) -eq 1) {
            $inv = $inv.Replace($a, (Decode $INV_I1R_B64))
            $changed = $true
            Write-Host "  Back to Admin button added" -ForegroundColor DarkGray
        } else {
            Write-Host "  WARNING: header-actions anchor not found - Back to Admin skipped." -ForegroundColor Yellow
        }
    }

    # Gift Orders stat card
    if ($inv.Contains("inventory_totals.gift_orders")) {
        Write-Host "  Gift Orders card already present" -ForegroundColor DarkGray
    } else {
        $a = Decode $INV_I2A_B64
        if ((Count-Occurrences $inv $a) -eq 1) {
            $inv = $inv.Replace($a, (Decode $INV_I2R_B64))
            $changed = $true
            Write-Host "  Gift Orders card added" -ForegroundColor DarkGray
        } else {
            Write-Host "  WARNING: stat-card anchor not found - Gift Orders card skipped." -ForegroundColor Yellow
        }
    }

    # primary card caption
    if ($inv.Contains("+ gift orders")) {
        Write-Host "  summary caption already updated" -ForegroundColor DarkGray
    } else {
        $a = Decode $INV_I3A_B64
        if ((Count-Occurrences $inv $a) -eq 1) {
            $inv = $inv.Replace($a, (Decode $INV_I3R_B64))
            $changed = $true
            Write-Host "  summary caption updated" -ForegroundColor DarkGray
        } else {
            Write-Host "  WARNING: caption anchor not found - caption skipped." -ForegroundColor Yellow
        }
    }

    # Gift Orders table section
    if ($inv.Contains("gift-orders-heading")) {
        Write-Host "  Gift Orders table already present" -ForegroundColor DarkGray
    } else {
        $a = Decode $INV_I4A_B64
        if ((Count-Occurrences $inv $a) -eq 1) {
            $inv = $inv.Replace($a, (Decode $INV_I4R_B64))
            $changed = $true
            Write-Host "  Gift Orders table added" -ForegroundColor DarkGray
        } else {
            Write-Host "  WARNING: </main> anchor not found - Gift Orders table skipped." -ForegroundColor Yellow
        }
    }

    if ($changed) {
        if ($hadCrlf) { $inv = $inv.Replace("`n", "`r`n") }
        Write-Utf8 $invPath $inv
    }
}

# ---------- 3) templates/panel/transactions.html (dashboard-style list) ----------
Write-Host "`n[3/5] Redesigning the Transactions page..." -ForegroundColor Green
$txPath = Join-Path $root "templates\panel\transactions.html"
if (-not (Test-Path $txPath)) {
    Write-Host "  WARNING: templates\panel\transactions.html not found - skipping." -ForegroundColor Yellow
} else {
    $current = Read-Utf8 $txPath
    if ($current.Contains("transactions-list-card")) {
        Write-Host "  already redesigned, skipping" -ForegroundColor DarkGray
    } else {
        Backup-Once $txPath
        Write-Utf8 $txPath (Decode $TX_HTML_B64)
        Write-Host "  transactions page now matches the dashboard style" -ForegroundColor DarkGray
    }
}

# ---------- 4) static/css/transactions.css ----------
Write-Host "`n[4/5] Adding the dashboard-row styles to transactions.css..." -ForegroundColor Green
$cssPath = Join-Path $root "static\css\transactions.css"
if (-not (Test-Path $cssPath)) {
    Write-Host "  WARNING: static\css\transactions.css not found - skipping." -ForegroundColor Yellow
} else {
    $css = Read-Utf8 $cssPath
    if ($css.Contains("DASHBOARD-STYLE TRANSACTION LIST")) {
        Write-Host "  styles already present, skipping" -ForegroundColor DarkGray
    } else {
        Backup-Once $cssPath
        $css = $css.TrimEnd() + (Decode $TX_CSS_B64)
        Write-Utf8 $cssPath $css
        Write-Host "  styles appended" -ForegroundColor DarkGray
    }
}

# ---------- 5) accounts/views.py: feed the new transactions list ----------
Write-Host "`n[5/5] Updating the transactions view..." -ForegroundColor Green
$acctPath = Join-Path $root "accounts\views.py"
if (-not (Test-Path $acctPath)) {
    Write-Host "  WARNING: accounts\views.py not found - skipping." -ForegroundColor Yellow
} else {
    Backup-Once $acctPath
    $hadCrlf = (Read-Utf8 $acctPath).Contains("`r`n")
    $acct = (Read-Utf8 $acctPath).Replace("`r`n", "`n")
    if ($acct.Contains('"total_deposit": total_deposit,')) {
        Write-Host "  already patched, skipping" -ForegroundColor DarkGray
    } else {
        $a = Decode $ACCT_A_B64
        if ((Count-Occurrences $acct $a) -ne 1) {
            Write-Host "  WARNING: expected code not found in accounts\views.py - no changes made." -ForegroundColor Yellow
            Write-Host "  Send me the output so I can adjust the patch." -ForegroundColor Yellow
        } else {
            $acct = $acct.Replace($a, (Decode $ACCT_R_B64))
            if ($hadCrlf) { $acct = $acct.Replace("`n", "`r`n") }
            Write-Utf8 $acctPath $acct
            Write-Host "  transactions view updated (rows + total deposits)" -ForegroundColor DarkGray
        }
    }
}

# ---------- done ----------
Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host " Done! Next steps:" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Check the changes:" -ForegroundColor White
Write-Host "     findstr /C:`"gift_rows`" finance\services.py" -ForegroundColor Gray
Write-Host "     findstr /C:`"Back to Admin`" templates\finance\inventory.html" -ForegroundColor Gray
Write-Host "     findstr /C:`"transactions-list-card`" templates\panel\transactions.html" -ForegroundColor Gray
Write-Host "   Each command should print a line." -ForegroundColor Gray
Write-Host ""
Write-Host "2. Publish to Render:" -ForegroundColor White
Write-Host "     git add ." -ForegroundColor Gray
Write-Host "     git commit -m `"inventory gift orders + transactions redesign`"" -ForegroundColor Gray
Write-Host "     git push" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Wait until Render shows 'Deploy live', then in the Render Shell run:" -ForegroundColor White
Write-Host "     python manage.py collectstatic --noinput" -ForegroundColor Gray
Write-Host "   (No migrate needed - no database changes in this update.)" -ForegroundColor Gray
Write-Host ""
Write-Host "Then open Finance -> Sales Inventory: you will see the Gift Orders" -ForegroundColor White
Write-Host "card and table plus a Back to Admin button, and your Transactions" -ForegroundColor White
Write-Host "page will look like the dashboard's Recent Transactions list." -ForegroundColor White
