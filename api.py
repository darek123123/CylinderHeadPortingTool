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

from typing import Dict, List, Literal, Any, Optional

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
    """Compute Flow Test header/rows and full series for intake and exhaust."""
    import math
    if units == "SI":
        # Validate
        _ = FlowHeaderInputsSI(**header)
        _ = [FlowRowSI(**r) for r in rows]
        header_metrics = A.flowtest_header_metrics_SI({**header})
        table_rows = A.flowtest_tables_SI(rows)
        # Points per side
        x_lift = [float(r.get("lift_mm", 0.0)) for r in rows]
        d_in = float(header.get("d_valve_in_mm", 0.0))
        d_ex = float(header.get("d_valve_ex_mm", 0.0))
        pts_int = []
        pts_ex = []
        for r in rows:
            lift = float(r.get("lift_mm", 0.0))
            dp = float(r.get("dp_inH2O", 28.0))
            pts_int.append({
                "q_m3min": float(r.get("q_in_m3min", 0.0)),
                "a_ref_mm2": math.pi * d_in * lift,
                "dp_inH2O": dp,
                "a_mean_mm2": r.get("a_mean_mm2"),
                "a_eff_mm2": r.get("a_eff_mm2"),
                "lift_mm": lift,
                "d_valve_mm": d_in,
            })
            pts_ex.append({
                "q_m3min": float(r.get("q_ex_m3min", 0.0)),
                "a_ref_mm2": math.pi * d_ex * lift,
                "dp_inH2O": dp,
                "a_mean_mm2": r.get("a_mean_mm2"),
                "a_eff_mm2": r.get("a_eff_mm2"),
                "lift_mm": lift,
                "d_valve_mm": d_ex,
            })
        # X axes
        x_ld_int = A.series_flow_vs_ld(pts_int, units="SI", axis_round=True)
        x_ld_ex = A.series_flow_vs_ld(pts_ex, units="SI", axis_round=True)
        # Series
        def safe(call, default_len):
            try:
                return call()
            except Exception:
                return [None] * default_len
        flow_int = A.series_flow_vs_lift(pts_int, "SI")
        flow_ex = A.series_flow_vs_lift(pts_ex, "SI")
        sae_cd_int = A.series_sae_cd(pts_int, "SI")
        sae_cd_ex = A.series_sae_cd(pts_ex, "SI")
        eff_cd_int = safe(lambda: A.series_effective_sae_cd(pts_int, "SI"), len(pts_int))
        eff_cd_ex = safe(lambda: A.series_effective_sae_cd(pts_ex, "SI"), len(pts_ex))
        v_mean_int = safe(lambda: A.series_port_velocity(pts_int, "SI"), len(pts_int))
        v_mean_ex = safe(lambda: A.series_port_velocity(pts_ex, "SI"), len(pts_ex))
        v_eff_int = safe(lambda: A.series_effective_velocity(pts_int, "SI"), len(pts_int))
        v_eff_ex = safe(lambda: A.series_effective_velocity(pts_ex, "SI"), len(pts_ex))
        energy_int = A.series_port_energy(pts_int, "SI")
        energy_ex = A.series_port_energy(pts_ex, "SI")
        energy_density_int = A.series_port_energy_density(pts_int, "SI")
        energy_density_ex = A.series_port_energy_density(pts_ex, "SI")
        observed_int = A.series_cfm_per_sq_area(pts_int, "SI")
        observed_ex = A.series_cfm_per_sq_area(pts_ex, "SI")
        units_map = {
            "flow": "m³/min",
            "vel": "m/s",
            "energy": "J/m",
            "energy_density": "J/m³",
            "observed_per_area": "m³/min/mm²",
            "cd": "-",
        }
        return {
            "x": {"lift_mm": x_lift, "ld_int": x_ld_int, "ld_ex": x_ld_ex},
            "series": {
                "flow_int": flow_int, "flow_ex": flow_ex,
                "sae_cd_int": sae_cd_int, "sae_cd_ex": sae_cd_ex,
                "eff_cd_int": eff_cd_int, "eff_cd_ex": eff_cd_ex,
                "v_mean_int": v_mean_int, "v_mean_ex": v_mean_ex,
                "v_eff_int": v_eff_int, "v_eff_ex": v_eff_ex,
                "energy_int": energy_int, "energy_ex": energy_ex,
                "energy_density_int": energy_density_int, "energy_density_ex": energy_density_ex,
                "observed_per_area_int": observed_int, "observed_per_area_ex": observed_ex,
            },
            "units": units_map,
            "header": header_metrics,
            "rows": table_rows,
        }
    elif units == "US":
        # Validate
        _ = FlowHeaderInputsUS(**header)
        _ = [FlowRowUS(**r) for r in rows]
        # Convert to SI-like rows then compute series in SI units for consistency
        si_rows: List[Dict[str, Any]] = []
        for r in rows:
            lift_mm = F.in_to_mm(r["lift_in"]) if "lift_in" in r else r.get("lift_mm", 0.0)
            q_in_m3min = F.cfm_to_m3min(r.get("q_cfm", r.get("q_in_cfm", 0.0)))
            q_ex_m3min = F.cfm_to_m3min(r.get("q_ex_cfm", r.get("q_cfm", 0.0)))
            dp_in = r.get("dp_inH2O", 28.0)
            d_valve_mm = header.get("d_valve_in_mm", 0.0)
            si_rows.append({
                "lift_mm": lift_mm,
                "q_in_m3min": q_in_m3min,
                "q_ex_m3min": q_ex_m3min,
                "dp_inH2O": dp_in,
                "d_valve_mm": d_valve_mm,
                **({"a_mean_mm2": F.in2_to_mm2(r["a_mean_in2"]) } if "a_mean_in2" in r else {}),
                **({"a_eff_mm2": F.in2_to_mm2(r["a_eff_in2"]) } if "a_eff_in2" in r else {}),
            })
        hdr_si = {**header}
        hdr_si.setdefault("rows_in", [])
        hdr_si.setdefault("rows_ex", [])
        hdr_si["rows_in"] = [{"m3min_corr": p["q_in_m3min"], "dp_inH2O": p.get("dp_inH2O", 28.0)} for p in si_rows]
        hdr_si["rows_ex"] = [{"m3min_corr": p["q_ex_m3min"], "dp_inH2O": p.get("dp_inH2O", 28.0)} for p in si_rows]
        header_metrics = A.flowtest_header_metrics_SI(hdr_si)
        table_rows = A.flowtest_tables_SI(si_rows)
        # Build points per side (SI shape)
        import math
        x_lift = [float(r.get("lift_mm", 0.0)) for r in si_rows]
        d_in = float(header.get("d_valve_in_mm", 0.0))
        d_ex = float(header.get("d_valve_ex_mm", 0.0))
        pts_int = []
        pts_ex = []
        for r in si_rows:
            lift = float(r.get("lift_mm", 0.0))
            dp = float(r.get("dp_inH2O", 28.0))
            pts_int.append({
                "q_m3min": float(r.get("q_in_m3min", 0.0)),
                "a_ref_mm2": math.pi * d_in * lift,
                "dp_inH2O": dp,
                "a_mean_mm2": r.get("a_mean_mm2"),
                "a_eff_mm2": r.get("a_eff_mm2"),
                "lift_mm": lift,
                "d_valve_mm": d_in,
            })
            pts_ex.append({
                "q_m3min": float(r.get("q_ex_m3min", 0.0)),
                "a_ref_mm2": math.pi * d_ex * lift,
                "dp_inH2O": dp,
                "a_mean_mm2": r.get("a_mean_mm2"),
                "a_eff_mm2": r.get("a_eff_mm2"),
                "lift_mm": lift,
                "d_valve_mm": d_ex,
            })
        x_ld_int = A.series_flow_vs_ld(pts_int, units="SI", axis_round=True)
        x_ld_ex = A.series_flow_vs_ld(pts_ex, units="SI", axis_round=True)
        # Series (SI units for consistency)
        def safe(call, default_len):
            try:
                return call()
            except Exception:
                return [None] * default_len
        flow_int = A.series_flow_vs_lift(pts_int, "SI")
        flow_ex = A.series_flow_vs_lift(pts_ex, "SI")
        sae_cd_int = A.series_sae_cd(pts_int, "SI")
        sae_cd_ex = A.series_sae_cd(pts_ex, "SI")
        eff_cd_int = safe(lambda: A.series_effective_sae_cd(pts_int, "SI"), len(pts_int))
        eff_cd_ex = safe(lambda: A.series_effective_sae_cd(pts_ex, "SI"), len(pts_ex))
        v_mean_int = safe(lambda: A.series_port_velocity(pts_int, "SI"), len(pts_int))
        v_mean_ex = safe(lambda: A.series_port_velocity(pts_ex, "SI"), len(pts_ex))
        v_eff_int = safe(lambda: A.series_effective_velocity(pts_int, "SI"), len(pts_int))
        v_eff_ex = safe(lambda: A.series_effective_velocity(pts_ex, "SI"), len(pts_ex))
        energy_int = A.series_port_energy(pts_int, "SI")
        energy_ex = A.series_port_energy(pts_ex, "SI")
        energy_density_int = A.series_port_energy_density(pts_int, "SI")
        energy_density_ex = A.series_port_energy_density(pts_ex, "SI")
        observed_int = A.series_cfm_per_sq_area(pts_int, "SI")
        observed_ex = A.series_cfm_per_sq_area(pts_ex, "SI")
        units_map = {
            "flow": "m³/min",
            "vel": "m/s",
            "energy": "J/m",
            "energy_density": "J/m³",
            "observed_per_area": "m³/min/mm²",
            "cd": "-",
        }
        return {
            "x": {"lift_mm": x_lift, "ld_int": x_ld_int, "ld_ex": x_ld_ex},
            "series": {
                "flow_int": flow_int, "flow_ex": flow_ex,
                "sae_cd_int": sae_cd_int, "sae_cd_ex": sae_cd_ex,
                "eff_cd_int": eff_cd_int, "eff_cd_ex": eff_cd_ex,
                "v_mean_int": v_mean_int, "v_mean_ex": v_mean_ex,
                "v_eff_int": v_eff_int, "v_eff_ex": v_eff_ex,
                "energy_int": energy_int, "energy_ex": energy_ex,
                "energy_density_int": energy_density_int, "energy_density_ex": energy_density_ex,
                "observed_per_area_int": observed_int, "observed_per_area_ex": observed_ex,
            },
            "units": units_map,
            "header": header_metrics,
            "rows": table_rows,
        }
    else:
        raise ValueError("units must be 'US' or 'SI'")


def compare_tests(
        units: Units,
        mode: Mode,
        A_points: List[Dict[str, Any]],
        B_points: List[Dict[str, Any]],
        metric: Optional[str] = None,
) -> Dict[str, Any]:
    """Compare two flow tests across key series for intake/exhaust, with optional metric focus.

    Returns:
        {
            "x": {"lift_mm": [...], "ld_int": [...], "ld_ex": [...]},
            "A": { full series like flowtest_compute["series"] },
            "B": { ... },
            "delta_pct": {same keys as series, elementwise %Δ with None for B==0}
        }
    """
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
    # Build intake/exhaust views for A and B
    def _split(points: List[Dict[str, Any]]) -> tuple[list[Dict[str, Any]], list[Dict[str, Any]]]:
        pts_int: List[Dict[str, Any]] = []
        pts_ex: List[Dict[str, Any]] = []
        if units == "US":
            for p in points:
                lift_in = p.get("lift_in") if "lift_in" in p else F.mm_to_in(p.get("lift_mm", 0.0))
                pts_int.append({**p, "q_cfm": p.get("q_cfm", p.get("q_in_cfm")), "lift_in": lift_in})
                pts_ex.append({**p, "q_cfm": p.get("q_ex_cfm", p.get("q_cfm")), "lift_in": lift_in})
        else:
            for p in points:
                pts_int.append({**p, "q_m3min": p.get("q_in_m3min", p.get("q_m3min", 0.0))})
                pts_ex.append({**p, "q_m3min": p.get("q_ex_m3min", p.get("q_m3min", 0.0))})
        return pts_int, pts_ex

    A_int, A_ex = _split(A_points)
    B_int, B_ex = _split(B_points)

    # X axes
    if mode == "ld":
        x_int = A.series_flow_vs_ld(A_int, units=units, axis_round=True)
        x_ex = A.series_flow_vs_ld(A_ex, units=units, axis_round=True)
    else:
        x_int = [p["lift_in"] if units == "US" else p["lift_mm"] for p in A_points]
        x_ex = [p["lift_in"] if units == "US" else p["lift_mm"] for p in A_points]
    x_lift = [p["lift_in"] if units == "US" else p["lift_mm"] for p in A_points]

    def _series_pack(pts_int: List[Dict[str, Any]], pts_ex: List[Dict[str, Any]]):
        # Flow
        flow_int = A.series_flow_vs_lift(pts_int, units)
        flow_ex = A.series_flow_vs_lift(pts_ex, units)
        # SAE CD
        sae_cd_int = A.series_sae_cd(pts_int, units)
        sae_cd_ex = A.series_sae_cd(pts_ex, units)
        # Eff CD (may fail if a_eff missing)
        try:
            eff_cd_int = A.series_effective_sae_cd(pts_int, units)
        except Exception:
            eff_cd_int = [None] * len(pts_int)
        try:
            eff_cd_ex = A.series_effective_sae_cd(pts_ex, units)
        except Exception:
            eff_cd_ex = [None] * len(pts_ex)
        # Velocities
        try:
            v_mean_int = A.series_port_velocity(pts_int, units)
        except Exception:
            v_mean_int = [None] * len(pts_int)
        try:
            v_mean_ex = A.series_port_velocity(pts_ex, units)
        except Exception:
            v_mean_ex = [None] * len(pts_ex)
        try:
            v_eff_int = A.series_effective_velocity(pts_int, units)
        except Exception:
            v_eff_int = [None] * len(pts_int)
        try:
            v_eff_ex = A.series_effective_velocity(pts_ex, units)
        except Exception:
            v_eff_ex = [None] * len(pts_ex)
        # Energy
        energy_int = A.series_port_energy(pts_int, units)
        energy_ex = A.series_port_energy(pts_ex, units)
        energy_density_int = A.series_port_energy_density(pts_int, units)
        energy_density_ex = A.series_port_energy_density(pts_ex, units)
        # Observed per area
        observed_int = A.series_cfm_per_sq_area(pts_int, units)
        observed_ex = A.series_cfm_per_sq_area(pts_ex, units)
        return {
            "flow_int": flow_int, "flow_ex": flow_ex,
            "sae_cd_int": sae_cd_int, "sae_cd_ex": sae_cd_ex,
            "eff_cd_int": eff_cd_int, "eff_cd_ex": eff_cd_ex,
            "v_mean_int": v_mean_int, "v_mean_ex": v_mean_ex,
            "v_eff_int": v_eff_int, "v_eff_ex": v_eff_ex,
            "energy_int": energy_int, "energy_ex": energy_ex,
            "energy_density_int": energy_density_int, "energy_density_ex": energy_density_ex,
            "observed_per_area_int": observed_int, "observed_per_area_ex": observed_ex,
        }

    A_ser = _series_pack(A_int, A_ex)
    B_ser = _series_pack(B_int, B_ex)

    def _pct(a: List[Optional[float]], b: List[Optional[float]]):
        out: List[Optional[float]] = []
        for aa, bb in zip(a, b):
            if aa is None or bb is None or bb == 0:
                out.append(None)
            else:
                out.append(((aa - bb) / bb) * 100.0)
        return out

    delta = {k: _pct(A_ser[k], B_ser[k]) for k in A_ser.keys()}

    return {
        "x": {"lift_mm": x_lift if units == "SI" else [F.in_to_mm(v) for v in x_lift], "ld_int": x_int, "ld_ex": x_ex},
        "A": A_ser,
        "B": B_ser,
        "delta_pct": delta,
    }
