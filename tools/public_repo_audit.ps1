param(
  [string]$RepoRoot = "C:\Users\yuanz\Desktop\LBMD3Q27"
)

$ErrorActionPreference = "Stop"

$forbiddenPatterns = @(
  "*.vti", "*.pvti", "*.pri",
  "*.exe", "*.dll", "*.so", "*.o", "*.obj", "*.lib", "*.a",
  "*.tar", "*.tgz", "*.gz", "*.zip", "*.7z", "*.rar",
  "*.pem", "*.key", ".env"
)

$forbidden = foreach ($pat in $forbiddenPatterns) {
  Get-ChildItem -Path $RepoRoot -Recurse -File -Filter $pat -ErrorAction SilentlyContinue
}

$large = Get-ChildItem -Path $RepoRoot -Recurse -File |
  Where-Object { $_.Length -gt 100MB }

$secretRegex = "(ghp_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+|glpat-[A-Za-z0-9_\-]+|BEGIN (RSA |OPENSSH |DSA |EC )?PRIVATE KEY|MINERU_API_TOKEN|access_token|api[_-]?token|password\s*=)"
$generatedReports = @(
  (Join-Path $RepoRoot "reports\file_manifest.json"),
  (Join-Path $RepoRoot "reports\public_repo_audit_summary.json")
)
function Is-GeneratedReport([string]$Path) {
  foreach ($report in $generatedReports) {
    if ($Path -eq $report) { return $true }
  }
  return $false
}

$secretHits = @()
Get-ChildItem -Path $RepoRoot -Recurse -File |
  Where-Object {
    $_.Length -lt 20MB -and
    $_.FullName -ne (Join-Path $RepoRoot "tools\public_repo_audit.ps1")
  } |
  ForEach-Object {
    $matches = Select-String -LiteralPath $_.FullName -Pattern $secretRegex -AllMatches -ErrorAction SilentlyContinue
    foreach ($m in $matches) {
      $secretHits += [pscustomobject]@{
        path = $_.FullName.Substring($RepoRoot.Length + 1)
        line = $m.LineNumber
      }
    }
  }

$files = Get-ChildItem -Path $RepoRoot -Recurse -File |
  Where-Object { -not (Is-GeneratedReport $_.FullName) } |
  ForEach-Object {
  [pscustomobject]@{
    path = $_.FullName.Substring($RepoRoot.Length + 1).Replace("\", "/")
    bytes = $_.Length
    sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
  }
}

$reportDir = Join-Path $RepoRoot "reports"
New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
$files | Sort-Object path | ConvertTo-Json -Depth 4 |
  Set-Content -Path (Join-Path $reportDir "file_manifest.json") -Encoding UTF8

$summary = [pscustomobject]@{
  file_count = @($files).Count
  total_bytes = (@($files) | Measure-Object bytes -Sum).Sum
  forbidden_count = @($forbidden).Count
  large_over_100mb_count = @($large).Count
  secret_hit_count = @($secretHits).Count
  forbidden = @($forbidden | ForEach-Object { $_.FullName.Substring($RepoRoot.Length + 1) })
  large_over_100mb = @($large | ForEach-Object { $_.FullName.Substring($RepoRoot.Length + 1) })
  secret_hits = $secretHits
}

$summary | ConvertTo-Json -Depth 5 |
  Set-Content -Path (Join-Path $reportDir "public_repo_audit_summary.json") -Encoding UTF8

if ($summary.forbidden_count -gt 0 -or $summary.large_over_100mb_count -gt 0 -or $summary.secret_hit_count -gt 0) {
  $summary | ConvertTo-Json -Depth 5
  exit 2
}

$summary | ConvertTo-Json -Depth 5
