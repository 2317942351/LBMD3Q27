# Cylinder static cases with compact-ghost BC (WallCompactStencilMode=2) on AnalyticCylinder.
# Merges stage13 compact-stencil Model params with stage12 cylinder geometry/init.
import importlib.util, sys, os, math
spec=importlib.util.spec_from_file_location("r","/home/yuan/stage13_flat_wall_diagnostic_run.py")
r=importlib.util.module_from_spec(spec); sys.modules["r"]=r; spec.loader.exec_module(r)
VTK=r.VTK_FIELDS
ROOT=sys.argv[1]
def P(n,v): return f"<Param name=\"{n}\" value=\"{v}\"/>"
def sphere_cap_parent(solid_r, vol_r, th_deg):
    th=math.radians(th_deg)
    def outside(R):
        return math.pi*R**3*(2+math.cos(th))*(1-math.cos(th))**2/3 - 2*math.pi*solid_r**2*R*(1-math.cos(th)) + 2*math.pi*solid_r**3*(math.cos(th)-math.cos(3*th))/3
    target=4*math.pi*vol_r**3/3
    lo,hi=0.1,400.0
    while outside(hi)<target: hi*=2
    for _ in range(80):
        mid=0.5*(lo+hi)
        if outside(mid)<target: lo=mid
        else: hi=mid
    R=0.5*(lo+hi); cd=R*(1-math.cos(th)); return R,cd
def cyl_xml(th, M=0.6, Iters=12000):
    sc=(48.0,48.0,48.0); rs=20.0; vr=16.0
    R,cd=sphere_cap_parent(rs,vr,th)
    cap_c=(sc[0],sc[1]+cd,sc[2]); probe=(sc[0],sc[1]+rs+4.0,sc[2])
    init="\n".join([P("Radius",0),P("CenterX",probe[0]),P("CenterY",probe[1]),P("CenterZ",probe[2]),
      P("CylinderCapInit",1),P("CylinderCapInitParentRadius",R),P("CylinderCapInitCenterX",cap_c[0]),
      P("CylinderCapInitCenterY",cap_c[1]),P("CylinderCapInitCenterZ",cap_c[2]),
      P("CylinderCapInitSolidCenterX",sc[0]),P("CylinderCapInitSolidCenterY",sc[1]),P("CylinderCapInitSolidCenterZ",sc[2]),
      P("CylinderCapInitSolidRadius",rs),P("CylinderCapInitSolidAxis",2)])
    return f"""<?xml version="1.0"?>
<CLBConfig output="output/" permissive="true">
  <Geometry nx="96" ny="96" nz="96">
    <MRT><Box/></MRT>
    <Wall mask="ALL" name="OuterDomain"><Box nx="1"/><Box dx="-1"/><Box ny="1"/><Box dy="-1"/><Box nz="1"/><Box dz="-1"/></Wall>
    <Wall mask="ALL" name="AnalyticCylinder"><Cylinder dx="28" nx="40" dy="28" ny="40" dz="0" nz="96"/></Wall>
  </Geometry>
  <Model>
    <Param name="Density_h" value="1"/><Param name="Density_l" value="0.001"/>
    <Param name="Viscosity_h" value="0.1"/><Param name="Viscosity_l" value="0.1"/>
    <Param name="tauUpdate" value="1"/><Param name="sigma" value="5e-05"/>
    <Param name="M" value="{M}"/><Param name="IntWidth" value="3"/>
{init}
    <Param name="BubbleType" value="1.0"/><Param name="VelocityX" value="0"/><Param name="VelocityY" value="0"/><Param name="VelocityZ" value="0"/>
    <Param name="GravitationX" value="0"/><Param name="GravitationY" value="0"/><Param name="GravitationZ" value="0"/>
    <Param name="radAngle" value="90d"/><Param name="radAngle" value="90d" zone="OuterDomain"/>
    <Param name="AnalyticSolidType" value="2"/><Param name="AnalyticSolidAxis" value="2"/>
    <Param name="AnalyticSolidCenterX" value="{sc[0]}"/><Param name="AnalyticSolidCenterY" value="{sc[1]}"/><Param name="AnalyticSolidCenterZ" value="{sc[2]}"/><Param name="AnalyticSolidRadius" value="{rs}"/>
    <Param name="AnalyticWetting" value="1"/><Param name="WettingBCMode" value="0"/>
    <Param name="WallCompactStencilMode" value="2"/><Param name="WallCompactStencilNormalMode" value="1"/><Param name="WallCompactStencilMaxL" value="3"/>
    <Param name="WallCompactStencilBoundEps" value="0"/><Param name="WallCompactStencilMaxBoundedDelta" value="1e-8"/><Param name="WallCompactStencilAppliedResidualTol" value="1e-8"/><Param name="WallCompactStencilWriteAllowedFlag" value="1"/>
    <Param name="ForceFixedTol" value="0"/><Param name="ForceFixedMaxIter" value="2"/>
    <Param name="WallGradMode" value="0"/><Param name="WallGradContactSign" value="1"/><Param name="WallMuMode" value="0"/>
    <Param name="DynamicCLMode" value="2"/><Param name="DynamicCLCosSign" value="-1"/><Param name="DynamicCLForceSign" value="-1"/><Param name="DynamicCLCoeff" value="0"/>
    <Param name="radAngle" value="{th}d" zone="AnalyticCylinder"/>
    <Param name="minGradient" value="1e-8"/>
  </Model>
  <VTK what="{VTK}"/>
  <Log Iterations="1000"/><Failcheck Iterations="1000"/>
  <Solve Iterations="{Iters}"><VTK Iterations="2000" what="{VTK}"/><Log Iterations="1000"/><Failcheck Iterations="1000"/></Solve>
</CLBConfig>"""
for th in [60,90,120]:
    d=os.path.join(ROOT,f"cyl_t{th}"); os.makedirs(d,exist_ok=True)
    open(os.path.join(d,"case.xml"),"w").write(cyl_xml(th)); print("wrote",d)
