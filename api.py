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
        return {"units": units, "header": header_metrics, "rows": table_rows}

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
        return {"units": units, "header": header_metrics, "rows": table_rows}

    raise ValueError("units must be 'US' or 'SI'")


def compare_tests(units: Units, mode: Mode, A_points: List[Dict[str, Any]], B_points: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compare two flow tests across key series (Flow, CD, v, energy, etc.)."""
    if units not in ("US", "SI"):
        raise ValueError("units must be 'US' or 'SI'")
    if mode not in ("lift", "ld"):
        raise ValueError("mode must be 'lift' or 'ld'")
    # Lightweight validation using FlowRow* models; extra fields allowed
    if units == "US":
        _ = [FlowRowUS(**p) for p in A_points]
        _ = [FlowRowUS(**p) for p in B_points]
    else:
        _ = [FlowRowSI(**p) for p in A_points]
        _ = [FlowRowSI(**p) for p in B_points]
    return A.compare_two_tests(A_points, B_points, mode=mode, units=units)
