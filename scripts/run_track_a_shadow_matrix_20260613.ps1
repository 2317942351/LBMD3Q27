param(
    [ValidateSet("plane", "cylinder", "sphere", "all")]
    [string]$CaseGroup = "all",
    [string]$Cases = "",
    [switch]$DryRun,
    [switch]$Execute,
    [string]$GpuId = "",
    [string]$TclbBinary = "",
    [string]$RuntimeRoot = "runtime_outputs/track_a_usable_angle_ladder_20260613",
    [string]$XmlOutputRoot = ""
)

$ErrorActionPreference = "Stop"

if (-not $Execute) {
    $DryRun = $true
}

Write-Host "Track A usable-angle validation ladder"
Write-Host "Status: runtime_sanity / exploratory_not_validation"
Write-Host "This is not PRE reproduction, not validation, and not a production fix."
Write-Host "Stage8OperatorMode=1 shadow-only cases are prepared; no sphere11 write is included."

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$caseRoot = Join-Path $repoRoot "cases/track_a_usable_angle_ladder_20260613"
$manifestPath = Join-Path $caseRoot "manifest.json"
if (-not (Test-Path -LiteralPath $manifestPath)) {
    throw "Missing manifest: $manifestPath"
}

$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$caseFilter = @{}
if (-not [string]::IsNullOrWhiteSpace($Cases)) {
    foreach ($raw in ($Cases -split ",")) {
        $token = $raw.Trim()
        if ($token.Length -eq 0) {
            continue
        }
        $caseFilter[$token.ToLowerInvariant()] = $true
    }
}

function Test-CaseSelected {
    param(
        [string]$Group,
        [int]$Angle,
        [string]$CaseId
    )
    if ($caseFilter.Count -eq 0) {
        return $true
    }
    $angle3 = "{0:D3}" -f $Angle
    $keys = @(
        $CaseId.ToLowerInvariant(),
        ("{0}{1}" -f $Group, $Angle).ToLowerInvariant(),
        ("{0}{1}" -f $Group, $angle3).ToLowerInvariant(),
        ("{0}_theta{1}" -f $Group, $angle3).ToLowerInvariant(),
        ("theta{0}" -f $angle3).ToLowerInvariant()
    )
    foreach ($key in $keys) {
        if ($caseFilter.ContainsKey($key)) {
            return $true
        }
    }
    return $false
}

function Get-CapSphereRadius {
    param(
        [double]$VolumeRadius,
        [double]$ThetaDeg
    )
    $theta = [Math]::PI * $ThetaDeg / 180.0
    $denom = [Math]::Pow(1.0 - [Math]::Cos($theta), 2.0) * (2.0 + [Math]::Cos($theta))
    if ($denom -le 0.0) {
        throw "Invalid cap theta: $ThetaDeg"
    }
    return $VolumeRadius * [Math]::Pow(4.0 / $denom, 1.0 / 3.0)
}

function Format-Invariant {
    param([double]$Value)
    return $Value.ToString("G17", [Globalization.CultureInfo]::InvariantCulture)
}

function Get-XmlCaseOutputDir {
    param(
        [string]$LocalCaseDir,
        [string]$CaseId
    )
    if ([string]::IsNullOrWhiteSpace($XmlOutputRoot)) {
        return $LocalCaseDir.Replace("\", "/")
    }
    return ($XmlOutputRoot.TrimEnd("/", "\") + "/" + $CaseId).Replace("\", "/")
}

$groups = @()
if ($CaseGroup -eq "all") {
    $groups = @("plane", "cylinder", "sphere")
} else {
    $groups = @($CaseGroup)
}

$commands = @()
foreach ($group in $groups) {
    $groupInfo = $manifest.case_groups.$group
    $templatePath = Join-Path $caseRoot $groupInfo.template
    if (-not (Test-Path -LiteralPath $templatePath)) {
        throw "Missing template: $templatePath"
    }
    $template = Get-Content -LiteralPath $templatePath -Raw
    foreach ($angle in $groupInfo.angles_deg) {
        $angleInt = [int]$angle
        $caseId = ("track_a_{0}_theta{1:D3}_shadow" -f $group, $angleInt)
        if (-not (Test-CaseSelected -Group $group -Angle $angleInt -CaseId $caseId)) {
            continue
        }
        $caseDir = Join-Path $repoRoot (Join-Path $RuntimeRoot $caseId)
        $xmlPath = Join-Path $caseDir "case.xml"
        $xmlCaseDir = Get-XmlCaseOutputDir -LocalCaseDir $caseDir -CaseId $caseId
        $outputDir = ($xmlCaseDir.TrimEnd("/") + "/output").Replace("\", "/")
        $thetaRad = [Math]::PI * [double]$angleInt / 180.0
        $capRadius = Get-CapSphereRadius -VolumeRadius 24.0 -ThetaDeg ([double]$angleInt)
        $capCenterY = -1.0 * $capRadius * [Math]::Cos($thetaRad)
        $xmlText = $template.Replace("{{CASE_ID}}", $caseId).
            Replace("{{ANGLE_DEG}}", [string]$angleInt).
            Replace("{{ANGLE_RAD}}", (Format-Invariant $thetaRad)).
            Replace("{{CAP_RADIUS}}", (Format-Invariant $capRadius)).
            Replace("{{CAP_CENTER_Y}}", (Format-Invariant $capCenterY)).
            Replace("{{OUTPUT_DIR}}", $xmlCaseDir)
        $hasGeometryPlaceholder = $xmlText.Contains("Geometry placeholder")
        New-Item -ItemType Directory -Force -Path $caseDir | Out-Null
        Set-Content -LiteralPath $xmlPath -Value $xmlText -Encoding UTF8
        $cmd = if ([string]::IsNullOrWhiteSpace($TclbBinary)) {
            "TCLB_BINARY <case.xml>"
        } else {
            "`"$TclbBinary`" `"$xmlPath`""
        }
        if (-not [string]::IsNullOrWhiteSpace($GpuId)) {
            $cmd = "`$env:CUDA_DEVICE_ORDER='PCI_BUS_ID'; `$env:CUDA_VISIBLE_DEVICES='$GpuId'; $cmd"
        }
        $commands += [pscustomobject]@{
            case_id = $caseId
            group = $group
            angle_deg = $angleInt
            xml = $xmlPath
            output = $outputDir
            command = $cmd
            executable = -not $hasGeometryPlaceholder
        }
    }
}

if ($commands.Count -eq 0) {
    throw "No Track A cases selected. CaseGroup=$CaseGroup Cases=$Cases"
}

Write-Host ""
Write-Host "Prepared shadow cases:"
$commands | Format-Table case_id, group, angle_deg, xml -AutoSize
Write-Host ""
Write-Host "Commands:"
foreach ($item in $commands) {
    $execTag = if ($item.executable) { "ready-template" } else { "geometry-placeholder" }
    Write-Host ("[{0}] ({1}) {2}" -f $item.case_id, $execTag, $item.command)
}

if ($DryRun) {
    Write-Host ""
    Write-Host "DryRun active. No solver commands were executed."
    exit 0
}

$blocked = @($commands | Where-Object { -not $_.executable })
if ($blocked.Count -gt 0) {
    $blockedIds = ($blocked | ForEach-Object { $_.case_id }) -join ", "
    throw "Execution refused before launching any solver command. These cases still contain geometry placeholders: $blockedIds"
}

if ([string]::IsNullOrWhiteSpace($TclbBinary)) {
    throw "Execution requested but -TclbBinary was not provided."
}

$answer = Read-Host "Type RUN_TRACK_A_SHADOW to execute these local commands"
if ($answer -ne "RUN_TRACK_A_SHADOW") {
    Write-Host "Confirmation did not match. No solver commands were executed."
    exit 0
}

foreach ($item in $commands) {
    Write-Host ("Running {0}" -f $item.case_id)
    if (-not [string]::IsNullOrWhiteSpace($GpuId)) {
        $env:CUDA_DEVICE_ORDER = "PCI_BUS_ID"
        $env:CUDA_VISIBLE_DEVICES = $GpuId
    }
    & $TclbBinary $item.xml
    $LASTEXITCODE | Out-File -LiteralPath (Join-Path (Split-Path -Parent $item.xml) "run.returncode") -Encoding ascii
}
