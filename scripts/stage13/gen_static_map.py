import importlib.util, sys, os
spec=importlib.util.spec_from_file_location("runner","/home/yuan/stage13_flat_wall_diagnostic_run.py")
m=importlib.util.module_from_spec(spec)
sys.modules["runner"]=m
spec.loader.exec_module(m)
ROOT=sys.argv[1]
kw=dict(iterations=4000, vtk_period=1000, log_period=500, volume_radius=16.0,
  int_width=3.0, mobility=0.3, wetting_bc_mode=0, force_fixed_tol=0.0,
  force_fixed_max_iter=2, wall_compact_stencil_mode=2,
  wall_compact_stencil_write_allowed_flag=1, wall_grad_mode=0,
  wall_grad_contact_sign=1.0, wall_mu_mode=0, dynamic_cl_mode=2,
  cos_sign=-1.0, force_sign=-1.0, dynamic_cl_coeff=0.0)
for th in [45,60,120,135]:
    case=m.CaseDef("diag_wall_t%d"%th, float(th), float(th), "static map")
    xml=m.render_xml(case, **kw)
    d=os.path.join(ROOT, case.name); os.makedirs(d, exist_ok=True)
    open(os.path.join(d,"case.xml"),"w").write(xml); print("wrote", d)
