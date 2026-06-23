#!/bin/bash
# stage9_sphere_only.sh - run ONLY the sphere theta030 case with STL mask.
# Uses P100 #2 (device 2). Foreground (blocks until done).
export PATH=/usr/local/cuda-12.6/bin:/usr/bin:/bin:/usr/local/bin
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES=2
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh

RUNROOT=/home/yuan/data_sda/RUNS/runs/stage9
BIN=$RUNROOT/src/TCLB_stage9_analytic_wetting_20260614/CLB/d3q27_pf_velocity_q27_geometric/main
DIR=$RUNROOT/gate_sphere_theta030_stl

rm -rf "$DIR"
mkdir -p "$DIR/output"

# generate the sphere STL
python3 /home/yuan/gen_sphere_stl.py 40 40 48 24 "$DIR/solid_sphere.stl"
echo "=== STL generated ==="
head -3 "$DIR/solid_sphere.stl"

cat > "$DIR/case.xml" <<'XML'
<?xml version="1.0"?>
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
    <Param name="radAngle" value="30d"/>
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

echo "=== running sphere_theta030 (with STL) on device 2 ==="
cd "$DIR"
timeout 600 "$BIN" case.xml > run.log 2>&1
rc=$?
echo "rc=$rc"
echo "=== NaN count ==="
grep -c NaN run.log
echo "=== duration ==="
grep "Total duration" run.log | tail -1
echo "=== VTK files ==="
ls -la output/ | head
echo "=== last 10 log lines ==="
tail -10 run.log
