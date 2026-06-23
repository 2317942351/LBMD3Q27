# Setting permissive access policy.
# Stage9 note: this flag is retained because the wetting path intentionally
# writes PhaseF on wall nodes in calcWall_CA after calcPhase has already
# written PhaseF on fluid nodes within the same Iteration action. This is a
# legitimate multi-stage write (calcPhase sets fluid PhaseF, then calcWall_CA
# overrides PhaseF on wall nodes only). The permissive flag was removed
# initially to surface ordering bugs, but TCLB's strict checker treats the
# intentional wall-node override as an error, so the flag must stay. The
# Stage9 analytic path writes the wall ghost into the separate WallGhost
# field and only mirrors the fluid value into PhaseF on wall nodes, so no
# NEW ordering dependency is introduced.
SetOptions(permissive.access=TRUE)


# Density - table of variables of LB Node to stream
#	Velocity-based Evolution d3q27:
source("lattice.R")

# Densities for initialising with rinside
AddDensity(name="Init_UX_External", group="init", comment="free stream velocity", parameter=TRUE)
AddDensity(name="Init_UY_External", group="init", comment="free stream velocity", parameter=TRUE)
AddDensity(name="Init_UZ_External", group="init", comment="free stream velocity", parameter=TRUE)
AddDensity(name="Init_PhaseField_External", group="init", dx=0,dy=0,dz=0, parameter=TRUE)

# macroscopic params
# - consider migrating to fields
AddDensity(name="pnorm", dx=0, dy=0, dz=0, group="Vel")
AddDensity(name="U", dx=0, dy=0, dz=0, group="Vel")
AddDensity(name="V", dx=0, dy=0, dz=0, group="Vel")
AddDensity(name="W", dx=0, dy=0, dz=0, group="Vel")

# normal direction
# - consider migrating to fields
AddDensity(name="nw_x", dx=0, dy=0, dz=0, group="nw")
AddDensity(name="nw_y", dx=0, dy=0, dz=0, group="nw")
AddDensity(name="nw_z", dx=0, dy=0, dz=0, group="nw")

# Helper fields for the staircase improvement
extra_fields_to_load_for_bc = c()
extra_save_iteration = c()
extra_load_iteration = c()
extra_load_phase = c()

if (Options$staircaseimp) {
    # actual normal directions
    AddDensity(name="nw_actual_x", dx=0, dy=0, dz=0, group="nw_actual")
    AddDensity(name="nw_actual_y", dx=0, dy=0, dz=0, group="nw_actual")
    AddDensity(name="nw_actual_z", dx=0, dy=0, dz=0, group="nw_actual")

    # Standard staircase improvement
    AddDensity(name="coeff_v1", dx=0, dy=0, dz=0, group="st_interpolation")
    AddDensity(name="coeff_v2", dx=0, dy=0, dz=0, group="st_interpolation")
    AddDensity(name="coeff_v3", dx=0, dy=0, dz=0, group="st_interpolation")
    AddDensity(name="triangle_index", dx=0, dy=0, dz=0, group="st_interpolation")

    if (Options$tprec) {
        # Staircase improvement with more precise second triangle
        AddDensity(name="coeff2_v1", dx=0, dy=0, dz=0, group="st_interpolation")
        AddDensity(name="coeff2_v2", dx=0, dy=0, dz=0, group="st_interpolation")
        AddDensity(name="coeff2_v3", dx=0, dy=0, dz=0, group="st_interpolation")
        AddDensity(name="triangle_index2", dx=0, dy=0, dz=0, group="st_interpolation")
    }

    # Make sure that those fields are now loaded
    extra_save_iteration = c(extra_save_iteration, "nw_actual", "st_interpolation")
    extra_load_iteration = c(extra_load_iteration, "nw_actual", "st_interpolation")
    extra_load_phase = c(extra_load_phase, "nw_actual")
    extra_fields_to_load_for_bc = c("nw_actual", "st_interpolation")
}

AddDensity("IsSpecialBoundaryPoint", dx=0, dy=0, dz=0, group="solid_boundary")
AddQuantity("SpecialBoundaryPoint", unit = 1)

if (Options$geometric){
    AddField("IsBoundary", stencil3d=2, group="solid_boundary")
} else {
    AddField("IsBoundary", stencil3d=1, group="solid_boundary")
}

# Stage9 analytic-geometry wetting BC fields.
#   WallGhost holds the wall ghost phi on wall/solid nodes only. It is a
#   separate field from PhaseF so that gradient stencils reading PhaseF never
#   pick up ghost values. WallH is the analytic signed distance from the
#   first-fluid node to the wall. AnalyticFlag tags nodes that belong to the
#   analytic geometry. All are 0 on fluid nodes by default.
AddField("WallGhost", stencil3d=2, group="solid_boundary")
AddField("WallH",     stencil3d=1, group="solid_boundary")
AddField("AnalyticFlag", stencil3d=1, group="solid_boundary")
AddField("WallGhostRaw", stencil3d=1, group="solid_boundary")
AddField("WallGhostClamped", stencil3d=1, group="solid_boundary")
AddField("WallGhostClampHit", stencil3d=1, group="solid_boundary")
AddField("WettingPathId", stencil3d=1, group="solid_boundary")
AddField("LocalRadAngle", stencil3d=1, group="solid_boundary")
AddField("WallCSQMode", stencil3d=1, group="solid_boundary")
AddField("WallCSQNormalMode", stencil3d=1, group="solid_boundary")
AddField("WallCSQValid", stencil3d=1, group="solid_boundary")
AddField("WallCSQThetaDeg", stencil3d=1, group="solid_boundary")
AddField("WallCSQNormalX", stencil3d=1, group="solid_boundary")
AddField("WallCSQNormalY", stencil3d=1, group="solid_boundary")
AddField("WallCSQNormalZ", stencil3d=1, group="solid_boundary")
AddField("WallCSQDs", stencil3d=1, group="solid_boundary")
AddField("WallCSQDf", stencil3d=1, group="solid_boundary")
AddField("WallCSQQf", stencil3d=1, group="solid_boundary")
AddField("WallCSQQsRaw", stencil3d=1, group="solid_boundary")
AddField("WallCSQQsBounded", stencil3d=1, group="solid_boundary")
AddField("WallCSQQw", stencil3d=1, group="solid_boundary")
AddField("WallCSQResidual", stencil3d=1, group="solid_boundary")
AddField("WallCSQAppliedResidual", stencil3d=1, group="solid_boundary")
AddField("WallCSQDiscriminant", stencil3d=1, group="solid_boundary")
AddField("WallCSQRootChoice", stencil3d=1, group="solid_boundary")
AddField("WallCSQStencilCase", stencil3d=1, group="solid_boundary")
AddField("WallCSQStencilL", stencil3d=1, group="solid_boundary")
AddField("WallCSQFallbackReason", stencil3d=1, group="solid_boundary")
AddField("WallCSQBoundedDelta", stencil3d=1, group="solid_boundary")
AddField("WallCSQAppliedWeight", stencil3d=1, group="solid_boundary")
AddField("WallCSQWriteAllowedFlag", stencil3d=1, group="solid_boundary")
AddField("WallCSQCandidateCount", stencil3d=1, group="solid_boundary")
AddField("WallCSQFluidVertexCount", stencil3d=1, group="solid_boundary")
AddField("WallCSQTriangleInside", stencil3d=1, group="solid_boundary")
AddField("WallCSQPlaneId", stencil3d=1, group="solid_boundary")
AddField("WallCSQBaryMin", stencil3d=1, group="solid_boundary")
AddField("WallCSQBaryMax", stencil3d=1, group="solid_boundary")
AddField("WallCSQMethodComplete", stencil3d=1, group="solid_boundary")
AddField("WallCSQVertexMaskBits", stencil3d=1, group="solid_boundary")
AddField("WallCSQVertexRealFluidBits", stencil3d=1, group="solid_boundary")
AddField("WallCSQVertexPhaseCleanBits", stencil3d=1, group="solid_boundary")
AddField("WallCSQVertexQMin", stencil3d=1, group="solid_boundary")
AddField("WallCSQVertexQMax", stencil3d=1, group="solid_boundary")
AddField("WallCSQRejectedSolidVertexCount", stencil3d=1, group="solid_boundary")
AddField("WallCSQRejectedSentinelCount", stencil3d=1, group="solid_boundary")
AddField("WallCSQStrictWriteReady", stencil3d=1, group="solid_boundary")
AddField("WallGradDeltaMag", stencil3d=1, group="wall_grad_diag")
AddField("WallGradThetaApp", stencil3d=1, group="wall_grad_diag")
AddField("WallMuCandidate", stencil3d=1, group="wall_grad_diag")
# Layer3 DynamicCL shadow diagnostics (Stage 15B). Candidate residual
# contact-line force computed but NOT added to F_total (DynamicCLMode<=1).
AddField("DynamicCLActive", stencil3d=1, group="wall_grad_diag")
AddField("DynamicCLIndicator", stencil3d=1, group="wall_grad_diag")
AddField("DynamicCLCosApp", stencil3d=1, group="wall_grad_diag")
AddField("DynamicCLThetaApp", stencil3d=1, group="wall_grad_diag")
AddField("DynamicCLCosEq", stencil3d=1, group="wall_grad_diag")
AddField("DynamicCLCosResidual", stencil3d=1, group="wall_grad_diag")
AddField("DynamicCLForceCandidateX", stencil3d=1, group="wall_grad_diag")
AddField("DynamicCLForceCandidateY", stencil3d=1, group="wall_grad_diag")
AddField("DynamicCLForceCandidateZ", stencil3d=1, group="wall_grad_diag")
AddField("DynamicCLForceCandidateMag", stencil3d=1, group="wall_grad_diag")
AddField("DynamicCLTangentialX", stencil3d=1, group="wall_grad_diag")
AddField("DynamicCLTangentialY", stencil3d=1, group="wall_grad_diag")
AddField("DynamicCLTangentialZ", stencil3d=1, group="wall_grad_diag")
AddField("DynamicCLWallNormalX", stencil3d=1, group="wall_grad_diag")
AddField("DynamicCLWallNormalY", stencil3d=1, group="wall_grad_diag")
AddField("DynamicCLWallNormalZ", stencil3d=1, group="wall_grad_diag")
AddField("DynamicCLRejectedReason", stencil3d=1, group="wall_grad_diag")
# Stage 15B fix: theta_eq must come from the adjacent WETTING wall (zone-
# resolved LocalRadAngle), NOT from this fluid node's own zonal radAngle
# (which reads the global default 90 deg on non-wetting-wall zones).
# These fields record how theta_eq / n_w were obtained and why a node may
# be blocked even if it sits near *some* boundary (rejects OuterDomain).
AddField("DynamicCLThetaEq", stencil3d=1, group="wall_grad_diag")
AddField("DynamicCLWallContextFound", stencil3d=1, group="wall_grad_diag")
AddField("DynamicCLBlockedReason", stencil3d=1, group="wall_grad_diag")
AddField("DynamicCLWallDx", stencil3d=1, group="wall_grad_diag")
AddField("DynamicCLWallDy", stencil3d=1, group="wall_grad_diag")
AddField("DynamicCLWallDz", stencil3d=1, group="wall_grad_diag")

stage13_wall_diag_fields = c(
    "WallGhost", "WallH", "AnalyticFlag", "WallGhostRaw",
    "WallGhostClamped", "WallGhostClampHit", "WettingPathId",
    "LocalRadAngle",
    "WallCSQMode", "WallCSQNormalMode", "WallCSQValid", "WallCSQThetaDeg",
    "WallCSQNormalX", "WallCSQNormalY", "WallCSQNormalZ",
    "WallCSQDs", "WallCSQDf", "WallCSQQf", "WallCSQQsRaw",
    "WallCSQQsBounded", "WallCSQQw", "WallCSQResidual",
    "WallCSQAppliedResidual",
    "WallCSQDiscriminant", "WallCSQRootChoice", "WallCSQStencilCase",
    "WallCSQStencilL", "WallCSQFallbackReason", "WallCSQBoundedDelta",
    "WallCSQAppliedWeight", "WallCSQWriteAllowedFlag",
    "WallCSQCandidateCount", "WallCSQFluidVertexCount",
    "WallCSQTriangleInside", "WallCSQPlaneId", "WallCSQBaryMin",
    "WallCSQBaryMax", "WallCSQMethodComplete",
    "WallCSQVertexMaskBits", "WallCSQVertexRealFluidBits",
    "WallCSQVertexPhaseCleanBits",
    "WallCSQVertexQMin", "WallCSQVertexQMax",
    "WallCSQRejectedSolidVertexCount", "WallCSQRejectedSentinelCount",
    "WallCSQStrictWriteReady"
)
stage13_wall_phase_save_fields = c("PhaseF", stage13_wall_diag_fields)

# Stage13 diagnostics: output-only in this pass. These fields are written by
# collision/update code but do not feed back into the solver.
AddField("ForceIterResidual", stencil3d=1, group="runtime_diagnostics")
AddField("ForceIterCount", stencil3d=1, group="runtime_diagnostics")
AddField("MassCorrectionApplied", stencil3d=1, group="runtime_diagnostics")
AddField("PhaseStencilGhostUseCount", stencil3d=1, group="runtime_diagnostics")
AddField("PhaseStencilFallbackCount", stencil3d=1, group="runtime_diagnostics")
AddField("PhaseStencilMidpointFallbackCount", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayPhaseConsumed", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayPhaseFromH", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayLapPhi", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayMu", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayGradPhiX", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayGradPhiY", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayGradPhiZ", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFsurfX", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFsurfY", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFsurfZ", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFpressureX", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFpressureY", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFpressureZ", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFbodyX", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFbodyY", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFbodyZ", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFmuX", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFmuY", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFmuZ", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFtotalX", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFtotalY", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFtotalZ", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayRho", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayTau", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayPressureMoment", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayUPreForceX", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayUPreForceY", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayUPreForceZ", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayUPostForceX", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayUPostForceY", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayUPostForceZ", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayPhaseAdvVelocityX", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayPhaseAdvVelocityY", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayPhaseAdvVelocityZ", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayForceOverRhoX", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayForceOverRhoY", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayForceOverRhoZ", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFmuIter1X", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFmuIter1Y", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFmuIter1Z", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFtotalIter1X", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFtotalIter1Y", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFtotalIter1Z", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayUPostIter1X", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayUPostIter1Y", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayUPostIter1Z", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayNormalX", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayNormalY", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayNormalZ", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayStressXX", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayStressXY", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayStressXZ", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayStressYY", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayStressYZ", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayStressZZ", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFphiSum", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFphiMaxAbs", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayTmp1", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayM0X", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayM0Y", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayM0Z", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayVelocityHalfForceX", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayVelocityHalfForceY", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayVelocityHalfForceZ", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayMFx", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayMFy", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayMFz", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayMomentumAfterGX", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayMomentumAfterGY", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayMomentumAfterGZ", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayMomentumDeltaGX", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayMomentumDeltaGY", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayMomentumDeltaGZ", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayPressureInput", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayPressureForceScale", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayPressurePhysicalInput", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFpressureNoThirdX", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFpressureNoThirdY", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFpressureNoThirdZ", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFpressurePhysicalX", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFpressurePhysicalY", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFpressurePhysicalZ", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayStressInputXX", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayStressInputXY", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayStressInputXZ", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayStressInputYY", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayStressInputYZ", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayStressInputZZ", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayStressIter1XX", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayStressIter1XY", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayStressIter1XZ", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayStressIter1YY", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayStressIter1YZ", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayStressIter1ZZ", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFmuRawX", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFmuRawY", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFmuRawZ", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFmuDeltaX", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFmuDeltaY", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayFmuDeltaZ", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayTauUsed", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayRhoForForce", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayForceInjectionMode", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayPressureClosureMode", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayForceDensityClosureMode", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayForceFixedPointMode", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayForceRhoRaw", stencil3d=1, group="runtime_diagnostics")
AddField("ReplayForceRhoEffective", stencil3d=1, group="runtime_diagnostics")

save_initial_PF = c("PF","Vel")
save_initial    = c("g","h","PF")
save_iteration  = c("g","h","Vel","nw", "solid_boundary", "runtime_diagnostics", "wall_grad_diag", extra_save_iteration)
load_iteration  = c("g","h","Vel","nw", "solid_boundary", "runtime_diagnostics", "wall_grad_diag", extra_load_iteration)
load_phase      = c("g","h","Vel","nw", "solid_boundary", extra_load_phase)

if (Options$OutFlow){
	for (d in rows(DensityAll)) {
		AddField( name=d$name, dx=-d$dx-1, dy=-d$dy, dz=-d$dz )
		AddField( name=d$name, dx=-d$dx+1, dy=-d$dy, dz=-d$dz )
	}
	
	AddField(name="U",dx=c(-1,0,0))
	AddField(name="U",dx=c(1,0,0))

    save_initial   = c(save_initial,  "gold","hold")
    save_iteration = c(save_iteration,"gold","hold")
    load_iteration = c(load_iteration,"gold","hold")
    load_phase     = c(load_phase,    "gold","hold")
}

if (Options$geometric){
    # Since phase field gradients for the geometric method are accessed in the
    # dynamic manner (different nodes access different gradients in non static way)
    # we need to disable static optimisation to preserve performance
    AddField("gradPhiVal_x", stencil3d=2, group="gradPhi", optimise_for_static_access = FALSE)
    AddField("gradPhiVal_y", stencil3d=2, group="gradPhi", optimise_for_static_access = FALSE)
    AddField("gradPhiVal_z", stencil3d=2, group="gradPhi", optimise_for_static_access = FALSE)
    # Fake field, to simply copy field values to PhaseF instead
    # of accessing them directly from PhaseF field
    # this is needed for the cases when PhaseF needs to be accessed in the dynamic manner
    # otherwise the performance will drop significantly
    AddField('gradPhi_PhaseF', stencil3d=1, group="gradPhi", optimise_for_static_access = FALSE)

    AddField("PhaseF",stencil3d=2, group="PF")
} else {
    AddField("PhaseF",stencil3d=1, group="PF")
}

if (Options$thermo){
    source("thermocapillary.R")

    save_initial_PF = c(save_initial_PF,"Thermal")
    save_iteration  = c(save_iteration, "Thermal")
    load_iteration  = c(load_iteration, "Thermal")
}

######################
########STAGES########
######################
# Remember stages must be added after fields/densities!
	AddStage("PhaseInit", "Init", save=Fields$group %in% save_initial_PF)
	AddStage("BaseInit" , "Init_distributions", save=Fields$group %in% save_initial)
	AddStage("calcPhase", "calcPhaseF", save=Fields$name %in% c("PhaseF", "ReplayPhaseFromH"), load=DensityAll$group %in% load_phase)
	AddStage("BaseIter" , "Run", save=Fields$group %in% save_iteration, load=DensityAll$group %in% load_iteration )
	AddStage(name="InitFromFieldsStage", load=DensityAll$group %in% "init",read=FALSE, save=Fields$group %in% save_initial_PF)
	# STAGES FOR VARIOUS OPTIONS
	if (Options$geometric){
		AddStage("WallInit_CA"  , "Init_wallNorm", save=Fields$group %in% c("nw", "solid_boundary", extra_fields_to_load_for_bc))
		AddStage("calcWall_CA"  , "calcWallPhase", save=Fields$name %in% stage13_wall_phase_save_fields, load=DensityAll$group %in% c("nw", "gradPhi", "PF", "solid_boundary", extra_fields_to_load_for_bc))

		AddStage('calcPhaseGrad', "calcPhaseGrad", load=DensityAll$group %in% c("nw", "PF", "solid_boundary"), save=Fields$group=="gradPhi")
		AddStage('calcPhaseGrad_init', "calcPhaseGrad_init", load=DensityAll$group %in% c("nw", "PF", "solid_boundary"), save=Fields$group=="gradPhi")
		AddStage("calcWallPhase_correction", "calcWallPhase_correction", save=Fields$name %in% stage13_wall_phase_save_fields, load=DensityAll$group %in% c("nw", "PF", "solid_boundary"))
	} else {
		AddStage("WallInit" , "Init_wallNorm", save=Fields$group %in% c("nw", "solid_boundary", extra_fields_to_load_for_bc))
		AddStage("calcWall" , "calcWallPhase", save=Fields$name %in% stage13_wall_phase_save_fields, load=DensityAll$group %in% c("nw", "solid_boundary", extra_fields_to_load_for_bc))
		AddStage("calcWallPhase_correction", "calcWallPhase_correction", save=Fields$name %in% stage13_wall_phase_save_fields, load=DensityAll$group %in% c("nw", "PF", "solid_boundary"))
	}
	if (Options$thermo){
		AddStage("CopyDistributions", "TempCopy",  save=Fields$group %in% c("g","h","Vel","nw", "PF","Thermal"))
		AddStage("CopyThermal","ThermalCopy", save=Fields$name %in% c("Temp","Cond","SurfaceTension"), load=DensityAll$name %in% c("Temp","Cond","SurfaceTension"))
		AddStage("RK_1", "TempUpdate1", save=Fields$name=="RK1", load=DensityAll$name %in% c("U","V","W","Cond","PhaseF","Temp"))
		AddStage("RK_2", "TempUpdate2", save=Fields$name=="RK2", load=DensityAll$name %in% c("U","V","W","RK1","Cond","PhaseF","Temp"))
		AddStage("RK_3", "TempUpdate3", save=Fields$name=="RK3", load=DensityAll$name %in% c("U","V","W","RK1","RK2","Cond","PhaseF","Temp"))
		AddStage("RK_4", "TempUpdate4", save=Fields$name %in% c("Temp","SurfaceTension"), load=DensityAll$name %in% c("U","V","W","RK1","RK2","RK3","Cond","PhaseF","Temp"))

		AddStage("NonLocalTemp","BoundUpdate", save=Fields$name %in% c("Temp","SurfaceTension"), load=DensityAll$name %in% c("Temp"))
	}

#######################
########ACTIONS########
#######################
	if (Options$thermo){	
		AddAction("TempToSteadyState", c("CopyDistributions","RK_1", "RK_2", "RK_3", "RK_4","NonLocalTemp"))
		AddAction("Iteration", c("BaseIter", "calcPhase", "calcWall","RK_1", "RK_2", "RK_3", "RK_4","NonLocalTemp"))
		AddAction("IterationConstantTemp", c("BaseIter", "calcPhase", "calcWall","CopyThermal"))
		AddAction("Init"     , c("PhaseInit","WallInit" , "calcWall","BaseInit"))
	} else if (Options$geometric) {
        calcGrad <- if (Options$isograd)  "calcPhaseGrad" else "calcPhaseGrad_init"
        AddAction("Iteration", c("BaseIter", "calcPhase",  calcGrad, "calcWall_CA", "calcWallPhase_correction"))
	    AddAction("Init"     , c("PhaseInit","WallInit_CA" , "calcPhaseGrad_init"  , "calcWall_CA", "calcWallPhase_correction", "BaseInit"))
	    AddAction("InitFields"     , c("InitFromFieldsStage","WallInit_CA" , "calcPhaseGrad_init", "calcWall_CA", "calcWallPhase_correction", "BaseInit"))
    } else {
		AddAction("Iteration", c("BaseIter", "calcPhase", "calcWall", "calcWallPhase_correction"))
		AddAction("Init"     , c("PhaseInit","WallInit" , "calcWall","calcWallPhase_correction", "BaseInit"))
		AddAction("InitFields", c("InitFromFieldsStage","WallInit" , "calcWall", "calcWallPhase_correction", "BaseInit"))
	}
#######################
########OUTPUTS########
#######################
	AddQuantity(name="Rho",unit="kg/m3")
	AddQuantity(name="PhaseField",unit="1")
	AddQuantity(name="U",	  unit="m/s",vector=T)
	AddQuantity(name="P",	  unit="Pa")
	AddQuantity(name="Pstar", unit="1")
	AddQuantity(name="Normal", unit=1, vector=T)
    AddQuantity(name="IsItBoundary", unit="1")
	if (Options$geometric){
		AddQuantity(name="GradPhi", unit=1, vector=T)
	}
	if (Options$staircaseimp) {
		AddQuantity(name="ActualNormal", unit=1, vector=T)
	}
	# Stage9 analytic-geometry wetting BC diagnostics
	AddQuantity(name="WallGhost", unit=1)
	AddQuantity(name="WallGhostRaw", unit=1)
	AddQuantity(name="WallGhostClamped", unit=1)
	AddQuantity(name="WallGhostClampHit", unit=1)
	AddQuantity(name="WettingPathId", unit=1)
	AddQuantity(name="LocalRadAngle", unit=1)
	AddQuantity(name="WallH", unit=1)
	AddQuantity(name="AnalyticWallNormal", unit=1, vector=T)
	AddQuantity(name="AnalyticFlag", unit=1)
	AddQuantity(name="WallCSQMode", unit=1)
	AddQuantity(name="WallCSQNormalMode", unit=1)
	AddQuantity(name="WallCSQValid", unit=1)
	AddQuantity(name="WallCSQThetaDeg", unit=1)
	AddQuantity(name="WallCSQNormalX", unit=1)
	AddQuantity(name="WallCSQNormalY", unit=1)
	AddQuantity(name="WallCSQNormalZ", unit=1)
	AddQuantity(name="WallCSQDs", unit=1)
	AddQuantity(name="WallCSQDf", unit=1)
	AddQuantity(name="WallCSQQf", unit=1)
	AddQuantity(name="WallCSQQsRaw", unit=1)
	AddQuantity(name="WallCSQQsBounded", unit=1)
	AddQuantity(name="WallCSQQw", unit=1)
	AddQuantity(name="WallCSQResidual", unit=1)
	AddQuantity(name="WallCSQAppliedResidual", unit=1)
	AddQuantity(name="WallCSQDiscriminant", unit=1)
	AddQuantity(name="WallCSQRootChoice", unit=1)
	AddQuantity(name="WallCSQStencilCase", unit=1)
	AddQuantity(name="WallCSQStencilL", unit=1)
	AddQuantity(name="WallCSQFallbackReason", unit=1)
	AddQuantity(name="WallCSQBoundedDelta", unit=1)
	AddQuantity(name="WallCSQAppliedWeight", unit=1)
	AddQuantity(name="WallCSQWriteAllowedFlag", unit=1)
	AddQuantity(name="WallCSQCandidateCount", unit=1)
	AddQuantity(name="WallCSQFluidVertexCount", unit=1)
	AddQuantity(name="WallCSQTriangleInside", unit=1)
	AddQuantity(name="WallCSQPlaneId", unit=1)
	AddQuantity(name="WallCSQBaryMin", unit=1)
	AddQuantity(name="WallCSQBaryMax", unit=1)
	AddQuantity(name="WallCSQMethodComplete", unit=1)
	AddQuantity(name="WallCSQVertexMaskBits", unit=1)
	AddQuantity(name="WallCSQVertexRealFluidBits", unit=1)
	AddQuantity(name="WallCSQVertexPhaseCleanBits", unit=1)
	AddQuantity(name="WallCSQVertexQMin", unit=1)
	AddQuantity(name="WallCSQVertexQMax", unit=1)
	AddQuantity(name="WallCSQRejectedSolidVertexCount", unit=1)
	AddQuantity(name="WallCSQRejectedSentinelCount", unit=1)
	AddQuantity(name="WallCSQStrictWriteReady", unit=1)
	AddQuantity(name="ForceIterResidual", unit=1)
	AddQuantity(name="ForceIterCount", unit=1)
	AddQuantity(name="MassCorrectionApplied", unit=1)
	AddQuantity(name="PhaseStencilGhostUseCount", unit=1)
	AddQuantity(name="PhaseStencilFallbackCount", unit=1)
	AddQuantity(name="PhaseStencilMidpointFallbackCount", unit=1)
	AddQuantity(name="ReplayPhaseConsumed", unit=1)
	AddQuantity(name="ReplayPhaseFromH", unit=1)
	AddQuantity(name="ReplayLapPhi", unit=1)
	AddQuantity(name="ReplayMu", unit=1)
	AddQuantity(name="ReplayGradPhi", unit=1, vector=T)
	AddQuantity(name="ReplayFsurf", unit=1, vector=T)
	AddQuantity(name="ReplayFpressure", unit=1, vector=T)
	AddQuantity(name="ReplayFbody", unit=1, vector=T)
	AddQuantity(name="ReplayFmu", unit=1, vector=T)
	AddQuantity(name="ReplayFtotal", unit=1, vector=T)
	AddQuantity(name="ReplayRho", unit=1)
	AddQuantity(name="ReplayTau", unit=1)
	AddQuantity(name="ReplayPressureMoment", unit=1)
	AddQuantity(name="ReplayUPreForce", unit=1, vector=T)
	AddQuantity(name="ReplayUPostForce", unit=1, vector=T)
	AddQuantity(name="ReplayPhaseAdvVelocity", unit=1, vector=T)
	AddQuantity(name="ReplayForceOverRho", unit=1, vector=T)
	AddQuantity(name="ReplayFmuIter1", unit=1, vector=T)
	AddQuantity(name="ReplayFtotalIter1", unit=1, vector=T)
	AddQuantity(name="ReplayUPostIter1", unit=1, vector=T)
	AddQuantity(name="ReplayNormal", unit=1, vector=T)
	AddQuantity(name="ReplayStressXX", unit=1)
	AddQuantity(name="ReplayStressXY", unit=1)
	AddQuantity(name="ReplayStressXZ", unit=1)
	AddQuantity(name="ReplayStressYY", unit=1)
	AddQuantity(name="ReplayStressYZ", unit=1)
	AddQuantity(name="ReplayStressZZ", unit=1)
	AddQuantity(name="ReplayFphiSum", unit=1)
	AddQuantity(name="ReplayFphiMaxAbs", unit=1)
	AddQuantity(name="ReplayTmp1", unit=1)
	AddQuantity(name="ReplayM0", unit=1, vector=T)
	AddQuantity(name="ReplayVelocityHalfForce", unit=1, vector=T)
	AddQuantity(name="ReplayMF", unit=1, vector=T)
	AddQuantity(name="ReplayMomentumAfterG", unit=1, vector=T)
	AddQuantity(name="ReplayMomentumDeltaG", unit=1, vector=T)
	AddQuantity(name="ReplayPressureInput", unit=1)
	AddQuantity(name="ReplayPressureForceScale", unit=1)
	AddQuantity(name="ReplayPressurePhysicalInput", unit=1)
	AddQuantity(name="ReplayFpressureNoThird", unit=1, vector=T)
	AddQuantity(name="ReplayFpressurePhysical", unit=1, vector=T)
	AddQuantity(name="ReplayStressInputXX", unit=1)
	AddQuantity(name="ReplayStressInputXY", unit=1)
	AddQuantity(name="ReplayStressInputXZ", unit=1)
	AddQuantity(name="ReplayStressInputYY", unit=1)
	AddQuantity(name="ReplayStressInputYZ", unit=1)
	AddQuantity(name="ReplayStressInputZZ", unit=1)
	AddQuantity(name="ReplayStressIter1XX", unit=1)
	AddQuantity(name="ReplayStressIter1XY", unit=1)
	AddQuantity(name="ReplayStressIter1XZ", unit=1)
	AddQuantity(name="ReplayStressIter1YY", unit=1)
	AddQuantity(name="ReplayStressIter1YZ", unit=1)
	AddQuantity(name="ReplayStressIter1ZZ", unit=1)
	AddQuantity(name="ReplayFmuRaw", unit=1, vector=T)
	AddQuantity(name="ReplayFmuDelta", unit=1, vector=T)
	AddQuantity(name="ReplayTauUsed", unit=1)
	AddQuantity(name="ReplayRhoForForce", unit=1)
	AddQuantity(name="ReplayForceInjectionMode", unit=1)
	AddQuantity(name="ReplayPressureClosureMode", unit=1)
	AddQuantity(name="ReplayForceDensityClosureMode", unit=1)
	AddQuantity(name="ReplayForceFixedPointMode", unit=1)
	AddQuantity(name="ReplayForceRhoRaw", unit=1)
	AddQuantity(name="ReplayForceRhoEffective", unit=1)
	AddQuantity(name="WallGradDeltaMag", unit=1)
	AddQuantity(name="WallGradThetaApp", unit=1)
	AddQuantity(name="WallMuCandidate", unit=1)
	# Layer3 DynamicCL shadow diagnostics (Stage 15B)
	AddQuantity(name="DynamicCLActive", unit=1)
	AddQuantity(name="DynamicCLIndicator", unit=1)
	AddQuantity(name="DynamicCLCosApp", unit=1)
	AddQuantity(name="DynamicCLThetaApp", unit=1)
	AddQuantity(name="DynamicCLCosEq", unit=1)
	AddQuantity(name="DynamicCLCosResidual", unit=1)
	AddQuantity(name="DynamicCLForceCandidateX", unit=1)
	AddQuantity(name="DynamicCLForceCandidateY", unit=1)
	AddQuantity(name="DynamicCLForceCandidateZ", unit=1)
	AddQuantity(name="DynamicCLForceCandidateMag", unit=1)
	AddQuantity(name="DynamicCLTangentialX", unit=1)
	AddQuantity(name="DynamicCLTangentialY", unit=1)
	AddQuantity(name="DynamicCLTangentialZ", unit=1)
	AddQuantity(name="DynamicCLWallNormalX", unit=1)
	AddQuantity(name="DynamicCLWallNormalY", unit=1)
	AddQuantity(name="DynamicCLWallNormalZ", unit=1)
	AddQuantity(name="DynamicCLRejectedReason", unit=1)
	AddQuantity(name="DynamicCLThetaEq", unit=1)
	AddQuantity(name="DynamicCLWallContextFound", unit=1)
	AddQuantity(name="DynamicCLBlockedReason", unit=1)
	AddQuantity(name="DynamicCLWallDx", unit=1)
	AddQuantity(name="DynamicCLWallDy", unit=1)
	AddQuantity(name="DynamicCLWallDz", unit=1)
###################################
########INPUTS - PHASEFIELD########
###################################
	AddSetting(name="Density_h", comment='High density')
	AddSetting(name="Density_l", comment='Low  density')
	AddSetting(name="PhaseField_h", default=1, comment='PhaseField in Liquid')
	AddSetting(name="PhaseField_l", default=0, comment='PhaseField gas')
	AddSetting(name="PhaseField", 	   comment='Initial PhaseField distribution', zonal=T)
	AddSetting(name="IntWidth", default=4,    comment='Anti-diffusivity coeff')
	AddSetting(name="omega_phi", comment='one over relaxation time (phase field)')
	AddSetting(name="M", omega_phi='1.0/(3*M+0.5)', default=0.02, comment='Mobility')
	AddSetting(name="sigma", comment='surface tension')
	AddSetting(name="force_fixed_iterator", default=2, comment='to resolve implicit relation of viscous force')
	AddSetting(name="ForceFixedTol", default=0.0, comment='Stage13 force fixed-point residual tolerance; <=0 preserves fixed-count iteration')
	AddSetting(name="ForceFixedMaxIter", default=2, comment='Stage13 force fixed-point maximum iterations used when ForceFixedTol>0')
	AddSetting(name="ReplayDiagnosticsMode", default=0, comment='S1/S2 output-only replay diagnostics: 0 zeroed, 1 write collision intermediate fields')
	AddSetting(name="PhaseValidityEps", default=1e-3, comment='Stage14/S2: tolerance for accepting PhaseF/WallGhost as physical stencil input')
	AddSetting(name="PhaseAdvectionVelocityMode", default=0, comment='Stage14 diagnostic: 0 legacy h-equilibrium uses post-force velocity, 1 MRT h-equilibrium uses pre-force m0 velocity')
	AddSetting(name="MomentumForceMode", default=0, comment='Stage14 diagnostic: 0 legacy, 1 omit F_mu, 2 omit F_pressure, 3 omit F_surf, 4 no momentum force, 5 surface-only momentum force')
	AddSetting(name="MomentumClosureDiagnosticsMode", default=0, comment='Stage14 output-only MRT momentum closure diagnostics: 0 off, 1 write m0/half-force/mF/g-after fields')
	AddSetting(name="MomentumClosureProbeMode", default=0, comment='Stage14 diagnostic MRT force-insertion probe: 0/1 legacy, 2 no-half-force g-equilibrium, 3 no mF injection, 4 half mF injection')
	AddSetting(name="PressureClosureMode", default=0, comment='Stage14 diagnostic pressure input mode: 0 legacy p=m0[0], 1 p*rho*cs2 in calc_Fp, 2 p-PressureClosureReference')
	AddSetting(name="PressureClosureReference", default=0.0, comment='Stage14 diagnostic pressure reference used only when PressureClosureMode=2')
	AddSetting(name="ForceDensityClosureMode", default=0, comment='Stage14 diagnostic F/rho denominator mode: 0 legacy rho(C), 1 floor denominator by ForceDensityRhoFloor or Density_l')
	AddSetting(name="ForceDensityRhoFloor", default=0.0, comment='Stage14 diagnostic rho floor for ForceDensityClosureMode=1; <=0 uses Density_l')
	AddSetting(name="ForceFixedPointMode", default=0, comment='Stage14 diagnostic fixed-point mode: 0 legacy count/tol behavior, 1 residual gate with divergence guard, 2 single-pass')
	AddSetting(name="ForceFixedDivergenceGuardFactor", default=100.0, comment='Stage14 diagnostic ForceFixedPointMode=1 guard; stop before accepting a pass whose residual exceeds this factor')
  	AddSetting(name="Washburn_start", default="0", comment='Start of washburn gas phase')
  	AddSetting(name="Washburn_end", default="0", comment='End of washburn gas phase')
	AddSetting(name="radAngle", default='1.570796', comment='Contact angle in radians, can use units -> 90d where d=2pi/360', zonal=T)
	AddSetting(name="minGradient", default='1e-8', comment='if the phase gradient is less than this, set phase normals to zero')
	##STAGE9 ANALYTIC-GEOMETRY WETTING BC
	#   When AnalyticWetting > 0.5, wall nodes whose zone declares an analytic
	#   solid use the analytic wall normal and signed distance instead of the
	#   lattice-recovered normal. This is the physically correct path for
	#   plane/cylinder/sphere. The lattice path is unchanged for nodes/zones
	#   without an analytic geometry, so unmodified cases behave identically.
	AddSetting(name="AnalyticWetting", default=0, comment='Stage9: 1 enables analytic-geometry wetting BC on analytic zones')
	AddSetting(name="AnalyticSolidType", default=0, comment='Stage9: 0 off, 1 plane, 2 infinite cylinder, 3 sphere')
	AddSetting(name="AnalyticSolidCenterX", default=0.0, comment='Stage9: solid center x (cylinder/sphere)')
	AddSetting(name="AnalyticSolidCenterY", default=0.0, comment='Stage9: solid center y (cylinder/sphere)')
	AddSetting(name="AnalyticSolidCenterZ", default=0.0, comment='Stage9: solid center z (cylinder/sphere)')
	AddSetting(name="AnalyticSolidRadius", default=0.0, comment='Stage9: solid radius (cylinder/sphere)')
	AddSetting(name="AnalyticSolidAxis", default=2, comment='Stage9: plane normal / cylinder axis: 0=x, 1=y, 2=z')
	AddSetting(name="AnalyticSolidPlaneOffset", default=0.0, comment='Stage9: plane offset along axis (plane only)')
	AddSetting(name="WettingBCMode", default=0, comment='Stage13 analytic wetting BC mode: 0 legacy Briant/Jacqmin, 1 geometric tangent/curvature diagnostic')
	AddSetting(name="WallCompactStencilMode", default=0, comment='Stage13 compact-stencil wetting mode: 0 off, 1 shadow only, 2 write after gate')
	AddSetting(name="WallCompactStencilNormalMode", default=1, comment='Stage13 compact-stencil normal mode: only 1 analytic signed-distance normal is implemented; other modes reject compact writes')
	AddSetting(name="WallCompactStencilMaxL", default=3, comment='Stage13 compact-stencil seven-plane local search radius for shadow diagnostics')
	AddSetting(name="WallCompactStencilThetaEps", default=1e-6, comment='Stage13 compact-stencil neutral-angle epsilon in radians')
	AddSetting(name="WallCompactStencilBoundEps", default=0.0, comment='Stage13 compact-stencil q bound tolerance; strict write keeps q_s inside physical [0,1]')
	AddSetting(name="WallCompactStencilMaxBoundedDelta", default=1e-8, comment='Stage13 compact-stencil write gate: max allowed |q_s_bounded-q_s_raw|')
	AddSetting(name="WallCompactStencilAppliedResidualTol", default=1e-8, comment='Stage13 compact-stencil write gate: max residual after applying bounded q_s')
	AddSetting(name="WallCompactStencilWriteAllowedFlag", default=0, comment='Stage13 hard gate: compact-stencil writes are blocked unless explicitly enabled')
	AddSetting(name="PhaseEquationMode", default=0, comment='Stage13 reserved: 0 legacy phase equation; mass correction inactive until Stage E')
	##LAYER 1-2 CONTACT LINE DRIVE (Wang 2025 / Ju 2024)
	AddSetting(name="WallGradMode", default=0, comment='Layer1 Wang corrected gradient: 0 off, 1 shadow, 2 write')
	AddSetting(name="WallGradContactSign", default=1.0, comment='Layer1: contact angle sign +1 or -1')
	AddSetting(name="WallGradCapFactor", default=2.0, comment='Layer1: corrected gradient magnitude cap factor')
	AddSetting(name="WallGradContactLineEps", default=0.02, comment='Layer1: skip nodes where q<eps or q>1-eps')
	AddSetting(name="WallMuMode", default=0, comment='Layer2 Ju wall-mu source: 0 off, 1 shadow, 2 write')
	AddSetting(name="WallMuScale", default=1.0, comment='Layer2: mu_wall scaling factor')
	AddSetting(name="WallMuContactLineEps", default=0.02, comment='Layer2: skip nodes where q<eps or q>1-eps')
	# Layer3 DynamicCL residual contact-line force (Stage 15B shadow / 15C write)
	# Residual R_theta = cos(theta_eq) - cos(theta_app), added to F_total.
	# Vanishes at equilibrium by construction (theta_app -> theta_eq).
	# 15B: DynamicCLMode<=1 shadow only (diagnostics, never adds to F_total).
	# 15C: DynamicCLMode>=2 write (reserved; runner refuses until 15C).
	AddSetting(name="DynamicCLMode", default=0, comment='Layer3 DynamicCL: 0 off, 1 shadow diagnostics, 2 add residual CL force (reserved 15C)')
	AddSetting(name="DynamicCLCoeff", default=0.0, comment='Layer3: residual contact-line force coefficient')
	AddSetting(name="DynamicCLForceCap", default=0.02, comment='Layer3: force cap in units of sigma/IntWidth')
	AddSetting(name="DynamicCLEpsQ", default=0.05, comment='Layer3: contact-line band cutoff eps<q<1-eps')
	AddSetting(name="DynamicCLGradMin", default=1e-10, comment='Layer3: minimum |gradPhi| for theta_app')
	AddSetting(name="DynamicCLCosTol", default=1e-3, comment='Layer3: no candidate force below this |cos_eq-cos_app|')
	AddSetting(name="DynamicCLCosSign", default=1.0, comment='Layer3: sign convention for cos_app, calibrated by equilibrium 30/90/150')
	AddSetting(name="DynamicCLForceSign", default=1.0, comment='Layer3: global force direction sign, calibrated by decoupled footprint')
	##SPECIAL INITIALISATIONS
	# RTI
		AddSetting(name="RTI_Characteristic_Length", default=-999, comment='Use for RTI instability')
	    AddSetting(name="pseudo2D", default="0", comment="if 1, assume model is pseduo2D")
    # Single droplet/bubble
		AddSetting(name="Radius", default=0.0, comment='Diffuse Sphere Radius')
		AddSetting(name="CenterX", default=0.0, comment='Diffuse sphere center_x')
		AddSetting(name="CenterY", default=0.0, comment='Diffuse sphere center_y')
		AddSetting(name="CenterZ", default=0.0, comment='Diffuse sphere center_z')
		AddSetting(name="BubbleType",default=1.0, comment='droplet(1.0) or bubble(-1.0)?!')
		AddSetting(name="CapInit", default=0.0, comment='Default-off spherical-cap initializer for flat-wall static contact-angle diagnostics')
		AddSetting(name="CapInitRadius", default=0.0, comment='Spherical cap parent-sphere radius')
		AddSetting(name="CapInitTheta", default='1.570796', comment='Spherical cap target contact angle in radians; metadata only')
		AddSetting(name="CapInitCenterX", default=0.0, comment='Spherical cap parent-sphere center X')
		AddSetting(name="CapInitCenterY", default=0.0, comment='Spherical cap parent-sphere center Y')
		AddSetting(name="CapInitCenterZ", default=0.0, comment='Spherical cap parent-sphere center Z')
		AddSetting(name="SphereCapInit", default=0.0, comment='Default-off cap-on-sphere initializer for static curved-wall diagnostics')
		AddSetting(name="SphereCapInitParentRadius", default=0.0, comment='Sphere-cap liquid parent-sphere radius')
		AddSetting(name="SphereCapInitCenterX", default=0.0, comment='Sphere-cap liquid parent-sphere center X')
		AddSetting(name="SphereCapInitCenterY", default=0.0, comment='Sphere-cap liquid parent-sphere center Y')
		AddSetting(name="SphereCapInitCenterZ", default=0.0, comment='Sphere-cap liquid parent-sphere center Z')
		AddSetting(name="SphereCapInitSolidCenterX", default=0.0, comment='Sphere-cap solid sphere center X')
		AddSetting(name="SphereCapInitSolidCenterY", default=0.0, comment='Sphere-cap solid sphere center Y')
		AddSetting(name="SphereCapInitSolidCenterZ", default=0.0, comment='Sphere-cap solid sphere center Z')
		AddSetting(name="SphereCapInitSolidRadius", default=0.0, comment='Sphere-cap solid sphere radius')
		AddSetting(name="CylinderCapInit", default=0.0, comment='Default-off cap-on-cylinder initializer for static curved-wall diagnostics')
		AddSetting(name="CylinderCapInitParentRadius", default=0.0, comment='Cylinder-cap liquid parent-sphere radius')
		AddSetting(name="CylinderCapInitCenterX", default=0.0, comment='Cylinder-cap liquid parent-sphere center X')
		AddSetting(name="CylinderCapInitCenterY", default=0.0, comment='Cylinder-cap liquid parent-sphere center Y')
		AddSetting(name="CylinderCapInitCenterZ", default=0.0, comment='Cylinder-cap liquid parent-sphere center Z')
		AddSetting(name="CylinderCapInitSolidCenterX", default=0.0, comment='Cylinder-cap solid cylinder center X')
		AddSetting(name="CylinderCapInitSolidCenterY", default=0.0, comment='Cylinder-cap solid cylinder center Y')
		AddSetting(name="CylinderCapInitSolidCenterZ", default=0.0, comment='Cylinder-cap solid cylinder center Z')
		AddSetting(name="CylinderCapInitSolidRadius", default=0.0, comment='Cylinder-cap solid cylinder radius')
		AddSetting(name="CylinderCapInitSolidAxis", default=0, comment='Cylinder-cap solid cylinder axis: 0=x, 1=y, 2=z')
		AddSetting(name="CompositeDropletTailRadius", default=0.0, comment='optional top cylinder tail radius for a volume-conserved sphere-plus-tail droplet')
		AddSetting(name="CompositeDropletTailLength", default=0.0, comment='optional top cylinder tail length along +Z')
		AddSetting(name="CompositeDropletBodyRadius", default=0.0, comment='optional solved body radius override; <=0 solves volume-conserved radius from Radius')
	# Annular Taylor bubble
		AddSetting(name="DonutTime", default=0.0, comment='Radius of a Torus - initialised to travel along x-axis')
		AddSetting(name="Donut_h",   default=0.0, comment='Half donut thickness, i.e. the radius of the cross-section')
		AddSetting(name="Donut_D",   default=0.0, comment='Dilation factor along the x-axis')
		AddSetting(name="Donut_x0",  default=0.0, comment='Position along x-axis')
	# Poiseuille flow in 2D channel (flow in x direction)
		AddSetting("HEIGHT", default=0,	comment="Height of channel for 2D Poiseuille flow")
		AddSetting("Uavg", default=0,	zonal=T, comment="Average velocity of channel for 2D Poiseuille flow")
		AddSetting("developedFlow", default=0,	comment="set greater than 0 for fully developed flow in the domain (x-direction)")
		AddSetting("developedPipeFlow", default=0,	comment="set greater than 0 for fully developed pipe flow in the inlets")
		AddSetting("developedPipeFlow_X", default=0,comment="set greater than 0 for fully developed pipe flow in the domain (x-direction-only)")
        AddSetting("pipeRadius", default=0, comment="radius of pipe for developed pipe flow")
        AddSetting("pipeCentre_Y", default=0, comment="pipe centre Y co-ord for developed pipe flow")
        AddSetting("pipeCentre_Z", default=0, comment="pipe centre Z co-ord for developed pipe flow")
##############################
########INPUTS - FLUID########
##############################
	AddSetting(name="tau_l", comment='relaxation time (low density fluid)')
	AddSetting(name="tau_h", comment='relaxation time (high density fluid)')
    AddSetting(name="tauUpdate", default="1", comment="Interpolation: 1-linear, 2- inverse, 3- dyn viscosity")
	AddSetting(name="Viscosity_l", tau_l='(3*Viscosity_l)', default=0.16666666, comment='kinematic viscosity')
	AddSetting(name="Viscosity_h", tau_h='(3*Viscosity_h)', default=0.16666666, comment='kinematic viscosity')
	AddSetting(name="VelocityX", default=0.0, comment='inlet/outlet/init velocity', zonal=T)
	AddSetting(name="VelocityY", default=0.0, comment='inlet/outlet/init velocity', zonal=T)
	AddSetting(name="VelocityZ", default=0.0, comment='inlet/outlet/init velocity', zonal=T)
	AddSetting(name="DropletOnlyVelocity", default=0.0, comment='0 off, 1 hard droplet mask, 2 smooth phase-fraction weighted droplet velocity')
	AddSetting(name="DropletVelocityX", default=0.0, comment='droplet-only initial velocity x')
	AddSetting(name="DropletVelocityY", default=0.0, comment='droplet-only initial velocity y')
	AddSetting(name="DropletVelocityZ", default=0.0, comment='droplet-only initial velocity z')
	AddSetting(name="CompositeDropletTailVelocityMode", default=0.0, comment='0 off, 1 smooth uniform tail velocity, 2 smooth axial ramp tail velocity')
	AddSetting(name="CompositeDropletTailVelocityX", default=0.0, comment='optional extra tail velocity x')
	AddSetting(name="CompositeDropletTailVelocityY", default=0.0, comment='optional extra tail velocity y')
	AddSetting(name="CompositeDropletTailVelocityZ", default=0.0, comment='optional extra tail velocity z')
	AddSetting(name="Pressure" , default=0.0, comment='inlet/outlet/init density', zonal=T)
	AddSetting(name="GravitationX", default=0.0, comment='applied (rho)*GravitationX')
	AddSetting(name="GravitationY", default=0.0, comment='applied (rho)*GravitationY')
	AddSetting(name="GravitationZ", default=0.0, comment='applied (rho)*GravitationZ')
	AddSetting(name="BuoyancyX", default=0.0, comment='applied (rho_h-rho)*BuoyancyX')
	AddSetting(name="BuoyancyY", default=0.0, comment='applied (rho_h-rho)*BuoyancyY')
	AddSetting(name="BuoyancyZ", default=0.0, comment='applied (rho_h-rho)*BuoyancyZ')
##################################
########TRACKING VARIABLES########
##################################
	AddSetting(name="xyzTrack", default=1,comment='x<-1, y<-2, z<-3')
	AddNodeType("Centerline",group="ADDITIONALS")
	AddNodeType(name="Spiketrack", group="ADDITIONALS")
	AddNodeType(name="Saddletrack", group="ADDITIONALS")
	AddNodeType(name="Bubbletrack", group="ADDITIONALS")
	AddGlobal("InterfacePosition", op="MAX", comment='trackPosition')
    AddGlobal("InterfaceYTop", op="MAX", comment="Track top position of the interface in Y direction")
	AddGlobal("Vfront",comment='velocity infront of bubble')
	AddGlobal("Vback",comment='velocity behind bubble')
	AddGlobal("RTISpike", op="MAX", comment='SpikeTracker ')
	AddGlobal("RTIBubble",op="MAX", comment='BubbleTracker')
	AddGlobal("RTISaddle",op="MAX", comment='SaddleTracker')
	AddGlobal("XLocation", comment='tracking of x-centroid of the gas regions in domain', unit="m")
	AddGlobal(name="DropFront",	op="MAX",  comment='Highest location of droplet', unit="m")
##########################
########NODE TYPES########
##########################
	AddNodeType("Smoothing",group="ADDITIONALS")
	AddNodeType(name="flux_nodes", group="ADDITIONALS")
	dotR_my_velocity_boundaries = paste0(c("N","E","S","W","F","B"),"Velocity")
    dotR_my_pressure_boundaries = paste0(c("N","E","S","W","F","B"),"Pressure")
    for (ii in 1:6){
        AddNodeType(name=dotR_my_velocity_boundaries[ii], group="BOUNDARY")
        AddNodeType(name=dotR_my_pressure_boundaries[ii], group="BOUNDARY")
    }
	AddNodeType(name="MovingWall_N", group="BOUNDARY")
	AddNodeType(name="MovingWall_S", group="BOUNDARY")
	AddNodeType(name="Solid", group="BOUNDARY")
	AddNodeType(name="Wall", group="BOUNDARY")
	AddNodeType(name="BGK", group="COLLISION")
	AddNodeType(name="MRT", group="COLLISION")
	if (Options$OutFlow){
		AddNodeType(name="ENeumann", group="BOUNDARY")
		AddNodeType(name="WNeumann", group="BOUNDARY")
		AddNodeType(name="EConvect", group="BOUNDARY")
		AddNodeType(name="WConvect", group="BOUNDARY")
	}
#######################
########GLOBALS########
#######################
	AddGlobal(name="PressureLoss", comment='pressure loss', unit="1mPa")
	AddGlobal(name="OutletFlux", comment='pressure loss', unit="1m2/s")
	AddGlobal(name="InletFlux", comment='pressure loss', unit="1m2/s")
	AddGlobal(name="TotalDensity", comment='Mass conservation check', unit="1kg/m3")
	AddGlobal(name="KineticEnergy",comment='Measure of kinetic energy', unit="J")
	AddGlobal(name="GasTotalVelocity", comment='use to determine avg velocity of bubbles', unit="m/s")
	AddGlobal(name="GasTotalVelocityX", comment='use to determine avg velocity of bubbles', unit="m/s")
	AddGlobal(name="GasTotalVelocityY", comment='use to determine avg velocity of bubbles', unit="m/s")
	AddGlobal(name="GasTotalVelocityZ", comment='use to determine avg velocity of bubbles', unit="m/s")
	AddGlobal(name="GasTotalPhase",	   comment='use in line with GasTotalVelocity to determine average velocity', unit="1")
	AddGlobal(name="LiqTotalVelocity", 	comment='use to determine avg velocity of droplets', unit="m/s")
	AddGlobal(name="LiqTotalVelocityX", comment='use to determine avg velocity of droplets', unit="m/s")
	AddGlobal(name="LiqTotalVelocityY", comment='use to determine avg velocity of droplets', unit="m/s")
	AddGlobal(name="LiqTotalVelocityZ", comment='use to determine avg velocity of droplets', unit="m/s")
    AddGlobal(name="NumFluidCells", comment='Number of fluid cells')
    AddGlobal(name="NumSpecialPoints", comment='Number of special points')
    AddGlobal(name="NumWallBoundaryPoints", comment='Number of boundary nodes')
    AddGlobal(name="NumBoundaryPoints", comment='Number of boundary nodes')
	AddGlobal(name="LiqTotalPhase",	   		comment='use in line with LiqTotalVelocity to determine average velocity', unit="1")
	AddGlobal(name="FluxNodeCount",comment='nodes in flux region', unit="1")
	AddGlobal(name="FluxX",comment='flux in x direction for flux_nodes', unit="1")
	AddGlobal(name="FluxY",comment='flux in y direction for flux_nodes', unit="1")
	AddGlobal(name="FluxZ",comment='flux in z direction for flux_nodes', unit="1")
