#!/bin/bash
# Run short static Stage12 smoke cases for a cylinder wall or a flat lower wall.
# Usage:
#   bash stage12_static_run.sh <name> cylinder <theta> <iterations>
#   bash stage12_static_run.sh <name> wall     <theta> <iterations>
set -euo pipefail

export PATH=/usr/local/cuda-12.6/bin:/usr/bin:/bin:/usr/local/bin
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-1}"
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh

NAME="$1"
GEOM="$2"
THETA="$3"
ITERATIONS="$4"

BIN=/home/yuan/data_sda/RUNS/runs/stage9/src/TCLB_stage9_analytic_wetting_20260614/CLB/d3q27_pf_velocity_q27_geometric/main
DIR=/home/yuan/data_sda/RUNS/runs/stage12_static/$NAME
rm -rf "$DIR"
mkdir -p "$DIR/output"

if [ "$GEOM" = "cylinder" ]; then
    NX=96; NY=96; NZ=96
    W=3
    R_DROP=16
    DX=48; DY=48; DZ=70
    SCY=48; SCZ=48; RS=20
    python3 /home/yuan/gen_cylinder_stl.py "$SCY" "$SCZ" "$RS" 0 "$NX" "$DIR/solid.stl"
    GEOMETRY_BLOCK=$(cat <<XML
    <Wall mask="ALL" name="OuterDomain">
      <Box nx="1"/><Box dx="-1"/><Box ny="1"/><Box dy="-1"/><Box nz="1"/><Box dz="-1"/>
    </Wall>
    <Wall mask="ALL" name="AnalyticSolid"><STL file="solid.stl" scale="1" side="in"/></Wall>
XML
)
    SOLID_PARAMS=$(cat <<XML
    <Param name="AnalyticSolidType" value="2"/>
    <Param name="AnalyticSolidAxis" value="0"/>
    <Param name="AnalyticSolidCenterX" value="${DX}"/>
    <Param name="AnalyticSolidCenterY" value="${SCY}"/>
    <Param name="AnalyticSolidCenterZ" value="${SCZ}"/>
    <Param name="AnalyticSolidRadius" value="${RS}"/>
XML
)
    PLOT_ARGS="cylinder ${DX} ${SCY} ${SCZ} ${RS} ${DX} ${DY} ${DZ} ${R_DROP} ${NX} ${NY} ${NZ}"
elif [ "$GEOM" = "wall" ]; then
    NX=96; NY=80; NZ=96
    W=3
    R_DROP=16
    DX=48; DY=17; DZ=48
    GEOMETRY_BLOCK=$(cat <<XML
    <Wall mask="ALL" name="OuterDomain">
      <Box nx="1"/><Box dx="-1"/><Box dy="-1"/><Box nz="1"/><Box dz="-1"/>
    </Wall>
    <Wall mask="ALL" name="FlatLowerY"><Box ny="1"/></Wall>
XML
)
    SOLID_PARAMS=$(cat <<XML
    <Param name="AnalyticSolidType" value="1"/>
    <Param name="AnalyticSolidAxis" value="1"/>
    <Param name="AnalyticSolidPlaneOffset" value="0.0"/>
XML
)
    PLOT_ARGS="wall ${DX} 0 ${DZ} 0 ${DX} ${DY} ${DZ} ${R_DROP} ${NX} ${NY} ${NZ}"
else
    echo "unknown geometry: $GEOM" >&2
    exit 2
fi

cat > "$DIR/case.xml" <<XML
<?xml version="1.0"?>
<CLBConfig version="2.0" output="output/" permissive="true">
  <Geometry nx="${NX}" ny="${NY}" nz="${NZ}">
    <MRT><Box/></MRT>
${GEOMETRY_BLOCK}
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
    <Param name="Radius" value="${R_DROP}"/>
    <Param name="CenterX" value="${DX}"/>
    <Param name="CenterY" value="${DY}"/>
    <Param name="CenterZ" value="${DZ}"/>
    <Param name="BubbleType" value="1.0"/>
    <Param name="VelocityX" value="0.0"/>
    <Param name="VelocityY" value="0.0"/>
    <Param name="VelocityZ" value="0.0"/>
    <Param name="GravitationX" value="0.0"/>
    <Param name="GravitationY" value="0.0"/>
    <Param name="GravitationZ" value="0.0"/>
    <Param name="radAngle" value="90d"/>
    <Param name="radAngle" value="90d" zone="OuterDomain"/>
    <Param name="AnalyticWetting" value="1"/>
${SOLID_PARAMS}
    <Param name="radAngle" value="${THETA}d"/>
    <Param name="minGradient" value="1e-08"/>
  </Model>
  <VTK what="PhaseField,Rho,U,P,BOUNDARY,IsItBoundary,WallGhost,WallH,AnalyticWallNormal,AnalyticFlag"/>
  <Log Iterations="50"/>
  <Failcheck Iterations="50"/>
  <Solve Iterations="${ITERATIONS}">
    <VTK Iterations="${ITERATIONS}" what="PhaseField,Rho,U,P,BOUNDARY,IsItBoundary,WallGhost,WallH,AnalyticWallNormal,AnalyticFlag"/>
    <Log Iterations="50"/>
    <Failcheck Iterations="50"/>
  </Solve>
</CLBConfig>
XML

cd "$DIR"
echo "=== static $NAME geom=$GEOM theta=$THETA grid=${NX}x${NY}x${NZ} iterations=$ITERATIONS ==="
timeout 300 "$BIN" case.xml > run.log 2>&1
rc=$?
nan=$(grep -ci "nan" run.log || true)
echo "rc=$rc nan_lines=$nan"
FINAL_VTI=$(find output -maxdepth 1 -name 'case_VTK_P00_*.vti' | sort | tail -1)
if [ -z "$FINAL_VTI" ]; then
    echo "no VTI output" >&2
    exit 3
fi
python3 /home/yuan/stage12_static_plot.py "$FINAL_VTI" "$DIR/${NAME}.png" $PLOT_ARGS
echo "CASE_DIR=$DIR"
echo "FINAL_VTI=$DIR/$FINAL_VTI"
echo "FIGURE=$DIR/${NAME}.png"
