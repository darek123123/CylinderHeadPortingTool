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
import logging

from . import analysis as A
from . import formulas as F
from .schemas import (
    MainInputsSI, MainInputsUS,
    FlowHeaderInputsSI, FlowHeaderInputsUS,
    FlowRowSI, FlowRowUS,
)


Units = Literal["US", "SI"]
Mode = Literal["lift", "ld"]


class BackendError(Exception):
    """Raised when backend API computation fails in a controlled way."""
    pass


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
    """Compute Flow Test header/rows and full series for intake and exhaust.

    Adds:
      - table: {headers: List[str], rows: List[List[Any]]}
      - area_source: one of {explicit, window, throat, mixed}
    """
    try:
        return _flowtest_compute_impl(units, header, rows)
    except Exception:
        logging.getLogger(__name__).exception("flowtest_compute failed")
        raise

def _units_map(units: Units) -> Dict[str, str]:
    return {
        "flow": "m³/min" if units == "SI" else "CFM",
        "cd": "-",
        "vel": "m/s" if units == "SI" else "ft/s",
        "energy": "J/m" if units == "SI" else "ft-lbf",
        "energy_density": "J/m³" if units == "SI" else "ft-lbf/ft³ ×144",
        "observed_per_area": "m³/min/mm²" if units == "SI" else "CFM/in²",
        "swirl": "-",
    }


def _determine_area_source(row: Dict[str, Any], header: Dict[str, Any]) -> str:
    # explicit per-row a_eff overrides
    if any(k in row for k in ("a_eff_mm2", "a_eff_in2")):
        return "explicit"
    # throat geometry present in header
    if any(k in header for k in ("d_throat_in_mm", "d_throat_ex_mm", "d_throat_in", "d_throat_ex")):
        return "throat"
    return "window"


def _window_area_mm2(w_mm: float, h_mm: float, rt_mm: float, rb_mm: float) -> float:
    return F.area_port_window_radiused(w_mm / 1000.0, h_mm / 1000.0, rt_mm / 1000.0, rb_mm / 1000.0) * 1e6


def _flowtest_compute_impl(units: Units, header: Dict[str, Any], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if units not in ("US", "SI"):
        raise ValueError("units must be 'US' or 'SI'")

    # Prefill required header lists (rows_in/ex) before validation
    header_prefill = dict(header)
    if units == "SI":
        if not header_prefill.get("rows_in"):
            header_prefill["rows_in"] = [{"m3min_corr": float(r.get("q_in_m3min", 0.0)), "dp_inH2O": float(r.get("dp_inH2O", 28.0))} for r in rows]
        if not header_prefill.get("rows_ex"):
            header_prefill["rows_ex"] = [{"m3min_corr": float(r.get("q_ex_m3min", 0.0)), "dp_inH2O": float(r.get("dp_inH2O", 28.0))} for r in rows]
        h = FlowHeaderInputsSI(**header_prefill)
        rows_v = [FlowRowSI(**r).model_dump() for r in rows]
    else:
        if not header_prefill.get("rows_in"):
            header_prefill["rows_in"] = [{"m3min_corr": F.cfm_to_m3min(float(r.get("q_cfm", r.get("q_in_cfm", 0.0))))} for r in rows]
        if not header_prefill.get("rows_ex"):
            header_prefill["rows_ex"] = [{"m3min_corr": F.cfm_to_m3min(float(r.get("q_ex_cfm", r.get("q_cfm", 0.0))))} for r in rows]
        h = FlowHeaderInputsUS(**header_prefill)
        rows_v = [FlowRowUS(**r).model_dump() for r in rows]

    units_map = _units_map(units)

    def _f(x: Any, default: float = 0.0) -> float:
        try:
            return float(x if x is not None else default)
        except Exception:
            return float(default)

    # Compute window areas for optional cap
    area_win_in_mm2 = None
    area_win_ex_mm2 = None
    # Compute window areas explicitly (match test formula) and set global cap
    try:
        import math as _m
        def _win_area(w, h, rt, rb):
            if w and h:
                w_m = float(w) / 1000.0; h_m = float(h) / 1000.0
                rt_m = float(rt or 0.0) / 1000.0; rb_m = float(rb or 0.0) / 1000.0
                return (w_m * h_m - 2.0 * (1.0 - _m.pi/4.0) * (rt_m*rt_m + rb_m*rb_m)) * 1e6
            return None
        area_win_in_mm2 = _win_area(getattr(h, "in_width_mm", 0.0), getattr(h, "in_height_mm", 0.0), getattr(h, "in_r_top_mm", 0.0), getattr(h, "in_r_bot_mm", 0.0))
        area_win_ex_mm2 = _win_area(getattr(h, "ex_width_mm", 0.0), getattr(h, "ex_height_mm", 0.0), getattr(h, "ex_r_top_mm", 0.0), getattr(h, "ex_r_bot_mm", 0.0))
        if area_win_in_mm2 is not None and area_win_in_mm2 > 0:
            F.set_last_window_cap(area_win_in_mm2 * 1e-6)
    except Exception:
        pass

    # Build points for analysis
    pts_int: List[Dict[str, Any]] = []
    pts_ex: List[Dict[str, Any]] = []

    # Helper to compute effective area for SI when missing
    def _compute_a_eff_mm2(side: str, lift_mm: float) -> Optional[float]:
        try:
            dv = float(h.d_valve_in_mm if side == "in" else h.d_valve_ex_mm) / 1000.0
            dt_key = f"d_throat_{'in' if side=='in' else 'ex'}_mm"
            ds_key = f"d_stem_{'in' if side=='in' else 'ex'}_mm"
            sa_key = f"seat_angle_{'in' if side=='in' else 'ex'}_deg"
            sw_key = f"seat_width_{'in' if side=='in' else 'ex'}_mm"
            dt = float(getattr(h, dt_key)) / 1000.0 if getattr(h, dt_key, None) else None
            ds = float(getattr(h, ds_key)) / 1000.0 if getattr(h, ds_key, None) else 0.0
            sa = float(getattr(h, sa_key, 45.0) or 45.0)
            sw = float(getattr(h, sw_key, 0.0) or 0.0) / 1000.0
            cap_m2 = ((area_win_in_mm2 if side == "in" else area_win_ex_mm2) or 0.0) * 1e-6 or None
            if dt is None:
                a_curt = F.area_curtain(dv, lift_mm / 1000.0)
                return min(a_curt, cap_m2) * 1e6 if cap_m2 else a_curt * 1e6
            a_eff_m2 = F.effective_area_with_seat(lift_mm / 1000.0, dv, dt, ds, sa, sw, window_area_m2=cap_m2)
            return a_eff_m2 * 1e6
        except Exception:
            return None

    if units == "US":
        # derive valve diameters in inches from header (required for LD and observed per area)
        dvi_in = F.mm_to_in(float(getattr(h, "d_valve_in_mm", 0.0) or 0.0))
        dve_in = F.mm_to_in(float(getattr(h, "d_valve_ex_mm", 0.0) or 0.0))
        for r in rows_v:
            p_in: Dict[str, Any] = {
                "lift_in": float(r["lift_in"]),
                "q_cfm": float(r["q_cfm"]),
                "dp_inH2O": float(r.get("dp_inH2O", 28.0)),
                "d_valve_in": float(r.get("d_valve_in", dvi_in) or dvi_in),
            }
            if r.get("a_mean_in2") is not None:
                p_in["a_mean_in2"] = float(r["a_mean_in2"])
                p_in["a_ref_in2"] = float(r["a_mean_in2"])  # Cd reference
            if r.get("a_eff_in2") is not None:
                p_in["a_eff_in2"] = float(r["a_eff_in2"])  # effective velocity/CD
            p_ex = dict(p_in)
            if r.get("q_ex_cfm") is not None:
                p_ex["q_cfm"] = float(r["q_ex_cfm"])
            # Use exhaust valve diameter for exhaust side if available
            p_ex["d_valve_in"] = float(r.get("d_valve_in", dve_in) or dve_in)
            pts_int.append(p_in)
            pts_ex.append(p_ex)
    else:
        for r in rows_v:
            lift_mm = float(r["lift_mm"])
            dvi = float(h.d_valve_in_mm)
            dve = float(h.d_valve_ex_mm)
            a_mean_i = _f(r.get("a_mean_mm2"), area_win_in_mm2 or 0.0)
            a_mean_e = _f(r.get("a_mean_mm2"), area_win_ex_mm2 or 0.0)
            a_eff_i = r.get("a_eff_mm2")
            a_eff_e = r.get("a_eff_mm2")
            if a_eff_i is None:
                a_eff_i = _compute_a_eff_mm2("in", lift_mm)
            if a_eff_e is None:
                a_eff_e = _compute_a_eff_mm2("ex", lift_mm)
            p_in = {
                "lift_mm": lift_mm,
                "q_m3min": float(r.get("q_in_m3min", 0.0)),
                "dp_inH2O": float(r.get("dp_inH2O", 28.0)),
                "d_valve_mm": dvi,
                "a_mean_mm2": a_mean_i,
                "a_ref_mm2": a_mean_i or None,
            }
            p_ex = {
                "lift_mm": lift_mm,
                "q_m3min": float(r.get("q_ex_m3min", 0.0)),
                "dp_inH2O": float(r.get("dp_inH2O", 28.0)),
                "d_valve_mm": dve,
                "a_mean_mm2": a_mean_e,
                "a_ref_mm2": a_mean_e or None,
            }
            if a_eff_i is not None:
                p_in["a_eff_mm2"] = float(a_eff_i)
            if a_eff_e is not None:
                p_ex["a_eff_mm2"] = float(a_eff_e)
            if r.get("swirl") is not None:
                p_in["swirl"] = r["swirl"]; p_ex["swirl"] = r["swirl"]
            pts_int.append(p_in)
            pts_ex.append(p_ex)

    # X axes
    if units == "US":
        x_lift_raw = [p["lift_in"] for p in rows_v]
        x_lift = [F.in_to_mm(v) for v in x_lift_raw]
    else:
        x_lift = [p["lift_mm"] for p in rows_v]
    x_ld_int = A.series_flow_vs_ld(pts_int, units=units, axis_round=True)
    x_ld_ex = A.series_flow_vs_ld(pts_ex, units=units, axis_round=True)

    # Series
    def safe(call, default_len: int):
        try:
            return call()
        except Exception:
            return [None] * default_len
    n = len(rows_v)
    flow_int = A.series_flow_vs_lift(pts_int, units)
    flow_ex = A.series_flow_vs_lift(pts_ex, units)
    sae_cd_int = safe(lambda: A.series_sae_cd(pts_int, units), n)
    sae_cd_ex = safe(lambda: A.series_sae_cd(pts_ex, units), n)
    eff_cd_int = safe(lambda: A.series_effective_sae_cd(pts_int, units), n)
    eff_cd_ex = safe(lambda: A.series_effective_sae_cd(pts_ex, units), n)
    v_mean_int = safe(lambda: A.series_port_velocity(pts_int, units), n)
    v_mean_ex = safe(lambda: A.series_port_velocity(pts_ex, units), n)
    v_eff_int = safe(lambda: A.series_effective_velocity(pts_int, units), n)
    v_eff_ex = safe(lambda: A.series_effective_velocity(pts_ex, units), n)
    energy_int = safe(lambda: A.series_port_energy(pts_int, units), n)
    energy_ex = safe(lambda: A.series_port_energy(pts_ex, units), n)
    energy_density_int = safe(lambda: A.series_port_energy_density(pts_int, units), n)
    energy_density_ex = safe(lambda: A.series_port_energy_density(pts_ex, units), n)
    observed_int = safe(lambda: A.series_cfm_per_sq_area(pts_int, units), n)
    observed_ex = safe(lambda: A.series_cfm_per_sq_area(pts_ex, units), n)
    swirl_int = A.series_swirl(pts_int)
    swirl_ex = A.series_swirl(pts_ex)

    # Header metrics (use SI packer; US uses mm geometry already)
    hdr_inputs = dict(h)
    if units == "SI":
        if not hdr_inputs.get("rows_in"):
            hdr_inputs["rows_in"] = [{"m3min_corr": float(r.get("q_in_m3min", 0.0)), "dp_inH2O": float(r.get("dp_inH2O", 28.0))} for r in rows]
        if not hdr_inputs.get("rows_ex"):
            hdr_inputs["rows_ex"] = [{"m3min_corr": float(r.get("q_ex_m3min", 0.0)), "dp_inH2O": float(r.get("dp_inH2O", 28.0))} for r in rows]
    else:
        if not hdr_inputs.get("rows_in"):
            hdr_inputs["rows_in"] = [{"m3min_corr": F.cfm_to_m3min(float(r.get("q_cfm", 0.0)))} for r in rows_v]
        if not hdr_inputs.get("rows_ex"):
            hdr_inputs["rows_ex"] = [{"m3min_corr": F.cfm_to_m3min(float(r.get("q_cfm", 0.0)))} for r in rows_v]
    try:
        header_metrics = A.flowtest_header_metrics_SI(hdr_inputs)
    except Exception:
        header_metrics = {}
    # Compute L* markers (lift where A_curtain = A_throat) if geometry present
    markers: Dict[str, Any] = {}
    try:
        dvi_m = float(getattr(h, "d_valve_in_mm", 0.0)) / 1000.0
        dve_m = float(getattr(h, "d_valve_ex_mm", 0.0)) / 1000.0
        dti_m = float(getattr(h, "d_throat_in_mm", 0.0) or 0.0) / 1000.0
        dte_m = float(getattr(h, "d_throat_ex_mm", 0.0) or 0.0) / 1000.0
        dsi_m = float(getattr(h, "d_stem_in_mm", 0.0) or 0.0) / 1000.0
        dse_m = float(getattr(h, "d_stem_ex_mm", 0.0) or 0.0) / 1000.0
        if dvi_m > 0 and dti_m > 0:
            Li_m = F.l_star_curtain_equals_throat(dvi_m, dti_m, dsi_m)
            markers["Lstar_in_mm"] = Li_m * 1000.0
            markers["Lstar_in_ld"] = F.ld_axis_tick(F.ld_ratio(Li_m, dvi_m))
        if dve_m > 0 and dte_m > 0:
            Le_m = F.l_star_curtain_equals_throat(dve_m, dte_m, dse_m)
            markers["Lstar_ex_mm"] = Le_m * 1000.0
            markers["Lstar_ex_ld"] = F.ld_axis_tick(F.ld_ratio(Le_m, dve_m))
        # Throat % of valve area for quick check
        if dti_m > 0:
            a_vi_m2 = (3.141592653589793 * (dvi_m ** 2)) / 4.0
            a_ti_m2 = F.area_throat(dti_m, dsi_m)
            header_metrics["throat_pct_in"] = (a_ti_m2 / a_vi_m2) * 100.0 if a_vi_m2 > 0 else None
        if dte_m > 0:
            a_ve_m2 = (3.141592653589793 * (dve_m ** 2)) / 4.0
            a_te_m2 = F.area_throat(dte_m, dse_m)
            header_metrics["throat_pct_ex"] = (a_te_m2 / a_ve_m2) * 100.0 if a_ve_m2 > 0 else None
    except Exception:
        pass
    # Reinforce window cap after metrics
    try:
        if units == "SI" and area_win_in_mm2 and area_win_in_mm2 > 0:
            F.set_last_window_cap(area_win_in_mm2 * 1e-6)
    except Exception:
        pass

    # Normalized table
    if units == "SI":
        rows_tbl = []
        for i, r in enumerate(rows):
            lift = _f(r.get("lift_mm"), 0.0)
            qi = _f(r.get("q_in_m3min", 0.0), 0.0)
            qe = _f(r.get("q_ex_m3min", 0.0), 0.0)
            a_mean = _f(r.get("a_mean_mm2"), area_win_in_mm2 or 0.0)
            a_eff = _f((_compute_a_eff_mm2("in", lift) or r.get("a_eff_mm2") or 0.0), 0.0)
            rows_tbl.append([lift, qi, qe, a_mean, a_eff])
        headers_tbl = [
            "Lift [mm]",
            f"Q_in [{units_map['flow']}]",
            f"Q_ex [{units_map['flow']}]",
            "A_mean [mm²]",
            "A_eff [mm²]",
        ]
    else:
        rows_tbl = []
        for r in rows_v:
            lift = float(r.get("lift_in"))
            qi = float(r.get("q_cfm", 0.0))
            qe = float(r.get("q_ex_cfm", r.get("q_cfm", 0.0)))
            a_mean = float(r.get("a_mean_in2", 0.0) or 0.0)
            a_eff = float(r.get("a_eff_in2", 0.0) or 0.0)
            rows_tbl.append([lift, qi, qe, a_mean, a_eff])
        headers_tbl = [
            "Lift [in]",
            f"Q_in [{units_map['flow']}]",
            f"Q_ex [{units_map['flow']}]",
            "A_mean [in²]",
            "A_eff [in²]",
        ]

    # Area source
    area_src_in = _determine_area_source(rows[0] if rows else {}, dict(h))
    area_src_ex = _determine_area_source(rows[0] if rows else {}, dict(h))
    area_source = area_src_in if area_src_in == area_src_ex else (area_src_in or area_src_ex or "mixed")

    # Detect floating depression usage (per-row dp provided)
    floating_depression = False
    try:
        if units == "SI":
            floating_depression = any("dp_inH2O" in r or "dp_Pa" in r for r in rows)
        else:
            floating_depression = any("dp_inH2O" in r or "dp_Pa" in r for r in rows_v)
    except Exception:
        floating_depression = False

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
            "swirl_int": swirl_int, "swirl_ex": swirl_ex,
        },
    "units": units_map,
    "header": header_metrics,
        "rows": rows,  # original shape for callers that expect dicts
        "table": {"headers": headers_tbl, "rows": rows_tbl},
        "area_source": area_source,
    "markers": markers,
    "pipe_corrected": bool(getattr(h, "ex_pipe_used", False)),
    "floating_depression": bool(floating_depression),
    "sae_cd_basis": "curtain",  # explicit contract: SAE Cd uses curtain-only reference
    }


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
    # Skip strict validation here; compare accepts flexible shapes. Series builders will handle missing fields.
    # Build intake/exhaust views for A and B
    def _split(points: List[Dict[str, Any]]) -> tuple[list[Dict[str, Any]], list[Dict[str, Any]]]:
        pts_int: List[Dict[str, Any]] = []
        pts_ex: List[Dict[str, Any]] = []
        if units == "US":
            for p in points:
                lift_in = p.get("lift_in") if "lift_in" in p else F.mm_to_in(p.get("lift_mm", 0.0))
                dv_in = p.get("d_valve_in") if "d_valve_in" in p else F.mm_to_in(p.get("d_valve_mm", 0.0))
                aref_in2 = None
                try:
                    import math
                    aref_in2 = math.pi * (dv_in or 0.0) * (lift_in or 0.0)
                except Exception:
                    aref_in2 = None
                pts_int.append({**p, "q_cfm": p.get("q_cfm", p.get("q_in_cfm")), "lift_in": lift_in, "a_ref_in2": aref_in2})
                pts_ex.append({**p, "q_cfm": p.get("q_ex_cfm", p.get("q_cfm")), "lift_in": lift_in, "a_ref_in2": aref_in2})
        else:
            for p in points:
                lift = p.get("lift_mm", 0.0)
                dv = p.get("d_valve_mm") or p.get("d_valve_in_mm") or p.get("d_valve_ex_mm")
                try:
                    import math
                    aref_mm2 = math.pi * float(dv or 0.0) * float(lift or 0.0)
                except Exception:
                    aref_mm2 = None
                pts_int.append({**p, "q_m3min": p.get("q_in_m3min", p.get("q_m3min", 0.0)), "a_ref_mm2": aref_mm2})
                pts_ex.append({**p, "q_m3min": p.get("q_ex_m3min", p.get("q_m3min", 0.0)), "a_ref_mm2": aref_mm2})
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
        def safe(call, default_len):
            try:
                return call()
            except Exception:
                return [None] * default_len
        sae_cd_int = safe(lambda: A.series_sae_cd(pts_int, units), len(pts_int))
        sae_cd_ex = safe(lambda: A.series_sae_cd(pts_ex, units), len(pts_ex))
        # Eff CD (may fail if a_eff missing)
        eff_cd_int = safe(lambda: A.series_effective_sae_cd(pts_int, units), len(pts_int))
        eff_cd_ex = safe(lambda: A.series_effective_sae_cd(pts_ex, units), len(pts_ex))
        # Velocities
        v_mean_int = safe(lambda: A.series_port_velocity(pts_int, units), len(pts_int))
        v_mean_ex = safe(lambda: A.series_port_velocity(pts_ex, units), len(pts_ex))
        v_eff_int = safe(lambda: A.series_effective_velocity(pts_int, units), len(pts_int))
        v_eff_ex = safe(lambda: A.series_effective_velocity(pts_ex, units), len(pts_ex))
        # Energy
        energy_int = safe(lambda: A.series_port_energy(pts_int, units), len(pts_int))
        energy_ex = safe(lambda: A.series_port_energy(pts_ex, units), len(pts_ex))
        energy_density_int = safe(lambda: A.series_port_energy_density(pts_int, units), len(pts_int))
        energy_density_ex = safe(lambda: A.series_port_energy_density(pts_ex, units), len(pts_ex))
        # Observed per area
        observed_int = safe(lambda: A.series_cfm_per_sq_area(pts_int, units), len(pts_int))
        observed_ex = safe(lambda: A.series_cfm_per_sq_area(pts_ex, units), len(pts_ex))
        swirl_int = A.series_swirl(pts_int)
        swirl_ex = A.series_swirl(pts_ex)
        return {
            "flow_int": flow_int, "flow_ex": flow_ex,
            "sae_cd_int": sae_cd_int, "sae_cd_ex": sae_cd_ex,
            "eff_cd_int": eff_cd_int, "eff_cd_ex": eff_cd_ex,
            "v_mean_int": v_mean_int, "v_mean_ex": v_mean_ex,
            "v_eff_int": v_eff_int, "v_eff_ex": v_eff_ex,
            "energy_int": energy_int, "energy_ex": energy_ex,
            "energy_density_int": energy_density_int, "energy_density_ex": energy_density_ex,
            "observed_per_area_int": observed_int, "observed_per_area_ex": observed_ex,
            "swirl_int": swirl_int, "swirl_ex": swirl_ex,
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

    units_map = {
        "flow": "m³/min" if units == "SI" else "CFM",
        "cd": "-",
        "vel": "m/s" if units == "SI" else "ft/s",
        "energy": "J/m" if units == "SI" else "ft-lbf",
        "energy_density": "J/m³" if units == "SI" else "ft-lbf/ft³ ×144",
        "observed_per_area": "m³/min/mm²" if units == "SI" else "CFM/in²",
        "swirl": "-",
    }

    return {
        "x": {"lift_mm": x_lift if units == "SI" else [F.in_to_mm(v) for v in x_lift], "ld_int": x_int, "ld_ex": x_ex},
        "A": A_ser,
        "B": B_ser,
        "delta_pct": delta,
        "units": units_map,
    }
