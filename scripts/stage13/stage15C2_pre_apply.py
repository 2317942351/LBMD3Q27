#!/usr/bin/env python3
"""Apply the 4-hunk Stage 15C2-pre hook to Dynamics.c.Rt (compile lane).
Idempotent: refuses if already applied. Exact-string match per hunk; aborts
on any mismatch so a partial apply cannot happen.
"""
import sys, hashlib
from pathlib import Path

P = Path("/home/yuan/src/TCLB_lbm2026_compile_lane/models/multiphase/d3q27_pf_velocity/Dynamics.c.Rt")
src = P.read_text()

# idempotency guard
if "Stage 15C write hook: add the residual contact-line force to F_total." in src:
    print("ALREADY APPLIED — aborting (no change)."); sys.exit(2)

pre_hash = hashlib.sha256(src.encode()).hexdigest()
print(f"pre-patch sha256: {pre_hash}")

# ---- HUNK 1: MRT hoist (replace the { real_t fcl... } block) ----
H1_OLD = """\t{
\t\treal_t fcl_x, fcl_y, fcl_z;
\t\tcalcDynamicCLShadow(gradPhi, C, &fcl_x, &fcl_y, &fcl_z);
\t\t// 15C write hook (disabled in 15B; runner refuses DynamicCLMode>=2):
\t\t// if (DynamicCLMode > 1.5) { F_cl[0]=fcl_x; F_cl[1]=fcl_y; F_cl[2]=fcl_z; }
\t}"""
H1_NEW = """\treal_t fcl_x = 0.0, fcl_y = 0.0, fcl_z = 0.0;
\t{
\t\t// Stage 15B/15C: compute the candidate residual contact-line force and
\t\t// write diagnostics on every call (Mode>=1). fcl_* is hoisted to
\t\t// function scope so the 15C write hook below can add it to F_total.
\t\tcalcDynamicCLShadow(gradPhi, C, &fcl_x, &fcl_y, &fcl_z);
\t}"""
assert src.count(H1_OLD) == 1, f"H1: expected 1 match, got {src.count(H1_OLD)}"
src = src.replace(H1_OLD, H1_NEW, 1)

# ---- HUNK 2: MRT guarded add (after the 3 F_total=...+F_mu lines, before 'if (j > 1)') ----
H2_OLD = """\t\tF_total[0] = F_surf[0] + F_pressure[0] + F_body[0] + F_mu[0];
\t\tF_total[1] = F_surf[1] + F_pressure[1] + F_body[1] + F_mu[1];
\t\tF_total[2] = F_surf[2] + F_pressure[2] + F_body[2] + F_mu[2];
\t\tif (j > 1) {"""
H2_NEW = """\t\tF_total[0] = F_surf[0] + F_pressure[0] + F_body[0] + F_mu[0];
\t\tF_total[1] = F_surf[1] + F_pressure[1] + F_body[1] + F_mu[1];
\t\tF_total[2] = F_surf[2] + F_pressure[2] + F_body[2] + F_mu[2];
\t\t// Stage 15C write hook: add the residual contact-line force to F_total.
\t\t// Shadow-only at Mode<=1 (no-op). calcDynamicCLShadow already applied
\t\t// ForceSign*Coeff*(sigma/IntWidth)*R_theta*I_cl and the ForceCap; do NOT
\t\t// rescale here. Mode>1.5 is refused by the runner until 15C is cleared.
\t\tif (DynamicCLMode > 1.5) {
\t\t\tF_total[0] += fcl_x;
\t\t\tF_total[1] += fcl_y;
\t\t\tF_total[2] += fcl_z;
\t\t}
\t\tif (j > 1) {"""
assert src.count(H2_OLD) == 1, f"H2: expected 1 match, got {src.count(H2_OLD)}"
src = src.replace(H2_OLD, H2_NEW, 1)

# ---- HUNK 3: BGK hoist ----
H3_OLD = """\t{
\t\treal_t fcl_x, fcl_y, fcl_z;
\t\tcalcDynamicCLShadow(gradPhi, C, &fcl_x, &fcl_y, &fcl_z);
\t}"""
H3_NEW = """\treal_t fcl_x = 0.0, fcl_y = 0.0, fcl_z = 0.0;
\t{
\t\t// Stage 15B/15C: diagnostics on every call; fcl_* hoisted for the 15C
\t\t// write hook below (BGK path, symmetric with MRT).
\t\tcalcDynamicCLShadow(gradPhi, C, &fcl_x, &fcl_y, &fcl_z);
\t}"""
assert src.count(H3_OLD) == 1, f"H3: expected 1 match, got {src.count(H3_OLD)}"
src = src.replace(H3_OLD, H3_NEW, 1)

# ---- HUNK 4: BGK guarded add (8-space indent, before the <?R C( u, g %*% U) ?> line) ----
H4_OLD = """        F_total[0] = F_surf[0] + F_pressure[0] + F_body[0] + F_mu[0];
        F_total[1] = F_surf[1] + F_pressure[1] + F_body[1] + F_mu[1];
        F_total[2] = F_surf[2] + F_pressure[2] + F_body[2] + F_mu[2];

    <?R C( u, g %*% U) ?>"""
H4_NEW = """        F_total[0] = F_surf[0] + F_pressure[0] + F_body[0] + F_mu[0];
        F_total[1] = F_surf[1] + F_pressure[1] + F_body[1] + F_mu[1];
        F_total[2] = F_surf[2] + F_pressure[2] + F_body[2] + F_mu[2];
        // Stage 15C write hook: add residual contact-line force to F_total.
        // Shadow-only at Mode<=1 (no-op). calcDynamicCLShadow already applied
        // ForceSign*Coeff*(sigma/IntWidth)*R_theta*I_cl and the ForceCap.
        if (DynamicCLMode > 1.5) {
            F_total[0] += fcl_x;
            F_total[1] += fcl_y;
            F_total[2] += fcl_z;
        }

    <?R C( u, g %*% U) ?>"""
assert src.count(H4_OLD) == 1, f"H4: expected 1 match, got {src.count(H4_OLD)}"
src = src.replace(H4_OLD, H4_NEW, 1)

P.write_text(src)
post_hash = hashlib.sha256(src.encode()).hexdigest()
print(f"post-patch sha256: {post_hash}")
print("ALL 4 HUNKS APPLIED OK")
