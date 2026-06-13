#!/bin/bash
# stage9_gate_smoke.sh - run the gate smoke cases on two P100s.
# P100 #1 (device 1): plane theta030, plane theta090, plane theta150
# P100 #2 (device 2): sphere theta030 (the case that was failing in stage5-8)
# All runs are 1000-step smokes. Status: exploratory_not_validation.
export PATH=/usr/local/cuda-12.6/bin:/usr/bin:/bin:/usr/local/bin
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh

RUNROOT=/home/yuan/data_sda/RUNS/runs/stage9
BIN=$RUNROOT/src/TCLB_stage9_analytic_wetting_20260614/CLB/d3q27_pf_velocity_q27_geometric/main
GATE=$RUNROOT/gate_smoke_20260614
mkdir -p "$GATE"

# Record binary provenance
{
  echo "binary_sha256: $(sha256sum "$BIN" | cut -d' ' -f1)"
  echo "binary_path: $BIN"
  echo "options: $(cat "$RUNROOT/src/TCLB_stage9_analytic_wetting_20260614/CLB/d3q27_pf_velocity_q27_geometric/options.R" | tr '\n' ' ')"
  echo "run_date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$GATE/provenance.txt"
cat "$GATE/provenance.txt"

##############################
# helper: write a plane case
##############################
write_plane_case() {
    local dir="$1"; local theta_deg="$2"
    mkdir -p "$dir/output"
    cat > "$dir/case.xml" <<XML
<?xml version="1.0"?>
<CLBConfig version="2.0" output="output/" permissive="true">
  <Geometry nx="64" ny="48" nz="64">
    <MRT><Box/></MRT>
    <Wall mask="ALL" name="OuterDomain">
      <Box nx="1"/>
      <Box dx="-1"/>
      <Box dy="-1"/>
      <Box nz="1"/>
      <Box dz="-1"/>
    </Wall>
    <Wall mask="ALL" name="FlatLowerY">
      <Box ny="1"/>
    </Wall>
  </Geometry>
  <Model>
    <Param name="Density_h" value="1"/>
    <Param name="Density_l" value="0.001"/>
    <Param name="Viscosity_h" value="0.1"/>
    <Param name="Viscosity_l" value="0.1"/>
    <Param name="tauUpdate" value="1"/>
    <Param name="sigma" value="5e-05"/>
    <Param name="M" value="0.1"/>
    <Param name="IntWidth" value="6"/>
    <Param name="Radius" value="12.0"/>
    <Param name="CenterX" value="32"/>
    <Param name="CenterY" value="20"/>
    <Param name="CenterZ" value="32"/>
    <Param name="BubbleType" value="1.0"/>
    <Param name="radAngle" value="90d"/>
    <Param name="radAngle" value="90d" zone="OuterDomain"/>
    <Param name="radAngle" value="${theta_deg}d" zone="FlatLowerY"/>
    <Param name="AnalyticWetting" value="1"/>
    <Param name="AnalyticSolidType" value="1"/>
    <Param name="AnalyticSolidAxis" value="1"/>
    <Param name="AnalyticSolidPlaneOffset" value="0.0"/>
    <Param name="minGradient" value="1e-08"/>
  </Model>
  <VTK what="PhaseField,Rho,BOUNDARY,WallGhost,WallH,AnalyticWallNormal,AnalyticFlag"/>
  <Solve Iterations="1000">
    <VTK Iterations="1000" what="PhaseField,Rho,BOUNDARY,WallGhost,WallH,AnalyticWallNormal,AnalyticFlag"/>
    <Log Iterations="100"/>
    <Failcheck Iterations="100"/>
  </Solve>
</CLBConfig>
XML
}

##############################
# helper: write a sphere case (WITH STL solid mask)
##############################
write_sphere_case() {
    local dir="$1"; local theta_deg="$2"
    mkdir -p "$dir/output"
    # generate the sphere STL: center (40,40,48), radius 24
    python3 /home/yuan/gen_sphere_stl.py 40 40 48 24 "$dir/solid_sphere.stl"
    cat > "$dir/case.xml" <<XML
<?xml version="1.0"?>
<!-- Stage9 sphere theta=${theta_deg}. Solid sphere via STL: center (40,40,48),
     R=24. Analytic geometry declared via Model params must MATCH the STL.
     A droplet (R=12) starts above the sphere apex (z=80). -->
<CLBConfig version="2.0" output="output/" permissive="true">
  <Geometry nx="80" ny="80" nz="120">
    <MRT><Box/></MRT>
    <Wall mask="ALL" name="OuterDomain">
      <Box nx="1"/>
      <Box dx="-1"/>
      <Box dy="-1"/>
      <Box nz="1"/>
      <Box dz="-1"/>
    </Wall>
    <Wall mask="ALL" name="AnalyticSphere">
      <STL file="solid_sphere.stl" scale="1" side="out"/>
    </Wall>
  </Geometry>
  <Model>
    <Param name="Density_h" value="1"/>
    <Param name="Density_l" value="0.001"/>
    <Param name="Viscosity_h" value="0.1"/>
    <Param name="Viscosity_l" value="0.1"/>
    <Param name="tauUpdate" value="1"/>
    <Param name="sigma" value="5e-05"/>
    <Param name="M" value="0.1"/>
    <Param name="IntWidth" value="6"/>
    <Param name="Radius" value="12.0"/>
    <Param name="CenterX" value="40"/>
    <Param name="CenterY" value="40"/>
    <Param name="CenterZ" value="80"/>
    <Param name="BubbleType" value="1.0"/>
    <Param name="radAngle" value="90d"/>
    <Param name="radAngle" value="90d" zone="OuterDomain"/>
    <Param name="AnalyticWetting" value="1"/>
    <Param name="AnalyticSolidType" value="3"/>
    <Param name="AnalyticSolidCenterX" value="40"/>
    <Param name="AnalyticSolidCenterY" value="40"/>
    <Param name="AnalyticSolidCenterZ" value="48"/>
    <Param name="AnalyticSolidRadius" value="24"/>
    <Param name="radAngle" value="${theta_deg}d"/>
    <Param name="minGradient" value="1e-08"/>
  </Model>
  <VTK what="PhaseField,Rho,BOUNDARY,WallGhost,WallH,AnalyticWallNormal,AnalyticFlag"/>
  <Solve Iterations="1000">
    <VTK Iterations="1000" what="PhaseField,Rho,BOUNDARY,WallGhost,WallH,AnalyticWallNormal,AnalyticFlag"/>
    <Log Iterations="100"/>
    <Failcheck Iterations="100"/>
  </Solve>
</CLBConfig>
XML
}

# Write all cases
write_plane_case "$GATE/plane_theta030" 30
write_plane_case "$GATE/plane_theta090" 90
write_plane_case "$GATE/plane_theta150" 150
write_sphere_case "$GATE/sphere_theta030" 30

echo "=== cases written ==="
ls "$GATE/"

##############################
# run on P100 #1 (device 1): plane cases, sequential
##############################
run_plane() {
    export CUDA_DEVICE_ORDER=PCI_BUS_ID
    export CUDA_VISIBLE_DEVICES=1
    for case in plane_theta030 plane_theta090 plane_theta150; do
        local dir="$GATE/$case"
        echo "=== running $case on P100 #1 (device 1) ==="
        ( cd "$dir" && timeout 600 "$BIN" case.xml > run.log 2>&1 )
        local rc=$?
        local nan_count=$(grep -c NaN "$dir/run.log" 2>/dev/null || echo 0)
        local dur=$(grep "Total duration" "$dir/run.log" 2>/dev/null | tail -1)
        echo "  $case: rc=$rc, NaN_lines=$nan_count, $dur"
    done
}

##############################
# run on P100 #2 (device 2): sphere case
##############################
run_sphere() {
    export CUDA_DEVICE_ORDER=PCI_BUS_ID
    export CUDA_VISIBLE_DEVICES=2
    local dir="$GATE/sphere_theta030"
    echo "=== running sphere_theta030 on P100 #2 (device 2) ==="
    ( cd "$dir" && timeout 600 "$BIN" case.xml > run.log 2>&1 )
    local rc=$?
    local nan_count=$(grep -c NaN "$dir/run.log" 2>/dev/null || echo 0)
    local dur=$(grep "Total duration" "$dir/run.log" 2>/dev/null | tail -1)
    echo "  sphere_theta030: rc=$rc, NaN_lines=$nan_count, $dur"
}

# Run both lanes in parallel
run_plane &
PID_PLANE=$!
run_sphere &
PID_SPHERE=$!

wait $PID_PLANE
wait $PID_SPHERE

echo "=== all gate smokes complete ==="
echo "=== summary ==="
for case in plane_theta030 plane_theta090 plane_theta150 sphere_theta030; do
    dir="$GATE/$case"
    nan_count=$(grep -c NaN "$dir/run.log" 2>/dev/null || echo 0)
    dur=$(grep "Total duration" "$dir/run.log" 2>/dev/null | tail -1)
    vti_count=$(find "$dir/output" -name "*.vti" 2>/dev/null | wc -l)
    echo "  $case: NaN_lines=$nan_count, vti_files=$vti_count, $dur"
done
