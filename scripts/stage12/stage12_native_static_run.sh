#!/bin/bash
# Run short static wetting audit cases using TCLB native solid primitives.
# This avoids STL side-convention ambiguity while keeping the Stage9 analytic
# wetting parameters matched to the native plane/cylinder/sphere geometry.
#
# Usage:
#   bash stage12_native_static_run.sh <name> <wall|cylinder|sphere> <theta_deg> <iterations>
set -euo pipefail

export PATH=/usr/local/cuda-12.6/bin:/usr/bin:/bin:/usr/local/bin
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-1}"
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh

NAME="$1"
GEOM="$2"
THETA="$3"
ITERATIONS="$4"

BIN="${TCLB_BIN:-/home/yuan/data_sda/RUNS/runs/stage9/src/TCLB_stage9_analytic_wetting_20260614/CLB/d3q27_pf_velocity_q27_geometric/main}"
ROOT="${STAGE12_NATIVE_ROOT:-/home/yuan/data_sda/RUNS/runs/stage12_native_static}"
DIR="$ROOT/$NAME"

rm -rf "$DIR"
mkdir -p "$DIR/output"

W="${STAGE12_W:-3}"
R_DROP="${STAGE12_R_DROP:-16}"

case "$GEOM" in
  wall)
    NX=96; NY=80; NZ=96
    DX=48; DY=17; DZ=48
    SOLID_CX=48; SOLID_CY=0; SOLID_CZ=48; RS=0; AXIS=1
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
    ;;
  cylinder)
    NX=96; NY=96; NZ=96
    DX=48; DY=70; DZ=48
    SOLID_CX=48; SOLID_CY=48; SOLID_CZ=48; RS=20; AXIS=2
    GEOMETRY_BLOCK=$(cat <<XML
    <Wall mask="ALL" name="OuterDomain">
      <Box nx="1"/><Box dx="-1"/><Box ny="1"/><Box dy="-1"/><Box nz="1"/><Box dz="-1"/>
    </Wall>
    <Wall mask="ALL" name="AnalyticCylinder">
      <Cylinder dx="28" nx="40" dy="28" ny="40" dz="0" nz="96"/>
    </Wall>
XML
)
    SOLID_PARAMS=$(cat <<XML
    <Param name="AnalyticSolidType" value="2"/>
    <Param name="AnalyticSolidAxis" value="${AXIS}"/>
    <Param name="AnalyticSolidCenterX" value="${SOLID_CX}"/>
    <Param name="AnalyticSolidCenterY" value="${SOLID_CY}"/>
    <Param name="AnalyticSolidCenterZ" value="${SOLID_CZ}"/>
    <Param name="AnalyticSolidRadius" value="${RS}"/>
XML
)
    ;;
  sphere)
    NX=80; NY=80; NZ=140
    DX=40; DY=40; DZ=90
    SOLID_CX=40; SOLID_CY=40; SOLID_CZ=48; RS=20; AXIS=2
    GEOMETRY_BLOCK=$(cat <<XML
    <Wall mask="ALL" name="OuterDomain">
      <Box nx="1"/><Box dx="-1"/><Box ny="1"/><Box dy="-1"/><Box nz="1"/><Box dz="-1"/>
    </Wall>
    <Wall mask="ALL" name="AnalyticSphere">
      <Sphere dx="20" nx="40" dy="20" ny="40" dz="28" nz="40"/>
    </Wall>
XML
)
    SOLID_PARAMS=$(cat <<XML
    <Param name="AnalyticSolidType" value="3"/>
    <Param name="AnalyticSolidCenterX" value="${SOLID_CX}"/>
    <Param name="AnalyticSolidCenterY" value="${SOLID_CY}"/>
    <Param name="AnalyticSolidCenterZ" value="${SOLID_CZ}"/>
    <Param name="AnalyticSolidRadius" value="${RS}"/>
XML
)
    ;;
  *)
    echo "unknown geometry: $GEOM" >&2
    exit 2
    ;;
esac

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
echo "=== native-static $NAME geom=$GEOM theta=$THETA grid=${NX}x${NY}x${NZ} W=$W R_drop=$R_DROP iterations=$ITERATIONS ==="
timeout "${STAGE12_TIMEOUT:-600}" "$BIN" case.xml > run.log 2>&1
rc=$?
nan_lines=$(grep -ci "nan" run.log || true)
echo "rc=$rc nan_lines=$nan_lines"
final_vti=$(find output -maxdepth 1 -name 'case_VTK_P00_*.vti' | sort | tail -1)
if [ -z "$final_vti" ]; then
  echo "no VTI output" >&2
  exit 3
fi
echo "CASE_DIR=$DIR"
echo "FINAL_VTI=$DIR/$final_vti"
echo "PLOT_ARGS=$GEOM $SOLID_CX $SOLID_CY $SOLID_CZ $RS $DX $DY $DZ $R_DROP $NX $NY $NZ"
