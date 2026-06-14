#!/bin/bash
# stage12_run.sh - run one Stage12 case. Generates STL, runs, measures.
# Usage: bash stage12_run.sh <name> <geom: cylinder|sphere> <theta> <grid_nx> <grid_ny> <grid_nz> <W> <R_drop> <drop_x> <drop_y> <drop_z> <solid_cy> <solid_cz> <R_solid>
export PATH=/usr/local/cuda-12.6/bin:/usr/bin:/bin:/usr/local/bin
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES=1
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh

NAME="$1"; GEOM="$2"; THETA="$3"; NX="$4"; NY="$5"; NZ="$6"
W="$7"; R_DROP="$8"; DX="$9"; DY="${10}"; DZ="${11}"
SCY="${12}"; SCZ="${13}"; RS="${14}"
BIN=/home/yuan/data_sda/RUNS/runs/stage9/src/TCLB_stage9_analytic_wetting_20260614/CLB/d3q27_pf_velocity_q27_geometric/main
DIR=/home/yuan/data_sda/RUNS/runs/stage12/$NAME
rm -rf "$DIR"; mkdir -p "$DIR/output"

# generate STL
if [ "$GEOM" = "cylinder" ]; then
    python3 /home/yuan/gen_cylinder_stl.py "$SCY" "$SCZ" "$RS" 0 "$NX" "$DIR/solid.stl"
    STL_BLOCK="<Wall mask=\"ALL\" name=\"AnalyticSolid\"><STL file=\"solid.stl\" scale=\"1\" side=\"out\"/></Wall>"
    AN_TYPE="2"; AN_AXIS="0"
    AN_CX="$SCY"; AN_CY="$SCZ"; AN_CZ="$SCZ"
    SOLID_PARAMS="<Param name=\"AnalyticSolidType\" value=\"2\"/>
    <Param name=\"AnalyticSolidAxis\" value=\"0\"/>
    <Param name=\"AnalyticSolidCenterX\" value=\"${SCY}\"/>
    <Param name=\"AnalyticSolidCenterY\" value=\"${SCZ}\"/>
    <Param name=\"AnalyticSolidCenterZ\" value=\"${SCZ}\"/>
    <Param name=\"AnalyticSolidRadius\" value=\"${RS}\"/>"
else
    python3 /home/yuan/gen_sphere_stl.py "$SCY" "$SCZ" "$SCZ" "$RS" "$DIR/solid.stl"
    STL_BLOCK="<Wall mask=\"ALL\" name=\"AnalyticSolid\"><STL file=\"solid.stl\" scale=\"1\" side=\"in\"/></Wall>"
    SOLID_PARAMS="<Param name=\"AnalyticSolidType\" value=\"3\"/>
    <Param name=\"AnalyticSolidCenterX\" value=\"${SCY}\"/>
    <Param name=\"AnalyticSolidCenterY\" value=\"${SCZ}\"/>
    <Param name=\"AnalyticSolidCenterZ\" value=\"${SCZ}\"/>
    <Param name=\"AnalyticSolidRadius\" value=\"${RS}\"/>"
fi

cat > "$DIR/case.xml" <<XML
<?xml version="1.0"?>
<CLBConfig version="2.0" output="output/" permissive="true">
  <Geometry nx="${NX}" ny="${NY}" nz="${NZ}">
    <MRT><Box/></MRT>
    <Wall mask="ALL" name="OuterDomain">
      <Box nx="1"/><Box dx="-1"/><Box dy="-1"/><Box nz="1"/><Box dz="-1"/>
    </Wall>
    ${STL_BLOCK}
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
    <Param name="radAngle" value="90d"/>
    <Param name="radAngle" value="90d" zone="OuterDomain"/>
    <Param name="AnalyticWetting" value="1"/>
    ${SOLID_PARAMS}
    <Param name="radAngle" value="${THETA}d"/>
    <Param name="minGradient" value="1e-08"/>
  </Model>
  <VTK what="PhaseField,Rho,U,P,BOUNDARY,WallGhost,WallH,AnalyticWallNormal,AnalyticFlag"/>
  <Solve Iterations="100000">
    <VTK Iterations="100000" what="PhaseField,Rho,U,P,BOUNDARY,WallGhost,WallH,AnalyticWallNormal,AnalyticFlag"/>
    <Failcheck Iterations="5000"/>
  </Solve>
</CLBConfig>
XML

echo "=== $NAME : geom=$GEOM theta=$THETA W=$W grid=${NX}x${NY}x${NZ} R_drop=$R_DROP ==="
cd "$DIR"
timeout 540 "$BIN" case.xml > run.log 2>&1
rc=$?
nan=$(grep -c NaN run.log)
echo "rc=$rc nan=$nan"
if [ "$rc" -eq 0 ] && [ "$nan" -eq 0 ] && [ -f output/case_VTK_P00_00100000.vti ]; then
    echo "--- curved-angle post-process ---"
    python3 /home/yuan/stage12_curved_angle.py output/case_VTK_P00_00100000.vti "$GEOM" "$SCY" "$SCZ" "$SCZ" "$RS" "$DX" "$DY" "$DZ" 2>&1 | grep -E "contact angle|phase range|left:|right:|contour"
else
    echo "RESULT $NAME FAIL rc=$rc nan=$nan"
fi
