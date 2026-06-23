/*-------------------------------------------------------------*/
/*  CLB - Cudne LB - Stencil Version                           */
/*     CUDA based Adjoint Lattice Boltzmann Solver             */
/*     Author: Lukasz Laniewski-Wollk                          */
/*     Developed at: Warsaw University of Technology - 2012    */
/*-------------------------------------------------------------*/

// 04/02/2017 - Model Developed: A. Fakhari, T. Mitchell
//    Extension to 3D from:
// """" A roust phase-field lattice Boltzmann model
//		for immiscible fluids at high density ratios """"
//
// Maintainer: Travis-Mitchell @TravisMitchell

// Major code updates:
//		01/04/2017: Initial implementation
//			    Plan is d3q27 for hydrodynamics
//			    and d3q15 for interface dynamics
//		08/04/2017: Verification and validation
//				- Layered Poiseuille flow
//				- Rayleigh Taylor up to water-air like properties and Re=3000
//				- Validated with air Taylor bubble rising through olive oil
//				  experiment by Bugg et al. (2002)
//		14/08/2017: Look to improve readability by incorporating more R code
//				- e.g. for MRT operations etc.
//		12/12/2017: Model updated for inclusion in v6.2
//				- MRT collision updated to moment space
//				- Symmetry bounds removed, autosym added to options
//				- BGK made option
//		21/03/2018: Fix of solid contact
//				- Previous issue with bulk solid regions i.e. solid cells
//				  surrounded by all solid nodes
//				- Check added for these cases to stop nan appearances
//		28/04/2020: Added thermocapillary effects option
//		07/04/2021: Code clean up
//				- thermocapillary moved to the bottom of the file to separate
//				- forces broken up into individual functions, set up so that additional
//				  physics can be added simply if only a force needs to be altered
//				- edge case for wall phase calculation in which normal direction points
//				  towards a solid node was found. Temporary fix by setting this to a
//				  reasonable value (1) has been made - this is not ideal...
//		xx/xx/2022: Extension of phase field to d3q27 option to move away from crappy q15 lattice.
//		xx/xx/2022: Development of geometric wetting B.C. option as well as existing surface energy.
//		xx/xx/2023: Code extension for wetting on curved boundaries.

#include <math.h>
#define PI 3.14159265
#define cs2 0.33333333
#ifdef OPTIONS_q27
#define hPops 27
#else
#define hPops 15
#endif


CudaDeviceFunction real_t getRho(){
	if ( IamWall || IamSolid) {
		return 0.0;
	} else {
		real_t current_phase = getPhaseField();
		return Density_l + (Density_h-Density_l) * (current_phase - PhaseField_l)/(PhaseField_h - PhaseField_l);
	}
}

CudaDeviceFunction real_t getPhaseField(){
	return PhaseF(0,0,0);
}

CudaDeviceFunction vector_t getU(){
	vector_t u;
	if ( IamWall || IamSolid ) {
		u.x = 0.0; u.y = 0.0; u.z = 0.0;
	} else {
		u.x = U; u.y = V; u.z = W;
	}
	return u;
}

CudaDeviceFunction real_t getPstar(){
	return g26 + g25 + g24 + g23 + g22 + g21 + g20 + g19 + g18 + g17 + g16 + g15 + g14 + g13 + g12 + g11 + g10 + g9 + g8 + g7 + g6 + g5 + g4 + g3 + g2 + g1 + g0;
}

CudaDeviceFunction real_t getP(){
	real_t d = getRho();
	real_t pstar = getPstar();
	return pstar*d*cs2;
}

CudaDeviceFunction vector_t getNormal(){
	vector_t n = {nw_x, nw_y, nw_z};
	return n;
}

CudaDeviceFunction int stage13_phase_is_valid(real_t pf) {
	if (!(pf == pf)) return 0;
	real_t lo = PhaseField_l;
	real_t hi = PhaseField_h;
	if (lo > hi) {
		real_t tmp = lo;
		lo = hi;
		hi = tmp;
	}
	real_t eps = PhaseValidityEps;
	if (eps < 0.0) eps = 0.0;
	return (pf >= lo - eps && pf <= hi + eps);
}

CudaDeviceFunction real_t stage13_select_phase_for_stencil(real_t pf, real_t is_boundary, real_t ghost, real_t center) {
	// Stage 15B-pre safety cleanup: the compact-stencil WallGhost is the single
	// main physics channel for the geometric contact-angle boundary (14A/14C-prime
	// proved it healthy on the contact-line band). It must ALWAYS be consumed by
	// the stencil when valid, independent of WallGradMode. The prior WallGradMode
	// guard skipped ghost substitution when Layer1 (>=2) was active, which would
	// let the already-disproven corrected-gradient write path bypass the compact
	// ghost and silently change both gradPhi and lapPhi/mu. That path is now
	// disabled in calcGradPhi(); the guard here is removed so the compact ghost
	// is the sole source of the wall phase seen by the stencil.
	if (is_boundary > 0.5 && stage13_phase_is_valid(ghost)) {
		if (ReplayDiagnosticsMode > 0.5) PhaseStencilGhostUseCount = PhaseStencilGhostUseCount + 1.0;
		return ghost;
	}
	if (stage13_phase_is_valid(pf)) return pf;
	if (stage13_phase_is_valid(ghost)) {
		if (ReplayDiagnosticsMode > 0.5) PhaseStencilFallbackCount = PhaseStencilFallbackCount + 1.0;
		return ghost;
	}
	if (stage13_phase_is_valid(center)) {
		if (ReplayDiagnosticsMode > 0.5) PhaseStencilFallbackCount = PhaseStencilFallbackCount + 1.0;
		return center;
	}
	if (ReplayDiagnosticsMode > 0.5) {
		PhaseStencilFallbackCount = PhaseStencilFallbackCount + 1.0;
		PhaseStencilMidpointFallbackCount = PhaseStencilMidpointFallbackCount + 1.0;
	}
	return 0.5*(PhaseField_l + PhaseField_h);
}

#define STAGE13_PHASE_FOR_STENCIL(dx,dy,dz) \
	stage13_select_phase_for_stencil(PhaseF(dx,dy,dz), IsBoundary(dx,dy,dz), WallGhost(dx,dy,dz), PhaseF(0,0,0))

CudaDeviceFunction real_t getForceIterResidual(){
	return ForceIterResidual(0,0,0);
}

CudaDeviceFunction real_t getForceIterCount(){
	return ForceIterCount(0,0,0);
}

CudaDeviceFunction real_t getMassCorrectionApplied(){
	return MassCorrectionApplied(0,0,0);
}

CudaDeviceFunction real_t getPhaseStencilGhostUseCount(){
	return PhaseStencilGhostUseCount(0,0,0);
}

CudaDeviceFunction real_t getPhaseStencilFallbackCount(){
	return PhaseStencilFallbackCount(0,0,0);
}

CudaDeviceFunction real_t getPhaseStencilMidpointFallbackCount(){
	return PhaseStencilMidpointFallbackCount(0,0,0);
}

CudaDeviceFunction int stage16_replay_diagnostics_active(){
	return (ReplayDiagnosticsMode > 0.5 && !(IamWall || IamSolid));
}

CudaDeviceFunction void stage16_zero_replay_diagnostics(){
	ReplayPhaseConsumed = 0.0;
	ReplayLapPhi = 0.0;
	ReplayMu = 0.0;
	ReplayGradPhiX = 0.0;
	ReplayGradPhiY = 0.0;
	ReplayGradPhiZ = 0.0;
	ReplayFsurfX = 0.0;
	ReplayFsurfY = 0.0;
	ReplayFsurfZ = 0.0;
	ReplayFpressureX = 0.0;
	ReplayFpressureY = 0.0;
	ReplayFpressureZ = 0.0;
	ReplayFbodyX = 0.0;
	ReplayFbodyY = 0.0;
	ReplayFbodyZ = 0.0;
	ReplayFmuX = 0.0;
	ReplayFmuY = 0.0;
	ReplayFmuZ = 0.0;
	ReplayFtotalX = 0.0;
	ReplayFtotalY = 0.0;
	ReplayFtotalZ = 0.0;
	ReplayRho = 0.0;
	ReplayTau = 0.0;
	ReplayPressureMoment = 0.0;
	ReplayUPreForceX = 0.0;
	ReplayUPreForceY = 0.0;
	ReplayUPreForceZ = 0.0;
	ReplayUPostForceX = 0.0;
	ReplayUPostForceY = 0.0;
	ReplayUPostForceZ = 0.0;
	ReplayForceOverRhoX = 0.0;
	ReplayForceOverRhoY = 0.0;
	ReplayForceOverRhoZ = 0.0;
	ReplayFmuIter1X = 0.0;
	ReplayFmuIter1Y = 0.0;
	ReplayFmuIter1Z = 0.0;
	ReplayFtotalIter1X = 0.0;
	ReplayFtotalIter1Y = 0.0;
	ReplayFtotalIter1Z = 0.0;
	ReplayUPostIter1X = 0.0;
	ReplayUPostIter1Y = 0.0;
	ReplayUPostIter1Z = 0.0;
	ReplayNormalX = 0.0;
	ReplayNormalY = 0.0;
	ReplayNormalZ = 0.0;
	ReplayStressXX = 0.0;
	ReplayStressXY = 0.0;
	ReplayStressXZ = 0.0;
	ReplayStressYY = 0.0;
	ReplayStressYZ = 0.0;
	ReplayStressZZ = 0.0;
	ReplayFphiSum = 0.0;
	ReplayFphiMaxAbs = 0.0;
	ReplayTmp1 = 0.0;
}

CudaDeviceFunction real_t stage16_replay_scalar(real_t value){
	if (stage16_replay_diagnostics_active()) return value;
	return 0.0;
}

CudaDeviceFunction real_t getReplayPhaseConsumed(){
	return stage16_replay_scalar(ReplayPhaseConsumed(0,0,0));
}

CudaDeviceFunction real_t getReplayPhaseFromH(){
	if (ReplayDiagnosticsMode > 0.5) return ReplayPhaseFromH(0,0,0);
	return 0.0;
}

CudaDeviceFunction real_t getReplayLapPhi(){
	return stage16_replay_scalar(ReplayLapPhi(0,0,0));
}

CudaDeviceFunction real_t getReplayMu(){
	return stage16_replay_scalar(ReplayMu(0,0,0));
}

CudaDeviceFunction vector_t getReplayGradPhi(){
	vector_t out;
	out.x = stage16_replay_scalar(ReplayGradPhiX(0,0,0));
	out.y = stage16_replay_scalar(ReplayGradPhiY(0,0,0));
	out.z = stage16_replay_scalar(ReplayGradPhiZ(0,0,0));
	return out;
}

CudaDeviceFunction vector_t getReplayFsurf(){
	vector_t out;
	out.x = stage16_replay_scalar(ReplayFsurfX(0,0,0));
	out.y = stage16_replay_scalar(ReplayFsurfY(0,0,0));
	out.z = stage16_replay_scalar(ReplayFsurfZ(0,0,0));
	return out;
}

CudaDeviceFunction vector_t getReplayFpressure(){
	vector_t out;
	out.x = stage16_replay_scalar(ReplayFpressureX(0,0,0));
	out.y = stage16_replay_scalar(ReplayFpressureY(0,0,0));
	out.z = stage16_replay_scalar(ReplayFpressureZ(0,0,0));
	return out;
}

CudaDeviceFunction vector_t getReplayFbody(){
	vector_t out;
	out.x = stage16_replay_scalar(ReplayFbodyX(0,0,0));
	out.y = stage16_replay_scalar(ReplayFbodyY(0,0,0));
	out.z = stage16_replay_scalar(ReplayFbodyZ(0,0,0));
	return out;
}

CudaDeviceFunction vector_t getReplayFmu(){
	vector_t out;
	out.x = stage16_replay_scalar(ReplayFmuX(0,0,0));
	out.y = stage16_replay_scalar(ReplayFmuY(0,0,0));
	out.z = stage16_replay_scalar(ReplayFmuZ(0,0,0));
	return out;
}

CudaDeviceFunction vector_t getReplayFtotal(){
	vector_t out;
	out.x = stage16_replay_scalar(ReplayFtotalX(0,0,0));
	out.y = stage16_replay_scalar(ReplayFtotalY(0,0,0));
	out.z = stage16_replay_scalar(ReplayFtotalZ(0,0,0));
	return out;
}

CudaDeviceFunction real_t getReplayRho(){
	return stage16_replay_scalar(ReplayRho(0,0,0));
}

CudaDeviceFunction real_t getReplayTau(){
	return stage16_replay_scalar(ReplayTau(0,0,0));
}

CudaDeviceFunction real_t getReplayPressureMoment(){
	return stage16_replay_scalar(ReplayPressureMoment(0,0,0));
}

CudaDeviceFunction vector_t getReplayUPreForce(){
	vector_t out;
	out.x = stage16_replay_scalar(ReplayUPreForceX(0,0,0));
	out.y = stage16_replay_scalar(ReplayUPreForceY(0,0,0));
	out.z = stage16_replay_scalar(ReplayUPreForceZ(0,0,0));
	return out;
}

CudaDeviceFunction vector_t getReplayUPostForce(){
	vector_t out;
	out.x = stage16_replay_scalar(ReplayUPostForceX(0,0,0));
	out.y = stage16_replay_scalar(ReplayUPostForceY(0,0,0));
	out.z = stage16_replay_scalar(ReplayUPostForceZ(0,0,0));
	return out;
}

CudaDeviceFunction vector_t getReplayForceOverRho(){
	vector_t out;
	out.x = stage16_replay_scalar(ReplayForceOverRhoX(0,0,0));
	out.y = stage16_replay_scalar(ReplayForceOverRhoY(0,0,0));
	out.z = stage16_replay_scalar(ReplayForceOverRhoZ(0,0,0));
	return out;
}

CudaDeviceFunction vector_t getReplayFmuIter1(){
	vector_t out;
	out.x = stage16_replay_scalar(ReplayFmuIter1X(0,0,0));
	out.y = stage16_replay_scalar(ReplayFmuIter1Y(0,0,0));
	out.z = stage16_replay_scalar(ReplayFmuIter1Z(0,0,0));
	return out;
}

CudaDeviceFunction vector_t getReplayFtotalIter1(){
	vector_t out;
	out.x = stage16_replay_scalar(ReplayFtotalIter1X(0,0,0));
	out.y = stage16_replay_scalar(ReplayFtotalIter1Y(0,0,0));
	out.z = stage16_replay_scalar(ReplayFtotalIter1Z(0,0,0));
	return out;
}

CudaDeviceFunction vector_t getReplayUPostIter1(){
	vector_t out;
	out.x = stage16_replay_scalar(ReplayUPostIter1X(0,0,0));
	out.y = stage16_replay_scalar(ReplayUPostIter1Y(0,0,0));
	out.z = stage16_replay_scalar(ReplayUPostIter1Z(0,0,0));
	return out;
}

CudaDeviceFunction vector_t getReplayNormal(){
	vector_t out;
	out.x = stage16_replay_scalar(ReplayNormalX(0,0,0));
	out.y = stage16_replay_scalar(ReplayNormalY(0,0,0));
	out.z = stage16_replay_scalar(ReplayNormalZ(0,0,0));
	return out;
}

CudaDeviceFunction real_t getReplayStressXX(){
	return stage16_replay_scalar(ReplayStressXX(0,0,0));
}

CudaDeviceFunction real_t getReplayStressXY(){
	return stage16_replay_scalar(ReplayStressXY(0,0,0));
}

CudaDeviceFunction real_t getReplayStressXZ(){
	return stage16_replay_scalar(ReplayStressXZ(0,0,0));
}

CudaDeviceFunction real_t getReplayStressYY(){
	return stage16_replay_scalar(ReplayStressYY(0,0,0));
}

CudaDeviceFunction real_t getReplayStressYZ(){
	return stage16_replay_scalar(ReplayStressYZ(0,0,0));
}

CudaDeviceFunction real_t getReplayStressZZ(){
	return stage16_replay_scalar(ReplayStressZZ(0,0,0));
}

CudaDeviceFunction real_t getReplayFphiSum(){
	return stage16_replay_scalar(ReplayFphiSum(0,0,0));
}

CudaDeviceFunction real_t getReplayFphiMaxAbs(){
	return stage16_replay_scalar(ReplayFphiMaxAbs(0,0,0));
}

CudaDeviceFunction real_t getReplayTmp1(){
	return stage16_replay_scalar(ReplayTmp1(0,0,0));
}

CudaDeviceFunction real_t getWallGradDeltaMag(){
	return WallGradDeltaMag(0,0,0);
}
CudaDeviceFunction real_t getWallGradThetaApp(){
	return WallGradThetaApp(0,0,0);
}
CudaDeviceFunction real_t getWallMuCandidate(){
	return WallMuCandidate(0,0,0);
}

// ================================================================
// Layer 3 (DynamicCL, Stage 15B): residual contact-line shadow diagnostics
// ================================================================
// Getters for the DynamicCL diagnostic fields. Each AddQuantity above needs a
// get<Name>() device function returning the cell-field value.
CudaDeviceFunction real_t getDynamicCLActive(){ return DynamicCLActive(0,0,0); }
CudaDeviceFunction real_t getDynamicCLIndicator(){ return DynamicCLIndicator(0,0,0); }
CudaDeviceFunction real_t getDynamicCLCosApp(){ return DynamicCLCosApp(0,0,0); }
CudaDeviceFunction real_t getDynamicCLThetaApp(){ return DynamicCLThetaApp(0,0,0); }
CudaDeviceFunction real_t getDynamicCLCosEq(){ return DynamicCLCosEq(0,0,0); }
CudaDeviceFunction real_t getDynamicCLCosResidual(){ return DynamicCLCosResidual(0,0,0); }
CudaDeviceFunction real_t getDynamicCLForceCandidateX(){ return DynamicCLForceCandidateX(0,0,0); }
CudaDeviceFunction real_t getDynamicCLForceCandidateY(){ return DynamicCLForceCandidateY(0,0,0); }
CudaDeviceFunction real_t getDynamicCLForceCandidateZ(){ return DynamicCLForceCandidateZ(0,0,0); }
CudaDeviceFunction real_t getDynamicCLForceCandidateMag(){ return DynamicCLForceCandidateMag(0,0,0); }
CudaDeviceFunction real_t getDynamicCLTangentialX(){ return DynamicCLTangentialX(0,0,0); }
CudaDeviceFunction real_t getDynamicCLTangentialY(){ return DynamicCLTangentialY(0,0,0); }
CudaDeviceFunction real_t getDynamicCLTangentialZ(){ return DynamicCLTangentialZ(0,0,0); }
CudaDeviceFunction real_t getDynamicCLWallNormalX(){ return DynamicCLWallNormalX(0,0,0); }
CudaDeviceFunction real_t getDynamicCLWallNormalY(){ return DynamicCLWallNormalY(0,0,0); }
CudaDeviceFunction real_t getDynamicCLWallNormalZ(){ return DynamicCLWallNormalZ(0,0,0); }
CudaDeviceFunction real_t getDynamicCLRejectedReason(){ return DynamicCLRejectedReason(0,0,0); }
CudaDeviceFunction real_t getDynamicCLThetaEq(){ return DynamicCLThetaEq(0,0,0); }
CudaDeviceFunction real_t getDynamicCLWallContextFound(){ return DynamicCLWallContextFound(0,0,0); }
CudaDeviceFunction real_t getDynamicCLBlockedReason(){ return DynamicCLBlockedReason(0,0,0); }
CudaDeviceFunction real_t getDynamicCLWallDx(){ return DynamicCLWallDx(0,0,0); }
CudaDeviceFunction real_t getDynamicCLWallDy(){ return DynamicCLWallDy(0,0,0); }
CudaDeviceFunction real_t getDynamicCLWallDz(){ return DynamicCLWallDz(0,0,0); }

// ----------------------------------------------------------------
// Stage 15B: compute the contact-line residual R_theta and a candidate
// force F_CL = DynamicCLForceSign * DynamicCLCoeff * sigma/IntWidth * R_theta
//            * I_CL * t_CL.
// This is SHADOW ONLY in 15B: it writes the DynamicCL* diagnostic fields and
// returns the candidate force vector, but the caller must NOT add it to
// F_total unless DynamicCLMode >= 2 (reserved for 15C).
//
// R_theta = cos(theta_eq) - cos(theta_app) vanishes at equilibrium by
// construction. theta_app is read from the interface normal n_i = gradPhi/|g|
// vs the analytic wall normal n_w. theta_eq is the zone-resolved contact
// angle taken from the adjacent WETTING wall node's LocalRadAngle (NOT this
// fluid node's own zonal radAngle, which reads the global 90 deg default off
// the wetting-wall zone — that produced the cos_eq=0 artifact). The sign
// convention DynamicCLCosSign is calibrated by the equilibrium 30/90/150
// cases (the value that makes cos_app -> cos(theta_eq) there).
//
// Rejected-reason codes (DynamicCLRejectedReason / legacy):
//   0 accepted, 1 wall/solid node, 2 no adjacent wetting wall, 3 invalid/too-far
//   wall normal, 4 q out of contact-line band, 5 |gradPhi| too small,
//   6 |R_theta| below DynamicCLCosTol.
// Blocked-reason codes (DynamicCLBlockedReason / 15B, more granular):
//   0 accepted or DynamicCLMode off, 1 wall/solid, 2 no adjacent wetting wall,
//   3 invalid/too-far wall normal, 5 q out of band, 6 |gradPhi| too small,
//   7 |R_theta| below DynamicCLCosTol.
// ----------------------------------------------------------------
CudaDeviceFunction void calcDynamicCLShadow(vector_t gradPhi, real_t C,
	real_t *fx, real_t *fy, real_t *fz)
{
	// Defaults: zero candidate + zero diagnostics.
	*fx = 0.0; *fy = 0.0; *fz = 0.0;
	DynamicCLActive = 0.0;
	DynamicCLIndicator = 0.0;
	DynamicCLCosApp = 0.0;
	DynamicCLThetaApp = 0.0;
	DynamicCLCosEq = 0.0;
	DynamicCLCosResidual = 0.0;
	DynamicCLForceCandidateX = 0.0;
	DynamicCLForceCandidateY = 0.0;
	DynamicCLForceCandidateZ = 0.0;
	DynamicCLForceCandidateMag = 0.0;
	DynamicCLTangentialX = 0.0;
	DynamicCLTangentialY = 0.0;
	DynamicCLTangentialZ = 0.0;
	DynamicCLWallNormalX = 0.0;
	DynamicCLWallNormalY = 0.0;
	DynamicCLWallNormalZ = 0.0;
	DynamicCLRejectedReason = 0.0;
	DynamicCLThetaEq = 0.0;
	DynamicCLWallContextFound = 0.0;
	DynamicCLBlockedReason = 0.0;
	DynamicCLWallDx = 0.0;
	DynamicCLWallDy = 0.0;
	DynamicCLWallDz = 0.0;

	if (DynamicCLMode < 0.5) return;

	if (IamWall || IamSolid) { DynamicCLRejectedReason = 1.0; DynamicCLBlockedReason = 1.0; return; }

	// Stage 15B fix: require an adjacent WETTING wall (AnalyticFlag>0 with a
	// populated LocalRadAngle), not merely "any boundary neighbour". This
	// rejects OuterDomain walls (AnalyticFlag=0) which otherwise leak the
	// contact-line force band onto the outer-domain skin. The coarse
	// stage13_is_fluid_boundary_node() gate is intentionally NOT used here.
	real_t theta_eq;
	int wdx = 0, wdy = 0, wdz = 0;
	if (!stage15_find_wetting_wall_context(&theta_eq, &wdx, &wdy, &wdz)) {
		DynamicCLRejectedReason = 2.0;          // legacy code: not a contact-line node
		DynamicCLBlockedReason = 2.0;           // 15B: no adjacent wetting wall
		return;
	}
	DynamicCLWallContextFound = 1.0;
	DynamicCLWallDx = (real_t) wdx;
	DynamicCLWallDy = (real_t) wdy;
	DynamicCLWallDz = (real_t) wdz;

	real_t h_dist;
	vector_t n_w = stage9_analytic_wall_normal_and_distance(&h_dist);
	real_t nmag = sqrt(n_w.x*n_w.x + n_w.y*n_w.y + n_w.z*n_w.z);
	if (nmag < 1.0e-12) { DynamicCLRejectedReason = 3.0; DynamicCLBlockedReason = 3.0; return; }
	if (fabs(h_dist) > 2.0) { DynamicCLRejectedReason = 3.0; DynamicCLBlockedReason = 3.0; return; }
	n_w.x /= nmag; n_w.y /= nmag; n_w.z /= nmag;
	DynamicCLWallNormalX = n_w.x;
	DynamicCLWallNormalY = n_w.y;
	DynamicCLWallNormalZ = n_w.z;

	real_t pf_scale = PhaseField_h - PhaseField_l;
	if (fabs(pf_scale) < 1.0e-30) { DynamicCLRejectedReason = 4.0; DynamicCLBlockedReason = 4.0; return; }
	real_t q = (C - PhaseField_l) / pf_scale;
	if (q < 0.0) q = 0.0;
	if (q > 1.0) q = 1.0;
	// Contact-line band gate (Step D): exclude pure liquid / pure gas. This
	// alone removes a large class of spurious activations on near-wall bulk
	// nodes that happened to pass the old boundary-proximity gate.
	if (q < DynamicCLEpsQ || q > 1.0 - DynamicCLEpsQ) { DynamicCLRejectedReason = 4.0; DynamicCLBlockedReason = 5.0; return; }

	real_t gmag = sqrt(gradPhi.x*gradPhi.x + gradPhi.y*gradPhi.y + gradPhi.z*gradPhi.z);
	if (gmag < DynamicCLGradMin) { DynamicCLRejectedReason = 5.0; DynamicCLBlockedReason = 6.0; return; }

	vector_t n_i;
	n_i.x = gradPhi.x / gmag;
	n_i.y = gradPhi.y / gmag;
	n_i.z = gradPhi.z / gmag;

	real_t dot_nw = n_i.x*n_w.x + n_i.y*n_w.y + n_i.z*n_w.z;
	real_t cos_app = DynamicCLCosSign * dot_nw;
	if (cos_app > 1.0) cos_app = 1.0;
	if (cos_app < -1.0) cos_app = -1.0;
	// Stage 15B fix: theta_eq comes from the adjacent wetting wall's zone-
	// resolved LocalRadAngle (captured above), NOT from this fluid node's
	// own zonal radAngle (which reads the global 90 deg default off the
	// wetting-wall zone and produced the cos_eq=0 artifact).
	real_t cos_eq = cos(theta_eq);
	DynamicCLThetaEq = theta_eq;
	real_t R_theta = cos_eq - cos_app;
	DynamicCLCosApp = cos_app;
	DynamicCLCosEq = cos_eq;
	DynamicCLCosResidual = R_theta;
	// theta_app in degrees for diagnostics
	DynamicCLThetaApp = acos(cos_app) * 180.0 / 3.14159265358979323846;

	if (fabs(R_theta) < DynamicCLCosTol) { DynamicCLRejectedReason = 6.0; DynamicCLBlockedReason = 7.0; return; }

	// Wall-tangential direction of the interface normal projection:
	// t_CL = n_i - (n_i . n_w) n_w, normalized.
	vector_t t;
	t.x = n_i.x - dot_nw*n_w.x;
	t.y = n_i.y - dot_nw*n_w.y;
	t.z = n_i.z - dot_nw*n_w.z;
	real_t tmag = sqrt(t.x*t.x + t.y*t.y + t.z*t.z);
	if (tmag < 1.0e-14) { DynamicCLRejectedReason = 5.0; return; }
	t.x /= tmag; t.y /= tmag; t.z /= tmag;
	DynamicCLTangentialX = t.x;
	DynamicCLTangentialY = t.y;
	DynamicCLTangentialZ = t.z;

	real_t I_cl = 4.0 * q * (1.0 - q);
	DynamicCLIndicator = I_cl;

	// Candidate force magnitude (capped). NOT added to F_total in 15B.
	real_t scale = sigma / IntWidth;
	real_t mag = DynamicCLForceSign * DynamicCLCoeff * scale * R_theta * I_cl;
	real_t cap = DynamicCLForceCap * scale;
	if (mag >  cap) mag =  cap;
	if (mag < -cap) mag = -cap;

	*fx = mag * t.x;
	*fy = mag * t.y;
	*fz = mag * t.z;
	DynamicCLForceCandidateX = *fx;
	DynamicCLForceCandidateY = *fy;
	DynamicCLForceCandidateZ = *fz;
	DynamicCLForceCandidateMag = fabs(mag);
	DynamicCLActive = 1.0;  // accepted: node is in contact-line band with usable R_theta
}

// ================================================================
// Layer 1 (Wang 2025): boundary-fluid corrected gradient
// ================================================================

// Check if this node is a fluid node adjacent to a boundary/wall node.
CudaDeviceFunction int stage13_is_fluid_boundary_node()
{
	if (IamWall || IamSolid) return 0;
	// Check 6 face neighbours for IsBoundary
	if (IsBoundary(1,0,0) > 0.5) return 1;
	if (IsBoundary(-1,0,0) > 0.5) return 1;
	if (IsBoundary(0,1,0) > 0.5) return 1;
	if (IsBoundary(0,-1,0) > 0.5) return 1;
	if (IsBoundary(0,0,1) > 0.5) return 1;
	if (IsBoundary(0,0,-1) > 0.5) return 1;
	return 0;
}

// ================================================================
// Stage 15B fix: wetting-wall context lookup.
//
// Problem being fixed: calcDynamicCLShadow runs on FLUID nodes, but
// `radAngle` is a zonal setting. The flat-wall case only sets the target
// angle in the FlatLowerY wall zone (y=0); fluid nodes (y>=1) read the
// global default (90 deg), so cos_eq = cos(radAngle) came out as 0 for the
// t30 case. The compact-ghost path is correct because it runs on the wall
// node itself and stores the zone-resolved angle into LocalRadAngle.
//
// This helper recovers the correct theta_eq for a fluid node by reading the
// LocalRadAngle stored on an adjacent WETTING wall node (one that has
// AnalyticFlag>0, i.e. close to the analytic solid surface). OuterDomain
// walls have AnalyticFlag=0 (they are far from the analytic y=0 plane), so
// they are correctly rejected here even though they are also boundary nodes.
//
// IMPLEMENTATION NOTE: TCLB's IsBoundary/AnalyticFlag/LocalRadAngle field
// accesses expand to LatticeAccess<range_int<...>> template parameters and
// therefore require COMPILE-TIME CONSTANT offsets. A runtime loop or a
// helper function taking int (dx,dy,dz) parameters CANNOT be instantiated
// (nvcc: "no instance of overloaded load_* matches the argument list /
// expression must have a constant value"). So the 6 face offsets are written
// out as literals here, and the three tests are inlined per offset rather
// than factored into a variable-argument helper. This is sufficient for the
// flat-wall contact line (reached through a face neighbour). Curved-surface
// compact-stencil support, if ever needed, must enumerate any extra offsets
// as literals too, not via a loop.
//
// Returns 1 if a usable wetting-wall neighbour was found, in which case
// *out_theta receives its LocalRadAngle; *out_dx/dy/dz receive its offset.
// Returns 0 otherwise (caller must block the node, NOT fall back to the
// local zonal radAngle, which would silently reintroduce the 90 deg bug).
// ================================================================
#define STAGE15_CHECK_FACE(OX,OY,OZ) \
	if (IsBoundary(OX,OY,OZ) > 0.5 && AnalyticFlag(OX,OY,OZ) > 0.5) { \
		real_t theta_ = LocalRadAngle(OX,OY,OZ); \
		if (theta_ > 1.0e-6 && theta_ < 3.14159265358979 - 1.0e-6) { \
			*out_theta = theta_; *out_dx = OX; *out_dy = OY; *out_dz = OZ; return 1; \
		} \
	}

CudaDeviceFunction int stage15_find_wetting_wall_context(
	real_t *out_theta, int *out_dx, int *out_dy, int *out_dz)
{
	STAGE15_CHECK_FACE( 1, 0, 0)
	STAGE15_CHECK_FACE(-1, 0, 0)
	STAGE15_CHECK_FACE( 0, 1, 0)
	STAGE15_CHECK_FACE( 0,-1, 0)
	STAGE15_CHECK_FACE( 0, 0, 1)
	STAGE15_CHECK_FACE( 0, 0,-1)
	return 0;
}
#undef STAGE15_CHECK_FACE

// Wang 2025 corrected gradient: replace the normal component of gradPhi
// on boundary fluid nodes with the value required by the equilibrium
// contact-angle relation, while preserving the tangential component.
CudaDeviceFunction vector_t calcGradPhiBoundaryCorrected(vector_t g_bulk)
{
	vector_t g = g_bulk;
	WallGradDeltaMag = 0.0;
	WallGradThetaApp = 0.0;

	if (WallGradMode < 0.5) return g;
	if (!stage13_is_fluid_boundary_node()) return g;

	// Obtain analytic wall normal and distance at this fluid node.
	real_t h_dist;
	vector_t n_w = stage9_analytic_wall_normal_and_distance(&h_dist);
	real_t nmag = sqrt(n_w.x*n_w.x + n_w.y*n_w.y + n_w.z*n_w.z);
	if (nmag < 1.0e-12) return g;
	// Only correct nodes close to the wall.
	real_t d_abs = fabs(h_dist);
	if (d_abs > 2.0) return g;

	// Normalise wall normal.
	n_w.x /= nmag; n_w.y /= nmag; n_w.z /= nmag;

	// Normalised phase q in [0,1].
	real_t pf = PhaseF(0,0,0);
	real_t pf_scale = PhaseField_h - PhaseField_l;
	if (fabs(pf_scale) < 1.0e-30) return g;
	real_t q = (pf - PhaseField_l) / pf_scale;
	if (q < 0.0) q = 0.0;
	if (q > 1.0) q = 1.0;

	// Skip pure-phase regions.
	if (q < WallGradContactLineEps || q > 1.0 - WallGradContactLineEps) return g;

	// Decompose bulk gradient into tangential and normal.
	real_t dotgn = g.x*n_w.x + g.y*n_w.y + g.z*n_w.z;
	vector_t g_t;
	g_t.x = g.x - dotgn*n_w.x;
	g_t.y = g.y - dotgn*n_w.y;
	g_t.z = g.z - dotgn*n_w.z;

	// Target normal gradient from equilibrium contact-angle relation.
	// n_w . grad(q) = -(4/W) cos(theta) q(1-q)
	real_t A_wet = 4.0 / IntWidth;
	real_t gn_target_q = -WallGradContactSign * A_wet * cos(radAngle) * q * (1.0 - q);
	real_t gn_target_pf = gn_target_q * pf_scale;

	// Apparent contact angle for diagnostics.
	real_t gmag = sqrt(g.x*g.x + g.y*g.y + g.z*g.z);
	if (gmag > 1.0e-14) {
		real_t cos_app = -(g.x*n_w.x + g.y*n_w.y + g.z*n_w.z) / gmag;
		if (cos_app < -1.0) cos_app = -1.0;
		if (cos_app > 1.0) cos_app = 1.0;
		WallGradThetaApp = acos(cos_app) * 180.0 / 3.14159265358979323846;
	}

	// Assemble corrected gradient.
	vector_t gc;
	gc.x = g_t.x + gn_target_pf * n_w.x;
	gc.y = g_t.y + gn_target_pf * n_w.y;
	gc.z = g_t.z + gn_target_pf * n_w.z;

	// Magnitude cap to prevent over-driving at low angles.
	real_t magc = sqrt(gc.x*gc.x + gc.y*gc.y + gc.z*gc.z);
	real_t ref_mag = gmag;
	if (fabs(pf_scale/IntWidth) > ref_mag) ref_mag = fabs(pf_scale/IntWidth);
	real_t cap = WallGradCapFactor * ref_mag;
	if (magc > cap && magc > 1.0e-14) {
		gc.x *= cap/magc; gc.y *= cap/magc; gc.z *= cap/magc;
	}

	// Record delta for diagnostics.
	real_t dx = gc.x - g.x, dy = gc.y - g.y, dz = gc.z - g.z;
	WallGradDeltaMag = sqrt(dx*dx + dy*dy + dz*dz);

	return gc;
}

// ================================================================
// Layer 2 (Ju 2024): wall free-energy chemical potential source
// ================================================================

// Compute mu_wall = -a_v * sqrt(2*kappa*beta) * cos(theta) * q*(1-q)
// where sqrt(2*kappa*beta) = 6*sigma in the current TCLB convention.
CudaDeviceFunction real_t calcWallMuSource(real_t C)
{
	if (WallMuMode < 0.5) return 0.0;
	if (IamWall || IamSolid) return 0.0;
	if (!stage13_is_fluid_boundary_node()) return 0.0;

	real_t h_dist;
	vector_t n_w = stage9_analytic_wall_normal_and_distance(&h_dist);
	real_t nmag = sqrt(n_w.x*n_w.x + n_w.y*n_w.y + n_w.z*n_w.z);
	if (nmag < 1.0e-12) return 0.0;
	if (fabs(h_dist) > 2.0) return 0.0;

	real_t pf_scale = PhaseField_h - PhaseField_l;
	if (fabs(pf_scale) < 1.0e-30) return 0.0;
	real_t q = (C - PhaseField_l) / pf_scale;
	if (q < 0.0) q = 0.0;
	if (q > 1.0) q = 1.0;
	if (q < WallMuContactLineEps || q > 1.0 - WallMuContactLineEps) return 0.0;

	// Effective surface area a_v: approximate with IsBoundary gradient magnitude.
	real_t av = 0.0;
	av += fabs(IsBoundary(1,0,0) - IsBoundary(-1,0,0));
	av += fabs(IsBoundary(0,1,0) - IsBoundary(0,-1,0));
	av += fabs(IsBoundary(0,0,1) - IsBoundary(0,0,-1));
	av *= 0.5;  // first-order difference
	real_t av_cap = 2.0 / IntWidth;
	if (av > av_cap) av = av_cap;
	if (av < 1.0e-14) return 0.0;

	// mu_wall = -a_v * 6*sigma * cos(theta) * q*(1-q) / pf_scale
	real_t mu_wall = -WallMuScale * av * 6.0 * sigma * cos(radAngle) * q * (1.0 - q);
	mu_wall /= pf_scale;

	return mu_wall;
}


/*
	This function uses isotropic gradient stencils to return
	the gradient of the phase field variable \phi.
*/
CudaDeviceFunction vector_t calcGradPhiRaw()
{
	vector_t gradPhi = {0.0,0.0,0.0};
	#ifdef OPTIONS_OutFlow
		if ((NodeType & NODE_BOUNDARY) == NODE_ENeumann || (NodeType & NODE_BOUNDARY) == NODE_EConvect) {
			gradPhi.x = 0.0;
			gradPhi.y = 16.00 * (STAGE13_PHASE_FOR_STENCIL(0,1,0) - STAGE13_PHASE_FOR_STENCIL(0,-1,0))
						+ 2.0*(STAGE13_PHASE_FOR_STENCIL(-1,1,1) - STAGE13_PHASE_FOR_STENCIL(-1,-1,1)
						+ STAGE13_PHASE_FOR_STENCIL(-1,1,-1)- STAGE13_PHASE_FOR_STENCIL(-1,-1,-1))
						+  4.00 * (2.0*( STAGE13_PHASE_FOR_STENCIL(-1,1,0) - STAGE13_PHASE_FOR_STENCIL(-1,-1,0))
							+  STAGE13_PHASE_FOR_STENCIL(0,1,1) - STAGE13_PHASE_FOR_STENCIL(0,-1,1) + STAGE13_PHASE_FOR_STENCIL(0,1,-1) - STAGE13_PHASE_FOR_STENCIL(0,-1,-1));
			gradPhi.z = 16.00 * (STAGE13_PHASE_FOR_STENCIL(0,0,1) - STAGE13_PHASE_FOR_STENCIL(0,0,-1))
						+ 2.0*( STAGE13_PHASE_FOR_STENCIL(-1,1,1) + STAGE13_PHASE_FOR_STENCIL(-1,-1,1)
						-  STAGE13_PHASE_FOR_STENCIL(-1,1,-1)- STAGE13_PHASE_FOR_STENCIL(-1,-1,-1))
						+  4.00 * (2.0*( STAGE13_PHASE_FOR_STENCIL(-1,0,1) - STAGE13_PHASE_FOR_STENCIL(-1,0,-1))
							+  STAGE13_PHASE_FOR_STENCIL(0,1,1) + STAGE13_PHASE_FOR_STENCIL(0,-1,1) - STAGE13_PHASE_FOR_STENCIL(0,1,-1) - STAGE13_PHASE_FOR_STENCIL(0,-1,-1));
		} else if ((NodeType & NODE_BOUNDARY) == NODE_WNeumann || (NodeType & NODE_BOUNDARY) == NODE_WConvect) {
			gradPhi.x = 0.0;
			gradPhi.y = 16.00 * (STAGE13_PHASE_FOR_STENCIL(0,1,0) - STAGE13_PHASE_FOR_STENCIL(0,-1,0))
						+ 2.0*(STAGE13_PHASE_FOR_STENCIL(1,1,1) - STAGE13_PHASE_FOR_STENCIL(1,-1,1)
						+ STAGE13_PHASE_FOR_STENCIL(1,1,-1)- STAGE13_PHASE_FOR_STENCIL(1,-1,-1))
						+  4.00 * (2.0*( STAGE13_PHASE_FOR_STENCIL(1,1,0) - STAGE13_PHASE_FOR_STENCIL(1,-1,0))
							+  STAGE13_PHASE_FOR_STENCIL(0,1,1) - STAGE13_PHASE_FOR_STENCIL(0,-1,1) + STAGE13_PHASE_FOR_STENCIL(0,1,-1) - STAGE13_PHASE_FOR_STENCIL(0,-1,-1));
			gradPhi.z = 16.00 * (STAGE13_PHASE_FOR_STENCIL(0,0,1) - STAGE13_PHASE_FOR_STENCIL(0,0,-1))
						+ 2.0*( STAGE13_PHASE_FOR_STENCIL(1,1,1) + STAGE13_PHASE_FOR_STENCIL(1,-1,1)
						-  STAGE13_PHASE_FOR_STENCIL(1,1,-1)- STAGE13_PHASE_FOR_STENCIL(1,-1,-1))
						+  4.00 * (2.0*( STAGE13_PHASE_FOR_STENCIL(1,0,1) - STAGE13_PHASE_FOR_STENCIL(1,0,-1))
							+  STAGE13_PHASE_FOR_STENCIL(0,1,1) + STAGE13_PHASE_FOR_STENCIL(0,-1,1) - STAGE13_PHASE_FOR_STENCIL(0,1,-1) - STAGE13_PHASE_FOR_STENCIL(0,-1,-1));
		} else if ((NodeType & NODE_BOUNDARY)) {
			gradPhi.x = 0.0;gradPhi.y = 0.0;gradPhi.z = 0.0;
		} else {
			gradPhi.y = 16.00 * (STAGE13_PHASE_FOR_STENCIL(0,1,0) - STAGE13_PHASE_FOR_STENCIL(0,-1,0)) + STAGE13_PHASE_FOR_STENCIL(1,1,1) + STAGE13_PHASE_FOR_STENCIL(-1,1,1) - STAGE13_PHASE_FOR_STENCIL(1,-1,1) - STAGE13_PHASE_FOR_STENCIL(-1,-1,1) + STAGE13_PHASE_FOR_STENCIL(1,1,-1)+ STAGE13_PHASE_FOR_STENCIL(-1,1,-1)- STAGE13_PHASE_FOR_STENCIL(1,-1,-1)- STAGE13_PHASE_FOR_STENCIL(-1,-1,-1) +  4.00 * (STAGE13_PHASE_FOR_STENCIL(1,1,0) + STAGE13_PHASE_FOR_STENCIL(-1,1,0) - STAGE13_PHASE_FOR_STENCIL(1,-1,0) - STAGE13_PHASE_FOR_STENCIL(-1,-1,0) +  STAGE13_PHASE_FOR_STENCIL(0,1,1) - STAGE13_PHASE_FOR_STENCIL(0,-1,1) + STAGE13_PHASE_FOR_STENCIL(0,1,-1) - STAGE13_PHASE_FOR_STENCIL(0,-1,-1));
gradPhi.x = 16.00 * (STAGE13_PHASE_FOR_STENCIL(1,0,0) - STAGE13_PHASE_FOR_STENCIL(-1,0,0)) + STAGE13_PHASE_FOR_STENCIL(1,1,1) - STAGE13_PHASE_FOR_STENCIL(-1,1,1) + STAGE13_PHASE_FOR_STENCIL(1,-1,1) - STAGE13_PHASE_FOR_STENCIL(-1,-1,1) + STAGE13_PHASE_FOR_STENCIL(1,1,-1)- STAGE13_PHASE_FOR_STENCIL(-1,1,-1) + STAGE13_PHASE_FOR_STENCIL(1,-1,-1) - STAGE13_PHASE_FOR_STENCIL(-1,-1,-1) +  4.00 * (STAGE13_PHASE_FOR_STENCIL(1,1,0) - STAGE13_PHASE_FOR_STENCIL(-1,1,0) + STAGE13_PHASE_FOR_STENCIL(1,-1,0) - STAGE13_PHASE_FOR_STENCIL(-1,-1,0) + STAGE13_PHASE_FOR_STENCIL(1,0,1) - STAGE13_PHASE_FOR_STENCIL(-1,0,1) + STAGE13_PHASE_FOR_STENCIL(1,0,-1) - STAGE13_PHASE_FOR_STENCIL(-1,0,-1));
gradPhi.z = 16.00 * (STAGE13_PHASE_FOR_STENCIL(0,0,1) - STAGE13_PHASE_FOR_STENCIL(0,0,-1)) + STAGE13_PHASE_FOR_STENCIL(1,1,1) + STAGE13_PHASE_FOR_STENCIL(-1,1,1) + STAGE13_PHASE_FOR_STENCIL(1,-1,1) + STAGE13_PHASE_FOR_STENCIL(-1,-1,1) - STAGE13_PHASE_FOR_STENCIL(1,1,-1)- STAGE13_PHASE_FOR_STENCIL(-1,1,-1)- STAGE13_PHASE_FOR_STENCIL(1,-1,-1)- STAGE13_PHASE_FOR_STENCIL(-1,-1,-1) +  4.00 * (STAGE13_PHASE_FOR_STENCIL(1,0,1) + STAGE13_PHASE_FOR_STENCIL(-1,0,1) - STAGE13_PHASE_FOR_STENCIL(1,0,-1) - STAGE13_PHASE_FOR_STENCIL(-1,0,-1) +  STAGE13_PHASE_FOR_STENCIL(0,1,1) + STAGE13_PHASE_FOR_STENCIL(0,-1,1) - STAGE13_PHASE_FOR_STENCIL(0,1,-1) - STAGE13_PHASE_FOR_STENCIL(0,-1,-1));
gradPhi.x /= 72.0;
gradPhi.y /= 72.0;
gradPhi.z /= 72.0;

		}
	#else
		    gradPhi.y = 16.00 * (STAGE13_PHASE_FOR_STENCIL(0,1,0) - STAGE13_PHASE_FOR_STENCIL(0,-1,0)) + STAGE13_PHASE_FOR_STENCIL(1,1,1) + STAGE13_PHASE_FOR_STENCIL(-1,1,1) - STAGE13_PHASE_FOR_STENCIL(1,-1,1) - STAGE13_PHASE_FOR_STENCIL(-1,-1,1) + STAGE13_PHASE_FOR_STENCIL(1,1,-1)+ STAGE13_PHASE_FOR_STENCIL(-1,1,-1)- STAGE13_PHASE_FOR_STENCIL(1,-1,-1)- STAGE13_PHASE_FOR_STENCIL(-1,-1,-1) +  4.00 * (STAGE13_PHASE_FOR_STENCIL(1,1,0) + STAGE13_PHASE_FOR_STENCIL(-1,1,0) - STAGE13_PHASE_FOR_STENCIL(1,-1,0) - STAGE13_PHASE_FOR_STENCIL(-1,-1,0) +  STAGE13_PHASE_FOR_STENCIL(0,1,1) - STAGE13_PHASE_FOR_STENCIL(0,-1,1) + STAGE13_PHASE_FOR_STENCIL(0,1,-1) - STAGE13_PHASE_FOR_STENCIL(0,-1,-1));
gradPhi.x = 16.00 * (STAGE13_PHASE_FOR_STENCIL(1,0,0) - STAGE13_PHASE_FOR_STENCIL(-1,0,0)) + STAGE13_PHASE_FOR_STENCIL(1,1,1) - STAGE13_PHASE_FOR_STENCIL(-1,1,1) + STAGE13_PHASE_FOR_STENCIL(1,-1,1) - STAGE13_PHASE_FOR_STENCIL(-1,-1,1) + STAGE13_PHASE_FOR_STENCIL(1,1,-1)- STAGE13_PHASE_FOR_STENCIL(-1,1,-1) + STAGE13_PHASE_FOR_STENCIL(1,-1,-1) - STAGE13_PHASE_FOR_STENCIL(-1,-1,-1) +  4.00 * (STAGE13_PHASE_FOR_STENCIL(1,1,0) - STAGE13_PHASE_FOR_STENCIL(-1,1,0) + STAGE13_PHASE_FOR_STENCIL(1,-1,0) - STAGE13_PHASE_FOR_STENCIL(-1,-1,0) + STAGE13_PHASE_FOR_STENCIL(1,0,1) - STAGE13_PHASE_FOR_STENCIL(-1,0,1) + STAGE13_PHASE_FOR_STENCIL(1,0,-1) - STAGE13_PHASE_FOR_STENCIL(-1,0,-1));
gradPhi.z = 16.00 * (STAGE13_PHASE_FOR_STENCIL(0,0,1) - STAGE13_PHASE_FOR_STENCIL(0,0,-1)) + STAGE13_PHASE_FOR_STENCIL(1,1,1) + STAGE13_PHASE_FOR_STENCIL(-1,1,1) + STAGE13_PHASE_FOR_STENCIL(1,-1,1) + STAGE13_PHASE_FOR_STENCIL(-1,-1,1) - STAGE13_PHASE_FOR_STENCIL(1,1,-1)- STAGE13_PHASE_FOR_STENCIL(-1,1,-1)- STAGE13_PHASE_FOR_STENCIL(1,-1,-1)- STAGE13_PHASE_FOR_STENCIL(-1,-1,-1) +  4.00 * (STAGE13_PHASE_FOR_STENCIL(1,0,1) + STAGE13_PHASE_FOR_STENCIL(-1,0,1) - STAGE13_PHASE_FOR_STENCIL(1,0,-1) - STAGE13_PHASE_FOR_STENCIL(-1,0,-1) +  STAGE13_PHASE_FOR_STENCIL(0,1,1) + STAGE13_PHASE_FOR_STENCIL(0,-1,1) - STAGE13_PHASE_FOR_STENCIL(0,1,-1) - STAGE13_PHASE_FOR_STENCIL(0,-1,-1));
gradPhi.x /= 72.0;
gradPhi.y /= 72.0;
gradPhi.z /= 72.0;

	#endif
	return gradPhi;
}

// Layer 1 wrapper: apply Wang 2025 boundary-fluid corrected gradient.
CudaDeviceFunction vector_t calcGradPhi()
{
	vector_t g = calcGradPhiRaw();
	if (WallGradMode > 0.5) {
		vector_t gc = calcGradPhiBoundaryCorrected(g);
		// Stage 15B-pre safety cleanup: WallGradMode is now DIAGNOSTIC ONLY.
		// calcGradPhiBoundaryCorrected still updates its diagnostic fields
		// (WallGradDeltaMag, WallGradThetaApp) inside the helper, but the
		// corrected gradient gc is NEVER returned to the dynamics. Returning gc
		// (the old WallGradMode>=2 write path) replaces gradPhi with the static
		// equilibrium contact-angle gradient and erases the non-equilibrium
		// residual that drives contact-line motion; this was disproven by the
		// decoupled direction tests. The compact ghost (consumed in
		// stage13_select_phase_for_stencil) remains the sole wall-phase source.
	}
	return g;
}

/*
	This function is run as the second stage of each action and fills
	the iteration buffer with updated values of PhaseF.
*/
CudaDeviceFunction void calcPhaseF()
{
	updateBoundary();
	// NOTE: On the wall we want to take the previous value of the phase field, because
	// it might be needed for calculation of the gradient
	ReplayPhaseFromH = 0.0;
	if (!( IamWall || IamSolid )) {
		real_t phase_from_h = h26 + h25 + h24 + h23 + h22 + h21 + h20 + h19 + h18 + h17 + h16 + h15 + h14 + h13 + h12 + h11 + h10 + h9 + h8 + h7 + h6 + h5 + h4 + h3 + h2 + h1 + h0;
		PhaseF = phase_from_h;
		ReplayPhaseFromH = phase_from_h;
	} else {
		PhaseF = PhaseF(0,0,0);
	}
}

/*
	Calculate the chemical potential, mu
	Eqn. 5 in: Improved locality of the phase-field lattice-Boltzmann model
	for immiscible fluids at high density ratios
*/
CudaDeviceFunction real_t calcMu(real_t C)
{
	real_t pfavg, lpPhi, mu;
	pfavg = 0.5*(PhaseField_l+PhaseField_h);
	#ifdef OPTIONS_OutFlow
		if ((NodeType & NODE_BOUNDARY) == NODE_ENeumann || (NodeType & NODE_BOUNDARY) == NODE_EConvect) {
			lpPhi = 16.0 *( 2.0* STAGE13_PHASE_FOR_STENCIL(-1,0,0)
						+ (STAGE13_PHASE_FOR_STENCIL(0,1,0)) + (STAGE13_PHASE_FOR_STENCIL(0,-1,0))
						+ (STAGE13_PHASE_FOR_STENCIL(0,0,1)) + (STAGE13_PHASE_FOR_STENCIL(0,0,-1)))
					+ 1.0 *(  2.0*(STAGE13_PHASE_FOR_STENCIL(-1,1,1)
						+ (STAGE13_PHASE_FOR_STENCIL(-1,-1,1))
							+ (STAGE13_PHASE_FOR_STENCIL(-1,1,-1))
							+ (STAGE13_PHASE_FOR_STENCIL(-1,-1,-1))))
					+ 4.0 *(2.0*( (STAGE13_PHASE_FOR_STENCIL(-1,1,0))
						+ (STAGE13_PHASE_FOR_STENCIL(-1,-1,0))
						+ (STAGE13_PHASE_FOR_STENCIL(-1,0,1))
						+ (STAGE13_PHASE_FOR_STENCIL(-1,0,-1)))
						+ (STAGE13_PHASE_FOR_STENCIL(0,1,1)) + (STAGE13_PHASE_FOR_STENCIL(0,-1,1))
						+ (STAGE13_PHASE_FOR_STENCIL(0,1,-1))+ (STAGE13_PHASE_FOR_STENCIL(0,-1,-1)))
				- 152.0 * STAGE13_PHASE_FOR_STENCIL(0,0,0);
		} else if ((NodeType & NODE_BOUNDARY) == NODE_WNeumann || (NodeType & NODE_BOUNDARY) == NODE_WConvect) {
			lpPhi = 16.0 *( 2.0* STAGE13_PHASE_FOR_STENCIL(1,0,0)
						+ (STAGE13_PHASE_FOR_STENCIL(0,1,0)) + (STAGE13_PHASE_FOR_STENCIL(0,-1,0))
						+ (STAGE13_PHASE_FOR_STENCIL(0,0,1)) + (STAGE13_PHASE_FOR_STENCIL(0,0,-1)))
					+ 1.0 *(  2.0*(STAGE13_PHASE_FOR_STENCIL(1,1,1)
						+ (STAGE13_PHASE_FOR_STENCIL(1,-1,1))
							+ (STAGE13_PHASE_FOR_STENCIL(1,1,-1))
							+ (STAGE13_PHASE_FOR_STENCIL(1,-1,-1))))
					+ 4.0 *(2.0*( (STAGE13_PHASE_FOR_STENCIL(1,1,0))
						+ (STAGE13_PHASE_FOR_STENCIL(1,-1,0))
						+ (STAGE13_PHASE_FOR_STENCIL(1,0,1))
						+ (STAGE13_PHASE_FOR_STENCIL(1,0,-1)))
						+ (STAGE13_PHASE_FOR_STENCIL(0,1,1)) + (STAGE13_PHASE_FOR_STENCIL(0,-1,1))
						+ (STAGE13_PHASE_FOR_STENCIL(0,1,-1))+ (STAGE13_PHASE_FOR_STENCIL(0,-1,-1)))
				- 152.0 * STAGE13_PHASE_FOR_STENCIL(0,0,0);
		} else if ((NodeType & NODE_BOUNDARY)) {
			// If single phase inlet/outlet, dont want periodic bounds
			// to interfere - can cause waves/instabilities
			lpPhi = 0.0;
		} else {
			lpPhi = 16.0 *((STAGE13_PHASE_FOR_STENCIL(1,0,0)) + (STAGE13_PHASE_FOR_STENCIL(-1,0,0)) + (STAGE13_PHASE_FOR_STENCIL(0,1,0)) + (STAGE13_PHASE_FOR_STENCIL(0,-1,0))+ (STAGE13_PHASE_FOR_STENCIL(0,0,1)) + (STAGE13_PHASE_FOR_STENCIL(0,0,-1)))	+ 1.0 *((STAGE13_PHASE_FOR_STENCIL(1,1,1)) + (STAGE13_PHASE_FOR_STENCIL(-1,1,1)) + (STAGE13_PHASE_FOR_STENCIL(1,-1,1))+ (STAGE13_PHASE_FOR_STENCIL(-1,-1,1)) + (STAGE13_PHASE_FOR_STENCIL(1,1,-1))+ (STAGE13_PHASE_FOR_STENCIL(-1,1,-1)) + (STAGE13_PHASE_FOR_STENCIL(1,-1,-1))+(STAGE13_PHASE_FOR_STENCIL(-1,-1,-1))) + 4.0 *((STAGE13_PHASE_FOR_STENCIL(1,1,0)) + (STAGE13_PHASE_FOR_STENCIL(-1,1,0))+ (STAGE13_PHASE_FOR_STENCIL(1,-1,0))+ (STAGE13_PHASE_FOR_STENCIL(-1,-1,0))+ (STAGE13_PHASE_FOR_STENCIL(1,0,1)) + (STAGE13_PHASE_FOR_STENCIL(-1,0,1))+ (STAGE13_PHASE_FOR_STENCIL(1,0,-1))+ (STAGE13_PHASE_FOR_STENCIL(-1,0,-1))+ (STAGE13_PHASE_FOR_STENCIL(0,1,1)) + (STAGE13_PHASE_FOR_STENCIL(0,-1,1))+ (STAGE13_PHASE_FOR_STENCIL(0,1,-1))+ (STAGE13_PHASE_FOR_STENCIL(0,-1,-1))) - 152.0 * STAGE13_PHASE_FOR_STENCIL(0,0,0);
lpPhi/= 36.0;

		}
	#else
			lpPhi = 16.0 *((STAGE13_PHASE_FOR_STENCIL(1,0,0)) + (STAGE13_PHASE_FOR_STENCIL(-1,0,0)) + (STAGE13_PHASE_FOR_STENCIL(0,1,0)) + (STAGE13_PHASE_FOR_STENCIL(0,-1,0))+ (STAGE13_PHASE_FOR_STENCIL(0,0,1)) + (STAGE13_PHASE_FOR_STENCIL(0,0,-1)))	+ 1.0 *((STAGE13_PHASE_FOR_STENCIL(1,1,1)) + (STAGE13_PHASE_FOR_STENCIL(-1,1,1)) + (STAGE13_PHASE_FOR_STENCIL(1,-1,1))+ (STAGE13_PHASE_FOR_STENCIL(-1,-1,1)) + (STAGE13_PHASE_FOR_STENCIL(1,1,-1))+ (STAGE13_PHASE_FOR_STENCIL(-1,1,-1)) + (STAGE13_PHASE_FOR_STENCIL(1,-1,-1))+(STAGE13_PHASE_FOR_STENCIL(-1,-1,-1))) + 4.0 *((STAGE13_PHASE_FOR_STENCIL(1,1,0)) + (STAGE13_PHASE_FOR_STENCIL(-1,1,0))+ (STAGE13_PHASE_FOR_STENCIL(1,-1,0))+ (STAGE13_PHASE_FOR_STENCIL(-1,-1,0))+ (STAGE13_PHASE_FOR_STENCIL(1,0,1)) + (STAGE13_PHASE_FOR_STENCIL(-1,0,1))+ (STAGE13_PHASE_FOR_STENCIL(1,0,-1))+ (STAGE13_PHASE_FOR_STENCIL(-1,0,-1))+ (STAGE13_PHASE_FOR_STENCIL(0,1,1)) + (STAGE13_PHASE_FOR_STENCIL(0,-1,1))+ (STAGE13_PHASE_FOR_STENCIL(0,1,-1))+ (STAGE13_PHASE_FOR_STENCIL(0,-1,-1))) - 152.0 * STAGE13_PHASE_FOR_STENCIL(0,0,0);
lpPhi/= 36.0;

	#endif
	#ifdef OPTIONS_thermo
		mu = 4.0*(12.0*SurfaceTension(0,0,0)/IntWidth)*(C-PhaseField_l)*(C-PhaseField_h)*(C-pfavg)
			- (1.5 *SurfaceTension(0,0,0)*IntWidth) * lpPhi;
	#else
		mu = 4.0*(12.0*sigma/IntWidth)*(C-PhaseField_l)*(C-PhaseField_h)*(C-pfavg)
			- (1.5 *sigma*IntWidth) * lpPhi;
	#endif
	// Layer 2 (Ju 2024): wall free-energy chemical potential source.
	if (WallMuMode > 0.5) {
		real_t mu_wall = calcWallMuSource(C);
		WallMuCandidate = mu_wall;
		if (WallMuMode > 1.5) mu += mu_wall;
	} else {
		WallMuCandidate = 0.0;
	}
	if (stage16_replay_diagnostics_active()) {
		ReplayLapPhi = lpPhi;
		ReplayMu = mu;
	}
	return mu;
}

/*
	Eqn. 10 in: Improved locality of the phase-field lattice-Boltzmann model
	for immiscible fluids at high density ratios
*/
CudaDeviceFunction real_t calcGamma(int i, real_t u, real_t v, real_t w, real_t u2mag)
{
	real_t gamma, tmp;
	tmp = (d3q27_ex[i]*u+d3q27_ey[i]*v+d3q27_ez[i]*w);

	gamma = wg[i] * (1 + 3.0*(tmp) + 4.5*(tmp*tmp) - 1.5*(u2mag)) ;
	return gamma;
}

/*
	Eqn. 7 in: Improved locality of the phase-field lattice-Boltzmann model
	for immiscible fluids at high density ratios
*/
CudaDeviceFunction real_t calcF_phi(int i, real_t tmp1, real_t nx, real_t ny, real_t nz)
{
	real_t f_phi;
	#ifdef OPTIONS_q27
		f_phi = wg[i] * tmp1 * (d3q27_ex[i]*nx + d3q27_ey[i]*ny + d3q27_ez[i]*nz);
	#else
		f_phi = wh[i] * tmp1 * (d3q27_ex[i]*nx + d3q27_ey[i]*ny + d3q27_ez[i]*nz);
	#endif
	return f_phi;
}

CudaDeviceFunction real_t sphereTail_max(real_t a, real_t b)
{
	return (a > b) ? a : b;
}

CudaDeviceFunction real_t sphereTail_min(real_t a, real_t b)
{
	return (a < b) ? a : b;
}

CudaDeviceFunction real_t sphereTail_sphereBelowVolume(real_t radius, real_t z_join)
{
	return PI * (radius*radius*z_join - z_join*z_join*z_join/3.0 + 2.0*radius*radius*radius/3.0);
}

CudaDeviceFunction real_t sphereTail_compositeVolume(real_t body_radius, real_t tail_radius, real_t tail_length)
{
	if (tail_radius <= 0.0 || tail_length <= 0.0) {
		return 4.0*PI*body_radius*body_radius*body_radius/3.0;
	}
	if (body_radius <= tail_radius) {
		return 1.0e300;
	}
	real_t z_join = sqrt(body_radius*body_radius - tail_radius*tail_radius);
	return sphereTail_sphereBelowVolume(body_radius, z_join)
	     + PI*tail_radius*tail_radius*tail_length;
}

CudaDeviceFunction real_t sphereTail_solveBodyRadius(real_t reference_radius, real_t tail_radius, real_t tail_length)
{
	if (tail_radius <= 0.0 || tail_length <= 0.0) return reference_radius;

	real_t target = 4.0*PI*reference_radius*reference_radius*reference_radius/3.0;
	real_t low = tail_radius * (1.0 + 1.0e-9);
	if (low < 1.0e-12) low = 1.0e-12;
	real_t high = reference_radius;
	if (high <= low) high = low * 1.25;

	for (int i = 0; i < 80 && sphereTail_compositeVolume(high, tail_radius, tail_length) < target; i++) {
		high *= 1.05;
	}
	for (int i = 0; i < 80; i++) {
		real_t mid = 0.5*(low + high);
		if (sphereTail_compositeVolume(mid, tail_radius, tail_length) < target) {
			low = mid;
		} else {
			high = mid;
		}
	}
	return 0.5*(low + high);
}

CudaDeviceFunction real_t sphereTail_topCappedCylinderSignedDistance(real_t radial, real_t z_local, real_t tail_radius, real_t z_join, real_t tail_length)
{
	real_t z_top = z_join + tail_length;
	real_t qx = radial - tail_radius;
	real_t qz = z_local - z_top;
	if (z_local <= z_top) {
		return sphereTail_max(qx, qz);
	}
	real_t ox = sphereTail_max(qx, 0.0);
	return sqrt(ox*ox + qz*qz);
}

CudaDeviceFunction real_t sphereTail_signedDistance(real_t body_radius, real_t tail_radius, real_t tail_length)
{
	real_t x_local = X - CenterX;
	real_t y_local = Y - CenterY;
	real_t z_local = Z - CenterZ;
	real_t radial = sqrt(x_local*x_local + y_local*y_local);
	real_t sphere_sdf = sqrt(x_local*x_local + y_local*y_local + z_local*z_local) - body_radius;

	if (tail_radius <= 0.0 || tail_length <= 0.0 || body_radius <= tail_radius) return sphere_sdf;

	real_t z_join = sqrt(body_radius*body_radius - tail_radius*tail_radius);
	real_t truncated_sphere_sdf = sphereTail_max(sphere_sdf, z_local - z_join);
	real_t cylinder_sdf = 1.0e30;
	if (z_local >= z_join) {
		cylinder_sdf = sphereTail_topCappedCylinderSignedDistance(radial, z_local, tail_radius, z_join, tail_length);
	}
	return sphereTail_min(truncated_sphere_sdf, cylinder_sdf);
}

CudaDeviceFunction real_t sphereTail_tailVelocityWeight(real_t body_radius, real_t tail_radius, real_t tail_length, real_t velocity_mode)
{
	if (tail_radius <= 0.0 || tail_length <= 0.0 || body_radius <= tail_radius) return 0.0;

	real_t x_local = X - CenterX;
	real_t y_local = Y - CenterY;
	real_t z_local = Z - CenterZ;
	real_t radial = sqrt(x_local*x_local + y_local*y_local);
	real_t z_join = sqrt(body_radius*body_radius - tail_radius*tail_radius);
	real_t axial = (z_local - z_join) / tail_length;
	if (axial <= 0.0 || axial > 1.0) return 0.0;

	real_t radial_weight = 0.5*(1.0 - tanh(2.0*(radial - tail_radius)/IntWidth));
	real_t top_weight = 0.5*(1.0 - tanh(2.0*(z_local - (z_join + tail_length))/IntWidth));
	real_t axial_weight = (velocity_mode > 1.5) ? axial : 1.0;
	real_t weight = axial_weight * radial_weight * top_weight;
	if (weight < 0.0) weight = 0.0;
	if (weight > 1.0) weight = 1.0;
	return weight;
}

/*	INITIALISATION:	*/
CudaDeviceFunction void Init()
{
	PhaseF = PhaseField;
	specialCases_Init();
	if ( IamWall || IamSolid ) PhaseF = -999;

	if (developedFlow > 0.1) {
		U = 6.0 * Uavg * Y*(HEIGHT - Y)/(HEIGHT*HEIGHT);
		V = 0.0;
		W = 0.0;
	} else if ( developedPipeFlow_X > 0.1 ){
		U = 2.0 * Uavg * (1 - pow( (sqrt(pow((Y-pipeCentre_Y),2) + pow((Z-pipeCentre_Z),2)) / pipeRadius),2));
		V = 0.0;
		W = 0.0;
	} else {
		U = VelocityX;	V = VelocityY;	W = VelocityZ;
	}

	if (DropletOnlyVelocity > 0.5) {
		real_t pf_mid = 0.5*(PhaseField_h + PhaseField_l);
		real_t liquid_fraction = (PhaseF - PhaseField_l)/(PhaseField_h - PhaseField_l);
		if (liquid_fraction < 0.0) liquid_fraction = 0.0;
		if (liquid_fraction > 1.0) liquid_fraction = 1.0;
		real_t droplet_fraction = (BubbleType >= 0.0) ? liquid_fraction : (1.0 - liquid_fraction);
		if (DropletOnlyVelocity > 1.5) {
			U = droplet_fraction * DropletVelocityX;
			V = droplet_fraction * DropletVelocityY;
			W = droplet_fraction * DropletVelocityZ;
		} else {
			int in_droplet = (BubbleType >= 0.0 && PhaseF > pf_mid) ||
			                 (BubbleType <  0.0 && PhaseF < pf_mid);
			if (in_droplet) {
				U = DropletVelocityX;
				V = DropletVelocityY;
				W = DropletVelocityZ;
			} else {
				U = 0.0;
				V = 0.0;
				W = 0.0;
			}
		}
	}

	if (CompositeDropletTailVelocityMode > 0.5 &&
	    CompositeDropletTailRadius > 0.0 &&
	    CompositeDropletTailLength > 0.0 &&
	    (CompositeDropletTailVelocityX != 0.0 ||
	     CompositeDropletTailVelocityY != 0.0 ||
	     CompositeDropletTailVelocityZ != 0.0)) {
		real_t body_radius = CompositeDropletBodyRadius;
		if (body_radius <= 0.0) {
			body_radius = sphereTail_solveBodyRadius(Radius, CompositeDropletTailRadius, CompositeDropletTailLength);
		}
		real_t tail_weight = sphereTail_tailVelocityWeight(body_radius, CompositeDropletTailRadius, CompositeDropletTailLength, CompositeDropletTailVelocityMode);
		U += tail_weight * CompositeDropletTailVelocityX;
		V += tail_weight * CompositeDropletTailVelocityY;
		W += tail_weight * CompositeDropletTailVelocityZ;
	}

	pnorm = 0.0; // initialise as zero and fill in later stage
}

CudaDeviceFunction void InitFromFieldsStage()
{
	PhaseF = Init_PhaseField_External;
	U = Init_UX_External;
	V = Init_UY_External;
	W = Init_UZ_External;
	if ( IamWall || IamSolid ) PhaseF = -999;
	pnorm = 0.0; // initialise as zero and fill in later stage
}

CudaDeviceFunction void specialCases_Init()
{
	#ifdef OPTIONS_thermo
		Temp   = T_init;
		if (fabs(dT) > 0){
			Temp = T_init + dT*Y;
		}
		if (fabs(dTx) > 0){
			Temp = T_init + dTx*X;
		}
		#ifdef OPTIONS_planarBenchmark
			if ( (NodeType & NODE_ADDITIONALS) == NODE_BWall) { //bottom wall
				real_t x, omega;
				x = (X-0.5) - myL;
				omega = 3.1415926535897 / myL;
				Temp = T_h + T_0 * cos(omega * x);
				printf("y,x=%.4lf,%.4lf\n", Y,x);
			} else if ( (NodeType & NODE_ADDITIONALS) == NODE_TWall) {
				Temp = T_c;
				printf("y,x=%.4lf,%.4lf\n", Y, X);
			}
			PhaseF = 0.5 + PLUSMINUS * (0.5) * tanh( (Y - MIDPOINT)/(IntWidth/2) );
		#endif
		if (surfPower > 1) {
			SurfaceTension = sigma + sigma_TT*pow((Temp(0,0,0) - T_ref),surfPower) * (1.0/surfPower);
		} else {
			SurfaceTension = sigma + sigma_T*(Temp(0,0,0) - T_ref);
		}
		Cond = interp(PhaseF, k_h, k_l);
	#endif
	// Pre-defined Initialisation patterns:
	// Diffuse interface sphere
	   // BubbleType = -1 refers to light fluid bubble.
        if ( Radius > 0 ){
                real_t Ri;
		if (CompositeDropletTailRadius > 0.0 && CompositeDropletTailLength > 0.0) {
			real_t body_radius = CompositeDropletBodyRadius;
			if (body_radius <= 0.0) {
				body_radius = sphereTail_solveBodyRadius(Radius, CompositeDropletTailRadius, CompositeDropletTailLength);
			}
			Ri = Radius + sphereTail_signedDistance(body_radius, CompositeDropletTailRadius, CompositeDropletTailLength);
		} else {
			Ri = sqrt( (X - CenterX)*(X - CenterX) + (Y - CenterY)*(Y - CenterY) + (Z - CenterZ)*(Z - CenterZ) );
		}
                PhaseF = 0.5*(PhaseField_h + PhaseField_l)
                       - 0.5*(PhaseField_h - PhaseField_l) * BubbleType * tanh(2 * (Ri - Radius)/IntWidth);
        }

	// Stage12 static-contact initializers. These are deliberately default-off
	// and only set the initial diffuse phase field. They do not change the
	// wall wetting law, and solid/wall nodes are still reset to -999 by Init().
	if (CapInit > 0.5 && CapInitRadius > 0.0) {
		real_t Ri = sqrt((X - CapInitCenterX)*(X - CapInitCenterX) +
		                 (Y - CapInitCenterY)*(Y - CapInitCenterY) +
		                 (Z - CapInitCenterZ)*(Z - CapInitCenterZ));
		PhaseF = PhaseField_l + 0.5*(PhaseField_h - PhaseField_l) *
		         (1.0 - tanh(2.0*(Ri - CapInitRadius)/IntWidth));
	}

	if (SphereCapInit > 0.5 && SphereCapInitParentRadius > 0.0 && SphereCapInitSolidRadius > 0.0) {
		real_t Ri = sqrt((X - SphereCapInitCenterX)*(X - SphereCapInitCenterX) +
		                 (Y - SphereCapInitCenterY)*(Y - SphereCapInitCenterY) +
		                 (Z - SphereCapInitCenterZ)*(Z - SphereCapInitCenterZ));
		real_t Rs = sqrt((X - SphereCapInitSolidCenterX)*(X - SphereCapInitSolidCenterX) +
		                 (Y - SphereCapInitSolidCenterY)*(Y - SphereCapInitSolidCenterY) +
		                 (Z - SphereCapInitSolidCenterZ)*(Z - SphereCapInitSolidCenterZ));
		real_t cap_pf = PhaseField_l + 0.5*(PhaseField_h - PhaseField_l) *
		                (1.0 - tanh(2.0*(Ri - SphereCapInitParentRadius)/IntWidth));
		PhaseF = (Rs < SphereCapInitSolidRadius) ? PhaseField_l : cap_pf;
	}

	if (CylinderCapInit > 0.5 && CylinderCapInitParentRadius > 0.0 && CylinderCapInitSolidRadius > 0.0) {
		real_t Ri = sqrt((X - CylinderCapInitCenterX)*(X - CylinderCapInitCenterX) +
		                 (Y - CylinderCapInitCenterY)*(Y - CylinderCapInitCenterY) +
		                 (Z - CylinderCapInitCenterZ)*(Z - CylinderCapInitCenterZ));
		real_t dxs = X - CylinderCapInitSolidCenterX;
		real_t dys = Y - CylinderCapInitSolidCenterY;
		real_t dzs = Z - CylinderCapInitSolidCenterZ;
		real_t radial;
		if (CylinderCapInitSolidAxis < 0.5) {
			radial = sqrt(dys*dys + dzs*dzs);
		} else if (CylinderCapInitSolidAxis < 1.5) {
			radial = sqrt(dxs*dxs + dzs*dzs);
		} else {
			radial = sqrt(dxs*dxs + dys*dys);
		}
		real_t cap_pf = PhaseField_l + 0.5*(PhaseField_h - PhaseField_l) *
		                (1.0 - tanh(2.0*(Ri - CylinderCapInitParentRadius)/IntWidth));
		PhaseF = (radial < CylinderCapInitSolidRadius) ? PhaseField_l : cap_pf;
	}

		// Rayleigh-Taylor Instability
	    // Initialises with a sharp interface
	if (RTI_Characteristic_Length > 0){
		real_t d = RTI_Characteristic_Length;
		real_t ycutoff;
        if (pseudo2D > 0.5){
			ycutoff = 2.0*d + 0.1*d*(cos(2.0*PI*X/d));
        } else {
			ycutoff = 2.0*d + 0.05*d*(cos(2.0*PI*X/d) + cos(2.0*PI*Z/d));
		}
		if (Y < ycutoff) {PhaseF = 0.0; }
		else             {PhaseF = 1.0;	}
	}
    // Annular Taylor bubble set up
	if ( DonutTime > 0){
		real_t intLocation = Donut_D *
					sqrt( pow(Donut_h,2)
					    - pow( DonutTime - sqrt(pow(Y-CenterY,2) + pow(Z-CenterZ,2)), 2) );
		real_t shifter = atan2( (Z-CenterZ), (Y-CenterY));
		if (shifter < 0) shifter = shifter + 2*PI;
		if (  (X < Donut_x0 + intLocation*sin(shifter/2)) && (X > Donut_x0 - intLocation) )
		{
			PhaseF = 0.0;
		} else {
			PhaseF = 1.0;
		}
	}
    // Washburn Law test setup
    if ((Washburn_start > 0) && (Washburn_end > 0) ) {
		PhaseF = 1 - 0.5 *  ( tanh( 2.0 * ( X - Washburn_start ) / IntWidth ) -
						   tanh( 2.0 * ( X - Washburn_end  )  / IntWidth ));
	}
}

CudaDeviceFunction void Init_distributions()
{
	// Initialise phase variables:
	int i;
	real_t C0 = 0.5*(PhaseField_h - PhaseField_l);
	PhaseF = PhaseF(0,0,0);
	real_t d = Density_l + (Density_h-Density_l) * (PhaseF - PhaseField_l)/(PhaseField_h - PhaseField_l);
    pnorm = Pressure / (d*cs2);

	// Gradients and phasefield normals:
	real_t nx, ny, nz, magnPhi;
	vector_t gradPhi = calcGradPhi();
	magnPhi = sqrt(gradPhi.x*gradPhi.x + gradPhi.y*gradPhi.y + gradPhi.z*gradPhi.z);

	#ifdef OPTIONS_geometric
		gradPhiVal_x = gradPhi.x;
		gradPhiVal_y = gradPhi.y;
		gradPhiVal_z = gradPhi.z;
	#endif
	if (magnPhi < minGradient){
		nx=0.0; ny=0.0; nz=0.0;
	} else {
		nx = gradPhi.x/magnPhi;
		ny = gradPhi.y/magnPhi;
		nz = gradPhi.z/magnPhi;
	}

	U = U(0,0,0);
	V = V(0,0,0);
	W = W(0,0,0);

	real_t mag = U*U + V*V + W*W;
	real_t Gamma[27];
	// ##### heq
	real_t F_phi[hPops];
	real_t tmp1 = (1.0 - 4.0*(PhaseF - C0)*(PhaseF - C0))/IntWidth;
	for (i=0; i< 27; i++){
		Gamma[i] = calcGamma(i, U, V, W, mag);
		if (i < hPops) F_phi[i] = calcF_phi(i, tmp1, nx, ny, nz);
	}

	h0 = Gamma[0]*PhaseF;
h1 = Gamma[1]*PhaseF;
h2 = Gamma[2]*PhaseF;
h3 = Gamma[3]*PhaseF;
h4 = Gamma[4]*PhaseF;
h5 = Gamma[5]*PhaseF;
h6 = Gamma[6]*PhaseF;
h7 = Gamma[7]*PhaseF;
h8 = Gamma[8]*PhaseF;
h9 = Gamma[9]*PhaseF;
h10 = Gamma[10]*PhaseF;
h11 = Gamma[11]*PhaseF;
h12 = Gamma[12]*PhaseF;
h13 = Gamma[13]*PhaseF;
h14 = Gamma[14]*PhaseF;
h15 = Gamma[15]*PhaseF;
h16 = Gamma[16]*PhaseF;
h17 = Gamma[17]*PhaseF;
h18 = Gamma[18]*PhaseF;
h19 = Gamma[19]*PhaseF;
h20 = Gamma[20]*PhaseF;
h21 = Gamma[21]*PhaseF;
h22 = Gamma[22]*PhaseF;
h23 = Gamma[23]*PhaseF;
h24 = Gamma[24]*PhaseF;
h25 = Gamma[25]*PhaseF;
h26 = Gamma[26]*PhaseF;


	// ##### geq
	g0 = Gamma[0] + ( -1 + pnorm )*wg[0];
g1 = Gamma[1] + ( -1 + pnorm )*wg[1];
g2 = Gamma[2] + ( -1 + pnorm )*wg[2];
g3 = Gamma[3] + ( -1 + pnorm )*wg[3];
g4 = Gamma[4] + ( -1 + pnorm )*wg[4];
g5 = Gamma[5] + ( -1 + pnorm )*wg[5];
g6 = Gamma[6] + ( -1 + pnorm )*wg[6];
g7 = Gamma[7] + ( -1 + pnorm )*wg[7];
g8 = Gamma[8] + ( -1 + pnorm )*wg[8];
g9 = Gamma[9] + ( -1 + pnorm )*wg[9];
g10 = Gamma[10] + ( -1 + pnorm )*wg[10];
g11 = Gamma[11] + ( -1 + pnorm )*wg[11];
g12 = Gamma[12] + ( -1 + pnorm )*wg[12];
g13 = Gamma[13] + ( -1 + pnorm )*wg[13];
g14 = Gamma[14] + ( -1 + pnorm )*wg[14];
g15 = Gamma[15] + ( -1 + pnorm )*wg[15];
g16 = Gamma[16] + ( -1 + pnorm )*wg[16];
g17 = Gamma[17] + ( -1 + pnorm )*wg[17];
g18 = Gamma[18] + ( -1 + pnorm )*wg[18];
g19 = Gamma[19] + ( -1 + pnorm )*wg[19];
g20 = Gamma[20] + ( -1 + pnorm )*wg[20];
g21 = Gamma[21] + ( -1 + pnorm )*wg[21];
g22 = Gamma[22] + ( -1 + pnorm )*wg[22];
g23 = Gamma[23] + ( -1 + pnorm )*wg[23];
g24 = Gamma[24] + ( -1 + pnorm )*wg[24];
g25 = Gamma[25] + ( -1 + pnorm )*wg[25];
g26 = Gamma[26] + ( -1 + pnorm )*wg[26];

        pnorm  = g26 + g25 + g24 + g23 + g22 + g21 + g20 + g19 + g18 + g17 + g16 + g15 + g14 + g13 + g12 + g11 + g10 + g9 + g8 + g7 + g6 + g5 + g4 + g3 + g2 + g1 + g0;
		PhaseF = h26 + h25 + h24 + h23 + h22 + h21 + h20 + h19 + h18 + h17 + h16 + h15 + h14 + h13 + h12 + h11 + h10 + h9 + h8 + h7 + h6 + h5 + h4 + h3 + h2 + h1 + h0;
	#ifdef OPTIONS_thermo
		Temp   = Temp(0,0,0);
		Cond   = interp(PhaseF, k_h, k_l);
	#endif
	#ifdef OPTIONS_OutFlow
			if ((NodeType & NODE_BOUNDARY) == NODE_EConvect){

			}
	#endif
}

CudaDeviceFunction void UpdateGlobalMarkers()
{
	if (IsSpecialBoundaryPoint) {
		AddToNumSpecialPoints(1);
	}

	if ( IamWall || IamSolid ) {
		real_t a, h, pf_f;

		h = 0.5 * sqrt(nw_x*nw_x + nw_y*nw_y + nw_z*nw_z);

        real_t am_i_surrounded = h < 0.001;

        if (! am_i_surrounded) {
          AddToNumWallBoundaryPoints(1);
        }

        AddToNumBoundaryPoints(1);
    }

    if (IamCOLLISION){
      AddToNumFluidCells(1);
    }
}

/*	ITERATION:	*/
CudaDeviceFunction void Run()
{
	IsBoundary = IsBoundary(0,0,0); // propagate it into the next iteration
	UpdateGlobalMarkers();
	stage16_zero_replay_diagnostics();

    if ((NodeType & NODE_ADDITIONALS) == NODE_Smoothing) {
		// If desired, incorporate a smoothing stage, in this we simply let diffusion occur
		Init_distributions();
    } else {
        updateBoundary();
		#ifdef OPTIONS_BGK
			if (NodeType & NODE_BGK) {
				CollisionBGK();
		}
		#else
			if (NodeType & NODE_MRT)
			{
				CollisionMRT();
			}
		#endif
	}
        pnorm  = g26 + g25 + g24 + g23 + g22 + g21 + g20 + g19 + g18 + g17 + g16 + g15 + g14 + g13 + g12 + g11 + g10 + g9 + g8 + g7 + g6 + g5 + g4 + g3 + g2 + g1 + g0;
}

CudaDeviceFunction real_t calcTau(real_t pf)
{
	real_t tau;
	if ( pf < PhaseField_l){
		tau = tau_l + 0.5;
	} else if (pf > PhaseField_h) {
		tau = tau_h + 0.5;
	} else {
	    if (tauUpdate == 1) { // Linear update:
            tau = 0.5 + tau_l + (pf-PhaseField_l)*(tau_h - tau_l)/(PhaseField_h - PhaseField_l);
        } else if (tauUpdate == 2){ // Inverse update:
		    tau = (pf - PhaseField_l)/(PhaseField_h - PhaseField_l) * (1.0/tau_h - 1.0/tau_l) + 1.0/tau_l;
		    tau = 1.0/tau + 0.5;
			// NOTE: For some reason Viscosity_h and Viscosity_l are set to zero. Deduce it from tau here
			// instead for tauUpdate 3 and tauUpdate 4
        } else if (tauUpdate == 3){	// Viscosity update:
		    real_t DynVisc = Density_l*tau_l / 3.0 + pf * (tau_h*Density_h/3.0 - Density_l*tau_l/3.0);
            real_t rho = getRho();
		    tau = 3.0 * DynVisc / rho + 0.5;
        } else if (tauUpdate == 4) { // update from Zu-He 2013
			real_t mu_l = Density_l * tau_l / 3.0;
			real_t mu_h = Density_h * tau_h / 3.0;
		    real_t DynVisc = mu_l * mu_h * (PhaseField_h - PhaseField_l) / ((pf - PhaseField_l)*mu_l  + (PhaseField_h - pf)*mu_h);
            real_t rho = getRho();
			tau = 3.0 * DynVisc / rho + 0.5;
		} else { // default to linear...
            tau = 0.5 + tau_l + (pf-PhaseField_l)*(tau_h - tau_l)/(PhaseField_h - PhaseField_l);
        }
	}
	return tau;
}

CudaDeviceFunction void calc_Fp(real_t *fx, real_t *fy, real_t *fz, real_t pressure, vector_t gPhi){
	*fx = (-1.0/3.0) * pressure * (Density_h-Density_l) * gPhi.x;
	*fy = (-1.0/3.0) * pressure * (Density_h-Density_l) * gPhi.y;
	*fz = (-1.0/3.0) * pressure * (Density_h-Density_l) * gPhi.z;
}

CudaDeviceFunction void calc_Fb(real_t *fx, real_t *fy, real_t *fz, real_t rho){
    *fx = (Density_h-rho)*BuoyancyX + rho*GravitationX;
	*fy = (Density_h-rho)*BuoyancyY + rho*GravitationY;
	*fz = (Density_h-rho)*BuoyancyZ + rho*GravitationZ;
}

CudaDeviceFunction void calc_Fs(real_t *fx, real_t *fy, real_t *fz, real_t mu, vector_t gPhi){
	#ifdef OPTIONS_thermo
		Temp = Temp(0,0,0);
		SurfaceTension = SurfaceTension(0,0,0);
		Cond = Cond(0,0,0);
		real_t tmpSig, delta_s, dotTMP, magnPhi, magnPhi2;
		magnPhi = sqrt(gPhi.x*gPhi.x + gPhi.y*gPhi.y + gPhi.z*gPhi.z);
		magnPhi2 = magnPhi*magnPhi;
		vector_t gradT;
		gradT.y = 16.00 * (Temp(0,1,0) - Temp(0,-1,0)) + Temp(1,1,1) + Temp(-1,1,1) - Temp(1,-1,1) - Temp(-1,-1,1) + Temp(1,1,-1)+ Temp(-1,1,-1)- Temp(1,-1,-1)- Temp(-1,-1,-1) +  4.00 * (Temp(1,1,0) + Temp(-1,1,0) - Temp(1,-1,0) - Temp(-1,-1,0) +  Temp(0,1,1) - Temp(0,-1,1) + Temp(0,1,-1) - Temp(0,-1,-1));
gradT.x = 16.00 * (Temp(1,0,0) - Temp(-1,0,0)) + Temp(1,1,1) - Temp(-1,1,1) + Temp(1,-1,1) - Temp(-1,-1,1) + Temp(1,1,-1)- Temp(-1,1,-1) + Temp(1,-1,-1) - Temp(-1,-1,-1) +  4.00 * (Temp(1,1,0) - Temp(-1,1,0) + Temp(1,-1,0) - Temp(-1,-1,0) + Temp(1,0,1) - Temp(-1,0,1) + Temp(1,0,-1) - Temp(-1,0,-1));
gradT.z = 16.00 * (Temp(0,0,1) - Temp(0,0,-1)) + Temp(1,1,1) + Temp(-1,1,1) + Temp(1,-1,1) + Temp(-1,-1,1) - Temp(1,1,-1)- Temp(-1,1,-1)- Temp(1,-1,-1)- Temp(-1,-1,-1) +  4.00 * (Temp(1,0,1) + Temp(-1,0,1) - Temp(1,0,-1) - Temp(-1,0,-1) +  Temp(0,1,1) + Temp(0,-1,1) - Temp(0,1,-1) - Temp(0,-1,-1));
gradT.x /= 72.0;
gradT.y /= 72.0;
gradT.z /= 72.0;

		dotTMP = dotProduct(gradT,gPhi);
		if (surfPower < 2) {
			delta_s = 1.5*IntWidth*sigma_T;
			*fx = mu * gPhi.x + delta_s*( magnPhi2*gradT.x - dotTMP*gPhi.x );
			*fy = mu * gPhi.y + delta_s*( magnPhi2*gradT.y - dotTMP*gPhi.y );
			*fz = mu * gPhi.z + delta_s*( magnPhi2*gradT.z - dotTMP*gPhi.z );
		} else {
			vector_t gradSig;
			gradSig.y = 16.00 * (SurfaceTension(0,1,0) - SurfaceTension(0,-1,0)) + SurfaceTension(1,1,1) + SurfaceTension(-1,1,1) - SurfaceTension(1,-1,1) - SurfaceTension(-1,-1,1) + SurfaceTension(1,1,-1)+ SurfaceTension(-1,1,-1)- SurfaceTension(1,-1,-1)- SurfaceTension(-1,-1,-1) +  4.00 * (SurfaceTension(1,1,0) + SurfaceTension(-1,1,0) - SurfaceTension(1,-1,0) - SurfaceTension(-1,-1,0) +  SurfaceTension(0,1,1) - SurfaceTension(0,-1,1) + SurfaceTension(0,1,-1) - SurfaceTension(0,-1,-1));
gradSig.x = 16.00 * (SurfaceTension(1,0,0) - SurfaceTension(-1,0,0)) + SurfaceTension(1,1,1) - SurfaceTension(-1,1,1) + SurfaceTension(1,-1,1) - SurfaceTension(-1,-1,1) + SurfaceTension(1,1,-1)- SurfaceTension(-1,1,-1) + SurfaceTension(1,-1,-1) - SurfaceTension(-1,-1,-1) +  4.00 * (SurfaceTension(1,1,0) - SurfaceTension(-1,1,0) + SurfaceTension(1,-1,0) - SurfaceTension(-1,-1,0) + SurfaceTension(1,0,1) - SurfaceTension(-1,0,1) + SurfaceTension(1,0,-1) - SurfaceTension(-1,0,-1));
gradSig.z = 16.00 * (SurfaceTension(0,0,1) - SurfaceTension(0,0,-1)) + SurfaceTension(1,1,1) + SurfaceTension(-1,1,1) + SurfaceTension(1,-1,1) + SurfaceTension(-1,-1,1) - SurfaceTension(1,1,-1)- SurfaceTension(-1,1,-1)- SurfaceTension(1,-1,-1)- SurfaceTension(-1,-1,-1) +  4.00 * (SurfaceTension(1,0,1) + SurfaceTension(-1,0,1) - SurfaceTension(1,0,-1) - SurfaceTension(-1,0,-1) +  SurfaceTension(0,1,1) + SurfaceTension(0,-1,1) - SurfaceTension(0,1,-1) - SurfaceTension(0,-1,-1));
gradSig.x /= 72.0;
gradSig.y /= 72.0;
gradSig.z /= 72.0;

			delta_s = 1.5*IntWidth;
			*fx = mu * gPhi.x + delta_s*gradSig.x*( magnPhi2*gradT.x - dotTMP*gPhi.x );
			*fy = mu * gPhi.y + delta_s*gradSig.y*( magnPhi2*gradT.y - dotTMP*gPhi.y );
			*fz = mu * gPhi.z + delta_s*gradSig.z*( magnPhi2*gradT.z - dotTMP*gPhi.z );
		}
	#else
		*fx = mu * gPhi.x;
		*fy = mu * gPhi.y;
		*fz = mu * gPhi.z;
	#endif
}

#ifndef OPTIONS_BGK
CudaDeviceFunction void CollisionMRT()
{
	PhaseF = PhaseF(0,0,0);
	int i, j;
	real_t C  = PhaseF;
	if (stage16_replay_diagnostics_active()) {
		ReplayPhaseConsumed = C;
	}
	ForceIterResidual = 0.0;
	ForceIterCount = 0.0;
	MassCorrectionApplied = 0.0;
	PhaseStencilGhostUseCount = 0.0;
	PhaseStencilFallbackCount = 0.0;
	PhaseStencilMidpointFallbackCount = 0.0;
    real_t mu = calcMu( C );
	real_t tau, DynVisc, rho, p;			// Macroscopic Properties
	vector_t n, gradPhi;					// Phase field gradients
	real_t magnPhi;							// Normals
	real_t F_pressure[3], F_body[3], F_mu[3], F_surf[3], F_total[3]; // Forces
	real_t tmp1, stress[6]={0.0,0.0,0.0,0.0,0.0,0.0};     // Stress tensor calculation
	real_t F_phi[hPops], heq[hPops];				// Phase field collision terms
	real_t F_i[27];							// Momentum distribution forcing term
	real_t m[27];							//MRT Details
	real_t F_prev[3] = {0.0, 0.0, 0.0};

	// Find Macroscopic Details
	rho = Density_l + (C - PhaseField_l)*(Density_h - Density_l)/(PhaseField_h - PhaseField_l);

	updateMyGlobals( C );

	real_t m0[27];
	m0[0] = g26 + g25 + g24 + g23 + g22 + g21 + g20 + g19 + g18 + g17 + g16 + g15 + g14 + g13 + g12 + g11 + g10 + g9 + g8 + g7 + g6 + g5 + g4 + g3 + g2 + g1 + g0;
m0[1] = -g22 + g21 - g20 + g19 - g18 + g17 - g16 + g15 - g14 + g13 - g12 + g11 - g10 + g9 - g8 + g7 - g2 + g1;
m0[2] = -g26 + g25 - g24 + g23 - g18 - g17 + g16 + g15 - g14 - g13 + g12 + g11 - g10 - g9 + g8 + g7 - g4 + g3;
m0[3] = -g26 - g25 + g24 + g23 - g22 - g21 + g20 + g19 - g14 - g13 - g12 - g11 + g10 + g9 + g8 + g7 - g6 + g5;
m0[4] = g18 - g17 - g16 + g15 + g14 - g13 - g12 + g11 + g10 - g9 - g8 + g7;
m0[5] = g26 - g25 - g24 + g23 + g14 + g13 - g12 - g11 - g10 - g9 + g8 + g7;
m0[6] = g22 - g21 - g20 + g19 + g14 - g13 + g12 - g11 - g10 + g9 - g8 + g7;
m0[7] = g22 + g21 + g20 + g19 + g18 + g17 + g16 + g15 - g6 - g5 - g4 - g3 + ( -g26 - g25 - g24 - g23 + g2 + g1 )*2.;
m0[8] = -g22 - g21 - g20 - g19 + g18 + g17 + g16 + g15 - g6 - g5 + g4 + g3;
m0[9] = g26 + g25 + g24 + g23 + g22 + g21 + g20 + g19 + g18 + g17 + g16 + g15 - g0 + ( g14 + g13 + g12 + g11 + g10 + g9 + g8 + g7 )*2.;
m0[10] = -g22 + g21 - g20 + g19 - g18 + g17 - g16 + g15 + ( g2 - g1 + ( -g14 + g13 - g12 + g11 - g10 + g9 - g8 + g7 )*2. )*2.;
m0[11] = -g26 + g25 - g24 + g23 - g18 - g17 + g16 + g15 + ( g4 - g3 + ( -g14 - g13 + g12 + g11 - g10 - g9 + g8 + g7 )*2. )*2.;
m0[12] = -g26 - g25 + g24 + g23 - g22 - g21 + g20 + g19 + ( g6 - g5 + ( -g14 - g13 - g12 - g11 + g10 + g9 + g8 + g7 )*2. )*2.;
m0[13] = g22 - g21 + g20 - g19 - g18 + g17 - g16 + g15;
m0[14] = -g26 + g25 - g24 + g23 + g18 + g17 - g16 - g15;
m0[15] = g26 + g25 - g24 - g23 - g22 - g21 + g20 + g19;
m0[16] = -g14 + g13 + g12 - g11 + g10 - g9 - g8 + g7;
m0[17] = -g6 - g5 - g4 - g3 - g2 - g1 + g0 + ( g14 + g13 + g12 + g11 + g10 + g9 + g8 + g7 )*4.;
m0[18] = g6 + g5 + g4 + g3 + ( g22 + g21 + g20 + g19 + g18 + g17 + g16 + g15 - g2 - g1 + ( -g26 - g25 - g24 - g23 )*2. )*2.;
m0[19] = g6 + g5 - g4 - g3 + ( -g22 - g21 - g20 - g19 + g18 + g17 + g16 + g15 )*2.;
m0[20] = -g18 + g17 + g16 - g15 + ( g14 - g13 - g12 + g11 + g10 - g9 - g8 + g7 )*2.;
m0[21] = -g26 + g25 + g24 - g23 + ( g14 + g13 - g12 - g11 - g10 - g9 + g8 + g7 )*2.;
m0[22] = -g22 + g21 + g20 - g19 + ( g14 - g13 + g12 - g11 - g10 + g9 - g8 + g7 )*2.;
m0[23] = -g2 + g1 + ( g22 - g21 + g20 - g19 + g18 - g17 + g16 - g15 + ( -g14 + g13 - g12 + g11 - g10 + g9 - g8 + g7 )*2. )*2.;
m0[24] = -g4 + g3 + ( g26 - g25 + g24 - g23 + g18 + g17 - g16 - g15 + ( -g14 - g13 + g12 + g11 - g10 - g9 + g8 + g7 )*2. )*2.;
m0[25] = -g6 + g5 + ( g26 + g25 - g24 - g23 + g22 + g21 - g20 - g19 + ( -g14 - g13 - g12 - g11 + g10 + g9 + g8 + g7 )*2. )*2.;
m0[26] = -g0 + ( g6 + g5 + g4 + g3 + g2 + g1 + ( -g26 - g25 - g24 - g23 - g22 - g21 - g20 - g19 - g18 - g17 - g16 - g15 + ( g14 + g13 + g12 + g11 + g10 + g9 + g8 + g7 )*2. )*2. )*2.;

	p = m0[0];

	tau = calcTau( C );
	if (stage16_replay_diagnostics_active()) {
		ReplayRho = rho;
		ReplayTau = tau;
		ReplayPressureMoment = p;
		ReplayUPreForceX = m0[1];
		ReplayUPreForceY = m0[2];
		ReplayUPreForceZ = m0[3];
	}

	// GRADIENTS AND NORMALS
	gradPhi = calcGradPhi();
	if (stage16_replay_diagnostics_active()) {
		ReplayGradPhiX = gradPhi.x;
		ReplayGradPhiY = gradPhi.y;
		ReplayGradPhiZ = gradPhi.z;
	}
	magnPhi = sqrt(gradPhi.x*gradPhi.x + gradPhi.y*gradPhi.y + gradPhi.z*gradPhi.z);

	// Stage 15B: DynamicCL shadow. Compute the candidate residual contact-line
	// force and write diagnostics. In 15B the candidate is NEVER added to
	// F_total (DynamicCLMode<=1). The F_total += F_CL line is reserved for 15C
	// and guarded by DynamicCLMode>=2 below, inside the force-iteration block.
	real_t fcl_x = 0.0, fcl_y = 0.0, fcl_z = 0.0;
	{
		// Stage 15B/15C: compute the candidate residual contact-line force and
		// write diagnostics on every call (Mode>=1). fcl_* is hoisted to
		// function scope so the 15C write hook below can add it to F_total.
		calcDynamicCLShadow(gradPhi, C, &fcl_x, &fcl_y, &fcl_z);
	}

	if (magnPhi < minGradient){
		n.x=0.0; n.y=0.0; n.z=0.0;
	} else {
		n.x = gradPhi.x/magnPhi;
		n.y = gradPhi.y/magnPhi;
		n.z = gradPhi.z/magnPhi;
	}
	if (stage16_replay_diagnostics_active()) {
		ReplayNormalX = n.x;
		ReplayNormalY = n.y;
		ReplayNormalZ = n.z;
	}
	//magnPhi = sqrt(gradPhi.x*gradPhi.x + gradPhi.y*gradPhi.y + gradPhi.z*gradPhi.z + 1e-2);
	//n.x = gradPhi.x/magnPhi;
	//n.y = gradPhi.y/magnPhi;
	//n.z = gradPhi.z/magnPhi;

	// CALCULATE FORCES:
    calc_Fp(&F_pressure[0], &F_pressure[1], &F_pressure[2], p, gradPhi);
	calc_Fb(&F_body[0], &F_body[1], &F_body[2], rho);
    calc_Fs(&F_surf[0], &F_surf[1], &F_surf[2], mu, gradPhi);
	if (stage16_replay_diagnostics_active()) {
		ReplayFpressureX = F_pressure[0];
		ReplayFpressureY = F_pressure[1];
		ReplayFpressureZ = F_pressure[2];
		ReplayFbodyX = F_body[0];
		ReplayFbodyY = F_body[1];
		ReplayFbodyZ = F_body[2];
		ReplayFsurfX = F_surf[0];
		ReplayFsurfY = F_surf[1];
		ReplayFsurfZ = F_surf[2];
	}
	// Viscous force fixed-point iteration. ForceFixedTol<=0 preserves the
	// legacy fixed-count loop controlled by force_fixed_iterator.
	int force_iter_limit = force_fixed_iterator;
	if (ForceFixedTol > 0.0) {
		force_iter_limit = ForceFixedMaxIter;
	}
	if (force_iter_limit < 1) {
		force_iter_limit = 1;
	}
	j = 0;
	bool force_iter_converged = false;
	do {	// do while loop is guaranteeing the loop will execute at least once
		j++;
	m[0] = -p + m0[0];
m[1] = -U + m0[1];
m[2] = -V + m0[2];
m[3] = -W + m0[3];
m[4] = ( -V*U + m0[4] )/tau;
m[5] = ( -W*V + m0[5] )/tau;
m[6] = ( -W*U + m0[6] )/tau;
m[7] = ( W*W + V*V + m0[7] - U*U*2. )/tau;
m[8] = ( W*W - V*V + m0[8] )/tau;
m[9] = -W*W - V*V - U*U + m0[9];
m[10] = m0[10];
m[11] = m0[11];
m[12] = m0[12];
m[13] = m0[13];
m[14] = m0[14];
m[15] = m0[15];
m[16] = m0[16];
m[17] = m0[17];
m[18] = m0[18];
m[19] = m0[19];
m[20] = m0[20];
m[21] = m0[21];
m[22] = m0[22];
m[23] = m0[23];
m[24] = m0[24];
m[25] = m0[25];
m[26] = m0[26];
stress[0] = ( m[9] + m[7] + m[0] )/3.;
stress[1] = m[4];
stress[2] = m[6];
stress[3] = ( -m[7] + m[8]*3. + ( m[9] + m[0] )*2. )/6.;
stress[4] = m[5];
stress[5] = ( -m[7] - m[8]*3. + ( m[9] + m[0] )*2. )/6.;

		F_mu[0] = (0.5-tau) * (Density_h-Density_l) * (stress[0]*gradPhi.x + stress[1]*gradPhi.y + stress[2]*gradPhi.z);
		F_mu[1] = (0.5-tau) * (Density_h-Density_l) * (stress[1]*gradPhi.x + stress[3]*gradPhi.y + stress[4]*gradPhi.z);
		F_mu[2] = (0.5-tau) * (Density_h-Density_l) * (stress[2]*gradPhi.x + stress[4]*gradPhi.y + stress[5]*gradPhi.z);
		F_total[0] = F_surf[0] + F_pressure[0] + F_body[0] + F_mu[0];
		F_total[1] = F_surf[1] + F_pressure[1] + F_body[1] + F_mu[1];
		F_total[2] = F_surf[2] + F_pressure[2] + F_body[2] + F_mu[2];
		// Stage 15C write hook: add the residual contact-line force to F_total.
		// Shadow-only at Mode<=1 (no-op). calcDynamicCLShadow already applied
		// ForceSign*Coeff*(sigma/IntWidth)*R_theta*I_cl and the ForceCap; do NOT
		// rescale here. Mode>1.5 is refused by the runner until 15C is cleared.
		if (DynamicCLMode > 1.5) {
			F_total[0] += fcl_x;
			F_total[1] += fcl_y;
			F_total[2] += fcl_z;
		}
		if (stage16_replay_diagnostics_active()) {
			ReplayFmuX = F_mu[0];
			ReplayFmuY = F_mu[1];
			ReplayFmuZ = F_mu[2];
			ReplayFtotalX = F_total[0];
			ReplayFtotalY = F_total[1];
			ReplayFtotalZ = F_total[2];
			ReplayStressXX = stress[0];
			ReplayStressXY = stress[1];
			ReplayStressXZ = stress[2];
			ReplayStressYY = stress[3];
			ReplayStressYZ = stress[4];
			ReplayStressZZ = stress[5];
			if (j == 1) {
				ReplayFmuIter1X = F_mu[0];
				ReplayFmuIter1Y = F_mu[1];
				ReplayFmuIter1Z = F_mu[2];
				ReplayFtotalIter1X = F_total[0];
				ReplayFtotalIter1Y = F_total[1];
				ReplayFtotalIter1Z = F_total[2];
			}
		}
		if (j > 1) {
			real_t dFx = F_total[0] - F_prev[0];
			real_t dFy = F_total[1] - F_prev[1];
			real_t dFz = F_total[2] - F_prev[2];
			real_t delta_norm = sqrt(dFx*dFx + dFy*dFy + dFz*dFz);
			real_t prev_norm = sqrt(F_prev[0]*F_prev[0] + F_prev[1]*F_prev[1] + F_prev[2]*F_prev[2]);
			ForceIterResidual = delta_norm / (prev_norm + 1.0e-30);
		}
		F_prev[0] = F_total[0];
		F_prev[1] = F_total[1];
		F_prev[2] = F_total[2];
		ForceIterCount = j;

	U = m0[1] + F_total[0]/rho/2.;
V = m0[2] + F_total[1]/rho/2.;
W = m0[3] + F_total[2]/rho/2.;

		if (stage16_replay_diagnostics_active()) {
			real_t inv_rho_diag = (rho != 0.0) ? 1.0/rho : 0.0;
			ReplayUPostForceX = U;
			ReplayUPostForceY = V;
			ReplayUPostForceZ = W;
			ReplayForceOverRhoX = F_total[0] * inv_rho_diag;
			ReplayForceOverRhoY = F_total[1] * inv_rho_diag;
			ReplayForceOverRhoZ = F_total[2] * inv_rho_diag;
			if (j == 1) {
				ReplayUPostIter1X = U;
				ReplayUPostIter1Y = V;
				ReplayUPostIter1Z = W;
			}
		}
		if (ForceFixedTol > 0.0 && j > 1 && ForceIterResidual < ForceFixedTol) {
			force_iter_converged = true;
		}
	} while (j < force_iter_limit && !force_iter_converged);
	// PHASE FIELD POPULATION UPDATE:
	tmp1 = (1.0 - 4.0*(C - 0.5)*(C - 0.5))/IntWidth;
	if (stage16_replay_diagnostics_active()) {
		ReplayTmp1 = tmp1;
	}
	heq[0] = ( 2. + ( -W*W - V*V - U*U )*3. )*C*4./27.;
heq[1] = ( 2. + ( -W*W - V*V + ( 1 + U )*U*2. )*3. )*C/27.;
heq[2] = ( 2. + ( -W*W - V*V + ( -1 + U )*U*2. )*3. )*C/27.;
heq[3] = ( 2. + ( -W*W - U*U + ( 1 + V )*V*2. )*3. )*C/27.;
heq[4] = ( 2. + ( -W*W - U*U + ( -1 + V )*V*2. )*3. )*C/27.;
heq[5] = ( 2. + ( -V*V - U*U + ( 1 + W )*W*2. )*3. )*C/27.;
heq[6] = ( 2. + ( -V*V - U*U + ( -1 + W )*W*2. )*3. )*C/27.;
heq[7] = ( 1 + ( ( 1 + W )*W + ( 1 + V + W*3. )*V + ( 1 + U + ( W + V )*3. )*U )*3. )*C*0.00462962962962964;
heq[8] = ( 1 + ( ( 1 + W )*W + ( 1 + V + W*3. )*V + ( -1 + U + ( -W - V )*3. )*U )*3. )*C*0.00462962962962964;
heq[9] = ( 1 + ( ( 1 + W )*W + ( -1 + V - W*3. )*V + ( 1 + U + ( W - V )*3. )*U )*3. )*C*0.00462962962962964;
heq[10] = ( 1 + ( ( 1 + W )*W + ( -1 + V - W*3. )*V + ( -1 + U + ( -W + V )*3. )*U )*3. )*C*0.00462962962962964;
heq[11] = ( 1 + ( ( -1 + W )*W + ( 1 + V - W*3. )*V + ( 1 + U + ( -W + V )*3. )*U )*3. )*C*0.00462962962962964;
heq[12] = ( 1 + ( ( -1 + W )*W + ( 1 + V - W*3. )*V + ( -1 + U + ( W - V )*3. )*U )*3. )*C*0.00462962962962964;
heq[13] = ( 1 + ( ( -1 + W )*W + ( -1 + V + W*3. )*V + ( 1 + U + ( -W - V )*3. )*U )*3. )*C*0.00462962962962964;
heq[14] = ( 1 + ( ( -1 + W )*W + ( -1 + V + W*3. )*V + ( -1 + U + ( W + V )*3. )*U )*3. )*C*0.00462962962962964;
heq[15] = ( 0.0185185185185185 + ( -W*W + ( ( 1 + V )*V + ( 1 + U + V*3. )*U )*2. )/36. )*C;
heq[16] = ( 0.0185185185185185 + ( -W*W + ( ( 1 + V )*V + ( -1 + U - V*3. )*U )*2. )/36. )*C;
heq[17] = ( 0.0185185185185185 + ( -W*W + ( ( -1 + V )*V + ( 1 + U - V*3. )*U )*2. )/36. )*C;
heq[18] = ( 0.0185185185185185 + ( -W*W + ( ( -1 + V )*V + ( -1 + U + V*3. )*U )*2. )/36. )*C;
heq[19] = ( 0.0185185185185185 + ( -V*V + ( ( 1 + W )*W + ( 1 + U + W*3. )*U )*2. )/36. )*C;
heq[20] = ( 0.0185185185185185 + ( -V*V + ( ( 1 + W )*W + ( -1 + U - W*3. )*U )*2. )/36. )*C;
heq[21] = ( 0.0185185185185185 + ( -V*V + ( ( -1 + W )*W + ( 1 + U - W*3. )*U )*2. )/36. )*C;
heq[22] = ( 0.0185185185185185 + ( -V*V + ( ( -1 + W )*W + ( -1 + U + W*3. )*U )*2. )/36. )*C;
heq[23] = ( 0.0185185185185185 + ( -U*U + ( ( 1 + W )*W + ( 1 + V + W*3. )*V )*2. )/36. )*C;
heq[24] = ( 0.0185185185185185 + ( -U*U + ( ( 1 + W )*W + ( -1 + V - W*3. )*V )*2. )/36. )*C;
heq[25] = ( 0.0185185185185185 + ( -U*U + ( ( -1 + W )*W + ( 1 + V - W*3. )*V )*2. )/36. )*C;
heq[26] = ( 0.0185185185185185 + ( -U*U + ( ( -1 + W )*W + ( -1 + V + W*3. )*V )*2. )/36. )*C;
F_phi[0] = 0;
F_phi[1] = n.x*tmp1*2./27.;
F_phi[2] = -n.x*tmp1*2./27.;
F_phi[3] = n.y*tmp1*2./27.;
F_phi[4] = -n.y*tmp1*2./27.;
F_phi[5] = n.z*tmp1*2./27.;
F_phi[6] = -n.z*tmp1*2./27.;
F_phi[7] = ( n.z + n.y + n.x )*tmp1*0.00462962962962964;
F_phi[8] = ( n.z + n.y - n.x )*tmp1*0.00462962962962964;
F_phi[9] = ( n.z - n.y + n.x )*tmp1*0.00462962962962964;
F_phi[10] = ( n.z - n.y - n.x )*tmp1*0.00462962962962964;
F_phi[11] = ( -n.z + n.y + n.x )*tmp1*0.00462962962962964;
F_phi[12] = ( -n.z + n.y - n.x )*tmp1*0.00462962962962964;
F_phi[13] = ( -n.z - n.y + n.x )*tmp1*0.00462962962962964;
F_phi[14] = ( n.z + n.y + n.x )*tmp1*-0.00462962962962964;
F_phi[15] = ( n.y + n.x )*tmp1*0.0185185185185185;
F_phi[16] = ( n.y - n.x )*tmp1*0.0185185185185185;
F_phi[17] = ( -n.y + n.x )*tmp1*0.0185185185185185;
F_phi[18] = ( n.y + n.x )*tmp1*-0.0185185185185185;
F_phi[19] = ( n.z + n.x )*tmp1*0.0185185185185185;
F_phi[20] = ( n.z - n.x )*tmp1*0.0185185185185185;
F_phi[21] = ( -n.z + n.x )*tmp1*0.0185185185185185;
F_phi[22] = ( n.z + n.x )*tmp1*-0.0185185185185185;
F_phi[23] = ( n.z + n.y )*tmp1*0.0185185185185185;
F_phi[24] = ( n.z - n.y )*tmp1*0.0185185185185185;
F_phi[25] = ( -n.z + n.y )*tmp1*0.0185185185185185;
F_phi[26] = ( n.z + n.y )*tmp1*-0.0185185185185185;
h0 = F_phi[0] + h0 + ( heq[0] - h0 - F_phi[0]/2. )*omega_phi;
h1 = F_phi[1] + h1 + ( heq[1] - h1 - F_phi[1]/2. )*omega_phi;
h2 = F_phi[2] + h2 + ( heq[2] - h2 - F_phi[2]/2. )*omega_phi;
h3 = F_phi[3] + h3 + ( heq[3] - h3 - F_phi[3]/2. )*omega_phi;
h4 = F_phi[4] + h4 + ( heq[4] - h4 - F_phi[4]/2. )*omega_phi;
h5 = F_phi[5] + h5 + ( heq[5] - h5 - F_phi[5]/2. )*omega_phi;
h6 = F_phi[6] + h6 + ( heq[6] - h6 - F_phi[6]/2. )*omega_phi;
h7 = F_phi[7] + h7 + ( heq[7] - h7 - F_phi[7]/2. )*omega_phi;
h8 = F_phi[8] + h8 + ( heq[8] - h8 - F_phi[8]/2. )*omega_phi;
h9 = F_phi[9] + h9 + ( heq[9] - h9 - F_phi[9]/2. )*omega_phi;
h10 = F_phi[10] + h10 + ( heq[10] - h10 - F_phi[10]/2. )*omega_phi;
h11 = F_phi[11] + h11 + ( heq[11] - h11 - F_phi[11]/2. )*omega_phi;
h12 = F_phi[12] + h12 + ( heq[12] - h12 - F_phi[12]/2. )*omega_phi;
h13 = F_phi[13] + h13 + ( heq[13] - h13 - F_phi[13]/2. )*omega_phi;
h14 = F_phi[14] + h14 + ( heq[14] - h14 - F_phi[14]/2. )*omega_phi;
h15 = F_phi[15] + h15 + ( heq[15] - h15 - F_phi[15]/2. )*omega_phi;
h16 = F_phi[16] + h16 + ( heq[16] - h16 - F_phi[16]/2. )*omega_phi;
h17 = F_phi[17] + h17 + ( heq[17] - h17 - F_phi[17]/2. )*omega_phi;
h18 = F_phi[18] + h18 + ( heq[18] - h18 - F_phi[18]/2. )*omega_phi;
h19 = F_phi[19] + h19 + ( heq[19] - h19 - F_phi[19]/2. )*omega_phi;
h20 = F_phi[20] + h20 + ( heq[20] - h20 - F_phi[20]/2. )*omega_phi;
h21 = F_phi[21] + h21 + ( heq[21] - h21 - F_phi[21]/2. )*omega_phi;
h22 = F_phi[22] + h22 + ( heq[22] - h22 - F_phi[22]/2. )*omega_phi;
h23 = F_phi[23] + h23 + ( heq[23] - h23 - F_phi[23]/2. )*omega_phi;
h24 = F_phi[24] + h24 + ( heq[24] - h24 - F_phi[24]/2. )*omega_phi;
h25 = F_phi[25] + h25 + ( heq[25] - h25 - F_phi[25]/2. )*omega_phi;
h26 = F_phi[26] + h26 + ( heq[26] - h26 - F_phi[26]/2. )*omega_phi;
m[0] = p;
m[1] = U + F_total[0]/rho/2.;
m[2] = V + F_total[1]/rho/2.;
m[3] = W + F_total[2]/rho/2.;
m[4] = m0[4] + ( V*U - m0[4] )/tau;
m[5] = m0[5] + ( W*V - m0[5] )/tau;
m[6] = m0[6] + ( W*U - m0[6] )/tau;
m[7] = m0[7] + ( -W*W - V*V - m0[7] + U*U*2. )/tau;
m[8] = m0[8] + ( -W*W + V*V - m0[8] )/tau;
m[9] = W*W + V*V + U*U;
m[10] = 0;
m[11] = 0;
m[12] = 0;
m[13] = 0;
m[14] = 0;
m[15] = 0;
m[16] = 0;
m[17] = 0;
m[18] = 0;
m[19] = 0;
m[20] = 0;
m[21] = 0;
m[22] = 0;
m[23] = 0;
m[24] = 0;
m[25] = 0;
m[26] = 0;
g0 = ( -m[26] + ( m[0]*4. + ( m[17] - m[9]*2. )*3. )*2. )/27.;
g1 = ( m[26] + m[0]*4. + ( m[23] - m[18] - m[17] + ( -m[10] + m[7] + m[1]*2. )*2. )*3. )*0.0185185185185185;
g2 = ( m[26] + m[0]*4. + ( -m[23] - m[18] - m[17] + ( m[10] + m[7] - m[1]*2. )*2. )*3. )*0.0185185185185186;
g3 = ( m[26] + m[0]*4. )*0.0185185185185185 + ( m[18] - m[19]*3. + ( m[24] - m[17] - m[7] + m[8]*3. + ( -m[11] + m[2]*2. )*2. )*2. )/36.;
g4 = ( m[26] + m[0]*4. )*0.0185185185185185 + ( m[18] - m[19]*3. + ( -m[24] - m[17] - m[7] + m[8]*3. + ( m[11] - m[2]*2. )*2. )*2. )/36.;
g5 = ( m[26] + m[0]*4. )*0.0185185185185185 + ( m[18] + m[19]*3. + ( m[25] - m[17] - m[7] - m[8]*3. + ( -m[12] + m[3]*2. )*2. )*2. )/36.;
g6 = ( m[26] + m[0]*4. )*0.0185185185185185 + ( m[18] + m[19]*3. + ( -m[25] - m[17] - m[7] - m[8]*3. + ( m[12] - m[3]*2. )*2. )*2. )/36.;
g7 = ( m[26] + m[0] + ( m[25] + m[24] + m[23] + m[17] + m[12] + m[11] + m[10] + m[9] + m[3] + m[2] + m[1] + ( m[22] + m[21] + m[20] + m[6] + m[5] + m[4] + m[16]*3. )*3. )*3. )*0.00462962962962963;
g8 = ( m[26] + m[0] + ( m[25] + m[24] - m[23] + m[17] + m[12] + m[11] - m[10] + m[9] + m[3] + m[2] - m[1] + ( -m[22] + m[21] - m[20] - m[6] + m[5] - m[4] - m[16]*3. )*3. )*3. )*0.00462962962962963;
g9 = ( m[26] + m[0] + ( m[25] - m[24] + m[23] + m[17] + m[12] - m[11] + m[10] + m[9] + m[3] - m[2] + m[1] + ( m[22] - m[21] - m[20] + m[6] - m[5] - m[4] - m[16]*3. )*3. )*3. )*0.00462962962962964;
g10 = ( m[26] + m[0] + ( m[25] - m[24] - m[23] + m[17] + m[12] - m[11] - m[10] + m[9] + m[3] - m[2] - m[1] + ( -m[22] - m[21] + m[20] - m[6] - m[5] + m[4] + m[16]*3. )*3. )*3. )*0.00462962962962963;
g11 = ( m[26] + m[0] + ( -m[25] + m[24] + m[23] + m[17] - m[12] + m[11] + m[10] + m[9] - m[3] + m[2] + m[1] + ( -m[22] - m[21] + m[20] - m[6] - m[5] + m[4] - m[16]*3. )*3. )*3. )*0.00462962962962963;
g12 = ( m[26] + m[0] + ( -m[25] + m[24] - m[23] + m[17] - m[12] + m[11] - m[10] + m[9] - m[3] + m[2] - m[1] + ( m[22] - m[21] - m[20] + m[6] - m[5] - m[4] + m[16]*3. )*3. )*3. )*0.00462962962962963;
g13 = ( m[26] + m[0] + ( -m[25] - m[24] + m[23] + m[17] - m[12] - m[11] + m[10] + m[9] - m[3] - m[2] + m[1] + ( -m[22] + m[21] - m[20] - m[6] + m[5] - m[4] + m[16]*3. )*3. )*3. )*0.00462962962962963;
g14 = ( m[26] + m[0] + ( -m[25] - m[24] - m[23] + m[17] - m[12] - m[11] - m[10] + m[9] - m[3] - m[2] - m[1] + ( m[22] + m[21] + m[20] + m[6] + m[5] + m[4] - m[16]*3. )*3. )*3. )*0.00462962962962963;
g15 = ( m[26] - m[0]*2. )*-0.00925925925925926 + ( m[18] + m[11] + m[10] + m[7] + ( m[19] + m[8] + ( -m[14] + m[13] )*3. )*3. + ( -m[24] - m[23] + m[9] - m[20]*3. + ( m[2] + m[1] + m[4]*3. )*2. )*2. )*0.013888888888889;
g16 = ( m[26] - m[0]*2. )*-0.00925925925925926 + ( m[18] + m[11] - m[10] + m[7] + ( m[19] + m[8] + ( -m[14] - m[13] )*3. )*3. + ( -m[24] + m[23] + m[9] + m[20]*3. + ( m[2] - m[1] - m[4]*3. )*2. )*2. )*0.0138888888888889;
g17 = ( m[26] - m[0]*2. )*-0.00925925925925926 + ( m[18] - m[11] + m[10] + m[7] + ( m[19] + m[8] + ( m[14] + m[13] )*3. )*3. + ( m[24] - m[23] + m[9] + m[20]*3. + ( -m[2] + m[1] - m[4]*3. )*2. )*2. )*0.0138888888888889;
g18 = ( m[26] - m[0]*2. )*-0.00925925925925926 + ( m[18] - m[11] - m[10] + m[7] + ( m[19] + m[8] + ( m[14] - m[13] )*3. )*3. + ( m[24] + m[23] + m[9] - m[20]*3. + ( -m[2] - m[1] + m[4]*3. )*2. )*2. )*0.0138888888888889;
g19 = ( m[26] - m[0]*2. )*-0.00925925925925926 + ( m[18] + m[12] + m[10] + m[7] + ( -m[19] - m[8] + ( m[15] - m[13] )*3. )*3. + ( -m[25] - m[23] + m[9] - m[22]*3. + ( m[3] + m[1] + m[6]*3. )*2. )*2. )*0.0138888888888889;
g20 = ( m[26] - m[0]*2. )*-0.00925925925925926 + ( m[18] + m[12] - m[10] + m[7] + ( -m[19] - m[8] + ( m[15] + m[13] )*3. )*3. + ( -m[25] + m[23] + m[9] + m[22]*3. + ( m[3] - m[1] - m[6]*3. )*2. )*2. )*0.0138888888888889;
g21 = ( m[26] - m[0]*2. )*-0.00925925925925926 + ( m[18] - m[12] + m[10] + m[7] + ( -m[19] - m[8] + ( -m[15] - m[13] )*3. )*3. + ( m[25] - m[23] + m[9] + m[22]*3. + ( -m[3] + m[1] - m[6]*3. )*2. )*2. )*0.0138888888888889;
g22 = ( m[26] - m[0]*2. )*-0.00925925925925926 + ( m[18] - m[12] - m[10] + m[7] + ( -m[19] - m[8] + ( -m[15] + m[13] )*3. )*3. + ( m[25] + m[23] + m[9] - m[22]*3. + ( -m[3] - m[1] + m[6]*3. )*2. )*2. )*0.0138888888888889;
g23 = ( m[26] - m[0]*2. )*-0.00925925925925926 + ( m[12] + m[11] + ( -m[15] + m[14] )*9. + ( -m[25] - m[24] - m[18] + m[9] - m[7] - m[21]*3. + ( m[3] + m[2] + m[5]*3. )*2. )*2. )*0.0138888888888889;
g24 = ( m[26] - m[0]*2. )*-0.00925925925925926 + ( m[12] - m[11] + ( -m[15] - m[14] )*9. + ( -m[25] + m[24] - m[18] + m[9] - m[7] + m[21]*3. + ( m[3] - m[2] - m[5]*3. )*2. )*2. )*0.0138888888888889;
g25 = ( m[26] - m[0]*2. )*-0.00925925925925926 + ( -m[12] + m[11] + ( m[15] + m[14] )*9. + ( m[25] - m[24] - m[18] + m[9] - m[7] + m[21]*3. + ( -m[3] + m[2] - m[5]*3. )*2. )*2. )*0.0138888888888889;
g26 = ( m[26] - m[0]*2. )*-0.00925925925925926 + ( m[12] + m[11] + ( -m[15] + m[14] )*9. + ( -m[25] - m[24] + m[18] - m[9] + m[7] + m[21]*3. + ( m[3] + m[2] - m[5]*3. )*2. )*2. )*-0.0138888888888889;

	if (stage16_replay_diagnostics_active()) {
		real_t fphi_sum_diag = 0.0;
		real_t fphi_max_diag = 0.0;
		for (i=0; i<hPops; i++) {
			real_t abs_fphi = fabs(F_phi[i]);
			fphi_sum_diag += F_phi[i];
			if (abs_fphi > fphi_max_diag) fphi_max_diag = abs_fphi;
		}
		ReplayFphiSum = fphi_sum_diag;
		ReplayFphiMaxAbs = fphi_max_diag;
	}

    updateTrackers( C );
}
#endif

//######BOUNDARY CONDITIONS######//

CudaDeviceFunction void NVelocity(){
    U = VelocityX;
    V = VelocityY;
    W = VelocityZ;
    if ( developedFlow > 0.1 ){
        U = 0;
V = ( -1 + Z/HEIGHT )*Z*Uavg/HEIGHT*6.;
W = 0;

    }
    if ( developedPipeFlow > 0.1 ){
        U = 0 * (2.0*Uavg*(1-pow(sqrt(pipeCentre_Z*pipeCentre_Z + Z*Z + pipeCentre_Y*pipeCentre_Y + Y*Y + ( -pipeCentre_Z*Z - pipeCentre_Y*Y )*2.)/pipeRadius,2) )) ;
        V = -1 * (2.0*Uavg*(1-pow(sqrt(pipeCentre_Z*pipeCentre_Z + X*X + pipeCentre_Y*pipeCentre_Y + Z*Z + ( -pipeCentre_Z*X - pipeCentre_Y*Z )*2.)/pipeRadius,2) )) ;
        W = 0 * (2.0*Uavg*(1-pow(sqrt(pipeCentre_Z*pipeCentre_Z + Y*Y + pipeCentre_Y*pipeCentre_Y + X*X + ( -pipeCentre_Z*Y - pipeCentre_Y*X )*2.)/pipeRadius,2) )) ;
    }
	g4 = g3 - V*4./9.;
g9 = g12 + ( -V + ( g6 - g5 + g2 - g1 + W + U + ( g22 - g19 )*2. )*3. )/36.;
g10 = g11 + ( -V + ( g6 - g5 - g2 + g1 + W - U + ( g21 - g20 )*2. )*3. )/36.;
g13 = g8 + ( -V + ( -g6 + g5 + g2 - g1 - W + U + ( -g21 + g20 )*2. )*3. )/36.;
g14 = g7 + ( -V + ( -g6 + g5 - g2 + g1 - W - U + ( -g22 + g19 )*2. )*3. )/36.;
g17 = g16 + ( -V*4. + ( g22 - g21 + g20 - g19 + g2 - g1 + U*2. )*3. )/36.;
g18 = g15 + ( -V*4. + ( -g22 + g21 - g20 + g19 - g2 + g1 - U*2. )*3. )/36.;
g24 = g25 + ( -V*4. + ( g22 + g21 - g20 - g19 + g6 - g5 + W*2. )*3. )/36.;
g26 = g23 + ( -V*4. + ( -g22 - g21 + g20 + g19 - g6 + g5 - W*2. )*3. )/36.;

	h4 = -h3 + PhaseField*5./27. + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 + ( V*V*7. + ( -W*W - U*U )*4. )*PhaseField )/18.;
h9 = -h12 + PhaseField*0.0462962962962963 + ( ( W*W - V*V + U*U + ( -W*V + ( W - V )*U )*3. )*PhaseField + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 )*2. )/36.;
h10 = -h11 + PhaseField*0.0462962962962963 + ( ( W*W - V*V + U*U + ( -W*V + ( -W + V )*U )*3. )*PhaseField + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 )*2. )/36.;
h13 = -h8 + PhaseField*0.0462962962962963 + ( ( W*W - V*V + U*U + ( W*V + ( -W - V )*U )*3. )*PhaseField + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 )*2. )/36.;
h14 = -h7 + PhaseField*0.0462962962962963 + ( ( W*W - V*V + U*U + ( W*V + ( W + V )*U )*3. )*PhaseField + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 )*2. )/36.;
h17 = -h16 + PhaseField*2./27. + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 + ( -W*W + V*V + ( U - V*3. )*U*2. )*PhaseField )/18.;
h18 = -h15 + PhaseField*2./27. + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 + ( -W*W + V*V + ( U + V*3. )*U*2. )*PhaseField )/18.;
h24 = -h25 + PhaseField*2./27. + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 + ( V*V - U*U + ( W - V*3. )*W*2. )*PhaseField )/18.;
h26 = -h23 + PhaseField*2./27. + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 + ( V*V - U*U + ( W + V*3. )*W*2. )*PhaseField )/18.;

}

CudaDeviceFunction void NPressure(){
    real_t d = getRho();
	real_t pstar = Pressure / (d*cs2);
	g4 = -g3 - wg[3] - wg[4] + 5./27. + ( wg[3] + wg[4] )*pstar + ( -wg[22] - g22 - wg[21] - g21 - wg[20] - g20 - wg[19] - g19 - wg[6] - g6 - wg[5] - g5 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + V*V*7. + ( -W*W - U*U )*4. + ( wg[22] + wg[21] + wg[20] + wg[19] + wg[6] + wg[5] + wg[2] + wg[1] + wg[0] )*pstar )/18.;
g9 = -g12 - wg[12] - wg[9] + 0.0462962962962963 + ( wg[12] + wg[9] )*pstar + ( W*W - V*V + U*U + ( -W*V + ( W - V )*U )*3. + ( -wg[22] - g22 - wg[21] - g21 - wg[20] - g20 - wg[19] - g19 - wg[6] - g6 - wg[5] - g5 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + ( wg[22] + wg[21] + wg[20] + wg[19] + wg[6] + wg[5] + wg[2] + wg[1] + wg[0] )*pstar )*2. )/36.;
g10 = -g11 - wg[11] - wg[10] + 0.0462962962962963 + ( wg[11] + wg[10] )*pstar + ( W*W - V*V + U*U + ( -W*V + ( -W + V )*U )*3. + ( -wg[22] - g22 - wg[21] - g21 - wg[20] - g20 - wg[19] - g19 - wg[6] - g6 - wg[5] - g5 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + ( wg[22] + wg[21] + wg[20] + wg[19] + wg[6] + wg[5] + wg[2] + wg[1] + wg[0] )*pstar )*2. )/36.;
g13 = -g8 - wg[8] - wg[13] + 0.0462962962962963 + ( wg[8] + wg[13] )*pstar + ( W*W - V*V + U*U + ( W*V + ( -W - V )*U )*3. + ( -wg[22] - g22 - wg[21] - g21 - wg[20] - g20 - wg[19] - g19 - wg[6] - g6 - wg[5] - g5 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + ( wg[22] + wg[21] + wg[20] + wg[19] + wg[6] + wg[5] + wg[2] + wg[1] + wg[0] )*pstar )*2. )/36.;
g14 = -g7 - wg[7] - wg[14] + 0.0462962962962963 + ( wg[7] + wg[14] )*pstar + ( W*W - V*V + U*U + ( W*V + ( W + V )*U )*3. + ( -wg[22] - g22 - wg[21] - g21 - wg[20] - g20 - wg[19] - g19 - wg[6] - g6 - wg[5] - g5 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + ( wg[22] + wg[21] + wg[20] + wg[19] + wg[6] + wg[5] + wg[2] + wg[1] + wg[0] )*pstar )*2. )/36.;
g17 = -g16 - wg[16] - wg[17] + 2./27. + ( wg[16] + wg[17] )*pstar + ( -wg[22] - g22 - wg[21] - g21 - wg[20] - g20 - wg[19] - g19 - wg[6] - g6 - wg[5] - g5 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 - W*W + V*V + ( U - V*3. )*U*2. + ( wg[22] + wg[21] + wg[20] + wg[19] + wg[6] + wg[5] + wg[2] + wg[1] + wg[0] )*pstar )/18.;
g18 = -g15 - wg[15] - wg[18] + 2./27. + ( wg[15] + wg[18] )*pstar + ( -wg[22] - g22 - wg[21] - g21 - wg[20] - g20 - wg[19] - g19 - wg[6] - g6 - wg[5] - g5 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 - W*W + V*V + ( U + V*3. )*U*2. + ( wg[22] + wg[21] + wg[20] + wg[19] + wg[6] + wg[5] + wg[2] + wg[1] + wg[0] )*pstar )/18.;
g24 = -g25 - wg[25] - wg[24] + 2./27. + ( wg[25] + wg[24] )*pstar + ( -wg[22] - g22 - wg[21] - g21 - wg[20] - g20 - wg[19] - g19 - wg[6] - g6 - wg[5] - g5 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + V*V - U*U + ( W - V*3. )*W*2. + ( wg[22] + wg[21] + wg[20] + wg[19] + wg[6] + wg[5] + wg[2] + wg[1] + wg[0] )*pstar )/18.;
g26 = -g23 - wg[23] - wg[26] + 2./27. + ( wg[23] + wg[26] )*pstar + ( -wg[22] - g22 - wg[21] - g21 - wg[20] - g20 - wg[19] - g19 - wg[6] - g6 - wg[5] - g5 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + V*V - U*U + ( W + V*3. )*W*2. + ( wg[22] + wg[21] + wg[20] + wg[19] + wg[6] + wg[5] + wg[2] + wg[1] + wg[0] )*pstar )/18.;

	h4 = -h3 + PhaseField*5./27. + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 + ( V*V*7. + ( -W*W - U*U )*4. )*PhaseField )/18.;
h9 = -h12 + PhaseField*0.0462962962962963 + ( ( W*W - V*V + U*U + ( -W*V + ( W - V )*U )*3. )*PhaseField + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 )*2. )/36.;
h10 = -h11 + PhaseField*0.0462962962962963 + ( ( W*W - V*V + U*U + ( -W*V + ( -W + V )*U )*3. )*PhaseField + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 )*2. )/36.;
h13 = -h8 + PhaseField*0.0462962962962963 + ( ( W*W - V*V + U*U + ( W*V + ( -W - V )*U )*3. )*PhaseField + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 )*2. )/36.;
h14 = -h7 + PhaseField*0.0462962962962963 + ( ( W*W - V*V + U*U + ( W*V + ( W + V )*U )*3. )*PhaseField + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 )*2. )/36.;
h17 = -h16 + PhaseField*2./27. + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 + ( -W*W + V*V + ( U - V*3. )*U*2. )*PhaseField )/18.;
h18 = -h15 + PhaseField*2./27. + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 + ( -W*W + V*V + ( U + V*3. )*U*2. )*PhaseField )/18.;
h24 = -h25 + PhaseField*2./27. + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 + ( V*V - U*U + ( W - V*3. )*W*2. )*PhaseField )/18.;
h26 = -h23 + PhaseField*2./27. + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 + ( V*V - U*U + ( W + V*3. )*W*2. )*PhaseField )/18.;

}


CudaDeviceFunction void EVelocity(){
    U = VelocityX;
    V = VelocityY;
    W = VelocityZ;
    if ( developedFlow > 0.1 ){
        U = ( -1 + Y/HEIGHT )*Y*Uavg/HEIGHT*6.;
V = 0;
W = 0;

    }
    if ( developedPipeFlow > 0.1 ){
        U = -1 * (2.0*Uavg*(1-pow(sqrt(pipeCentre_Z*pipeCentre_Z + Z*Z + pipeCentre_Y*pipeCentre_Y + Y*Y + ( -pipeCentre_Z*Z - pipeCentre_Y*Y )*2.)/pipeRadius,2) )) ;
        V = 0 * (2.0*Uavg*(1-pow(sqrt(pipeCentre_Z*pipeCentre_Z + X*X + pipeCentre_Y*pipeCentre_Y + Z*Z + ( -pipeCentre_Z*X - pipeCentre_Y*Z )*2.)/pipeRadius,2) )) ;
        W = 0 * (2.0*Uavg*(1-pow(sqrt(pipeCentre_Z*pipeCentre_Z + Y*Y + pipeCentre_Y*pipeCentre_Y + X*X + ( -pipeCentre_Z*Y - pipeCentre_Y*X )*2.)/pipeRadius,2) )) ;
    }
	g2 = g1 - U*4./9.;
g8 = g13 + ( -U + ( g6 - g5 + g4 - g3 + W + V + ( g26 - g23 )*2. )*3. )/36.;
g10 = g11 + ( -U + ( g6 - g5 - g4 + g3 + W - V + ( g25 - g24 )*2. )*3. )/36.;
g12 = g9 + ( -U + ( -g6 + g5 + g4 - g3 - W + V + ( -g25 + g24 )*2. )*3. )/36.;
g14 = g7 + ( -U + ( -g6 + g5 - g4 + g3 - W - V + ( -g26 + g23 )*2. )*3. )/36.;
g16 = g17 + ( -U*4. + ( g26 - g25 + g24 - g23 + g4 - g3 + V*2. )*3. )/36.;
g18 = g15 + ( -U*4. + ( -g26 + g25 - g24 + g23 - g4 + g3 - V*2. )*3. )/36.;
g20 = g21 + ( -U*4. + ( g26 + g25 - g24 - g23 + g6 - g5 + W*2. )*3. )/36.;
g22 = g19 + ( -U*4. + ( -g26 - g25 + g24 + g23 - g6 + g5 - W*2. )*3. )/36.;

	h2 = -h1 + PhaseField*5./27. + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 + ( U*U*7. + ( -W*W - V*V )*4. )*PhaseField )/18.;
h8 = -h13 + PhaseField*0.0462962962962963 + ( ( W*W + V*V - U*U + ( W*V + ( -W - V )*U )*3. )*PhaseField + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 )*2. )/36.;
h10 = -h11 + PhaseField*0.0462962962962963 + ( ( W*W + V*V - U*U + ( -W*V + ( -W + V )*U )*3. )*PhaseField + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 )*2. )/36.;
h12 = -h9 + PhaseField*0.0462962962962963 + ( ( W*W + V*V - U*U + ( -W*V + ( W - V )*U )*3. )*PhaseField + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 )*2. )/36.;
h14 = -h7 + PhaseField*0.0462962962962963 + ( ( W*W + V*V - U*U + ( W*V + ( W + V )*U )*3. )*PhaseField + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 )*2. )/36.;
h16 = -h17 + PhaseField*2./27. + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 + ( -W*W + U*U + ( V - U*3. )*V*2. )*PhaseField )/18.;
h18 = -h15 + PhaseField*2./27. + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 + ( -W*W + U*U + ( V + U*3. )*V*2. )*PhaseField )/18.;
h20 = -h21 + PhaseField*2./27. + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 + ( -V*V + U*U + ( W - U*3. )*W*2. )*PhaseField )/18.;
h22 = -h19 + PhaseField*2./27. + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 + ( -V*V + U*U + ( W + U*3. )*W*2. )*PhaseField )/18.;

}

CudaDeviceFunction void EPressure(){
    real_t d = getRho();
	real_t pstar = Pressure / (d*cs2);
	g2 = -g1 - wg[1] - wg[2] + 5./27. + ( wg[1] + wg[2] )*pstar + ( -wg[26] - g26 - wg[25] - g25 - wg[24] - g24 - wg[23] - g23 - wg[6] - g6 - wg[5] - g5 - wg[4] - g4 - wg[3] - g3 - wg[0] - g0 + U*U*7. + ( -W*W - V*V )*4. + ( wg[26] + wg[25] + wg[24] + wg[23] + wg[6] + wg[5] + wg[4] + wg[3] + wg[0] )*pstar )/18.;
g8 = -g13 - wg[13] - wg[8] + 0.0462962962962963 + ( wg[13] + wg[8] )*pstar + ( W*W + V*V - U*U + ( W*V + ( -W - V )*U )*3. + ( -wg[26] - g26 - wg[25] - g25 - wg[24] - g24 - wg[23] - g23 - wg[6] - g6 - wg[5] - g5 - wg[4] - g4 - wg[3] - g3 - wg[0] - g0 + ( wg[26] + wg[25] + wg[24] + wg[23] + wg[6] + wg[5] + wg[4] + wg[3] + wg[0] )*pstar )*2. )/36.;
g10 = -g11 - wg[11] - wg[10] + 0.0462962962962963 + ( wg[11] + wg[10] )*pstar + ( W*W + V*V - U*U + ( -W*V + ( -W + V )*U )*3. + ( -wg[26] - g26 - wg[25] - g25 - wg[24] - g24 - wg[23] - g23 - wg[6] - g6 - wg[5] - g5 - wg[4] - g4 - wg[3] - g3 - wg[0] - g0 + ( wg[26] + wg[25] + wg[24] + wg[23] + wg[6] + wg[5] + wg[4] + wg[3] + wg[0] )*pstar )*2. )/36.;
g12 = -g9 - wg[9] - wg[12] + 0.0462962962962963 + ( wg[9] + wg[12] )*pstar + ( W*W + V*V - U*U + ( -W*V + ( W - V )*U )*3. + ( -wg[26] - g26 - wg[25] - g25 - wg[24] - g24 - wg[23] - g23 - wg[6] - g6 - wg[5] - g5 - wg[4] - g4 - wg[3] - g3 - wg[0] - g0 + ( wg[26] + wg[25] + wg[24] + wg[23] + wg[6] + wg[5] + wg[4] + wg[3] + wg[0] )*pstar )*2. )/36.;
g14 = -g7 - wg[7] - wg[14] + 0.0462962962962963 + ( wg[7] + wg[14] )*pstar + ( W*W + V*V - U*U + ( W*V + ( W + V )*U )*3. + ( -wg[26] - g26 - wg[25] - g25 - wg[24] - g24 - wg[23] - g23 - wg[6] - g6 - wg[5] - g5 - wg[4] - g4 - wg[3] - g3 - wg[0] - g0 + ( wg[26] + wg[25] + wg[24] + wg[23] + wg[6] + wg[5] + wg[4] + wg[3] + wg[0] )*pstar )*2. )/36.;
g16 = -g17 - wg[17] - wg[16] + 2./27. + ( wg[17] + wg[16] )*pstar + ( -wg[26] - g26 - wg[25] - g25 - wg[24] - g24 - wg[23] - g23 - wg[6] - g6 - wg[5] - g5 - wg[4] - g4 - wg[3] - g3 - wg[0] - g0 - W*W + U*U + ( V - U*3. )*V*2. + ( wg[26] + wg[25] + wg[24] + wg[23] + wg[6] + wg[5] + wg[4] + wg[3] + wg[0] )*pstar )/18.;
g18 = -g15 - wg[15] - wg[18] + 2./27. + ( wg[15] + wg[18] )*pstar + ( -wg[26] - g26 - wg[25] - g25 - wg[24] - g24 - wg[23] - g23 - wg[6] - g6 - wg[5] - g5 - wg[4] - g4 - wg[3] - g3 - wg[0] - g0 - W*W + U*U + ( V + U*3. )*V*2. + ( wg[26] + wg[25] + wg[24] + wg[23] + wg[6] + wg[5] + wg[4] + wg[3] + wg[0] )*pstar )/18.;
g20 = -g21 - wg[21] - wg[20] + 2./27. + ( wg[21] + wg[20] )*pstar + ( -wg[26] - g26 - wg[25] - g25 - wg[24] - g24 - wg[23] - g23 - wg[6] - g6 - wg[5] - g5 - wg[4] - g4 - wg[3] - g3 - wg[0] - g0 - V*V + U*U + ( W - U*3. )*W*2. + ( wg[26] + wg[25] + wg[24] + wg[23] + wg[6] + wg[5] + wg[4] + wg[3] + wg[0] )*pstar )/18.;
g22 = -g19 - wg[19] - wg[22] + 2./27. + ( wg[19] + wg[22] )*pstar + ( -wg[26] - g26 - wg[25] - g25 - wg[24] - g24 - wg[23] - g23 - wg[6] - g6 - wg[5] - g5 - wg[4] - g4 - wg[3] - g3 - wg[0] - g0 - V*V + U*U + ( W + U*3. )*W*2. + ( wg[26] + wg[25] + wg[24] + wg[23] + wg[6] + wg[5] + wg[4] + wg[3] + wg[0] )*pstar )/18.;

	h2 = -h1 + PhaseField*5./27. + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 + ( U*U*7. + ( -W*W - V*V )*4. )*PhaseField )/18.;
h8 = -h13 + PhaseField*0.0462962962962963 + ( ( W*W + V*V - U*U + ( W*V + ( -W - V )*U )*3. )*PhaseField + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 )*2. )/36.;
h10 = -h11 + PhaseField*0.0462962962962963 + ( ( W*W + V*V - U*U + ( -W*V + ( -W + V )*U )*3. )*PhaseField + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 )*2. )/36.;
h12 = -h9 + PhaseField*0.0462962962962963 + ( ( W*W + V*V - U*U + ( -W*V + ( W - V )*U )*3. )*PhaseField + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 )*2. )/36.;
h14 = -h7 + PhaseField*0.0462962962962963 + ( ( W*W + V*V - U*U + ( W*V + ( W + V )*U )*3. )*PhaseField + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 )*2. )/36.;
h16 = -h17 + PhaseField*2./27. + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 + ( -W*W + U*U + ( V - U*3. )*V*2. )*PhaseField )/18.;
h18 = -h15 + PhaseField*2./27. + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 + ( -W*W + U*U + ( V + U*3. )*V*2. )*PhaseField )/18.;
h20 = -h21 + PhaseField*2./27. + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 + ( -V*V + U*U + ( W - U*3. )*W*2. )*PhaseField )/18.;
h22 = -h19 + PhaseField*2./27. + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 + ( -V*V + U*U + ( W + U*3. )*W*2. )*PhaseField )/18.;

}


CudaDeviceFunction void SVelocity(){
    U = VelocityX;
    V = VelocityY;
    W = VelocityZ;
    if ( developedFlow > 0.1 ){
        U = 0;
V = ( 1 - Z/HEIGHT )*Z*Uavg/HEIGHT*6.;
W = 0;

    }
    if ( developedPipeFlow > 0.1 ){
        U = 0 * (2.0*Uavg*(1-pow(sqrt(pipeCentre_Z*pipeCentre_Z + Z*Z + pipeCentre_Y*pipeCentre_Y + Y*Y + ( -pipeCentre_Z*Z - pipeCentre_Y*Y )*2.)/pipeRadius,2) )) ;
        V = 1 * (2.0*Uavg*(1-pow(sqrt(pipeCentre_Z*pipeCentre_Z + X*X + pipeCentre_Y*pipeCentre_Y + Z*Z + ( -pipeCentre_Z*X - pipeCentre_Y*Z )*2.)/pipeRadius,2) )) ;
        W = 0 * (2.0*Uavg*(1-pow(sqrt(pipeCentre_Z*pipeCentre_Z + Y*Y + pipeCentre_Y*pipeCentre_Y + X*X + ( -pipeCentre_Z*Y - pipeCentre_Y*X )*2.)/pipeRadius,2) )) ;
    }
	g3 = g4 + V*4./9.;
g7 = g14 + ( V + ( g6 - g5 + g2 - g1 + W + U + ( g22 - g19 )*2. )*3. )/36.;
g8 = g13 + ( V + ( g6 - g5 - g2 + g1 + W - U + ( g21 - g20 )*2. )*3. )/36.;
g11 = g10 + ( V + ( -g6 + g5 + g2 - g1 - W + U + ( -g21 + g20 )*2. )*3. )/36.;
g12 = g9 + ( V + ( -g6 + g5 - g2 + g1 - W - U + ( -g22 + g19 )*2. )*3. )/36.;
g15 = g18 + ( V*4. + ( g22 - g21 + g20 - g19 + g2 - g1 + U*2. )*3. )/36.;
g16 = g17 + ( V*4. + ( -g22 + g21 - g20 + g19 - g2 + g1 - U*2. )*3. )/36.;
g23 = g26 + ( V*4. + ( g22 + g21 - g20 - g19 + g6 - g5 + W*2. )*3. )/36.;
g25 = g24 + ( V*4. + ( -g22 - g21 + g20 + g19 - g6 + g5 - W*2. )*3. )/36.;

	h3 = -h4 + PhaseField*5./27. + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 + ( V*V*7. + ( -W*W - U*U )*4. )*PhaseField )/18.;
h7 = -h14 + PhaseField*0.0462962962962963 + ( ( W*W - V*V + U*U + ( W*V + ( W + V )*U )*3. )*PhaseField + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 )*2. )/36.;
h8 = -h13 + PhaseField*0.0462962962962963 + ( ( W*W - V*V + U*U + ( W*V + ( -W - V )*U )*3. )*PhaseField + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 )*2. )/36.;
h11 = -h10 + PhaseField*0.0462962962962963 + ( ( W*W - V*V + U*U + ( -W*V + ( -W + V )*U )*3. )*PhaseField + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 )*2. )/36.;
h12 = -h9 + PhaseField*0.0462962962962963 + ( ( W*W - V*V + U*U + ( -W*V + ( W - V )*U )*3. )*PhaseField + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 )*2. )/36.;
h15 = -h18 + PhaseField*2./27. + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 + ( -W*W + V*V + ( U + V*3. )*U*2. )*PhaseField )/18.;
h16 = -h17 + PhaseField*2./27. + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 + ( -W*W + V*V + ( U - V*3. )*U*2. )*PhaseField )/18.;
h23 = -h26 + PhaseField*2./27. + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 + ( V*V - U*U + ( W + V*3. )*W*2. )*PhaseField )/18.;
h25 = -h24 + PhaseField*2./27. + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 + ( V*V - U*U + ( W - V*3. )*W*2. )*PhaseField )/18.;

}

CudaDeviceFunction void SPressure(){
    real_t d = getRho();
	real_t pstar = Pressure / (d*cs2);
	g3 = -g4 - wg[4] - wg[3] + 5./27. + ( wg[4] + wg[3] )*pstar + ( -wg[22] - g22 - wg[21] - g21 - wg[20] - g20 - wg[19] - g19 - wg[6] - g6 - wg[5] - g5 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + V*V*7. + ( -W*W - U*U )*4. + ( wg[22] + wg[21] + wg[20] + wg[19] + wg[6] + wg[5] + wg[2] + wg[1] + wg[0] )*pstar )/18.;
g7 = -g14 - wg[14] - wg[7] + 0.0462962962962963 + ( wg[14] + wg[7] )*pstar + ( W*W - V*V + U*U + ( W*V + ( W + V )*U )*3. + ( -wg[22] - g22 - wg[21] - g21 - wg[20] - g20 - wg[19] - g19 - wg[6] - g6 - wg[5] - g5 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + ( wg[22] + wg[21] + wg[20] + wg[19] + wg[6] + wg[5] + wg[2] + wg[1] + wg[0] )*pstar )*2. )/36.;
g8 = -g13 - wg[13] - wg[8] + 0.0462962962962963 + ( wg[13] + wg[8] )*pstar + ( W*W - V*V + U*U + ( W*V + ( -W - V )*U )*3. + ( -wg[22] - g22 - wg[21] - g21 - wg[20] - g20 - wg[19] - g19 - wg[6] - g6 - wg[5] - g5 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + ( wg[22] + wg[21] + wg[20] + wg[19] + wg[6] + wg[5] + wg[2] + wg[1] + wg[0] )*pstar )*2. )/36.;
g11 = -g10 - wg[10] - wg[11] + 0.0462962962962963 + ( wg[10] + wg[11] )*pstar + ( W*W - V*V + U*U + ( -W*V + ( -W + V )*U )*3. + ( -wg[22] - g22 - wg[21] - g21 - wg[20] - g20 - wg[19] - g19 - wg[6] - g6 - wg[5] - g5 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + ( wg[22] + wg[21] + wg[20] + wg[19] + wg[6] + wg[5] + wg[2] + wg[1] + wg[0] )*pstar )*2. )/36.;
g12 = -g9 - wg[9] - wg[12] + 0.0462962962962963 + ( wg[9] + wg[12] )*pstar + ( W*W - V*V + U*U + ( -W*V + ( W - V )*U )*3. + ( -wg[22] - g22 - wg[21] - g21 - wg[20] - g20 - wg[19] - g19 - wg[6] - g6 - wg[5] - g5 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + ( wg[22] + wg[21] + wg[20] + wg[19] + wg[6] + wg[5] + wg[2] + wg[1] + wg[0] )*pstar )*2. )/36.;
g15 = -g18 - wg[18] - wg[15] + 2./27. + ( wg[18] + wg[15] )*pstar + ( -wg[22] - g22 - wg[21] - g21 - wg[20] - g20 - wg[19] - g19 - wg[6] - g6 - wg[5] - g5 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 - W*W + V*V + ( U + V*3. )*U*2. + ( wg[22] + wg[21] + wg[20] + wg[19] + wg[6] + wg[5] + wg[2] + wg[1] + wg[0] )*pstar )/18.;
g16 = -g17 - wg[17] - wg[16] + 2./27. + ( wg[17] + wg[16] )*pstar + ( -wg[22] - g22 - wg[21] - g21 - wg[20] - g20 - wg[19] - g19 - wg[6] - g6 - wg[5] - g5 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 - W*W + V*V + ( U - V*3. )*U*2. + ( wg[22] + wg[21] + wg[20] + wg[19] + wg[6] + wg[5] + wg[2] + wg[1] + wg[0] )*pstar )/18.;
g23 = -g26 - wg[26] - wg[23] + 2./27. + ( wg[26] + wg[23] )*pstar + ( -wg[22] - g22 - wg[21] - g21 - wg[20] - g20 - wg[19] - g19 - wg[6] - g6 - wg[5] - g5 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 - U*U + V*V + ( W + V*3. )*W*2. + ( wg[22] + wg[21] + wg[20] + wg[19] + wg[6] + wg[5] + wg[2] + wg[1] + wg[0] )*pstar )/18.;
g25 = -g24 - wg[24] - wg[25] + 2./27. + ( wg[24] + wg[25] )*pstar + ( -wg[22] - g22 - wg[21] - g21 - wg[20] - g20 - wg[19] - g19 - wg[6] - g6 - wg[5] - g5 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + V*V - U*U + ( W - V*3. )*W*2. + ( wg[22] + wg[21] + wg[20] + wg[19] + wg[6] + wg[5] + wg[2] + wg[1] + wg[0] )*pstar )/18.;

	h3 = -h4 + PhaseField*5./27. + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 + ( V*V*7. + ( -W*W - U*U )*4. )*PhaseField )/18.;
h7 = -h14 + PhaseField*0.0462962962962963 + ( ( W*W - V*V + U*U + ( W*V + ( W + V )*U )*3. )*PhaseField + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 )*2. )/36.;
h8 = -h13 + PhaseField*0.0462962962962963 + ( ( W*W - V*V + U*U + ( W*V + ( -W - V )*U )*3. )*PhaseField + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 )*2. )/36.;
h11 = -h10 + PhaseField*0.0462962962962963 + ( ( W*W - V*V + U*U + ( -W*V + ( -W + V )*U )*3. )*PhaseField + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 )*2. )/36.;
h12 = -h9 + PhaseField*0.0462962962962963 + ( ( W*W - V*V + U*U + ( -W*V + ( W - V )*U )*3. )*PhaseField + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 )*2. )/36.;
h15 = -h18 + PhaseField*2./27. + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 + ( -W*W + V*V + ( U + V*3. )*U*2. )*PhaseField )/18.;
h16 = -h17 + PhaseField*2./27. + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 + ( -W*W + V*V + ( U - V*3. )*U*2. )*PhaseField )/18.;
h23 = -h26 + PhaseField*2./27. + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 + ( V*V - U*U + ( W + V*3. )*W*2. )*PhaseField )/18.;
h25 = -h24 + PhaseField*2./27. + ( -h22 - h21 - h20 - h19 - h6 - h5 - h2 - h1 - h0 + ( V*V - U*U + ( W - V*3. )*W*2. )*PhaseField )/18.;

}


CudaDeviceFunction void WVelocity(){
    U = VelocityX;
    V = VelocityY;
    W = VelocityZ;
    if ( developedFlow > 0.1 ){
        U = ( 1 - Y/HEIGHT )*Y*Uavg/HEIGHT*6.;
V = 0;
W = 0;

    }
    if ( developedPipeFlow > 0.1 ){
        U = 1 * (2.0*Uavg*(1-pow(sqrt(pipeCentre_Z*pipeCentre_Z + Z*Z + pipeCentre_Y*pipeCentre_Y + Y*Y + ( -pipeCentre_Z*Z - pipeCentre_Y*Y )*2.)/pipeRadius,2) )) ;
        V = 0 * (2.0*Uavg*(1-pow(sqrt(pipeCentre_Z*pipeCentre_Z + X*X + pipeCentre_Y*pipeCentre_Y + Z*Z + ( -pipeCentre_Z*X - pipeCentre_Y*Z )*2.)/pipeRadius,2) )) ;
        W = 0 * (2.0*Uavg*(1-pow(sqrt(pipeCentre_Z*pipeCentre_Z + Y*Y + pipeCentre_Y*pipeCentre_Y + X*X + ( -pipeCentre_Z*Y - pipeCentre_Y*X )*2.)/pipeRadius,2) )) ;
    }
	g1 = g2 + U*4./9.;
g7 = g14 + ( U + ( g6 - g5 + g4 - g3 + W + V + ( g26 - g23 )*2. )*3. )/36.;
g9 = g12 + ( U + ( g6 - g5 - g4 + g3 + W - V + ( g25 - g24 )*2. )*3. )/36.;
g11 = g10 + ( U + ( -g6 + g5 + g4 - g3 - W + V + ( -g25 + g24 )*2. )*3. )/36.;
g13 = g8 + ( U + ( -g6 + g5 - g4 + g3 - W - V + ( -g26 + g23 )*2. )*3. )/36.;
g15 = g18 + ( U*4. + ( g26 - g25 + g24 - g23 + g4 - g3 + V*2. )*3. )/36.;
g17 = g16 + ( U*4. + ( -g26 + g25 - g24 + g23 - g4 + g3 - V*2. )*3. )/36.;
g19 = g22 + ( U*4. + ( g26 + g25 - g24 - g23 + g6 - g5 + W*2. )*3. )/36.;
g21 = g20 + ( U*4. + ( -g26 - g25 + g24 + g23 - g6 + g5 - W*2. )*3. )/36.;

	h1 = -h2 + PhaseField*5./27. + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 + ( U*U*7. + ( -W*W - V*V )*4. )*PhaseField )/18.;
h7 = -h14 + PhaseField*0.0462962962962963 + ( ( W*W + V*V - U*U + ( W*V + ( W + V )*U )*3. )*PhaseField + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 )*2. )/36.;
h9 = -h12 + PhaseField*0.0462962962962963 + ( ( W*W + V*V - U*U + ( -W*V + ( W - V )*U )*3. )*PhaseField + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 )*2. )/36.;
h11 = -h10 + PhaseField*0.0462962962962963 + ( ( W*W + V*V - U*U + ( -W*V + ( -W + V )*U )*3. )*PhaseField + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 )*2. )/36.;
h13 = -h8 + PhaseField*0.0462962962962963 + ( ( W*W + V*V - U*U + ( W*V + ( -W - V )*U )*3. )*PhaseField + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 )*2. )/36.;
h15 = -h18 + PhaseField*2./27. + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 + ( -W*W + U*U + ( V + U*3. )*V*2. )*PhaseField )/18.;
h17 = -h16 + PhaseField*2./27. + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 + ( -W*W + U*U + ( V - U*3. )*V*2. )*PhaseField )/18.;
h19 = -h22 + PhaseField*2./27. + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 + ( -V*V + U*U + ( W + U*3. )*W*2. )*PhaseField )/18.;
h21 = -h20 + PhaseField*2./27. + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 + ( -V*V + U*U + ( W - U*3. )*W*2. )*PhaseField )/18.;

}

CudaDeviceFunction void WPressure(){
    real_t d = getRho();
	real_t pstar = Pressure / (d*cs2);
	g1 = -g2 - wg[2] - wg[1] + 5./27. + ( wg[2] + wg[1] )*pstar + ( -wg[26] - g26 - wg[25] - g25 - wg[24] - g24 - wg[23] - g23 - wg[6] - g6 - wg[5] - g5 - wg[4] - g4 - wg[3] - g3 - wg[0] - g0 + U*U*7. + ( -W*W - V*V )*4. + ( wg[26] + wg[25] + wg[24] + wg[23] + wg[6] + wg[5] + wg[4] + wg[3] + wg[0] )*pstar )/18.;
g7 = -g14 - wg[14] - wg[7] + 0.0462962962962963 + ( wg[14] + wg[7] )*pstar + ( W*W + V*V - U*U + ( W*V + ( W + V )*U )*3. + ( -wg[26] - g26 - wg[25] - g25 - wg[24] - g24 - wg[23] - g23 - wg[6] - g6 - wg[5] - g5 - wg[4] - g4 - wg[3] - g3 - wg[0] - g0 + ( wg[26] + wg[25] + wg[24] + wg[23] + wg[6] + wg[5] + wg[4] + wg[3] + wg[0] )*pstar )*2. )/36.;
g9 = -g12 - wg[12] - wg[9] + 0.0462962962962963 + ( wg[12] + wg[9] )*pstar + ( W*W + V*V - U*U + ( -W*V + ( W - V )*U )*3. + ( -wg[26] - g26 - wg[25] - g25 - wg[24] - g24 - wg[23] - g23 - wg[6] - g6 - wg[5] - g5 - wg[4] - g4 - wg[3] - g3 - wg[0] - g0 + ( wg[26] + wg[25] + wg[24] + wg[23] + wg[6] + wg[5] + wg[4] + wg[3] + wg[0] )*pstar )*2. )/36.;
g11 = -g10 - wg[10] - wg[11] + 0.0462962962962963 + ( wg[10] + wg[11] )*pstar + ( W*W + V*V - U*U + ( -W*V + ( -W + V )*U )*3. + ( -wg[26] - g26 - wg[25] - g25 - wg[24] - g24 - wg[23] - g23 - wg[6] - g6 - wg[5] - g5 - wg[4] - g4 - wg[3] - g3 - wg[0] - g0 + ( wg[26] + wg[25] + wg[24] + wg[23] + wg[6] + wg[5] + wg[4] + wg[3] + wg[0] )*pstar )*2. )/36.;
g13 = -g8 - wg[8] - wg[13] + 0.0462962962962963 + ( wg[8] + wg[13] )*pstar + ( W*W + V*V - U*U + ( W*V + ( -W - V )*U )*3. + ( -wg[26] - g26 - wg[25] - g25 - wg[24] - g24 - wg[23] - g23 - wg[6] - g6 - wg[5] - g5 - wg[4] - g4 - wg[3] - g3 - wg[0] - g0 + ( wg[26] + wg[25] + wg[24] + wg[23] + wg[6] + wg[5] + wg[4] + wg[3] + wg[0] )*pstar )*2. )/36.;
g15 = -g18 - wg[18] - wg[15] + 2./27. + ( wg[18] + wg[15] )*pstar + ( -wg[26] - g26 - wg[25] - g25 - wg[24] - g24 - wg[23] - g23 - wg[6] - g6 - wg[5] - g5 - wg[4] - g4 - wg[3] - g3 - wg[0] - g0 - W*W + U*U + ( V + U*3. )*V*2. + ( wg[26] + wg[25] + wg[24] + wg[23] + wg[6] + wg[5] + wg[4] + wg[3] + wg[0] )*pstar )/18.;
g17 = -g16 - wg[16] - wg[17] + 2./27. + ( wg[16] + wg[17] )*pstar + ( -wg[26] - g26 - wg[25] - g25 - wg[24] - g24 - wg[23] - g23 - wg[6] - g6 - wg[5] - g5 - wg[4] - g4 - wg[3] - g3 - wg[0] - g0 - W*W + U*U + ( V - U*3. )*V*2. + ( wg[26] + wg[25] + wg[24] + wg[23] + wg[6] + wg[5] + wg[4] + wg[3] + wg[0] )*pstar )/18.;
g19 = -g22 - wg[22] - wg[19] + 2./27. + ( wg[22] + wg[19] )*pstar + ( -wg[26] - g26 - wg[25] - g25 - wg[24] - g24 - wg[23] - g23 - wg[6] - g6 - wg[5] - g5 - wg[4] - g4 - wg[3] - g3 - wg[0] - g0 - V*V + U*U + ( W + U*3. )*W*2. + ( wg[26] + wg[25] + wg[24] + wg[23] + wg[6] + wg[5] + wg[4] + wg[3] + wg[0] )*pstar )/18.;
g21 = -g20 - wg[20] - wg[21] + 2./27. + ( wg[20] + wg[21] )*pstar + ( -wg[26] - g26 - wg[25] - g25 - wg[24] - g24 - wg[23] - g23 - wg[6] - g6 - wg[5] - g5 - wg[4] - g4 - wg[3] - g3 - wg[0] - g0 - V*V + U*U + ( W - U*3. )*W*2. + ( wg[26] + wg[25] + wg[24] + wg[23] + wg[6] + wg[5] + wg[4] + wg[3] + wg[0] )*pstar )/18.;

	h1 = -h2 + PhaseField*5./27. + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 + ( U*U*7. + ( -W*W - V*V )*4. )*PhaseField )/18.;
h7 = -h14 + PhaseField*0.0462962962962963 + ( ( W*W + V*V - U*U + ( W*V + ( W + V )*U )*3. )*PhaseField + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 )*2. )/36.;
h9 = -h12 + PhaseField*0.0462962962962963 + ( ( W*W + V*V - U*U + ( -W*V + ( W - V )*U )*3. )*PhaseField + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 )*2. )/36.;
h11 = -h10 + PhaseField*0.0462962962962963 + ( ( W*W + V*V - U*U + ( -W*V + ( -W + V )*U )*3. )*PhaseField + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 )*2. )/36.;
h13 = -h8 + PhaseField*0.0462962962962963 + ( ( W*W + V*V - U*U + ( W*V + ( -W - V )*U )*3. )*PhaseField + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 )*2. )/36.;
h15 = -h18 + PhaseField*2./27. + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 + ( -W*W + U*U + ( V + U*3. )*V*2. )*PhaseField )/18.;
h17 = -h16 + PhaseField*2./27. + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 + ( -W*W + U*U + ( V - U*3. )*V*2. )*PhaseField )/18.;
h19 = -h22 + PhaseField*2./27. + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 + ( -V*V + U*U + ( W + U*3. )*W*2. )*PhaseField )/18.;
h21 = -h20 + PhaseField*2./27. + ( -h26 - h25 - h24 - h23 - h6 - h5 - h4 - h3 - h0 + ( -V*V + U*U + ( W - U*3. )*W*2. )*PhaseField )/18.;

}


CudaDeviceFunction void FVelocity(){
    U = VelocityX;
    V = VelocityY;
    W = VelocityZ;
    if ( developedFlow > 0.1 ){
        U = 0;
V = 0;
W = ( -1 + X/HEIGHT )*X*Uavg/HEIGHT*6.;

    }
    if ( developedPipeFlow > 0.1 ){
        U = 0 * (2.0*Uavg*(1-pow(sqrt(pipeCentre_Z*pipeCentre_Z + Z*Z + pipeCentre_Y*pipeCentre_Y + Y*Y + ( -pipeCentre_Z*Z - pipeCentre_Y*Y )*2.)/pipeRadius,2) )) ;
        V = 0 * (2.0*Uavg*(1-pow(sqrt(pipeCentre_Z*pipeCentre_Z + X*X + pipeCentre_Y*pipeCentre_Y + Z*Z + ( -pipeCentre_Z*X - pipeCentre_Y*Z )*2.)/pipeRadius,2) )) ;
        W = -1 * (2.0*Uavg*(1-pow(sqrt(pipeCentre_Z*pipeCentre_Z + Y*Y + pipeCentre_Y*pipeCentre_Y + X*X + ( -pipeCentre_Z*Y - pipeCentre_Y*X )*2.)/pipeRadius,2) )) ;
    }
	g6 = g5 - W*4./9.;
g11 = g10 + ( -W + ( g4 - g3 + g2 - g1 + V + U + ( g18 - g15 )*2. )*3. )/36.;
g12 = g9 + ( -W + ( g4 - g3 - g2 + g1 + V - U + ( g17 - g16 )*2. )*3. )/36.;
g13 = g8 + ( -W + ( -g4 + g3 + g2 - g1 - V + U + ( -g17 + g16 )*2. )*3. )/36.;
g14 = g7 + ( -W + ( -g4 + g3 - g2 + g1 - V - U + ( -g18 + g15 )*2. )*3. )/36.;
g21 = g20 + ( -W*4. + ( g18 - g17 + g16 - g15 + g2 - g1 + U*2. )*3. )/36.;
g22 = g19 + ( -W*4. + ( -g18 + g17 - g16 + g15 - g2 + g1 - U*2. )*3. )/36.;
g25 = g24 + ( -W*4. + ( g18 + g17 - g16 - g15 + g4 - g3 + V*2. )*3. )/36.;
g26 = g23 + ( -W*4. + ( -g18 - g17 + g16 + g15 - g4 + g3 - V*2. )*3. )/36.;

	h6 = -h5 + PhaseField*5./27. + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 + ( W*W*7. + ( -V*V - U*U )*4. )*PhaseField )/18.;
h11 = -h10 + PhaseField*0.0462962962962963 + ( ( -W*W + V*V + U*U + ( -W*V + ( -W + V )*U )*3. )*PhaseField + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 )*2. )/36.;
h12 = -h9 + PhaseField*0.0462962962962963 + ( ( -W*W + V*V + U*U + ( -W*V + ( W - V )*U )*3. )*PhaseField + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 )*2. )/36.;
h13 = -h8 + PhaseField*0.0462962962962963 + ( ( -W*W + V*V + U*U + ( W*V + ( -W - V )*U )*3. )*PhaseField + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 )*2. )/36.;
h14 = -h7 + PhaseField*0.0462962962962963 + ( ( -W*W + V*V + U*U + ( W*V + ( W + V )*U )*3. )*PhaseField + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 )*2. )/36.;
h21 = -h20 + PhaseField*2./27. + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 + ( W*W - V*V + ( U - W*3. )*U*2. )*PhaseField )/18.;
h22 = -h19 + PhaseField*2./27. + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 + ( W*W - V*V + ( U + W*3. )*U*2. )*PhaseField )/18.;
h25 = -h24 + PhaseField*2./27. + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 + ( W*W - U*U + ( V - W*3. )*V*2. )*PhaseField )/18.;
h26 = -h23 + PhaseField*2./27. + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 + ( W*W - U*U + ( V + W*3. )*V*2. )*PhaseField )/18.;

}

CudaDeviceFunction void FPressure(){
    real_t d = getRho();
	real_t pstar = Pressure / (d*cs2);
	g6 = -g5 - wg[5] - wg[6] + 5./27. + ( wg[5] + wg[6] )*pstar + ( -wg[18] - g18 - wg[17] - g17 - wg[16] - g16 - wg[15] - g15 - wg[4] - g4 - wg[3] - g3 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + W*W*7. + ( -U*U - V*V )*4. + ( wg[18] + wg[17] + wg[16] + wg[15] + wg[4] + wg[3] + wg[2] + wg[1] + wg[0] )*pstar )/18.;
g11 = -g10 - wg[10] - wg[11] + 0.0462962962962963 + ( wg[10] + wg[11] )*pstar + ( -W*W + V*V + U*U + ( -W*V + ( -W + V )*U )*3. + ( -wg[18] - g18 - wg[17] - g17 - wg[16] - g16 - wg[15] - g15 - wg[4] - g4 - wg[3] - g3 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + ( wg[18] + wg[17] + wg[16] + wg[15] + wg[4] + wg[3] + wg[2] + wg[1] + wg[0] )*pstar )*2. )/36.;
g12 = -g9 - wg[9] - wg[12] + 0.0462962962962963 + ( wg[9] + wg[12] )*pstar + ( -W*W + V*V + U*U + ( -W*V + ( W - V )*U )*3. + ( -wg[18] - g18 - wg[17] - g17 - wg[16] - g16 - wg[15] - g15 - wg[4] - g4 - wg[3] - g3 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + ( wg[18] + wg[17] + wg[16] + wg[15] + wg[4] + wg[3] + wg[2] + wg[1] + wg[0] )*pstar )*2. )/36.;
g13 = -g8 - wg[8] - wg[13] + 0.0462962962962963 + ( wg[8] + wg[13] )*pstar + ( -W*W + V*V + U*U + ( W*V + ( -W - V )*U )*3. + ( -wg[18] - g18 - wg[17] - g17 - wg[16] - g16 - wg[15] - g15 - wg[4] - g4 - wg[3] - g3 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + ( wg[18] + wg[17] + wg[16] + wg[15] + wg[4] + wg[3] + wg[2] + wg[1] + wg[0] )*pstar )*2. )/36.;
g14 = -g7 - wg[7] - wg[14] + 0.0462962962962963 + ( wg[7] + wg[14] )*pstar + ( -W*W + V*V + U*U + ( W*V + ( W + V )*U )*3. + ( -wg[18] - g18 - wg[17] - g17 - wg[16] - g16 - wg[15] - g15 - wg[4] - g4 - wg[3] - g3 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + ( wg[18] + wg[17] + wg[16] + wg[15] + wg[4] + wg[3] + wg[2] + wg[1] + wg[0] )*pstar )*2. )/36.;
g21 = -g20 - wg[20] - wg[21] + 2./27. + ( wg[20] + wg[21] )*pstar + ( -wg[18] - g18 - wg[17] - g17 - wg[16] - g16 - wg[15] - g15 - wg[4] - g4 - wg[3] - g3 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + W*W - V*V + ( U - W*3. )*U*2. + ( wg[18] + wg[17] + wg[16] + wg[15] + wg[4] + wg[3] + wg[2] + wg[1] + wg[0] )*pstar )/18.;
g22 = -g19 - wg[19] - wg[22] + 2./27. + ( wg[19] + wg[22] )*pstar + ( -wg[18] - g18 - wg[17] - g17 - wg[16] - g16 - wg[15] - g15 - wg[4] - g4 - wg[3] - g3 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + W*W - V*V + ( U + W*3. )*U*2. + ( wg[18] + wg[17] + wg[16] + wg[15] + wg[4] + wg[3] + wg[2] + wg[1] + wg[0] )*pstar )/18.;
g25 = -g24 - wg[24] - wg[25] + 2./27. + ( wg[24] + wg[25] )*pstar + ( -wg[18] - g18 - wg[17] - g17 - wg[16] - g16 - wg[15] - g15 - wg[4] - g4 - wg[3] - g3 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + W*W - U*U + ( V - W*3. )*V*2. + ( wg[18] + wg[17] + wg[16] + wg[15] + wg[4] + wg[3] + wg[2] + wg[1] + wg[0] )*pstar )/18.;
g26 = -g23 - wg[23] - wg[26] + 2./27. + ( wg[23] + wg[26] )*pstar + ( -wg[18] - g18 - wg[17] - g17 - wg[16] - g16 - wg[15] - g15 - wg[4] - g4 - wg[3] - g3 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + W*W - U*U + ( V + W*3. )*V*2. + ( wg[18] + wg[17] + wg[16] + wg[15] + wg[4] + wg[3] + wg[2] + wg[1] + wg[0] )*pstar )/18.;

	h6 = -h5 + PhaseField*5./27. + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 + ( W*W*7. + ( -V*V - U*U )*4. )*PhaseField )/18.;
h11 = -h10 + PhaseField*0.0462962962962963 + ( ( -W*W + V*V + U*U + ( -W*V + ( -W + V )*U )*3. )*PhaseField + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 )*2. )/36.;
h12 = -h9 + PhaseField*0.0462962962962963 + ( ( -W*W + V*V + U*U + ( -W*V + ( W - V )*U )*3. )*PhaseField + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 )*2. )/36.;
h13 = -h8 + PhaseField*0.0462962962962963 + ( ( -W*W + V*V + U*U + ( W*V + ( -W - V )*U )*3. )*PhaseField + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 )*2. )/36.;
h14 = -h7 + PhaseField*0.0462962962962963 + ( ( -W*W + V*V + U*U + ( W*V + ( W + V )*U )*3. )*PhaseField + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 )*2. )/36.;
h21 = -h20 + PhaseField*2./27. + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 + ( W*W - V*V + ( U - W*3. )*U*2. )*PhaseField )/18.;
h22 = -h19 + PhaseField*2./27. + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 + ( W*W - V*V + ( U + W*3. )*U*2. )*PhaseField )/18.;
h25 = -h24 + PhaseField*2./27. + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 + ( W*W - U*U + ( V - W*3. )*V*2. )*PhaseField )/18.;
h26 = -h23 + PhaseField*2./27. + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 + ( W*W - U*U + ( V + W*3. )*V*2. )*PhaseField )/18.;

}


CudaDeviceFunction void BVelocity(){
    U = VelocityX;
    V = VelocityY;
    W = VelocityZ;
    if ( developedFlow > 0.1 ){
        U = 0;
V = 0;
W = ( 1 - X/HEIGHT )*X*Uavg/HEIGHT*6.;

    }
    if ( developedPipeFlow > 0.1 ){
        U = 0 * (2.0*Uavg*(1-pow(sqrt(pipeCentre_Z*pipeCentre_Z + Z*Z + pipeCentre_Y*pipeCentre_Y + Y*Y + ( -pipeCentre_Z*Z - pipeCentre_Y*Y )*2.)/pipeRadius,2) )) ;
        V = 0 * (2.0*Uavg*(1-pow(sqrt(pipeCentre_Z*pipeCentre_Z + X*X + pipeCentre_Y*pipeCentre_Y + Z*Z + ( -pipeCentre_Z*X - pipeCentre_Y*Z )*2.)/pipeRadius,2) )) ;
        W = 1 * (2.0*Uavg*(1-pow(sqrt(pipeCentre_Z*pipeCentre_Z + Y*Y + pipeCentre_Y*pipeCentre_Y + X*X + ( -pipeCentre_Z*Y - pipeCentre_Y*X )*2.)/pipeRadius,2) )) ;
    }
	g5 = g6 + W*4./9.;
g7 = g14 + ( W + ( g4 - g3 + g2 - g1 + V + U + ( g18 - g15 )*2. )*3. )/36.;
g8 = g13 + ( W + ( g4 - g3 - g2 + g1 + V - U + ( g17 - g16 )*2. )*3. )/36.;
g9 = g12 + ( W + ( -g4 + g3 + g2 - g1 - V + U + ( -g17 + g16 )*2. )*3. )/36.;
g10 = g11 + ( W + ( -g4 + g3 - g2 + g1 - V - U + ( -g18 + g15 )*2. )*3. )/36.;
g19 = g22 + ( W*4. + ( g18 - g17 + g16 - g15 + g2 - g1 + U*2. )*3. )/36.;
g20 = g21 + ( W*4. + ( -g18 + g17 - g16 + g15 - g2 + g1 - U*2. )*3. )/36.;
g23 = g26 + ( W*4. + ( g18 + g17 - g16 - g15 + g4 - g3 + V*2. )*3. )/36.;
g24 = g25 + ( W*4. + ( -g18 - g17 + g16 + g15 - g4 + g3 - V*2. )*3. )/36.;

	h5 = -h6 + PhaseField*5./27. + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 + ( W*W*7. + ( -V*V - U*U )*4. )*PhaseField )/18.;
h7 = -h14 + PhaseField*0.0462962962962963 + ( ( -W*W + V*V + U*U + ( W*V + ( W + V )*U )*3. )*PhaseField + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 )*2. )/36.;
h8 = -h13 + PhaseField*0.0462962962962963 + ( ( -W*W + V*V + U*U + ( W*V + ( -W - V )*U )*3. )*PhaseField + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 )*2. )/36.;
h9 = -h12 + PhaseField*0.0462962962962963 + ( ( -W*W + V*V + U*U + ( -W*V + ( W - V )*U )*3. )*PhaseField + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 )*2. )/36.;
h10 = -h11 + PhaseField*0.0462962962962963 + ( ( -W*W + V*V + U*U + ( -W*V + ( -W + V )*U )*3. )*PhaseField + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 )*2. )/36.;
h19 = -h22 + PhaseField*2./27. + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 + ( W*W - V*V + ( U + W*3. )*U*2. )*PhaseField )/18.;
h20 = -h21 + PhaseField*2./27. + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 + ( W*W - V*V + ( U - W*3. )*U*2. )*PhaseField )/18.;
h23 = -h26 + PhaseField*2./27. + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 + ( W*W - U*U + ( V + W*3. )*V*2. )*PhaseField )/18.;
h24 = -h25 + PhaseField*2./27. + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 + ( W*W - U*U + ( V - W*3. )*V*2. )*PhaseField )/18.;

}

CudaDeviceFunction void BPressure(){
    real_t d = getRho();
	real_t pstar = Pressure / (d*cs2);
	g5 = -g6 - wg[6] - wg[5] + 5./27. + ( wg[6] + wg[5] )*pstar + ( -wg[18] - g18 - wg[17] - g17 - wg[16] - g16 - wg[15] - g15 - wg[4] - g4 - wg[3] - g3 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + W*W*7. + ( -V*V - U*U )*4. + ( wg[18] + wg[17] + wg[16] + wg[15] + wg[4] + wg[3] + wg[2] + wg[1] + wg[0] )*pstar )/18.;
g7 = -g14 - wg[14] - wg[7] + 0.0462962962962963 + ( wg[14] + wg[7] )*pstar + ( -W*W + V*V + U*U + ( W*V + ( W + V )*U )*3. + ( -wg[18] - g18 - wg[17] - g17 - wg[16] - g16 - wg[15] - g15 - wg[4] - g4 - wg[3] - g3 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + ( wg[18] + wg[17] + wg[16] + wg[15] + wg[4] + wg[3] + wg[2] + wg[1] + wg[0] )*pstar )*2. )/36.;
g8 = -g13 - wg[13] - wg[8] + 0.0462962962962963 + ( wg[13] + wg[8] )*pstar + ( -W*W + V*V + U*U + ( W*V + ( -W - V )*U )*3. + ( -wg[18] - g18 - wg[17] - g17 - wg[16] - g16 - wg[15] - g15 - wg[4] - g4 - wg[3] - g3 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + ( wg[18] + wg[17] + wg[16] + wg[15] + wg[4] + wg[3] + wg[2] + wg[1] + wg[0] )*pstar )*2. )/36.;
g9 = -g12 - wg[12] - wg[9] + 0.0462962962962963 + ( wg[12] + wg[9] )*pstar + ( -W*W + V*V + U*U + ( -W*V + ( W - V )*U )*3. + ( -wg[18] - g18 - wg[17] - g17 - wg[16] - g16 - wg[15] - g15 - wg[4] - g4 - wg[3] - g3 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + ( wg[18] + wg[17] + wg[16] + wg[15] + wg[4] + wg[3] + wg[2] + wg[1] + wg[0] )*pstar )*2. )/36.;
g10 = -g11 - wg[11] - wg[10] + 0.0462962962962963 + ( wg[11] + wg[10] )*pstar + ( -W*W + V*V + U*U + ( -W*V + ( -W + V )*U )*3. + ( -wg[18] - g18 - wg[17] - g17 - wg[16] - g16 - wg[15] - g15 - wg[4] - g4 - wg[3] - g3 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + ( wg[18] + wg[17] + wg[16] + wg[15] + wg[4] + wg[3] + wg[2] + wg[1] + wg[0] )*pstar )*2. )/36.;
g19 = -g22 - wg[22] - wg[19] + 2./27. + ( wg[22] + wg[19] )*pstar + ( -wg[18] - g18 - wg[17] - g17 - wg[16] - g16 - wg[15] - g15 - wg[4] - g4 - wg[3] - g3 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + W*W - V*V + ( U + W*3. )*U*2. + ( wg[18] + wg[17] + wg[16] + wg[15] + wg[4] + wg[3] + wg[2] + wg[1] + wg[0] )*pstar )/18.;
g20 = -g21 - wg[21] - wg[20] + 2./27. + ( wg[21] + wg[20] )*pstar + ( -wg[18] - g18 - wg[17] - g17 - wg[16] - g16 - wg[15] - g15 - wg[4] - g4 - wg[3] - g3 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + W*W - V*V + ( U - W*3. )*U*2. + ( wg[18] + wg[17] + wg[16] + wg[15] + wg[4] + wg[3] + wg[2] + wg[1] + wg[0] )*pstar )/18.;
g23 = -g26 - wg[26] - wg[23] + 2./27. + ( wg[26] + wg[23] )*pstar + ( -wg[18] - g18 - wg[17] - g17 - wg[16] - g16 - wg[15] - g15 - wg[4] - g4 - wg[3] - g3 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 - U*U + W*W + ( V + W*3. )*V*2. + ( wg[18] + wg[17] + wg[16] + wg[15] + wg[4] + wg[3] + wg[2] + wg[1] + wg[0] )*pstar )/18.;
g24 = -g25 - wg[25] - wg[24] + 2./27. + ( wg[25] + wg[24] )*pstar + ( -wg[18] - g18 - wg[17] - g17 - wg[16] - g16 - wg[15] - g15 - wg[4] - g4 - wg[3] - g3 - wg[2] - g2 - wg[1] - g1 - wg[0] - g0 + W*W - U*U + ( V - W*3. )*V*2. + ( wg[18] + wg[17] + wg[16] + wg[15] + wg[4] + wg[3] + wg[2] + wg[1] + wg[0] )*pstar )/18.;

	h5 = -h6 + PhaseField*5./27. + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 + ( W*W*7. + ( -V*V - U*U )*4. )*PhaseField )/18.;
h7 = -h14 + PhaseField*0.0462962962962963 + ( ( -W*W + V*V + U*U + ( W*V + ( W + V )*U )*3. )*PhaseField + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 )*2. )/36.;
h8 = -h13 + PhaseField*0.0462962962962963 + ( ( -W*W + V*V + U*U + ( W*V + ( -W - V )*U )*3. )*PhaseField + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 )*2. )/36.;
h9 = -h12 + PhaseField*0.0462962962962963 + ( ( -W*W + V*V + U*U + ( -W*V + ( W - V )*U )*3. )*PhaseField + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 )*2. )/36.;
h10 = -h11 + PhaseField*0.0462962962962963 + ( ( -W*W + V*V + U*U + ( -W*V + ( -W + V )*U )*3. )*PhaseField + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 )*2. )/36.;
h19 = -h22 + PhaseField*2./27. + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 + ( W*W - V*V + ( U + W*3. )*U*2. )*PhaseField )/18.;
h20 = -h21 + PhaseField*2./27. + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 + ( W*W - V*V + ( U - W*3. )*U*2. )*PhaseField )/18.;
h23 = -h26 + PhaseField*2./27. + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 + ( W*W - U*U + ( V + W*3. )*V*2. )*PhaseField )/18.;
h24 = -h25 + PhaseField*2./27. + ( -h18 - h17 - h16 - h15 - h4 - h3 - h2 - h1 - h0 + ( W*W - U*U + ( V - W*3. )*V*2. )*PhaseField )/18.;

}



#ifdef OPTIONS_OutFlow

#define myMax(a,b) \
   ({ __typeof__ (a) _a = (a); \
       __typeof__ (b) _b = (b); \
     _a > _b ? _a : _b; })
// Convective boundary from: A phase-field lattice Boltzmann model for simulating multiphase flows
//							in porous media: Application and comparison to experiments of CO2
//							sequestration at pore scale
CudaDeviceFunction void EConvect(){
	real_t U_local = myMax(0, U(-1,0,0));
	real_t invU = 1.0/(1+ U_local);

}
CudaDeviceFunction void WConvect(){
	real_t U_local = myMax(0, -U(1,0,0));
	real_t invU = 1.0/(1 - U_local);

}

CudaDeviceFunction void ENeumann(){

}
CudaDeviceFunction void WNeumann(){

}
#endif

CudaDeviceFunction void MovingNWall(){
	// Experimental, use with care!

	g4  = g3;
	g24 = g25;
	g26 = g23;

	g9  = g12 + VelocityX/36.0;
	g13 = g8  + VelocityX/36.0;
	g17 = g16 + VelocityX/9.0;

	g10 = g11 - VelocityX/36.0;
	g14 = g7  - VelocityX/36.0;
	g18 = g15 - VelocityX/9.0;
	{
		/********* pressure-type Zou He boundary condition  ****************/
real_t Rx  =  -PhaseField + h26 + h25 + h24 + h23 + h6 + h5 + h4 + h3 + h0 + ( h21 + h19 + h17 + h15 + h11 + h9 + h13 + h7 + h1 )*2. ;
real_t Ry  =  ( h26 - h25 + h24 - h23 + h4 - h3 )*3. ;
real_t Rz  =  ( h26 + h25 - h24 - h23 + h6 - h5 )*3. ;
h2 = h1 - Rx*4./9.;
h8 = h13 + ( Rz + Ry - Rx )/36.;
h10 = h11 + ( Rz - Ry - Rx )/36.;
h12 = h9 + ( -Rz + Ry - Rx )/36.;
h14 = h7 + ( -Rz - Ry - Rx )/36.;
h16 = h17 + ( Ry - Rx )/9.;
h18 = h15 + ( -Ry - Rx )/9.;
h20 = h21 + ( Rz - Rx )/9.;
h22 = h19 + ( -Rz - Rx )/9.;

	}
}

CudaDeviceFunction void MovingSWall(){
	// Experimental, use with care!

	g3  = g4;
	g25 = g24;
	g23 = g26;

	g12 = g9  - VelocityX/36.0;
	g8  = g13 - VelocityX/36.0;
	g16 = g17 - VelocityX/9.0;

	g11 = g10 + VelocityX/36.0;
	g7  = g14 + VelocityX/36.0;
	g15 = g18 + VelocityX/9.0;
	{
		/********* pressure-type Zou He boundary condition  ****************/
real_t Rx  =  -PhaseField + h26 + h25 + h24 + h23 + h6 + h5 + h4 + h3 + h0 + ( h21 + h19 + h17 + h15 + h11 + h9 + h13 + h7 + h1 )*2. ;
real_t Ry  =  ( h26 - h25 + h24 - h23 + h4 - h3 )*3. ;
real_t Rz  =  ( h26 + h25 - h24 - h23 + h6 - h5 )*3. ;
h2 = h1 - Rx*4./9.;
h8 = h13 + ( Rz + Ry - Rx )/36.;
h10 = h11 + ( Rz - Ry - Rx )/36.;
h12 = h9 + ( -Rz + Ry - Rx )/36.;
h14 = h7 + ( -Rz - Ry - Rx )/36.;
h16 = h17 + ( Ry - Rx )/9.;
h18 = h15 + ( -Ry - Rx )/9.;
h20 = h21 + ( Rz - Rx )/9.;
h22 = h19 + ( -Rz - Rx )/9.;

	}
}

CudaDeviceFunction void BounceBack(){
	real_t tmp;
	tmp = g0; g0 = g0; g0 = tmp;
	tmp = g1; g1 = g2; g2 = tmp;
	tmp = g3; g3 = g4; g4 = tmp;
	tmp = g5; g5 = g6; g6 = tmp;
	tmp = g7; g7 = g14; g14 = tmp;
	tmp = g8; g8 = g13; g13 = tmp;
	tmp = g9; g9 = g12; g12 = tmp;
	tmp = g10; g10 = g11; g11 = tmp;
	tmp = g15; g15 = g18; g18 = tmp;
	tmp = g16; g16 = g17; g17 = tmp;
	tmp = g19; g19 = g22; g22 = tmp;
	tmp = g20; g20 = g21; g21 = tmp;
	tmp = g23; g23 = g26; g26 = tmp;
	tmp = g24; g24 = g25; g25 = tmp;

	tmp = h0; h0 = h0; h0 = tmp;
	tmp = h1; h1 = h2; h2 = tmp;
	tmp = h3; h3 = h4; h4 = tmp;
	tmp = h5; h5 = h6; h6 = tmp;
	tmp = h7; h7 = h14; h14 = tmp;
	tmp = h8; h8 = h13; h13 = tmp;
	tmp = h9; h9 = h12; h12 = tmp;
	tmp = h10; h10 = h11; h11 = tmp;
#ifdef OPTIONS_q27
	tmp = h15; h15 = h18; h18 = tmp;
	tmp = h16; h16 = h17; h17 = tmp;
	tmp = h19; h19 = h22; h22 = tmp;
	tmp = h20; h20 = h21; h21 = tmp;
	tmp = h23; h23 = h26; h26 = tmp;
	tmp = h24; h24 = h25; h25 = tmp;
#endif
}

//######WETTING CONDITION DETAILS######//


//##################################################################//
//### STAGE9: ANALYTIC-GEOMETRY DIFFUSE-INTERFACE WETTING BC ######//
//###                                                            ###//
//### Physics: discretise the exact Cahn-Hilliard natural wall BC ###//
//###   kappa * d(phi)/d(n_w) = gamma_sv * cos(theta_e)          ###//
//### using the analytic wall normal n_w and signed distance h,   ###//
//### instead of the lattice-recovered normal. See                ###//
//### docs/stage9/analytic_wetting_bc_design_20260614.md.         ###//
//##################################################################//

// ---- coordinate access (X,Y,Z are TCLB-provided globals) ----
CudaDeviceFunction real_t stage9_coord_x() { return X; }
CudaDeviceFunction real_t stage9_coord_y() { return Y; }
CudaDeviceFunction real_t stage9_coord_z() { return Z; }

// ---- analytic geometry primitives ----
// All normals are outward wall unit normals pointing INTO THE FLUID.
// Signed distance h is positive for points in the fluid, negative in the solid.

// Plane: defined by axis (AnalyticSolidAxis) and offset along that axis.
// Fluid side is the +axis side; wall normal points +axis.
CudaDeviceFunction vector_t stage9_plane_normal() {
	vector_t n = {0.0, 0.0, 0.0};
	if (AnalyticSolidAxis < 0.5)        { n.x = 1.0; }
	else if (AnalyticSolidAxis < 1.5)   { n.y = 1.0; }
	else                                { n.z = 1.0; }
	return n;
}
CudaDeviceFunction real_t stage9_plane_signed_distance() {
	real_t coord = (AnalyticSolidAxis < 0.5) ? X
	             : (AnalyticSolidAxis < 1.5) ? Y : Z;
	return coord - AnalyticSolidPlaneOffset;
}

// Infinite cylinder: axis = AnalyticSolidAxis, radius AnalyticSolidRadius,
// centered at (cx,cy,cz) in the perpendicular plane. The cylinder axis
// coordinate is ignored for the distance/normal computation.
CudaDeviceFunction void stage9_cylinder_perp_components(real_t* a, real_t* b) {
	real_t dx = X - AnalyticSolidCenterX;
	real_t dy = Y - AnalyticSolidCenterY;
	real_t dz = Z - AnalyticSolidCenterZ;
	if (AnalyticSolidAxis < 0.5)        { *a = dy; *b = dz; }   // axis = x
	else if (AnalyticSolidAxis < 1.5)   { *a = dx; *b = dz; }   // axis = y
	else                                { *a = dx; *b = dy; }   // axis = z
}
CudaDeviceFunction vector_t stage9_cylinder_normal() {
	real_t a, b;
	stage9_cylinder_perp_components(&a, &b);
	real_t r = sqrt(a*a + b*b);
	vector_t n = {0.0, 0.0, 0.0};
	if (r < 1e-30) return n;
	real_t inv = 1.0/r;
	// axis = x: perp plane is (y,z); axis = y: perp plane is (x,z); axis = z: perp plane is (x,y)
	if (AnalyticSolidAxis < 0.5)        { n.y = a*inv; n.z = b*inv; }
	else if (AnalyticSolidAxis < 1.5)   { n.x = a*inv; n.z = b*inv; }
	else                                { n.x = a*inv; n.y = b*inv; }
	return n;
}
CudaDeviceFunction real_t stage9_cylinder_signed_distance() {
	real_t a, b;
	stage9_cylinder_perp_components(&a, &b);
	return sqrt(a*a + b*b) - AnalyticSolidRadius;
}

// Sphere: center (cx,cy,cz), radius AnalyticSolidRadius.
CudaDeviceFunction vector_t stage9_sphere_normal() {
	real_t dx = X - AnalyticSolidCenterX;
	real_t dy = Y - AnalyticSolidCenterY;
	real_t dz = Z - AnalyticSolidCenterZ;
	real_t r = sqrt(dx*dx + dy*dy + dz*dz);
	vector_t n = {0.0, 0.0, 0.0};
	if (r < 1e-30) return n;
	real_t inv = 1.0/r;
	n.x = dx*inv; n.y = dy*inv; n.z = dz*inv;
	return n;
}
CudaDeviceFunction real_t stage9_sphere_signed_distance() {
	real_t dx = X - AnalyticSolidCenterX;
	real_t dy = Y - AnalyticSolidCenterY;
	real_t dz = Z - AnalyticSolidCenterZ;
	return sqrt(dx*dx + dy*dy + dz*dz) - AnalyticSolidRadius;
}

CudaDeviceFunction real_t stage13_analytic_signed_distance_at_offset(real_t ox, real_t oy, real_t oz)
{
	real_t px = X + ox;
	real_t py = Y + oy;
	real_t pz = Z + oz;
	real_t t = AnalyticSolidType;
	if (AnalyticWetting < 0.5 || t < 0.5) return 1.0;
	if (t < 1.5) {
		real_t coord = (AnalyticSolidAxis < 0.5) ? px
		             : (AnalyticSolidAxis < 1.5) ? py : pz;
		return coord - AnalyticSolidPlaneOffset;
	}
	if (t < 2.5) {
		real_t dx = px - AnalyticSolidCenterX;
		real_t dy = py - AnalyticSolidCenterY;
		real_t dz = pz - AnalyticSolidCenterZ;
		real_t a = 0.0;
		real_t b = 0.0;
		if (AnalyticSolidAxis < 0.5)        { a = dy; b = dz; }
		else if (AnalyticSolidAxis < 1.5)   { a = dx; b = dz; }
		else                                { a = dx; b = dy; }
		return sqrt(a*a + b*b) - AnalyticSolidRadius;
	}
	real_t dx = px - AnalyticSolidCenterX;
	real_t dy = py - AnalyticSolidCenterY;
	real_t dz = pz - AnalyticSolidCenterZ;
	return sqrt(dx*dx + dy*dy + dz*dz) - AnalyticSolidRadius;
}

CudaDeviceFunction int stage13_compact_vertex_is_geometric_fluid(int ox, int oy, int oz)
{
	real_t sd = stage13_analytic_signed_distance_at_offset((real_t)ox, (real_t)oy, (real_t)oz);
	return (sd > 1.0e-9);
}

// Dispatch: fill out_n and out_h for the declared analytic geometry.
// Returns the analytic wall normal (unit, pointing into fluid). out_h receives
// the signed distance (>0 in fluid). If AnalyticWetting is off or the geometry
// is invalid, returns the zero vector and out_h = 0; callers must check.
CudaDeviceFunction vector_t stage9_analytic_wall_normal_and_distance(real_t* out_h) {
	vector_t n = {0.0, 0.0, 0.0};
	*out_h = 0.0;
	if (AnalyticWetting < 0.5) return n;
	real_t t = AnalyticSolidType;
	if (t < 0.5)        return n;                                  // off
	else if (t < 1.5)   { n = stage9_plane_normal();     *out_h = stage9_plane_signed_distance();     }
	else if (t < 2.5)   { n = stage9_cylinder_normal();  *out_h = stage9_cylinder_signed_distance();  }
	else                { n = stage9_sphere_normal();    *out_h = stage9_sphere_signed_distance();    }
	return n;
}

CudaDeviceFunction int stage9_probe_component(real_t n) {
	if (n >  0.5) return  1;
	if (n < -0.5) return -1;
	return 0;
}

// Curvature (1/R) used for the leading-order centered-difference correction.
// Plane = 0, cylinder = 1/R, sphere = 1/R.
CudaDeviceFunction real_t stage9_analytic_curvature() {
	real_t t = AnalyticSolidType;
	if (t < 2.5) {  // plane or cylinder
		if (t < 1.5) return 0.0;
		if (AnalyticSolidRadius > 1e-30) return 1.0/AnalyticSolidRadius;
		return 0.0;
	}
	if (AnalyticSolidRadius > 1e-30) return 1.0/AnalyticSolidRadius;
	return 0.0;
}

// ---- trilinear interpolation of the physical phase field ----
// NOTE: TCLB's PhaseF(dx,dy,dz) reads RELATIVE to the current node, so absolute
// lattice coordinates cannot be indexed portably. The diffuse BC is therefore
// evaluated at the first fluid node itself using the local isotropic gradient
// (gradPhiVal_*), which is already a high-order isotropic estimate of grad(phi)
// at this node. phi_0 = PhaseF(0,0,0). No trilinear probe is needed. This keeps
// the BC local and avoids reading ghost/sentinel values on wall nodes.

// Compute the wall ghost value using the diffuse-interface wetting BC.
// Called from calcWallPhase on a wall/solid node, with:
//   n_w  : analytic wall unit normal (pointing into fluid), already in nw_*
//   h0   : analytic signed distance from this wall node to the surface + 0.5
//   phi_0: phase at the first fluid node along +n_w (caller passes PhaseF_dyn(nw))
//   grad : phase gradient at the first fluid node along +n_w
//
// Discrete BC (see design doc sec 1.3):
//   phi_ghost = phi_0 + 2*h0 * tan(pi/2 - theta) * |grad_t phi|
//             + (h0^2/R) * tan(pi/2 - theta) * |grad_t phi|     [curvature corr]
//
// grad_t: gradient projected onto the analytic tangent plane (perp to n_w).
CudaDeviceFunction real_t stage13_clamp_phase_value(real_t raw, real_t *clamp_hit)
{
	real_t out = raw;
	*clamp_hit = 0.0;
	if (out < PhaseField_l) {
		out = PhaseField_l;
		*clamp_hit = 1.0;
	}
	if (out > PhaseField_h) {
		out = PhaseField_h;
		*clamp_hit = 1.0;
	}
	return out;
}

CudaDeviceFunction real_t stage13_compute_geometric_tangent_raw(
	vector_t n_w, real_t h0, real_t phi_0, vector_t grad, real_t theta)
{
	real_t phase_range = PhaseField_h - PhaseField_l;
	if (fabs(phase_range) < 1e-12) phase_range = 1.0;

	// project gradient onto tangent plane: grad_t = grad - (grad.n_w) n_w
	real_t gdotn = grad.x*n_w.x + grad.y*n_w.y + grad.z*n_w.z;
	vector_t grad_t;
	grad_t.x = grad.x - gdotn * n_w.x;
	grad_t.y = grad.y - gdotn * n_w.y;
	grad_t.z = grad.z - gdotn * n_w.z;
	real_t gt_mag = sqrt(grad_t.x*grad_t.x + grad_t.y*grad_t.y + grad_t.z*grad_t.z);

	real_t tan_coeff = tan(PI/2.0 - theta);
	real_t kappa_corr = stage9_analytic_curvature() * h0 * h0;

	return phi_0 + 2.0 * h0 * tan_coeff * gt_mag
	             + kappa_corr * tan_coeff * gt_mag;
}

CudaDeviceFunction real_t stage9_calc_wall_ghost(
	vector_t n_w, real_t h0, real_t phi_0, vector_t grad)
{
	real_t clamp_hit = 0.0;
	real_t raw = stage13_compute_geometric_tangent_raw(n_w, h0, phi_0, grad, radAngle);
	return stage13_clamp_phase_value(raw, &clamp_hit);
}

CudaDeviceFunction real_t stage13_compute_briant_wall_ghost_raw(
	real_t phi_f, real_t h0, real_t theta, real_t *path_id)
{
	real_t a = -h0 * (4.0/IntWidth) * cos(theta);
	real_t discrim = (1.0+a)*(1.0+a) - 4.0*a*phi_f;
	*path_id = 2.0;
	if (discrim < 0.0) {
		*path_id = -2.0;
		return phi_f;
	}
	return (1.0 + a - sqrt(discrim))/(a + 1e-12) - phi_f;
}

CudaDeviceFunction real_t stage13_compute_analytic_wall_ghost(
	vector_t n_w, real_t h0, real_t phi_f, vector_t grad, real_t theta,
	real_t *raw_out, real_t *clamped_out, real_t *clamp_hit, real_t *path_id)
{
	if (fabs(theta - PI/2.0) < 1e-4) {
		*path_id = 1.0;
		*raw_out = phi_f;
		*clamped_out = phi_f;
		*clamp_hit = 0.0;
		return phi_f;
	}

	real_t raw;
	if (WettingBCMode > 0.5 && WettingBCMode < 1.5) {
		raw = stage13_compute_geometric_tangent_raw(n_w, h0, phi_f, grad, theta);
		*path_id = 20.0;
	} else {
		raw = stage13_compute_briant_wall_ghost_raw(phi_f, h0, theta, path_id);
	}

	*raw_out = raw;
	*clamped_out = stage13_clamp_phase_value(raw, clamp_hit);
	return *clamped_out;
}

CudaDeviceFunction real_t stage13_phase_to_q(real_t phi)
{
	real_t range = PhaseField_h - PhaseField_l;
	if (fabs(range) < 1.0e-30) return 0.5;
	return (phi - PhaseField_l) / range;
}

CudaDeviceFunction real_t stage13_q_to_phase(real_t q)
{
	return PhaseField_l + q * (PhaseField_h - PhaseField_l);
}

CudaDeviceFunction int stage13_compact_write_requested()
{
	return (WallCompactStencilMode > 1.5 && WallCompactStencilWriteAllowedFlag > 0.5);
}

CudaDeviceFunction int stage13_compact_normal_mode_allows_write()
{
	// Only analytic signed-distance normals are implemented for the compact
	// stencil. Other advertised modes must not silently write.
	return (WallCompactStencilNormalMode > 0.5 && WallCompactStencilNormalMode < 1.5);
}

CudaDeviceFunction int stage13_csq_fallback_allows_write()
{
	return (fabs(WallCSQFallbackReason) < 0.5 ||
	        fabs(WallCSQFallbackReason - 4.0) < 0.5);
}

CudaDeviceFunction int stage13_compact_solution_can_write()
{
	real_t max_bounded_delta = WallCompactStencilMaxBoundedDelta;
	real_t max_applied_residual = WallCompactStencilAppliedResidualTol;
	if (max_bounded_delta < 0.0) max_bounded_delta = 0.0;
	if (max_applied_residual < 0.0) max_applied_residual = 0.0;
	int ready = (stage13_compact_write_requested()
	     && stage13_compact_normal_mode_allows_write()
	     && WallCSQValid > 0.5
	     && WallCSQMethodComplete > 0.5
	     && stage13_csq_fallback_allows_write()
	     && WallCSQBoundedDelta <= max_bounded_delta
	     && fabs(WallCSQAppliedResidual) <= max_applied_residual);
	WallCSQStrictWriteReady = ready ? 1.0 : 0.0;
	return ready;
}

CudaDeviceFunction real_t stage13_compact_solution_wall_ghost(
	real_t *raw_out, real_t *clamped_out, real_t *clamp_hit)
{
	real_t raw = stage13_q_to_phase(WallCSQQsRaw);
	real_t bounded = stage13_q_to_phase(WallCSQQsBounded);
	real_t phase_clamp_hit = 0.0;
	real_t out = stage13_clamp_phase_value(bounded, &phase_clamp_hit);
	*raw_out = raw;
	*clamped_out = out;
	*clamp_hit = phase_clamp_hit;
	if (WallCSQBoundedDelta > 1.0e-14) {
		*clamp_hit = 1.0;
	}
	return out;
}

CudaDeviceFunction int stage13_boundary_phase_is_valid(real_t pf) {
	if (!(pf == pf)) return 0;
	real_t lo = PhaseField_l;
	real_t hi = PhaseField_h;
	if (lo > hi) {
		real_t tmp = lo;
		lo = hi;
		hi = tmp;
	}
	real_t eps = PhaseValidityEps;
	if (eps < 0.0) eps = 0.0;
	return (pf >= lo - eps && pf <= hi + eps);
}

CudaDeviceFunction int stage13_compact_vertex_is_real_fluid(int ox, int oy, int oz, real_t pf)
{
	// This helper is used from calcWallPhase after Init_wallNorm has saved the
	// IsBoundary field. Do not move it into Init_wallNorm: neighbour
	// IsBoundary_dyn reads are stale while that field is being populated there.
	if (!stage13_boundary_phase_is_valid(pf)) return 0;
	if (IsBoundary_dyn(ox, oy, oz) > 0.5) return 0;
	return 1;
}

CudaDeviceFunction real_t stage13_bit3_value(int a, int b, int c)
{
	return (real_t)(a + 2*b + 4*c);
}

CudaDeviceFunction real_t stage13_bound_q(real_t q)
{
	real_t eps = WallCompactStencilBoundEps;
	if (eps < 0.0) eps = 0.0;
	if (q < -eps) return -eps;
	if (q > 1.0 + eps) return 1.0 + eps;
	return q;
}

CudaDeviceFunction real_t stage13_wall_csq_residual(
	real_t q_s, real_t q_f, real_t d_s, real_t d_f, real_t theta)
{
	real_t D = d_s + d_f;
	if (D <= 1.0e-30 || IntWidth <= 1.0e-30) return 1.0e30;
	real_t q_w = (d_s*q_f + d_f*q_s) / D;
	real_t lhs = (q_f - q_s) / D;
	real_t rhs = -(4.0/IntWidth) * q_w * (1.0 - q_w) * cos(theta);
	return lhs - rhs;
}

CudaDeviceFunction int stage13_floor_int(real_t x)
{
	int out = (int)floor(x);
	return out;
}

CudaDeviceFunction int stage13_ceil_int(real_t x)
{
	int out = (int)ceil(x);
	return out;
}

CudaDeviceFunction int stage13_max_int(int a, int b)
{
	return (a > b) ? a : b;
}

CudaDeviceFunction int stage13_min_int(int a, int b)
{
	return (a < b) ? a : b;
}

CudaDeviceFunction real_t stage13_min_real(real_t a, real_t b)
{
	return (a < b) ? a : b;
}

CudaDeviceFunction real_t stage13_max_real(real_t a, real_t b)
{
	return (a > b) ? a : b;
}

CudaDeviceFunction int stage13_coord_span_ok(
	int ax, int ay, int az,
	int bx, int by, int bz,
	int cx, int cy, int cz)
{
	int minx = stage13_min_int(ax, stage13_min_int(bx, cx));
	int maxx = stage13_max_int(ax, stage13_max_int(bx, cx));
	int miny = stage13_min_int(ay, stage13_min_int(by, cy));
	int maxy = stage13_max_int(ay, stage13_max_int(by, cy));
	int minz = stage13_min_int(az, stage13_min_int(bz, cz));
	int maxz = stage13_max_int(az, stage13_max_int(bz, cz));
	return ((maxx - minx) <= 1 && (maxy - miny) <= 1 && (maxz - minz) <= 1);
}

CudaDeviceFunction int stage13_barycentric_3d(
	real_t px, real_t py, real_t pz,
	real_t ax, real_t ay, real_t az,
	real_t bx, real_t by, real_t bz,
	real_t cx, real_t cy, real_t cz,
	real_t *w0, real_t *w1, real_t *w2)
{
	real_t v0x = bx - ax;
	real_t v0y = by - ay;
	real_t v0z = bz - az;
	real_t v1x = cx - ax;
	real_t v1y = cy - ay;
	real_t v1z = cz - az;
	real_t v2x = px - ax;
	real_t v2y = py - ay;
	real_t v2z = pz - az;
	real_t d00 = v0x*v0x + v0y*v0y + v0z*v0z;
	real_t d01 = v0x*v1x + v0y*v1y + v0z*v1z;
	real_t d11 = v1x*v1x + v1y*v1y + v1z*v1z;
	real_t d20 = v2x*v0x + v2y*v0y + v2z*v0z;
	real_t d21 = v2x*v1x + v2y*v1y + v2z*v1z;
	real_t denom = d00*d11 - d01*d01;
	if (fabs(denom) < 1.0e-30) return 0;
	real_t v = (d11*d20 - d01*d21) / denom;
	real_t w = (d00*d21 - d01*d20) / denom;
	real_t u = 1.0 - v - w;
	*w0 = u;
	*w1 = v;
	*w2 = w;
	return 1;
}

CudaDeviceFunction int stage13_barycentric_inside(real_t w0, real_t w1, real_t w2)
{
	real_t tol = 1.0e-10;
	return (w0 >= -tol && w1 >= -tol && w2 >= -tol &&
	        w0 <= 1.0 + tol && w1 <= 1.0 + tol && w2 <= 1.0 + tol);
}

CudaDeviceFunction int stage13_try_compact_triangle(
	int ax, int ay, int az,
	int bx, int by, int bz,
	int cx, int cy, int cz,
	int sx, int sy, int sz,
	real_t fx, real_t fy, real_t fz,
	real_t *q_f, real_t *bary_min, real_t *bary_max)
{
	if (!stage13_coord_span_ok(ax, ay, az, bx, by, bz, cx, cy, cz)) return 0;
	WallCSQCandidateCount = WallCSQCandidateCount + 1.0;

	real_t pf_a = PhaseF_dyn(sx*ax, sy*ay, sz*az);
	real_t pf_b = PhaseF_dyn(sx*bx, sy*by, sz*bz);
	real_t pf_c = PhaseF_dyn(sx*cx, sy*cy, sz*cz);
	int a_geom_fluid = stage13_compact_vertex_is_geometric_fluid(sx*ax, sy*ay, sz*az);
	int b_geom_fluid = stage13_compact_vertex_is_geometric_fluid(sx*bx, sy*by, sz*bz);
	int c_geom_fluid = stage13_compact_vertex_is_geometric_fluid(sx*cx, sy*cy, sz*cz);
	int a_real_fluid = stage13_compact_vertex_is_real_fluid(sx*ax, sy*ay, sz*az, pf_a);
	int b_real_fluid = stage13_compact_vertex_is_real_fluid(sx*bx, sy*by, sz*bz, pf_b);
	int c_real_fluid = stage13_compact_vertex_is_real_fluid(sx*cx, sy*cy, sz*cz, pf_c);
	int a_fluid = a_geom_fluid && a_real_fluid;
	int b_fluid = b_geom_fluid && b_real_fluid;
	int c_fluid = c_geom_fluid && c_real_fluid;
	int a_clean = stage13_boundary_phase_is_valid(pf_a);
	int b_clean = stage13_boundary_phase_is_valid(pf_b);
	int c_clean = stage13_boundary_phase_is_valid(pf_c);
	WallCSQVertexMaskBits = stage13_bit3_value(a_fluid, b_fluid, c_fluid);
	WallCSQVertexRealFluidBits = stage13_bit3_value(a_real_fluid, b_real_fluid, c_real_fluid);
	WallCSQVertexPhaseCleanBits = stage13_bit3_value(a_clean, b_clean, c_clean);
	if (!a_fluid || !b_fluid || !c_fluid) {
		WallCSQRejectedSolidVertexCount = WallCSQRejectedSolidVertexCount + 1.0;
		return 0;
	}
	if (!a_clean || !b_clean || !c_clean) {
		WallCSQRejectedSentinelCount = WallCSQRejectedSentinelCount + 1.0;
		return 0;
	}
	real_t q_a = stage13_phase_to_q(pf_a);
	real_t q_b = stage13_phase_to_q(pf_b);
	real_t q_c = stage13_phase_to_q(pf_c);
	WallCSQVertexQMin = stage13_min_real(q_a, stage13_min_real(q_b, q_c));
	WallCSQVertexQMax = stage13_max_real(q_a, stage13_max_real(q_b, q_c));

	real_t w0 = 0.0;
	real_t w1 = 0.0;
	real_t w2 = 0.0;
	if (!stage13_barycentric_3d(
			fx, fy, fz,
			(real_t)ax, (real_t)ay, (real_t)az,
			(real_t)bx, (real_t)by, (real_t)bz,
			(real_t)cx, (real_t)cy, (real_t)cz,
			&w0, &w1, &w2)) {
		return 0;
	}
	if (!stage13_barycentric_inside(w0, w1, w2)) return 0;

	*bary_min = stage13_min_real(w0, stage13_min_real(w1, w2));
	*bary_max = stage13_max_real(w0, stage13_max_real(w1, w2));
	*q_f = w0*q_a + w1*q_b + w2*q_c;
	return 1;
}

CudaDeviceFunction void stage13_fill_compact_stencil_solution(
	real_t q_f, real_t d_s, real_t d_f, real_t theta, real_t method_complete)
{
	WallCSQDs = d_s;
	WallCSQDf = d_f;
	WallCSQQf = q_f;
	if (fabs(cos(theta)) < WallCompactStencilThetaEps) {
		WallCSQValid = 1.0;
		WallCSQQsRaw = q_f;
		WallCSQQsBounded = stage13_bound_q(q_f);
		WallCSQQw = q_f;
		WallCSQResidual = 0.0;
		WallCSQAppliedResidual = stage13_wall_csq_residual(WallCSQQsBounded, q_f, d_s, d_f, theta);
		WallCSQDiscriminant = 0.0;
		WallCSQRootChoice = 90.0;
		WallCSQBoundedDelta = fabs(WallCSQQsBounded - WallCSQQsRaw);
		WallCSQFallbackReason = 4.0;  // neutral branch
		WallCSQMethodComplete = method_complete;
		return;
	}
	real_t D = d_s + d_f;
	real_t K = -(4.0/IntWidth) * cos(theta);
	real_t C = d_s * q_f;
	real_t E = D - C;
	real_t a = K * d_f * d_f;
	real_t b = -D - K * d_f * (E - C);
	real_t c = D * q_f - K * C * E;
	real_t disc = b*b - 4.0*a*c;
	WallCSQDiscriminant = disc;
	real_t q_s = q_f;
	real_t root_choice = 0.0;
	if (disc < 0.0) {
		WallCSQFallbackReason = 5.0;  // no real root
		q_s = q_f;
		root_choice = -2.0;
	} else if (fabs(a) < 1.0e-30) {
		if (fabs(b) < 1.0e-30) {
			WallCSQFallbackReason = 6.0;  // degenerate equation
			q_s = q_f;
			root_choice = -3.0;
		} else {
			q_s = -c / b;
			root_choice = -1.0;
			WallCSQValid = 1.0;
		}
	} else {
		real_t sqrt_disc = sqrt(disc);
		real_t r1 = (-b - sqrt_disc) / (2.0*a);
		real_t r2 = (-b + sqrt_disc) / (2.0*a);
		real_t eps = WallCompactStencilBoundEps;
		if (eps < 0.0) eps = 0.0;
		bool r1_ok = (r1 >= -eps && r1 <= 1.0 + eps);
		bool r2_ok = (r2 >= -eps && r2 <= 1.0 + eps);
		if (r1_ok && r2_ok) {
			if (fabs(r1 - q_f) <= fabs(r2 - q_f)) {
				q_s = r1;
				root_choice = 1.0;
			} else {
				q_s = r2;
				root_choice = 2.0;
			}
			WallCSQValid = 1.0;
		} else if (r1_ok) {
			q_s = r1;
			root_choice = 1.0;
			WallCSQValid = 1.0;
		} else if (r2_ok) {
			q_s = r2;
			root_choice = 2.0;
			WallCSQValid = 1.0;
		} else {
			q_s = (fabs(r1 - q_f) <= fabs(r2 - q_f)) ? r1 : r2;
			root_choice = -4.0;
			WallCSQFallbackReason = 7.0;  // roots out of bounded range
		}
	}
	real_t q_s_bounded = stage13_bound_q(q_s);
	real_t q_w = (d_s*q_f + d_f*q_s) / D;
	WallCSQQsRaw = q_s;
	WallCSQQsBounded = q_s_bounded;
	WallCSQQw = q_w;
	WallCSQResidual = stage13_wall_csq_residual(q_s, q_f, d_s, d_f, theta);
	WallCSQAppliedResidual = stage13_wall_csq_residual(q_s_bounded, q_f, d_s, d_f, theta);
	WallCSQRootChoice = root_choice;
	WallCSQBoundedDelta = fabs(q_s_bounded - q_s);
	if (WallCSQValid > 0.5 && WallCSQFallbackReason == 0.0) {
		WallCSQFallbackReason = 0.0;
	}
	WallCSQMethodComplete = method_complete;
}

CudaDeviceFunction int stage13_find_compact_qf(
	vector_t n_w, real_t d_s, real_t *out_q_f, real_t *out_d_f)
{
	real_t nmag = sqrt(n_w.x*n_w.x + n_w.y*n_w.y + n_w.z*n_w.z);
	if (nmag < 1.0e-30) {
		WallCSQFallbackReason = 8.0;  // invalid normal
		return 0;
	}
	real_t nx = fabs(n_w.x) / nmag;
	real_t ny = fabs(n_w.y) / nmag;
	real_t nz = fabs(n_w.z) / nmag;
	int sx = (n_w.x < 0.0) ? -1 : 1;
	int sy = (n_w.y < 0.0) ? -1 : 1;
	int sz = (n_w.z < 0.0) ? -1 : 1;
	int max_l = (int)(WallCompactStencilMaxL + 0.5);
	if (max_l < 1) max_l = 1;
	if (max_l > 4) max_l = 4;

	real_t best_df = 1.0e30;
	real_t best_qf = 0.5;
	real_t best_bary_min = 0.0;
	real_t best_bary_max = 0.0;
	real_t best_plane = 0.0;
	real_t best_l = 0.0;
	real_t found = 0.0;
	real_t clean_seen = 0.0;

	for (int plane = 1; plane <= 7; ++plane) {
		int cx = (plane == 1 || plane == 4 || plane == 6 || plane == 7) ? 1 : 0;
		int cy = (plane == 2 || plane == 4 || plane == 5 || plane == 7) ? 1 : 0;
		int cz = (plane == 3 || plane == 5 || plane == 6 || plane == 7) ? 1 : 0;
		real_t denom = cx*nx + cy*ny + cz*nz;
		if (denom < 1.0e-14) continue;
		for (int L = 1; L <= max_l; ++L) {
			real_t t = ((real_t)L) / denom;
			if (t <= d_s + 1.0e-9) continue;
			real_t fx = nx*t;
			real_t fy = ny*t;
			real_t fz = nz*t;
			int x0 = stage13_max_int(0, stage13_floor_int(fx) - 1);
			int y0 = stage13_max_int(0, stage13_floor_int(fy) - 1);
			int z0 = stage13_max_int(0, stage13_floor_int(fz) - 1);
			int x1 = stage13_max_int(x0, stage13_ceil_int(fx) + 1);
			int y1 = stage13_max_int(y0, stage13_ceil_int(fy) + 1);
			int z1 = stage13_max_int(z0, stage13_ceil_int(fz) + 1);
			int nodes[64][3];
			int node_count = 0;
			for (int ix = x0; ix <= x1; ++ix) {
				for (int iy = y0; iy <= y1; ++iy) {
					for (int iz = z0; iz <= z1; ++iz) {
						if (cx*ix + cy*iy + cz*iz != L) continue;
						if (node_count < 64) {
							nodes[node_count][0] = ix;
							nodes[node_count][1] = iy;
							nodes[node_count][2] = iz;
							node_count++;
						}
					}
				}
			}
			for (int ia = 0; ia < node_count; ++ia) {
				for (int ib = ia + 1; ib < node_count; ++ib) {
					for (int ic = ib + 1; ic < node_count; ++ic) {
						real_t q_f = 0.5;
						real_t bary_min = 0.0;
						real_t bary_max = 0.0;
						int tri_ok = stage13_try_compact_triangle(
							nodes[ia][0], nodes[ia][1], nodes[ia][2],
							nodes[ib][0], nodes[ib][1], nodes[ib][2],
							nodes[ic][0], nodes[ic][1], nodes[ic][2],
							sx, sy, sz, fx, fy, fz,
							&q_f, &bary_min, &bary_max);
						if (!tri_ok) continue;
						clean_seen = 1.0;
						WallCSQTriangleInside = 1.0;
						real_t d_f = t - d_s;
						if (d_f <= 1.0e-9) continue;
						if (d_f < best_df) {
							best_df = d_f;
							best_qf = q_f;
							best_bary_min = bary_min;
							best_bary_max = bary_max;
							best_plane = (real_t)plane;
							best_l = (real_t)L;
							found = 1.0;
						}
					}
				}
			}
		}
	}

	if (found > 0.5) {
		*out_q_f = best_qf;
		*out_d_f = best_df;
		WallCSQFluidVertexCount = 3.0;
		WallCSQPlaneId = best_plane;
		WallCSQStencilCase = 100.0 + best_plane;
		WallCSQStencilL = best_l;
		WallCSQBaryMin = best_bary_min;
		WallCSQBaryMax = best_bary_max;
		WallCSQAppliedWeight = 1.0;
		return 1;
	}
	if (WallCSQCandidateCount < 0.5) {
		WallCSQFallbackReason = 8.0;  // no candidate triangle generated
	} else if (clean_seen < 0.5) {
		WallCSQFallbackReason = 9.0;  // no clean all-fluid triangle
	} else {
		WallCSQFallbackReason = 10.0; // no accepted positive-distance triangle
	}
	return 0;
}

CudaDeviceFunction void stage13_reset_wall_csq()
{
	WallCSQMode = 0.0;
	WallCSQNormalMode = 0.0;
	WallCSQValid = 0.0;
	WallCSQThetaDeg = 0.0;
	WallCSQNormalX = 0.0;
	WallCSQNormalY = 0.0;
	WallCSQNormalZ = 0.0;
	WallCSQDs = 0.0;
	WallCSQDf = 0.0;
	WallCSQQf = 0.0;
	WallCSQQsRaw = 0.0;
	WallCSQQsBounded = 0.0;
	WallCSQQw = 0.0;
	WallCSQResidual = 0.0;
	WallCSQAppliedResidual = 0.0;
	WallCSQDiscriminant = 0.0;
	WallCSQRootChoice = 0.0;
	WallCSQStencilCase = 0.0;
	WallCSQStencilL = 0.0;
	WallCSQFallbackReason = 0.0;
	WallCSQBoundedDelta = 0.0;
	WallCSQAppliedWeight = 0.0;
	WallCSQWriteAllowedFlag = WallCompactStencilWriteAllowedFlag;
	WallCSQCandidateCount = 0.0;
	WallCSQFluidVertexCount = 0.0;
	WallCSQTriangleInside = 0.0;
	WallCSQPlaneId = 0.0;
	WallCSQBaryMin = 0.0;
	WallCSQBaryMax = 0.0;
	WallCSQMethodComplete = 0.0;
	WallCSQVertexMaskBits = 0.0;
	WallCSQVertexRealFluidBits = 0.0;
	WallCSQVertexPhaseCleanBits = 0.0;
	WallCSQVertexQMin = 0.0;
	WallCSQVertexQMax = 0.0;
	WallCSQRejectedSolidVertexCount = 0.0;
	WallCSQRejectedSentinelCount = 0.0;
	WallCSQStrictWriteReady = 0.0;
}

CudaDeviceFunction void stage13_keep_wall_csq()
{
	WallCSQMode = WallCSQMode(0,0,0);
	WallCSQNormalMode = WallCSQNormalMode(0,0,0);
	WallCSQValid = WallCSQValid(0,0,0);
	WallCSQThetaDeg = WallCSQThetaDeg(0,0,0);
	WallCSQNormalX = WallCSQNormalX(0,0,0);
	WallCSQNormalY = WallCSQNormalY(0,0,0);
	WallCSQNormalZ = WallCSQNormalZ(0,0,0);
	WallCSQDs = WallCSQDs(0,0,0);
	WallCSQDf = WallCSQDf(0,0,0);
	WallCSQQf = WallCSQQf(0,0,0);
	WallCSQQsRaw = WallCSQQsRaw(0,0,0);
	WallCSQQsBounded = WallCSQQsBounded(0,0,0);
	WallCSQQw = WallCSQQw(0,0,0);
	WallCSQResidual = WallCSQResidual(0,0,0);
	WallCSQAppliedResidual = WallCSQAppliedResidual(0,0,0);
	WallCSQDiscriminant = WallCSQDiscriminant(0,0,0);
	WallCSQRootChoice = WallCSQRootChoice(0,0,0);
	WallCSQStencilCase = WallCSQStencilCase(0,0,0);
	WallCSQStencilL = WallCSQStencilL(0,0,0);
	WallCSQFallbackReason = WallCSQFallbackReason(0,0,0);
	WallCSQBoundedDelta = WallCSQBoundedDelta(0,0,0);
	WallCSQAppliedWeight = WallCSQAppliedWeight(0,0,0);
	WallCSQWriteAllowedFlag = WallCSQWriteAllowedFlag(0,0,0);
	WallCSQCandidateCount = WallCSQCandidateCount(0,0,0);
	WallCSQFluidVertexCount = WallCSQFluidVertexCount(0,0,0);
	WallCSQTriangleInside = WallCSQTriangleInside(0,0,0);
	WallCSQPlaneId = WallCSQPlaneId(0,0,0);
	WallCSQBaryMin = WallCSQBaryMin(0,0,0);
	WallCSQBaryMax = WallCSQBaryMax(0,0,0);
	WallCSQMethodComplete = WallCSQMethodComplete(0,0,0);
	WallCSQVertexMaskBits = WallCSQVertexMaskBits(0,0,0);
	WallCSQVertexRealFluidBits = WallCSQVertexRealFluidBits(0,0,0);
	WallCSQVertexPhaseCleanBits = WallCSQVertexPhaseCleanBits(0,0,0);
	WallCSQVertexQMin = WallCSQVertexQMin(0,0,0);
	WallCSQVertexQMax = WallCSQVertexQMax(0,0,0);
	WallCSQRejectedSolidVertexCount = WallCSQRejectedSolidVertexCount(0,0,0);
	WallCSQRejectedSentinelCount = WallCSQRejectedSentinelCount(0,0,0);
	WallCSQStrictWriteReady = WallCSQStrictWriteReady(0,0,0);
}

CudaDeviceFunction void stage13_compute_compact_stencil_solution(
	vector_t n_w, real_t d_to_surface, real_t phi_f, real_t theta)
{
	stage13_reset_wall_csq();
	WallCSQMode = WallCompactStencilMode;
	WallCSQNormalMode = WallCompactStencilNormalMode;
	WallCSQThetaDeg = theta * 180.0 / PI;
	WallCSQNormalX = n_w.x;
	WallCSQNormalY = n_w.y;
	WallCSQNormalZ = n_w.z;
	WallCSQWriteAllowedFlag = WallCompactStencilWriteAllowedFlag;
	if (WallCompactStencilMode < 0.5) {
		WallCSQFallbackReason = 1.0;  // mode off
		return;
	}
	if (!stage13_compact_normal_mode_allows_write()) {
		WallCSQFallbackReason = 11.0;  // unsupported normal mode
		return;
	}
	real_t range = PhaseField_h - PhaseField_l;
	if (fabs(range) < 1.0e-30 || IntWidth <= 1.0e-30) {
		WallCSQFallbackReason = 2.0;  // invalid normalization or interface width
		return;
	}
	int first_probe_valid = stage13_boundary_phase_is_valid(phi_f);
	if (!first_probe_valid) {
		WallCSQFallbackReason = 3.0;  // no valid first fluid probe
	}
	real_t d_s = d_to_surface;
	if (d_s < 0.0) d_s = -d_s;
	if (d_s < 0.0) d_s = 0.0;

	real_t q_f = 0.5;
	real_t d_f = 0.0;
	if (stage13_find_compact_qf(n_w, d_s, &q_f, &d_f)) {
		WallCSQFallbackReason = 0.0;
		stage13_fill_compact_stencil_solution(q_f, d_s, d_f, theta, 1.0);
	} else {
		real_t fallback_reason = WallCSQFallbackReason;
		if (!first_probe_valid) {
			WallCSQFallbackReason = fallback_reason;
			return;
		}
		real_t q_probe = stage13_phase_to_q(phi_f);
		real_t d_probe = 1.0 - d_s;
		if (d_probe <= 1.0e-6) d_probe = 1.0;
		WallCSQStencilCase = 1.0;  // incomplete first-ring normal probe fallback
		WallCSQStencilL = 1.0;
		WallCSQFluidVertexCount = 1.0;
		WallCSQTriangleInside = 0.0;
		WallCSQPlaneId = 0.0;
		WallCSQBaryMin = 1.0;
		WallCSQBaryMax = 1.0;
		stage13_fill_compact_stencil_solution(q_probe, d_s, d_probe, theta, 0.0);
		WallCSQFallbackReason = fallback_reason;
	}
}

// Public accessor: the analytic wall normal at this node (zero if not analytic).
CudaDeviceFunction vector_t getAnalyticWallNormal() {
	if (AnalyticFlag(0,0,0) < 0.5) {
		vector_t zero = {0.0, 0.0, 0.0};
		return zero;
	}
	real_t h;
	return stage9_analytic_wall_normal_and_distance(&h);
}
CudaDeviceFunction real_t getWallH() {
	return WallH(0,0,0);
}
CudaDeviceFunction real_t getWallGhost() {
	return WallGhost(0,0,0);
}
CudaDeviceFunction real_t getWallGhostRaw() {
	return WallGhostRaw(0,0,0);
}
CudaDeviceFunction real_t getWallGhostClamped() {
	return WallGhostClamped(0,0,0);
}
CudaDeviceFunction real_t getWallGhostClampHit() {
	return WallGhostClampHit(0,0,0);
}
CudaDeviceFunction real_t getWettingPathId() {
	return WettingPathId(0,0,0);
}
CudaDeviceFunction real_t getLocalRadAngle() {
	return LocalRadAngle(0,0,0);
}
CudaDeviceFunction real_t getAnalyticFlag() {
	return AnalyticFlag(0,0,0);
}
CudaDeviceFunction real_t getWallCSQMode() { return WallCSQMode(0,0,0); }
CudaDeviceFunction real_t getWallCSQNormalMode() { return WallCSQNormalMode(0,0,0); }
CudaDeviceFunction real_t getWallCSQValid() { return WallCSQValid(0,0,0); }
CudaDeviceFunction real_t getWallCSQThetaDeg() { return WallCSQThetaDeg(0,0,0); }
CudaDeviceFunction real_t getWallCSQNormalX() { return WallCSQNormalX(0,0,0); }
CudaDeviceFunction real_t getWallCSQNormalY() { return WallCSQNormalY(0,0,0); }
CudaDeviceFunction real_t getWallCSQNormalZ() { return WallCSQNormalZ(0,0,0); }
CudaDeviceFunction real_t getWallCSQDs() { return WallCSQDs(0,0,0); }
CudaDeviceFunction real_t getWallCSQDf() { return WallCSQDf(0,0,0); }
CudaDeviceFunction real_t getWallCSQQf() { return WallCSQQf(0,0,0); }
CudaDeviceFunction real_t getWallCSQQsRaw() { return WallCSQQsRaw(0,0,0); }
CudaDeviceFunction real_t getWallCSQQsBounded() { return WallCSQQsBounded(0,0,0); }
CudaDeviceFunction real_t getWallCSQQw() { return WallCSQQw(0,0,0); }
CudaDeviceFunction real_t getWallCSQResidual() { return WallCSQResidual(0,0,0); }
CudaDeviceFunction real_t getWallCSQAppliedResidual() { return WallCSQAppliedResidual(0,0,0); }
CudaDeviceFunction real_t getWallCSQDiscriminant() { return WallCSQDiscriminant(0,0,0); }
CudaDeviceFunction real_t getWallCSQRootChoice() { return WallCSQRootChoice(0,0,0); }
CudaDeviceFunction real_t getWallCSQStencilCase() { return WallCSQStencilCase(0,0,0); }
CudaDeviceFunction real_t getWallCSQStencilL() { return WallCSQStencilL(0,0,0); }
CudaDeviceFunction real_t getWallCSQFallbackReason() { return WallCSQFallbackReason(0,0,0); }
CudaDeviceFunction real_t getWallCSQBoundedDelta() { return WallCSQBoundedDelta(0,0,0); }
CudaDeviceFunction real_t getWallCSQAppliedWeight() { return WallCSQAppliedWeight(0,0,0); }
CudaDeviceFunction real_t getWallCSQWriteAllowedFlag() { return WallCSQWriteAllowedFlag(0,0,0); }
CudaDeviceFunction real_t getWallCSQCandidateCount() { return WallCSQCandidateCount(0,0,0); }
CudaDeviceFunction real_t getWallCSQFluidVertexCount() { return WallCSQFluidVertexCount(0,0,0); }
CudaDeviceFunction real_t getWallCSQTriangleInside() { return WallCSQTriangleInside(0,0,0); }
CudaDeviceFunction real_t getWallCSQPlaneId() { return WallCSQPlaneId(0,0,0); }
CudaDeviceFunction real_t getWallCSQBaryMin() { return WallCSQBaryMin(0,0,0); }
CudaDeviceFunction real_t getWallCSQBaryMax() { return WallCSQBaryMax(0,0,0); }
CudaDeviceFunction real_t getWallCSQMethodComplete() { return WallCSQMethodComplete(0,0,0); }
CudaDeviceFunction real_t getWallCSQVertexMaskBits() { return WallCSQVertexMaskBits(0,0,0); }
CudaDeviceFunction real_t getWallCSQVertexRealFluidBits() { return WallCSQVertexRealFluidBits(0,0,0); }
CudaDeviceFunction real_t getWallCSQVertexPhaseCleanBits() { return WallCSQVertexPhaseCleanBits(0,0,0); }
CudaDeviceFunction real_t getWallCSQVertexQMin() { return WallCSQVertexQMin(0,0,0); }
CudaDeviceFunction real_t getWallCSQVertexQMax() { return WallCSQVertexQMax(0,0,0); }
CudaDeviceFunction real_t getWallCSQRejectedSolidVertexCount() { return WallCSQRejectedSolidVertexCount(0,0,0); }
CudaDeviceFunction real_t getWallCSQRejectedSentinelCount() { return WallCSQRejectedSentinelCount(0,0,0); }
CudaDeviceFunction real_t getWallCSQStrictWriteReady() { return WallCSQStrictWriteReady(0,0,0); }

#ifdef OPTIONS_staircaseimp

/* Array of lattice triangle coordinates, should not be used in the code apart
 * from initializaton since dynamic access to cuda constant memory is slow.
 *
 * Instead use triangle_id_to_vertex that generates coordinates of the vertices of the triangle on the fly.
 *
 * This is mostly left for the reference.
 */
CudaConstantMemory real_t const d3q27_faces_normals[6][3] = {{-1, 0, 0}, {1, 0, 0}, {0, -1, 0}, {0, 1, 0}, {0, 0, -1}, {0, 0, 1}};
CudaConstantMemory real_t const d3q27_faces_drop_indexes[6] = {0, 0, 1, 1, 2, 2};
CudaConstantMemory real_t const d3q27_triangles[6][8][3][3] = {\
  {{{1, 0, 0}, {1, 1, 1},  {1, 1, 0.0}},
  {{1, 0, 0}, {1, 1, 1},   {1, 0.0, 1}},
  {{1, 0, 0}, {1, -1, 1},  {1, 0.0, 1}},
  {{1, 0, 0}, {1, -1, 1},  {1, -1, 0.0}},
  {{1, 0, 0}, {1, -1, -1}, {1, -1, 0.0}},
  {{1, 0, 0}, {1, -1, -1}, {1, 0.0, -1}},
  {{1, 0, 0}, {1, 1, -1},  {1, 0.0, -1}},
  {{1, 0, 0}, {1, 1, -1},  {1, 1, 0.0}}},
 {{{-1, 0, 0}, {-1, 1, 1}, {-1, 1, 0.0}},
  {{-1, 0, 0}, {-1, 1, 1}, {-1, 0.0, 1}},
  {{-1, 0, 0}, {-1, -1, 1}, {-1, 0.0, 1}},
  {{-1, 0, 0}, {-1, -1, 1}, {-1, -1, 0.0}},
  {{-1, 0, 0}, {-1, -1, -1}, {-1, -1, 0.0}},
  {{-1, 0, 0}, {-1, -1, -1}, {-1, 0.0, -1}},
  {{-1, 0, 0}, {-1, 1, -1}, {-1, 0.0, -1}},
  {{-1, 0, 0}, {-1, 1, -1}, {-1, 1, 0.0}}},
 {{{0, 1, 0}, {1, 1, 1}, {1, 1, 0.0}},
  {{0, 1, 0}, {1, 1, 1}, {0.0, 1, 1}},
  {{0, 1, 0}, {-1, 1, 1}, {0.0, 1, 1}},
  {{0, 1, 0}, {-1, 1, 1}, {-1, 1, 0.0}},
  {{0, 1, 0}, {-1, 1, -1}, {-1, 1, 0.0}},
  {{0, 1, 0}, {-1, 1, -1}, {0.0, 1, -1}},
  {{0, 1, 0}, {1, 1, -1}, {0.0, 1, -1}},
  {{0, 1, 0}, {1, 1, -1}, {1, 1, 0.0}}},
 {{{0, -1, 0}, {1, -1, 1}, {1, -1, 0.0}},
  {{0, -1, 0}, {1, -1, 1}, {0.0, -1, 1}},
  {{0, -1, 0}, {-1, -1, 1}, {0.0, -1, 1}},
  {{0, -1, 0}, {-1, -1, 1}, {-1, -1, 0.0}},
  {{0, -1, 0}, {-1, -1, -1}, {-1, -1, 0.0}},
  {{0, -1, 0}, {-1, -1, -1}, {0.0, -1, -1}},
  {{0, -1, 0}, {1, -1, -1}, {0.0, -1, -1}},
  {{0, -1, 0}, {1, -1, -1}, {1, -1, 0.0}}},
 {{{0, 0, 1}, {1, 1, 1}, {1, 0.0, 1}},
  {{0, 0, 1}, {1, 1, 1}, {0.0, 1, 1}},
  {{0, 0, 1}, {-1, 1, 1}, {0.0, 1, 1}},
  {{0, 0, 1}, {-1, 1, 1}, {-1, 0.0, 1}},
  {{0, 0, 1}, {-1, -1, 1}, {-1, 0.0, 1}},
  {{0, 0, 1}, {-1, -1, 1}, {0.0, -1, 1}},
  {{0, 0, 1}, {1, -1, 1}, {0.0, -1, 1}},
  {{0, 0, 1}, {1, -1, 1}, {1, 0.0, 1}}},
 {{{0, 0, -1}, {1, 1, -1}, {1, 0.0, -1}},
  {{0, 0, -1}, {1, 1, -1}, {0.0, 1, -1}},
  {{0, 0, -1}, {-1, 1, -1}, {0.0, 1, -1}},
  {{0, 0, -1}, {-1, 1, -1}, {-1, 0.0, -1}},
  {{0, 0, -1}, {-1, -1, -1}, {-1, 0.0, -1}},
  {{0, 0, -1}, {-1, -1, -1}, {0.0, -1, -1}},
  {{0, 0, -1}, {1, -1, -1}, {0.0, -1, -1}},
  {{0, 0, -1}, {1, -1, -1}, {1, 0.0, -1}}}
};

CudaDeviceFunction vector_t getActualNormal() {
	vector_t actualNormal;
	actualNormal.x = nw_actual_x;
	actualNormal.y = nw_actual_y;
	actualNormal.z = nw_actual_z;
	return actualNormal;
}


/*
 * Reconstruct full coordinates of the  vertex of the triangle "triangle_id" from d3q27_triangles array
 * on face "face" and store in "coords"
 * Verification: https://github.com/TravisMitchell/3D_PF_benchmarkCases/blob/main/scripts/triangle_id_to_lattice_directions.py
 */
CudaDeviceFunction void triangle_id_to_vertex_1_coords(int face, int triangle_id, int *coords)
{
	// compute triangle on the fly to save memory
	int index_pos = face / 2;
	int is_positive = face % 2 == 0;

	int first_component = 0;
	int second_component = 0;



	first_component = 0;
	second_component = 0;



	coords[index_pos] = is_positive ? 1 : -1;
	coords[index_pos == 0] = first_component;
	coords[2 - (index_pos == 2)] = second_component;
}

/*
 * Reconstruct full coordinates of the  vertex of the triangle "triangle_id" from d3q27_triangles array
 * on face "face" and store in "coords"
 * Verification: https://github.com/TravisMitchell/3D_PF_benchmarkCases/blob/main/scripts/triangle_id_to_lattice_directions.py
 */
CudaDeviceFunction void triangle_id_to_vertex_2_coords(int face, int triangle_id, int *coords)
{
	// compute triangle on the fly to save memory
	int index_pos = face / 2;
	int is_positive = face % 2 == 0;

	int first_component = 0;
	int second_component = 0;



	second_component = 1 - 2*(triangle_id / 4 );
	first_component = 1 - 2*(((triangle_id + 2) % 8) / 4);



	coords[index_pos] = is_positive ? 1 : -1;
	coords[index_pos == 0] = first_component;
	coords[2 - (index_pos == 2)] = second_component;
}

/*
 * Reconstruct full coordinates of the  vertex of the triangle "triangle_id" from d3q27_triangles array
 * on face "face" and store in "coords"
 * Verification: https://github.com/TravisMitchell/3D_PF_benchmarkCases/blob/main/scripts/triangle_id_to_lattice_directions.py
 */
CudaDeviceFunction void triangle_id_to_vertex_3_coords(int face, int triangle_id, int *coords)
{
	// compute triangle on the fly to save memory
	int index_pos = face / 2;
	int is_positive = face % 2 == 0;

	int first_component = 0;
	int second_component = 0;



    second_component = triangle_id <= 3 ? int((triangle_id % 4 ) % 3 != 0): -int((triangle_id % 4 ) % 3 != 0);
    int val = (triangle_id + 2) % 8;
    first_component = val <= 3 ? int((val % 4 ) % 3 != 0): -int((val % 4 ) % 3 != 0);



	coords[index_pos] = is_positive ? 1 : -1;
	coords[index_pos == 0] = first_component;
	coords[2 - (index_pos == 2)] = second_component;
}


/*
 * Get reference id of the triangle which is intersected by the ray based
 * on the normal vector
 */
CudaDeviceFunction void calcIntersectionTriangleId(
												  real_t vec[],
												  int& triangle_index,
												  int& face_index,
												  real_t koeff[],
												  real_t intersection_point[],
												  int& triangle_index2,
												  real_t koeff2[]
												   ) {
	real_t plane_angle = -1;

	// find on which face the point lies
	for (int i = 0; i < 6; ++i) {

		// kind-off get the component of the vector that is the same as face normal
		real_t prod = d3q27_faces_normals[i][0]*vec[0] + d3q27_faces_normals[i][1] * vec[1] + d3q27_faces_normals[i][2] * vec[2];
		// rays in other direction
		if (prod > 0) continue;
		// avoid division by zero
		if (fabs(prod) < 1e-10) continue;
		// the same direction as the original vector
		// rescale the vector to the plane and get intersection point
		real_t point[3] = { - vec[0] / prod,  - vec[1] / prod, - vec[2] / prod };
		// got the intersection, get coordinate in 2d by removing common coordinate
		real_t drop_index = d3q27_faces_drop_indexes[i];
		// transform into 2d
		real_t point2d[2] = { point[drop_index == 1 ? 0 : (int(drop_index) + 1) % 3], point[drop_index == 1? 2 : (int(drop_index) + 2) % 3] };
		if (point2d[0] >= -1 && point2d[0] <= 1 && point2d[1] >= -1 && point2d[1] <= 1) {
			// it is inside the facet
			face_index = i;
			// determine in which triangle we lie, based on the plane angle
			// (similar to identity circle, going anti clockwise by 45 degrees
			// triangles)
			real_t x = point2d[0];
			real_t y = point2d[1];

			plane_angle = atan2(y, x) * 180.0 / PI;
			plane_angle = plane_angle < 0? plane_angle + 360 : plane_angle;

			// find matching triangle index
			for (int j = 0; j < 8; j++) {
				if (plane_angle >= j*45 && plane_angle < (j + 1) * 45) {
					triangle_index = j;
					break;
				}
			}
            // map triangle to 2D and get barycentric coordinates
            real_t triangle2d[3][2];
            for (int i = 0; i < 3; ++i) {
                // map triangle to 2D and (all points of it)
                triangle2d[i][0] = d3q27_triangles[face_index][triangle_index][i][drop_index == 1? 0 : (int(drop_index) + 1) % 3];
                triangle2d[i][1] = d3q27_triangles[face_index][triangle_index][i][drop_index == 1? 2 : (int(drop_index) + 2) % 3];
            }
			// get barycentric coordinates for the points inside triangle
            real_t detT = (triangle2d[1][1] - triangle2d[2][1]) * (triangle2d[0][0] - triangle2d[2][0]) + \
                           (triangle2d[2][0] - triangle2d[1][0]) * (triangle2d[0][1]- triangle2d[2][1]);

            real_t koeff_1 = (triangle2d[1][1] - triangle2d[2][1]) * (point2d[0] - triangle2d[2][0]) + \
                    (triangle2d[2][0] - triangle2d[1][0]) * (point2d[1]- triangle2d[2][1]);

            real_t koeff_2 = (triangle2d[2][1] - triangle2d[0][1]) * (point2d[0] - triangle2d[2][0]) + \
                     (triangle2d[0][0] - triangle2d[2][0]) * (point2d[1]- triangle2d[2][1]);

            koeff_1 /= detT;
            koeff_2 /= detT;

			// adjustment to prevent round-off errors
			if (koeff_1 < 1e-12) koeff_1 = 0.;
			if (koeff_2 < 1e-12) koeff_2 = 0.;

			intersection_point[0] = point[0];
			intersection_point[1] = point[1];
			intersection_point[2] = point[2];

            koeff[0] = koeff_1;
            koeff[1] = koeff_2;
            koeff[2] = 1 - koeff_1 - koeff_2;

			// ----------------------------------
			// TODO: Duplicate code as above to be refactored someday (but not today)
			// ----------------------------------

			// Original 2d point coodinate in the intersection with the second layer would be 2*point2d
			// We get the coordinate point in the new reference plane, relative to the second vertex of the first triangle (of the
			// form (-1, -1) (1, -1) - face corner vertexes), so that new poin2d coordinates relative to it should always be in the range (-1, 1),
			// as we want it to be to get the barycentric coordinates relative to the triangle as relative to the second vertex
			real_t point2_2d[2] = {2*point2d[0] - triangle2d[1][0], 2*point2d[1] - triangle2d[1][1] };
			x = point2_2d[0];
			y = point2_2d[1];

			real_t plane_angle2 = atan2(y, x) * 180.0 / PI;
			plane_angle2 = plane_angle2 < 0? plane_angle2 + 360 : plane_angle2;
			// find matching triangle index
			for (int j = 0; j < 8; j++) {
				if (plane_angle2 >= j*45 && plane_angle2 < (j + 1) * 45) {
					triangle_index2 = j;
					break;
				}
			}

            // map triangle to 2D and get barycentric coordinates
            real_t triangle2_2d[3][2];
            for (int i = 0; i < 3; ++i) {
                // map triangle2_ to 2D and (all point2_s of it)
                triangle2_2d[i][0] = d3q27_triangles[face_index][triangle_index2][i][drop_index == 1? 0 : (int(drop_index) + 1) % 3];
                triangle2_2d[i][1] = d3q27_triangles[face_index][triangle_index2][i][drop_index == 1? 2 : (int(drop_index) + 2) % 3];
            }
			// get barycentric coordinates for the point2_s inside triangle2_
            detT = (triangle2_2d[1][1] - triangle2_2d[2][1]) * (triangle2_2d[0][0] - triangle2_2d[2][0]) + \
                           (triangle2_2d[2][0] - triangle2_2d[1][0]) * (triangle2_2d[0][1]- triangle2_2d[2][1]);

            koeff_1 = (triangle2_2d[1][1] - triangle2_2d[2][1]) * (point2_2d[0] - triangle2_2d[2][0]) + \
                    (triangle2_2d[2][0] - triangle2_2d[1][0]) * (point2_2d[1]- triangle2_2d[2][1]);

            koeff_2 = (triangle2_2d[2][1] - triangle2_2d[0][1]) * (point2_2d[0] - triangle2_2d[2][0]) + \
                     (triangle2_2d[0][0] - triangle2_2d[2][0]) * (point2_2d[1]- triangle2_2d[2][1]);

            koeff_1 /= detT;
            koeff_2 /= detT;

			// adjustment to prevent round-off errors
			if (koeff_1 < 1e-12) koeff_1 = 0.;
			if (koeff_2 < 1e-12) koeff_2 = 0.;

            koeff2[0] = koeff_1;
            koeff2[1] = koeff_2;
            koeff2[2] = 1 - koeff_1 - koeff_2;

			break;
		}
	}
}

#endif

CudaDeviceFunction real_t getIsItBoundary() {
	return IsBoundary(0, 0, 0);
}

CudaDeviceFunction real_t stage13_select_boundary_phase(real_t pf, real_t is_boundary, real_t ghost, real_t center) {
	if (is_boundary > 0.5 && stage13_boundary_phase_is_valid(ghost)) return ghost;
	if (stage13_boundary_phase_is_valid(pf)) return pf;
	if (stage13_boundary_phase_is_valid(ghost)) return ghost;
	if (stage13_boundary_phase_is_valid(center)) return center;
	return 0.5*(PhaseField_l + PhaseField_h);
}

#define STAGE13_BOUNDARY_PHASE(dx,dy,dz) \
	stage13_select_boundary_phase(PhaseF(dx,dy,dz), IsBoundary(dx,dy,dz), WallGhost(dx,dy,dz), PhaseF(0,0,0))


#ifdef OPTIONS_geometric
CudaDeviceFunction vector_t getGradPhi() {
	vector_t gradPhi;
	gradPhi.x = gradPhiVal_x(0,0,0);
	gradPhi.y = gradPhiVal_y(0,0,0);
	gradPhi.z = gradPhiVal_z(0,0,0);
	return gradPhi;
}

CudaDeviceFunction void calcPhaseGrad(){
    vector_t gradPhi;
    gradPhi.y = 16.00 * (STAGE13_BOUNDARY_PHASE(0,1,0) - STAGE13_BOUNDARY_PHASE(0,-1,0)) + STAGE13_BOUNDARY_PHASE(1,1,1) + STAGE13_BOUNDARY_PHASE(-1,1,1) - STAGE13_BOUNDARY_PHASE(1,-1,1) - STAGE13_BOUNDARY_PHASE(-1,-1,1) + STAGE13_BOUNDARY_PHASE(1,1,-1)+ STAGE13_BOUNDARY_PHASE(-1,1,-1)- STAGE13_BOUNDARY_PHASE(1,-1,-1)- STAGE13_BOUNDARY_PHASE(-1,-1,-1) +  4.00 * (STAGE13_BOUNDARY_PHASE(1,1,0) + STAGE13_BOUNDARY_PHASE(-1,1,0) - STAGE13_BOUNDARY_PHASE(1,-1,0) - STAGE13_BOUNDARY_PHASE(-1,-1,0) +  STAGE13_BOUNDARY_PHASE(0,1,1) - STAGE13_BOUNDARY_PHASE(0,-1,1) + STAGE13_BOUNDARY_PHASE(0,1,-1) - STAGE13_BOUNDARY_PHASE(0,-1,-1));
gradPhi.x = 16.00 * (STAGE13_BOUNDARY_PHASE(1,0,0) - STAGE13_BOUNDARY_PHASE(-1,0,0)) + STAGE13_BOUNDARY_PHASE(1,1,1) - STAGE13_BOUNDARY_PHASE(-1,1,1) + STAGE13_BOUNDARY_PHASE(1,-1,1) - STAGE13_BOUNDARY_PHASE(-1,-1,1) + STAGE13_BOUNDARY_PHASE(1,1,-1)- STAGE13_BOUNDARY_PHASE(-1,1,-1) + STAGE13_BOUNDARY_PHASE(1,-1,-1) - STAGE13_BOUNDARY_PHASE(-1,-1,-1) +  4.00 * (STAGE13_BOUNDARY_PHASE(1,1,0) - STAGE13_BOUNDARY_PHASE(-1,1,0) + STAGE13_BOUNDARY_PHASE(1,-1,0) - STAGE13_BOUNDARY_PHASE(-1,-1,0) + STAGE13_BOUNDARY_PHASE(1,0,1) - STAGE13_BOUNDARY_PHASE(-1,0,1) + STAGE13_BOUNDARY_PHASE(1,0,-1) - STAGE13_BOUNDARY_PHASE(-1,0,-1));
gradPhi.z = 16.00 * (STAGE13_BOUNDARY_PHASE(0,0,1) - STAGE13_BOUNDARY_PHASE(0,0,-1)) + STAGE13_BOUNDARY_PHASE(1,1,1) + STAGE13_BOUNDARY_PHASE(-1,1,1) + STAGE13_BOUNDARY_PHASE(1,-1,1) + STAGE13_BOUNDARY_PHASE(-1,-1,1) - STAGE13_BOUNDARY_PHASE(1,1,-1)- STAGE13_BOUNDARY_PHASE(-1,1,-1)- STAGE13_BOUNDARY_PHASE(1,-1,-1)- STAGE13_BOUNDARY_PHASE(-1,-1,-1) +  4.00 * (STAGE13_BOUNDARY_PHASE(1,0,1) + STAGE13_BOUNDARY_PHASE(-1,0,1) - STAGE13_BOUNDARY_PHASE(1,0,-1) - STAGE13_BOUNDARY_PHASE(-1,0,-1) +  STAGE13_BOUNDARY_PHASE(0,1,1) + STAGE13_BOUNDARY_PHASE(0,-1,1) - STAGE13_BOUNDARY_PHASE(0,1,-1) - STAGE13_BOUNDARY_PHASE(0,-1,-1));
gradPhi.x /= 72.0;
gradPhi.y /= 72.0;
gradPhi.z /= 72.0;

    gradPhiVal_x = gradPhi.x;
    gradPhiVal_y = gradPhi.y;
    gradPhiVal_z = gradPhi.z;
	calcPhaseGradCloseToBoundary();
	// simply copy the values
	gradPhi_PhaseF = PhaseF(0,0,0);
}

/*
 * Initialize gradients at the first time step,
 * because isotropic gradients would not work, as the wall values have no
 * Phase field values just yet
 */
CudaDeviceFunction void calcPhaseGrad_init(){
    real_t h = 1.0;

	gradPhiVal_x = gradPhiVal_x(0, 0, 0);
	gradPhiVal_y = gradPhiVal_y(0, 0, 0);
	gradPhiVal_z = gradPhiVal_z(0, 0, 0);

	gradPhiVal_x = (STAGE13_BOUNDARY_PHASE(1, 0, 0) - STAGE13_BOUNDARY_PHASE(-1, 0, 0) )/ (2.0*h);
	gradPhiVal_y = (STAGE13_BOUNDARY_PHASE(0, 1, 0) - STAGE13_BOUNDARY_PHASE(0, -1, 0) )/ (2.0*h);
	gradPhiVal_z = (STAGE13_BOUNDARY_PHASE(0, 0, 1) - STAGE13_BOUNDARY_PHASE(0, 0, -1) )/ (2.0*h);

	calcPhaseGradCloseToBoundary();

	// probably accidentally touched the boundary, it is ok, this should be
	// fixed on the next iterations and should not cause problems

		if (fabs(gradPhiVal_x) > 20) {
			gradPhiVal_x = 0;
		}

		if (fabs(gradPhiVal_y) > 20) {
			gradPhiVal_y = 0;
		}

		if (fabs(gradPhiVal_z) > 20) {
			gradPhiVal_z = 0;
		}


    // simply copy the values
	gradPhi_PhaseF = PhaseF(0,0,0);
}

/*
 * Corrects gradient values on the next layer closer to the boundary, trying
 * its best to avoid taking the boundary values into the calculation of gradient
 * and using 2nd order finite difference instead when possible. Should be
 * used in conjunction of function calculating isotropic gradient everywhere else.
 */
CudaDeviceFunction void calcPhaseGradCloseToBoundary(){


    vector_t forcedFiniteDifference= {0, 0, 0};
    forcedFiniteDifference.y = IsBoundary(1,1,1) || IsBoundary(-1,1,1) || IsBoundary(1,-1,1) || IsBoundary(-1,-1,1) || IsBoundary(1,1,-1)|| IsBoundary(-1,1,-1)|| IsBoundary(1,-1,-1)|| IsBoundary(-1,-1,-1) ||    IsBoundary(1,1,0) || IsBoundary(-1,1,0) || IsBoundary(1,-1,0) || IsBoundary(-1,-1,0) ||  IsBoundary(0,1,1) || IsBoundary(0,-1,1) || IsBoundary(0,1,-1) || IsBoundary(0,-1,-1);
forcedFiniteDifference.x = IsBoundary(1,1,1) || IsBoundary(-1,1,1) || IsBoundary(1,-1,1) || IsBoundary(-1,-1,1) || IsBoundary(1,1,-1)|| IsBoundary(-1,1,-1) || IsBoundary(1,-1,-1) || IsBoundary(-1,-1,-1) ||  IsBoundary(1,1,0) || IsBoundary(-1,1,0) || IsBoundary(1,-1,0) || IsBoundary(-1,-1,0) || IsBoundary(1,0,1) || IsBoundary(-1,0,1) || IsBoundary(1,0,-1) || IsBoundary(-1,0,-1);
forcedFiniteDifference.z = IsBoundary(1,1,1) || IsBoundary(-1,1,1) || IsBoundary(1,-1,1) || IsBoundary(-1,-1,1) || IsBoundary(1,1,-1)|| IsBoundary(-1,1,-1)|| IsBoundary(1,-1,-1)|| IsBoundary(-1,-1,-1) ||     IsBoundary(1,0,1) || IsBoundary(-1,0,1) || IsBoundary(1,0,-1) || IsBoundary(-1,0,-1) ||  IsBoundary(0,1,1) || IsBoundary(0,-1,1) || IsBoundary(0,1,-1) || IsBoundary(0,-1,-1);



    real_t h = 1.0;

	bool canForceFiniteDifferenceUp;
	bool canForceFiniteDifferenceDown;
	bool canForceCentralDifference;
	bool set_gradPhi = false;



	set_gradPhi = false;

	// if we want to use finite differences, try to pick the best directions in which we
	// dont touch the boundary
	canForceFiniteDifferenceDown = forcedFiniteDifference.x && \
		(!IsBoundary(-1,0,0)) && (!IsBoundary(-2,0,0));

	canForceFiniteDifferenceUp = forcedFiniteDifference.x && \
		(!IsBoundary(1,0,0)) && (!IsBoundary(2,0,0));

	canForceCentralDifference = forcedFiniteDifference.x && \
		(!IsBoundary(-1,0,0)) && (!IsBoundary(1,0,0));

	if (canForceCentralDifference) {
		gradPhiVal_x = (STAGE13_BOUNDARY_PHASE(1,0,0) - \
							STAGE13_BOUNDARY_PHASE(-1,0,0))/(2.0*h);
		set_gradPhi = true;
	}


	if (IsBoundary(1,0,0) || (canForceFiniteDifferenceDown && !set_gradPhi) ) {
		if (IsBoundary(-1,0,0)
			|| IsBoundary(-2,0,0)) {
			// keep it as it is, calculated using the previously set gradient and the boundary
			// value
		} else {
			gradPhiVal_x = -(4*STAGE13_BOUNDARY_PHASE(-1,0,0) - \
							 STAGE13_BOUNDARY_PHASE(-2,0,0) - 3*STAGE13_BOUNDARY_PHASE(0, 0, 0))/(2.0*h);
			set_gradPhi = true;
		}
	}

	// check other direction and make sure that even points futher away are
	// handled properly, otherwise continue using isotropic gradient
	if (IsBoundary(-1,0,0) || (canForceFiniteDifferenceUp && !set_gradPhi)) {
		if (IsBoundary(1,0,0)
			|| IsBoundary(2,0,0)) {
			// keep it as it is, calculated using the previously set gradient and the boundary
			// value
		} else {
		gradPhiVal_x = (4*STAGE13_BOUNDARY_PHASE(1,0,0) -
						STAGE13_BOUNDARY_PHASE(2,0,0) - 3*STAGE13_BOUNDARY_PHASE(0, 0, 0))/(2.0*h);
		}
	}

	// end of the chunk for direction x


	set_gradPhi = false;

	// if we want to use finite differences, try to pick the best directions in which we
	// dont touch the boundary
	canForceFiniteDifferenceDown = forcedFiniteDifference.y && \
		(!IsBoundary(0,-1,0)) && (!IsBoundary(0,-2,0));

	canForceFiniteDifferenceUp = forcedFiniteDifference.y && \
		(!IsBoundary(0,1,0)) && (!IsBoundary(0,2,0));

	canForceCentralDifference = forcedFiniteDifference.y && \
		(!IsBoundary(0,-1,0)) && (!IsBoundary(0,1,0));

	if (canForceCentralDifference) {
		gradPhiVal_y = (STAGE13_BOUNDARY_PHASE(0,1,0) - \
							STAGE13_BOUNDARY_PHASE(0,-1,0))/(2.0*h);
		set_gradPhi = true;
	}


	if (IsBoundary(0,1,0) || (canForceFiniteDifferenceDown && !set_gradPhi) ) {
		if (IsBoundary(0,-1,0)
			|| IsBoundary(0,-2,0)) {
			// keep it as it is, calculated using the previously set gradient and the boundary
			// value
		} else {
			gradPhiVal_y = -(4*STAGE13_BOUNDARY_PHASE(0,-1,0) - \
							 STAGE13_BOUNDARY_PHASE(0,-2,0) - 3*STAGE13_BOUNDARY_PHASE(0, 0, 0))/(2.0*h);
			set_gradPhi = true;
		}
	}

	// check other direction and make sure that even points futher away are
	// handled properly, otherwise continue using isotropic gradient
	if (IsBoundary(0,-1,0) || (canForceFiniteDifferenceUp && !set_gradPhi)) {
		if (IsBoundary(0,1,0)
			|| IsBoundary(0,2,0)) {
			// keep it as it is, calculated using the previously set gradient and the boundary
			// value
		} else {
		gradPhiVal_y = (4*STAGE13_BOUNDARY_PHASE(0,1,0) -
						STAGE13_BOUNDARY_PHASE(0,2,0) - 3*STAGE13_BOUNDARY_PHASE(0, 0, 0))/(2.0*h);
		}
	}

	// end of the chunk for direction y


	set_gradPhi = false;

	// if we want to use finite differences, try to pick the best directions in which we
	// dont touch the boundary
	canForceFiniteDifferenceDown = forcedFiniteDifference.z && \
		(!IsBoundary(0,0,-1)) && (!IsBoundary(0,0,-2));

	canForceFiniteDifferenceUp = forcedFiniteDifference.z && \
		(!IsBoundary(0,0,1)) && (!IsBoundary(0,0,2));

	canForceCentralDifference = forcedFiniteDifference.z && \
		(!IsBoundary(0,0,-1)) && (!IsBoundary(0,0,1));

	if (canForceCentralDifference) {
		gradPhiVal_z = (STAGE13_BOUNDARY_PHASE(0,0,1) - \
							STAGE13_BOUNDARY_PHASE(0,0,-1))/(2.0*h);
		set_gradPhi = true;
	}


	if (IsBoundary(0,0,1) || (canForceFiniteDifferenceDown && !set_gradPhi) ) {
		if (IsBoundary(0,0,-1)
			|| IsBoundary(0,0,-2)) {
			// keep it as it is, calculated using the previously set gradient and the boundary
			// value
		} else {
			gradPhiVal_z = -(4*STAGE13_BOUNDARY_PHASE(0,0,-1) - \
							 STAGE13_BOUNDARY_PHASE(0,0,-2) - 3*STAGE13_BOUNDARY_PHASE(0, 0, 0))/(2.0*h);
			set_gradPhi = true;
		}
	}

	// check other direction and make sure that even points futher away are
	// handled properly, otherwise continue using isotropic gradient
	if (IsBoundary(0,0,-1) || (canForceFiniteDifferenceUp && !set_gradPhi)) {
		if (IsBoundary(0,0,1)
			|| IsBoundary(0,0,2)) {
			// keep it as it is, calculated using the previously set gradient and the boundary
			// value
		} else {
		gradPhiVal_z = (4*STAGE13_BOUNDARY_PHASE(0,0,1) -
						STAGE13_BOUNDARY_PHASE(0,0,2) - 3*STAGE13_BOUNDARY_PHASE(0, 0, 0))/(2.0*h);
		}
	}

	// end of the chunk for direction z


	if (IsBoundary(0,0,0)) {
		gradPhiVal_x = 0.;
		gradPhiVal_y = 0.;
		gradPhiVal_z = 0.;
	}
}

#endif


/* Correct PhaseField values on the boundary nodes
 * that were not previously set because the normal
 * was pointing into another boundary node with not
 * yet set value
 */
CudaDeviceFunction void calcWallPhase_correction() {
	PhaseF = PhaseF(0,0,0);
	WallGhost = WallGhost(0,0,0);
	WallGhostRaw = WallGhostRaw(0,0,0);
	WallGhostClamped = WallGhostClamped(0,0,0);
	WallGhostClampHit = WallGhostClampHit(0,0,0);
	WettingPathId = WettingPathId(0,0,0);
	LocalRadAngle = LocalRadAngle(0,0,0);
	stage13_keep_wall_csq();

	// Stage9 analytic path: the ghost was already written in calcWallPhase and
	// stored in WallGhost. Nothing to correct; analytic normals never point
	// into a solid, so the NORMAL_POINTING_INTO_SOLID_ON_NEXT_NODE case is
	// unreachable on analytic-flagged nodes.
	if (AnalyticFlag(0,0,0) > 0.5) {
		return;
	}

	if (IsSpecialBoundaryPoint == 1 ) {
		// take the phase field calculated already from the node in front.
		// Might as well calculate using the neighbors, e.g. averaging
		real_t corrected = PhaseF_dyn(nw_x, nw_y, nw_z);
		if (stage13_boundary_phase_is_valid(corrected)) {
			PhaseF = corrected;
		} else {
			PhaseF = 0.5*(PhaseField_l + PhaseField_h);
		}
		WallGhost = PhaseF;
		WallGhostRaw = PhaseF;
		WallGhostClamped = PhaseF;
		WallGhostClampHit = 0.0;
		WettingPathId = -12.0;
		LocalRadAngle = radAngle;
	}
}


/*
 * Calculate the phase field value for the boundary nodes
 */
CudaDeviceFunction void calcWallPhase(){
	PhaseF = PhaseF(0,0,0); //For fluid nodes.
	WallGhost = 0.0;
	WallH = 0.0;
	AnalyticFlag = 0.0;
	WallGhostRaw = 0.0;
	WallGhostClamped = 0.0;
	WallGhostClampHit = 0.0;
	WettingPathId = 0.0;
	LocalRadAngle = 0.0;
	stage13_reset_wall_csq();
	if ( IamWall || IamSolid ) {
		// ----------------------------------------------------------
		// Stage9 analytic-geometry wetting BC.
		//
		// The wall ghost is computed with the analytic geometry distance.
		// We reconstruct the analytic tag here instead of relying on
		// AnalyticFlag persistence across unrelated stages. The nw_* fields
		// intentionally remain integer lattice offsets for TCLB dynamic field
		// reads; exact analytic normals are recomputed for diagnostics.
		// surface-energy formula (the closed-form wall value for an
		// equilibrium tanh interface of width IntWidth). See the block
		// below for the exact expression.
		//
		// IMPORTANT (audit 2026-06-14): this Briant formula and the
		// tan(pi/2-theta) sharp-interface formula give IDENTICAL measured
		// contact angles (verified: 77.60 deg at theta=75 for both, and
		// the unmodified upstream binary also gives 77.60 deg). The
		// cot(theta)-scaled contact-angle error is therefore MODEL-
		// INTRINSIC (Fakhari-Mitchell interface discretization), NOT a
		// wall-BC formula artifact. This BC fixes the stage5-8 sign-flip
		// and special-points on curved walls, but does NOT by itself
		// reduce the contact-angle error below the model's O(W/R) floor.
		//
		// The result goes into WallGhost; PhaseF on this wall node is set
		// to the mirrored fluid value so gradient stencils never see -999.
		//
		// GUARD: take this branch only when the first and second fluid-side
		// probes along the analytic normal are real fluid nodes, not solid
		// sentinels.
		// ----------------------------------------------------------
		if (AnalyticWetting > 0.5) {
			real_t sd_a = 0.0;
			vector_t n_w_a = stage9_analytic_wall_normal_and_distance(&sd_a);
			real_t nmag_a = sqrt(n_w_a.x*n_w_a.x + n_w_a.y*n_w_a.y + n_w_a.z*n_w_a.z);
			real_t d_to_surface_a = (sd_a < 0.0) ? -sd_a : sd_a;
			if (nmag_a > 0.5 && d_to_surface_a < 1.5) {
				int probe_dx = stage9_probe_component(n_w_a.x);
				int probe_dy = stage9_probe_component(n_w_a.y);
				int probe_dz = stage9_probe_component(n_w_a.z);
				real_t h_a = d_to_surface_a + 0.5;
				real_t pf_f = PhaseF_dyn(probe_dx, probe_dy, probe_dz);
				real_t pf_ff = PhaseF_dyn(2*probe_dx, 2*probe_dy, 2*probe_dz);
				bool both_probes_fluid = stage13_boundary_phase_is_valid(pf_f) && stage13_boundary_phase_is_valid(pf_ff);
				bool compact_write = stage13_compact_write_requested() && (AnalyticSolidType < 1.5);
				if (h_a > 0.001 && (compact_write || both_probes_fluid)) {
					AnalyticFlag = 1.0;
					nw_x = probe_dx;
					nw_y = probe_dy;
					nw_z = probe_dz;
					WallH = h_a;
					LocalRadAngle = radAngle;
					if (compact_write) {
						stage13_compute_compact_stencil_solution(n_w_a, d_to_surface_a, pf_f, radAngle);
						if (stage13_compact_solution_can_write()) {
							WallGhost = stage13_compact_solution_wall_ghost(
								&WallGhostRaw, &WallGhostClamped, &WallGhostClampHit);
							WettingPathId = 30.0;
						} else {
							if (stage13_boundary_phase_is_valid(pf_f)) {
								WallGhost = pf_f;
							} else if (stage13_boundary_phase_is_valid(pf_ff)) {
								WallGhost = pf_ff;
							} else {
								WallGhost = 0.5*(PhaseField_l + PhaseField_h);
							}
							WallGhostRaw = WallGhost;
							WallGhostClamped = WallGhost;
							WallGhostClampHit = 0.0;
							WettingPathId = -30.0;
						}
						if (stage13_boundary_phase_is_valid(pf_f)) {
							PhaseF = pf_f;
						} else if (stage13_boundary_phase_is_valid(pf_ff)) {
							PhaseF = pf_ff;
						} else {
							PhaseF = 0.5*(PhaseField_l + PhaseField_h);
						}
						return;
					}
					vector_t grad_f = {0.0, 0.0, 0.0};
#ifdef OPTIONS_geometric
					grad_f.x = gradPhiVal_x_dyn(probe_dx, probe_dy, probe_dz);
					grad_f.y = gradPhiVal_y_dyn(probe_dx, probe_dy, probe_dz);
					grad_f.z = gradPhiVal_z_dyn(probe_dx, probe_dy, probe_dz);
#endif
					WallGhost = stage13_compute_analytic_wall_ghost(
						n_w_a, h_a, pf_f, grad_f, radAngle,
						&WallGhostRaw, &WallGhostClamped, &WallGhostClampHit, &WettingPathId);
					stage13_compute_compact_stencil_solution(n_w_a, d_to_surface_a, pf_f, radAngle);
					PhaseF = pf_f;
					return;
				}
				// Stage13D: this node lies on the declared analytic surface,
				// but the fluid-side probe is blocked by another wall/solid
				// node. That happens at flat-wall edge/corner overlaps with
				// the outer domain. Do not fall through to the legacy geometric
				// wetting path: it uses a lattice normal, may apply the target
				// angle to an edge node, and can write an unbounded wall phase
				// for acute angles. Keep the node finite and neutral for the
				// stencil while tagging the non-load-bearing overlap explicitly.
				AnalyticFlag = 0.5;
				nw_x = probe_dx;
				nw_y = probe_dy;
				nw_z = probe_dz;
				WallH = h_a;
				LocalRadAngle = radAngle;
				if (stage13_boundary_phase_is_valid(pf_f)) {
					PhaseF = pf_f;
				} else if (stage13_boundary_phase_is_valid(pf_ff)) {
					PhaseF = pf_ff;
				} else {
					PhaseF = 0.5*(PhaseField_l + PhaseField_h);
				}
				WallGhost = PhaseF;
				WallGhostRaw = PhaseF;
				WallGhostClamped = PhaseF;
				WallGhostClampHit = 0.0;
				WettingPathId = -20.0;
				stage13_compute_compact_stencil_solution(n_w_a, d_to_surface_a, PhaseF, radAngle);
				return;
			}
		}


		real_t h, pf_f;
		LocalRadAngle = radAngle;

		// This is needed, because otherwise geometric_staircaseimp performance will drop
		// (presumably because of the dynamic access that it has)


        pf_f = gradPhi_PhaseF_dyn(nw_x, nw_y, nw_z);
		if (!stage13_boundary_phase_is_valid(pf_f)) {
			pf_f = 0.5*(PhaseField_l + PhaseField_h);
		}

		h = 0.5 * sqrt(nw_x*nw_x + nw_y*nw_y + nw_z*nw_z);

        // handling special cases
		if (h < 0.001) {
			// If I am a wall/solid node and I am surrounded by solid nodes
			WettingPathId = -10.0;
			PhaseF = 1;
		} else if (fabs(radAngle - PI/2.0) < 1e-4) {
			// If I am not surrounded, but contact angle is pi/2 (90d)
			WettingPathId = 11.0;
			PhaseF = pf_f;
		} else if (IsSpecialBoundaryPoint == 1) {
			// Stage13 P0: never write the old huge sentinel here. It can pass
			// fluid-probe guards and poison near-wall finite-difference
			// stencils. Use the available fluid-side value when valid; otherwise
			// fall back to the phase midpoint until the correction stage.
			WettingPathId = -11.0;
			if (stage13_boundary_phase_is_valid(pf_f)) {
				PhaseF = pf_f;
			} else {
				PhaseF = 0.5*(PhaseField_l + PhaseField_h);
			}
		} else if  (IsSpecialBoundaryPoint == 2) {
			// Eventhough I am geometric boundary condition, still apply surface energy
			// here because otherwise we cant really apply anything else
			real_t path_id = 12.0;
			PhaseF = stage13_compute_briant_wall_ghost_raw(pf_f, h, radAngle, &path_id);
			WettingPathId = (path_id < 0.0) ? -12.0 : 12.0;
		} else {
			// normal calculation with picking correct form depending on the boundary condition

#ifdef OPTIONS_staircaseimp

			int face_index = int(triangle_index) / 8;
			int face_triangle_index = int(triangle_index) % 8;
			int vertex_coords[3] = {0,0,0};


				triangle_id_to_vertex_1_coords(face_index, face_triangle_index, vertex_coords);
				int v1_x = vertex_coords[0], v1_y = vertex_coords[1], v1_z = vertex_coords[2];

				triangle_id_to_vertex_2_coords(face_index, face_triangle_index, vertex_coords);
				int v2_x = vertex_coords[0], v2_y = vertex_coords[1], v2_z = vertex_coords[2];

				triangle_id_to_vertex_3_coords(face_index, face_triangle_index, vertex_coords);
				int v3_x = vertex_coords[0], v3_y = vertex_coords[1], v3_z = vertex_coords[2];






				real_t pf_v1 = gradPhi_PhaseF_dyn(v1_x, v1_y, v1_z);

				real_t pf_v2 = gradPhi_PhaseF_dyn(v2_x, v2_y, v2_z);

				real_t pf_v3 = gradPhi_PhaseF_dyn(v3_x, v3_y, v3_z);



			// dont do staircase improvement if any of the interpolating nodes are solid
			if (IsSpecialBoundaryPoint != 4) {
				real_t pf_interpolated = coeff_v1 * pf_v1 + coeff_v2 * pf_v2 + coeff_v3 * pf_v3;
				h = 0.5 * sqrt(nw_actual_x*nw_actual_x + nw_actual_y*nw_actual_y + nw_actual_z*nw_actual_z);
				pf_f = pf_interpolated;
			}
#endif

#ifndef OPTIONS_geometric
			// Case 1: Apply surface energy BC (with calculated pf_f with standard or staircase improvement)
			real_t path_id = 13.0;
			PhaseF = stage13_compute_briant_wall_ghost_raw(pf_f, h, radAngle, &path_id);
			WettingPathId = (path_id < 0.0) ? -13.0 : 13.0;
#else
	#ifdef OPTIONS_staircaseimp
		// Case 2: Apply geometric BC
		// Case 2.1: Apply geometric BC with staircase improvement
		vector_t solid_normal = {nw_actual_x, nw_actual_y, nw_actual_z};
		real_t der_x_1, der_y_1, der_z_1, der_x_2, der_y_2, der_z_2;

		// interpolate only if none of the interpolating points are solid
		if (IsSpecialBoundaryPoint != 4 && IsSpecialBoundaryPoint != 3 &&
			IsSpecialBoundaryPoint != 5)
			{

				der_x_1 =   coeff_v1*gradPhiVal_x_dyn(v1_x, v1_y, v1_z) + \
									coeff_v2*gradPhiVal_x_dyn(v2_x, v2_y, v2_z) +  \
									coeff_v3*gradPhiVal_x_dyn(v3_x, v3_y, v3_z);

				der_y_1 =   coeff_v1*gradPhiVal_y_dyn(v1_x, v1_y, v1_z) + \
									coeff_v2*gradPhiVal_y_dyn(v2_x, v2_y, v2_z) +  \
									coeff_v3*gradPhiVal_y_dyn(v3_x, v3_y, v3_z);

				der_z_1 =   coeff_v1*gradPhiVal_z_dyn(v1_x, v1_y, v1_z) + \
									coeff_v2*gradPhiVal_z_dyn(v2_x, v2_y, v2_z) +  \
									coeff_v3*gradPhiVal_z_dyn(v3_x, v3_y, v3_z);

		#ifndef OPTIONS_tprec
			// Case 2.1a: Apply geometric BC with staircase improvement and "larger" second triangle
			// Bigger triangle
			// Get gradient on the second node in the normal direction

				der_x_2 =   coeff_v1*gradPhiVal_x_dyn(2*v1_x, 2*v1_y, 2*v1_z) + \
									coeff_v2*gradPhiVal_x_dyn(2*v2_x, 2*v2_y, 2*v2_z) +  \
									coeff_v3*gradPhiVal_x_dyn(2*v3_x, 2*v3_y, 2*v3_z);


				der_y_2 =   coeff_v1*gradPhiVal_y_dyn(2*v1_x, 2*v1_y, 2*v1_z) + \
									coeff_v2*gradPhiVal_y_dyn(2*v2_x, 2*v2_y, 2*v2_z) +  \
									coeff_v3*gradPhiVal_y_dyn(2*v3_x, 2*v3_y, 2*v3_z);


				der_z_2 =   coeff_v1*gradPhiVal_z_dyn(2*v1_x, 2*v1_y, 2*v1_z) + \
									coeff_v2*gradPhiVal_z_dyn(2*v2_x, 2*v2_y, 2*v2_z) +  \
									coeff_v3*gradPhiVal_z_dyn(2*v3_x, 2*v3_y, 2*v3_z);


		#else
			// Case 2.1b: Apply geometric BC with staircase improvement and "precice/smaller" triangle triangle
			// get new triangle vertices in relation to one vertice of the previous triangle (plane index remains the same)
			int face_triangle_index2 = int(triangle_index2) % 8;


				triangle_id_to_vertex_1_coords(face_index, face_triangle_index2, vertex_coords);
				// get the coordinates of the vertex, with triangle indexing relateive to the second node of the first triangle,
				// because it is the closest
				int v2_1_x = vertex_coords[0], v2_1_y = vertex_coords[1], v2_1_z = vertex_coords[2];
				// transform from reference coordinates with respect to v2 to the proper coordinates with respet to boundary points
				int v2a_1_x = v2_1_x + v2_x, v2a_1_y = v2_1_y + v2_y, v2a_1_z = v2_1_z + v2_z;

				triangle_id_to_vertex_2_coords(face_index, face_triangle_index2, vertex_coords);
				// get the coordinates of the vertex, with triangle indexing relateive to the second node of the first triangle,
				// because it is the closest
				int v2_2_x = vertex_coords[0], v2_2_y = vertex_coords[1], v2_2_z = vertex_coords[2];
				// transform from reference coordinates with respect to v2 to the proper coordinates with respet to boundary points
				int v2a_2_x = v2_2_x + v2_x, v2a_2_y = v2_2_y + v2_y, v2a_2_z = v2_2_z + v2_z;

				triangle_id_to_vertex_3_coords(face_index, face_triangle_index2, vertex_coords);
				// get the coordinates of the vertex, with triangle indexing relateive to the second node of the first triangle,
				// because it is the closest
				int v2_3_x = vertex_coords[0], v2_3_y = vertex_coords[1], v2_3_z = vertex_coords[2];
				// transform from reference coordinates with respect to v2 to the proper coordinates with respet to boundary points
				int v2a_3_x = v2_3_x + v2_x, v2a_3_y = v2_3_y + v2_y, v2a_3_z = v2_3_z + v2_z;



			// Get gradient on the second node in the normal direction (triangle indexing relative to the second node of the first triangle because it is the closest)

				der_x_2 =   coeff2_v1*gradPhiVal_x_dyn(v2a_1_x, v2a_1_y, v2a_1_z) + \
									coeff2_v2*gradPhiVal_x_dyn(v2a_2_x, v2a_2_y, v2a_2_z) + \
									coeff2_v3*gradPhiVal_x_dyn(v2a_3_x, v2a_3_y, v2a_3_z);

				der_y_2 =   coeff2_v1*gradPhiVal_y_dyn(v2a_1_x, v2a_1_y, v2a_1_z) + \
									coeff2_v2*gradPhiVal_y_dyn(v2a_2_x, v2a_2_y, v2a_2_z) + \
									coeff2_v3*gradPhiVal_y_dyn(v2a_3_x, v2a_3_y, v2a_3_z);

				der_z_2 =   coeff2_v1*gradPhiVal_z_dyn(v2a_1_x, v2a_1_y, v2a_1_z) + \
									coeff2_v2*gradPhiVal_z_dyn(v2a_2_x, v2a_2_y, v2a_2_z) + \
									coeff2_v3*gradPhiVal_z_dyn(v2a_3_x, v2a_3_y, v2a_3_z);

				#endif // end tprec ifdef
			} else {
				// Revert to using "normals rounded to lattice directions" method,
				// which should not point to solid nodes hopefully
				// unfortunately the code is duplicated between #ifdef and if branches

					solid_normal.x = nw_x;
					// Get gradient on the first node in the normal direction
					der_x_1 = gradPhiVal_x_dyn(nw_x,    nw_y,   nw_z);
					// Get gradient on the second node in the normal direction
					der_x_2 = gradPhiVal_x_dyn(2*nw_x, 2*nw_y, 2*nw_z);

					solid_normal.y = nw_y;
					// Get gradient on the first node in the normal direction
					der_y_1 = gradPhiVal_y_dyn(nw_x,    nw_y,   nw_z);
					// Get gradient on the second node in the normal direction
					der_y_2 = gradPhiVal_y_dyn(2*nw_x, 2*nw_y, 2*nw_z);

					solid_normal.z = nw_z;
					// Get gradient on the first node in the normal direction
					der_z_1 = gradPhiVal_z_dyn(nw_x,    nw_y,   nw_z);
					// Get gradient on the second node in the normal direction
					der_z_2 = gradPhiVal_z_dyn(2*nw_x, 2*nw_y, 2*nw_z);

			}
			#else // no staircase improvement
			// Case 2.2: No staircase improvement
			vector_t solid_normal = {nw_x, nw_y, nw_z};

				// Get gradient on the first node in the normal direction
				real_t der_x_1 = gradPhiVal_x_dyn(nw_x,   nw_y,     nw_z);
				// Get gradient on the second node in the normal direction
				real_t der_x_2 = gradPhiVal_x_dyn(2*nw_x, 2*nw_y, 2*nw_z);

				// Get gradient on the first node in the normal direction
				real_t der_y_1 = gradPhiVal_y_dyn(nw_x,   nw_y,     nw_z);
				// Get gradient on the second node in the normal direction
				real_t der_y_2 = gradPhiVal_y_dyn(2*nw_x, 2*nw_y, 2*nw_z);

				// Get gradient on the first node in the normal direction
				real_t der_z_1 = gradPhiVal_z_dyn(nw_x,   nw_y,     nw_z);
				// Get gradient on the second node in the normal direction
				real_t der_z_2 = gradPhiVal_z_dyn(2*nw_x, 2*nw_y, 2*nw_z);

	#endif // end staircase improvement ifdef
		// Case 2 general: Continue applying geometric formulas
			real_t norm = solid_normal.x*solid_normal.x + solid_normal.y * solid_normal.y + solid_normal.z * solid_normal.z;
			real_t coeff;

			// project the gradients of two nodes in the normal direction on the boundary plane

					coeff = (der_x_1 * solid_normal.x + der_y_1* solid_normal.y + der_z_1* solid_normal.z)/norm;
					vector_t proj_grad_1 = {der_x_1 - coeff*solid_normal.x, der_y_1 - coeff*solid_normal.y, der_z_1 - coeff * solid_normal.z};

					coeff = (der_x_2 * solid_normal.x + der_y_2* solid_normal.y + der_z_2* solid_normal.z)/norm;
					vector_t proj_grad_2 = {der_x_2 - coeff*solid_normal.x, der_y_2 - coeff*solid_normal.y, der_z_2 - coeff * solid_normal.z};


			// extrapolate their components
			vector_t grad_tangent_v = { 1.5 * proj_grad_1.x - 0.5 * proj_grad_2.x,
										1.5 * proj_grad_1.y - 0.5 * proj_grad_2.y,
										1.5 * proj_grad_1.z - 0.5 * proj_grad_2.z};


			// compute the norm
			real_t grad_tangent = sqrt(grad_tangent_v.x * grad_tangent_v.x  + \
									 grad_tangent_v.y * grad_tangent_v.y + \
									 grad_tangent_v.z * grad_tangent_v.z);

			// apply geometric boundary condition
			WettingPathId = 14.0;
			PhaseF =  tan(PI/2.0 - radAngle) * grad_tangent * 2.0*h + pf_f;
#endif // end boundary condition pick
		}
		WallGhostRaw = PhaseF;
		WallGhost = stage13_clamp_phase_value(WallGhostRaw, &WallGhostClampHit);
		WallGhostClamped = WallGhost;
		PhaseF = WallGhost;
	}
}

CudaDeviceFunction real_t getSpecialBoundaryPoint() {
	return IsSpecialBoundaryPoint;
}


/*
 * Initialise and set: wall normals, get interpolating triangles and their coefficients,
 * find special nodes,
 */
CudaDeviceFunction void Init_wallNorm(){
	PhaseF = PhaseF(0,0,0);
    IsBoundary = IsBoundary(0,0,0);
	IsBoundary = 0.0;
	IsSpecialBoundaryPoint = 0.0;
#ifdef OPTIONS_staircaseimp
	coeff_v1 = 0;
	coeff_v2 = 0;
	coeff_v3 = 0;
#endif
	if ( IamWall || IamSolid ) {
        IsBoundary = 1.0;
		int i,j,k;
		real_t tmp = 0.0;
		for (i=-1;i<2;i++){for (j=-1;j<2;j++){for (k=-1;k<2;k++){
			tmp += PhaseF_dyn(i,j,k);
		}}}

		if ( abs(tmp) > 26000){
			// I am surrounded by all solid nodes (sum(pf) = 27*-999 = -26973 if surrounded):
			nw_x = 0.0; nw_y = 0.0; nw_z = 0.0;
#ifdef OPTIONS_staircaseimp
			nw_actual_x = 0.0;
			nw_actual_y = 0.0;
			nw_actual_z = 0.0;
#endif
		} else {
			// no I am not surrounded, so calc normal:
			int solidFlag[27];
			int maxi = 0;
			real_t myNorm[3] = {0.0,0.0,0.0};
			real_t maxn=0.0, dot;

			// Calculate the normal direction based converting
			// negative PhaseF into actual solid flags
			solidFlag[0] = PhaseF(0,0,0)/-998;
solidFlag[1] = PhaseF(1,0,0)/-998;
solidFlag[2] = PhaseF(-1,0,0)/-998;
solidFlag[3] = PhaseF(0,1,0)/-998;
solidFlag[4] = PhaseF(0,-1,0)/-998;
solidFlag[5] = PhaseF(0,0,1)/-998;
solidFlag[6] = PhaseF(0,0,-1)/-998;
solidFlag[7] = PhaseF(1,1,1)/-998;
solidFlag[8] = PhaseF(-1,1,1)/-998;
solidFlag[9] = PhaseF(1,-1,1)/-998;
solidFlag[10] = PhaseF(-1,-1,1)/-998;
solidFlag[11] = PhaseF(1,1,-1)/-998;
solidFlag[12] = PhaseF(-1,1,-1)/-998;
solidFlag[13] = PhaseF(1,-1,-1)/-998;
solidFlag[14] = PhaseF(-1,-1,-1)/-998;
solidFlag[15] = PhaseF(1,1,0)/-998;
solidFlag[16] = PhaseF(-1,1,0)/-998;
solidFlag[17] = PhaseF(1,-1,0)/-998;
solidFlag[18] = PhaseF(-1,-1,0)/-998;
solidFlag[19] = PhaseF(1,0,1)/-998;
solidFlag[20] = PhaseF(-1,0,1)/-998;
solidFlag[21] = PhaseF(1,0,-1)/-998;
solidFlag[22] = PhaseF(-1,0,-1)/-998;
solidFlag[23] = PhaseF(0,1,1)/-998;
solidFlag[24] = PhaseF(0,-1,1)/-998;
solidFlag[25] = PhaseF(0,1,-1)/-998;
solidFlag[26] = PhaseF(0,-1,-1)/-998;

			for (i=0;i<27;i++){
				myNorm[0] += wg[i] * solidFlag[i] * d3q27_ex[i];
				myNorm[1] += wg[i] * solidFlag[i] * d3q27_ey[i];
				myNorm[2] += wg[i] * solidFlag[i] * d3q27_ez[i];

			}
			myNorm[0] *= -1.0/3.0;myNorm[1] *= -1.0/3.0;myNorm[2] *= -1.0/3.0;
			tmp = myNorm[0]*myNorm[0] + myNorm[1]*myNorm[1] + myNorm[2]*myNorm[2];

			// Calculate the closest discrete direction for normal:
			for (i = 0; i<27; i++) {
				dot = (myNorm[0]*d3q27_ex[i] + myNorm[1]*d3q27_ey[i] + myNorm[2]*d3q27_ez[i]) /
					sqrt( tmp*(d3q27_ex[i]*d3q27_ex[i] + d3q27_ey[i]*d3q27_ey[i] +
						   d3q27_ez[i]*d3q27_ez[i]) + 1e-12);
				if (dot > maxn) {
					maxn = dot; maxi = i;
				}
			}
			if (maxi < 0) {
				// This should not happen ?
				nw_x = 0.0;nw_y = 0.0;nw_z = 0.0;
			} else {
				nw_x = d3q27_ex[maxi];
				nw_y = d3q27_ey[maxi];
				nw_z = d3q27_ez[maxi];

				// normal points into another solid node, save it for the later treatment
				// NOTE: Cant use IsBoundary here, because it is not yet necessary set for
				// the neighboring nodes
				if (PhaseF_dyn(nw_x, nw_y, nw_z) < -100) {
					IsSpecialBoundaryPoint = 1;
				}
			}

#ifdef OPTIONS_staircaseimp
			real_t truncated_normals[3] = {nw_x, nw_y, nw_z};
			real_t intersection_point[3];
			int face_index;
			real_t coeff[3];
			real_t coeff2[3];
			int t_index;
			int t_index2;

			calcIntersectionTriangleId(myNorm, t_index, face_index, coeff, intersection_point, t_index2, coeff2);

			// make sure normal vector is extended to the surface (to use it during interpolation)
			nw_actual_x = intersection_point[0];
			nw_actual_y = intersection_point[1];
			nw_actual_z = intersection_point[2];
			triangle_index = triangle_index(0,0,0);
			triangle_index = t_index + face_index*8;


            coeff_v1 = coeff[0];
            coeff_v2 = coeff[1];
            coeff_v3 = coeff[2];

	#ifdef OPTIONS_tprec
			triangle_index2 = triangle_index2(0,0,0);
			triangle_index2 = t_index2 + face_index*8;
            coeff2_v1 = coeff2[0];
            coeff2_v2 = coeff2[1];
            coeff2_v3 = coeff2[2];
	#endif
#endif

#ifdef OPTIONS_staircaseimp
		// Detect if any of the triangle vertices is a solid node and
		// if so, use the simple normal instead if possible
		int face_triangle_index = t_index;
		int vertex_coords[3] = {0,0,0};


			triangle_id_to_vertex_1_coords(face_index, face_triangle_index, vertex_coords);
			int v1_x = vertex_coords[0], v1_y = vertex_coords[1], v1_z = vertex_coords[2];
			real_t pf_v1 = PhaseF_dyn(v1_x, v1_y, v1_z);

			triangle_id_to_vertex_2_coords(face_index, face_triangle_index, vertex_coords);
			int v2_x = vertex_coords[0], v2_y = vertex_coords[1], v2_z = vertex_coords[2];
			real_t pf_v2 = PhaseF_dyn(v2_x, v2_y, v2_z);

			triangle_id_to_vertex_3_coords(face_index, face_triangle_index, vertex_coords);
			int v3_x = vertex_coords[0], v3_y = vertex_coords[1], v3_z = vertex_coords[2];
			real_t pf_v3 = PhaseF_dyn(v3_x, v3_y, v3_z);



		bool will_interpolate_from_the_boundary = pf_v3 < -100 || pf_v2 < -100 || pf_v1 < -100;

		// if normal vector points to the solid, continue marking this point as the special point
		// because this is definitely a vector vertices of which coincide with the one of triangle
		// vertices. Otherwise if I am trying to interpolate from the boundary, use the simple normal
		if (will_interpolate_from_the_boundary && IsSpecialBoundaryPoint != 1) {
			IsSpecialBoundaryPoint = 4;
		}

	#ifdef OPTIONS_geometric

		#ifdef OPTIONS_tprec
			int face_triangle_index2 = int(triangle_index2) % 8;

				triangle_id_to_vertex_1_coords(face_index, face_triangle_index2, vertex_coords);
				// get the coordinates of the vertex, with triangle indexing relateive to the second node of the first triangle,
				// because it is the closest
				int v2_1_x = vertex_coords[0], v2_1_y = vertex_coords[1], v2_1_z = vertex_coords[2];
				// transform from reference coordinates with respect to v2 to the proper coordinates with respet to boundary points
				int v2a_1_x = v2_1_x + v2_x, v2a_1_y = v2_1_y + v2_y, v2a_1_z = v2_1_z + v2_z;

				triangle_id_to_vertex_2_coords(face_index, face_triangle_index2, vertex_coords);
				// get the coordinates of the vertex, with triangle indexing relateive to the second node of the first triangle,
				// because it is the closest
				int v2_2_x = vertex_coords[0], v2_2_y = vertex_coords[1], v2_2_z = vertex_coords[2];
				// transform from reference coordinates with respect to v2 to the proper coordinates with respet to boundary points
				int v2a_2_x = v2_2_x + v2_x, v2a_2_y = v2_2_y + v2_y, v2a_2_z = v2_2_z + v2_z;

				triangle_id_to_vertex_3_coords(face_index, face_triangle_index2, vertex_coords);
				// get the coordinates of the vertex, with triangle indexing relateive to the second node of the first triangle,
				// because it is the closest
				int v2_3_x = vertex_coords[0], v2_3_y = vertex_coords[1], v2_3_z = vertex_coords[2];
				// transform from reference coordinates with respect to v2 to the proper coordinates with respet to boundary points
				int v2a_3_x = v2_3_x + v2_x, v2a_3_y = v2_3_y + v2_y, v2a_3_z = v2_3_z + v2_z;


			bool will_interpolate_further_from_the_boundary = PhaseF_dyn(v2a_1_x, v2a_1_y, v2a_1_z) < -100 || PhaseF_dyn(v2a_2_x, v2a_2_y, v2a_2_z) < -100 || PhaseF_dyn(v2a_3_x, v2a_3_y, v2a_3_z) < -100;
		#else
			bool will_interpolate_further_from_the_boundary = PhaseF_dyn(2*v1_x, 2*v1_y, 2*v1_z) < -100 || PhaseF_dyn(2*v2_x, 2*v2_y, 2*v2_z) < -100 || PhaseF_dyn(2*v3_x, 2*v3_y, 2*v3_z) < -100;

		#endif
		bool normal_pointing_into_solid_on_further_next_node = PhaseF_dyn(2*nw_x, 2*nw_y, 2*nw_z) < -100;

		// if the normal point poinst to a solid, it takes precedence, otherwise enter if condition
		if (will_interpolate_further_from_the_boundary && IsSpecialBoundaryPoint != 1) {
			// if next next next point is a solid, cant use geometric method
			if (normal_pointing_into_solid_on_further_next_node) {
				IsSpecialBoundaryPoint = 2;
			// else if one (but not one of the normal points) is solid,  can still use geometric method, but not interpolation
			} else {
				IsSpecialBoundaryPoint = will_interpolate_from_the_boundary ? 5  : 3;
			}
		}
	#endif

#else
        // when there is no staircase improvement and I am geometric
#ifdef OPTIONS_geometric
		// if the next-next node is solid (but next is not) we cant really compute anything with geometric method and have to switch to surface energy
		if (IsSpecialBoundaryPoint != 1 && PhaseF_dyn(2*nw_x, 2*nw_y, 2*nw_z) < -100) {
			IsSpecialBoundaryPoint = 2;
		}
#endif
#endif

		}
	} else {
	// I am a fluid node, I dont need no solid normal.
		nw_x = 0.0;
		nw_y = 0.0;
		nw_z = 0.0;
#ifdef OPTIONS_staircaseimp
		nw_actual_x = 0.0;
		nw_actual_y = 0.0;
		nw_actual_z = 0.0;
		coeff_v1 = 0.0;
		coeff_v2 = 0.0;
		coeff_v3 = 0.0;
		triangle_index = 0;
	#ifdef OPTIONS_tprec
		coeff2_v1 = 0.0;
		coeff2_v2 = 0.0;
		coeff2_v3 = 0.0;
		triangle_index2 = 0;
	#endif
#endif
	}

	// ------------------------------------------------------------------ //
	// Stage9 analytic-geometry normal injection.                          //
	// For every wall/solid node within one cell of the declared analytic   //
	// surface, replace the lattice-recovered normal with the exact analytic//
	// normal pointing INTO THE FLUID, store the analytic signed distance in//
	// WallH, and set AnalyticFlag=1 so calcWallPhase takes the analytic    //
	// branch. This eliminates NORMAL_POINTING_INTO_SOLID special points   //
	// (the analytic normal never points into the solid) and removes the    //
	// ~25 deg normal-quantisation error on curved walls.                  //
	// ------------------------------------------------------------------ //
	AnalyticFlag = 0.0;
	WallH = 0.0;
	WallGhost = 0.0;
	WallGhostRaw = 0.0;
	WallGhostClamped = 0.0;
	WallGhostClampHit = 0.0;
	WettingPathId = 0.0;
	LocalRadAngle = 0.0;
	if (AnalyticWetting > 0.5 && (IamWall || IamSolid)) {
		real_t sd = 0.0;
		vector_t n_w = stage9_analytic_wall_normal_and_distance(&sd);
		real_t nmag = sqrt(n_w.x*n_w.x + n_w.y*n_w.y + n_w.z*n_w.z);
		// Only tag this node as analytic if (a) the analytic geometry is
		// valid (unit normal) AND (b) this node is actually close to the
		// analytic surface (within ~1.5 lattice units). Without the
		// distance gate, EVERY wall node in the domain (including outer
		// domain walls far from the analytic surface) would be tagged with
		// the analytic normal, producing wrong normals and NaNs.
		if (nmag > 0.5) {
			real_t d_to_surface = (sd < 0.0) ? -sd : sd;
			if (d_to_surface < 1.5) {
				// The fluid-side probe along the analytic normal must be a
				// real fluid node. This excludes corner/edge wall nodes where
				// the analytic normal (correct for the analytic surface) would
				// point along another wall, which would corrupt the gradient
				// read. Corner nodes are left to the legacy lattice path.
				//
				// IMPORTANT: we cannot use IsBoundary_dyn here as the gate,
				// because during the Init action the IsBoundary field is being
				// populated by this very stage and neighbours read stale/zero
				// values. We gate on PhaseF_dyn instead: solid nodes carry
				// the -999 sentinel (set by PhaseInit), fluid nodes carry a
				// physical phase value. This is reliable during Init.
				int probe_dx = stage9_probe_component(n_w.x);
				int probe_dy = stage9_probe_component(n_w.y);
				int probe_dz = stage9_probe_component(n_w.z);
				real_t probe_pf = PhaseF_dyn(probe_dx, probe_dy, probe_dz);
				bool probe_is_fluid_node = stage13_boundary_phase_is_valid(probe_pf);
				if (probe_is_fluid_node) {
					// This wall node is genuinely on the analytic surface and
					// the fluid-side probe is a real fluid node. Keep nw_* as
					// integer offsets; dynamic field access is not continuous.
					AnalyticFlag = 1.0;
					nw_x = probe_dx;
					nw_y = probe_dy;
					nw_z = probe_dz;
					WallH = d_to_surface + 0.5;
					LocalRadAngle = radAngle;
				}
			}
		}
	}
}

//############//

//######UPDATE FUNCTIONS#######//
CudaDeviceFunction void updateBoundary(){
    switch (NodeType & NODE_BOUNDARY) {
		case NODE_Solid:
		case NODE_Wall:
			BounceBack();
			break;

        case NODE_NVelocity:
			NVelocity();
			break;
		case NODE_NPressure:
			NPressure();
			break;

        case NODE_EVelocity:
			EVelocity();
			break;
		case NODE_EPressure:
			EPressure();
			break;

        case NODE_SVelocity:
			SVelocity();
			break;
		case NODE_SPressure:
			SPressure();
			break;

        case NODE_WVelocity:
			WVelocity();
			break;
		case NODE_WPressure:
			WPressure();
			break;

        case NODE_FVelocity:
			FVelocity();
			break;
		case NODE_FPressure:
			FPressure();
			break;

        case NODE_BVelocity:
			BVelocity();
			break;
		case NODE_BPressure:
			BPressure();
			break;

		case NODE_MovingWall_N:
			MovingNWall();
			break;
		case NODE_MovingWall_S:
			MovingSWall();
			break;
		#ifdef OPTIONS_OutFlow
			case NODE_EConvect:
				EConvect();
				break;
			case NODE_WConvect:
				WConvect();
				break;
			case NODE_ENeumann:
				ENeumann();
				break;
			case NODE_WNeumann:
				WNeumann();
				break;
		#endif
	}
}

CudaDeviceFunction void updateMyGlobals(real_t pf){
	real_t tmpPF = 1 - pf;
	real_t rho = Density_l + ((pf) - PhaseField_l)*(Density_h - Density_l)/(PhaseField_h - PhaseField_l);
	real_t u2mag = (U*U+V*V+W*W);
	AddToTotalDensity( rho ); // Add globals of post-stream, pre-collide macroscopic globals.
	AddToKineticEnergy( rho * u2mag );

	if ( (pf) < 0.5 )
	{
	    AddToGasTotalVelocity( tmpPF*sqrt(u2mag));
	    AddToGasTotalVelocityX( tmpPF*U );
	    AddToGasTotalVelocityY( tmpPF*V );
	    AddToGasTotalVelocityZ( tmpPF*W );
	    AddToGasTotalPhase( tmpPF );
	    AddToXLocation( tmpPF*X );
	} else {
	    AddToLiqTotalVelocity( pf*sqrt(u2mag));
	    AddToLiqTotalVelocityX( U*pf );
	    AddToLiqTotalVelocityY( V*pf );
	    AddToLiqTotalVelocityZ( W*pf );
	    AddToLiqTotalPhase( pf );
	}

	if ((NodeType & NODE_ADDITIONALS) == NODE_flux_nodes) {
		AddToFluxNodeCount( 1 );
		AddToFluxX( U );
		AddToFluxY( V );
		AddToFluxZ( W );
	}
}

CudaDeviceFunction void updateTrackers(real_t C){
	real_t location;

	// track top of the interface in Y direction, only on actual nodes
	if ((NodeType & NODE_BGK) || (NodeType & NODE_MRT)) {
		if ( C < 0.5 && PhaseF(0, -1, 0) > 0.5) {
			location = Y - (C-0.5)/(C-PhaseF(0,-1,0));
			AddToInterfaceYTop(location);
		}
	}

	switch (NodeType & NODE_ADDITIONALS) {
		case NODE_Centerline:
		    if ( fabs(xyzTrack-1) < 1e-3 )
		    {  // track along X
                if (C < 0.5 && PhaseF(1,0,0) > 0.5)
                {
                    location = X + (C-0.5)/(C-PhaseF(1,0,0));
                    AddToInterfacePosition(location);
                    AddToVback(U);
                }
                if (C >0.5 && PhaseF(-1,0,0) < 0.5)
                {
                    AddToVfront(U);
                }
		    } else if ( fabs(xyzTrack-2) < 1e-3)
		    { // track along Y
                if (C < 0.5 && PhaseF(0,1,0) > 0.5)
                {
                    location = Y + (C-0.5)/(C-PhaseF(0,1,0));
                    AddToInterfacePosition(location);
                    AddToVback(V);
                }
                if (C >0.5 && PhaseF(0,-1,0) < 0.5)
                {
                    AddToVfront(V);
                }
		    } else if ( fabs(xyzTrack-3) < 1e-3)
		    { // track along Z
			if (C < 0.5 && PhaseF(0,0,1) > 0.5)
                {
                    location = Z + (C-0.5)/(C-PhaseF(0,0,1));
                    AddToInterfacePosition(location);
                    AddToVback(W);
                }
                if (C >0.5 && PhaseF(0,0,-1) < 0.5)
                {
                    AddToVfront(W);
                }
		    } else if ( fabs(xyzTrack-4) < 1e-3 )
		    {  // track reverse along X
                if (C < 0.5 && PhaseF(-1,0,0) > 0.5)
                {
                    location = X - (C-0.5)/(C-PhaseF(-1,0,0));
                    AddToInterfacePosition(location);
				    AddToVback(U);
			    }
            } else if ( fabs(xyzTrack-5) < 1e-3 )
		    {  // track reverse along Y (e.g. tracking north pole of the droplet
			   // as it is falling)
                if (C < 0.5 && PhaseF(0,-1,0) > 0.5)
                {
                    location = Y - (C-0.5)/(C-PhaseF(0,-1,0));
                    AddToInterfacePosition(location);
			    }
            }

		case NODE_Spiketrack:
			if (C < 0.5 && PhaseF(0,1,0) > 0.5)
			{
				location = Y + (C-0.5)/(C-PhaseF(0,1,0));
				AddToRTISpike(location);
			}
		case NODE_Saddletrack:
			if (C < 0.5 && PhaseF(0,1,0) > 0.5)
			{
				location = Y + (C-0.5)/(C-PhaseF(0,1,0));
				AddToRTISaddle(location);
			}
		case NODE_Bubbletrack:
			if (C < 0.5 && PhaseF(0,1,0) > 0.5)
			{
				location = Y + (C-0.5)/(C-PhaseF(0,1,0));
				AddToRTIBubble(location);
			}
	}
}
//#############//
//######THERMOCAPILLARY UPDATE######//
#ifdef OPTIONS_thermo
	CudaDeviceFunction real_t getT(){
    return Temp(0,0,0);
}
CudaDeviceFunction real_t getST(){
    real_t surfaceTen;
    if (surfPower > 1) {
        surfaceTen = sigma + sigma_TT*pow((Temp(0,0,0) - T_ref),surfPower) * (1.0/surfPower);
    } else {
        surfaceTen = sigma + sigma_T*(Temp(0,0,0) - T_ref);
    }
    return surfaceTen;
}
/* Save everything from buffer 1 to 2. */
CudaDeviceFunction void TempCopy(){
    g0  = g0(0,0,0);
    g1  = g1(0,0,0);
    g2  = g2(0,0,0);
    g3  = g3(0,0,0);
    g4  = g4(0,0,0);
    g5  = g5(0,0,0);
    g6  = g6(0,0,0);
    g7  = g7(0,0,0);
    g8  = g8(0,0,0);
    g9  = g9(0,0,0);
    g10 = g10(0,0,0);
    g11 = g11(0,0,0);
    g12 = g12(0,0,0);
    g13 = g13(0,0,0);
    g14 = g14(0,0,0);
    g15 = g15(0,0,0);
    g16 = g16(0,0,0);
    g17 = g17(0,0,0);
    g18 = g18(0,0,0);
    g19 = g19(0,0,0);
    g20 = g20(0,0,0);
    g21 = g21(0,0,0);
    g22 = g22(0,0,0);
    g23 = g23(0,0,0);
    g24 = g24(0,0,0);
    g25 = g25(0,0,0);
    g26 = g26(0,0,0);

    h0 = h0(0,0,0);
    h1 = h1(0,0,0);
    h2 = h2(0,0,0);
    h3 = h3(0,0,0);
    h4 = h3(0,0,0);
    h5 = h4(0,0,0);
    h6 = h5(0,0,0);
    h7 = h7(0,0,0);
    h8 = h8(0,0,0);
    h9 = h9(0,0,0);
    h10 = h10(0,0,0);
    h11 = h11(0,0,0);
    h12 = h12(0,0,0);
    h13 = h13(0,0,0);
    h14 = h14(0,0,0);

    U = U(0,0,0);
    V = V(0,0,0);
    W = W(0,0,0);

    nw_x = nw_x(0,0,0);
    nw_y = nw_y(0,0,0);
    nw_z = nw_z(0,0,0);

    PhaseF = PhaseF(0,0,0);

    Temp = Temp(0,0,0);
    Cond = Cond(0,0,0);
    SurfaceTension = SurfaceTension(0,0,0);
}

CudaDeviceFunction void ThermalCopy(){
    Temp = Temp(0,0,0);
    Cond = Cond(0,0,0);
    SurfaceTension = SurfaceTension(0,0,0);
}


CudaDeviceFunction void TempUpdate1(){
    PhaseF = PhaseF(0,0,0);
    if ( IamWall || IamSolid || ((NodeType & NODE_ADDITIONALS) == NODE_ConstantTemp) ) {
        RK1 = Temp(0,0,0);
    } else {
        real_t myCp, lapT, rho, tmpT, tmpK, UpdateT;
        int i;
        vector_t gradT = {0.0,0.0,0.0};
        vector_t gradK = {0.0,0.0,0.0};
        vector_t vel   = {U(0,0,0), V(0,0,0), W(0,0,0)};
        myCp = interp(PhaseF, cp_h, cp_l);
        rho  = interp(PhaseF, Density_h, Density_l);
        gradT.y = 16.00 * (Temp(0,1,0) - Temp(0,-1,0)) + Temp(1,1,1) + Temp(-1,1,1) - Temp(1,-1,1) - Temp(-1,-1,1) + Temp(1,1,-1)+ Temp(-1,1,-1)- Temp(1,-1,-1)- Temp(-1,-1,-1) +  4.00 * (Temp(1,1,0) + Temp(-1,1,0) - Temp(1,-1,0) - Temp(-1,-1,0) +  Temp(0,1,1) - Temp(0,-1,1) + Temp(0,1,-1) - Temp(0,-1,-1));
gradT.x = 16.00 * (Temp(1,0,0) - Temp(-1,0,0)) + Temp(1,1,1) - Temp(-1,1,1) + Temp(1,-1,1) - Temp(-1,-1,1) + Temp(1,1,-1)- Temp(-1,1,-1) + Temp(1,-1,-1) - Temp(-1,-1,-1) +  4.00 * (Temp(1,1,0) - Temp(-1,1,0) + Temp(1,-1,0) - Temp(-1,-1,0) + Temp(1,0,1) - Temp(-1,0,1) + Temp(1,0,-1) - Temp(-1,0,-1));
gradT.z = 16.00 * (Temp(0,0,1) - Temp(0,0,-1)) + Temp(1,1,1) + Temp(-1,1,1) + Temp(1,-1,1) + Temp(-1,-1,1) - Temp(1,1,-1)- Temp(-1,1,-1)- Temp(1,-1,-1)- Temp(-1,-1,-1) +  4.00 * (Temp(1,0,1) + Temp(-1,0,1) - Temp(1,0,-1) - Temp(-1,0,-1) +  Temp(0,1,1) + Temp(0,-1,1) - Temp(0,1,-1) - Temp(0,-1,-1));
gradT.x /= 72.0;
gradT.y /= 72.0;
gradT.z /= 72.0;
gradK.y = 16.00 * (Cond(0,1,0) - Cond(0,-1,0)) + Cond(1,1,1) + Cond(-1,1,1) - Cond(1,-1,1) - Cond(-1,-1,1) + Cond(1,1,-1)+ Cond(-1,1,-1)- Cond(1,-1,-1)- Cond(-1,-1,-1) +  4.00 * (Cond(1,1,0) + Cond(-1,1,0) - Cond(1,-1,0) - Cond(-1,-1,0) +  Cond(0,1,1) - Cond(0,-1,1) + Cond(0,1,-1) - Cond(0,-1,-1));
gradK.x = 16.00 * (Cond(1,0,0) - Cond(-1,0,0)) + Cond(1,1,1) - Cond(-1,1,1) + Cond(1,-1,1) - Cond(-1,-1,1) + Cond(1,1,-1)- Cond(-1,1,-1) + Cond(1,-1,-1) - Cond(-1,-1,-1) +  4.00 * (Cond(1,1,0) - Cond(-1,1,0) + Cond(1,-1,0) - Cond(-1,-1,0) + Cond(1,0,1) - Cond(-1,0,1) + Cond(1,0,-1) - Cond(-1,0,-1));
gradK.z = 16.00 * (Cond(0,0,1) - Cond(0,0,-1)) + Cond(1,1,1) + Cond(-1,1,1) + Cond(1,-1,1) + Cond(-1,-1,1) - Cond(1,1,-1)- Cond(-1,1,-1)- Cond(1,-1,-1)- Cond(-1,-1,-1) +  4.00 * (Cond(1,0,1) + Cond(-1,0,1) - Cond(1,0,-1) - Cond(-1,0,-1) +  Cond(0,1,1) + Cond(0,-1,1) - Cond(0,1,-1) - Cond(0,-1,-1));
gradK.x /= 72.0;
gradK.y /= 72.0;
gradK.z /= 72.0;
lapT = 16.0 *((Temp(1,0,0)) + (Temp(-1,0,0)) + (Temp(0,1,0)) + (Temp(0,-1,0))+ (Temp(0,0,1)) + (Temp(0,0,-1)))	+ 1.0 *((Temp(1,1,1)) + (Temp(-1,1,1)) + (Temp(1,-1,1))+ (Temp(-1,-1,1)) + (Temp(1,1,-1))+ (Temp(-1,1,-1)) + (Temp(1,-1,-1))+(Temp(-1,-1,-1))) + 4.0 *((Temp(1,1,0)) + (Temp(-1,1,0))+ (Temp(1,-1,0))+ (Temp(-1,-1,0))+ (Temp(1,0,1)) + (Temp(-1,0,1))+ (Temp(1,0,-1))+ (Temp(-1,0,-1))+ (Temp(0,1,1)) + (Temp(0,-1,1))+ (Temp(0,1,-1))+ (Temp(0,-1,-1))) - 152.0 * Temp(0,0,0);
lapT/= 36.0;

        // RK1 = Tn + 0.5h1
        RK1 = Temp(0,0,0) + stabiliser*0.5*(-1.0*dotProduct(vel, gradT) + (1.0/(rho*myCp)) * (dotProduct(gradK,gradT) + Cond(0,0,0)*lapT));
    }
}

CudaDeviceFunction void TempUpdate2(){
    PhaseF = PhaseF(0,0,0);
    if ( IamWall || IamSolid || ((NodeType & NODE_ADDITIONALS) == NODE_ConstantTemp) ) {
        RK2 = Temp(0,0,0);
    } else {
        real_t myCp, lapT, rho, tmpT, tmpK, UpdateT;
        int i;
        vector_t gradT = {0.0,0.0,0.0};
        vector_t gradK = {0.0,0.0,0.0};
        vector_t vel   = {U(0,0,0), V(0,0,0), W(0,0,0)};
        myCp = interp(PhaseF, cp_h, cp_l);
        rho  = interp(PhaseF, Density_h, Density_l);

        gradT.y = 16.00 * (RK1(0,1,0) - RK1(0,-1,0)) + RK1(1,1,1) + RK1(-1,1,1) - RK1(1,-1,1) - RK1(-1,-1,1) + RK1(1,1,-1)+ RK1(-1,1,-1)- RK1(1,-1,-1)- RK1(-1,-1,-1) +  4.00 * (RK1(1,1,0) + RK1(-1,1,0) - RK1(1,-1,0) - RK1(-1,-1,0) +  RK1(0,1,1) - RK1(0,-1,1) + RK1(0,1,-1) - RK1(0,-1,-1));
gradT.x = 16.00 * (RK1(1,0,0) - RK1(-1,0,0)) + RK1(1,1,1) - RK1(-1,1,1) + RK1(1,-1,1) - RK1(-1,-1,1) + RK1(1,1,-1)- RK1(-1,1,-1) + RK1(1,-1,-1) - RK1(-1,-1,-1) +  4.00 * (RK1(1,1,0) - RK1(-1,1,0) + RK1(1,-1,0) - RK1(-1,-1,0) + RK1(1,0,1) - RK1(-1,0,1) + RK1(1,0,-1) - RK1(-1,0,-1));
gradT.z = 16.00 * (RK1(0,0,1) - RK1(0,0,-1)) + RK1(1,1,1) + RK1(-1,1,1) + RK1(1,-1,1) + RK1(-1,-1,1) - RK1(1,1,-1)- RK1(-1,1,-1)- RK1(1,-1,-1)- RK1(-1,-1,-1) +  4.00 * (RK1(1,0,1) + RK1(-1,0,1) - RK1(1,0,-1) - RK1(-1,0,-1) +  RK1(0,1,1) + RK1(0,-1,1) - RK1(0,1,-1) - RK1(0,-1,-1));
gradT.x /= 72.0;
gradT.y /= 72.0;
gradT.z /= 72.0;
gradK.y = 16.00 * (Cond(0,1,0) - Cond(0,-1,0)) + Cond(1,1,1) + Cond(-1,1,1) - Cond(1,-1,1) - Cond(-1,-1,1) + Cond(1,1,-1)+ Cond(-1,1,-1)- Cond(1,-1,-1)- Cond(-1,-1,-1) +  4.00 * (Cond(1,1,0) + Cond(-1,1,0) - Cond(1,-1,0) - Cond(-1,-1,0) +  Cond(0,1,1) - Cond(0,-1,1) + Cond(0,1,-1) - Cond(0,-1,-1));
gradK.x = 16.00 * (Cond(1,0,0) - Cond(-1,0,0)) + Cond(1,1,1) - Cond(-1,1,1) + Cond(1,-1,1) - Cond(-1,-1,1) + Cond(1,1,-1)- Cond(-1,1,-1) + Cond(1,-1,-1) - Cond(-1,-1,-1) +  4.00 * (Cond(1,1,0) - Cond(-1,1,0) + Cond(1,-1,0) - Cond(-1,-1,0) + Cond(1,0,1) - Cond(-1,0,1) + Cond(1,0,-1) - Cond(-1,0,-1));
gradK.z = 16.00 * (Cond(0,0,1) - Cond(0,0,-1)) + Cond(1,1,1) + Cond(-1,1,1) + Cond(1,-1,1) + Cond(-1,-1,1) - Cond(1,1,-1)- Cond(-1,1,-1)- Cond(1,-1,-1)- Cond(-1,-1,-1) +  4.00 * (Cond(1,0,1) + Cond(-1,0,1) - Cond(1,0,-1) - Cond(-1,0,-1) +  Cond(0,1,1) + Cond(0,-1,1) - Cond(0,1,-1) - Cond(0,-1,-1));
gradK.x /= 72.0;
gradK.y /= 72.0;
gradK.z /= 72.0;
lapT = 16.0 *((RK1(1,0,0)) + (RK1(-1,0,0)) + (RK1(0,1,0)) + (RK1(0,-1,0))+ (RK1(0,0,1)) + (RK1(0,0,-1)))	+ 1.0 *((RK1(1,1,1)) + (RK1(-1,1,1)) + (RK1(1,-1,1))+ (RK1(-1,-1,1)) + (RK1(1,1,-1))+ (RK1(-1,1,-1)) + (RK1(1,-1,-1))+(RK1(-1,-1,-1))) + 4.0 *((RK1(1,1,0)) + (RK1(-1,1,0))+ (RK1(1,-1,0))+ (RK1(-1,-1,0))+ (RK1(1,0,1)) + (RK1(-1,0,1))+ (RK1(1,0,-1))+ (RK1(-1,0,-1))+ (RK1(0,1,1)) + (RK1(0,-1,1))+ (RK1(0,1,-1))+ (RK1(0,-1,-1))) - 152.0 * RK1(0,0,0);
lapT/= 36.0;

        // RK2 = Tn + 0.5h2
        RK2 = Temp(0,0,0) + stabiliser*0.5*(-1.0*dotProduct(vel, gradT) + (1.0/(rho*myCp)) * (dotProduct(gradK,gradT) + Cond(0,0,0)*lapT));
    }
}

CudaDeviceFunction void TempUpdate3(){
    PhaseF = PhaseF(0,0,0);
    RK2 = RK2(0,0,0);
    if ( IamWall || IamSolid || ((NodeType & NODE_ADDITIONALS) == NODE_ConstantTemp) ) {
        RK3 = Temp(0,0,0);
    //	} else if ((NodeType & NODE_ADDITIONALS) == NODE_EAdiabatic) {
    //		RK3 = Temp(-1,0,0);
    } else {
        real_t myCp, lapT, rho, tmpT, tmpK, UpdateT;
        int i;
        vector_t gradT = {0.0,0.0,0.0};
        vector_t gradK = {0.0,0.0,0.0};
        vector_t vel   = {U(0,0,0), V(0,0,0), W(0,0,0)};
        myCp = interp(PhaseF, cp_h, cp_l);
        rho  = interp(PhaseF, Density_h, Density_l);

        gradT.y = 16.00 * (RK2(0,1,0) - RK2(0,-1,0)) + RK2(1,1,1) + RK2(-1,1,1) - RK2(1,-1,1) - RK2(-1,-1,1) + RK2(1,1,-1)+ RK2(-1,1,-1)- RK2(1,-1,-1)- RK2(-1,-1,-1) +  4.00 * (RK2(1,1,0) + RK2(-1,1,0) - RK2(1,-1,0) - RK2(-1,-1,0) +  RK2(0,1,1) - RK2(0,-1,1) + RK2(0,1,-1) - RK2(0,-1,-1));
gradT.x = 16.00 * (RK2(1,0,0) - RK2(-1,0,0)) + RK2(1,1,1) - RK2(-1,1,1) + RK2(1,-1,1) - RK2(-1,-1,1) + RK2(1,1,-1)- RK2(-1,1,-1) + RK2(1,-1,-1) - RK2(-1,-1,-1) +  4.00 * (RK2(1,1,0) - RK2(-1,1,0) + RK2(1,-1,0) - RK2(-1,-1,0) + RK2(1,0,1) - RK2(-1,0,1) + RK2(1,0,-1) - RK2(-1,0,-1));
gradT.z = 16.00 * (RK2(0,0,1) - RK2(0,0,-1)) + RK2(1,1,1) + RK2(-1,1,1) + RK2(1,-1,1) + RK2(-1,-1,1) - RK2(1,1,-1)- RK2(-1,1,-1)- RK2(1,-1,-1)- RK2(-1,-1,-1) +  4.00 * (RK2(1,0,1) + RK2(-1,0,1) - RK2(1,0,-1) - RK2(-1,0,-1) +  RK2(0,1,1) + RK2(0,-1,1) - RK2(0,1,-1) - RK2(0,-1,-1));
gradT.x /= 72.0;
gradT.y /= 72.0;
gradT.z /= 72.0;
gradK.y = 16.00 * (Cond(0,1,0) - Cond(0,-1,0)) + Cond(1,1,1) + Cond(-1,1,1) - Cond(1,-1,1) - Cond(-1,-1,1) + Cond(1,1,-1)+ Cond(-1,1,-1)- Cond(1,-1,-1)- Cond(-1,-1,-1) +  4.00 * (Cond(1,1,0) + Cond(-1,1,0) - Cond(1,-1,0) - Cond(-1,-1,0) +  Cond(0,1,1) - Cond(0,-1,1) + Cond(0,1,-1) - Cond(0,-1,-1));
gradK.x = 16.00 * (Cond(1,0,0) - Cond(-1,0,0)) + Cond(1,1,1) - Cond(-1,1,1) + Cond(1,-1,1) - Cond(-1,-1,1) + Cond(1,1,-1)- Cond(-1,1,-1) + Cond(1,-1,-1) - Cond(-1,-1,-1) +  4.00 * (Cond(1,1,0) - Cond(-1,1,0) + Cond(1,-1,0) - Cond(-1,-1,0) + Cond(1,0,1) - Cond(-1,0,1) + Cond(1,0,-1) - Cond(-1,0,-1));
gradK.z = 16.00 * (Cond(0,0,1) - Cond(0,0,-1)) + Cond(1,1,1) + Cond(-1,1,1) + Cond(1,-1,1) + Cond(-1,-1,1) - Cond(1,1,-1)- Cond(-1,1,-1)- Cond(1,-1,-1)- Cond(-1,-1,-1) +  4.00 * (Cond(1,0,1) + Cond(-1,0,1) - Cond(1,0,-1) - Cond(-1,0,-1) +  Cond(0,1,1) + Cond(0,-1,1) - Cond(0,1,-1) - Cond(0,-1,-1));
gradK.x /= 72.0;
gradK.y /= 72.0;
gradK.z /= 72.0;
lapT = 16.0 *((RK2(1,0,0)) + (RK2(-1,0,0)) + (RK2(0,1,0)) + (RK2(0,-1,0))+ (RK2(0,0,1)) + (RK2(0,0,-1)))	+ 1.0 *((RK2(1,1,1)) + (RK2(-1,1,1)) + (RK2(1,-1,1))+ (RK2(-1,-1,1)) + (RK2(1,1,-1))+ (RK2(-1,1,-1)) + (RK2(1,-1,-1))+(RK2(-1,-1,-1))) + 4.0 *((RK2(1,1,0)) + (RK2(-1,1,0))+ (RK2(1,-1,0))+ (RK2(-1,-1,0))+ (RK2(1,0,1)) + (RK2(-1,0,1))+ (RK2(1,0,-1))+ (RK2(-1,0,-1))+ (RK2(0,1,1)) + (RK2(0,-1,1))+ (RK2(0,1,-1))+ (RK2(0,-1,-1))) - 152.0 * RK2(0,0,0);
lapT/= 36.0;

        // RK3 = Tn + h3
        RK3 = Temp(0,0,0) + stabiliser*1.0*(-1.0*dotProduct(vel, gradT) + (1.0/(rho*myCp)) * (dotProduct(gradK,gradT) + Cond(0,0,0)*lapT));
    }
}

CudaDeviceFunction void TempUpdate4(){
    PhaseF = PhaseF(0,0,0);
    RK3 = RK3(0,0,0);
    if ( IamWall || IamSolid || ((NodeType & NODE_ADDITIONALS) == NODE_ConstantTemp) ) {
        Temp = Temp(0,0,0);
    //	} else if ((NodeType & NODE_ADDITIONALS) == NODE_EAdiabatic) {
    //		Temp = RK3(0,0,0);
    } else {
        real_t myCp, lapT, rho, tmpT, tmpK, UpdateT;
        int i;
        vector_t gradT = {0.0,0.0,0.0};
        vector_t gradK = {0.0,0.0,0.0};
        vector_t vel   = {U(0,0,0), V(0,0,0), W(0,0,0)};
        myCp = interp(PhaseF, cp_h, cp_l);
        rho  = interp(PhaseF, Density_h, Density_l);

        gradT.y = 16.00 * (RK3(0,1,0) - RK3(0,-1,0)) + RK3(1,1,1) + RK3(-1,1,1) - RK3(1,-1,1) - RK3(-1,-1,1) + RK3(1,1,-1)+ RK3(-1,1,-1)- RK3(1,-1,-1)- RK3(-1,-1,-1) +  4.00 * (RK3(1,1,0) + RK3(-1,1,0) - RK3(1,-1,0) - RK3(-1,-1,0) +  RK3(0,1,1) - RK3(0,-1,1) + RK3(0,1,-1) - RK3(0,-1,-1));
gradT.x = 16.00 * (RK3(1,0,0) - RK3(-1,0,0)) + RK3(1,1,1) - RK3(-1,1,1) + RK3(1,-1,1) - RK3(-1,-1,1) + RK3(1,1,-1)- RK3(-1,1,-1) + RK3(1,-1,-1) - RK3(-1,-1,-1) +  4.00 * (RK3(1,1,0) - RK3(-1,1,0) + RK3(1,-1,0) - RK3(-1,-1,0) + RK3(1,0,1) - RK3(-1,0,1) + RK3(1,0,-1) - RK3(-1,0,-1));
gradT.z = 16.00 * (RK3(0,0,1) - RK3(0,0,-1)) + RK3(1,1,1) + RK3(-1,1,1) + RK3(1,-1,1) + RK3(-1,-1,1) - RK3(1,1,-1)- RK3(-1,1,-1)- RK3(1,-1,-1)- RK3(-1,-1,-1) +  4.00 * (RK3(1,0,1) + RK3(-1,0,1) - RK3(1,0,-1) - RK3(-1,0,-1) +  RK3(0,1,1) + RK3(0,-1,1) - RK3(0,1,-1) - RK3(0,-1,-1));
gradT.x /= 72.0;
gradT.y /= 72.0;
gradT.z /= 72.0;
gradK.y = 16.00 * (Cond(0,1,0) - Cond(0,-1,0)) + Cond(1,1,1) + Cond(-1,1,1) - Cond(1,-1,1) - Cond(-1,-1,1) + Cond(1,1,-1)+ Cond(-1,1,-1)- Cond(1,-1,-1)- Cond(-1,-1,-1) +  4.00 * (Cond(1,1,0) + Cond(-1,1,0) - Cond(1,-1,0) - Cond(-1,-1,0) +  Cond(0,1,1) - Cond(0,-1,1) + Cond(0,1,-1) - Cond(0,-1,-1));
gradK.x = 16.00 * (Cond(1,0,0) - Cond(-1,0,0)) + Cond(1,1,1) - Cond(-1,1,1) + Cond(1,-1,1) - Cond(-1,-1,1) + Cond(1,1,-1)- Cond(-1,1,-1) + Cond(1,-1,-1) - Cond(-1,-1,-1) +  4.00 * (Cond(1,1,0) - Cond(-1,1,0) + Cond(1,-1,0) - Cond(-1,-1,0) + Cond(1,0,1) - Cond(-1,0,1) + Cond(1,0,-1) - Cond(-1,0,-1));
gradK.z = 16.00 * (Cond(0,0,1) - Cond(0,0,-1)) + Cond(1,1,1) + Cond(-1,1,1) + Cond(1,-1,1) + Cond(-1,-1,1) - Cond(1,1,-1)- Cond(-1,1,-1)- Cond(1,-1,-1)- Cond(-1,-1,-1) +  4.00 * (Cond(1,0,1) + Cond(-1,0,1) - Cond(1,0,-1) - Cond(-1,0,-1) +  Cond(0,1,1) + Cond(0,-1,1) - Cond(0,1,-1) - Cond(0,-1,-1));
gradK.x /= 72.0;
gradK.y /= 72.0;
gradK.z /= 72.0;
lapT = 16.0 *((RK3(1,0,0)) + (RK3(-1,0,0)) + (RK3(0,1,0)) + (RK3(0,-1,0))+ (RK3(0,0,1)) + (RK3(0,0,-1)))	+ 1.0 *((RK3(1,1,1)) + (RK3(-1,1,1)) + (RK3(1,-1,1))+ (RK3(-1,-1,1)) + (RK3(1,1,-1))+ (RK3(-1,1,-1)) + (RK3(1,-1,-1))+(RK3(-1,-1,-1))) + 4.0 *((RK3(1,1,0)) + (RK3(-1,1,0))+ (RK3(1,-1,0))+ (RK3(-1,-1,0))+ (RK3(1,0,1)) + (RK3(-1,0,1))+ (RK3(1,0,-1))+ (RK3(-1,0,-1))+ (RK3(0,1,1)) + (RK3(0,-1,1))+ (RK3(0,1,-1))+ (RK3(0,-1,-1))) - 152.0 * RK3(0,0,0);
lapT/= 36.0;


        UpdateT = Temp(0,0,0);
        Temp = (1-4.0/3.0)*UpdateT + (2*RK1(0,0,0) + 4*RK2(0,0,0) + 2*RK3(0,0,0) - stabiliser*(1.0*dotProduct(vel, gradT) + (1.0/(rho*myCp)) * (dotProduct(gradK,gradT) + Cond(0,0,0)*lapT)))/6.0;
        AddToTempChange( (Temp-UpdateT)*(Temp-UpdateT)  );
    }
    if (surfPower > 1) {
        SurfaceTension = sigma + sigma_TT*pow((Temp(0,0,0) - T_ref),surfPower) * (1.0/surfPower);
    } else {
        SurfaceTension = sigma + sigma_T*(Temp(0,0,0) - T_ref);
    }
}

CudaDeviceFunction void BoundUpdate(){
    if ((NodeType & NODE_ADDITIONALS) == NODE_EAdiabatic) {
        Temp = Temp(-1,0,0);
    } else {
        Temp = Temp(0,0,0);
    }
    if (surfPower > 1) {
        SurfaceTension = sigma + sigma_TT*pow((Temp(0,0,0) - T_ref),surfPower) * (1.0/surfPower);
    } else {
        SurfaceTension = sigma + sigma_T*(Temp(0,0,0) - T_ref);
    }
}

CudaDeviceFunction real_t dotProduct( vector_t a, vector_t b) {
    return a.x*b.x + a.y*b.y + a.z*b.z;
}

CudaDeviceFunction real_t interp(real_t current, real_t upper, real_t lower){
    return lower + current*(upper - lower);
}

#endif
//#############//


#ifdef OPTIONS_BGK
CudaDeviceFunction void CollisionBGK()
{
    PhaseF = PhaseF(0,0,0);
	int i, j;
	real_t C  = PhaseF;
	if (stage16_replay_diagnostics_active()) {
		ReplayPhaseConsumed = C;
	}
	ForceIterResidual = 0.0;
	ForceIterCount = 0.0;
	MassCorrectionApplied = 0.0;
	PhaseStencilGhostUseCount = 0.0;
	PhaseStencilFallbackCount = 0.0;
	PhaseStencilMidpointFallbackCount = 0.0;
    real_t mu = calcMu( C );
	real_t tau, DynVisc, rho, p;			// Macroscopic Properties
	vector_t gradPhi;				// Phase field gradients
	real_t nx, ny, nz, magnPhi;			// Normals
	real_t Gamma[27], geq[27], mag;			// equilibrium, pressure equilibrium, velocity magnitude
	real_t F_surf[3], F_pressure[3], F_body[3], F_mu[3], F_total[3]; // Forces
	real_t tmp1, stress[6]={0.0,0.0,0.0,0.0,0.0,0.0};     // Stress tensor calculation
	real_t F_phi[hPops], heq[hPops];			// Phase field collision terms
	real_t F_i[27];					// Momentum distribution forcing term

	// Find Macroscopic Details
	rho = Density_l + (C - PhaseField_l)*(Density_h - Density_l)/(PhaseField_h - PhaseField_l);
	p = g26 + g25 + g24 + g23 + g22 + g21 + g20 + g19 + g18 + g17 + g16 + g15 + g14 + g13 + g12 + g11 + g10 + g9 + g8 + g7 + g6 + g5 + g4 + g3 + g2 + g1 + g0;
	tau = calcTau( C );

	updateMyGlobals( C );

	// GRADIENTS AND NORMALS
	gradPhi = calcGradPhi();
	if (stage16_replay_diagnostics_active()) {
		ReplayGradPhiX = gradPhi.x;
		ReplayGradPhiY = gradPhi.y;
		ReplayGradPhiZ = gradPhi.z;
	}
	magnPhi = sqrt(gradPhi.x*gradPhi.x + gradPhi.y*gradPhi.y + gradPhi.z*gradPhi.z + 1e-32);
	nx = gradPhi.x/magnPhi;
	ny = gradPhi.y/magnPhi;
	nz = gradPhi.z/magnPhi;
	// Stage 15B: DynamicCL shadow (BGK path). Diagnostics only; never added to
	// F_total in 15B. See the MRT path above and calcDynamicCLShadow for the
	// 15C write hook (reserved; runner refuses DynamicCLMode>=2).
	real_t fcl_x = 0.0, fcl_y = 0.0, fcl_z = 0.0;
	{
		// Stage 15B/15C: diagnostics on every call; fcl_* hoisted for the 15C
		// write hook below (BGK path, symmetric with MRT).
		calcDynamicCLShadow(gradPhi, C, &fcl_x, &fcl_y, &fcl_z);
	}

	// CALCULATE FORCES:
    calc_Fp(&F_pressure[0], &F_pressure[1], &F_pressure[2], p, gradPhi);
	calc_Fb(&F_body[0], &F_body[1], &F_body[2], rho);
    calc_Fs(&F_surf[0], &F_surf[1], &F_surf[2], mu, gradPhi);
	if (stage16_replay_diagnostics_active()) {
		ReplayFpressureX = F_pressure[0];
		ReplayFpressureY = F_pressure[1];
		ReplayFpressureZ = F_pressure[2];
		ReplayFbodyX = F_body[0];
		ReplayFbodyY = F_body[1];
		ReplayFbodyZ = F_body[2];
		ReplayFsurfX = F_surf[0];
		ReplayFsurfY = F_surf[1];
		ReplayFsurfZ = F_surf[2];
	}
    // VISCOUS FORCE:
    for (j=0;j<2;j++) {
		ForceIterCount = j + 1;
    // GAMMA AND EQUILIBRIUM
        mag = U*U + V*V + W*W;
        for (i=0; i< 27; i++){
            Gamma[i] = calcGamma(i, U, V, W, mag);
            geq[i] = wg[i]*p + Gamma[i] - wg[i];
        }

    geq[0] = -geq[0] + g0;
geq[1] = -geq[1] + g1;
geq[2] = -geq[2] + g2;
geq[3] = -geq[3] + g3;
geq[4] = -geq[4] + g4;
geq[5] = -geq[5] + g5;
geq[6] = -geq[6] + g6;
geq[7] = -geq[7] + g7;
geq[8] = -geq[8] + g8;
geq[9] = -geq[9] + g9;
geq[10] = -geq[10] + g10;
geq[11] = -geq[11] + g11;
geq[12] = -geq[12] + g12;
geq[13] = -geq[13] + g13;
geq[14] = -geq[14] + g14;
geq[15] = -geq[15] + g15;
geq[16] = -geq[16] + g16;
geq[17] = -geq[17] + g17;
geq[18] = -geq[18] + g18;
geq[19] = -geq[19] + g19;
geq[20] = -geq[20] + g20;
geq[21] = -geq[21] + g21;
geq[22] = -geq[22] + g22;
geq[23] = -geq[23] + g23;
geq[24] = -geq[24] + g24;
geq[25] = -geq[25] + g25;
geq[26] = -geq[26] + g26;

            // Stress/strain Tensor
        for (i=0; i< 6 ; i++)
        {
            stress[i] = 0.0;
        }
        for (i=0; i< 27; i++){
            stress[0] += geq[i]*d3q27_ex[i]*d3q27_ex[i];
            stress[1] += geq[i]*d3q27_ex[i]*d3q27_ey[i];
            stress[2] += geq[i]*d3q27_ex[i]*d3q27_ez[i];
            stress[3] += geq[i]*d3q27_ey[i]*d3q27_ey[i];
            stress[4] += geq[i]*d3q27_ey[i]*d3q27_ez[i];
            stress[5] += geq[i]*d3q27_ez[i]*d3q27_ez[i];
        }

        F_mu[0] = (0.5-tau)/tau * (Density_h-Density_l) * (stress[0]*gradPhi.x + stress[1]*gradPhi.y + stress[2]*gradPhi.z);
        F_mu[1] = (0.5-tau)/tau * (Density_h-Density_l) * (stress[1]*gradPhi.x + stress[3]*gradPhi.y + stress[4]*gradPhi.z);
        F_mu[2] = (0.5-tau)/tau * (Density_h-Density_l) * (stress[2]*gradPhi.x + stress[4]*gradPhi.y + stress[5]*gradPhi.z);
        F_total[0] = F_surf[0] + F_pressure[0] + F_body[0] + F_mu[0];
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
        if (stage16_replay_diagnostics_active()) {
            ReplayFmuX = F_mu[0];
            ReplayFmuY = F_mu[1];
            ReplayFmuZ = F_mu[2];
            ReplayFtotalX = F_total[0];
            ReplayFtotalY = F_total[1];
            ReplayFtotalZ = F_total[2];
        }

    U = -g22 + g21 - g20 + g19 - g18 + g17 - g16 + g15 - g14 + g13 - g12 + g11 - g10 + g9 - g8 + g7 - g2 + g1;
V = -g26 + g25 - g24 + g23 - g18 - g17 + g16 + g15 - g14 - g13 + g12 + g11 - g10 - g9 + g8 + g7 - g4 + g3;
W = -g26 - g25 + g24 + g23 - g22 - g21 + g20 + g19 - g14 - g13 - g12 - g11 + g10 + g9 + g8 + g7 - g6 + g5;

        U = U + (0.5*F_total[0])/rho;
        V = V + (0.5*F_total[1])/rho;
        W = W + (0.5*F_total[2])/rho;
    }

	// PHASE FIELD POPULATION UPDATE:
	tmp1 = (1.0 - 4.0*(C - 0.5)*(C - 0.5))/IntWidth;
	for (i=0; i< hPops; i++){
		F_phi[i] = calcF_phi(i, tmp1, nx, ny, nz);		// Forcing Terms
		heq[i] = C * Gamma[i];	// heq
	}

	h0 = F_phi[0] + h0 + ( -h0 + PhaseField*wg[0]*8./27. + ( -F_phi[0]*9. + ( -W*W - V*V - U*U )*PhaseField*wg[0]*8. )/18. )*omega_phi;
h1 = F_phi[1] + h1 + ( -h1 + PhaseField*wg[1]*2./27. + ( -F_phi[1]*9. + ( -W*W - V*V + ( 1 + U )*U*2. )*PhaseField*wg[1]*2. )/18. )*omega_phi;
h2 = F_phi[2] + h2 + ( -h2 + PhaseField*wg[2]*2./27. + ( -F_phi[2]*9. + ( -W*W - V*V + ( -1 + U )*U*2. )*PhaseField*wg[2]*2. )/18. )*omega_phi;
h3 = F_phi[3] + h3 + ( -h3 + PhaseField*wg[3]*2./27. + ( -F_phi[3]*9. + ( -W*W - U*U + ( 1 + V )*V*2. )*PhaseField*wg[3]*2. )/18. )*omega_phi;
h4 = F_phi[4] + h4 + ( -h4 + PhaseField*wg[4]*2./27. + ( -F_phi[4]*9. + ( -W*W - U*U + ( -1 + V )*V*2. )*PhaseField*wg[4]*2. )/18. )*omega_phi;
h5 = F_phi[5] + h5 + ( -h5 + PhaseField*wg[5]*2./27. + ( -F_phi[5]*9. + ( -V*V - U*U + ( 1 + W )*W*2. )*PhaseField*wg[5]*2. )/18. )*omega_phi;
h6 = F_phi[6] + h6 + ( -h6 + PhaseField*wg[6]*2./27. + ( -F_phi[6]*9. + ( -V*V - U*U + ( -1 + W )*W*2. )*PhaseField*wg[6]*2. )/18. )*omega_phi;
h7 = F_phi[7] + h7 + ( -h7 + ( PhaseField*wg[7] + ( -F_phi[7]*36. + ( ( 1 + W )*W + ( 1 + V + W*3. )*V + ( 1 + U + ( W + V )*3. )*U )*PhaseField*wg[7] )*3. )*0.00462962962962964 )*omega_phi;
h8 = F_phi[8] + h8 + ( -h8 + ( PhaseField*wg[8] + ( -F_phi[8]*36. + ( ( 1 + W )*W + ( 1 + V + W*3. )*V + ( -1 + U + ( -W - V )*3. )*U )*PhaseField*wg[8] )*3. )*0.00462962962962964 )*omega_phi;
h9 = F_phi[9] + h9 + ( -h9 + ( PhaseField*wg[9] + ( -F_phi[9]*36. + ( ( 1 + W )*W + ( -1 + V - W*3. )*V + ( 1 + U + ( W - V )*3. )*U )*PhaseField*wg[9] )*3. )*0.00462962962962964 )*omega_phi;
h10 = F_phi[10] + h10 + ( -h10 + ( PhaseField*wg[10] + ( -F_phi[10]*36. + ( ( 1 + W )*W + ( -1 + V - W*3. )*V + ( -1 + U + ( -W + V )*3. )*U )*PhaseField*wg[10] )*3. )*0.00462962962962964 )*omega_phi;
h11 = F_phi[11] + h11 + ( -h11 + ( PhaseField*wg[11] + ( -F_phi[11]*36. + ( ( -1 + W )*W + ( 1 + V - W*3. )*V + ( 1 + U + ( -W + V )*3. )*U )*PhaseField*wg[11] )*3. )*0.00462962962962964 )*omega_phi;
h12 = F_phi[12] + h12 + ( -h12 + ( PhaseField*wg[12] + ( -F_phi[12]*36. + ( ( -1 + W )*W + ( 1 + V - W*3. )*V + ( -1 + U + ( W - V )*3. )*U )*PhaseField*wg[12] )*3. )*0.00462962962962964 )*omega_phi;
h13 = F_phi[13] + h13 + ( -h13 + ( PhaseField*wg[13] + ( -F_phi[13]*36. + ( ( -1 + W )*W + ( -1 + V + W*3. )*V + ( 1 + U + ( -W - V )*3. )*U )*PhaseField*wg[13] )*3. )*0.00462962962962964 )*omega_phi;
h14 = F_phi[14] + h14 + ( -h14 + ( PhaseField*wg[14] + ( -F_phi[14]*36. + ( ( -1 + W )*W + ( -1 + V + W*3. )*V + ( -1 + U + ( W + V )*3. )*U )*PhaseField*wg[14] )*3. )*0.00462962962962964 )*omega_phi;
h15 = F_phi[15] + h15 + ( -h15 + PhaseField*wg[15]*0.0185185185185185 + ( -W*W*PhaseField*wg[15] + ( -F_phi[15]*9. + ( ( 1 + V )*V + ( 1 + U + V*3. )*U )*PhaseField*wg[15] )*2. )/36. )*omega_phi;
h16 = F_phi[16] + h16 + ( -h16 + PhaseField*wg[16]*0.0185185185185185 + ( -W*W*PhaseField*wg[16] + ( -F_phi[16]*9. + ( ( 1 + V )*V + ( -1 + U - V*3. )*U )*PhaseField*wg[16] )*2. )/36. )*omega_phi;
h17 = F_phi[17] + h17 + ( -h17 + PhaseField*wg[17]*0.0185185185185185 + ( -W*W*PhaseField*wg[17] + ( -F_phi[17]*9. + ( ( -1 + V )*V + ( 1 + U - V*3. )*U )*PhaseField*wg[17] )*2. )/36. )*omega_phi;
h18 = F_phi[18] + h18 + ( -h18 + PhaseField*wg[18]*0.0185185185185185 + ( -W*W*PhaseField*wg[18] + ( -F_phi[18]*9. + ( ( -1 + V )*V + ( -1 + U + V*3. )*U )*PhaseField*wg[18] )*2. )/36. )*omega_phi;
h19 = F_phi[19] + h19 + ( -h19 + PhaseField*wg[19]*0.0185185185185185 + ( -V*V*PhaseField*wg[19] + ( -F_phi[19]*9. + ( ( 1 + W )*W + ( 1 + U + W*3. )*U )*PhaseField*wg[19] )*2. )/36. )*omega_phi;
h20 = F_phi[20] + h20 + ( -h20 + PhaseField*wg[20]*0.0185185185185185 + ( -V*V*PhaseField*wg[20] + ( -F_phi[20]*9. + ( ( 1 + W )*W + ( -1 + U - W*3. )*U )*PhaseField*wg[20] )*2. )/36. )*omega_phi;
h21 = F_phi[21] + h21 + ( -h21 + PhaseField*wg[21]*0.0185185185185185 + ( -V*V*PhaseField*wg[21] + ( -F_phi[21]*9. + ( ( -1 + W )*W + ( 1 + U - W*3. )*U )*PhaseField*wg[21] )*2. )/36. )*omega_phi;
h22 = F_phi[22] + h22 + ( -h22 + PhaseField*wg[22]*0.0185185185185185 + ( -V*V*PhaseField*wg[22] + ( -F_phi[22]*9. + ( ( -1 + W )*W + ( -1 + U + W*3. )*U )*PhaseField*wg[22] )*2. )/36. )*omega_phi;
h23 = F_phi[23] + h23 + ( -h23 + PhaseField*wg[23]*0.0185185185185185 + ( -U*U*PhaseField*wg[23] + ( -F_phi[23]*9. + ( ( 1 + W )*W + ( 1 + V + W*3. )*V )*PhaseField*wg[23] )*2. )/36. )*omega_phi;
h24 = F_phi[24] + h24 + ( -h24 + PhaseField*wg[24]*0.0185185185185185 + ( -U*U*PhaseField*wg[24] + ( -F_phi[24]*9. + ( ( 1 + W )*W + ( -1 + V - W*3. )*V )*PhaseField*wg[24] )*2. )/36. )*omega_phi;
h25 = F_phi[25] + h25 + ( -h25 + PhaseField*wg[25]*0.0185185185185185 + ( -U*U*PhaseField*wg[25] + ( -F_phi[25]*9. + ( ( -1 + W )*W + ( 1 + V - W*3. )*V )*PhaseField*wg[25] )*2. )/36. )*omega_phi;
h26 = F_phi[26] + h26 + ( -h26 + PhaseField*wg[26]*0.0185185185185185 + ( -U*U*PhaseField*wg[26] + ( -F_phi[26]*9. + ( ( -1 + W )*W + ( -1 + V + W*3. )*V )*PhaseField*wg[26] )*2. )/36. )*omega_phi;


	// PRESSURE EVOLUTION UPDATE:
	for (i=0; i< 27; i++) {
		F_i[i] = 3.0*wg[i] * (F_total[0]*d3q27_ex[i] + F_total[1]*d3q27_ey[i] + F_total[2]*d3q27_ez[i])/rho;
	}
	real_t omega_g = 1.0/tau;
	g0 = -omega_g*geq[0] + g0 + ( 1 - omega_g/2. )*F_i[0];
g1 = -omega_g*geq[1] + g1 + ( 1 - omega_g/2. )*F_i[1];
g2 = -omega_g*geq[2] + g2 + ( 1 - omega_g/2. )*F_i[2];
g3 = -omega_g*geq[3] + g3 + ( 1 - omega_g/2. )*F_i[3];
g4 = -omega_g*geq[4] + g4 + ( 1 - omega_g/2. )*F_i[4];
g5 = -omega_g*geq[5] + g5 + ( 1 - omega_g/2. )*F_i[5];
g6 = -omega_g*geq[6] + g6 + ( 1 - omega_g/2. )*F_i[6];
g7 = -omega_g*geq[7] + g7 + ( 1 - omega_g/2. )*F_i[7];
g8 = -omega_g*geq[8] + g8 + ( 1 - omega_g/2. )*F_i[8];
g9 = -omega_g*geq[9] + g9 + ( 1 - omega_g/2. )*F_i[9];
g10 = -omega_g*geq[10] + g10 + ( 1 - omega_g/2. )*F_i[10];
g11 = -omega_g*geq[11] + g11 + ( 1 - omega_g/2. )*F_i[11];
g12 = -omega_g*geq[12] + g12 + ( 1 - omega_g/2. )*F_i[12];
g13 = -omega_g*geq[13] + g13 + ( 1 - omega_g/2. )*F_i[13];
g14 = -omega_g*geq[14] + g14 + ( 1 - omega_g/2. )*F_i[14];
g15 = -omega_g*geq[15] + g15 + ( 1 - omega_g/2. )*F_i[15];
g16 = -omega_g*geq[16] + g16 + ( 1 - omega_g/2. )*F_i[16];
g17 = -omega_g*geq[17] + g17 + ( 1 - omega_g/2. )*F_i[17];
g18 = -omega_g*geq[18] + g18 + ( 1 - omega_g/2. )*F_i[18];
g19 = -omega_g*geq[19] + g19 + ( 1 - omega_g/2. )*F_i[19];
g20 = -omega_g*geq[20] + g20 + ( 1 - omega_g/2. )*F_i[20];
g21 = -omega_g*geq[21] + g21 + ( 1 - omega_g/2. )*F_i[21];
g22 = -omega_g*geq[22] + g22 + ( 1 - omega_g/2. )*F_i[22];
g23 = -omega_g*geq[23] + g23 + ( 1 - omega_g/2. )*F_i[23];
g24 = -omega_g*geq[24] + g24 + ( 1 - omega_g/2. )*F_i[24];
g25 = -omega_g*geq[25] + g25 + ( 1 - omega_g/2. )*F_i[25];
g26 = -omega_g*geq[26] + g26 + ( 1 - omega_g/2. )*F_i[26];

    updateTrackers( C );
}
#endif

CudaDeviceFunction vector_t getA(){
	vector_t ret;
	return ret;
}
CudaDeviceFunction float2 Color() {
        float2 ret;
        vector_t u = getU();
        ret.x = PhaseF(0,0);
        if (NodeType == NODE_Solid){
                ret.y = 0;
        } else {
                ret.y = 1;
        }
        return ret;
}

/* MRT Matrix Check:
    g0 g1 g2 g3 g4 g5 g6 g7 g8 g9 g10 g11 g12 g13 g14 g15 g16 g17 g18 g19 g20 g21 g22 g23 g24 g25 g26
     1  1  1  1  1  1  1  1  1  1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1   1
m1   0  1 -1  0  0  0  0  1 -1  1  -1   1  -1   1  -1   1  -1   1  -1   1  -1   1  -1   0   0   0   0
m2   0  0  0  1 -1  0  0  1  1 -1  -1   1   1  -1  -1   1   1  -1  -1   0   0   0   0   1  -1   1  -1
m3   0  0  0  0  0  1 -1  1  1  1   1  -1  -1  -1  -1   0   0   0   0   1   1  -1  -1   1   1  -1  -1
m4   0  0  0  0  0  0  0  1 -1 -1   1   1  -1  -1   1   1  -1  -1   1   0   0   0   0   0   0   0   0
m5   0  0  0  0  0  0  0  1  1 -1  -1  -1  -1   1   1   0   0   0   0   0   0   0   0   1  -1  -1   1
m6   0  0  0  0  0  0  0  1 -1  1  -1  -1   1  -1   1   0   0   0   0   1  -1  -1   1   0   0   0   0
m7   0  2  2 -1 -1 -1 -1  0  0  0   0   0   0   0   0   1   1   1   1   1   1   1   1  -2  -2  -2  -2
m8   0  0  0  1  1 -1 -1  0  0  0   0   0   0   0   0   1   1   1   1  -1  -1  -1  -1   0   0   0   0
m9  -1  0  0  0  0  0  0  2  2  2   2   2   2   2   2   1   1   1   1   1   1   1   1   1   1   1   1
m10  0 -2  2  0  0  0  0  4 -4  4  -4   4  -4   4  -4   1  -1   1  -1   1  -1   1  -1   0   0   0   0
m11  0  0  0 -2  2  0  0  4  4 -4  -4   4   4  -4  -4   1   1  -1  -1   0   0   0   0   1  -1   1  -1
m12  0  0  0  0  0 -2  2  4  4  4   4  -4  -4  -4  -4   0   0   0   0   1   1  -1  -1   1   1  -1  -1
m13  0  0  0  0  0  0  0  0  0  0   0   0   0   0   0   1  -1   1  -1  -1   1  -1   1   0   0   0   0
m14  0  0  0  0  0  0  0  0  0  0   0   0   0   0   0  -1  -1   1   1   0   0   0   0   1  -1   1  -1
m15  0  0  0  0  0  0  0  0  0  0   0   0   0   0   0   0   0   0   0   1   1  -1  -1  -1  -1   1   1
m16  0  0  0  0  0  0  0  1 -1 -1   1  -1   1   1  -1   0   0   0   0   0   0   0   0   0   0   0   0
m17  1 -1 -1 -1 -1 -1 -1  4  4  4   4   4   4   4   4   0   0   0   0   0   0   0   0   0   0   0   0
m18  0 -2 -2  1  1  1  1  0  0  0   0   0   0   0   0   2   2   2   2   2   2   2   2  -4  -4  -4  -4
m19  0  0  0 -1 -1  1  1  0  0  0   0   0   0   0   0   2   2   2   2  -2  -2  -2  -2   0   0   0   0
m20  0  0  0  0  0  0  0  2 -2 -2   2   2  -2  -2   2  -1   1   1  -1   0   0   0   0   0   0   0   0
m21  0  0  0  0  0  0  0  2  2 -2  -2  -2  -2   2   2   0   0   0   0   0   0   0   0  -1   1   1  -1
m22  0  0  0  0  0  0  0  2 -2  2  -2  -2   2  -2   2   0   0   0   0  -1   1   1  -1   0   0   0   0
m23  0  1 -1  0  0  0  0  4 -4  4  -4   4  -4   4  -4  -2   2  -2   2  -2   2  -2   2   0   0   0   0
m24  0  0  0  1 -1  0  0  4  4 -4  -4   4   4  -4  -4  -2  -2   2   2   0   0   0   0  -2   2  -2   2
m25  0  0  0  0  0  1 -1  4  4  4   4  -4  -4  -4  -4   0   0   0   0  -2  -2   2   2  -2  -2   2   2
m26 -1  2  2  2  2  2  2  8  8  8   8   8   8   8   8  -4  -4  -4  -4  -4  -4  -4  -4  -4  -4  -4  -4
Orthogonality Check
Moment 0:  1.00, 0.00, -0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, -0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, -0.00,
Moment 1:  0.33, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, -0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,
Moment 2:  0.33, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, -0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,
Moment 3:  0.33, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, -0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,
Moment 4:  0.11, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,
Moment 5:  0.11, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,
Moment 6:  0.11, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,
Moment 7:  1.33, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, -0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,
Moment 8:  0.44, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,
Moment 9:  0.67, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,
Moment 10:  1.33, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,
Moment 11:  1.33, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,
Moment 12:  1.33, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,
Moment 13:  0.15, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,
Moment 14:  0.15, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,
Moment 15:  0.15, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,
Moment 16:  0.04, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,
Moment 17:  1.33, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,
Moment 18:  2.67, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,
Moment 19:  0.89, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,
Moment 20:  0.22, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,
Moment 21:  0.22, 0.00, 0.00, 0.00, 0.00, 0.00,
Moment 22:  0.22, 0.00, 0.00, 0.00, 0.00,
Moment 23:  1.33, 0.00, 0.00, 0.00,
Moment 24:  1.33, 0.00, 0.00,
Moment 25:  1.33, 0.00,
Moment 26:  8.00,

*/
