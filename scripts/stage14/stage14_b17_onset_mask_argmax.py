#!/usr/bin/env python3
"""Stage14-B17 mask and argmax onset diagnostics.

This script is diagnostic-only. It reads TCLB VTI frames from a short
wall_60to30_10 onset run and answers where the first large values occur:
interface, near-wall, low-density gas, liquid bulk, or their overlap. It does
not validate a contact angle and does not modify any solver state.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np


SCALAR_FIELDS = [
    "PhaseField",
    "Rho",
    "P",
    "BOUNDARY",
    "IsItBoundary",
    "WallGhost",
    "ReplayPhaseConsumed",
    "ReplayPhaseFromH",
    "ReplayPhaseOutOfBoundsFlag",
    "ReplayLapPhi",
    "ReplayMu",
    "ReplayRho",
    "ReplayTau",
    "ReplayPressureMoment",
    "ReplayPressureInput",
    "ReplayPressureForceScale",
    "ReplayPressurePhysicalInput",
    "ReplayTauUsed",
    "ReplayRhoForForce",
    "ReplayForceRhoRaw",
    "ReplayForceRhoEffective",
    "ReplayForceInjectionMode",
    "ReplayPressureClosureMode",
    "ReplayForceDensityClosureMode",
    "ReplayForceFixedPointMode",
    "ReplayHPreSum",
    "ReplayHPostSum",
    "ReplayHeqSum",
    "ReplayHPreMaxAbs",
    "ReplayHPostMaxAbs",
    "ReplayHeqMaxAbs",
    "ReplayFphiSum",
    "ReplayFphiMaxAbs",
    "ReplayTmp1",
    "ReplayTmp1BoundedShadow",
    "B20ProbeActive",
    "B20FphiActiveSum",
    "B20FphiActiveMaxAbs",
    "B20FphiRawPostForceSum",
    "B20FphiRawPostForceMaxAbs",
    "B20FphiPreForceSum",
    "B20FphiPreForceMaxAbs",
    "B20FphiBoundedSum",
    "B20FphiBoundedMaxAbs",
    "B20HeqActiveSum",
    "B20HeqActiveMaxAbs",
    "B20HeqRawPostForceSum",
    "B20HeqRawPostForceMaxAbs",
    "B20HeqPreForceSum",
    "B20HeqPreForceMaxAbs",
    "B20HeqBoundedSum",
    "B20HeqBoundedMaxAbs",
    "B20HPostActiveSum",
    "B20HPostActiveMaxAbs",
    "B20HPostRawPostForceSum",
    "B20HPostRawPostForceMaxAbs",
    "B20HPostPreForceSum",
    "B20HPostPreForceMaxAbs",
    "B20HPostBoundedSum",
    "B20HPostBoundedMaxAbs",
    "B20PhaseFromHActiveShadow",
    "B20PhaseFromHRawPostForceShadow",
    "B20PhaseFromHPreForceShadow",
    "B20PhaseFromHBoundedShadow",
    "B20HPostActiveOutOfBoundsFlag",
    "B20HPostRawPostForceOutOfBoundsFlag",
    "B20HPostPreForceOutOfBoundsFlag",
    "B20HPostBoundedOutOfBoundsFlag",
    "B21ProbeActive",
    "B21HPreSum",
    "B21HPreSumAbs",
    "B21HPreL2",
    "B21HPreMin",
    "B21HPreMax",
    "B21HPreMaxAbs",
    "B21HPreMaxAbsIndex",
    "B21HPrePosSum",
    "B21HPreNegSumAbs",
    "B21HPreCancellationRatio",
    "B21HPreSignedRange",
    "B21HeqSum",
    "B21HeqSumMinusC",
    "B21HeqSumAbs",
    "B21HeqL2",
    "B21HeqMin",
    "B21HeqMax",
    "B21HeqMaxAbs",
    "B21HeqMaxAbsIndex",
    "B21HeqCancellationRatio",
    "B21HeqVelocityMachShadow",
    "B21HeqVelocitySquared",
    "B21FphiSum",
    "B21FphiSumAbs",
    "B21FphiL2",
    "B21FphiMin",
    "B21FphiMax",
    "B21FphiMaxAbs",
    "B21FphiMaxAbsIndex",
    "B21FphiCancellationRatio",
    "B21Tmp1",
    "B21NormalMag",
    "B21HPostSum",
    "B21HPostSumAbs",
    "B21HPostL2",
    "B21HPostMin",
    "B21HPostMax",
    "B21HPostMaxAbs",
    "B21HPostMaxAbsIndex",
    "B21HPostPosSum",
    "B21HPostNegSumAbs",
    "B21HPostCancellationRatio",
    "B21HPostOutOfBoundsFlag",
    "B21HPostSumMinusFormula",
    "B22ProbeActive",
    "B22M0Speed",
    "B22MomentumSpeed",
    "B22PhaseAdvSpeed",
    "B22ForceOverRhoMag",
    "B22ForceRhoRaw",
    "B22ForceRhoEffective",
    "B22FpressureMag",
    "B22FsurfMag",
    "B22FmuMag",
    "B22FtotalMag",
    "B22HeqFromM0MaxAbs",
    "B22HeqFromMomentumMaxAbs",
    "B22HeqFromBoundedShadowMaxAbs",
    "B22VelocitySourceId",
    "B22VelocityMachExceededFlag",
    "ForceIterCount",
    "ForceIterResidual",
]

VECTOR_FIELDS = [
    "U",
    "GradPhi",
    "ReplayGradPhi",
    "ReplayFsurf",
    "ReplayFpressure",
    "ReplayFbody",
    "ReplayFmu",
    "ReplayFtotal",
    "ReplayForceOverRho",
    "ReplayFmuRaw",
    "ReplayFmuDelta",
    "ReplayFmuIter1",
    "ReplayFtotalIter1",
    "ReplayUPreForce",
    "ReplayUPostForce",
    "ReplayUPostIter1",
    "ReplayPhaseAdvVelocity",
    "ReplayM0",
    "ReplayVelocityHalfForce",
    "ReplayMF",
    "ReplayMomentumAfterG",
    "ReplayMomentumDeltaG",
    "ReplayFpressureNoThird",
    "ReplayFpressurePhysical",
    "B18FmuLegacy",
    "B18FmuPreForce",
    "B18FmuPostForce",
    "B18FmuForceExcluded",
    "B18FmuIncoming",
    "B18FmuCandidateDelta",
    "B18ForceOverRhoRaw",
    "B18ForceOverRhoDensityFloor",
    "B18ForceOverRhoPhaseMixture",
    "B18HVelocityLegacy",
    "B18HVelocityPreForce",
    "B18HVelocityRawPostForce",
    "B18HVelocityBoundedShadow",
    "B22M0U",
    "B22MomentumU",
    "B22PhaseAdvU",
    "B22ForceOverRho",
    "B22HalfForceU",
]

STRESS_GROUPS = {
    "StressInputNorm": [
        "ReplayStressInputXX",
        "ReplayStressInputXY",
        "ReplayStressInputXZ",
        "ReplayStressInputYY",
        "ReplayStressInputYZ",
        "ReplayStressInputZZ",
    ],
    "StressIter1Norm": [
        "ReplayStressIter1XX",
        "ReplayStressIter1XY",
        "ReplayStressIter1XZ",
        "ReplayStressIter1YY",
        "ReplayStressIter1YZ",
        "ReplayStressIter1ZZ",
    ],
    "StressPreForceNorm": [
        "ReplayStressPreForceShadowXX",
        "ReplayStressPreForceShadowXY",
        "ReplayStressPreForceShadowXZ",
        "ReplayStressPreForceShadowYY",
        "ReplayStressPreForceShadowYZ",
        "ReplayStressPreForceShadowZZ",
    ],
    "StressPostForceNorm": [
        "ReplayStressPostForceShadowXX",
        "ReplayStressPostForceShadowXY",
        "ReplayStressPostForceShadowXZ",
        "ReplayStressPostForceShadowYY",
        "ReplayStressPostForceShadowYZ",
        "ReplayStressPostForceShadowZZ",
    ],
    "StressLegacyNorm": [
        "ReplayStressXX",
        "ReplayStressXY",
        "ReplayStressXZ",
        "ReplayStressYY",
        "ReplayStressYZ",
        "ReplayStressZZ",
    ],
    "B18StressLegacyNorm": [
        "B18StressLegacyXX",
        "B18StressLegacyXY",
        "B18StressLegacyXZ",
        "B18StressLegacyYY",
        "B18StressLegacyYZ",
        "B18StressLegacyZZ",
    ],
    "B18StressPreForceNorm": [
        "B18StressPreForceXX",
        "B18StressPreForceXY",
        "B18StressPreForceXZ",
        "B18StressPreForceYY",
        "B18StressPreForceYZ",
        "B18StressPreForceZZ",
    ],
    "B18StressPostForceNorm": [
        "B18StressPostForceXX",
        "B18StressPostForceXY",
        "B18StressPostForceXZ",
        "B18StressPostForceYY",
        "B18StressPostForceYZ",
        "B18StressPostForceZZ",
    ],
    "B18StressForceExcludedNorm": [
        "B18StressForceExcludedXX",
        "B18StressForceExcludedXY",
        "B18StressForceExcludedXZ",
        "B18StressForceExcludedYY",
        "B18StressForceExcludedYZ",
        "B18StressForceExcludedZZ",
    ],
    "B18StressIncomingNorm": [
        "B18StressIncomingXX",
        "B18StressIncomingXY",
        "B18StressIncomingXZ",
        "B18StressIncomingYY",
        "B18StressIncomingYZ",
        "B18StressIncomingZZ",
    ],
}

DERIVED_VECTOR_MAG_FIELDS = {
    "GradPhiNorm": "ReplayGradPhi",
    "FsurfNorm": "ReplayFsurf",
    "FpressureNorm": "ReplayFpressure",
    "FpressureNoThirdNorm": "ReplayFpressureNoThird",
    "FpressurePhysicalNorm": "ReplayFpressurePhysical",
    "FmuNorm": "ReplayFmu",
    "FmuRawNorm": "ReplayFmuRaw",
    "FmuDeltaNorm": "ReplayFmuDelta",
    "FmuIter1Norm": "ReplayFmuIter1",
    "FtotalNorm": "ReplayFtotal",
    "FtotalIter1Norm": "ReplayFtotalIter1",
    "ForceOverRhoNorm": "ReplayForceOverRho",
    "UPreForceNorm": "ReplayUPreForce",
    "UPostForceNorm": "ReplayUPostForce",
    "UPostIter1Norm": "ReplayUPostIter1",
    "PhaseAdvVelocityNorm": "ReplayPhaseAdvVelocity",
    "VelocityNorm": "U",
    "MomentumAfterGNorm": "ReplayMomentumAfterG",
    "MomentumDeltaGNorm": "ReplayMomentumDeltaG",
    "B18FmuLegacyNorm": "B18FmuLegacy",
    "B18FmuPreForceNorm": "B18FmuPreForce",
    "B18FmuPostForceNorm": "B18FmuPostForce",
    "B18FmuForceExcludedNorm": "B18FmuForceExcluded",
    "B18FmuIncomingNorm": "B18FmuIncoming",
    "B18FmuCandidateDeltaNorm": "B18FmuCandidateDelta",
    "B18ForceOverRhoRawNorm": "B18ForceOverRhoRaw",
    "B18ForceOverRhoDensityFloorNorm": "B18ForceOverRhoDensityFloor",
    "B18ForceOverRhoPhaseMixtureNorm": "B18ForceOverRhoPhaseMixture",
    "B18HVelocityLegacyNorm": "B18HVelocityLegacy",
    "B18HVelocityPreForceNorm": "B18HVelocityPreForce",
    "B18HVelocityRawPostForceNorm": "B18HVelocityRawPostForce",
    "B18HVelocityBoundedShadowNorm": "B18HVelocityBoundedShadow",
    "B22M0UNorm": "B22M0U",
    "B22MomentumUNorm": "B22MomentumU",
    "B22PhaseAdvUNorm": "B22PhaseAdvU",
    "B22ForceOverRhoNorm": "B22ForceOverRho",
    "B22HalfForceUNorm": "B22HalfForceU",
}

TARGET_FIELDS = [
    "PhaseField",
    "ReplayPhaseFromH",
    "ReplayPhaseOutOfBoundsFlag",
    "ReplayHPostMaxAbs",
    "ReplayHeqMaxAbs",
    "ReplayFphiMaxAbs",
    "ReplayTmp1",
    "ReplayPressureInput",
    "ReplayLapPhi",
    "ReplayMu",
    "FpressureNorm",
    "FpressurePhysicalNorm",
    "GradPhiNorm",
    "FsurfNorm",
    "FmuRawNorm",
    "FmuDeltaNorm",
    "FtotalNorm",
    "ForceOverRhoNorm",
    "StressInputNorm",
    "StressIter1Norm",
    "StressPreForceNorm",
    "StressPostForceNorm",
    "StressPostMinusPreNorm",
    "StressPostOverPreRatio",
    "B18ProbeActive",
    "B18StressPreForceNorm",
    "B18StressPostForceNorm",
    "B18StressForceExcludedNorm",
    "B18StressIncomingNorm",
    "B18StressPostMinusPreNorm",
    "B18StressPostOverPre",
    "B18StressAmplificationFlag",
    "B18FmuPreForceNorm",
    "B18FmuPostForceNorm",
    "B18FmuForceExcludedNorm",
    "B18FmuCandidateDeltaNorm",
    "B18ForceOverRhoRawNorm",
    "B18ForceOverRhoDensityFloorNorm",
    "B18ForceOverRhoPhaseMixtureNorm",
    "B18HVelocityLegacyNorm",
    "B18HVelocityPreForceNorm",
    "B18HVelocityRawPostForceNorm",
    "B18HVelocityBoundedShadowNorm",
    "B18HeqLegacyMaxAbs",
    "B18HeqPreForceMaxAbs",
    "B18HeqBoundedShadowMaxAbs",
    "B20ProbeActive",
    "B20FphiActiveMaxAbs",
    "B20FphiRawPostForceMaxAbs",
    "B20FphiPreForceMaxAbs",
    "B20FphiBoundedMaxAbs",
    "B20HeqActiveMaxAbs",
    "B20HeqRawPostForceMaxAbs",
    "B20HeqPreForceMaxAbs",
    "B20HeqBoundedMaxAbs",
    "B20HPostActiveMaxAbs",
    "B20HPostRawPostForceMaxAbs",
    "B20HPostPreForceMaxAbs",
    "B20HPostBoundedMaxAbs",
    "B20PhaseFromHActiveShadow",
    "B20PhaseFromHRawPostForceShadow",
    "B20PhaseFromHPreForceShadow",
    "B20PhaseFromHBoundedShadow",
    "B20HPostActiveOutOfBoundsFlag",
    "B20HPostRawPostForceOutOfBoundsFlag",
    "B20HPostPreForceOutOfBoundsFlag",
    "B20HPostBoundedOutOfBoundsFlag",
    "B21ProbeActive",
    "B21HPreSum",
    "B21HPreSumAbs",
    "B21HPreMaxAbs",
    "B21HPreMaxAbsIndex",
    "B21HPreCancellationRatio",
    "B21HeqSum",
    "B21HeqSumMinusC",
    "B21HeqSumAbs",
    "B21HeqMaxAbs",
    "B21HeqMaxAbsIndex",
    "B21HeqCancellationRatio",
    "B21HeqVelocityMachShadow",
    "B21FphiSum",
    "B21FphiSumAbs",
    "B21FphiMaxAbs",
    "B21FphiMaxAbsIndex",
    "B21FphiCancellationRatio",
    "B21Tmp1",
    "B21NormalMag",
    "B21HPostSum",
    "B21HPostSumAbs",
    "B21HPostMaxAbs",
    "B21HPostMaxAbsIndex",
    "B21HPostCancellationRatio",
    "B21HPostOutOfBoundsFlag",
    "B21HPostSumMinusFormula",
    "B22ProbeActive",
    "B22M0Speed",
    "B22MomentumSpeed",
    "B22PhaseAdvSpeed",
    "B22M0UNorm",
    "B22MomentumUNorm",
    "B22PhaseAdvUNorm",
    "B22ForceOverRhoNorm",
    "B22ForceOverRhoMag",
    "B22HalfForceUNorm",
    "B22ForceRhoRaw",
    "B22ForceRhoEffective",
    "B22FpressureMag",
    "B22FsurfMag",
    "B22FmuMag",
    "B22FtotalMag",
    "B22HeqFromM0MaxAbs",
    "B22HeqFromMomentumMaxAbs",
    "B22HeqFromBoundedShadowMaxAbs",
    "B22VelocitySourceId",
    "B22VelocityMachExceededFlag",
    "UPostForceNorm",
    "PhaseAdvVelocityNorm",
]

COLOCATE_FIELDS = [
    "PhaseField",
    "ReplayPhaseFromH",
    "ReplayPhaseConsumed",
    "ReplayLapPhi",
    "ReplayMu",
    "Rho",
    "ReplayRho",
    "ReplayRhoForForce",
    "ReplayForceRhoRaw",
    "ReplayForceRhoEffective",
    "ReplayTau",
    "ReplayTauUsed",
    "ReplayMu",
    "GradPhiNorm",
    "FsurfNorm",
    "P",
    "ReplayPressureInput",
    "ReplayPressurePhysicalInput",
    "ReplayM0",
    "ReplayVelocityHalfForce",
    "ReplayMF",
    "ReplayMomentumAfterG",
    "ReplayMomentumDeltaG",
    "FpressureNorm",
    "FpressurePhysicalNorm",
    "FmuRawNorm",
    "FmuDeltaNorm",
    "FtotalNorm",
    "ForceOverRhoNorm",
    "StressInputNorm",
    "StressIter1Norm",
    "StressPreForceNorm",
    "StressPostForceNorm",
    "StressPostMinusPreNorm",
    "StressPostOverPreRatio",
    "B18ProbeActive",
    "B18StressPreForceNorm",
    "B18StressPostForceNorm",
    "B18StressForceExcludedNorm",
    "B18StressIncomingNorm",
    "B18StressPostMinusPreNorm",
    "B18StressPostOverPre",
    "B18StressAmplificationFlag",
    "B18FmuPreForceNorm",
    "B18FmuPostForceNorm",
    "B18FmuForceExcludedNorm",
    "B18FmuCandidateDeltaNorm",
    "B18ForceOverRhoRawNorm",
    "B18ForceOverRhoDensityFloorNorm",
    "B18ForceOverRhoPhaseMixtureNorm",
    "B18RhoDenominatorRaw",
    "B18RhoDenominatorFloor",
    "B18RhoDenominatorPhaseMix",
    "B18HVelocityLegacyNorm",
    "B18HVelocityPreForceNorm",
    "B18HVelocityRawPostForceNorm",
    "B18HVelocityBoundedShadowNorm",
    "B18HeqLegacyMaxAbs",
    "B18HeqPreForceMaxAbs",
    "B18HeqBoundedShadowMaxAbs",
    "B20ProbeActive",
    "B20FphiActiveMaxAbs",
    "B20FphiRawPostForceMaxAbs",
    "B20FphiPreForceMaxAbs",
    "B20FphiBoundedMaxAbs",
    "B20HeqActiveMaxAbs",
    "B20HeqRawPostForceMaxAbs",
    "B20HeqPreForceMaxAbs",
    "B20HeqBoundedMaxAbs",
    "B20HPostActiveMaxAbs",
    "B20HPostRawPostForceMaxAbs",
    "B20HPostPreForceMaxAbs",
    "B20HPostBoundedMaxAbs",
    "B20PhaseFromHActiveShadow",
    "B20PhaseFromHRawPostForceShadow",
    "B20PhaseFromHPreForceShadow",
    "B20PhaseFromHBoundedShadow",
    "B20HPostActiveOutOfBoundsFlag",
    "B20HPostRawPostForceOutOfBoundsFlag",
    "B20HPostPreForceOutOfBoundsFlag",
    "B20HPostBoundedOutOfBoundsFlag",
    "B21ProbeActive",
    "B21HPreSum",
    "B21HPreSumAbs",
    "B21HPreL2",
    "B21HPreMin",
    "B21HPreMax",
    "B21HPreMaxAbs",
    "B21HPreMaxAbsIndex",
    "B21HPrePosSum",
    "B21HPreNegSumAbs",
    "B21HPreCancellationRatio",
    "B21HPreSignedRange",
    "B21HeqSum",
    "B21HeqSumMinusC",
    "B21HeqSumAbs",
    "B21HeqL2",
    "B21HeqMin",
    "B21HeqMax",
    "B21HeqMaxAbs",
    "B21HeqMaxAbsIndex",
    "B21HeqCancellationRatio",
    "B21HeqVelocityMachShadow",
    "B21HeqVelocitySquared",
    "B21FphiSum",
    "B21FphiSumAbs",
    "B21FphiL2",
    "B21FphiMin",
    "B21FphiMax",
    "B21FphiMaxAbs",
    "B21FphiMaxAbsIndex",
    "B21FphiCancellationRatio",
    "B21Tmp1",
    "B21NormalMag",
    "B21HPostSum",
    "B21HPostSumAbs",
    "B21HPostL2",
    "B21HPostMin",
    "B21HPostMax",
    "B21HPostMaxAbs",
    "B21HPostMaxAbsIndex",
    "B21HPostPosSum",
    "B21HPostNegSumAbs",
    "B21HPostCancellationRatio",
    "B21HPostOutOfBoundsFlag",
    "B21HPostSumMinusFormula",
    "B22ProbeActive",
    "B22M0Speed",
    "B22MomentumSpeed",
    "B22PhaseAdvSpeed",
    "B22M0UNorm",
    "B22MomentumUNorm",
    "B22PhaseAdvUNorm",
    "B22ForceOverRhoNorm",
    "B22ForceOverRhoMag",
    "B22HalfForceUNorm",
    "B22ForceRhoRaw",
    "B22ForceRhoEffective",
    "B22FpressureMag",
    "B22FsurfMag",
    "B22FmuMag",
    "B22FtotalMag",
    "B22HeqFromM0MaxAbs",
    "B22HeqFromMomentumMaxAbs",
    "B22HeqFromBoundedShadowMaxAbs",
    "B22VelocitySourceId",
    "B22VelocityMachExceededFlag",
    "UPreForceNorm",
    "UPostForceNorm",
    "PhaseAdvVelocityNorm",
    "ReplayHPreMaxAbs",
    "ReplayHPostMaxAbs",
    "ReplayHeqMaxAbs",
    "ReplayTmp1",
    "ReplayFphiMaxAbs",
    "ForceIterCount",
    "ForceIterResidual",
]

THRESHOLDS = {
    "lap_phi_large": ("ReplayLapPhi", 1.0e3),
    "mu_large": ("ReplayMu", 1.0e3),
    "grad_phi_large": ("GradPhiNorm", 1.0e2),
    "fsurf_large": ("FsurfNorm", 1.0e3),
    "force_over_rho_large": ("ForceOverRhoNorm", 1.0e3),
    "fmu_raw_large": ("FmuRawNorm", 1.0e3),
    "stress_input_large": ("StressInputNorm", 1.0e3),
    "stress_post_large": ("StressPostForceNorm", 1.0e3),
    "b18_force_raw_large": ("B18ForceOverRhoRawNorm", 1.0e3),
    "b18_force_floor_large": ("B18ForceOverRhoDensityFloorNorm", 1.0e3),
    "b18_force_phase_mix_large": ("B18ForceOverRhoPhaseMixtureNorm", 1.0e3),
    "b18_stress_post_large": ("B18StressPostForceNorm", 1.0e3),
    "b18_stress_amp_large": ("B18StressPostOverPre", 10.0),
    "b18_fmu_post_large": ("B18FmuPostForceNorm", 1.0e3),
    "b18_heq_legacy_large": ("B18HeqLegacyMaxAbs", 1.0),
    "b18_heq_pre_large": ("B18HeqPreForceMaxAbs", 1.0),
    "b20_heq_active_large": ("B20HeqActiveMaxAbs", 1.0),
    "b20_heq_raw_post_large": ("B20HeqRawPostForceMaxAbs", 1.0),
    "b20_heq_pre_large": ("B20HeqPreForceMaxAbs", 1.0),
    "b20_heq_bounded_large": ("B20HeqBoundedMaxAbs", 1.0),
    "b20_hpost_active_large": ("B20HPostActiveMaxAbs", 1.0),
    "b20_hpost_raw_post_large": ("B20HPostRawPostForceMaxAbs", 1.0),
    "b20_hpost_pre_large": ("B20HPostPreForceMaxAbs", 1.0),
    "b20_hpost_bounded_large": ("B20HPostBoundedMaxAbs", 1.0),
    "b20_phase_active_oob": ("B20PhaseFromHActiveShadow", 1.0 + 1.0e-3),
    "b20_phase_raw_post_oob": ("B20PhaseFromHRawPostForceShadow", 1.0 + 1.0e-3),
    "b20_phase_pre_oob": ("B20PhaseFromHPreForceShadow", 1.0 + 1.0e-3),
    "b20_phase_bounded_oob": ("B20PhaseFromHBoundedShadow", 1.0 + 1.0e-3),
    "b21_hpre_cancel_large": ("B21HPreCancellationRatio", 100.0),
    "b21_hpre_max_large": ("B21HPreMaxAbs", 1.0),
    "b21_heq_cancel_large": ("B21HeqCancellationRatio", 100.0),
    "b21_hpost_cancel_large": ("B21HPostCancellationRatio", 100.0),
    "b21_heq_max_large": ("B21HeqMaxAbs", 1.0),
    "b21_hpost_max_large": ("B21HPostMaxAbs", 1.0),
    "b21_hpost_sum_oob": ("B21HPostSum", 1.0 + 1.0e-3),
    "b21_hpost_flag_oob": ("B21HPostOutOfBoundsFlag", 0.5),
    "b21_hpost_formula_residual_large": ("B21HPostSumMinusFormula", 1.0e-8),
    "b21_heq_mach_large": ("B21HeqVelocityMachShadow", 1.0),
    "b22_m0_speed_large": ("B22M0Speed", 1.0),
    "b22_momentum_speed_large": ("B22MomentumSpeed", 1.0),
    "b22_phase_adv_speed_large": ("B22PhaseAdvSpeed", 1.0),
    "b22_force_over_rho_large": ("B22ForceOverRhoMag", 1.0e3),
    "b22_force_pressure_large": ("B22FpressureMag", 1.0e3),
    "b22_force_surf_large": ("B22FsurfMag", 1.0e3),
    "b22_force_mu_large": ("B22FmuMag", 1.0e3),
    "b22_force_total_large": ("B22FtotalMag", 1.0e3),
    "b22_heq_m0_large": ("B22HeqFromM0MaxAbs", 1.0),
    "b22_heq_momentum_large": ("B22HeqFromMomentumMaxAbs", 1.0),
    "b22_heq_bounded_large": ("B22HeqFromBoundedShadowMaxAbs", 1.0),
    "b22_velocity_mach_flag": ("B22VelocityMachExceededFlag", 0.5),
    "pressure_input_large": ("ReplayPressureInput", 1.0e3),
    "pressure_force_large": ("FpressureNorm", 1.0e3),
    "phase_from_h_out_of_bounds": ("ReplayPhaseFromH", 1.0 + 1.0e-3),
    "phase_output_out_of_bounds": ("PhaseField", 1.0 + 1.0e-3),
    "tmp1_large": ("ReplayTmp1", 1.0),
    "fphi_large": ("ReplayFphiMaxAbs", 1.0),
    "hpost_large": ("ReplayHPostMaxAbs", 1.0),
}


def step_of(path: Path) -> int:
    match = re.search(r"P00_(\d+)\.vti$", path.name)
    return int(match.group(1)) if match else -1


def requested_vti_arrays() -> set[str]:
    names: set[str] = set(SCALAR_FIELDS + VECTOR_FIELDS + COLOCATE_FIELDS)
    for source in DERIVED_VECTOR_MAG_FIELDS.values():
        names.add(source)
    for sources in STRESS_GROUPS.values():
        names.update(sources)
    return names


def load_vti(path: Path) -> tuple[tuple[int, int, int], dict[str, np.ndarray]]:
    import vtk  # type: ignore
    from vtk.util.numpy_support import vtk_to_numpy  # type: ignore

    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(str(path))
    reader.UpdateInformation()
    cell_selection = reader.GetCellDataArraySelection()
    wanted = requested_vti_arrays()
    if cell_selection is not None:
        cell_selection.DisableAllArrays()
        for name in wanted:
            if cell_selection.ArrayExists(name):
                cell_selection.EnableArray(name)
    reader.Update()
    image = reader.GetOutput()
    dims = tuple(int(v) - 1 for v in image.GetDimensions())
    cell_data = image.GetCellData()
    arrays: dict[str, np.ndarray] = {}
    for idx in range(cell_data.GetNumberOfArrays()):
        arr = cell_data.GetArray(idx)
        if arr is not None:
            arrays[arr.GetName() or f"array_{idx}"] = vtk_to_numpy(arr).copy()
    return dims, arrays


def crop_to_physical(
    arr: np.ndarray, local_dims: tuple[int, int, int], physical_grid: list[int] | None
) -> np.ndarray:
    if not physical_grid:
        return np.asarray(arr)
    px, py, pz = [int(v) for v in physical_grid]
    nx, ny, nz = local_dims
    values = np.asarray(arr)
    if px > nx or py > ny or pz > nz:
        return values
    if values.shape[0] != nx * ny * nz:
        return values
    if values.ndim == 1:
        return values.reshape((nx, ny, nz))[:px, :py, :pz].reshape(-1)
    return values.reshape((nx, ny, nz, values.shape[1]))[:px, :py, :pz, :].reshape(
        -1, values.shape[1]
    )


def index_to_ijk(index: int, dims: tuple[int, int, int]) -> list[int]:
    nx, ny, _nz = dims
    i = int(index % nx)
    j = int((index // nx) % ny)
    k = int(index // (nx * ny))
    return [i, j, k]


def scalarize(arr: np.ndarray | None) -> np.ndarray | None:
    if arr is None:
        return None
    values = np.asarray(arr, dtype=float)
    if values.ndim == 2:
        return np.linalg.norm(values, axis=1)
    return values.reshape(-1)


def vector_norm(arr: np.ndarray | None) -> np.ndarray | None:
    return scalarize(arr)


def stress_norm(arrays: dict[str, np.ndarray], names: list[str]) -> np.ndarray | None:
    comps = [scalarize(arrays.get(name)) for name in names]
    if any(comp is None for comp in comps):
        return None
    stacked = np.column_stack([comp for comp in comps if comp is not None])
    weights = np.array([1.0, 2.0, 2.0, 1.0, 2.0, 1.0], dtype=float)
    return np.sqrt(np.sum(weights[None, :] * stacked * stacked, axis=1))


def add_derived_fields(arrays: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    out = dict(arrays)
    for name, source in DERIVED_VECTOR_MAG_FIELDS.items():
        values = vector_norm(arrays.get(source))
        if values is not None:
            out[name] = values
    for name, sources in STRESS_GROUPS.items():
        values = stress_norm(arrays, sources)
        if values is not None:
            out[name] = values
    pre = scalarize(out.get("StressPreForceNorm"))
    post = scalarize(out.get("StressPostForceNorm"))
    if pre is not None and post is not None:
        out["StressPostMinusPreNorm"] = np.abs(post - pre)
        out["StressPostOverPreRatio"] = post / (pre + 1.0e-300)
    b18_pre = scalarize(out.get("B18StressPreForceNorm"))
    b18_post = scalarize(out.get("B18StressPostForceNorm"))
    if b18_pre is not None and b18_post is not None:
        out["B18StressPostMinusPreNorm"] = np.abs(b18_post - b18_pre)
    return out


def read_metadata(case_dir: Path) -> dict[str, Any]:
    path = case_dir / "case_metadata.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def candidate_case_dirs(root: Path) -> list[Path]:
    if (root / "output").is_dir():
        return [root]
    case_dirs = [
        path for path in sorted(root.iterdir()) if path.is_dir() and (path / "output").is_dir()
    ]
    return case_dirs


def boundary_mask(arrays: dict[str, np.ndarray], n: int) -> np.ndarray:
    for name in ["BOUNDARY", "IsItBoundary"]:
        values = scalarize(arrays.get(name))
        if values is not None and values.size == n:
            return np.asarray(values, dtype=float) > 0.5
    return np.zeros(n, dtype=bool)


def adjacent_to_mask(mask: np.ndarray, dims: tuple[int, int, int]) -> np.ndarray:
    nx, ny, nz = dims
    grid = np.asarray(mask, dtype=bool).reshape((nx, ny, nz))
    adj = np.zeros_like(grid, dtype=bool)
    for dx, dy, dz in [
        (1, 0, 0),
        (-1, 0, 0),
        (0, 1, 0),
        (0, -1, 0),
        (0, 0, 1),
        (0, 0, -1),
    ]:
        src = [
            slice(max(0, -dx), nx - max(0, dx)),
            slice(max(0, -dy), ny - max(0, dy)),
            slice(max(0, -dz), nz - max(0, dz)),
        ]
        dst = [
            slice(max(0, dx), nx - max(0, -dx)),
            slice(max(0, dy), ny - max(0, -dy)),
            slice(max(0, dz), nz - max(0, -dz)),
        ]
        adj[tuple(dst)] |= grid[tuple(src)]
    return adj.reshape(-1)


def low_rho_mask(rho: np.ndarray | None, fluid: np.ndarray, density_l: float | None) -> np.ndarray:
    if rho is None:
        return np.zeros_like(fluid, dtype=bool)
    values = np.asarray(rho, dtype=float)
    good = fluid & np.isfinite(values)
    if not np.count_nonzero(good):
        return np.zeros_like(fluid, dtype=bool)
    threshold = float(np.nanpercentile(values[good], 0.1))
    if density_l is not None and density_l > 0:
        threshold = max(threshold, 5.0 * float(density_l))
    return good & (values <= threshold)


def make_masks(
    arrays: dict[str, np.ndarray], dims: tuple[int, int, int], metadata: dict[str, Any]
) -> dict[str, np.ndarray]:
    phase = scalarize(arrays.get("PhaseField"))
    n = dims[0] * dims[1] * dims[2]
    if phase is None:
        phase = np.full(n, np.nan)
    boundary = boundary_mask(arrays, n)
    fluid = ~boundary
    near_wall = fluid & adjacent_to_mask(boundary, dims)
    interface_strict = fluid & np.isfinite(phase) & (phase > 0.05) & (phase < 0.95)
    interface_wide = fluid & np.isfinite(phase) & (phase > 0.01) & (phase < 0.99)
    liquid_bulk = fluid & np.isfinite(phase) & (phase >= 0.95)
    gas_bulk = fluid & np.isfinite(phase) & (phase <= 0.05)
    density_l = metadata.get("density_l")
    try:
        density_l_value = float(density_l) if density_l is not None else None
    except (TypeError, ValueError):
        density_l_value = None
    rho = scalarize(arrays.get("Rho"))
    return {
        "all_cells": np.ones(n, dtype=bool),
        "fluid_all": fluid,
        "near_wall": near_wall,
        "interface_strict": interface_strict,
        "interface_wide": interface_wide,
        "near_interface_wall": near_wall & interface_wide,
        "liquid_bulk": liquid_bulk,
        "gas_bulk": gas_bulk,
        "low_rho": low_rho_mask(rho, fluid, density_l_value),
        "solid": boundary,
    }


def finite_stats(values: np.ndarray | None, mask: np.ndarray) -> dict[str, Any]:
    if values is None:
        return {
            "present": False,
            "count": int(np.count_nonzero(mask)),
            "finite_count": 0,
            "nonfinite_count": None,
            "min": None,
            "max": None,
            "mean": None,
            "p99_abs": None,
            "p999_abs": None,
            "max_abs": None,
        }
    vals = np.asarray(values, dtype=float).reshape(-1)[mask]
    finite = np.isfinite(vals)
    finite_vals = vals[finite]
    out: dict[str, Any] = {
        "present": True,
        "count": int(vals.size),
        "finite_count": int(np.count_nonzero(finite)),
        "nonfinite_count": int(vals.size - np.count_nonzero(finite)),
        "min": None,
        "max": None,
        "mean": None,
        "p99_abs": None,
        "p999_abs": None,
        "max_abs": None,
    }
    if finite_vals.size:
        abs_vals = np.abs(finite_vals)
        out.update(
            {
                "min": float(np.min(finite_vals)),
                "max": float(np.max(finite_vals)),
                "mean": float(np.mean(finite_vals)),
                "p99_abs": float(np.percentile(abs_vals, 99.0)),
                "p999_abs": float(np.percentile(abs_vals, 99.9)),
                "max_abs": float(np.max(abs_vals)),
            }
        )
    return out


def clean_value(value: Any) -> Any:
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return value
    if math.isfinite(v):
        return v
    return str(v)


def value_at(arrays: dict[str, np.ndarray], field: str, index: int) -> Any:
    arr = arrays.get(field)
    if arr is None:
        return None
    values = np.asarray(arr)
    if values.ndim == 1:
        return clean_value(values[index])
    return [clean_value(v) for v in values[index].ravel()]


def argmax_record(
    arrays: dict[str, np.ndarray],
    field: str,
    mask: np.ndarray,
    dims: tuple[int, int, int],
    masks: dict[str, np.ndarray],
) -> dict[str, Any] | None:
    values = scalarize(arrays.get(field))
    if values is None or not np.count_nonzero(mask):
        return None
    vals = np.asarray(values, dtype=float).reshape(-1)
    candidate = mask & np.isfinite(vals)
    if not np.count_nonzero(candidate):
        bad = np.flatnonzero(mask & ~np.isfinite(vals))
        if bad.size == 0:
            return None
        index = int(bad[0])
        max_abs = None
    else:
        candidate_indices = np.flatnonzero(candidate)
        local_index = int(np.argmax(np.abs(vals[candidate])))
        index = int(candidate_indices[local_index])
        max_abs = float(abs(vals[index]))
    record: dict[str, Any] = {
        "field": field,
        "flat_index": index,
        "ijk": index_to_ijk(index, dims),
        "max_abs": max_abs,
        "value": value_at(arrays, field, index),
        "mask_membership": {name: bool(mask_values[index]) for name, mask_values in masks.items()},
        "colocated": {},
    }
    for name in COLOCATE_FIELDS:
        if name in arrays:
            record["colocated"][name] = value_at(arrays, name, index)
    return record


def summarize_frame(
    case_dir: Path,
    vti_path: Path,
    metadata: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    raw_dims, raw_arrays = load_vti(vti_path)
    physical_grid = metadata.get("physical_grid")
    arrays = {
        name: crop_to_physical(values, raw_dims, physical_grid)
        for name, values in raw_arrays.items()
    }
    dims = tuple(int(v) for v in physical_grid) if physical_grid else raw_dims
    arrays = add_derived_fields(arrays)
    masks = make_masks(arrays, dims, metadata)
    step = step_of(vti_path)
    stats_rows: list[dict[str, Any]] = []
    argmax_rows: list[dict[str, Any]] = []
    for field in TARGET_FIELDS:
        values = scalarize(arrays.get(field))
        for mask_name, mask in masks.items():
            stats = finite_stats(values, mask)
            row = {
                "case": case_dir.name,
                "step": step,
                "field": field,
                "mask": mask_name,
                **stats,
            }
            stats_rows.append(row)
            record = argmax_record(arrays, field, mask, dims, masks)
            if record is not None:
                argmax_rows.append(
                    {
                        "case": case_dir.name,
                        "step": step,
                        "mask": mask_name,
                        **record,
                    }
                )
    field_presence = {
        name: name in arrays
        for name in sorted(set(SCALAR_FIELDS + VECTOR_FIELDS + TARGET_FIELDS + COLOCATE_FIELDS))
    }
    frame_summary = {
        "case": case_dir.name,
        "step": step,
        "path": str(vti_path),
        "dims": list(dims),
        "raw_dims": list(raw_dims),
        "mask_counts": {name: int(np.count_nonzero(mask)) for name, mask in masks.items()},
        "field_presence": field_presence,
    }
    return stats_rows, argmax_rows, frame_summary


def first_onsets(stats_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    onsets: list[dict[str, Any]] = []
    by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    sorted_rows = sorted(stats_rows, key=lambda row: (int(row["step"]), row["case"], row["mask"]))
    for row in sorted_rows:
        if row.get("present") and row.get("nonfinite_count") not in (None, 0):
            key = (f"nonfinite_{row['field']}", row["field"], row["mask"])
            if key not in by_key:
                by_key[key] = {
                    "trigger": key[0],
                    "field": row["field"],
                    "mask": row["mask"],
                    "case": row["case"],
                    "step": row["step"],
                    "value": row.get("nonfinite_count"),
                }
        for trigger, (field, threshold) in THRESHOLDS.items():
            if row["field"] != field or row.get("max_abs") is None:
                continue
            value = float(row["max_abs"])
            if value > threshold:
                key = (f"threshold_{trigger}", field, row["mask"])
                if key not in by_key:
                    by_key[key] = {
                        "trigger": key[0],
                        "field": field,
                        "mask": row["mask"],
                        "case": row["case"],
                        "step": row["step"],
                        "value": value,
                        "threshold": threshold,
                    }
    onsets = list(by_key.values())
    return sorted(onsets, key=lambda item: (int(item["step"]), item["trigger"], item["mask"]))


def key_summary(
    root: Path,
    stats_rows: list[dict[str, Any]],
    argmax_rows: list[dict[str, Any]],
    frame_summaries: list[dict[str, Any]],
    onsets: list[dict[str, Any]],
) -> dict[str, Any]:
    def first(trigger_prefix: str) -> dict[str, Any] | None:
        matches = [item for item in onsets if str(item["trigger"]).startswith(trigger_prefix)]
        if not matches:
            return None
        priority_masks = ["near_interface_wall", "interface_wide", "low_rho", "near_wall", "fluid_all"]
        matches = sorted(
            matches,
            key=lambda item: (
                int(item["step"]),
                priority_masks.index(item["mask"]) if item["mask"] in priority_masks else 99,
            ),
        )
        return matches[0]

    force = first("threshold_force_over_rho_large")
    fmu = first("threshold_fmu_raw_large")
    stress_post = first("threshold_stress_post_large")
    stress_input = first("threshold_stress_input_large")
    pressure = first("threshold_pressure_input_large")
    lap_phi = first("threshold_lap_phi_large")
    mu = first("threshold_mu_large")
    grad_phi = first("threshold_grad_phi_large")
    fsurf = first("threshold_fsurf_large")
    phase = first("threshold_phase_from_h_out_of_bounds")
    hpost = first("threshold_hpost_large")
    b18_force_raw = first("threshold_b18_force_raw_large")
    b18_force_floor = first("threshold_b18_force_floor_large")
    b18_force_phase_mix = first("threshold_b18_force_phase_mix_large")
    b18_stress_post = first("threshold_b18_stress_post_large")
    b18_stress_amp = first("threshold_b18_stress_amp_large")
    b18_fmu_post = first("threshold_b18_fmu_post_large")
    b18_heq_legacy = first("threshold_b18_heq_legacy_large")
    b18_heq_pre = first("threshold_b18_heq_pre_large")
    b20_heq_active = first("threshold_b20_heq_active_large")
    b20_heq_raw_post = first("threshold_b20_heq_raw_post_large")
    b20_heq_pre = first("threshold_b20_heq_pre_large")
    b20_heq_bounded = first("threshold_b20_heq_bounded_large")
    b20_hpost_active = first("threshold_b20_hpost_active_large")
    b20_hpost_raw_post = first("threshold_b20_hpost_raw_post_large")
    b20_hpost_pre = first("threshold_b20_hpost_pre_large")
    b20_hpost_bounded = first("threshold_b20_hpost_bounded_large")
    b20_phase_active = first("threshold_b20_phase_active_oob")
    b20_phase_raw_post = first("threshold_b20_phase_raw_post_oob")
    b20_phase_pre = first("threshold_b20_phase_pre_oob")
    b20_phase_bounded = first("threshold_b20_phase_bounded_oob")
    b21_hpre_cancel = first("threshold_b21_hpre_cancel_large")
    b21_hpre_max = first("threshold_b21_hpre_max_large")
    b21_heq_cancel = first("threshold_b21_heq_cancel_large")
    b21_heq_max = first("threshold_b21_heq_max_large")
    b21_heq_mach = first("threshold_b21_heq_mach_large")
    b21_hpost_cancel = first("threshold_b21_hpost_cancel_large")
    b21_hpost_max = first("threshold_b21_hpost_max_large")
    b21_hpost_sum_oob = first("threshold_b21_hpost_sum_oob")
    b21_hpost_flag_oob = first("threshold_b21_hpost_flag_oob")
    b21_hpost_formula = first("threshold_b21_hpost_formula_residual_large")
    b22_m0_speed = first("threshold_b22_m0_speed_large")
    b22_momentum_speed = first("threshold_b22_momentum_speed_large")
    b22_phase_adv_speed = first("threshold_b22_phase_adv_speed_large")
    b22_force_over_rho = first("threshold_b22_force_over_rho_large")
    b22_force_pressure = first("threshold_b22_force_pressure_large")
    b22_force_surf = first("threshold_b22_force_surf_large")
    b22_force_mu = first("threshold_b22_force_mu_large")
    b22_force_total = first("threshold_b22_force_total_large")
    b22_heq_m0 = first("threshold_b22_heq_m0_large")
    b22_heq_momentum = first("threshold_b22_heq_momentum_large")
    b22_heq_bounded = first("threshold_b22_heq_bounded_large")
    b22_mach_flag = first("threshold_b22_velocity_mach_flag")

    branch = "undetermined"
    reason = "No configured onset threshold was crossed."
    if lap_phi and (force is None or int(lap_phi["step"]) <= int(force["step"])):
        branch = "mu_laplace_first"
        reason = "LapPhi crosses its threshold before or with force-over-rho onset."
    elif mu and (force is None or int(mu["step"]) <= int(force["step"])):
        branch = "mu_first"
        reason = "Mu crosses its threshold before or with force-over-rho onset."
    elif grad_phi and (force is None or int(grad_phi["step"]) <= int(force["step"])):
        branch = "grad_phi_first"
        reason = "GradPhi crosses its threshold before or with force-over-rho onset."
    elif fsurf and (force is None or int(fsurf["step"]) <= int(force["step"])):
        branch = "surface_force_first"
        reason = "F_surf crosses its threshold before or with force-over-rho onset."
    elif force and (phase is None or int(force["step"]) <= int(phase["step"])):
        if fmu and int(fmu["step"]) <= int(force["step"]):
            branch = "fmu_force_over_rho_feedback"
            reason = "F_mu grows no later than F/rho and before or with phase loss."
        elif stress_post and int(stress_post["step"]) <= int(force["step"]):
            branch = "stress_timelevel_or_fixed_point_feedback"
            reason = "Post-force stress grows no later than F/rho and before or with phase loss."
        else:
            branch = "force_over_rho_density_closure"
            reason = "F/rho crosses its threshold before or with phase loss without an earlier F_mu marker."
    elif phase and (force is None or int(phase["step"]) < int(force["step"])):
        branch = "phase_update_or_h_advection_first"
        reason = "PhaseFromH leaves bounds before configured force-over-rho onset."
    if pressure and force and int(pressure["step"]) < int(force["step"]):
        branch = "pressure_closure_first"
        reason = "Pressure input crosses threshold before force-over-rho onset."
    if hpost and phase and int(hpost["step"]) < int(phase["step"]):
        branch = "h_population_update_first"
        reason = "HPost magnitude crosses threshold before PhaseFromH leaves bounds."

    b18_branch = "not_available"
    b18_reason = "B18 fields were not present or did not cross configured thresholds."
    if b18_stress_post and (
        b18_force_raw is None or int(b18_stress_post["step"]) <= int(b18_force_raw["step"])
    ):
        b18_branch = "stress_timelevel_shadow"
        b18_reason = "B18 post-force stress crosses before or with raw F/rho."
    if b18_stress_amp and (
        b18_stress_post is None or int(b18_stress_amp["step"]) <= int(b18_stress_post["step"])
    ):
        b18_branch = "stress_amplification_shadow"
        b18_reason = "B18 post/pre stress amplification crosses first."
    if b18_force_raw and (
        b18_stress_post is None or int(b18_force_raw["step"]) < int(b18_stress_post["step"])
    ):
        b18_branch = "force_over_rho_raw_denominator_shadow"
        b18_reason = "B18 raw F/rho crosses before post-force stress."
    if b18_force_raw and not b18_force_floor:
        b18_branch = "force_density_floor_relief_shadow"
        b18_reason = "B18 raw F/rho crosses, while density-floor shadow does not cross."
    if b18_force_raw and not b18_force_phase_mix:
        b18_branch = "phase_mixture_denominator_relief_shadow"
        b18_reason = "B18 raw F/rho crosses, while phase-mixture denominator shadow does not cross."
    if b18_heq_legacy and (b18_heq_pre is None or int(b18_heq_legacy["step"]) < int(b18_heq_pre["step"])):
        b18_branch = "h_velocity_input_shadow"
        b18_reason = "B18 legacy h-equilibrium shadow crosses earlier than pre-force h-equilibrium shadow."

    b20_branch = "not_available"
    b20_reason = "B20 fields were not present or did not cross configured thresholds."
    if b20_hpost_active:
        b20_branch = "active_hpost_shadow_unbounded"
        b20_reason = "B20 active hpost shadow crosses the configured threshold."
    if b20_phase_active:
        b20_branch = "active_phase_from_h_shadow_out_of_bounds"
        b20_reason = "B20 active PhaseFromH shadow leaves the physical phase interval."
    if b20_phase_active and b20_phase_raw_post and b20_phase_pre:
        raw_step = int(b20_phase_raw_post["step"])
        pre_step = int(b20_phase_pre["step"])
        active_step = int(b20_phase_active["step"])
        if raw_step <= active_step and raw_step < pre_step:
            b20_branch = "raw_post_force_h_velocity_shadow_first"
            b20_reason = "Raw post-force h-update candidate leaves bounds earlier than pre-force candidate."
        elif pre_step <= active_step and pre_step < raw_step:
            b20_branch = "pre_force_h_velocity_shadow_first"
            b20_reason = "Pre-force h-update candidate leaves bounds earlier than raw post-force candidate."
        elif raw_step == pre_step == active_step:
            b20_branch = "h_update_common_source"
            b20_reason = "Raw post-force and pre-force h-update candidates leave bounds at the same step."
    if b20_phase_active and not b20_phase_bounded:
        b20_branch = "bounded_velocity_relief_shadow"
        b20_reason = "B20 active PhaseFromH leaves bounds while bounded-velocity candidate does not."
    if b20_heq_active and (b20_hpost_active is None or int(b20_heq_active["step"]) <= int(b20_hpost_active["step"])):
        b20_branch = "heq_candidate_large_before_hpost"
        b20_reason = "B20 active heq shadow crosses before or with hpost."

    def onset_step(item: dict[str, Any] | None) -> int | None:
        if item is None:
            return None
        return int(item["step"])

    def earlier_or_equal(
        item: dict[str, Any] | None, *others: dict[str, Any] | None
    ) -> bool:
        item_step = onset_step(item)
        if item_step is None:
            return False
        other_steps = [step for step in (onset_step(other) for other in others) if step is not None]
        return not other_steps or item_step <= min(other_steps)

    b21_branch = "not_available"
    b21_reason = "B21 fields were not present or did not cross configured thresholds."
    if b21_hpost_formula:
        b21_branch = "hpost_formula_consistency_or_template_indexing"
        b21_reason = (
            "B21 hpost sum disagrees with the scalar sum of the same update formula; "
            "check generated R-template indexing before changing physics."
        )
    if earlier_or_equal(b21_hpre_max, b21_heq_max, b21_hpost_max):
        b21_branch = "incoming_h_population_streaming_history_contamination"
        b21_reason = "B21 HPre population amplitude is already large before or with heq/hpost growth."
    elif earlier_or_equal(b21_hpre_cancel, b21_heq_cancel, b21_hpost_cancel):
        b21_branch = "incoming_h_population_cancellation"
        b21_reason = "B21 HPre has strong signed cancellation before or with heq/hpost cancellation."
    elif earlier_or_equal(b21_heq_mach, b21_heq_max, b21_hpost_max):
        b21_branch = "phase_advection_velocity_mach_first"
        b21_reason = "B21 heq Mach shadow crosses first, implicating the phase-advection velocity."
    elif earlier_or_equal(b21_heq_max, b21_hpost_max, b21_hpost_sum_oob, b21_hpost_flag_oob):
        b21_branch = "heq_population_large_before_hpost"
        b21_reason = "B21 heq population amplitude crosses before or with hpost/phase-sum failure."
    elif earlier_or_equal(b21_hpost_max, b21_hpost_sum_oob, b21_hpost_flag_oob):
        b21_branch = "hpost_population_update_amplification"
        b21_reason = "B21 hpost population amplitude crosses before or with the hpost phase-sum failure."
    elif b21_hpost_sum_oob or b21_hpost_flag_oob:
        b21_branch = "hpost_sum_out_of_bounds_without_large_population_marker"
        b21_reason = "B21 hpost phase sum leaves bounds without an earlier configured population-amplitude onset."
    elif b21_heq_cancel:
        b21_branch = "heq_cancellation_without_amplitude_threshold"
        b21_reason = "B21 heq cancellation threshold crosses without the max-abs threshold crossing."

    b22_branch = "not_available"
    b22_reason = "B22 fields were not present or did not cross configured thresholds."
    if b22_m0_speed and earlier_or_equal(b22_m0_speed, b22_momentum_speed, b22_phase_adv_speed):
        b22_branch = "m0_velocity_first"
        b22_reason = "B22 m0/pre-force velocity crosses before or with post-force and active phase-advection velocity."
    elif b22_momentum_speed and earlier_or_equal(b22_momentum_speed, b22_phase_adv_speed):
        b22_branch = "post_force_momentum_velocity_first"
        b22_reason = "B22 post-force momentum velocity crosses before or with active phase-advection velocity."
    elif b22_phase_adv_speed:
        b22_branch = "phase_advection_velocity_selected_source_first"
        b22_reason = "B22 active phase-advection velocity crosses the velocity threshold."
    if b22_force_over_rho and (
        b22_m0_speed is None or int(b22_force_over_rho["step"]) <= int(b22_m0_speed["step"])
    ):
        b22_branch = "force_over_rho_feeds_velocity"
        b22_reason = "B22 F/rho crosses no later than m0 velocity; inspect denominator and force split."
    if b22_force_mu and (
        b22_force_over_rho is None or int(b22_force_mu["step"]) <= int(b22_force_over_rho["step"])
    ):
        b22_branch = "fmu_force_component_first"
        b22_reason = "B22 F_mu magnitude crosses before or with F/rho."
    if b22_force_pressure and (
        b22_force_over_rho is None or int(b22_force_pressure["step"]) <= int(b22_force_over_rho["step"])
    ):
        b22_branch = "pressure_force_component_first"
        b22_reason = "B22 pressure-force magnitude crosses before or with F/rho."
    if b22_heq_m0 and (
        b22_m0_speed is None or int(b22_heq_m0["step"]) <= int(b22_m0_speed["step"])
    ):
        b22_branch = "heq_from_m0_large_without_prior_m0_threshold"
        b22_reason = "B22 m0-based heq is large without a prior configured m0-speed crossing; audit heq formula/scaling."
    if b22_heq_momentum and (
        b22_momentum_speed is None or int(b22_heq_momentum["step"]) <= int(b22_momentum_speed["step"])
    ):
        b22_branch = "heq_from_post_force_large_without_prior_momentum_threshold"
        b22_reason = "B22 post-force heq is large without a prior configured post-force velocity crossing."
    if (b22_heq_m0 or b22_heq_momentum) and not b22_heq_bounded:
        b22_branch = "bounded_velocity_relief_shadow"
        b22_reason = "B22 unbounded heq candidate crosses while bounded-velocity heq candidate does not."

    return {
        "root": str(root),
        "status": "B17_B18_B20_B21_DIAGNOSTIC_COMPLETE",
        "claim_limit": "diagnostic-only; not contact-angle validation and not a solver fix",
        "frame_count": len(frame_summaries),
        "stat_row_count": len(stats_rows),
        "argmax_record_count": len(argmax_rows),
        "first_force_over_rho_onset": force,
        "first_fmu_raw_onset": fmu,
        "first_stress_post_onset": stress_post,
        "first_stress_input_onset": stress_input,
        "first_pressure_input_onset": pressure,
        "first_lap_phi_onset": lap_phi,
        "first_mu_onset": mu,
        "first_grad_phi_onset": grad_phi,
        "first_fsurf_onset": fsurf,
        "first_phase_from_h_onset": phase,
        "first_hpost_onset": hpost,
        "first_b18_force_raw_onset": b18_force_raw,
        "first_b18_force_floor_onset": b18_force_floor,
        "first_b18_force_phase_mix_onset": b18_force_phase_mix,
        "first_b18_stress_post_onset": b18_stress_post,
        "first_b18_stress_amp_onset": b18_stress_amp,
        "first_b18_fmu_post_onset": b18_fmu_post,
        "first_b18_heq_legacy_onset": b18_heq_legacy,
        "first_b18_heq_pre_onset": b18_heq_pre,
        "first_b20_heq_active_onset": b20_heq_active,
        "first_b20_heq_raw_post_onset": b20_heq_raw_post,
        "first_b20_heq_pre_onset": b20_heq_pre,
        "first_b20_heq_bounded_onset": b20_heq_bounded,
        "first_b20_hpost_active_onset": b20_hpost_active,
        "first_b20_hpost_raw_post_onset": b20_hpost_raw_post,
        "first_b20_hpost_pre_onset": b20_hpost_pre,
        "first_b20_hpost_bounded_onset": b20_hpost_bounded,
        "first_b20_phase_active_onset": b20_phase_active,
        "first_b20_phase_raw_post_onset": b20_phase_raw_post,
        "first_b20_phase_pre_onset": b20_phase_pre,
        "first_b20_phase_bounded_onset": b20_phase_bounded,
        "first_b21_hpre_cancel_onset": b21_hpre_cancel,
        "first_b21_hpre_max_onset": b21_hpre_max,
        "first_b21_heq_cancel_onset": b21_heq_cancel,
        "first_b21_heq_max_onset": b21_heq_max,
        "first_b21_heq_mach_onset": b21_heq_mach,
        "first_b21_hpost_cancel_onset": b21_hpost_cancel,
        "first_b21_hpost_max_onset": b21_hpost_max,
        "first_b21_hpost_sum_oob_onset": b21_hpost_sum_oob,
        "first_b21_hpost_flag_oob_onset": b21_hpost_flag_oob,
        "first_b21_hpost_formula_residual_onset": b21_hpost_formula,
        "first_b22_m0_speed_onset": b22_m0_speed,
        "first_b22_momentum_speed_onset": b22_momentum_speed,
        "first_b22_phase_adv_speed_onset": b22_phase_adv_speed,
        "first_b22_force_over_rho_onset": b22_force_over_rho,
        "first_b22_force_pressure_onset": b22_force_pressure,
        "first_b22_force_surf_onset": b22_force_surf,
        "first_b22_force_mu_onset": b22_force_mu,
        "first_b22_force_total_onset": b22_force_total,
        "first_b22_heq_m0_onset": b22_heq_m0,
        "first_b22_heq_momentum_onset": b22_heq_momentum,
        "first_b22_heq_bounded_onset": b22_heq_bounded,
        "first_b22_velocity_mach_flag_onset": b22_mach_flag,
        "primary_branch": branch,
        "primary_branch_reason": reason,
        "b18_primary_branch": b18_branch,
        "b18_primary_branch_reason": b18_reason,
        "b20_primary_branch": b20_branch,
        "b20_primary_branch_reason": b20_reason,
        "b21_primary_branch": b21_branch,
        "b21_primary_branch_reason": b21_reason,
        "b22_primary_branch": b22_branch,
        "b22_primary_branch_reason": b22_reason,
        "notes": [
            "Use mask-specific argmax records before changing solver physics.",
            "If high values localize in low_rho/gas_bulk, force-density closure is implicated.",
            "If stress_post exceeds stress_pre at the same argmax before phase loss, stress time-level is implicated.",
            "If LapPhi or Mu leads, audit calcMu and near-wall Laplace before changing force insertion.",
            "If GradPhi or Fsurf leads, audit calcGradPhi and F_surf scaling before changing F_mu.",
            "B18 force-excluded stress is a diagnostic shadow candidate, not a physics write path.",
            "If phase/h fields lead force diagnostics, return to h update and phase-advection timeline.",
            "B20 bounded-velocity h-update fields are shadow diagnostics only, not a physics limiter.",
            "B21 h-population fields are shadow diagnostics only and must not be interpreted as a solver write path.",
            "B22 velocity-producer fields are shadow diagnostics only and must not be interpreted as a solver write path.",
            "If B21 hpost formula residual appears first, audit generated TCLB indexing before changing the physical model.",
            "If B21 HPre is already large, inspect AddDensity streaming/history before modifying wetting or force closures.",
            "If B22 m0 velocity is already large, inspect g AddDensity streaming/history and MRT force insertion before modifying wetting.",
            "If B22 post-force velocity is large but m0 is not, inspect F/rho denominator and force components before modifying h equilibrium.",
        ],
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Case directory or root containing case directories.")
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--case-glob", default="*")
    parser.add_argument("--prefix", default="b17", help="Output filename prefix, e.g. b17 or b18.")
    args = parser.parse_args()

    root = args.root.resolve()
    out_dir = (args.out_dir or root).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    case_dirs = [path for path in candidate_case_dirs(root) if path.match(args.case_glob)]
    if not case_dirs:
        raise SystemExit(f"No case directories with output/ found under {root}")

    all_stats: list[dict[str, Any]] = []
    all_argmax: list[dict[str, Any]] = []
    frame_summaries: list[dict[str, Any]] = []
    pvti_only: list[str] = []
    for case_dir in case_dirs:
        metadata = read_metadata(case_dir)
        output = case_dir / "output"
        vtis = sorted(output.glob("case_VTK_P00_*.vti"), key=step_of)
        if not vtis and list(output.glob("case_VTK_P00_*.pvti")):
            pvti_only.append(str(case_dir))
            continue
        for vti_path in vtis:
            stats_rows, argmax_rows, frame_summary = summarize_frame(case_dir, vti_path, metadata)
            all_stats.extend(stats_rows)
            all_argmax.extend(argmax_rows)
            frame_summaries.append(frame_summary)

    if pvti_only and not frame_summaries:
        raise SystemExit(
            "Only .pvti shells were found; .vti pieces are required for B17 argmax diagnostics: "
            + ", ".join(pvti_only)
        )

    onsets = first_onsets(all_stats)
    summary = key_summary(root, all_stats, all_argmax, frame_summaries, onsets)
    summary["pvti_only_cases_skipped"] = pvti_only
    summary["frame_summaries"] = frame_summaries

    prefix = args.prefix
    write_csv(out_dir / f"{prefix}_mask_stats.csv", all_stats)
    (out_dir / f"{prefix}_argmax_trace.json").write_text(
        json.dumps(all_argmax, indent=2, sort_keys=True), encoding="utf-8"
    )
    (out_dir / f"{prefix}_first_onset.json").write_text(
        json.dumps(onsets, indent=2, sort_keys=True), encoding="utf-8"
    )
    (out_dir / f"{prefix}_field_presence.json").write_text(
        json.dumps(frame_summaries, indent=2, sort_keys=True), encoding="utf-8"
    )
    (out_dir / f"{prefix}_key_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in summary.items() if k != "frame_summaries"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
