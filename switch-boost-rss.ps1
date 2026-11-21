#Requires -Version 5.1
<#
    ABFverify - Switch boost provider to ReallySimpleSocial (v1)
    ============================================================
    * Replaces the GoodLuckBoostHub provider class with ReallySimpleSocial
      (same API v2 shape, https://reallysimplesocial.com/api/v2).
    * Renames every GoodLuckBoostHub / GLBH_API_KEY reference project-wide.
    * Rewrites the service sync (admin action + `manage.py sync_boost`):
      imports the FULL ReallySimpleSocial catalog - service ID, name,
      category, rate, min/max, refill/cancel - and hides anything the
      provider no longer offers (old services stay for order history).
    * Updates pricing labels to USD + adds migration 0007.
    * Adds RSS_API_KEY to .env.example.

    Safe to re-run. Backups (.bak-rss) are created before any file changes.
#>

$ErrorActionPreference = 'Stop'

Write-Host ""
Write-Host "======================================================" -ForegroundColor Magenta
Write-Host "   ABFverify - Boost provider switch  v1.3" -ForegroundColor Magenta
Write-Host "   GoodLuckBoostHub  ->  ReallySimpleSocial" -ForegroundColor Magenta
Write-Host "======================================================" -ForegroundColor Magenta
Write-Host ""

# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
function Read-Utf8([string]$Path) {
    # Reads a source file correctly no matter how it was saved:
    # BOM detection first (UTF-16LE/BE, UTF-8), then a UTF-16 guess
    # via NUL bytes (files saved UTF-16 WITHOUT a BOM), else UTF-8.
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
function Write-Utf8([string]$Path, [string]$Content) {
    # Always writes UTF-8 (no BOM) - what Django/Python expects.
    [IO.File]::WriteAllText($Path, $Content, (New-Object System.Text.UTF8Encoding($false)))
}
function Decode([string]$B64) {
    return [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($B64))
}
function Backup-Once([string]$Path) {
    $bak = "$Path.bak-rss"
    if (-not (Test-Path $bak)) { Copy-Item $Path $bak -Force }
}
function Count-Occurrences([string]$Haystack, [string]$Needle) {
    $n = 0; $i = 0
    while (($i = $Haystack.IndexOf($Needle, $i)) -ge 0) { $n++; $i += $Needle.Length }
    return $n
}
function Ok([string]$m)   { Write-Host "  [OK]   $m" -ForegroundColor Green }
function Skip([string]$m) { Write-Host "  [SKIP] $m" -ForegroundColor DarkGray }
function Warn([string]$m) { $script:Warnings += $m; Write-Host "  [WARN] $m" -ForegroundColor Yellow }

$script:Warnings = @()
$script:Changed  = @()

# ---------------------------------------------------------------
# Locate project root
# ---------------------------------------------------------------
$root = (Get-Location).Path
if (-not (Test-Path (Join-Path $root 'manage.py')) -or
    -not (Test-Path (Join-Path $root 'config\settings.py'))) {
    Write-Host ""
    Write-Host "ERROR: manage.py / config\settings.py not found." -ForegroundColor Red
    Write-Host "Run this script from the project root, e.g.:" -ForegroundColor Red
    Write-Host "  cd C:\Users\user\OneDrive\Desktop\ABFverify" -ForegroundColor Red
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\switch-boost-rss.ps1" -ForegroundColor Red
    exit 1
}
Write-Host "Project root: $root" -ForegroundColor Cyan
Write-Host ""

# ---------------------------------------------------------------
# Payloads (base64-encoded full file contents)
# ---------------------------------------------------------------
$B64_PROVIDERS = 'aW1wb3J0IHJlcXVlc3RzCmZyb20gZGphbmdvLmNvbmYgaW1wb3J0IHNldHRpbmdzCgoKY2xhc3MgUmVhbGx5U2ltcGxlU29jaWFsRXJyb3IoRXhjZXB0aW9uKToKICAgIHBhc3MKCgpjbGFzcyBSZWFsbHlTaW1wbGVTb2NpYWw6CiAgICBCQVNFX1VSTCA9ICJodHRwczovL3JlYWxseXNpbXBsZXNvY2lhbC5jb20vYXBpL3YyIgoKICAgIGRlZiBfX2luaXRfXyhzZWxmLCBhcGlfa2V5PU5vbmUpOgogICAgICAgIHNlbGYuYXBpX2tleSA9IGFwaV9rZXkgb3Igc2V0dGluZ3MuUlNTX0FQSV9LRVkKICAgICAgICBpZiBub3Qgc2VsZi5hcGlfa2V5OgogICAgICAgICAgICByYWlzZSBSZWFsbHlTaW1wbGVTb2NpYWxFcnJvcigiUlNTX0FQSV9LRVkgaXMgbm90IGNvbmZpZ3VyZWQiKQoKICAgIGRlZiBfcmVxdWVzdChzZWxmLCAqKnBhcmFtcyk6CiAgICAgICAgcGFyYW1zWyJrZXkiXSA9IHNlbGYuYXBpX2tleQogICAgICAgIHRyeToKICAgICAgICAgICAgcmVzcCA9IHJlcXVlc3RzLnBvc3Qoc2VsZi5CQVNFX1VSTCwgZGF0YT1wYXJhbXMsIHRpbWVvdXQ9MzApCiAgICAgICAgICAgIHJlc3AucmFpc2VfZm9yX3N0YXR1cygpCiAgICAgICAgZXhjZXB0IHJlcXVlc3RzLlJlcXVlc3RFeGNlcHRpb24gYXMgZToKICAgICAgICAgICAgcmFpc2UgUmVhbGx5U2ltcGxlU29jaWFsRXJyb3IoZiJDb25uZWN0aW9uIGVycm9yOiB7ZX0iKQoKICAgICAgICB0cnk6CiAgICAgICAgICAgIGRhdGEgPSByZXNwLmpzb24oKQogICAgICAgIGV4Y2VwdCBWYWx1ZUVycm9yOgogICAgICAgICAgICByYWlzZSBSZWFsbHlTaW1wbGVTb2NpYWxFcnJvcigiSW52YWxpZCByZXNwb25zZSBmcm9tIHByb3ZpZGVyIikKCiAgICAgICAgIyBUaGlzIEFQSSByZXR1cm5zIHsiZXJyb3IiOiAiLi4uIn0gb24gZmFpbHVyZQogICAgICAgIGlmIGlzaW5zdGFuY2UoZGF0YSwgZGljdCkgYW5kIGRhdGEuZ2V0KCJlcnJvciIpOgogICAgICAgICAgICByYWlzZSBSZWFsbHlTaW1wbGVTb2NpYWxFcnJvcihkYXRhWyJlcnJvciJdKQoKICAgICAgICByZXR1cm4gZGF0YQoKICAgIGRlZiBnZXRfc2VydmljZXMoc2VsZik6CiAgICAgICAgcmV0dXJuIHNlbGYuX3JlcXVlc3QoYWN0aW9uPSJzZXJ2aWNlcyIpCgogICAgZGVmIGFkZF9vcmRlcihzZWxmLCBzZXJ2aWNlX2lkLCBsaW5rLCBxdWFudGl0eSk6CiAgICAgICAgZGF0YSA9IHNlbGYuX3JlcXVlc3QoCiAgICAgICAgICAgIGFjdGlvbj0iYWRkIiwKICAgICAgICAgICAgc2VydmljZT1zZXJ2aWNlX2lkLAogICAgICAgICAgICBsaW5rPWxpbmssCiAgICAgICAgICAgIHF1YW50aXR5PXF1YW50aXR5LAogICAgICAgICkKICAgICAgICByZXR1cm4gZGF0YVsib3JkZXIiXQoKICAgIGRlZiBnZXRfb3JkZXJfc3RhdHVzKHNlbGYsIG9yZGVyX2lkKToKICAgICAgICAiIiJTaW5nbGUgb3JkZXIgc3RhdHVzLiIiIgogICAgICAgIHJldHVybiBzZWxmLl9yZXF1ZXN0KGFjdGlvbj0ic3RhdHVzIiwgb3JkZXI9b3JkZXJfaWQpCgogICAgZGVmIGdldF9vcmRlcnNfc3RhdHVzKHNlbGYsIG9yZGVyX2lkcyk6CiAgICAgICAgIiIib3JkZXJfaWRzOiBsaXN0IG9mIHByb3ZpZGVyIG9yZGVyIElEcyAobWF4IDEwMCkiIiIKICAgICAgICByZXR1cm4gc2VsZi5fcmVxdWVzdChhY3Rpb249InN0YXR1cyIsIG9yZGVycz0iLCIuam9pbihzdHIoaSkgZm9yIGkgaW4gb3JkZXJfaWRzKSkKCiAgICBkZWYgcmVmaWxsKHNlbGYsIG9yZGVyX2lkKToKICAgICAgICAiIiJDcmVhdGUgYSByZWZpbGwgZm9yIGEgc2luZ2xlIG9yZGVyLiBSZXR1cm5zIHJlZmlsbCBJRC4iIiIKICAgICAgICByZXR1cm4gc2VsZi5fcmVxdWVzdChhY3Rpb249InJlZmlsbCIsIG9yZGVyPW9yZGVyX2lkKQoKICAgIGRlZiBjYW5jZWwoc2VsZiwgb3JkZXJfaWRzKToKICAgICAgICAiIiJDYW5jZWwgb25lIG9yIG1vcmUgb3JkZXJzLiBSZXR1cm5zIGxpc3Qgb2Yge29yZGVyLCBjYW5jZWx9IHJlc3VsdHMuIiIiCiAgICAgICAgaWYgaXNpbnN0YW5jZShvcmRlcl9pZHMsIChsaXN0LCB0dXBsZSkpOgogICAgICAgICAgICBpZHMgPSAiLCIuam9pbihzdHIoaSkgZm9yIGkgaW4gb3JkZXJfaWRzKQogICAgICAgIGVsc2U6CiAgICAgICAgICAgIGlkcyA9IHN0cihvcmRlcl9pZHMpCiAgICAgICAgcmV0dXJuIHNlbGYuX3JlcXVlc3QoYWN0aW9uPSJjYW5jZWwiLCBvcmRlcnM9aWRzKQoKICAgIGRlZiBnZXRfYmFsYW5jZShzZWxmKToKICAgICAgICByZXR1cm4gc2VsZi5fcmVxdWVzdChhY3Rpb249ImJhbGFuY2UiKQo='
$B64_ADMIN = 'ZnJvbSBkamFuZ28uY29udHJpYiBpbXBvcnQgYWRtaW4KCmZyb20gLm1vZGVscyBpbXBvcnQgQm9vc3RTZXJ2aWNlLCBCb29zdE9yZGVyLCBCb29zdFNldHRpbmdzCmZyb20gLnByb3ZpZGVycyBpbXBvcnQgUmVhbGx5U2ltcGxlU29jaWFsLCBSZWFsbHlTaW1wbGVTb2NpYWxFcnJvcgoKCkBhZG1pbi5yZWdpc3RlcihCb29zdFNlcnZpY2UpCmNsYXNzIEJvb3N0U2VydmljZUFkbWluKGFkbWluLk1vZGVsQWRtaW4pOgogICAgbGlzdF9kaXNwbGF5ID0gKCJzZXJ2aWNlX2lkIiwgIm5hbWUiLCAiY2F0ZWdvcnkiLCAicmF0ZSIsICJtaW5fb3JkZXIiLCAibWF4X29yZGVyIiwgImlzX2FjdGl2ZSIpCiAgICBsaXN0X2ZpbHRlciA9ICgiY2F0ZWdvcnkiLCAiaXNfYWN0aXZlIiwgInJlZmlsbCIsICJjYW5jZWwiKQogICAgc2VhcmNoX2ZpZWxkcyA9ICgibmFtZSIsICJjYXRlZ29yeSIsICJzZXJ2aWNlX2lkIikKICAgIGxpc3RfcGVyX3BhZ2UgPSA1MAogICAgYWN0aW9ucyA9IFsic3luY19mcm9tX2FwaSJdCgogICAgQGFkbWluLmFjdGlvbihkZXNjcmlwdGlvbj0iU3luYyBzZXJ2aWNlcyBmcm9tIFJlYWxseVNpbXBsZVNvY2lhbCAoZmV0Y2hlcyBBTEwpIikKICAgIGRlZiBzeW5jX2Zyb21fYXBpKHNlbGYsIHJlcXVlc3QsIHF1ZXJ5c2V0KToKICAgICAgICB0cnk6CiAgICAgICAgICAgIHByb3ZpZGVyID0gUmVhbGx5U2ltcGxlU29jaWFsKCkKICAgICAgICAgICAgc2VydmljZXMgPSBwcm92aWRlci5nZXRfc2VydmljZXMoKQogICAgICAgIGV4Y2VwdCBSZWFsbHlTaW1wbGVTb2NpYWxFcnJvciBhcyBlOgogICAgICAgICAgICBzZWxmLm1lc3NhZ2VfdXNlcihyZXF1ZXN0LCBmIlN5bmMgZmFpbGVkOiB7ZX0iLCBsZXZlbD0iZXJyb3IiKQogICAgICAgICAgICByZXR1cm4KCiAgICAgICAgIyBIaWRlIGV2ZXJ5dGhpbmcgbm90IGluIHRoZSBwcm92aWRlcidzIGN1cnJlbnQgY2F0YWxvZywgc28gb2xkCiAgICAgICAgIyBsZWZ0b3ZlcnMgc3RheSBmb3Igb3JkZXIgaGlzdG9yeSBidXQgY2FuIG5vIGxvbmdlciBiZSBvcmRlcmVkLgogICAgICAgIEJvb3N0U2VydmljZS5vYmplY3RzLnVwZGF0ZShpc19hY3RpdmU9RmFsc2UpCgogICAgICAgIGNyZWF0ZWQgPSB1cGRhdGVkID0gMAogICAgICAgIGZvciBzIGluIHNlcnZpY2VzOgogICAgICAgICAgICBkZWZhdWx0cyA9IHsKICAgICAgICAgICAgICAgICJuYW1lIjogc1sibmFtZSJdLAogICAgICAgICAgICAgICAgImNhdGVnb3J5Ijogcy5nZXQoImNhdGVnb3J5IiwgIiIpLAogICAgICAgICAgICAgICAgInNlcnZpY2VfdHlwZSI6IHMuZ2V0KCJ0eXBlIiwgIiIpLAogICAgICAgICAgICAgICAgInJhdGUiOiBzWyJyYXRlIl0sCiAgICAgICAgICAgICAgICAibWluX29yZGVyIjogc1sibWluIl0sCiAgICAgICAgICAgICAgICAibWF4X29yZGVyIjogc1sibWF4Il0sCiAgICAgICAgICAgICAgICAicmVmaWxsIjogYm9vbChzLmdldCgicmVmaWxsIikpLAogICAgICAgICAgICAgICAgImNhbmNlbCI6IGJvb2wocy5nZXQoImNhbmNlbCIpKSwKICAgICAgICAgICAgICAgICJpc19hY3RpdmUiOiBUcnVlLAogICAgICAgICAgICB9CgogICAgICAgICAgICAjIEltcG9ydCBkZXNjcmlwdGlvbiBvbmx5IGlmIHRoZSBBUEkgcmV0dXJucyBvbmUg4oCUIG90aGVyd2lzZQogICAgICAgICAgICAjIGtlZXAgd2hhdGV2ZXIgaXMgYWxyZWFkeSBzYXZlZCAoZS5nLiB3cml0dGVuIG1hbnVhbGx5IGluIGFkbWluKQogICAgICAgICAgICBkZXNjID0gcy5nZXQoImRlc2NyaXB0aW9uIikgb3Igcy5nZXQoImRlc2MiKQogICAgICAgICAgICBpZiBkZXNjOgogICAgICAgICAgICAgICAgZGVmYXVsdHNbImRlc2NyaXB0aW9uIl0gPSBkZXNjCgogICAgICAgICAgICBfLCB3YXNfY3JlYXRlZCA9IEJvb3N0U2VydmljZS5vYmplY3RzLnVwZGF0ZV9vcl9jcmVhdGUoCiAgICAgICAgICAgICAgICBzZXJ2aWNlX2lkPXNbInNlcnZpY2UiXSwKICAgICAgICAgICAgICAgIGRlZmF1bHRzPWRlZmF1bHRzLAogICAgICAgICAgICApCiAgICAgICAgICAgIGlmIHdhc19jcmVhdGVkOgogICAgICAgICAgICAgICAgY3JlYXRlZCArPSAxCiAgICAgICAgICAgIGVsc2U6CiAgICAgICAgICAgICAgICB1cGRhdGVkICs9IDEKCiAgICAgICAgc2VsZi5tZXNzYWdlX3VzZXIocmVxdWVzdCwgZiJTeW5jIGNvbXBsZXRlOiB7Y3JlYXRlZH0gbmV3LCB7dXBkYXRlZH0gdXBkYXRlZC4iKQoKCkBhZG1pbi5yZWdpc3RlcihCb29zdE9yZGVyKQpjbGFzcyBCb29zdE9yZGVyQWRtaW4oYWRtaW4uTW9kZWxBZG1pbik6CiAgICBsaXN0X2Rpc3BsYXkgPSAoInByb3ZpZGVyX29yZGVyX2lkIiwgInVzZXIiLCAic2VydmljZSIsICJxdWFudGl0eSIsICJwcmljZSIsICJzdGF0dXMiLCAiY3JlYXRlZF9hdCIpCiAgICBsaXN0X2ZpbHRlciA9ICgic3RhdHVzIiwpCiAgICBzZWFyY2hfZmllbGRzID0gKCJwcm92aWRlcl9vcmRlcl9pZCIsICJsaW5rIiwgInVzZXJfX3VzZXJuYW1lIikKICAgIHJlYWRvbmx5X2ZpZWxkcyA9ICgicHJvdmlkZXJfb3JkZXJfaWQiLCAic3RhcnRfY291bnQiLCAicmVtYWlucyIpCgoKQGFkbWluLnJlZ2lzdGVyKEJvb3N0U2V0dGluZ3MpCmNsYXNzIEJvb3N0U2V0dGluZ3NBZG1pbihhZG1pbi5Nb2RlbEFkbWluKToKICAgIGxpc3RfZGlzcGxheSA9ICgiZXhjaGFuZ2VfcmF0ZSIsICJwcm9maXRfZmxhdCIsICJwcm9maXRfcGVyY2VudCIsICJ1cGRhdGVkX2F0IikKCiAgICBkZWYgaGFzX2FkZF9wZXJtaXNzaW9uKHNlbGYsIHJlcXVlc3QpOgogICAgICAgIHJldHVybiBub3QgQm9vc3RTZXR0aW5ncy5vYmplY3RzLmV4aXN0cygpCg=='
$B64_SYNC = 'ZnJvbSBkamFuZ28uY29yZS5tYW5hZ2VtZW50LmJhc2UgaW1wb3J0IEJhc2VDb21tYW5kCgpmcm9tIGJvb3N0Lm1vZGVscyBpbXBvcnQgQm9vc3RTZXJ2aWNlCmZyb20gYm9vc3QucHJvdmlkZXJzIGltcG9ydCBSZWFsbHlTaW1wbGVTb2NpYWwsIFJlYWxseVNpbXBsZVNvY2lhbEVycm9yCgoKY2xhc3MgQ29tbWFuZChCYXNlQ29tbWFuZCk6CiAgICBoZWxwID0gIlN5bmMgYm9vc3Qgc2VydmljZXMgZnJvbSBSZWFsbHlTaW1wbGVTb2NpYWwgaW50byB0aGUgZGF0YWJhc2UiCgogICAgZGVmIGhhbmRsZShzZWxmLCAqYXJncywgKipvcHRpb25zKToKICAgICAgICB0cnk6CiAgICAgICAgICAgIHByb3ZpZGVyID0gUmVhbGx5U2ltcGxlU29jaWFsKCkKICAgICAgICAgICAgc2VydmljZXMgPSBwcm92aWRlci5nZXRfc2VydmljZXMoKQogICAgICAgIGV4Y2VwdCBSZWFsbHlTaW1wbGVTb2NpYWxFcnJvciBhcyBlOgogICAgICAgICAgICBzZWxmLnN0ZGVyci53cml0ZShzZWxmLnN0eWxlLkVSUk9SKGYiU3luYyBmYWlsZWQ6IHtlfSIpKQogICAgICAgICAgICByZXR1cm4KCiAgICAgICAgIyBIaWRlIGV2ZXJ5dGhpbmcgbm90IGluIHRoZSBwcm92aWRlcidzIGN1cnJlbnQgY2F0YWxvZywgc28gb2xkCiAgICAgICAgIyBsZWZ0b3ZlcnMgc3RheSBmb3Igb3JkZXIgaGlzdG9yeSBidXQgY2FuIG5vIGxvbmdlciBiZSBvcmRlcmVkLgogICAgICAgIEJvb3N0U2VydmljZS5vYmplY3RzLnVwZGF0ZShpc19hY3RpdmU9RmFsc2UpCgogICAgICAgIGNyZWF0ZWQgPSB1cGRhdGVkID0gMAogICAgICAgIGZvciBzIGluIHNlcnZpY2VzOgogICAgICAgICAgICBkZWZhdWx0cyA9IHsKICAgICAgICAgICAgICAgICJuYW1lIjogc1sibmFtZSJdLAogICAgICAgICAgICAgICAgImNhdGVnb3J5Ijogcy5nZXQoImNhdGVnb3J5IiwgIiIpLAogICAgICAgICAgICAgICAgInNlcnZpY2VfdHlwZSI6IHMuZ2V0KCJ0eXBlIiwgIiIpLAogICAgICAgICAgICAgICAgInJhdGUiOiBzWyJyYXRlIl0sCiAgICAgICAgICAgICAgICAibWluX29yZGVyIjogc1sibWluIl0sCiAgICAgICAgICAgICAgICAibWF4X29yZGVyIjogc1sibWF4Il0sCiAgICAgICAgICAgICAgICAicmVmaWxsIjogYm9vbChzLmdldCgicmVmaWxsIikpLAogICAgICAgICAgICAgICAgImNhbmNlbCI6IGJvb2wocy5nZXQoImNhbmNlbCIpKSwKICAgICAgICAgICAgICAgICJpc19hY3RpdmUiOiBUcnVlLAogICAgICAgICAgICB9CiAgICAgICAgICAgIGRlc2MgPSBzLmdldCgiZGVzY3JpcHRpb24iKSBvciBzLmdldCgiZGVzYyIpCiAgICAgICAgICAgIGlmIGRlc2M6CiAgICAgICAgICAgICAgICBkZWZhdWx0c1siZGVzY3JpcHRpb24iXSA9IGRlc2MKCiAgICAgICAgICAgIF8sIHdhc19jcmVhdGVkID0gQm9vc3RTZXJ2aWNlLm9iamVjdHMudXBkYXRlX29yX2NyZWF0ZSgKICAgICAgICAgICAgICAgIHNlcnZpY2VfaWQ9c1sic2VydmljZSJdLAogICAgICAgICAgICAgICAgZGVmYXVsdHM9ZGVmYXVsdHMsCiAgICAgICAgICAgICkKICAgICAgICAgICAgaWYgd2FzX2NyZWF0ZWQ6CiAgICAgICAgICAgICAgICBjcmVhdGVkICs9IDEKICAgICAgICAgICAgZWxzZToKICAgICAgICAgICAgICAgIHVwZGF0ZWQgKz0gMQoKICAgICAgICBzZWxmLnN0ZG91dC53cml0ZShzZWxmLnN0eWxlLlNVQ0NFU1MoCiAgICAgICAgICAgIGYiU3luYyBjb21wbGV0ZToge2NyZWF0ZWR9IG5ldywge3VwZGF0ZWR9IHVwZGF0ZWQuIFRvdGFsIHJlY2VpdmVkOiB7bGVuKHNlcnZpY2VzKX0iCiAgICAgICAgKSkK'
$B64_MIGRATION = 'IyBTd2l0Y2hlcyBib29zdCBwcmljaW5nIGxhYmVscyB0byBVU0QgKFJlYWxseVNpbXBsZVNvY2lhbCBiaWxscyBpbiBVU0QpLgpmcm9tIGRqYW5nby5kYiBpbXBvcnQgbWlncmF0aW9ucywgbW9kZWxzCgoKY2xhc3MgTWlncmF0aW9uKG1pZ3JhdGlvbnMuTWlncmF0aW9uKToKCiAgICBkZXBlbmRlbmNpZXMgPSBbCiAgICAgICAgKCdib29zdCcsICcwMDA2X2FsdGVyX2Jvb3N0b3JkZXJfcHJvdmlkZXJfY29zdF9hbmRfbW9yZScpLAogICAgXQoKICAgIG9wZXJhdGlvbnMgPSBbCiAgICAgICAgbWlncmF0aW9ucy5BbHRlckZpZWxkKAogICAgICAgICAgICBtb2RlbF9uYW1lPSdib29zdHNldHRpbmdzJywKICAgICAgICAgICAgbmFtZT0nZXhjaGFuZ2VfcmF0ZScsCiAgICAgICAgICAgIGZpZWxkPW1vZGVscy5EZWNpbWFsRmllbGQoZGVjaW1hbF9wbGFjZXM9MiwgZGVmYXVsdD0xLjAsIGhlbHBfdGV4dD0nUmVhbGx5U2ltcGxlU29jaWFsIGJpbGxzIGluIFVTRC4gU2V0IHRoaXMgdG8gdGhlIGN1cnJlbnQgTkdOIHZhbHVlIG9mICQxIChlLmcuIDE1MDApLicsIG1heF9kaWdpdHM9MTApLAogICAgICAgICksCiAgICAgICAgbWlncmF0aW9ucy5BbHRlckZpZWxkKAogICAgICAgICAgICBtb2RlbF9uYW1lPSdib29zdHNlcnZpY2UnLAogICAgICAgICAgICBuYW1lPSdyYXRlJywKICAgICAgICAgICAgZmllbGQ9bW9kZWxzLkRlY2ltYWxGaWVsZChkZWNpbWFsX3BsYWNlcz00LCBoZWxwX3RleHQ9J1Byb3ZpZGVyIGNvc3QgcGVyIDEwMDAgdW5pdHMgKFVTRCknLCBtYXhfZGlnaXRzPTE2KSwKICAgICAgICApLAogICAgXQo='

# ===============================================================
# PART 1 - boost/providers.py : ReallySimpleSocial provider class
# ===============================================================
Write-Host "1. boost\providers.py - ReallySimpleSocial provider" -ForegroundColor Cyan
$provPath = Join-Path $root 'boost\providers.py'
if (-not (Test-Path $provPath)) { throw "boost\providers.py not found." }
$prov = Read-Utf8 $provPath
if ($prov.Contains('class ReallySimpleSocial')) {
    Skip "provider already switched"
} else {
    if ((Count-Occurrences $prov 'class GoodLuckBoostHub') -lt 1) {
        $head = ([IO.File]::ReadAllBytes($provPath) | Select-Object -First 16) -join ','
        throw "boost\providers.py does not contain the expected GoodLuckBoostHub class (first bytes: $head) - aborting before touching anything."
    }
    Backup-Once $provPath
    Write-Utf8 $provPath (Decode $B64_PROVIDERS)
    $script:Changed += 'boost\providers.py'
    Ok "provider class replaced (api/v2, RSS_API_KEY)"
}

# ===============================================================
# PART 2 - boost/admin.py : RSS sync action (import all services)
# ===============================================================
Write-Host "2. boost\admin.py - sync action" -ForegroundColor Cyan
$adminPath = Join-Path $root 'boost\admin.py'
if (-not (Test-Path $adminPath)) { throw "boost\admin.py not found." }
$admin = Read-Utf8 $adminPath
if ($admin.Contains('ReallySimpleSocial')) {
    Skip "admin already switched"
} else {
    if ((Count-Occurrences $admin 'GoodLuckBoostHub') -lt 1) {
        throw "boost\admin.py does not reference GoodLuckBoostHub - aborting."
    }
    Backup-Once $adminPath
    Write-Utf8 $adminPath (Decode $B64_ADMIN)
    $script:Changed += 'boost\admin.py'
    Ok "admin sync action now imports the full ReallySimpleSocial catalog"
}

# ===============================================================
# PART 3 - boost/management/commands/sync_boost.py : RSS sync
# ===============================================================
Write-Host "3. sync_boost command" -ForegroundColor Cyan
$syncPath = Join-Path $root 'boost\management\commands\sync_boost.py'
if (-not (Test-Path $syncPath)) { throw "boost\management\commands\sync_boost.py not found." }
$sync = Read-Utf8 $syncPath
if ($sync.Contains('ReallySimpleSocial')) {
    Skip "sync command already switched"
} else {
    Backup-Once $syncPath
    Write-Utf8 $syncPath (Decode $B64_SYNC)
    $script:Changed += 'boost\management\commands\sync_boost.py'
    Ok "sync_boost now pulls from ReallySimpleSocial"
}

# ===============================================================
# PART 4 - Project-wide rename: GoodLuckBoostHub -> ReallySimpleSocial
# ===============================================================
Write-Host "4. Renaming remaining provider references" -ForegroundColor Cyan
$renameFiles = @(
    'boost\views.py',
    'boost\scheduler.py',
    'boost\models.py',
    'accounts\management\commands\expire_orders.py',
    'config\settings.py',
    'boost\management\commands\boost_audit.py',
    'boost\management\commands\boost_clean.py',
    'boost\management\commands\boost_provider_review.py',
    'boost\management\commands\boost_ratecheck.py',
    'boost\management\commands\boost_reset.py',
    'boost\management\commands\boost_sync_glbh.py',
    'boost\management\commands\import_tiktok_followers.py',
    'boost\management\commands\swap_fb_followers.py'
)
foreach ($rel in $renameFiles) {
    $p = Join-Path $root $rel
    if (-not (Test-Path $p)) { Warn "$rel not found - skipped"; continue }
    $c = Read-Utf8 $p
    $n1 = Count-Occurrences $c 'GoodLuckBoostHub'
    $n2 = Count-Occurrences $c 'GLBH_API_KEY'
    if ($n1 + $n2 -eq 0) { Skip "$rel (nothing to rename)"; continue }
    Backup-Once $p
    $c = $c.Replace('GoodLuckBoostHub', 'ReallySimpleSocial').Replace('GLBH_API_KEY', 'RSS_API_KEY')
    Write-Utf8 $p $c
    $script:Changed += $rel
    Ok "${rel}: $($n1 + $n2) reference(s) renamed"
}

# ===============================================================
# PART 5 - boost/models.py : USD pricing labels
# ===============================================================
Write-Host "5. boost\models.py - USD pricing labels" -ForegroundColor Cyan
$modelsPath = Join-Path $root 'boost\models.py'
if (-not (Test-Path $modelsPath)) { throw "boost\models.py not found." }
$models = Read-Utf8 $modelsPath
$rateOld = '        help_text="Provider bills in NGN. Keep this at 1.0. Only change it if you switch to a USD-billing provider.",'
$rateNew = '        help_text="ReallySimpleSocial bills in USD. Set this to the current NGN value of $1 (e.g. 1500).",'
$costOld = 'help_text="Provider cost per 1000 units (NGN)"'
$costNew = 'help_text="Provider cost per 1000 units (USD)"'
$cmtOld  = '        # Convert provider cost to NGN FIRST (exchange_rate is 1.0 for NGN-billing providers)'
$cmtNew  = '        # Convert the USD provider cost to NGN (exchange_rate = NGN value of $1)'
if ($models.Contains($rateNew) -and $models.Contains($costNew)) {
    Skip "pricing labels already updated"
} else {
    $nA = Count-Occurrences $models $rateOld
    $nB = Count-Occurrences $models $costOld
    if ($nA -ne 1 -or $nB -ne 1) {
        throw "boost\models.py pricing anchors not found (rate=$nA cost=$nB) - aborting."
    }
    Backup-Once $modelsPath
    $models = $models.Replace($rateOld, $rateNew).Replace($costOld, $costNew).Replace($cmtOld, $cmtNew)
    Write-Utf8 $modelsPath $models
    $script:Changed += 'boost\models.py'
    Ok "exchange_rate + rate help texts now USD-based"
}

# ===============================================================
# PART 6 - boost/migrations/0007 : label migration
# ===============================================================
Write-Host "6. boost\migrations - 0007 label migration" -ForegroundColor Cyan
$migDir = Join-Path $root 'boost\migrations'
$migPath = Join-Path $migDir '0007_alter_boostsettings_exchange_rate_and_more.py'
$has0006 = Test-Path (Join-Path $migDir '0006_alter_boostorder_provider_cost_and_more.py')
if (Test-Path $migPath) {
    Skip "migration 0007 already exists"
} elseif (-not $has0006) {
    Warn "boost\migrations\0006_alter_boostorder_provider_cost_and_more.py not found."
    Warn "Run 'python manage.py makemigrations boost' yourself, then commit the new file."
} else {
    Write-Utf8 $migPath (Decode $B64_MIGRATION)
    $script:Changed += 'boost\migrations\0007_alter_boostsettings_exchange_rate_and_more.py'
    Ok "migration 0007 written"
}

# ===============================================================
# PART 7 - .env.example : document RSS_API_KEY
# ===============================================================
Write-Host "7. .env.example - RSS_API_KEY" -ForegroundColor Cyan
$envPath = Join-Path $root '.env.example'
if (-not (Test-Path $envPath)) {
    Warn ".env.example not found - skipped"
} else {
    $env = Read-Utf8 $envPath
    if ($env.Contains('RSS_API_KEY')) {
        Skip ".env.example already documents RSS_API_KEY"
    } else {
        $anchor = 'INSTANTNUMS_BASE_URL=https://instantnums.com/v1'
        if ((Count-Occurrences $env $anchor) -ne 1) {
            Warn ".env.example anchor not found - add RSS_API_KEY manually"
        } else {
            Backup-Once $envPath
            $block = $anchor + "`n`n# ReallySimpleSocial (boosting provider)`nRSS_API_KEY=your-reallysimplesocial-api-key-here"
            $env = $env.Replace($anchor, $block)
            Write-Utf8 $envPath $env
            $script:Changed += '.env.example'
            Ok ".env.example updated"
        }
    }
}

# ===============================================================
# Summary + git
# ===============================================================
Write-Host ""
Write-Host "======================================================" -ForegroundColor Magenta
Write-Host "   SUMMARY" -ForegroundColor Magenta
Write-Host "======================================================" -ForegroundColor Magenta
if ($script:Changed.Count -gt 0) {
    Write-Host "Changed files:" -ForegroundColor Cyan
    foreach ($f in $script:Changed) { Write-Host "  - $f" }
} else {
    Write-Host "No files needed changes (everything already applied)." -ForegroundColor DarkGray
}
foreach ($wmsg in $script:Warnings) { Write-Host "  WARNING: $wmsg" -ForegroundColor Yellow }

if ($script:Changed.Count -gt 0) {
    Write-Host ""
    Write-Host "Committing and pushing..." -ForegroundColor Cyan
    try {
        git add -A
        git commit -m "Switch boost provider from GoodLuckBoostHub to ReallySimpleSocial"
        git push
        Ok "pushed to git"
    } catch {
        Warn "git commit/push failed - run these yourself:"
        Write-Host "  git add -A" -ForegroundColor Yellow
        Write-Host "  git commit -m ""Switch boost provider to ReallySimpleSocial""" -ForegroundColor Yellow
        Write-Host "  git push" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "NEXT STEPS (in order)" -ForegroundColor Magenta
Write-Host "  1. Add your ReallySimpleSocial API key:" -ForegroundColor White
Write-Host "       - local .env:        RSS_API_KEY=your-key-here" -ForegroundColor White
Write-Host "       - Render dashboard:  Environment -> RSS_API_KEY=your-key-here" -ForegroundColor White
Write-Host "  2. Run migrations:" -ForegroundColor White
Write-Host "       python manage.py migrate        (locally, and in Render Shell)" -ForegroundColor White
Write-Host "  3. In the admin -> Boost -> Boost Settings:" -ForegroundColor White
Write-Host "       set Exchange rate = current NGN value of `$1 (RSS bills in USD)." -ForegroundColor White
Write-Host "  4. Import the catalog:" -ForegroundColor White
Write-Host "       python manage.py sync_boost     (or admin -> Boost services -> Sync action)" -ForegroundColor White
Write-Host "     You will see every RSS service with its service ID, category," -ForegroundColor White
Write-Host "     USD rate and min/max - same style as the SMS service list." -ForegroundColor White
Write-Host "  NOTE: any boost orders still open with the old provider stop" -ForegroundColor Yellow
Write-Host "  auto-syncing after this switch - complete/cancel them in the admin." -ForegroundColor Yellow
Write-Host ""
