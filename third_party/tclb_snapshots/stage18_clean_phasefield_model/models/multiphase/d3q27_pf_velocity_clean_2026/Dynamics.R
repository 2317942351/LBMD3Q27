# Stage18 clean phase-field model declarations.
#
# This file intentionally follows official TCLB model-development semantics:
# - streamed populations use AddDensity;
# - macroscopic, geometry, wetting, force, and diagnostics state use AddField;
# - every producer-consumer boundary is represented by an explicit AddStage.

source("lattice.R")

#####################################
######## INPUT / INITIAL DATA ########
#####################################

AddDensity(name="Init_UX_External", group="init", comment="initial/free-stream velocity x", parameter=TRUE, non.mandatory=TRUE)
AddDensity(name="Init_UY_External", group="init", comment="initial/free-stream velocity y", parameter=TRUE, non.mandatory=TRUE)
AddDensity(name="Init_UZ_External", group="init", comment="initial/free-stream velocity z", parameter=TRUE, non.mandatory=TRUE)
AddDensity(name="Init_PhaseField_External", group="init", dx=0, dy=0, dz=0, comment="initial phase field", parameter=TRUE, non.mandatory=TRUE)

########################################
######## NON-STREAMING STATE FIELDS ####
########################################

# Macroscopic phase and boundedness state.
AddField("PhaseF", stencil3d=2, group="PF")
AddField("PhaseFValid", group="PFState")
AddField("PhaseOutOfBoundsFlag", group="PFState")

# Macroscopic momentum/pressure state. These are fields, not zero-offset
# densities, because they are not physical streamed populations.
AddField("RhoField", group="Macro")
AddField("PressureMoment", group="Macro")
AddField("PhysicalPressure", group="Macro")
AddField("pnorm", group="Macro")
AddField("U", group="Macro")
AddField("V", group="Macro")
AddField("W", group="Macro")

# Geometry and wall state.
AddField("SolidIndicator", stencil3d=1, group="SolidGeom")
AddField("SignedDistance", stencil3d=1, group="SolidGeom")
AddField("SolidNormalX", stencil3d=1, group="SolidGeom")
AddField("SolidNormalY", stencil3d=1, group="SolidGeom")
AddField("SolidNormalZ", stencil3d=1, group="SolidGeom")
AddField("NearWallBand", stencil3d=1, group="SolidGeom")
AddField("SolidNeighborCount", stencil3d=1, group="SolidGeom")

# Legacy boundary metadata kept only as compatibility fields while old helper
# functions are retired. They are non-streaming fields in Stage18.
AddField("IsBoundary", stencil3d=2, group="solid_boundary")
AddField("IsSpecialBoundaryPoint", group="solid_boundary")
AddField("nw_x", stencil3d=1, group="nw")
AddField("nw_y", stencil3d=1, group="nw")
AddField("nw_z", stencil3d=1, group="nw")

# Gradients, Laplace, and chemical potential.
AddField("gradPhiVal_x", stencil3d=2, group="GradPhi", optimise_for_static_access=FALSE)
AddField("gradPhiVal_y", stencil3d=2, group="GradPhi", optimise_for_static_access=FALSE)
AddField("gradPhiVal_z", stencil3d=2, group="GradPhi", optimise_for_static_access=FALSE)
AddField("lapPhi", stencil3d=1, group="Mu")
AddField("mu", stencil3d=1, group="Mu")

# Wetting and passive wall source state.
AddField("WallPhase", stencil3d=1, group="Wetting")
AddField("WallPhaseValid", group="Wetting")
AddField("WallDistance", group="Wetting")
AddField("WallLinkMask", stencil3d=1, group="Wetting")
AddField("WallHOutgoingMass", group="WallSourceAudit")
AddField("WallHIncomingMass", group="WallSourceAudit")
AddField("WallHNetMass", group="WallSourceAudit")
AddField("WallHLinkWriteCount", group="WallSourceAudit")
AddField("WallHMassBefore", group="WallSourceAudit")
AddField("WallHMassAfter", group="WallSourceAudit")

# Phase-equation moment and boundedness audit. These fields are non-streaming;
# the physical phase state is still the streamed h population.
for (i in 0:(q_velocities - 1)) {
    AddField(name=paste0("HCur", i), group="HCache")
}
AddField("PhaseHPreSum", group="PhaseAudit")
AddField("PhaseHRawSum", group="PhaseAudit")
AddField("PhaseHRawMin", group="PhaseAudit")
AddField("PhaseHRawMax", group="PhaseAudit")
AddField("PhaseHRawNonfiniteCount", group="PhaseAudit")
AddField("PhaseHeqSum", group="PhaseAudit")
AddField("PhaseFphiSum", group="PhaseAudit")
AddField("PhaseFphiFirstMomentX", group="PhaseAudit")
AddField("PhaseFphiFirstMomentY", group="PhaseAudit")
AddField("PhaseFphiFirstMomentZ", group="PhaseAudit")
AddField("PhaseHPostSum", group="PhaseAudit")
AddField("PhaseCorrectionDelta", group="PhaseAudit")
AddField("PhaseMassRedistributionWeight", group="PhaseAudit")
AddField("PhaseGlobalCorrectionApplied", group="PhaseAudit")
AddField("PhasePopulationRepairApplied", group="PhaseAudit")

# Force state.
AddField("F_surf_x", group="Force")
AddField("F_surf_y", group="Force")
AddField("F_surf_z", group="Force")
AddField("F_pressure_x", group="Force")
AddField("F_pressure_y", group="Force")
AddField("F_pressure_z", group="Force")
AddField("F_mu_x", group="Force")
AddField("F_mu_y", group="Force")
AddField("F_mu_z", group="Force")
AddField("F_body_x", group="Force")
AddField("F_body_y", group="Force")
AddField("F_body_z", group="Force")
AddField("F_total_x", group="Force")
AddField("F_total_y", group="Force")
AddField("F_total_z", group="Force")
AddField("ForceOverRho", group="ForceAudit")
AddField("ForceInsertionAudit", group="ForceAudit")
AddField("ForceHalfVelocityX", group="ForceAudit")
AddField("ForceHalfVelocityY", group="ForceAudit")
AddField("ForceHalfVelocityZ", group="ForceAudit")
AddField("ForceMomentumBeforeX", group="ForceAudit")
AddField("ForceMomentumBeforeY", group="ForceAudit")
AddField("ForceMomentumBeforeZ", group="ForceAudit")
AddField("ForceMomentumAfterX", group="ForceAudit")
AddField("ForceMomentumAfterY", group="ForceAudit")
AddField("ForceMomentumAfterZ", group="ForceAudit")
AddField("ForceEquivalentInjectedX", group="ForceAudit")
AddField("ForceEquivalentInjectedY", group="ForceAudit")
AddField("ForceEquivalentInjectedZ", group="ForceAudit")
AddField("PressureInput", group="ForceAudit")
AddField("PressureReference", group="ForceAudit")
AddField("StressXX", group="StressAudit")
AddField("StressXY", group="StressAudit")
AddField("StressXZ", group="StressAudit")
AddField("StressYY", group="StressAudit")
AddField("StressYZ", group="StressAudit")
AddField("StressZZ", group="StressAudit")

# Slim diagnostics used in fast gates.
AddField("MassCorrectionApplied", group="Audit")
AddField("Stage18ContractViolation", group="Audit")

if (Options$OutFlow) {
    AddDensity(name=paste("gold", 0:26, sep=""), dx=0, dy=0, dz=0, group="gold")
    AddDensity(name=paste("hold", 0:(q_velocities-1), sep=""), dx=0, dy=0, dz=0, group="hold")
}

##############################
######## SETTINGS ############
##############################

AddSetting(name="Density_h", comment="high density")
AddSetting(name="Density_l", comment="low density")
AddSetting(name="PhaseField_h", default=1, comment="liquid/order-parameter high value")
AddSetting(name="PhaseField_l", default=0, comment="gas/order-parameter low value")
AddSetting(name="PhaseField", comment="initial phase-field distribution", zonal=TRUE)
AddSetting(name="IntWidth", default=4, comment="interface width")
AddSetting(name="omega_phi", comment="one over phase relaxation time")
AddSetting(name="M", omega_phi="1.0/(3*M+0.5)", default=0.02, comment="mobility")
AddSetting(name="sigma", default=0.01, comment="surface tension")
AddSetting(name="RhoFloor", default=1e-9, comment="minimum density for force/rho closure")
AddSetting(name="minGradient", default=1e-8, comment="minimum gradient magnitude for phase normal")

AddSetting(name="Radius", default=0.0, comment="initial droplet/bubble radius")
AddSetting(name="CenterX", default=0.0, comment="initial droplet center x")
AddSetting(name="CenterY", default=0.0, comment="initial droplet center y")
AddSetting(name="CenterZ", default=0.0, comment="initial droplet center z")
AddSetting(name="BubbleType", default=1.0, comment="droplet 1.0 or bubble -1.0")
AddSetting(name="CompositeDropletTailRadius", default=0.0, comment="legacy optional top cylinder tail radius")
AddSetting(name="CompositeDropletTailLength", default=0.0, comment="legacy optional top cylinder tail length")
AddSetting(name="CompositeDropletBodyRadius", default=0.0, comment="legacy optional solved body radius")
AddSetting(name="RTI_Characteristic_Length", default=-999, comment="legacy RTI initialization")
AddSetting(name="pseudo2D", default=0, comment="legacy pseudo-2D initialization")
AddSetting(name="Washburn_start", default=0, comment="legacy Washburn gas start")
AddSetting(name="Washburn_end", default=0, comment="legacy Washburn gas end")
AddSetting(name="DonutTime", default=0.0, comment="legacy torus radius")
AddSetting(name="Donut_h", default=0.0, comment="legacy torus half thickness")
AddSetting(name="Donut_D", default=0.0, comment="legacy torus dilation")
AddSetting(name="Donut_x0", default=0.0, comment="legacy torus x position")
AddSetting(name="HEIGHT", default=0, comment="legacy channel height")
AddSetting(name="Uavg", default=0, zonal=TRUE, comment="legacy average channel velocity")
AddSetting(name="developedFlow", default=0, comment="legacy developed channel flow")
AddSetting(name="developedPipeFlow", default=0, comment="legacy developed pipe flow")
AddSetting(name="developedPipeFlow_X", default=0, comment="legacy developed pipe flow in x")
AddSetting(name="pipeRadius", default=0, comment="legacy pipe radius")
AddSetting(name="pipeCentre_Y", default=0, comment="legacy pipe center y")
AddSetting(name="pipeCentre_Z", default=0, comment="legacy pipe center z")

AddSetting(name="VelocityX", default=0.0, comment="initial/inlet velocity x", zonal=TRUE)
AddSetting(name="VelocityY", default=0.0, comment="initial/inlet velocity y", zonal=TRUE)
AddSetting(name="VelocityZ", default=0.0, comment="initial/inlet velocity z", zonal=TRUE)
AddSetting(name="DropletOnlyVelocity", default=0.0, comment="legacy droplet-only velocity mode")
AddSetting(name="DropletVelocityX", default=0.0, comment="legacy droplet velocity x")
AddSetting(name="DropletVelocityY", default=0.0, comment="legacy droplet velocity y")
AddSetting(name="DropletVelocityZ", default=0.0, comment="legacy droplet velocity z")
AddSetting(name="CompositeDropletTailVelocityMode", default=0.0, comment="legacy tail velocity mode")
AddSetting(name="CompositeDropletTailVelocityX", default=0.0, comment="legacy tail velocity x")
AddSetting(name="CompositeDropletTailVelocityY", default=0.0, comment="legacy tail velocity y")
AddSetting(name="CompositeDropletTailVelocityZ", default=0.0, comment="legacy tail velocity z")
AddSetting(name="Pressure", default=0.0, comment="initial pressure-like moment", zonal=TRUE)
AddSetting(name="GravitationX", default=0.0, comment="gravity x")
AddSetting(name="GravitationY", default=0.0, comment="gravity y")
AddSetting(name="GravitationZ", default=0.0, comment="gravity z")
AddSetting(name="BuoyancyX", default=0.0, comment="buoyancy x")
AddSetting(name="BuoyancyY", default=0.0, comment="buoyancy y")
AddSetting(name="BuoyancyZ", default=0.0, comment="buoyancy z")

AddSetting(name="tau_l", comment="relaxation time offset for low-density phase")
AddSetting(name="tau_h", comment="relaxation time offset for high-density phase")
AddSetting(name="tauUpdate", default=1, comment="legacy tau interpolation mode")
AddSetting(name="Viscosity_l", tau_l="(3*Viscosity_l)", default=0.16666666, comment="low-phase kinematic viscosity")
AddSetting(name="Viscosity_h", tau_h="(3*Viscosity_h)", default=0.16666666, comment="high-phase kinematic viscosity")

# Clean architecture switches. Defaults keep write paths conservative.
AddSetting(name="PhaseEquationMode", default=2, comment="0 legacy-compatible, 1 normalized source, 2 conservative Allen-Cahn source")
AddSetting(name="PhaseBoundednessMode", default=1, comment="0 off, 1 shadow ledger, 2 local bounded h projection, 3 global correction setting")
AddSetting(name="PhaseGlobalCorrection", default=0.0, comment="host/global redistributed correction applied in PhaseBoundednessMode=3")
AddSetting(name="PhaseCorrectionBandMin", default=0.02, comment="minimum normalized phase for global correction redistribution band")
AddSetting(name="PhaseCorrectionBandMax", default=0.98, comment="maximum normalized phase for global correction redistribution band")
AddSetting(name="PhasePopulationRepairMode", default=1, comment="0 off, 1 repair nonfinite/out-of-bounds streamed h without midpoint masking")
AddSetting(name="GeometryMode", default=0, comment="0 bulk, 1 plane, 2 cylinder, 3 sphere, 4 diffuse/imported")
AddSetting(name="SolidAxis", default=2, comment="0 x, 1 y, 2 z for cylinder")
AddSetting(name="SolidRadius", default=0.0, comment="analytic cylinder/sphere radius")
AddSetting(name="SolidCenterX", default=0.0, comment="solid center x")
AddSetting(name="SolidCenterY", default=0.0, comment="solid center y")
AddSetting(name="SolidCenterZ", default=0.0, comment="solid center z")
AddSetting(name="SolidPlaneNormalX", default=0.0, comment="plane normal x")
AddSetting(name="SolidPlaneNormalY", default=1.0, comment="plane normal y")
AddSetting(name="SolidPlaneNormalZ", default=0.0, comment="plane normal z")
AddSetting(name="SolidPlaneOffset", default=0.0, comment="plane signed-distance offset")
AddSetting(name="WettingModel", default=0, comment="0 off, 1 geometric virtual phase, 2 surface-free-energy")
AddSetting(name="WettingWriteMode", default=0, comment="0 shadow/off, 1 full wall equilibrium h source, 2 per-link passive h source")
AddSetting(name="radAngle", default="1.570796", comment="target contact angle in radians", zonal=TRUE)
AddSetting(name="GradPhiMode", default=0, comment="0 isotropic bulk, 1 wall reconstructed, 2 diffuse-solid")
AddSetting(name="LaplaceMode", default=0, comment="0 isotropic bulk, 1 wall reconstructed, 2 diffuse-solid")
AddSetting(name="MuWallFluxMode", default=0, comment="0 none, 1 no-flux reconstructed")
AddSetting(name="PressureClosureMode", default=1, comment="0 legacy m0[0], 1 physical pressure pstar*rho*cs2, 2 physical pressure minus reference")
AddSetting(name="PressureReferenceValue", default=0.0, comment="reference pressure subtracted when PressureClosureMode=2")
AddSetting(name="ForceClosureMode", default=1, comment="0 legacy-compatible, 1 clean Fs+Fp+Fb, 2 clean plus F_mu stress")
AddSetting(name="FmuStressMode", default=0, comment="0 off, 1 non-equilibrium pre-collision stress reconstruction")
AddSetting(name="ForceInsertionMode", default=0, comment="0 legacy MRT compatible, 1 Guo/MRT audited")
AddSetting(name="MomentumMRTMode", default=1, comment="0 legacy relaxation spectrum, 1 bounded stable relaxation spectrum")
AddSetting(name="MRTShearOmegaOverride", default=-1.0, comment="override shear relaxation omega; <=0 uses 1/tau")
AddSetting(name="MRTBulkOmega", default=1.0, comment="bulk/energy-mode relaxation omega for Stage18 MRT")
AddSetting(name="MRTMinOmega", default=0.2, comment="minimum allowed MRT relaxation omega")
AddSetting(name="MRTMaxOmega", default=1.98, comment="maximum allowed MRT relaxation omega")
AddSetting(name="force_fixed_iterator", default=2, comment="legacy force fixed-point iterations")
AddSetting(name="DiagnosticsLevel", default=1, comment="0 none, 1 slim, 2 audit")

##############################
######## NODE TYPES ##########
##############################

AddNodeType(name="Solid", group="BOUNDARY")
AddNodeType(name="Wall", group="BOUNDARY")
AddNodeType(name="BGK", group="COLLISION")
AddNodeType(name="MRT", group="COLLISION")
AddNodeType(name="Smoothing", group="ADDITIONALS")
AddNodeType(name="flux_nodes", group="ADDITIONALS")
AddNodeType(name="Centerline", group="ADDITIONALS")
AddNodeType(name="Spiketrack", group="ADDITIONALS")
AddNodeType(name="Saddletrack", group="ADDITIONALS")
AddNodeType(name="Bubbletrack", group="ADDITIONALS")

dotR_my_velocity_boundaries = paste0(c("N", "E", "S", "W", "F", "B"), "Velocity")
dotR_my_pressure_boundaries = paste0(c("N", "E", "S", "W", "F", "B"), "Pressure")
for (ii in 1:6) {
    AddNodeType(name=dotR_my_velocity_boundaries[ii], group="BOUNDARY")
    AddNodeType(name=dotR_my_pressure_boundaries[ii], group="BOUNDARY")
}
AddNodeType(name="MovingWall_N", group="BOUNDARY")
AddNodeType(name="MovingWall_S", group="BOUNDARY")

if (Options$OutFlow) {
    AddNodeType(name="ENeumann", group="BOUNDARY")
    AddNodeType(name="WNeumann", group="BOUNDARY")
    AddNodeType(name="EConvect", group="BOUNDARY")
    AddNodeType(name="WConvect", group="BOUNDARY")
}

##############################
######## GLOBALS #############
##############################

AddGlobal(name="TotalDensity", comment="mass conservation check", unit="1kg/m3")
AddGlobal(name="KineticEnergy", comment="kinetic energy", unit="J")
AddGlobal(name="NumFluidCells", comment="number of collision cells")
AddGlobal(name="NumBoundaryPoints", comment="number of boundary cells")
AddGlobal(name="NumWallBoundaryPoints", comment="number of wall boundary cells")
AddGlobal(name="NumSpecialPoints", comment="legacy special wall points")
AddGlobal(name="InterfacePosition", op="MAX", comment="interface tracker")
AddGlobal(name="InterfaceYTop", op="MAX", comment="top interface y")
AddGlobal(name="GasTotalPhase", comment="gas phase total", unit="1")
AddGlobal(name="LiqTotalPhase", comment="liquid phase total", unit="1")
AddGlobal(name="GasTotalVelocity", comment="gas average velocity", unit="m/s")
AddGlobal(name="LiqTotalVelocity", comment="liquid average velocity", unit="m/s")
AddGlobal(name="PhaseClippedMass", comment="sum of local boundedness clipping mass", unit="1")
AddGlobal(name="PhaseRedistributionWeightTotal", comment="sum of eligible interface weights for global mass correction", unit="1")
AddGlobal(name="WallHNetMassTotal", comment="sum of wall passive h source net mass", unit="1")

##############################
######## STAGES ##############
##############################

save_pf_macro = Fields$group %in% c("PF", "PFState", "Macro")
save_geometry = Fields$group %in% c("SolidGeom", "solid_boundary", "nw")
save_grad = Fields$group %in% "GradPhi"
save_mu = Fields$group %in% "Mu"
save_wetting = Fields$group %in% "Wetting"
save_h_cache = Fields$group %in% "HCache"
save_wall_audit = Fields$group %in% "WallSourceAudit"
save_phase_audit = Fields$group %in% "PhaseAudit"
save_force = Fields$group %in% c("Force", "ForceAudit", "StressAudit")
save_audit = Fields$group %in% "Audit"
save_mass_audit = (Fields$name %in% "MassCorrectionApplied") | save_phase_audit
save_contract_audit = Fields$name %in% "Stage18ContractViolation"

load_populations = DensityAll$group %in% c("g", "h", "gold", "hold")
load_h = DensityAll$group %in% c("h", "hold")
load_g = DensityAll$group %in% c("g", "gold")
save_populations = Fields$group %in% c("g", "h", "gold", "hold")
save_h = Fields$group %in% c("h", "hold")
save_g = Fields$group %in% c("g", "gold")
save_stage18_persistent_state = save_pf_macro | save_geometry | save_grad | save_mu | save_wetting | save_force

AddStage("InitPhaseField", "Stage18_InitPhaseField", save=save_pf_macro)
AddStage("InitFromFieldsStage", "Stage18_InitFromFields", load=DensityAll$group %in% "init", read=FALSE, save=save_pf_macro)
AddStage("IterationInput", "Stage18_PhaseFromH", load=load_populations | (DensityAll$group %in% c("PF", "Macro", "GradPhi", "Mu", "Force", "Wetting")), save=save_g | save_pf_macro | save_h_cache | save_wall_audit | save_phase_audit, can.overwrite=TRUE)
AddStage("GeometryBuild", "Stage18_GeometryBuild", save=save_geometry)
AddStage("WettingBoundary", "Stage18_WettingBoundary", load=DensityAll$group %in% c("PF", "GradPhi", "SolidGeom", "solid_boundary", "nw"), save=save_wetting)
AddStage("WallPhasePopulationSource", "Stage18_WallPhasePopulationSource", load=load_h | (DensityAll$group %in% c("Wetting", "SolidGeom")), save=save_h | save_wall_audit, can.overwrite=TRUE)
AddStage("InitDistributions", "Stage18_InitDistributions", load=DensityAll$group %in% c("PF", "Macro", "GradPhi"), save=save_populations | save_h_cache)
AddStage("PhaseFromH", "Stage18_PhaseFromH", load=load_h | (DensityAll$group %in% c("PF", "Macro", "GradPhi", "Mu", "Force", "Wetting")), save=save_pf_macro | save_h_cache | save_h | save_wall_audit | save_phase_audit, can.overwrite=TRUE)
AddStage("GradPhi", "Stage18_GradPhi", load=DensityAll$group %in% c("PF", "SolidGeom", "Wetting", "solid_boundary", "nw"), save=save_grad)
AddStage("Mu", "Stage18_Mu", load=DensityAll$group %in% c("PF", "GradPhi", "SolidGeom", "Wetting"), save=save_mu)
AddStage("InitForceAudit", "Stage18_InitForceAudit", save=save_force | save_wall_audit | save_mass_audit)
AddStage("ForceClosure", "Stage18_ForceClosure", load=load_g | (DensityAll$group %in% c("PF", "Macro", "GradPhi", "Mu")), save=save_force)
AddStage("MomentumCollision", "Stage18_MomentumCollision", load=load_g | (DensityAll$group %in% c("PF", "Macro", "Force", "HCache")), save=save_populations | save_stage18_persistent_state | save_contract_audit | save_phase_audit | save_wall_audit | save_mass_audit, can.overwrite=TRUE)
AddStage("PhaseCollision", "Stage18_PhaseCollision", load=load_h | (DensityAll$group %in% c("PF", "Macro", "GradPhi", "Mu", "Force", "Wetting")), save=save_h | save_wall_audit | save_phase_audit, can.overwrite=TRUE)
AddStage("ConservativeBoundednessCorrection", "Stage18_ConservativeBoundednessCorrection", load=DensityAll$group %in% c("PF", "PFState", "PhaseAudit"), save=save_mass_audit | save_pf_macro, can.overwrite=TRUE)
AddStage("AuditSlim", "Stage18_AuditSlim", load=DensityAll$group %in% c("PF", "Macro", "Force", "Wetting"), save=save_stage18_persistent_state | save_contract_audit | save_phase_audit | save_wall_audit | save_mass_audit, can.overwrite=TRUE)

##############################
######## ACTIONS #############
##############################

AddAction("Init", c(
    "InitPhaseField",
    "GeometryBuild",
    "GradPhi",
    "Mu",
    "WettingBoundary",
    "InitForceAudit",
    "InitDistributions",
    "AuditSlim"
))

AddAction("InitFields", c(
    "InitFromFieldsStage",
    "GeometryBuild",
    "GradPhi",
    "Mu",
    "WettingBoundary",
    "InitForceAudit",
    "InitDistributions",
    "AuditSlim"
))

AddAction("Iteration", c(
    "IterationInput",
    "GeometryBuild",
    "GradPhi",
    "Mu",
    "WettingBoundary",
    "ForceClosure",
    "AuditSlim",
    "MomentumCollision"
))

##############################
######## OUTPUTS #############
##############################

AddQuantity(name="Rho", unit="kg/m3")
AddQuantity(name="PhaseField", unit="1")
AddQuantity(name="PhaseFValid", unit="1")
AddQuantity(name="PhaseOutOfBoundsFlag", unit="1")
AddQuantity(name="U", unit="m/s", vector=TRUE)
AddQuantity(name="P", unit="Pa")
AddQuantity(name="Pstar", unit="1")
AddQuantity(name="Normal", unit=1, vector=TRUE)
AddQuantity(name="IsItBoundary", unit="1")
AddQuantity(name="GradPhi", unit=1, vector=TRUE)
AddQuantity(name="WallPhase", unit="1")
AddQuantity(name="ForceTotal", unit="1", vector=TRUE)
AddQuantity(name="Stage18Violation", unit="1")
AddQuantity(name="PressureInput", unit="1")
AddQuantity(name="ForceOverRho", unit="1")
AddQuantity(name="ForceInsertionAudit", unit="1")
AddQuantity(name="ForceHalfVelocity", unit="1", vector=TRUE)
AddQuantity(name="ForceMomentumBefore", unit="1", vector=TRUE)
AddQuantity(name="ForceMomentumAfter", unit="1", vector=TRUE)
AddQuantity(name="MassCorrectionApplied", unit="1")
AddQuantity(name="WallHNetMass", unit="1")
AddQuantity(name="WallHLinkWriteCount", unit="1")
AddQuantity(name="WallHMassBefore", unit="1")
AddQuantity(name="WallHMassAfter", unit="1")
AddQuantity(name="PhaseHPreSum", unit="1")
AddQuantity(name="PhaseHRawSum", unit="1")
AddQuantity(name="PhaseHRawMin", unit="1")
AddQuantity(name="PhaseHRawMax", unit="1")
AddQuantity(name="PhaseHRawNonfiniteCount", unit="1")
AddQuantity(name="PhaseHeqSum", unit="1")
AddQuantity(name="PhaseFphiSum", unit="1")
AddQuantity(name="PhaseHPostSum", unit="1")
AddQuantity(name="PhaseCorrectionDelta", unit="1")
AddQuantity(name="PhaseMassRedistributionWeight", unit="1")
AddQuantity(name="PhaseGlobalCorrectionApplied", unit="1")
AddQuantity(name="PhasePopulationRepairApplied", unit="1")
AddQuantity(name="PhaseFphiFirstMoment", unit="1", vector=TRUE)
AddQuantity(name="ForceEquivalentInjected", unit="1", vector=TRUE)
