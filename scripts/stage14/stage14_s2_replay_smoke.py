#!/usr/bin/env python3
"""S2 replay smoke for TCLB phase-field time-level diagnostics.

This is a small runtime gate, not a contact-angle validation. It checks that
the S1 Replay* fields are produced by the compiled TCLB binary and can be read
from VTI outputs for steps 0-10. Full C-to-TCLB numerical replay is a later
step built on these artifacts.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


DEFAULT_BIN = (
    "/home/yuan/src/TCLB_lbm2026_compile_lane/"
    "CLB/d3q27_pf_velocity_q27_geometric/main"
)
DEFAULT_ROOT = "/mnt/usb1t/RUNS/runs/stage14_s2_replay_smoke_20260623"

VTK_FIELDS = ",".join(
    [
        "PhaseField",
        "Rho",
        "U",
        "P",
        "BOUNDARY",
        "IsItBoundary",
        "WallGhost",
        "WallGhostRaw",
        "WallGhostClamped",
        "WallGhostClampHit",
        "WettingPathId",
        "LocalRadAngle",
        "WallH",
        "AnalyticWallNormal",
        "AnalyticFlag",
        "GradPhi",
        "ForceIterResidual",
        "ForceIterCount",
        "MassCorrectionApplied",
        "PhaseStencilGhostUseCount",
        "PhaseStencilFallbackCount",
        "PhaseStencilMidpointFallbackCount",
        "ReplayPhaseConsumed",
        "ReplayPhaseFromH",
        "ReplayLapPhi",
        "ReplayMu",
        "ReplayGradPhi",
        "ReplayFsurf",
        "ReplayFpressure",
        "ReplayFbody",
        "ReplayFmu",
        "ReplayFtotal",
        "ReplayRho",
        "ReplayTau",
        "ReplayPressureMoment",
        "ReplayUPreForce",
        "ReplayUPostForce",
        "ReplayPhaseAdvVelocity",
        "ReplayForceOverRho",
        "ReplayFmuIter1",
        "ReplayFtotalIter1",
        "ReplayUPostIter1",
        "ReplayNormal",
        "ReplayStressXX",
        "ReplayStressXY",
        "ReplayStressXZ",
        "ReplayStressYY",
        "ReplayStressYZ",
        "ReplayStressZZ",
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
        "ReplayPhaseOutOfBoundsFlag",
        "ReplayM0",
        "ReplayVelocityHalfForce",
        "ReplayMF",
        "ReplayMomentumAfterG",
        "ReplayMomentumDeltaG",
        "ReplayPressureInput",
        "ReplayPressureForceScale",
        "ReplayPressurePhysicalInput",
        "ReplayFpressureNoThird",
        "ReplayFpressurePhysical",
        "ReplayStressInputXX",
        "ReplayStressInputXY",
        "ReplayStressInputXZ",
        "ReplayStressInputYY",
        "ReplayStressInputYZ",
        "ReplayStressInputZZ",
        "ReplayStressIter1XX",
        "ReplayStressIter1XY",
        "ReplayStressIter1XZ",
        "ReplayStressIter1YY",
        "ReplayStressIter1YZ",
        "ReplayStressIter1ZZ",
        "ReplayStressPreForceShadowXX",
        "ReplayStressPreForceShadowXY",
        "ReplayStressPreForceShadowXZ",
        "ReplayStressPreForceShadowYY",
        "ReplayStressPreForceShadowYZ",
        "ReplayStressPreForceShadowZZ",
        "ReplayStressPostForceShadowXX",
        "ReplayStressPostForceShadowXY",
        "ReplayStressPostForceShadowXZ",
        "ReplayStressPostForceShadowYY",
        "ReplayStressPostForceShadowYZ",
        "ReplayStressPostForceShadowZZ",
        "ReplayFmuRaw",
        "ReplayFmuDelta",
        "ReplayTauUsed",
        "ReplayRhoForForce",
        "ReplayForceInjectionMode",
        "ReplayPressureClosureMode",
        "ReplayForceDensityClosureMode",
        "ReplayForceFixedPointMode",
        "ReplayFmuStressClosureMode",
        "ReplayForceRhoRaw",
    "ReplayForceRhoEffective",
    "ReplayFmuStressClosureMode",
    "B18ProbeActive",
        "B18StressLegacyXX",
        "B18StressLegacyXY",
        "B18StressLegacyXZ",
        "B18StressLegacyYY",
        "B18StressLegacyYZ",
        "B18StressLegacyZZ",
        "B18StressPreForceXX",
        "B18StressPreForceXY",
        "B18StressPreForceXZ",
        "B18StressPreForceYY",
        "B18StressPreForceYZ",
        "B18StressPreForceZZ",
        "B18StressPostForceXX",
        "B18StressPostForceXY",
        "B18StressPostForceXZ",
        "B18StressPostForceYY",
        "B18StressPostForceYZ",
        "B18StressPostForceZZ",
        "B18StressForceExcludedXX",
        "B18StressForceExcludedXY",
        "B18StressForceExcludedXZ",
        "B18StressForceExcludedYY",
        "B18StressForceExcludedYZ",
        "B18StressForceExcludedZZ",
        "B18StressIncomingXX",
        "B18StressIncomingXY",
        "B18StressIncomingXZ",
        "B18StressIncomingYY",
        "B18StressIncomingYZ",
        "B18StressIncomingZZ",
        "B18StressPostOverPre",
        "B18StressAmplificationFlag",
        "B18FmuLegacy",
        "B18FmuPreForce",
        "B18FmuPostForce",
        "B18FmuForceExcluded",
        "B18FmuIncoming",
        "B18FmuCandidateDelta",
        "B18ForceOverRhoRaw",
        "B18ForceOverRhoDensityFloor",
        "B18ForceOverRhoPhaseMixture",
        "B18RhoDenominatorRaw",
        "B18RhoDenominatorFloor",
        "B18RhoDenominatorPhaseMix",
        "B18HVelocityLegacy",
        "B18HVelocityPreForce",
        "B18HVelocityRawPostForce",
        "B18HVelocityBoundedShadow",
        "B18HeqLegacyMaxAbs",
        "B18HeqPreForceMaxAbs",
        "B18HeqBoundedShadowMaxAbs",
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
    ]
)

VTK_FIELDS_MINIMAL = ",".join(
    [
        "PhaseField",
        "Rho",
        "U",
        "BOUNDARY",
        "IsItBoundary",
        "GradPhi",
        "ForceIterResidual",
        "ForceIterCount",
        "ReplayPhaseConsumed",
        "ReplayPhaseFromH",
        "ReplayGradPhi",
        "ReplayFpressure",
        "ReplayFmu",
        "ReplayFtotal",
        "ReplayRho",
        "ReplayTau",
        "ReplayUPreForce",
        "ReplayUPostForce",
        "ReplayPhaseAdvVelocity",
        "ReplayForceOverRho",
        "ReplayHPreMaxAbs",
        "ReplayHPostMaxAbs",
        "ReplayHeqMaxAbs",
        "ReplayFphiMaxAbs",
        "ReplayTmp1",
        "ReplayPhaseOutOfBoundsFlag",
        "ReplayPressureInput",
        "ReplayStressPreForceShadowXX",
        "ReplayStressPreForceShadowXY",
        "ReplayStressPreForceShadowXZ",
        "ReplayStressPreForceShadowYY",
        "ReplayStressPreForceShadowYZ",
        "ReplayStressPreForceShadowZZ",
        "ReplayStressPostForceShadowXX",
        "ReplayStressPostForceShadowXY",
        "ReplayStressPostForceShadowXZ",
        "ReplayStressPostForceShadowYY",
        "ReplayStressPostForceShadowYZ",
        "ReplayStressPostForceShadowZZ",
        "ReplayFmuRaw",
        "ReplayFmuDelta",
        "ReplayForceRhoRaw",
        "ReplayForceRhoEffective",
        "B18ProbeActive",
        "B18StressPreForceXX",
        "B18StressPreForceXY",
        "B18StressPreForceXZ",
        "B18StressPreForceYY",
        "B18StressPreForceYZ",
        "B18StressPreForceZZ",
        "B18StressPostForceXX",
        "B18StressPostForceXY",
        "B18StressPostForceXZ",
        "B18StressPostForceYY",
        "B18StressPostForceYZ",
        "B18StressPostForceZZ",
        "B18StressPostOverPre",
        "B18StressAmplificationFlag",
        "B18FmuPostForce",
        "B18ForceOverRhoRaw",
        "B18ForceOverRhoDensityFloor",
        "B18ForceOverRhoPhaseMixture",
        "B18RhoDenominatorRaw",
        "B18RhoDenominatorFloor",
        "B18RhoDenominatorPhaseMix",
        "B18HVelocityLegacy",
        "B18HVelocityPreForce",
        "B18HVelocityRawPostForce",
        "B18HVelocityBoundedShadow",
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
        "B22M0U",
        "B22MomentumU",
        "B22PhaseAdvU",
        "B22M0Speed",
        "B22MomentumSpeed",
        "B22PhaseAdvSpeed",
        "B22ForceOverRho",
        "B22ForceOverRhoMag",
        "B22ForceRhoRaw",
        "B22ForceRhoEffective",
        "B22HalfForceU",
        "B22FpressureMag",
        "B22FsurfMag",
        "B22FmuMag",
        "B22FtotalMag",
        "B22HeqFromM0MaxAbs",
        "B22HeqFromMomentumMaxAbs",
        "B22HeqFromBoundedShadowMaxAbs",
        "B22VelocitySourceId",
        "B22VelocityMachExceededFlag",
    ]
)

VTK_FIELDS_B21 = ",".join(
    [
        "PhaseField",
        "Rho",
        "U",
        "BOUNDARY",
        "IsItBoundary",
        "ReplayPhaseFromH",
        "ReplayPhaseAdvVelocity",
        "ReplayForceOverRho",
        "ReplayHPreMaxAbs",
        "ReplayHPostMaxAbs",
        "ReplayHeqMaxAbs",
        "ReplayFphiMaxAbs",
        "ReplayTmp1",
        "ReplayPhaseOutOfBoundsFlag",
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
    ]
)

VTK_FIELDS_B22 = ",".join(
    [
        "PhaseField",
        "Rho",
        "U",
        "BOUNDARY",
        "IsItBoundary",
        "ReplayPhaseFromH",
        "ReplayPhaseAdvVelocity",
        "ReplayForceOverRho",
        "ReplayFpressure",
        "ReplayFsurf",
        "ReplayFmu",
        "ReplayFtotal",
        "ReplayHPostMaxAbs",
        "ReplayHeqMaxAbs",
        "B21ProbeActive",
        "B21HeqVelocityMachShadow",
        "B21HeqMaxAbs",
        "B21HPostMaxAbs",
        "B22ProbeActive",
        "B22M0U",
        "B22MomentumU",
        "B22PhaseAdvU",
        "B22M0Speed",
        "B22MomentumSpeed",
        "B22PhaseAdvSpeed",
        "B22ForceOverRho",
        "B22ForceOverRhoMag",
        "B22ForceRhoRaw",
        "B22ForceRhoEffective",
        "B22HalfForceU",
        "B22FpressureMag",
        "B22FsurfMag",
        "B22FmuMag",
        "B22FtotalMag",
        "B22HeqFromM0MaxAbs",
        "B22HeqFromMomentumMaxAbs",
        "B22HeqFromBoundedShadowMaxAbs",
        "B22VelocitySourceId",
        "B22VelocityMachExceededFlag",
    ]
)

B26_REQUIRED_FIELDS = [
    "PhaseField",
    "Rho",
    "BOUNDARY",
    "IsItBoundary",
    "ReplayPhaseFromH",
    "ReplayPhaseAdvVelocity",
    "ReplayForceOverRho",
    "ReplayForceRhoRaw",
    "ReplayForceRhoEffective",
    "ReplayFmuRaw",
    "ReplayFmuDelta",
    "ReplayPressureClosureMode",
    "ReplayForceDensityClosureMode",
    "ReplayForceFixedPointMode",
    "B18ProbeActive",
    "B18StressPostOverPre",
    "B18ForceOverRhoRaw",
    "B18ForceOverRhoDensityFloor",
    "B18ForceOverRhoPhaseMixture",
    "B18RhoDenominatorRaw",
    "B18RhoDenominatorFloor",
    "B18RhoDenominatorPhaseMix",
    "B20ProbeActive",
    "B20FphiActiveMaxAbs",
    "B20HPostActiveMaxAbs",
    "B20PhaseFromHActiveShadow",
    "B21ProbeActive",
    "B21HeqVelocityMachShadow",
    "B21HeqMaxAbs",
    "B21HPostMaxAbs",
    "B22ProbeActive",
    "B22M0U",
    "B22MomentumU",
    "B22PhaseAdvU",
    "B22M0Speed",
    "B22MomentumSpeed",
    "B22PhaseAdvSpeed",
    "B22ForceOverRho",
    "B22ForceOverRhoMag",
    "B22ForceRhoRaw",
    "B22ForceRhoEffective",
    "B22HalfForceU",
    "B22FpressureMag",
    "B22FsurfMag",
    "B22FmuMag",
    "B22FtotalMag",
    "B22HeqFromM0MaxAbs",
    "B22HeqFromMomentumMaxAbs",
    "B22HeqFromBoundedShadowMaxAbs",
    "B22VelocitySourceId",
    "B22VelocityMachExceededFlag",
]

VTK_FIELDS_B26 = ",".join(
    dict.fromkeys(VTK_FIELDS.split(",") + VTK_FIELDS_B22.split(","))
)

B27_STRESS_REQUIRED_FIELDS = [
    "PhaseField",
    "Rho",
    "BOUNDARY",
    "IsItBoundary",
    "ReplayPhaseFromH",
    "ReplayForceOverRho",
    "ReplayForceRhoRaw",
    "ReplayForceRhoEffective",
    "ReplayFmuRaw",
    "ReplayFmuDelta",
    "B18ProbeActive",
    "B18StressPreForceXX",
    "B18StressPreForceXY",
    "B18StressPreForceXZ",
    "B18StressPreForceYY",
    "B18StressPreForceYZ",
    "B18StressPreForceZZ",
    "B18StressPostForceXX",
    "B18StressPostForceXY",
    "B18StressPostForceXZ",
    "B18StressPostForceYY",
    "B18StressPostForceYZ",
    "B18StressPostForceZZ",
    "B18StressPostOverPre",
    "B18StressAmplificationFlag",
    "B18FmuPreForce",
    "B18FmuPostForce",
    "B18FmuForceExcluded",
    "B18FmuCandidateDelta",
    "B18ForceOverRhoRaw",
    "B18ForceOverRhoDensityFloor",
    "B18ForceOverRhoPhaseMixture",
    "B18RhoDenominatorRaw",
    "B18RhoDenominatorFloor",
    "B18RhoDenominatorPhaseMix",
    "B21ProbeActive",
    "B21HeqVelocityMachShadow",
    "B21HeqMaxAbs",
    "B21HPostMaxAbs",
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
]

VTK_FIELDS_B27_STRESS = ",".join(B27_STRESS_REQUIRED_FIELDS)

B33_LEDGER_REQUIRED_FIELDS = list(
    dict.fromkeys(
        [
            "PhaseField",
            "Rho",
            "P",
            "BOUNDARY",
            "IsItBoundary",
            "ReplayPhaseConsumed",
            "ReplayPhaseFromH",
            "ReplayPhaseOutOfBoundsFlag",
            "ReplayLapPhi",
            "ReplayMu",
            "ReplayGradPhi",
            "ReplayFsurf",
            "ReplayFpressure",
            "ReplayFbody",
            "ReplayFmu",
            "ReplayFmuRaw",
            "ReplayFmuDelta",
            "ReplayFtotal",
            "ReplayForceOverRho",
            "ReplayRho",
            "ReplayTau",
            "ReplayTauUsed",
            "ReplayRhoForForce",
            "ReplayForceRhoRaw",
            "ReplayForceRhoEffective",
            "ReplayPressureMoment",
            "ReplayPressureInput",
            "ReplayPressurePhysicalInput",
            "ReplayFpressureNoThird",
            "ReplayFpressurePhysical",
            "ReplayUPreForce",
            "ReplayUPostForce",
            "ReplayPhaseAdvVelocity",
            "ReplayM0",
            "ReplayVelocityHalfForce",
            "ReplayMF",
            "ReplayMomentumAfterG",
            "ReplayMomentumDeltaG",
            "ReplayStressInputXX",
            "ReplayStressInputXY",
            "ReplayStressInputXZ",
            "ReplayStressInputYY",
            "ReplayStressInputYZ",
            "ReplayStressInputZZ",
            "ReplayStressIter1XX",
            "ReplayStressIter1XY",
            "ReplayStressIter1XZ",
            "ReplayStressIter1YY",
            "ReplayStressIter1YZ",
            "ReplayStressIter1ZZ",
            "ReplayStressPreForceShadowXX",
            "ReplayStressPreForceShadowXY",
            "ReplayStressPreForceShadowXZ",
            "ReplayStressPreForceShadowYY",
            "ReplayStressPreForceShadowYZ",
            "ReplayStressPreForceShadowZZ",
            "ReplayStressPostForceShadowXX",
            "ReplayStressPostForceShadowXY",
            "ReplayStressPostForceShadowXZ",
            "ReplayStressPostForceShadowYY",
            "ReplayStressPostForceShadowYZ",
            "ReplayStressPostForceShadowZZ",
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
            "ReplayForceInjectionMode",
            "ReplayPressureClosureMode",
            "ReplayForceDensityClosureMode",
            "ReplayForceFixedPointMode",
            "ReplayFmuStressClosureMode",
        ]
        + B27_STRESS_REQUIRED_FIELDS
    )
)

VTK_FIELDS_B33_LEDGER = ",".join(B33_LEDGER_REQUIRED_FIELDS)

B34_MRT_REQUIRED_FIELDS = [
    "PhaseField",
    "Rho",
    "BOUNDARY",
    "IsItBoundary",
    "ReplayM0",
    "ReplayVelocityHalfForce",
    "ReplayMF",
    "ReplayMomentumAfterG",
    "ReplayMomentumDeltaG",
    "ReplayForceOverRho",
    "ReplayFtotal",
    "ReplayRho",
    "ReplayForceRhoEffective",
    "ReplayForceInjectionMode",
    "ReplayPressureClosureMode",
    "ReplayForceDensityClosureMode",
    "ReplayForceFixedPointMode",
    "ReplayFmuStressClosureMode",
]

VTK_FIELDS_B34_MRT = ",".join(B34_MRT_REQUIRED_FIELDS)

REQUIRED_REPLAY_FIELDS = [
    "ReplayPhaseConsumed",
    "ReplayPhaseFromH",
    "ReplayLapPhi",
    "ReplayMu",
    "ReplayGradPhi",
    "ReplayFsurf",
    "ReplayFpressure",
    "ReplayFbody",
    "ReplayFmu",
    "ReplayFtotal",
    "ReplayRho",
    "ReplayTau",
    "ReplayUPostForce",
    "ReplayPhaseAdvVelocity",
    "ReplayForceOverRho",
    "ReplayFmuIter1",
    "ReplayFtotalIter1",
    "ReplayUPostIter1",
    "ReplayHPreSum",
    "ReplayHPostSum",
    "ReplayHeqSum",
    "ReplayHPreMaxAbs",
    "ReplayHPostMaxAbs",
    "ReplayHeqMaxAbs",
    "ReplayFphiMaxAbs",
    "ReplayTmp1BoundedShadow",
    "ReplayPhaseOutOfBoundsFlag",
    "ReplayM0",
    "ReplayVelocityHalfForce",
    "ReplayMF",
    "ReplayMomentumAfterG",
    "ReplayMomentumDeltaG",
    "ReplayPressureInput",
    "ReplayPressurePhysicalInput",
    "ReplayFpressureNoThird",
    "ReplayFpressurePhysical",
    "ReplayFmuRaw",
    "ReplayFmuDelta",
    "ReplayStressPreForceShadowXX",
    "ReplayStressPostForceShadowXX",
    "ReplayForceInjectionMode",
    "ReplayPressureClosureMode",
    "ReplayForceDensityClosureMode",
    "ReplayForceFixedPointMode",
    "ReplayFmuStressClosureMode",
    "ReplayForceRhoRaw",
    "ReplayForceRhoEffective",
]

REQUIRED_FIELDS_BY_VTK_SET = {
    "b21": [
        "PhaseField",
        "Rho",
        "BOUNDARY",
        "IsItBoundary",
        "ReplayPhaseFromH",
        "ReplayPhaseAdvVelocity",
        "ReplayForceOverRho",
        "ReplayHPostMaxAbs",
        "B21ProbeActive",
        "B21HPreMaxAbs",
        "B21HeqMaxAbs",
        "B21HPostMaxAbs",
        "B21HPostSumMinusFormula",
    ],
    "b22": [
        "PhaseField",
        "Rho",
        "BOUNDARY",
        "IsItBoundary",
        "ReplayPhaseFromH",
        "ReplayPhaseAdvVelocity",
        "ReplayForceOverRho",
        "B22ProbeActive",
        "B22M0U",
        "B22MomentumU",
        "B22PhaseAdvU",
        "B22M0Speed",
        "B22MomentumSpeed",
        "B22PhaseAdvSpeed",
        "B22ForceOverRhoMag",
        "B22HeqFromM0MaxAbs",
        "B22HeqFromMomentumMaxAbs",
        "B22HeqFromBoundedShadowMaxAbs",
        "B22VelocitySourceId",
    ],
    "b26": B26_REQUIRED_FIELDS,
    "b27stress": B27_STRESS_REQUIRED_FIELDS,
    "b34mrt": B34_MRT_REQUIRED_FIELDS,
    "b33ledger": B33_LEDGER_REQUIRED_FIELDS,
}


@dataclass(frozen=True)
class SmokeCase:
    name: str
    kind: str
    init_theta: float | None = None
    bc_theta: float | None = None


CASES = [
    SmokeCase("bulk_tanh_10", "bulk"),
    SmokeCase("wall_t90_10", "wall", 90.0, 90.0),
    SmokeCase("wall_60to30_10", "wall", 60.0, 30.0),
    SmokeCase("wall_120to150_10", "wall", 120.0, 150.0),
]


def param(name: str, value: str | float | int) -> str:
    return f'    <Param name="{name}" value="{value}"/>'


def cap_sphere_radius(volume_radius: float, theta_deg: float) -> float:
    theta = math.radians(theta_deg)
    denom = (1.0 - math.cos(theta)) ** 2 * (2.0 + math.cos(theta))
    if denom <= 0.0:
        raise ValueError(f"invalid cap theta: {theta_deg}")
    return volume_radius * (4.0 / denom) ** (1.0 / 3.0)


def common_model_params(args: argparse.Namespace) -> str:
    return "\n".join(
        [
            param("Density_h", args.density_h),
            param("Density_l", args.density_l),
            param("Viscosity_h", args.viscosity_h),
            param("Viscosity_l", args.viscosity_l),
            param("tauUpdate", 1),
            param("sigma", args.sigma),
            param("M", args.mobility),
            param("IntWidth", args.int_width),
            param("BubbleType", 1.0),
            param("VelocityX", 0.0),
            param("VelocityY", 0.0),
            param("VelocityZ", 0.0),
            param("GravitationX", 0.0),
            param("GravitationY", 0.0),
            param("GravitationZ", 0.0),
            param("ReplayDiagnosticsMode", args.replay_mode),
            param("PhaseAdvectionVelocityMode", args.phase_advection_velocity_mode),
            param("MomentumForceMode", args.momentum_force_mode),
            param("FmuStressClosureMode", args.fmu_stress_closure_mode),
            param("MomentumClosureDiagnosticsMode", args.momentum_closure_diagnostics_mode),
            param("Stage14B18ClosureDiagnosticsMode", args.b18_closure_diagnostics_mode),
            param("Stage14B18VelocityBound", args.b18_velocity_bound),
            param("Stage14B20HUpdateDiagnosticsMode", args.b20_hupdate_diagnostics_mode),
            param("Stage14B21HPopulationAuditMode", args.b21_hpopulation_audit_mode),
            param("Stage14B22VelocityProducerAuditMode", args.b22_velocity_producer_audit_mode),
            param("MomentumClosureProbeMode", args.momentum_closure_probe_mode),
            param("PressureClosureMode", args.pressure_closure_mode),
            param("PressureClosureReference", args.pressure_closure_reference),
            param("ForceDensityClosureMode", args.force_density_closure_mode),
            param("ForceDensityRhoFloor", args.force_density_rho_floor),
            param("ForceFixedPointMode", args.force_fixed_point_mode),
            param("ForceFixedDivergenceGuardFactor", args.force_fixed_divergence_guard_factor),
            param("force_fixed_iterator", args.force_fixed_iterator),
            param("ForceFixedTol", args.force_fixed_tol),
            param("ForceFixedMaxIter", args.force_fixed_max_iter),
            param("minGradient", "1e-08"),
            param("WettingBCMode", 0),
            param("WallGradMode", 0),
            param("WallMuMode", 0),
            param("DynamicCLMode", 0),
            param("DynamicCLCoeff", 0.0),
        ]
    )


def vtk_fields_for(args: argparse.Namespace) -> str:
    if args.vtk_field_set == "b34mrt":
        return VTK_FIELDS_B34_MRT
    if args.vtk_field_set == "b33ledger":
        return VTK_FIELDS_B33_LEDGER
    if args.vtk_field_set == "b27stress":
        return VTK_FIELDS_B27_STRESS
    if args.vtk_field_set == "b26":
        return VTK_FIELDS_B26
    if args.vtk_field_set == "b22":
        return VTK_FIELDS_B22
    if args.vtk_field_set == "b21":
        return VTK_FIELDS_B21
    if args.vtk_field_set == "minimal":
        return VTK_FIELDS_MINIMAL
    return VTK_FIELDS


def required_fields_for(metadata: dict[str, Any] | None = None) -> list[str]:
    if metadata:
        field_set = metadata.get("vtk_field_set")
        if field_set in REQUIRED_FIELDS_BY_VTK_SET:
            return REQUIRED_FIELDS_BY_VTK_SET[str(field_set)]
    return REQUIRED_REPLAY_FIELDS


def render_bulk_xml(
    iterations: int,
    vtk_period: int,
    log_period: int,
    args: argparse.Namespace,
) -> str:
    vtk_fields = vtk_fields_for(args)
    return f"""<?xml version="1.0"?>
<CLBConfig version="2.0" output="output/" permissive="true">
  <Geometry nx="32" ny="24" nz="24">
    <MRT><Box/></MRT>
  </Geometry>
  <Model>
{common_model_params(args)}
    <Param name="Radius" value="0"/>
    <Param name="CenterX" value="16"/>
    <Param name="CenterY" value="12"/>
    <Param name="CenterZ" value="12"/>
    <Param name="Washburn_start" value="8"/>
    <Param name="Washburn_end" value="24"/>
    <Param name="AnalyticWetting" value="0"/>
    <Param name="WallCompactStencilMode" value="0"/>
    <Param name="radAngle" value="90d"/>
  </Model>
  <VTK what="{vtk_fields}"/>
  <Log Iterations="{log_period}"/>
  <Failcheck Iterations="{log_period}"/>
  <Solve Iterations="{iterations}">
    <VTK Iterations="{vtk_period}" what="{vtk_fields}"/>
    <Log Iterations="{log_period}"/>
    <Failcheck Iterations="{log_period}"/>
  </Solve>
</CLBConfig>
"""


def render_wall_xml(
    init_theta: float,
    bc_theta: float,
    iterations: int,
    vtk_period: int,
    log_period: int,
    args: argparse.Namespace,
) -> str:
    vtk_fields = vtk_fields_for(args)
    volume_radius = 16.0
    parent_radius = cap_sphere_radius(volume_radius, init_theta)
    theta = math.radians(init_theta)
    cap_center_x = 48.0
    cap_center_y = -parent_radius * math.cos(theta)
    cap_center_z = 48.0
    init_params = "\n".join(
        [
            param("Radius", 0),
            param("CenterX", cap_center_x),
            param("CenterY", max(2.0, parent_radius * (1.0 - math.cos(theta)) * 0.35)),
            param("CenterZ", cap_center_z),
            param("CapInit", 1),
            param("CapInitRadius", f"{parent_radius:.16g}"),
            param("CapInitTheta", f"{theta:.16g}"),
            param("CapInitCenterX", f"{cap_center_x:.16g}"),
            param("CapInitCenterY", f"{cap_center_y:.16g}"),
            param("CapInitCenterZ", f"{cap_center_z:.16g}"),
        ]
    )
    return f"""<?xml version="1.0"?>
<CLBConfig version="2.0" output="output/" permissive="true">
  <Geometry nx="96" ny="80" nz="96">
    <MRT><Box/></MRT>
    <Wall mask="ALL" name="OuterDomain">
      <Box nx="1"/><Box dx="-1"/><Box dy="-1"/><Box nz="1"/><Box dz="-1"/>
    </Wall>
    <Wall mask="ALL" name="FlatLowerY"><Box dx="1" nx="94" ny="1" dz="1" nz="94"/></Wall>
  </Geometry>
  <Model>
{common_model_params(args)}
{init_params}
    <Param name="radAngle" value="90d"/>
    <Param name="radAngle" value="90d" zone="OuterDomain"/>
    <Param name="AnalyticSolidType" value="1"/>
    <Param name="AnalyticSolidAxis" value="1"/>
    <Param name="AnalyticSolidPlaneOffset" value="0.0"/>
    <Param name="AnalyticWetting" value="1"/>
    <Param name="WallCompactStencilMode" value="1"/>
    <Param name="WallCompactStencilNormalMode" value="1"/>
    <Param name="WallCompactStencilMaxL" value="3"/>
    <Param name="WallCompactStencilWriteAllowedFlag" value="0"/>
    <Param name="radAngle" value="{bc_theta:.16g}d" zone="FlatLowerY"/>
  </Model>
  <VTK what="{vtk_fields}"/>
  <Log Iterations="{log_period}"/>
  <Failcheck Iterations="{log_period}"/>
  <Solve Iterations="{iterations}">
    <VTK Iterations="{vtk_period}" what="{vtk_fields}"/>
    <Log Iterations="{log_period}"/>
    <Failcheck Iterations="{log_period}"/>
  </Solve>
</CLBConfig>
"""


def render_case_xml(
    case: SmokeCase,
    iterations: int,
    vtk_period: int,
    log_period: int,
    args: argparse.Namespace,
) -> str:
    if case.kind == "bulk":
        return render_bulk_xml(iterations, vtk_period, log_period, args)
    if case.kind == "wall":
        assert case.init_theta is not None and case.bc_theta is not None
        return render_wall_xml(
            case.init_theta,
            case.bc_theta,
            iterations,
            vtk_period,
            log_period,
            args,
        )
    raise ValueError(case.kind)


def binary_hash(binary: str) -> str | None:
    try:
        out = subprocess.check_output(["sha256sum", binary], text=True)
    except Exception:
        return None
    parts = out.split()
    return parts[0] if parts else None


def write_cases(args: argparse.Namespace) -> list[Path]:
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    case_dirs: list[Path] = []
    selected = {name.strip() for name in args.cases.split(",") if name.strip()}
    for case in CASES:
        if selected and case.name not in selected and "all" not in selected:
            continue
        case_dir = root / case.name
        if case_dir.exists() and args.force:
            shutil.rmtree(case_dir)
        case_dir.mkdir(parents=True, exist_ok=True)
        (case_dir / "output").mkdir(exist_ok=True)
        xml = render_case_xml(
            case,
            args.iterations,
            args.vtk_period,
            args.log_period,
            args,
        )
        (case_dir / "case.xml").write_text(xml, encoding="utf-8")
        metadata = {
            "stage": "stage14_s2_replay_smoke",
            "case": case.name,
            "kind": case.kind,
            "init_theta_deg": case.init_theta,
            "bc_theta_deg": case.bc_theta,
            "iterations": args.iterations,
            "vtk_period": args.vtk_period,
            "log_period": args.log_period,
            "physical_grid": xml_grid(xml),
            "vtk_field_set": args.vtk_field_set,
            "vtk_fields": vtk_fields_for(args).split(","),
            "binary": args.binary,
            "binary_sha256": binary_hash(args.binary),
            "gpu": args.gpu,
            "replay_mode": args.replay_mode,
            "phase_advection_velocity_mode": args.phase_advection_velocity_mode,
            "momentum_force_mode": args.momentum_force_mode,
            "fmu_stress_closure_mode": args.fmu_stress_closure_mode,
            "momentum_closure_diagnostics_mode": args.momentum_closure_diagnostics_mode,
            "b18_closure_diagnostics_mode": args.b18_closure_diagnostics_mode,
            "b18_velocity_bound": args.b18_velocity_bound,
            "b20_hupdate_diagnostics_mode": args.b20_hupdate_diagnostics_mode,
            "b21_hpopulation_audit_mode": args.b21_hpopulation_audit_mode,
            "b22_velocity_producer_audit_mode": args.b22_velocity_producer_audit_mode,
            "momentum_closure_probe_mode": args.momentum_closure_probe_mode,
            "pressure_closure_mode": args.pressure_closure_mode,
            "pressure_closure_reference": args.pressure_closure_reference,
            "force_density_closure_mode": args.force_density_closure_mode,
            "force_density_rho_floor": args.force_density_rho_floor,
            "force_fixed_point_mode": args.force_fixed_point_mode,
            "force_fixed_tol": args.force_fixed_tol,
            "force_fixed_max_iter": args.force_fixed_max_iter,
            "force_fixed_divergence_guard_factor": args.force_fixed_divergence_guard_factor,
            "density_h": args.density_h,
            "density_l": args.density_l,
            "viscosity_h": args.viscosity_h,
            "viscosity_l": args.viscosity_l,
            "sigma": args.sigma,
            "mobility": args.mobility,
            "int_width": args.int_width,
            "force_fixed_iterator": args.force_fixed_iterator,
            "claim_limit": "S2 replay smoke only; not contact-angle validation",
        }
        (case_dir / "case_metadata.json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8"
        )
        case_dirs.append(case_dir)
    return case_dirs


def run_cases(case_dirs: list[Path], args: argparse.Namespace) -> list[dict[str, Any]]:
    env = os.environ.copy()
    env["PATH"] = "/usr/local/cuda-12.6/bin:/usr/bin:/bin:/usr/local/bin"
    env["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    env["CUDA_VISIBLE_DEVICES"] = str(args.gpu)
    env["OMPI_MCA_plm_rsh_agent"] = "/usr/bin/ssh"
    env["LD_LIBRARY_PATH"] = "/usr/local/cuda-12.6/lib64:" + env.get("LD_LIBRARY_PATH", "")
    results = []
    for case_dir in case_dirs:
        with (case_dir / "run.log").open("w", encoding="utf-8", errors="replace") as log:
            log.write(f"case={case_dir.name}\n")
            log.write(f"gpu={args.gpu}\n")
            log.write(f"binary={args.binary}\n")
            log.write(f"binary_sha256={binary_hash(args.binary)}\n")
            log.flush()
            completed = subprocess.run(
                ["timeout", str(args.timeout), args.binary, "case.xml"],
                cwd=case_dir,
                stdout=log,
                stderr=subprocess.STDOUT,
                env=env,
            )
            log.write(f"\nRUN_RC={completed.returncode}\n")
        results.append({"case": case_dir.name, "run_rc": completed.returncode})
    return results


def xml_grid(xml: str) -> list[int] | None:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return None
    geom = root.find("Geometry")
    if geom is None:
        return None
    try:
        return [int(geom.attrib[name]) for name in ("nx", "ny", "nz")]
    except (KeyError, ValueError):
        return None


def step_of(path: Path) -> int:
    match = re.search(r"P00_(\d+)\.vti$", path.name)
    return int(match.group(1)) if match else -1


def load_vti(path: Path) -> tuple[tuple[int, int, int], dict[str, np.ndarray]]:
    import vtk  # type: ignore
    from vtk.util.numpy_support import vtk_to_numpy  # type: ignore

    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(str(path))
    reader.Update()
    data = reader.GetOutput()
    dims = tuple(int(v) - 1 for v in data.GetDimensions())
    cell_data = data.GetCellData()
    arrays: dict[str, np.ndarray] = {}
    for idx in range(cell_data.GetNumberOfArrays()):
        arr = cell_data.GetArray(idx)
        if arr is None:
            continue
        arrays[arr.GetName()] = vtk_to_numpy(arr)
    return dims, arrays


def crop_to_physical(
    arr: np.ndarray,
    local_dims: tuple[int, int, int],
    physical_grid: list[int] | None,
) -> np.ndarray:
    if not physical_grid:
        return arr
    px, py, pz = physical_grid
    nx, ny, nz = local_dims
    if px > nx or py > ny or pz > nz:
        return arr
    values = np.asarray(arr)
    if values.shape[0] != nx * ny * nz:
        return arr
    if values.ndim == 1:
        return values.reshape((nx, ny, nz))[:px, :py, :pz].reshape(-1)
    return values.reshape((nx, ny, nz, values.shape[1]))[:px, :py, :pz, :].reshape(
        -1, values.shape[1]
    )


def field_stats(arr: np.ndarray) -> dict[str, Any]:
    values = np.asarray(arr, dtype=float)
    finite = np.isfinite(values)
    finite_values = values[finite]
    if finite_values.size == 0:
        return {
            "present": True,
            "size": int(values.size),
            "finite_count": 0,
            "nonfinite_count": int(values.size),
            "min": None,
            "max": None,
            "mean": None,
            "max_abs": None,
            "nonzero_count": 0,
        }
    mag = np.linalg.norm(finite_values, axis=1) if finite_values.ndim == 2 else np.abs(finite_values)
    return {
        "present": True,
        "size": int(values.size),
        "finite_count": int(np.count_nonzero(finite)),
        "nonfinite_count": int(values.size - np.count_nonzero(finite)),
        "min": float(np.min(finite_values)),
        "max": float(np.max(finite_values)),
        "mean": float(np.mean(finite_values)),
        "max_abs": float(np.max(np.abs(finite_values))),
        "nonzero_count": int(np.count_nonzero(mag > 0.0)),
    }


def summarize_case(case_dir: Path) -> dict[str, Any]:
    physical_grid = None
    metadata: dict[str, Any] = {}
    metadata_path = case_dir / "case_metadata.json"
    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            physical_grid = metadata.get("physical_grid")
        except json.JSONDecodeError:
            physical_grid = None
            metadata = {}
    required_fields = required_fields_for(metadata)
    vtis = sorted((case_dir / "output").glob("case_VTK_P00_*.vti"), key=step_of)
    summary: dict[str, Any] = {
        "case": case_dir.name,
        "case_dir": str(case_dir),
        "n_vti": len(vtis),
        "steps": [step_of(path) for path in vtis],
        "physical_grid": physical_grid,
        "vtk_field_set": metadata.get("vtk_field_set"),
        "required_replay_fields": required_fields,
        "frames": [],
        "failures": [],
    }
    if not vtis:
        summary["failures"].append("no_vti_outputs")
        return summary
    for path in vtis:
        dims, arrays = load_vti(path)
        frame = {
            "step": step_of(path),
            "vti": str(path),
            "dims": list(dims),
            "array_count": len(arrays),
            "missing_required_replay": [name for name in required_fields if name not in arrays],
            "stats": {},
        }
        base_summary_fields = [
            "PhaseField",
            "WallGhost",
            "ForceIterResidual",
            "ForceIterCount",
            "ReplayPhaseConsumed",
            "ReplayPhaseFromH",
            "ReplayLapPhi",
            "ReplayMu",
            "ReplayGradPhi",
            "ReplayFsurf",
            "ReplayFpressure",
            "ReplayFbody",
            "ReplayFmu",
            "ReplayFtotal",
            "ReplayRho",
            "ReplayTau",
            "ReplayPressureMoment",
            "ReplayUPreForce",
            "ReplayUPostForce",
            "ReplayPhaseAdvVelocity",
            "ReplayForceOverRho",
            "ReplayFmuIter1",
            "ReplayFtotalIter1",
            "ReplayUPostIter1",
            "ReplayNormal",
            "ReplayStressXX",
            "ReplayStressXY",
            "ReplayStressXZ",
            "ReplayStressYY",
            "ReplayStressYZ",
            "ReplayStressZZ",
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
            "ReplayPhaseOutOfBoundsFlag",
            "ReplayM0",
            "ReplayVelocityHalfForce",
            "ReplayMF",
            "ReplayMomentumAfterG",
            "ReplayMomentumDeltaG",
            "ReplayPressureInput",
            "ReplayPressureForceScale",
            "ReplayPressurePhysicalInput",
            "ReplayFpressureNoThird",
            "ReplayFpressurePhysical",
            "ReplayStressInputXX",
            "ReplayStressInputXY",
            "ReplayStressInputXZ",
            "ReplayStressInputYY",
            "ReplayStressInputYZ",
            "ReplayStressInputZZ",
            "ReplayStressIter1XX",
            "ReplayStressIter1XY",
            "ReplayStressIter1XZ",
            "ReplayStressIter1YY",
            "ReplayStressIter1YZ",
            "ReplayStressIter1ZZ",
            "ReplayStressPreForceShadowXX",
            "ReplayStressPreForceShadowXY",
            "ReplayStressPreForceShadowXZ",
            "ReplayStressPreForceShadowYY",
            "ReplayStressPreForceShadowYZ",
            "ReplayStressPreForceShadowZZ",
            "ReplayStressPostForceShadowXX",
            "ReplayStressPostForceShadowXY",
            "ReplayStressPostForceShadowXZ",
            "ReplayStressPostForceShadowYY",
            "ReplayStressPostForceShadowYZ",
            "ReplayStressPostForceShadowZZ",
            "ReplayFmuRaw",
            "ReplayFmuDelta",
            "ReplayTauUsed",
            "ReplayRhoForForce",
            "ReplayForceInjectionMode",
            "ReplayPressureClosureMode",
            "ReplayForceDensityClosureMode",
            "ReplayForceFixedPointMode",
            "ReplayForceRhoRaw",
            "ReplayForceRhoEffective",
            "PhaseStencilGhostUseCount",
            "PhaseStencilFallbackCount",
            "PhaseStencilMidpointFallbackCount",
        ]
        fields_to_summarize = list(
            dict.fromkeys(
                base_summary_fields
                + sorted(
                    name
                    for name in arrays
                    if name.startswith("B18")
                    or name.startswith("B20")
                    or name.startswith("B21")
                    or name.startswith("B22")
                )
            )
        )
        for name in fields_to_summarize:
            if name in arrays:
                frame["stats"][name] = field_stats(
                    crop_to_physical(arrays[name], dims, physical_grid)
                )
            else:
                frame["stats"][name] = {"present": False}
        if frame["missing_required_replay"]:
            summary["failures"].append(f"missing_replay_fields_step_{frame['step']}")
        for name, stats in frame["stats"].items():
            if stats.get("present") and stats.get("nonfinite_count", 0) > 0:
                summary["failures"].append(f"nonfinite_{name}_step_{frame['step']}")
        summary["frames"].append(frame)
    summary["failures"] = sorted(set(summary["failures"]))
    return summary


def summarize_root(root: Path) -> dict[str, Any]:
    cases = []
    for case_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        if (case_dir / "output").is_dir():
            cases.append(summarize_case(case_dir))
    report = {
        "root": str(root),
        "case_count": len(cases),
        "cases": cases,
        "failures": sorted({failure for case in cases for failure in case.get("failures", [])}),
    }
    (root / "s2_replay_smoke_summary.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=DEFAULT_ROOT)
    parser.add_argument("--binary", default=DEFAULT_BIN)
    parser.add_argument("--gpu", type=int, default=1)
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--vtk-period", type=int, default=1)
    parser.add_argument(
        "--vtk-field-set",
        choices=("full", "minimal", "b21", "b22", "b26", "b27stress", "b34mrt", "b33ledger"),
        default="full",
    )
    parser.add_argument("--log-period", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--cases", default="all")
    parser.add_argument("--replay-mode", type=int, default=1)
    parser.add_argument("--phase-advection-velocity-mode", type=int, default=0)
    parser.add_argument("--momentum-force-mode", type=int, default=0)
    parser.add_argument("--fmu-stress-closure-mode", type=int, default=0)
    parser.add_argument("--momentum-closure-diagnostics-mode", type=int, default=0)
    parser.add_argument("--b18-closure-diagnostics-mode", type=int, default=0)
    parser.add_argument("--b18-velocity-bound", type=float, default=0.2)
    parser.add_argument("--b20-hupdate-diagnostics-mode", type=int, default=0)
    parser.add_argument("--b21-hpopulation-audit-mode", type=int, default=0)
    parser.add_argument("--b22-velocity-producer-audit-mode", type=int, default=0)
    parser.add_argument("--momentum-closure-probe-mode", type=int, default=0)
    parser.add_argument("--pressure-closure-mode", type=int, default=0)
    parser.add_argument("--pressure-closure-reference", type=float, default=0.0)
    parser.add_argument("--force-density-closure-mode", type=int, default=0)
    parser.add_argument("--force-density-rho-floor", type=float, default=0.0)
    parser.add_argument("--force-fixed-point-mode", type=int, default=0)
    parser.add_argument("--force-fixed-tol", type=float, default=0.0)
    parser.add_argument("--force-fixed-max-iter", type=int, default=2)
    parser.add_argument("--force-fixed-divergence-guard-factor", type=float, default=100.0)
    parser.add_argument("--density-h", type=float, default=1.0)
    parser.add_argument("--density-l", type=float, default=0.001)
    parser.add_argument("--viscosity-h", type=float, default=0.1)
    parser.add_argument("--viscosity-l", type=float, default=0.1)
    parser.add_argument("--sigma", default="5e-05")
    parser.add_argument("--mobility", type=float, default=0.3)
    parser.add_argument("--int-width", type=float, default=3.0)
    parser.add_argument("--force-fixed-iterator", type=int, default=2)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--summarize", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    case_dirs = write_cases(args)
    run_results: list[dict[str, Any]] = []
    if args.run:
        run_results = run_cases(case_dirs, args)
    report = None
    if args.summarize:
        report = summarize_root(Path(args.root))
    result = {
        "root": args.root,
        "case_dirs": [str(path) for path in case_dirs],
        "run_results": run_results,
        "summary": report,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if run_results and any(row["run_rc"] != 0 for row in run_results):
        return 2
    if report and report["failures"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
