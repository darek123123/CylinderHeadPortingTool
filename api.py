"""
Thin, stable API for the UI layer.

Contracts (do not change signatures during UI work):
  - compute_main_screen(units, inputs) -> dict
  - flowtest_compute(units, header, rows) -> dict
  - compare_tests(units, mode, A, B) -> dict

All functions require an explicit units parameter: "US" or "SI".
Validation is performed via Pydantic schemas where applicable.
"""
from __future__ import annotations

from typing import Dict, List, Literal, Any

from . import analysis as A
from . import formulas as F
from .schemas import (
    MainInputsSI, MainInputsUS,
    FlowHeaderInputsSI, FlowHeaderInputsUS,
    FlowRowSI, FlowRowUS,
)


Units = Literal["US", "SI"]
Mode = Literal["lift", "ld"]


def compute_main_screen(units: Units, inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Compute "Main" screen outputs. Units must be specified (US/SI)."""
    if units == "SI":
        _ = MainInputsSI(**inputs)  # validate
        return A.compute_main_screen_SI(inputs)
    elif units == "US":
        _ = MainInputsUS(**inputs)  # validate
        return A.compute_main_screen_US(inputs)
    else:
        raise ValueError("units must be 'US' or 'SI'")


def flowtest_compute(units: Units, header: Dict[str, Any], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute Flow Test header metrics and per-row table for given units.

    Returns a dict with keys: header (metrics dict), rows (list with computed columns), units.
    """
    if units == "SI":
        # Validate
        _ = FlowHeaderInputsSI(**header)
        _ = [FlowRowSI(**r) for r in rows]
        header_metrics = A.flowtest_header_metrics_SI({**header})
        table_rows = A.flowtest_tables_SI(rows)
        # Build series for UI (Flow and additional metrics intake/exhaust, x axes)
        x_lift = [r.get("lift_mm", 0.0) for r in rows]
        x_ld = A.series_flow_vs_ld(rows, units="SI", axis_round=True)
        # Intake/exhaust flows
        flow_in = [r.get("q_in_m3min", 0.0) for r in rows]
        flow_ex = [r.get("q_ex_m3min", 0.0) for r in rows]
        # SAE CD requires a_ref and dp; compute curtain as reference for each side
        import math
        d_in = float(header.get("d_valve_in_mm", 0.0))
        d_ex = float(header.get("d_valve_ex_mm", 0.0))
        pts_in = []
        pts_ex = []
        for r in rows:
            lift = float(r.get("lift_mm", 0.0))
            dp = float(r.get("dp_inH2O", 28.0))
            a_ref_in_mm2 = math.pi * d_in * lift  # curtain approx in mm^2
            a_ref_ex_mm2 = math.pi * d_ex * lift
            pts_in.append({
                "q_m3min": float(r.get("q_in_m3min", 0.0)),
                "a_ref_mm2": a_ref_in_mm2,
                "dp_inH2O": dp,
                "a_mean_mm2": r.get("a_mean_mm2"),
                "a_eff_mm2": r.get("a_eff_mm2"),
                "lift_mm": lift,
                "d_valve_mm": d_in,
            })
            pts_ex.append({
                "q_m3min": float(r.get("q_ex_m3min", 0.0)),
                "a_ref_mm2": a_ref_ex_mm2,
                "dp_inH2O": dp,
                "a_mean_mm2": r.get("a_mean_mm2"),
                "a_eff_mm2": r.get("a_eff_mm2"),
                "lift_mm": lift,
                "d_valve_mm": d_ex,
            })
        saecd_in = A.series_sae_cd(pts_in, units="SI")
        saecd_ex = A.series_sae_cd(pts_ex, units="SI")
        # Effective SAE CD (if a_eff present)
        try:
            effcd_in = A.series_effective_sae_cd(pts_in, units="SI")
            effcd_ex = A.series_effective_sae_cd(pts_ex, units="SI")
        except Exception:
            effcd_in = []
            effcd_ex = []
        # Velocities (intake mean/effective)
        v_mean = A.series_port_velocity(pts_in, units="SI")
        try:
            v_eff = A.series_effective_velocity(pts_in, units="SI")
        except Exception:
            v_eff = []
        # Energy and energy density (intake)
        energy = A.series_port_energy(pts_in, units="SI")
        energy_density = A.series_port_energy_density(pts_in, units="SI")
        # Observed per area (curtain) intake
        obs_area = A.series_cfm_per_sq_area(pts_in, units="SI")
        return {
            "units": units,
            "header": header_metrics,
            "rows": table_rows,
            "series": {
                "x_lift": x_lift,
                "x_ld": x_ld,
                "flow_in": flow_in,
                "flow_ex": flow_ex,
                "saecd_in": saecd_in,
                "saecd_ex": saecd_ex,
                "effcd_in": effcd_in,
                "effcd_ex": effcd_ex,
                "v_mean": v_mean,
                "v_eff": v_eff,
                "energy": energy,
                "energy_density": energy_density,
                "observed_area": obs_area,
            },
        }

    if units == "US":
        # Validate and map to SI-compatible shapes under the hood
        _ = FlowHeaderInputsUS(**header)
        _ = [FlowRowUS(**r) for r in rows]

        # Prepare SI-like rows with both intake and exhaust if available
        si_rows: List[Dict[str, Any]] = []
        for r in rows:
            lift_mm = F.in_to_mm(r["lift_in"]) if "lift_in" in r else r.get("lift_mm", 0.0)
            q_in_m3min = F.cfm_to_m3min(r["q_cfm"]) if "q_cfm" in r else r.get("q_in_m3min", 0.0)
            q_ex_m3min = F.cfm_to_m3min(r.get("q_ex_cfm", 0.0)) if "q_ex_cfm" in r else r.get("q_ex_m3min", 0.0)
            dp_in = r.get("dp_inH2O", 28.0)
            d_valve_mm = header.get("d_valve_in_mm", 0.0)
            si_rows.append({
                "lift_mm": lift_mm,
                "q_in_m3min": q_in_m3min,
                "q_ex_m3min": q_ex_m3min,
                "dp_inH2O": dp_in,
                "d_valve_mm": d_valve_mm,
                # allow optional mean/eff areas if provided
                **({"a_mean_mm2": F.in2_to_mm2(r["a_mean_in2"]) } if "a_mean_in2" in r else {}),
                **({"a_eff_mm2": F.in2_to_mm2(r["a_eff_in2"]) } if "a_eff_in2" in r else {}),
            })

        # Build a header compatible with SI routine, include per-row corrected totals for ratio metrics
        hdr_si = {**header}
        hdr_si.setdefault("rows_in", [])
        hdr_si.setdefault("rows_ex", [])
        hdr_si["rows_in"] = [{"m3min_corr": r["q_in_m3min"], "dp_inH2O": r.get("dp_inH2O", 28.0)} for r in si_rows]
        hdr_si["rows_ex"] = [{"m3min_corr": r["q_ex_m3min"], "dp_inH2O": r.get("dp_inH2O", 28.0)} for r in si_rows]

        header_metrics = A.flowtest_header_metrics_SI(hdr_si)
        table_rows = A.flowtest_tables_SI(si_rows)
        # X axes
        x_lift = [r.get("lift_mm", 0.0) for r in si_rows]
        x_ld = A.series_flow_vs_ld(si_rows, units="SI", axis_round=True)
        flow_in = [r.get("q_in_m3min", 0.0) for r in si_rows]
        flow_ex = [r.get("q_ex_m3min", 0.0) for r in si_rows]
        import math
        d_in = float(header.get("d_valve_in_mm", 0.0))
        d_ex = float(header.get("d_valve_ex_mm", 0.0))
        pts_in = []
        pts_ex = []
        for r in si_rows:
            lift = float(r.get("lift_mm", 0.0))
            dp = float(r.get("dp_inH2O", 28.0))
            a_ref_in_mm2 = math.pi * d_in * lift
            a_ref_ex_mm2 = math.pi * d_ex * lift
            pts_in.append({
                "q_m3min": float(r.get("q_in_m3min", 0.0)),
                "a_ref_mm2": a_ref_in_mm2,
                "dp_inH2O": dp,
                "a_mean_mm2": r.get("a_mean_mm2"),
                "a_eff_mm2": r.get("a_eff_mm2"),
                "lift_mm": lift,
                "d_valve_mm": d_in,
            })
            pts_ex.append({
                "q_m3min": float(r.get("q_ex_m3min", 0.0)),
                "a_ref_mm2": a_ref_ex_mm2,
                "dp_inH2O": dp,
                "a_mean_mm2": r.get("a_mean_mm2"),
                "a_eff_mm2": r.get("a_eff_mm2"),
                "lift_mm": lift,
                "d_valve_mm": d_ex,
            })
        saecd_in = A.series_sae_cd(pts_in, units="SI")
        saecd_ex = A.series_sae_cd(pts_ex, units="SI")
        try:
            effcd_in = A.series_effective_sae_cd(pts_in, units="SI")
            effcd_ex = A.series_effective_sae_cd(pts_ex, units="SI")
        except Exception:
            effcd_in = []
            effcd_ex = []
        v_mean = A.series_port_velocity(pts_in, units="SI")
        try:
            v_eff = A.series_effective_velocity(pts_in, units="SI")
        except Exception:
            v_eff = []
        energy = A.series_port_energy(pts_in, units="SI")
        energy_density = A.series_port_energy_density(pts_in, units="SI")
        obs_area = A.series_cfm_per_sq_area(pts_in, units="SI")
        return {
            "units": units,
            "header": header_metrics,
            "rows": table_rows,
            "series": {
                "x_lift": x_lift,
                "x_ld": x_ld,
                "flow_in": flow_in,
                "flow_ex": flow_ex,
                "saecd_in": saecd_in,
                "saecd_ex": saecd_ex,
                "effcd_in": effcd_in,
                "effcd_ex": effcd_ex,
                "v_mean": v_mean,
                "v_eff": v_eff,
                "energy": energy,
                "energy_density": energy_density,
                "observed_area": obs_area,
            },
        }

    raise ValueError("units must be 'US' or 'SI'")


def compare_tests(units: Units, mode: Mode, A_points: List[Dict[str, Any]], B_points: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compare two flow tests across key series (Flow, CD, v, energy, etc.)."""
    if units not in ("US", "SI"):
        raise ValueError("units must be 'US' or 'SI'")
    if mode not in ("lift", "ld"):
        raise ValueError("mode must be 'lift' or 'ld'")
    # Normalize points: allow SI rows with q_in_m3min/q_ex_m3min and fill q_m3min if missing.
    def _norm(points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out = []
        for p in points:
            q = p.get("q_m3min")
            if units == "SI" and q is None:
                # Prefer intake flow as default; if missing, try exhaust
                q = p.get("q_in_m3min", p.get("q_ex_m3min"))
                if q is not None:
                    p = {**p, "q_m3min": q}
            # Ensure d_valve key is present for LD if needed; try both in/ex
            if units == "SI" and "d_valve_mm" not in p:
                dv = p.get("d_valve_mm") or p.get("d_valve_in_mm") or p.get("d_valve_ex_mm")
                if dv is not None:
                    p = {**p, "d_valve_mm": dv}
            out.append(p)
        return out
    A_points = _norm(A_points)
    B_points = _norm(B_points)
    # Lightweight validation using FlowRow* models; extra fields allowed
    if units == "US":
        _ = [FlowRowUS(**p) for p in A_points]
        _ = [FlowRowUS(**p) for p in B_points]
    else:
        _ = [FlowRowSI(**p) for p in A_points]
        _ = [FlowRowSI(**p) for p in B_points]
    return A.compare_two_tests(A_points, B_points, mode=mode, units=units)
