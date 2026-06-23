#!/usr/bin/env python3
"""Audit TCLB stage, streaming-density, and wetting ghost semantics.

The script is intentionally source-level and conservative. It does not claim
that a model is correct. It records the implementation surfaces that must be
checked before translating explicit C-array boundary logic into TCLB stages.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any


ADD_DENSITY_RE = re.compile(
    r"AddDensity\(\s*name\s*=\s*\"(?P<name>[^\"]+)\"\s*,\s*dx\s*=\s*(?P<dx>[-0-9]+)\s*,\s*dy\s*=\s*(?P<dy>[-0-9]+)\s*,\s*dz\s*=\s*(?P<dz>[-0-9]+)\s*,\s*group\s*=\s*\"(?P<group>[^\"]+)\""
)
ADD_FIELD_RE = re.compile(
    r"AddField\(\s*(?:name\s*=\s*)?[\"'](?P<name>[^\"']+)[\"'](?P<rest>[^)]*)\)"
)
ADD_STAGE_RE = re.compile(
    r"AddStage\(\s*(?:name\s*=\s*)?[\"'](?P<stage>[^\"']+)[\"'](?P<rest>.*)\)"
)
ADD_SETTING_RE = re.compile(r"AddSetting\(\s*name\s*=\s*\"(?P<name>[^\"]+)\"(?P<rest>[^)]*)\)")
GROUP_RE = re.compile(r"group\s*=\s*[\"'](?P<group>[^\"']+)[\"']")
STENCIL_RE = re.compile(r"stencil3d\s*=\s*(?P<stencil>[0-9]+)")
CALL_RE = re.compile(r"\b(?P<fn>[A-Za-z_][A-Za-z0-9_]*)\s*\(")
ACTION_RE = re.compile(r"AddAction\(\s*[\"'](?P<action>[^\"']+)[\"']\s*,\s*c\((?P<body>.*?)\)\s*\)")

FIELDS_OF_INTEREST = [
    "PhaseF",
    "WallGhost",
    "WallGhostRaw",
    "WallGhostClamped",
    "WallGhostClampHit",
    "WettingPathId",
    "LocalRadAngle",
    "WallH",
    "AnalyticFlag",
    "gradPhiVal_x",
    "gradPhiVal_y",
    "gradPhiVal_z",
    "gradPhi_PhaseF",
    "PhaseStencilGhostUseCount",
    "PhaseStencilFallbackCount",
    "PhaseStencilMidpointFallbackCount",
    "ForceIterResidual",
    "ForceIterCount",
    "MassCorrectionApplied",
    "ReplayPhaseConsumed",
    "ReplayPhaseFromH",
    "ReplayLapPhi",
    "ReplayMu",
    "ReplayGradPhiX",
    "ReplayGradPhiY",
    "ReplayGradPhiZ",
    "ReplayFsurfX",
    "ReplayFsurfY",
    "ReplayFsurfZ",
    "ReplayFpressureX",
    "ReplayFpressureY",
    "ReplayFpressureZ",
    "ReplayFbodyX",
    "ReplayFbodyY",
    "ReplayFbodyZ",
    "ReplayFmuX",
    "ReplayFmuY",
    "ReplayFmuZ",
    "ReplayFtotalX",
    "ReplayFtotalY",
    "ReplayFtotalZ",
    "ReplayRho",
    "ReplayTau",
    "ReplayPressureMoment",
    "ReplayUPreForceX",
    "ReplayUPreForceY",
    "ReplayUPreForceZ",
    "ReplayUPostForceX",
    "ReplayUPostForceY",
    "ReplayUPostForceZ",
    "ReplayPhaseAdvVelocityX",
    "ReplayPhaseAdvVelocityY",
    "ReplayPhaseAdvVelocityZ",
    "ReplayForceOverRhoX",
    "ReplayForceOverRhoY",
    "ReplayForceOverRhoZ",
    "ReplayFmuIter1X",
    "ReplayFmuIter1Y",
    "ReplayFmuIter1Z",
    "ReplayFtotalIter1X",
    "ReplayFtotalIter1Y",
    "ReplayFtotalIter1Z",
    "ReplayUPostIter1X",
    "ReplayUPostIter1Y",
    "ReplayUPostIter1Z",
    "ReplayNormalX",
    "ReplayNormalY",
    "ReplayNormalZ",
    "ReplayStressXX",
    "ReplayStressXY",
    "ReplayStressXZ",
    "ReplayStressYY",
    "ReplayStressYZ",
    "ReplayStressZZ",
    "ReplayFphiSum",
    "ReplayFphiMaxAbs",
    "ReplayTmp1",
    "WallMuCandidate",
    "DynamicCLForceCandidateX",
    "DynamicCLForceCandidateY",
    "DynamicCLForceCandidateZ",
    "DynamicCLForceCandidateMag",
]

LOCAL_QUANTITIES = [
    "gradPhi",
    "lpPhi",
    "mu",
    "F_surf",
    "F_pressure",
    "F_body",
    "F_mu",
    "F_total",
    "F_phi",
    "p",
    "rho",
    "C",
]

IMPORTANT_FUNCTIONS = [
    "Init",
    "Init_distributions",
    "Run",
    "CollisionMRT",
    "CollisionBGK",
    "calcPhaseF",
    "calcGradPhi",
    "calcGradPhiRaw",
    "calcMu",
    "calc_Fp",
    "calc_Fs",
    "calcPhaseGrad",
    "calcPhaseGrad_init",
    "calcPhaseGradCloseToBoundary",
    "calcWallPhase",
    "calcWallPhase_correction",
    "BounceBack",
    "updateBoundary",
    "calcDynamicCLShadow",
    "calcWallMuSource",
]

STAGE_DIRECT_WRITES: dict[str, list[str]] = {
    "PhaseInit": ["PhaseF", "U", "V", "W", "pnorm"],
    "BaseInit": ["g*", "h*", "pnorm", "PhaseF", "gradPhiVal_x", "gradPhiVal_y", "gradPhiVal_z"],
    "calcPhase": ["PhaseF", "ReplayPhaseFromH"],
    "BaseIter": [
        "g*",
        "h*",
        "U",
        "V",
        "W",
        "pnorm",
        "ForceIterResidual",
        "ForceIterCount",
        "MassCorrectionApplied",
        "PhaseStencilGhostUseCount",
        "PhaseStencilFallbackCount",
        "PhaseStencilMidpointFallbackCount",
        "ReplayPhaseConsumed",
        "ReplayLapPhi",
        "ReplayMu",
        "ReplayGradPhi*",
        "ReplayFsurf*",
        "ReplayFpressure*",
        "ReplayFbody*",
        "ReplayFmu*",
        "ReplayFtotal*",
        "ReplayRho",
        "ReplayTau",
        "ReplayPressureMoment",
        "ReplayUPreForce*",
        "ReplayUPostForce*",
        "ReplayPhaseAdvVelocity*",
        "ReplayForceOverRho*",
        "ReplayNormal*",
        "ReplayStress*",
        "ReplayFphi*",
        "ReplayTmp1",
        "WallMuCandidate",
        "DynamicCL*",
    ],
    "WallInit_CA": ["nw_x", "nw_y", "nw_z", "IsSpecialBoundaryPoint", "IsBoundary"],
    "WallInit": ["nw_x", "nw_y", "nw_z", "IsSpecialBoundaryPoint", "IsBoundary"],
    "calcPhaseGrad": ["gradPhiVal_x", "gradPhiVal_y", "gradPhiVal_z", "gradPhi_PhaseF"],
    "calcPhaseGrad_init": ["gradPhiVal_x", "gradPhiVal_y", "gradPhiVal_z", "gradPhi_PhaseF"],
    "calcWall_CA": [
        "PhaseF",
        "WallGhost",
        "WallGhostRaw",
        "WallGhostClamped",
        "WallGhostClampHit",
        "WettingPathId",
        "LocalRadAngle",
        "WallH",
        "AnalyticFlag",
        "WallCSQ*",
    ],
    "calcWall": [
        "PhaseF",
        "WallGhost",
        "WallGhostRaw",
        "WallGhostClamped",
        "WallGhostClampHit",
        "WettingPathId",
        "LocalRadAngle",
        "WallH",
        "AnalyticFlag",
    ],
    "calcWallPhase_correction": [
        "PhaseF",
        "WallGhost",
        "WallGhostRaw",
        "WallGhostClamped",
        "WallGhostClampHit",
        "WettingPathId",
        "LocalRadAngle",
    ],
}

STAGE_DIRECT_READS: dict[str, list[str]] = {
    "PhaseInit": ["PhaseField", "NodeType", "X", "Y", "Z"],
    "BaseInit": ["PhaseF", "U", "V", "W", "WallGhost", "IsBoundary"],
    "calcPhase": ["h*", "PhaseF", "NodeType"],
    "BaseIter": ["g*", "h*", "PhaseF", "WallGhost", "IsBoundary", "U", "V", "W", "pnorm"],
    "WallInit_CA": ["PhaseF", "NodeType", "IsBoundary"],
    "WallInit": ["PhaseF", "NodeType", "IsBoundary"],
    "calcPhaseGrad": ["PhaseF", "WallGhost", "IsBoundary"],
    "calcPhaseGrad_init": ["PhaseF", "WallGhost", "IsBoundary", "gradPhiVal_x", "gradPhiVal_y", "gradPhiVal_z"],
    "calcWall_CA": ["PhaseF", "WallGhost", "gradPhiVal_x", "gradPhiVal_y", "gradPhiVal_z", "nw_x", "nw_y", "nw_z"],
    "calcWall": ["PhaseF", "WallGhost", "nw_x", "nw_y", "nw_z"],
    "calcWallPhase_correction": ["PhaseF", "WallGhost", "nw_x", "nw_y", "nw_z", "IsSpecialBoundaryPoint"],
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def parse_lattice(text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in ADD_DENSITY_RE.finditer(text):
        out.append(
            {
                "name": m.group("name"),
                "dx": int(m.group("dx")),
                "dy": int(m.group("dy")),
                "dz": int(m.group("dz")),
                "group": m.group("group"),
                "streams": any(int(m.group(a)) != 0 for a in ("dx", "dy", "dz")),
                "line": line_of(text, m.start()),
            }
        )
    return out


def parse_fields(text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in ADD_FIELD_RE.finditer(text):
        rest = m.group("rest")
        gm = GROUP_RE.search(rest)
        sm = STENCIL_RE.search(rest)
        out.append(
            {
                "name": m.group("name"),
                "group": gm.group("group") if gm else "",
                "stencil3d": int(sm.group("stencil")) if sm else None,
                "line": line_of(text, m.start()),
            }
        )
    return out


def parse_settings(text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in ADD_SETTING_RE.finditer(text):
        out.append({"name": m.group("name"), "line": line_of(text, m.start()), "rest": m.group("rest").strip()})
    return out


def parse_stages(text: str) -> list[dict[str, Any]]:
    stages: list[dict[str, Any]] = []
    for m in ADD_STAGE_RE.finditer(text):
        rest = m.group("rest").strip()
        function = ""
        fn_match = re.match(r",\s*[\"'](?P<fn>[^\"']+)[\"']", rest)
        if fn_match:
            function = fn_match.group("fn")
        elif "load=" in rest or "save=" in rest:
            function = ""
        stages.append(
            {
                "stage": m.group("stage"),
                "function": function,
                "line": line_of(text, m.start()),
                "raw": " ".join(m.group(0).split()),
            }
        )
    return stages


def parse_actions(text: str) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for m in ACTION_RE.finditer(text):
        raw_body = m.group("body")
        stages: list[str] = []
        for token in re.finditer(r"[\"'](?P<quoted>[^\"']+)[\"']|\b(?P<bare>calcGrad)\b", raw_body):
            stages.append(token.group("quoted") or token.group("bare") or "")
        actions.append(
            {
                "action": m.group("action"),
                "stages": stages,
                "line": line_of(text, m.start()),
                "raw": " ".join(m.group(0).split()),
            }
        )
    return actions


def find_occurrences(text: str, needles: list[str]) -> dict[str, list[int]]:
    found: dict[str, list[int]] = {}
    for needle in needles:
        lines = [i + 1 for i, line in enumerate(text.splitlines()) if needle in line]
        if lines:
            found[needle] = lines
    return found


def find_function_ranges(text: str) -> dict[str, dict[str, Any]]:
    funcs: dict[str, dict[str, Any]] = {}
    pat = re.compile(r"CudaDeviceFunction\s+[A-Za-z0-9_*\s]+\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(")
    matches = list(pat.finditer(text))
    for idx, m in enumerate(matches):
        name = m.group("name")
        start = m.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        funcs[name] = {
            "line": line_of(text, start),
            "end_line": line_of(text, end),
            "start_offset": start,
            "end_offset": end,
            "body": text[start:end],
        }
    return funcs


def public_function_map(funcs: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {name: {"line": data["line"], "end_line": data["end_line"]} for name, data in funcs.items()}


def scan_identifier_access(body: str, identifier: str) -> dict[str, list[int]]:
    reads: list[int] = []
    writes: list[int] = []
    calls: list[int] = []
    dyn_reads: list[int] = []
    local_decls: list[int] = []
    escaped = re.escape(identifier)
    call_pat = re.compile(rf"\b{escaped}\s*(?:_dyn)?\s*\(")
    write_pat = re.compile(rf"\b{escaped}\b\s*(?:[+\-*/]?=)")
    decl_pat = re.compile(rf"\b(?:real_t|vector_t|int|bool)\s+[^;\n]*\b{escaped}\b")

    for line_no, line in enumerate(body.splitlines(), start=1):
        stripped = line.split("//", 1)[0]
        if not stripped.strip():
            continue
        if decl_pat.search(stripped):
            local_decls.append(line_no)
        if call_pat.search(stripped):
            calls.append(line_no)
            reads.append(line_no)
            if f"{identifier}_dyn" in stripped:
                dyn_reads.append(line_no)
        if write_pat.search(stripped):
            writes.append(line_no)
        elif re.search(rf"\b{escaped}\b", stripped):
            reads.append(line_no)
    return {
        "reads": sorted(set(reads)),
        "writes": sorted(set(writes)),
        "calls": sorted(set(calls)),
        "dyn_reads": sorted(set(dyn_reads)),
        "local_decls": sorted(set(local_decls)),
    }


def scan_function_access(funcs: dict[str, dict[str, Any]], identifiers: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for fn_name, fn_data in funcs.items():
        if fn_name not in IMPORTANT_FUNCTIONS:
            continue
        body = fn_data["body"]
        for ident in identifiers:
            access = scan_identifier_access(body, ident)
            if any(access[key] for key in ("reads", "writes", "calls", "dyn_reads")):
                rows.append(
                    {
                        "function": fn_name,
                        "function_line": fn_data["line"],
                        "identifier": ident,
                        "reads_rel": access["reads"][:30],
                        "writes_rel": access["writes"][:30],
                        "calls_rel": access["calls"][:30],
                        "dyn_reads_rel": access["dyn_reads"][:30],
                        "local_decls_rel": access["local_decls"][:30],
                    }
                )
    return rows


def stage_sequence(actions: list[dict[str, Any]], action_name: str = "Iteration") -> list[str]:
    candidate_actions = [action for action in actions if action["action"] == action_name]
    for action in candidate_actions:
        if "calcWall_CA" in action["stages"]:
            seq: list[str] = []
            for stage in action["stages"]:
                if stage == "calcGrad":
                    seq.append("calcPhaseGrad_or_init")
                else:
                    seq.append(stage)
            return seq
    for action in actions:
        if action["action"] == action_name:
            seq: list[str] = []
            for stage in action["stages"]:
                if stage == "calcGrad":
                    seq.append("calcPhaseGrad_or_init")
                else:
                    seq.append(stage)
            return seq
    return []


def build_stage_timeline(stages: list[dict[str, Any]], actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_name = {stage["stage"]: stage for stage in stages}
    rows: list[dict[str, Any]] = []
    seq = stage_sequence(actions)
    if not seq:
        seq = ["BaseIter", "calcPhase", "calcPhaseGrad_or_init", "calcWall_CA", "calcWallPhase_correction"]
    for idx, stage_name in enumerate(seq, start=1):
        alternatives = ["calcPhaseGrad", "calcPhaseGrad_init"] if stage_name == "calcPhaseGrad_or_init" else [stage_name]
        for alt in alternatives:
            stage = by_name.get(alt, {})
            rows.append(
                {
                    "order": idx,
                    "stage": alt,
                    "function": stage.get("function", ""),
                    "line": stage.get("line", ""),
                    "reads": STAGE_DIRECT_READS.get(alt, []),
                    "writes": STAGE_DIRECT_WRITES.get(alt, []),
                    "time_level_note": stage_time_level_note(alt),
                }
            )
    return rows


def stage_time_level_note(stage: str) -> str:
    if stage == "BaseIter":
        return "consumes saved fields from previous action boundary and writes populations/macros for next saved state"
    if stage == "calcPhase":
        return "after Run, writes PhaseF from streamed/collided h populations for next force stage"
    if stage in {"calcPhaseGrad", "calcPhaseGrad_init"}:
        return "after calcPhase, writes cached gradPhiVal for wall reconstruction/output"
    if stage in {"calcWall_CA", "calcWall"}:
        return "after gradient stage, writes passive WallGhost and wall-node PhaseF mirror"
    if stage == "calcWallPhase_correction":
        return "final wall correction before next action boundary"
    return ""


def field_kind(name: str, densities: list[dict[str, Any]], fields: list[dict[str, Any]]) -> str:
    dens = [d for d in densities if d["name"] == name or (name.endswith("*") and d["group"] == name[:-1])]
    if dens:
        return "density_streaming" if any(d["streams"] for d in dens) else "density_nonstreaming"
    fld = [f for f in fields if f["name"] == name]
    if fld:
        return "field"
    if name.endswith("*"):
        return "pattern"
    return "local_or_setting"


def build_fields_of_interest(densities: list[dict[str, Any]], fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name in FIELDS_OF_INTEREST + ["g*", "h*", "U", "V", "W", "pnorm", "nw_x", "nw_y", "nw_z"]:
        matching_fields = [f for f in fields if f["name"] == name]
        matching_densities = [d for d in densities if d["name"] == name]
        if name == "g*":
            matching_densities = [d for d in densities if d["group"] == "g"]
        elif name == "h*":
            matching_densities = [d for d in densities if d["group"] == "h"]
        rows.append(
            {
                "name": name,
                "kind": field_kind(name, densities, fields),
                "group": ",".join(sorted({str(x.get("group", "")) for x in matching_fields + matching_densities})),
                "stencil3d": ",".join(sorted({str(x.get("stencil3d", "")) for x in matching_fields if x.get("stencil3d") is not None})),
                "streams": any(bool(x.get("streams")) for x in matching_densities),
                "line": ",".join(str(x.get("line", "")) for x in matching_fields + matching_densities),
            }
        )
    return rows


def build_producer_consumer_edges(timeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    last_writer: dict[str, dict[str, Any]] = {}
    for row in timeline:
        stage = row["stage"]
        order = row["order"]
        for written in row["writes"]:
            last_writer[written] = row
            edges.append(
                {
                    "quantity": written,
                    "producer_stage": stage,
                    "producer_order": order,
                    "consumer_stage": "",
                    "consumer_order": "",
                    "edge_type": "write",
                    "time_level": "produced during this stage for later saved state",
                }
            )
        for read_name in row["reads"]:
            producer = resolve_last_writer(read_name, last_writer)
            edges.append(
                {
                    "quantity": read_name,
                    "producer_stage": producer.get("stage", "previous_action_or_initial_state") if producer else "previous_action_or_initial_state",
                    "producer_order": producer.get("order", "") if producer else "",
                    "consumer_stage": stage,
                    "consumer_order": order,
                    "edge_type": "read",
                    "time_level": "same action prior stage" if producer else "loaded at action boundary / previous saved state",
                }
            )
    return edges


def resolve_last_writer(name: str, last_writer: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    if name in last_writer:
        return last_writer[name]
    if name.endswith("*") and name in last_writer:
        return last_writer[name]
    for pattern, row in last_writer.items():
        if pattern.endswith("*") and name.startswith(pattern[:-1]):
            return row
    return None


def build_unresolved_edges(edges: list[dict[str, Any]], function_access: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unresolved: list[dict[str, Any]] = []
    replay_coverage = {
        "gradPhi": ["ReplayGradPhiX", "ReplayGradPhiY", "ReplayGradPhiZ"],
        "mu": ["ReplayMu"],
        "lpPhi": ["ReplayLapPhi"],
        "F_surf": ["ReplayFsurfX", "ReplayFsurfY", "ReplayFsurfZ"],
        "F_pressure": ["ReplayFpressureX", "ReplayFpressureY", "ReplayFpressureZ"],
        "F_body": ["ReplayFbodyX", "ReplayFbodyY", "ReplayFbodyZ"],
        "F_mu": ["ReplayFmuX", "ReplayFmuY", "ReplayFmuZ"],
        "F_total": ["ReplayFtotalX", "ReplayFtotalY", "ReplayFtotalZ"],
    }
    written_quantities = {edge["quantity"] for edge in edges if edge["edge_type"] == "write"}
    def is_written(field: str) -> bool:
        if field in written_quantities:
            return True
        for written in written_quantities:
            if written.endswith("*") and field.startswith(written[:-1]):
                return True
        return False

    for edge in edges:
        if edge["edge_type"] == "read" and edge["producer_stage"] == "previous_action_or_initial_state":
            qty = edge["quantity"]
            if qty in {"PhaseF", "WallGhost", "gradPhiVal_x", "gradPhiVal_y", "gradPhiVal_z"}:
                unresolved.append(
                    {
                        "severity": "CHECK",
                        "quantity": qty,
                        "consumer_stage": edge["consumer_stage"],
                        "reason": "read comes from action-boundary state; S2 must verify time level against C replay",
                    }
                )
    for access in function_access:
        ident = access["identifier"]
        if ident in {"mu", "F_surf", "F_pressure", "F_total", "gradPhi"} and access["function"] in {"CollisionMRT", "CollisionBGK"}:
            if all(is_written(field) for field in replay_coverage.get(ident, [])):
                unresolved.append(
                    {
                        "severity": "COVERED",
                        "quantity": ident,
                        "consumer_stage": access["function"],
                        "reason": "local collision quantity is covered by Replay* diagnostics; S2 must compare numeric values and time level",
                    }
                )
                continue
            unresolved.append(
                {
                    "severity": "CHECK",
                    "quantity": ident,
                    "consumer_stage": access["function"],
                    "reason": "local collision quantity is not saved as an output field; S2 needs diagnostics or exact host recomputation",
                }
            )
    return unresolved


def classify_risks(report: dict[str, Any]) -> list[dict[str, Any]]:
    risks: list[dict[str, Any]] = []
    densities = report["densities"]
    stages = report["stages"]
    occurrences = report["occurrences"]
    functions = report["functions"]

    streaming_groups = sorted({d["group"] for d in densities if d["streams"]})
    if "g" in streaming_groups or "h" in streaming_groups:
        risks.append(
            {
                "severity": "INFO",
                "id": "STREAMING_DENSITY",
                "message": "g/h are TCLB AddDensity streaming groups; do not treat them as explicit current arrays.",
                "evidence": [d for d in densities if d["group"] in {"g", "h"}][:6],
            }
        )

    for needle in ["STAGE13_PHASE_FOR_STENCIL", "WallGhost", "PhaseF = -999", "IsBoundary"]:
        if needle in occurrences:
            risks.append(
                {
                    "severity": "CHECK",
                    "id": f"OCCURS_{needle.replace(' ', '_')}",
                    "message": f"{needle} appears in source and must be traced through producer/consumer stages.",
                    "lines": occurrences[needle][:20],
                }
            )

    stage_names = [s["stage"] for s in stages]
    if "calcWall_CA" in stage_names and "BaseIter" in stage_names:
        risks.append(
            {
                "severity": "CHECK",
                "id": "WALL_BEFORE_ITER",
                "message": "calcWall_CA/calcWall stage exists before BaseIter in Dynamics.R order; verify fields loaded by BaseIter consume the intended wall ghost time level.",
                "stage_order": stage_names,
            }
        )

    for fn in ["calcGradPhi", "calcMu", "calcPhaseF", "Run", "BounceBack", "calcWallPhase"]:
        if fn in functions:
            risks.append(
                {
                    "severity": "CHECK",
                    "id": f"FUNCTION_{fn}",
                    "message": f"{fn} is present; inspect its field reads/writes when changing wetting semantics.",
                    "line": functions[fn]["line"],
                }
            )

    if "SPECIAL_POINT_HUGE_MAGIC_NUMBER" in occurrences:
        risks.append(
            {
                "severity": "HIGH",
                "id": "SPECIAL_POINT_MAGIC",
                "message": "Special-point magic values are present; confirm they cannot enter grad/laplace/mu stencils.",
                "lines": occurrences["SPECIAL_POINT_HUGE_MAGIC_NUMBER"][:20],
            }
        )

    return risks


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            serialised = {
                key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value
                for key, value in row.items()
            }
            writer.writerow(serialised)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    model_dir = args.model_dir
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    lattice_text = read(model_dir / "lattice.R")
    dynamics_r_text = read(model_dir / "Dynamics.R")
    dynamics_c_text = read(model_dir / "Dynamics.c.Rt")
    boundary_c_text = read(model_dir / "Boundary.c.Rt")
    combined_c = dynamics_c_text + "\n" + boundary_c_text
    functions_private = find_function_ranges(combined_c)
    actions = parse_actions(dynamics_r_text)
    fields = parse_fields(dynamics_r_text)
    densities = parse_lattice(lattice_text)
    stages = parse_stages(dynamics_r_text)
    function_access = scan_function_access(functions_private, FIELDS_OF_INTEREST + LOCAL_QUANTITIES + ["U", "V", "W", "pnorm"])
    stage_timeline = build_stage_timeline(stages, actions)
    fields_of_interest = build_fields_of_interest(densities, fields)
    producer_consumer_edges = build_producer_consumer_edges(stage_timeline)
    unresolved_edges = build_unresolved_edges(producer_consumer_edges, function_access)

    report: dict[str, Any] = {
        "model_dir": str(model_dir),
        "densities": densities,
        "fields": fields,
        "settings": parse_settings(dynamics_r_text),
        "stages": stages,
        "actions": actions,
        "stage_timeline": stage_timeline,
        "fields_of_interest": fields_of_interest,
        "producer_consumer_edges": producer_consumer_edges,
        "unresolved_edges": unresolved_edges,
        "function_access": function_access,
        "functions": public_function_map(functions_private),
        "occurrences": find_occurrences(
            combined_c,
            [
                "STAGE13_PHASE_FOR_STENCIL",
                "WallGhost",
                "PhaseF = -999",
                "SPECIAL_POINT_HUGE_MAGIC_NUMBER",
                "IsBoundary",
                "BounceBack",
                "calcWallPhase",
                "calcGradPhi",
                "calcMu",
                "WallCompactStencil",
                "DynamicCL",
            ],
        ),
    }
    report["risks"] = classify_risks(report)
    report["timeline_summary"] = {
        "geometric_iteration_order": [row["stage"] for row in stage_timeline],
        "field_count_of_interest": len(fields_of_interest),
        "producer_consumer_edge_count": len(producer_consumer_edges),
        "unresolved_edge_count": len(unresolved_edges),
        "mandatory_s2_diagnostics_needed": sorted(
            {
                row["quantity"]
                for row in unresolved_edges
                if row["severity"] != "COVERED"
                and row["quantity"] in {"mu", "F_surf", "F_pressure", "F_total", "gradPhi"}
            }
        ),
        "s2_replay_diagnostics_covered": sorted(
            {
                row["quantity"]
                for row in unresolved_edges
                if row["severity"] == "COVERED"
                and row["quantity"] in {"mu", "F_surf", "F_pressure", "F_total", "gradPhi"}
            }
        ),
        "s1_gate_status": "needs_review" if unresolved_edges else "mapped_no_unresolved_edges",
    }

    (out_dir / "tclb_execution_semantics_audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "timeline_summary.json").write_text(
        json.dumps(report["timeline_summary"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_csv(out_dir / "densities.csv", report["densities"])
    write_csv(out_dir / "fields.csv", report["fields"])
    write_csv(out_dir / "settings.csv", report["settings"])
    write_csv(out_dir / "stages.csv", report["stages"])
    write_csv(out_dir / "actions.csv", report["actions"])
    write_csv(out_dir / "stage_timeline.csv", report["stage_timeline"])
    write_csv(out_dir / "fields_of_interest.csv", report["fields_of_interest"])
    write_csv(out_dir / "producer_consumer_edges.csv", report["producer_consumer_edges"])
    write_csv(out_dir / "unresolved_edges.csv", report["unresolved_edges"])
    write_csv(out_dir / "function_access.csv", report["function_access"])
    write_csv(out_dir / "risks.csv", report["risks"])

    print(f"wrote {out_dir}")
    print(f"densities={len(report['densities'])} fields={len(report['fields'])} stages={len(report['stages'])} risks={len(report['risks'])}")
    print(
        "timeline_edges="
        f"{len(producer_consumer_edges)} unresolved={len(unresolved_edges)} "
        f"s1_gate_status={report['timeline_summary']['s1_gate_status']}"
    )
    high = [r for r in report["risks"] if r["severity"] in {"HIGH"}]
    if high:
        print("high_risks=" + ",".join(r["id"] for r in high))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
