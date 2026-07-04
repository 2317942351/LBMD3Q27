#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/mnt/usb1t/RUNS/runs/stage18_closure2_smoke_20260703}"
BIN="${BIN:-/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_clean_2026_q27_stage18closure2/main}"
PY="${PY:-/usr/bin/python3}"
ANALYZER="${ANALYZER:-/home/yuan/stage18_smoke_analyze.py}"
GPU="${GPU:-1}"
ITERATIONS="${ITERATIONS:-20}"
VTK_PERIOD="${VTK_PERIOD:-10}"
LOG_PERIOD="${LOG_PERIOD:-10}"
TIMEOUT="${TIMEOUT:-900}"

WHAT="PhaseField,PhaseFValid,PhaseOutOfBoundsFlag,Rho,U,P,Pstar,GradPhi,WallPhase,ForceTotal,Stage18Violation,PressureInput,ForceOverRho,ForceInsertionAudit,ForceHalfVelocity,ForceMomentumBefore,ForceMomentumAfter,ForceEquivalentInjected,MassCorrectionApplied,WallHNetMass,WallHLinkWriteCount,WallHMassBefore,WallHMassAfter,PhaseHPreSum,PhaseHRawSum,PhaseHRawMin,PhaseHRawMax,PhaseHRawNonfiniteCount,PhaseHeqSum,PhaseFphiSum,PhaseHPostSum,PhaseCorrectionDelta,PhaseMassRedistributionWeight,PhaseGlobalCorrectionApplied,PhasePopulationRepairApplied,PhaseFphiFirstMoment,BOUNDARY"

export PATH=/usr/local/cuda-12.6/bin:/usr/bin:/bin:/usr/local/bin
export LD_LIBRARY_PATH=/usr/local/cuda-12.6/lib64:${LD_LIBRARY_PATH:-}
export CUDA_DEVICE_ORDER=PCI_BUS_ID

mkdir -p "${ROOT}"

write_xml() {
  local case_dir="$1"
  local geometry="$2"
  local wetting_model="$3"
  local wetting_write_mode="$4"
  local radius="$5"
  local center_y="$6"
  local zone_params="${7:-}"
  mkdir -p "${case_dir}"
  cat > "${case_dir}/case.xml" <<XML
<?xml version="1.0"?>
<CLBConfig version="2.0" output="output/" permissive="true">
  <Geometry nx="48" ny="40" nz="48">
    <MRT><Box/></MRT>
    ${geometry}
  </Geometry>
  <Model>
    <Param name="Density_h" value="1.0"/>
    <Param name="Density_l" value="0.005"/>
    <Param name="Viscosity_h" value="0.1"/>
    <Param name="Viscosity_l" value="0.1"/>
    <Param name="tauUpdate" value="1"/>
    <Param name="sigma" value="5e-05"/>
    <Param name="M" value="0.3"/>
    <Param name="IntWidth" value="3.0"/>
    <Param name="BubbleType" value="1.0"/>
    <Param name="Radius" value="${radius}"/>
    <Param name="CenterX" value="24.0"/>
    <Param name="CenterY" value="${center_y}"/>
    <Param name="CenterZ" value="24.0"/>
    <Param name="VelocityX" value="0.0"/>
    <Param name="VelocityY" value="0.0"/>
    <Param name="VelocityZ" value="0.0"/>
    <Param name="Pressure" value="0.0"/>
    <Param name="GravitationX" value="0.0"/>
    <Param name="GravitationY" value="0.0"/>
    <Param name="GravitationZ" value="0.0"/>
    <Param name="BuoyancyX" value="0.0"/>
    <Param name="BuoyancyY" value="0.0"/>
    <Param name="BuoyancyZ" value="0.0"/>
    <Param name="PhaseEquationMode" value="2"/>
    <Param name="PhaseBoundednessMode" value="1"/>
    <Param name="PhaseGlobalCorrection" value="0.0"/>
    <Param name="GeometryMode" value="${wetting_model}"/>
    <Param name="SolidPlaneNormalX" value="0.0"/>
    <Param name="SolidPlaneNormalY" value="1.0"/>
    <Param name="SolidPlaneNormalZ" value="0.0"/>
    <Param name="SolidPlaneOffset" value="0.0"/>
    <Param name="WettingModel" value="${wetting_model}"/>
    <Param name="WettingWriteMode" value="${wetting_write_mode}"/>
    <Param name="radAngle" value="90d"/>
    ${zone_params}
    <Param name="GradPhiMode" value="1"/>
    <Param name="LaplaceMode" value="1"/>
    <Param name="MuWallFluxMode" value="1"/>
    <Param name="PressureClosureMode" value="1"/>
    <Param name="PressureReferenceValue" value="0.0"/>
    <Param name="ForceClosureMode" value="1"/>
    <Param name="FmuStressMode" value="0"/>
    <Param name="ForceInsertionMode" value="0"/>
    <Param name="MomentumMRTMode" value="1"/>
    <Param name="MRTBulkOmega" value="1.0"/>
    <Param name="MRTMinOmega" value="0.2"/>
    <Param name="MRTMaxOmega" value="1.98"/>
    <Param name="RhoFloor" value="0.005"/>
    <Param name="minGradient" value="1e-08"/>
    <Param name="DiagnosticsLevel" value="1"/>
  </Model>
  <VTK Iterations="${VTK_PERIOD}" what="${WHAT}"/>
  <Log Iterations="${LOG_PERIOD}"/>
  <Failcheck Iterations="${LOG_PERIOD}"/>
  <Solve Iterations="${ITERATIONS}"/>
</CLBConfig>
XML
}

write_xml "${ROOT}/bulk_20" "" "0" "0" "10.0" "20.0" ""
write_xml "${ROOT}/flat90_shadow_20" '<Wall mask="ALL" name="FlatLowerY"><Box dx="1" nx="46" ny="1" dz="1" nz="46"/></Wall>' "1" "0" "10.0" "0.0" '<Param name="radAngle" value="90d" zone="FlatLowerY"/>'
write_xml "${ROOT}/flat90_perlink_20" '<Wall mask="ALL" name="FlatLowerY"><Box dx="1" nx="46" ny="1" dz="1" nz="46"/></Wall>' "1" "2" "10.0" "0.0" '<Param name="radAngle" value="90d" zone="FlatLowerY"/>'

{
  echo "stage=stage18_closure2_smoke"
  echo "root=${ROOT}"
  echo "binary=${BIN}"
  echo "gpu=${GPU}"
  echo "iterations=${ITERATIONS}"
  echo "vtk_period=${VTK_PERIOD}"
  echo "claim_limit=smoke_only_not_contact_angle_validation"
  date -Is
} | tee "${ROOT}/run_config.txt"

sha256sum "${BIN}" | tee "${ROOT}/binary_sha256.txt"
nvidia-smi -L | tee "${ROOT}/nvidia_smi_L.txt"
df -h /mnt/usb1t /home 2>&1 | tee "${ROOT}/df_before.txt"

overall_rc=0
for case in bulk_20 flat90_shadow_20 flat90_perlink_20; do
  (
    cd "${ROOT}/${case}"
    export CUDA_VISIBLE_DEVICES="${GPU}"
    set +e
    timeout "${TIMEOUT}" "${BIN}" case.xml > run.log 2> run.stderr
    rc=$?
    set -e
    echo "RC=${rc}" > run.status
    exit "${rc}"
  ) || overall_rc=3
done

set +e
"${PY}" "${ANALYZER}" "${ROOT}" \
  --out-json "${ROOT}/stage18_smoke_analysis.json" \
  --out-csv "${ROOT}/stage18_smoke_frames.csv" \
  > "${ROOT}/stage18_smoke_analyze_stdout.json" \
  2> "${ROOT}/stage18_smoke_analyze_stderr.log"
analysis_rc=$?
set -e

find "${ROOT}" -maxdepth 5 \( -name 'run.log' -o -name 'run.stderr' -o -name 'run.status' -o -name 'case.xml' -o -name '*.json' -o -name '*.csv' -o -name '*.txt' -o -name '*.log' \) -print > "${ROOT}/light_artifact_manifest.txt"
find "${ROOT}" \( -path '*/output/*.vti' -o -path '*/output/*.pvti' \) -type f | wc -l | awk '{print "VTK_COUNT="$1}' > "${ROOT}/vti_count.txt"
df -h /mnt/usb1t /home 2>&1 | tee "${ROOT}/df_after.txt"

if [[ "${analysis_rc}" -ne 0 ]]; then
  overall_rc=3
fi

{
  echo "OVERALL_RC=${overall_rc}"
  echo "ANALYSIS_RC=${analysis_rc}"
  if [[ "${overall_rc}" -eq 0 ]]; then
    echo "VERDICT=stage18_closure2_smoke_pass"
  else
    echo "VERDICT=stage18_closure2_smoke_fail_or_partial"
  fi
  date -Is
} | tee "${ROOT}/stage18_closure2_smoke.status"

exit "${overall_rc}"
