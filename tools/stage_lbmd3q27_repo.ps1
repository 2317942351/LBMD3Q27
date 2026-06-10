param(
  [string]$SourceRoot = "C:\Users\yuanz\Desktop\LBMCORE5\TCLB",
  [string]$DestRoot = "C:\Users\yuanz\Desktop\LBMD3Q27"
)

$ErrorActionPreference = "Stop"

function Ensure-Dir([string]$Path) {
  New-Item -ItemType Directory -Path $Path -Force | Out-Null
}

function Copy-FileChecked([string]$RelativePath) {
  $src = Join-Path $SourceRoot $RelativePath
  $dst = Join-Path $DestRoot $RelativePath
  if (-not (Test-Path -LiteralPath $src)) {
    Write-Warning "missing: $RelativePath"
    return
  }
  Ensure-Dir (Split-Path -Parent $dst)
  Copy-Item -LiteralPath $src -Destination $dst -Force
}

function Copy-DirFiltered([string]$RelativePath, [string[]]$Include = @("*")) {
  $srcRoot = Join-Path $SourceRoot $RelativePath
  if (-not (Test-Path -LiteralPath $srcRoot)) {
    Write-Warning "missing dir: $RelativePath"
    return
  }
  Get-ChildItem -LiteralPath $srcRoot -Recurse -File -Include $Include | ForEach-Object {
    $rel = $_.FullName.Substring($SourceRoot.Length + 1)
    Copy-FileChecked $rel
  }
}

function Copy-SelectedArtifact([string]$Name) {
  $artifactRoot = Join-Path $SourceRoot "artifacts\$Name"
  if (-not (Test-Path -LiteralPath $artifactRoot)) {
    Write-Warning "missing artifact: $Name"
    return
  }
  $allowed = @(
    "*.md", "*.txt", "*.csv", "*.json", "*.xml", "*.log", "*.stderr",
    "*.stdout", "*.returncode", "*.png", "*.jpg", "*.jpeg", "*.svg"
  )
  Get-ChildItem -LiteralPath $artifactRoot -Recurse -File -Include $allowed | ForEach-Object {
    $rel = $_.FullName.Substring($SourceRoot.Length + 1)
    Copy-FileChecked $rel
  }
}

Ensure-Dir $DestRoot

foreach ($file in @("AGENTS.md", "README.md")) {
  Copy-FileChecked $file
}

$docFiles = @(
  "docs\tclb_d3q27_pf_velocity_code_compile_audit_20260610.md",
  "docs\pre2025_sphere_phi_overshoot_solution_plan_audit_20260610.md",
  "docs\wall_geom_diag_clean_lane_stage2_20260610.md",
  "docs\wall_geom_bounded_diag_stage3_20260610.md",
  "docs\wall_geom_profile_diag_stage4_20260610.md",
  "docs\wall_geom_profile_600k_extension_20260610.md",
  "docs\pre2025_sphere_theta030_profile_liftZ32_geometry_audit_20260610.md",
  "docs\pre2025_sphere_tclb_audit_and_execution_plan_20260610.md",
  "docs\pre2025_wetting_boundary_tclb_analysis_20260609.md",
  "docs\wetting_boundary_article_analysis_20260609.md",
  "docs\official_wetting_boundary_reproduction_plan_20260609.md",
  "docs\literature_driven_resolution_plan_20260610.md",
  "docs\project_audit_and_next_plan_20260610.md",
  "docs\validation_and_output_protocol.md",
  "docs\subagent_goal_operating_model.md",
  "docs\tclb_project_handoff.md",
  "docs\tclb_path_index.md",
  "docs\remote_local_file_index.md",
  "docs\experience_log.md",
  "docs\literature_case_matrix.md",
  "docs\target_physical_case_plan.md",
  "docs\implementation_backlog.md"
)
foreach ($file in $docFiles) { Copy-FileChecked $file }

$scriptFiles = @(
  "scripts\make_pre2025_sphere_tableII_cases.py",
  "scripts\tclb_pre2025_sphere_postprocess.py",
  "scripts\pre2025_sphere_wall_diag_postprocess.py",
  "scripts\pre2025_sphere_single_case_frame_gallery.py",
  "scripts\pre2025_sphere_surface_film_audit.py",
  "scripts\compare_wall_geom_diag_profile.py",
  "scripts\compare_wall_geom_diag_bounded.py",
  "scripts\compare_pre2025_sphere_profile_candidate.py",
  "scripts\wall_geom_diag_postprocess.py",
  "scripts\make_wall_geom_diag_short_cases.py",
  "scripts\audit_pre2025_sphere_phi_overshoot.py",
  "scripts\audit_pre2025_sphere_boundary_phi_context.py",
  "scripts\audit_pre2025_sphere_geometric_wall_formula.py",
  "scripts\audit_pre2025_sphere_geometric_wall_angle_sensitivity.py",
  "scripts\plot_pre2025_sphere_wall_phi_diagnostics.py",
  "scripts\plot_wall_geom_profile_evolution.py",
  "scripts\plot_wall_geom_curved_rad011_10k_evolution.py",
  "scripts\plot_wall_geom_rad011_1000_evolution.py",
  "scripts\hm570_run_pre2025_sphere_profile_600k_20260610.sh",
  "scripts\hm570_run_pre2025_sphere_profile_liftZ32_400k_20260610.sh",
  "scripts\hm570_pre2025_sphere_status.sh",
  "scripts\README.md"
)
foreach ($file in $scriptFiles) { Copy-FileChecked $file }

$caseDirs = @(
  "cases\diagnostics\wall_geom_diag_flat_curved_20260610",
  "cases\diagnostics\wall_geom_diag_flat_curved_rad011_20260610",
  "cases\diagnostics\wall_geom_diag_bounded_flat_curved_20260610",
  "cases\diagnostics\wall_geom_diag_bounded_rad011_1000_20260610",
  "cases\diagnostics\wall_geom_diag_bounded_curved_rad011_10k_20260610",
  "cases\diagnostics\wall_geom_diag_profile_flat_curved_20260610",
  "cases\diagnostics\wall_geom_diag_profile_rad011_1000_20260610",
  "cases\diagnostics\wall_geom_diag_profile_curved_rad011_10k_20260610",
  "cases\validation\pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_50k_20260610",
  "cases\validation\pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_200k_20260610",
  "cases\validation\pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_600k_20260610",
  "cases\validation\pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_liftZ32_400k_20260610",
  "cases\validation\pre2025_sphere_tableII_q27_geometric_theta030_radAngle011_M0p1_W6_200k_20260610",
  "cases\validation\static_contact_angle"
)
foreach ($dir in $caseDirs) {
  Copy-DirFiltered $dir @("*.xml", "*.json", "*.csv", "*.md")
}

Copy-DirFiltered "references\pre2025_wetting_boundary" @("*.md", "*.json", "*.csv", "*.txt")
Copy-FileChecked "references\README.md"

$artifactDirs = @(
  "wall_geom_diag_summary_20260610",
  "wall_geom_diag_flat_curved_20260610",
  "wall_geom_diag_flat_curved_rad011_20260610",
  "wall_geom_diag_bounded_summary_20260610",
  "wall_geom_diag_bounded_flat_curved_20260610",
  "wall_geom_diag_bounded_rad011_1000_20260610",
  "wall_geom_diag_bounded_curved_rad011_10k_20260610",
  "wall_geom_diag_profile_summary_20260610",
  "wall_geom_diag_profile_flat_curved_20260610",
  "wall_geom_diag_profile_rad011_1000_20260610",
  "wall_geom_diag_profile_curved_rad011_10k_20260610",
  "pre2025_sphere_theta030_profile_candidate_summary_20260610",
  "pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_50k_20260610",
  "pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_200k_20260610",
  "pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_600k_20260610",
  "pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_liftZ32_400k_20260610",
  "pre2025_sphere_theta030_profile_z24_vs_liftZ32_compare_20260610",
  "pre2025_sphere_theta030_visual_diagnostics_20260610",
  "tclb_pre2025_sphere_tableII_q27_geometric_theta030_radAngle011_param_sensitivity_200k_20260610",
  "pre2025_sphere_tableII_q27_geometric_200k_20260610"
)
foreach ($dir in $artifactDirs) { Copy-SelectedArtifact $dir }

$tmpFiles = @(
  "tmp\tclb_wall_diag_clean_lane.diff",
  "tmp\tclb_wall_bounded_diag.patch"
)
foreach ($file in $tmpFiles) { Copy-FileChecked $file }

Get-ChildItem -LiteralPath $DestRoot -Recurse -File | ForEach-Object {
  $rel = $_.FullName.Substring($DestRoot.Length + 1)
  [pscustomobject]@{
    path = $rel.Replace("\", "/")
    bytes = $_.Length
    sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
  }
} | Sort-Object path | ConvertTo-Json -Depth 4 | Set-Content -Path (Join-Path $DestRoot "reports\staged_file_manifest.local.json") -Encoding UTF8

Write-Host "staged to $DestRoot"
