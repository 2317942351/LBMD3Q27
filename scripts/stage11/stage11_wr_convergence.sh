#!/bin/bash
# stage11_wr_convergence.sh - W/R convergence audit for Stage11.
# Plane wall, theta=30, stage9 binary (Briant formula). Two sweeps, serial.
# Single GPU (device 1). No code change.
#
# Sweep 1: fixed R=24, vary W in {6,4,3,2}. W=2 needs dx=0.5 (2x resolution).
# Sweep 2: fixed W=6, vary R in {12,24,48}. Grid scales with R.
#
# Output: per-case measured contact angle + JSON summary for the W/R collapse plot.
set -u
export PATH=/usr/local/cuda-12.6/bin:/usr/bin:/bin:/usr/local/bin
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES=1
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh

BIN=/home/yuan/data_sda/RUNS/runs/stage9/src/TCLB_stage9_analytic_wetting_20260614/CLB/d3q27_pf_velocity_q27_geometric/main
RUNROOT=/home/yuan/data_sda/RUNS/runs/stage11
mkdir -p "$RUNROOT"

run_case() {
    local name="$1"; local nx="$2"; local ny="$3"; local nz="$4"
    local W="$5"; local R="$6"; local cx="$7"; local cy="$8"; local cz="$9"
    local dir="$RUNROOT/$name"
    rm -rf "$dir"; mkdir -p "$dir/output"
    cat > "$dir/case.xml" <<XML
<?xml version="1.0"?>
<CLBConfig version="2.0" output="output/" permissive="true">
  <Geometry nx="${nx}" ny="${ny}" nz="${nz}">
    <MRT><Box/></MRT>
    <Wall mask="ALL" name="OuterDomain">
      <Box nx="1"/><Box dx="-1"/><Box dy="-1"/><Box nz="1"/><Box dz="-1"/>
    </Wall>
    <Wall mask="ALL" name="FlatLowerY"><Box ny="1"/></Wall>
  </Geometry>
  <Model>
    <Param name="Density_h" value="1"/>
    <Param name="Density_l" value="0.001"/>
    <Param name="Viscosity_h" value="0.1"/>
    <Param name="Viscosity_l" value="0.1"/>
    <Param name="tauUpdate" value="1"/>
    <Param name="sigma" value="5e-05"/>
    <Param name="M" value="0.1"/>
    <Param name="IntWidth" value="${W}"/>
    <Param name="Radius" value="${R}"/>
    <Param name="CenterX" value="${cx}"/>
    <Param name="CenterY" value="${cy}"/>
    <Param name="CenterZ" value="${cz}"/>
    <Param name="BubbleType" value="1.0"/>
    <Param name="radAngle" value="90d"/>
    <Param name="radAngle" value="90d" zone="OuterDomain"/>
    <Param name="radAngle" value="30d" zone="FlatLowerY"/>
    <Param name="AnalyticWetting" value="1"/>
    <Param name="AnalyticSolidType" value="1"/>
    <Param name="AnalyticSolidAxis" value="1"/>
    <Param name="AnalyticSolidPlaneOffset" value="0.0"/>
    <Param name="minGradient" value="1e-08"/>
  </Model>
  <VTK what="PhaseField,Rho,U,P,BOUNDARY,WallGhost,WallH,AnalyticWallNormal,AnalyticFlag"/>
  <Solve Iterations="100000">
    <VTK Iterations="100000" what="PhaseField,Rho,U,P,BOUNDARY,WallGhost,WallH,AnalyticWallNormal,AnalyticFlag"/>
    <Failcheck Iterations="5000"/>
  </Solve>
</CLBConfig>
XML
    echo "=== $name : W=$W R=$R grid=${nx}x${ny}x${nz} R/W=$(python3 -c "print($R/$W)") ==="
    ( cd "$dir" && "$BIN" case.xml > run.log 2>&1 )
    local rc=$?
    local nan=$(grep -c NaN "$dir/run.log" 2>/dev/null)
    echo "  rc=$rc NaN=$nan"
    if [ "$rc" -eq 0 ] && [ "$nan" -eq 0 ] && [ -f "$dir/output/case_VTK_P00_00100000.vti" ]; then
        local angle=$(python3 /home/yuan/stage9_contact_angle.py "$dir/output/case_VTK_P00_00100000.vti" plane 1 "$cx" "$cy" "$cz" 2>&1 | grep "left contact angle" | head -1 | grep -oE '[0-9]+\.[0-9]+')
        echo "  measured_angle = $angle deg"
        echo "$name $W $R $(python3 -c "print($R/$W)") $angle $rc $nan" >> "$RUNROOT/results.txt"
    else
        echo "  FAILED (no angle)"
        echo "$name $W $R $(python3 -c "print($R/$W)") FAIL $rc $nan" >> "$RUNROOT/results.txt"
    fi
}

# header
echo "name W R R_over_W measured_angle rc nan" > "$RUNROOT/results.txt"

echo "########## SWEEP 1: fixed R=24, vary W ##########"
# W=6 baseline (known 35.65); grid 96x64x96
run_case "s1_W6_R24"  96  64  96  6  24  48 24 48
# W=4
run_case "s1_W4_R24"  96  64  96  4  24  48 24 48
# W=3
run_case "s1_W3_R24"  96  64  96  3  24  48 24 48
# W=2 with dx=0.5 -> double grid; R=24 stays, droplet center doubles, domain doubles
run_case "s1_W2_R24" 192 128 192  2  24  96 48 96

echo ""
echo "########## SWEEP 2: fixed W=6, vary R ##########"
# R=12, grid 64x48x64
run_case "s2_W6_R12"  64  48  64  6  12  32 16 32
# R=24 baseline (same as s1_W6_R24, but rerun for cleanliness in this lane)
run_case "s2_W6_R24"  96  64  96  6  24  48 24 48
# R=48, grid 192x128x192
run_case "s2_W6_R48" 192 128 192  6  48  96 48 96

echo ""
echo "########## STAGE11 RESULTS ##########"
cat "$RUNROOT/results.txt"
echo ""
echo "########## W/R COLLAPSE CHECK ##########"
python3 /home/yuan/stage11_analyze.py "$RUNROOT/results.txt"
