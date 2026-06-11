# Wall Signed-Profile Candidate Failure

Date: 2026-06-11

Status: `failed_negative_evidence`

## Scope

This note records two isolated signed/profile wall-reconstruction candidates
tested after the z48 separated-geometry zonal smoke. These candidates are not
validation evidence and must not be used for longer PRE sphere runs.

## v1 Lane

```text
source = /home/yuan/src/TCLB_clean_wall_signed_profile_diag_20260611
binary = /home/yuan/src/TCLB_clean_wall_signed_profile_diag_20260611/CLB/d3q27_pf_velocity_q27_geometric/main
final binary_sha256 = 47b7281309f5f5e843b0a56e246ccfc92f3b5d2f4509904a85bd15fbe145e5e6
provenance = /mnt/8A0E24070E23EAC1/runs/tclb_wall_signed_profile_diag_provenance_20260611
```

Change:

```text
normal geometric path, further-next fallback, and next-node correction were
routed through a bounded logit/profile reconstruction.
```

Smoke:

```text
remote = /mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_theta030_z48_gap24_outer90_sphere11_signed_profile_smoke_20260611/theta030
case = z48/gap24, outer radAngle 90d, sphere radAngle 11d, 100 steps
solver rc = 0
run.done = present
run.stderr = empty
postprocess rc = 0 after corrected invocation
```

Failure:

```text
step 100 nonfinite_total = 4,375,152
PhaseField physical nonfinite = 1,104,400 / 1,152,000
Rho fluid_physical nonfinite = 1,038,980 / 1,038,980
UMag fluid_physical nonfinite = 1,038,980 / 1,038,980
```

## v2 Lane

```text
source = /home/yuan/src/TCLB_clean_wall_signed_profile_v2_diag_20260611
binary = /home/yuan/src/TCLB_clean_wall_signed_profile_v2_diag_20260611/CLB/d3q27_pf_velocity_q27_geometric/main
binary_sha256 = 36e640d56cbbbeb5567a1cbf0b9edd70d2b906fe5a6520ec493951367d366bd1
provenance = /mnt/8A0E24070E23EAC1/runs/tclb_wall_signed_profile_v2_diag_provenance_20260611
```

Change:

```text
only the normal geometric path was written through bounded logit/profile
reconstruction; next-node correction and further-next fallback retained the
previous profile-lane semantics.
```

Smoke:

```text
remote = /mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_theta030_z48_gap24_outer90_sphere11_signed_profile_v2_smoke_20260611/theta030
case = z48/gap24, outer radAngle 90d, sphere radAngle 11d, 100 steps
solver rc = 0
postprocess rc = 0
```

Failure:

```text
step 100 nonfinite_total = 4,375,152
PhaseField physical nonfinite = 1,104,400 / 1,152,000
Rho fluid_physical nonfinite = 1,038,980 / 1,038,980
UMag fluid_physical nonfinite = 1,038,980 / 1,038,980
```

## Interpretation

The shared failure in v1 and v2 shows that the direct signed-logit wall write
is not a viable immediate replacement for the profile lane. The failure is not
explained by XML zonal parsing, because both smokes still confirmed:

```text
Default/OuterDomain radAngle = 90d
SolidSphere radAngle = 11d
outer WallTanCoeff mean ~= 0
sphere WallTanCoeff mean ~= 5.144554
```

It is also not merely a diagnostic-output NaN: the physical fluid fields
`PhaseField`, `Rho`, and `U` become nonfinite by 100 steps.

## Next Safe Step

Do not run 50k or 200k with either signed-profile write candidate.

The next defensible source step is diagnostic-only:

```text
1. keep the stable profile actual wall write
2. output signed-logit/profile prediction as a passive diagnostic
3. inspect signed shift magnitude and spatial distribution
4. design a damped or analytically re-derived formula only after the passive
   diagnostic proves bounded finite fields through the z48 smoke and flat-wall
   gate
```
