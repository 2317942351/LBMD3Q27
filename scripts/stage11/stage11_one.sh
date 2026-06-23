#!/bin/bash
# stage11_one.sh - run a single Stage11 case by templating from s1_W6_R24.
# Usage: bash stage11_one.sh <name> <W> <R> <nx> <ny> <nz> <cx> <cy> <cz> <sweep_tag>
export PATH=/usr/local/cuda-12.6/bin:/usr/bin:/bin:/usr/local/bin
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES=1
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh

NAME="$1"; W="$2"; R="$3"; NX="$4"; NY="$5"; NZ="$6"; CX="$7"; CY="$8"; CZ="$9"; SWEEP="${10}"
BIN=/home/yuan/data_sda/RUNS/runs/stage9/src/TCLB_stage9_analytic_wetting_20260614/CLB/d3q27_pf_velocity_q27_geometric/main
DIR=/home/yuan/data_sda/RUNS/runs/stage11/$NAME

rm -rf "$DIR"; mkdir -p "$DIR/output"
cat > "$DIR/case.xml" <<XML
<?xml version="1.0"?>
<CLBConfig version="2.0" output="output/" permissive="true">
  <Geometry nx="${NX}" ny="${NY}" nz="${NZ}">
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
    <Param name="CenterX" value="${CX}"/>
    <Param name="CenterY" value="${CY}"/>
    <Param name="CenterZ" value="${CZ}"/>
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

echo "=== $NAME : W=$W R=$R grid=${NX}x${NY}x${NZ} R/W=$(python3 -c "print($R/$W)") ==="
cd "$DIR"
timeout 540 "$BIN" case.xml > run.log 2>&1
rc=$?
nan=$(grep -c NaN run.log)
echo "rc=$rc nan=$nan"
if [ "$rc" -eq 0 ] && [ "$nan" -eq 0 ] && [ -f output/case_VTK_P00_00100000.vti ]; then
    angle=$(python3 /home/yuan/stage9_contact_angle.py output/case_VTK_P00_00100000.vti plane 1 "$CX" "$CY" "$CZ" 2>&1 | grep "left contact angle" | grep -oE '[0-9]+\.[0-9]+' | head -1)
    echo "RESULT $NAME $W $R $(python3 -c "print($R/$W)") $angle"
else
    echo "RESULT $NAME $W $R $(python3 -c "print($R/$W)") FAIL"
fi
