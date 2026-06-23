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


def find_occurrences(text: str, needles: list[str]) -> dict[str, list[int]]:
    found: dict[str, list[int]] = {}
    for needle in needles:
        lines = [i + 1 for i, line in enumerate(text.splitlines()) if needle in line]
        if lines:
            found[needle] = lines
    return found


def find_functions(text: str) -> dict[str, dict[str, Any]]:
    funcs: dict[str, dict[str, Any]] = {}
    pat = re.compile(r"CudaDeviceFunction\s+[A-Za-z0-9_*\s]+\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(")
    for m in pat.finditer(text):
        name = m.group("name")
        start = m.start()
        funcs[name] = {"line": line_of(text, start)}
    return funcs


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

    report: dict[str, Any] = {
        "model_dir": str(model_dir),
        "densities": parse_lattice(lattice_text),
        "fields": parse_fields(dynamics_r_text),
        "settings": parse_settings(dynamics_r_text),
        "stages": parse_stages(dynamics_r_text),
        "functions": find_functions(combined_c),
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

    (out_dir / "tclb_execution_semantics_audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_csv(out_dir / "densities.csv", report["densities"])
    write_csv(out_dir / "fields.csv", report["fields"])
    write_csv(out_dir / "settings.csv", report["settings"])
    write_csv(out_dir / "stages.csv", report["stages"])
    write_csv(out_dir / "risks.csv", report["risks"])

    print(f"wrote {out_dir}")
    print(f"densities={len(report['densities'])} fields={len(report['fields'])} stages={len(report['stages'])} risks={len(report['risks'])}")
    high = [r for r in report["risks"] if r["severity"] in {"HIGH"}]
    if high:
        print("high_risks=" + ",".join(r["id"] for r in high))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
