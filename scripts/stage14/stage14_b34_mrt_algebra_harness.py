#!/usr/bin/env python3
"""Stage14-B34 single-node MRT algebra harness.

The harness mirrors the active TCLB template algebra:

    mF[1:4] = scale * F_total / rho_eff
    m = m0 - (m0 - Req + 0.5*mF)[selR] * Omega + mF
    g = invM @ m
    momentum_after_g = sum(e_i * g_i)

It is intentionally local algebra only. It does not validate TCLB streaming,
stage load/save, or contact-angle physics.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np


D3Q27 = np.array(
    [
        [0, 0, 0],
        [1, 0, 0],
        [-1, 0, 0],
        [0, 1, 0],
        [0, -1, 0],
        [0, 0, 1],
        [0, 0, -1],
        [1, 1, 1],
        [-1, 1, 1],
        [1, -1, 1],
        [-1, -1, 1],
        [1, 1, -1],
        [-1, 1, -1],
        [1, -1, -1],
        [-1, -1, -1],
        [1, 1, 0],
        [-1, 1, 0],
        [1, -1, 0],
        [-1, -1, 0],
        [1, 0, 1],
        [-1, 0, 1],
        [1, 0, -1],
        [-1, 0, -1],
        [0, 1, 1],
        [0, -1, 1],
        [0, 1, -1],
        [0, -1, -1],
    ],
    dtype=float,
)


def moment_matrix() -> np.ndarray:
    u = D3Q27
    x = u[:, 0]
    y = u[:, 1]
    z = u[:, 2]
    abs_ci2 = x * x + y * y + z * z
    rows = [
        np.ones(27),
        x,
        y,
        z,
        x * y,
        y * z,
        z * x,
        3 * x * x - abs_ci2,
        y * y - z * z,
        abs_ci2 - 1,
        x * (3 * abs_ci2 - 5),
        y * (3 * abs_ci2 - 5),
        z * (3 * abs_ci2 - 5),
        x * (y * y - z * z),
        y * (z * z - x * x),
        z * (x * x - y * y),
        x * y * z,
        0.5 * (3 * abs_ci2 * abs_ci2 - 7 * abs_ci2 + 2),
        (3 * abs_ci2 - 4) * (3 * x * x - abs_ci2),
        (3 * abs_ci2 - 4) * (y * y - z * z),
        x * y * (3 * abs_ci2 - 7),
        y * z * (3 * abs_ci2 - 7),
        z * x * (3 * abs_ci2 - 7),
        0.5 * x * (9 * abs_ci2 * abs_ci2 - 33 * abs_ci2 + 26),
        0.5 * y * (9 * abs_ci2 * abs_ci2 - 33 * abs_ci2 + 26),
        0.5 * z * (9 * abs_ci2 * abs_ci2 - 33 * abs_ci2 + 26),
        0.5 * (9 * abs_ci2 * abs_ci2 * abs_ci2 - 36 * abs_ci2 * abs_ci2 + 33 * abs_ci2 - 2),
    ]
    return np.vstack(rows)


def omega_vector(tau: float) -> tuple[np.ndarray, np.ndarray]:
    # Mirrors Dynamics.c.Rt: selR = EQ$order < 10, then Omega[5:9]=tau^-1
    # and Omega[1:4]=1 in R's 1-based indexing. In the current moment basis,
    # the relaxed low-order set is rows 0..8.
    sel = np.zeros(27, dtype=bool)
    sel[:9] = True
    omega = np.ones(27)
    omega[4:9] = 1.0 / tau
    omega[0:4] = 1.0
    return sel, omega


def mrt_update(
    m0: np.ndarray,
    req: np.ndarray,
    force_over_rho: np.ndarray,
    tau: float,
    injection_scale: float = 1.0,
) -> dict[str, Any]:
    m0 = np.asarray(m0, dtype=float).reshape(27)
    req = np.asarray(req, dtype=float).reshape(27)
    force_over_rho = np.asarray(force_over_rho, dtype=float).reshape(3)
    sel, omega = omega_vector(tau)
    m_force = np.zeros(27)
    m_force[1:4] = injection_scale * force_over_rho
    m = m0.copy()
    m[sel] = m0[sel] - (m0[sel] - req[sel] + 0.5 * m_force[sel]) * omega[sel] + m_force[sel]
    inv_m = np.linalg.inv(moment_matrix())
    g_after = inv_m @ m
    momentum_after = D3Q27.T @ g_after
    return {
        "m_force": m_force.tolist(),
        "m_after": m.tolist(),
        "g_after": g_after.tolist(),
        "momentum_after_g": momentum_after.tolist(),
        "momentum_delta_g": (momentum_after - m0[1:4]).tolist(),
    }


def default_node() -> dict[str, Any]:
    m0 = np.zeros(27)
    m0[0] = 1.0
    req = np.zeros(27)
    req[0] = 1.0
    return {
        "m0": m0.tolist(),
        "req": req.tolist(),
        "force_over_rho": [0.01, -0.02, 0.03],
        "tau": 0.3,
        "injection_scale": 1.0,
    }


def load_node(path: Path | None) -> dict[str, Any]:
    if path is None:
        return default_node()
    return json.loads(path.read_text(encoding="utf-8"))


def compare(result: dict[str, Any], node: dict[str, Any], atol: float) -> dict[str, Any]:
    expected = node.get("expected")
    if not isinstance(expected, dict):
        return {"available": False}
    out: dict[str, Any] = {"available": True, "atol": atol, "fields": {}}
    for key in ("momentum_after_g", "momentum_delta_g"):
        if key not in expected:
            continue
        got = np.asarray(result[key], dtype=float)
        exp = np.asarray(expected[key], dtype=float)
        diff = got - exp
        out["fields"][key] = {
            "max_abs_diff": float(np.max(np.abs(diff))),
            "pass": bool(np.allclose(got, exp, atol=atol, rtol=0.0)),
            "got": got.tolist(),
            "expected": exp.tolist(),
        }
    out["pass"] = all(field["pass"] for field in out["fields"].values())
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node-json", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--atol", type=float, default=1.0e-10)
    args = parser.parse_args()

    node = load_node(args.node_json)
    result = mrt_update(
        np.asarray(node["m0"], dtype=float),
        np.asarray(node["req"], dtype=float),
        np.asarray(node["force_over_rho"], dtype=float),
        float(node["tau"]),
        float(node.get("injection_scale", 1.0)),
    )
    report = {
        "claim_limit": "single-node MRT algebra only; no TCLB streaming or contact-angle validation",
        "input": node,
        "result": result,
        "comparison": compare(result, node, args.atol),
        "matrix_condition": float(np.linalg.cond(moment_matrix())),
        "source_formula": "Dynamics.c.Rt lines near mF[2:4] and m=m0-(m0-EQ+0.5*mF)*Omega+mF",
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not report["comparison"].get("available") or report["comparison"].get("pass") else 2


if __name__ == "__main__":
    raise SystemExit(main())
