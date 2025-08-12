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
    # Points per side
        x_lift = [float(r.get("lift_mm", 0.0)) for r in rows]
        d_in = float(header.get("d_valve_in_mm", 0.0))
        d_ex = float(header.get("d_valve_ex_mm", 0.0))
        pts_int: List[Dict[str, Any]] = []
        pts_ex: List[Dict[str, Any]] = []
        # Pre-compute geometry-derived mean areas (intake/exhaust)
        # Prefer explicit port_area_mm2 if provided; else compute from window; else throat
        try:
            a_mean_in_m2 = None
            a_mean_ex_m2 = None
            if header.get("port_area_mm2"):
                a_mean_in_m2 = float(header["port_area_mm2"]) * 1e-6
                a_mean_ex_m2 = a_mean_in_m2
            # Window areas
            win_in_m2 = F.area_port_window_radiused(
                float(header.get("in_width_mm", 0.0)) / 1000.0,
                float(header.get("in_height_mm", 0.0)) / 1000.0,
                float(header.get("in_r_top_mm", 0.0)) / 1000.0,
                float(header.get("in_r_bot_mm", 0.0)) / 1000.0,
                model="rect_with_2r",
            ) if header.get("in_width_mm") and header.get("in_height_mm") else None
            win_ex_m2 = F.area_port_window_radiused(
                float(header.get("ex_width_mm", 0.0)) / 1000.0,
                float(header.get("ex_height_mm", 0.0)) / 1000.0,
                float(header.get("ex_r_top_mm", 0.0)) / 1000.0,
                float(header.get("ex_r_bot_mm", 0.0)) / 1000.0,
                model="rect_with_2r",
            ) if header.get("ex_width_mm") and header.get("ex_height_mm") else None
            # Throat areas
            thr_in_m2 = None
            thr_ex_m2 = None
            if header.get("d_throat_in_mm"):
                thr_in_m2 = F.area_throat(float(header.get("d_throat_in_mm", 0.0))/1000.0, float(header.get("d_stem_in_mm", 0.0))/1000.0)
            if header.get("d_throat_ex_mm"):
                thr_ex_m2 = F.area_throat(float(header.get("d_throat_ex_mm", 0.0))/1000.0, float(header.get("d_stem_ex_mm", 0.0))/1000.0)
            # Resolve means
            if a_mean_in_m2 is None:
                a_mean_in_m2 = win_in_m2 or thr_in_m2
            if a_mean_ex_m2 is None:
                a_mean_ex_m2 = win_ex_m2 or thr_ex_m2
        except Exception:
            a_mean_in_m2 = None
            a_mean_ex_m2 = None
            win_in_m2 = None
            win_ex_m2 = None
            thr_in_m2 = None
            thr_ex_m2 = None
        for r in rows:
            lift = float(r.get("lift_mm", 0.0))
            dp = float(r.get("dp_inH2O", 28.0))
            # Row-level mean area (use row if provided, else derived)
            r_a_mean_mm2 = r.get("a_mean_mm2")
            pts_int.append({
                "q_m3min": float(r.get("q_in_m3min", 0.0)),
                "a_ref_mm2": math.pi * d_in * lift,
                "dp_inH2O": dp,
                "a_mean_mm2": r_a_mean_mm2 if r_a_mean_mm2 else (a_mean_in_m2 * 1e6 if a_mean_in_m2 else None),
                "a_eff_mm2": None,  # always compute below from geometry
                "lift_mm": lift,
                "d_valve_mm": d_in,
                "swirl": r.get("swirl"),
            })
            pts_ex.append({
                "q_m3min": float(r.get("q_ex_m3min", 0.0)),
                "a_ref_mm2": math.pi * d_ex * lift,
                "dp_inH2O": dp,
                "a_mean_mm2": r_a_mean_mm2 if r_a_mean_mm2 else (a_mean_ex_m2 * 1e6 if a_mean_ex_m2 else None),
                "a_eff_mm2": None,
                "lift_mm": lift,
                "d_valve_mm": d_ex,
                "swirl": r.get("swirl"),
            })
        # Always compute A_eff from geometry (min-rule) and cap by window
        try:
            dv_in = float(header.get("d_valve_in_mm", 0.0)) / 1000.0
            dt_in = float(header.get("d_throat_in_mm", 0.0)) / 1000.0
            ds_in = float(header.get("d_stem_in_mm", 0.0)) / 1000.0
            sa_in = float(header.get("seat_angle_in_deg", 0.0))
            sw_in = float(header.get("seat_width_in_mm", 0.0)) / 1000.0
            dv_ex_m = float(header.get("d_valve_ex_mm", 0.0)) / 1000.0
            dt_ex = float(header.get("d_throat_ex_mm", 0.0)) / 1000.0
            ds_ex = float(header.get("d_stem_ex_mm", 0.0)) / 1000.0
            sa_ex = float(header.get("seat_angle_ex_deg", 0.0))
            sw_ex = float(header.get("seat_width_ex_mm", 0.0)) / 1000.0
            if dv_in > 0 and dt_in > 0 and sa_in > 0 and sw_in >= 0:
                for p in pts_int:
                    a = F.effective_area_min_model(p["lift_mm"]/1000.0, dv_in, dt_in, ds_in, sa_in, sw_in, win_in_m2 if 'win_in_m2' in locals() else None)
                    p["a_eff_mm2"] = a * 1e6
            if dv_ex_m > 0 and dt_ex > 0 and sa_ex > 0 and sw_ex >= 0:
                for p in pts_ex:
                    a = F.effective_area_min_model(p["lift_mm"]/1000.0, dv_ex_m, dt_ex, ds_ex, sa_ex, sw_ex, win_ex_m2 if 'win_ex_m2' in locals() else None)
                    p["a_eff_mm2"] = a * 1e6
        except Exception:
            pass
        # Build table rows after enriching areas; prefer intake-side areas for single-column display
        rows_for_table: List[Dict[str, Any]] = []
        for i, r in enumerate(rows):
            base = {**r}
            if not base.get("d_valve_mm"):
                base["d_valve_mm"] = float(header.get("d_valve_in_mm", 0.0))
            # Prefer derived intake mean/eff if missing in row
            if not base.get("a_mean_mm2") and i < len(pts_int):
                if pts_int[i].get("a_mean_mm2"):
                    base["a_mean_mm2"] = pts_int[i]["a_mean_mm2"]
            if not base.get("a_eff_mm2") and i < len(pts_int):
                if pts_int[i].get("a_eff_mm2"):
                    base["a_eff_mm2"] = pts_int[i]["a_eff_mm2"]
            rows_for_table.append(base)
        table_rows = A.flowtest_tables_SI(rows_for_table)
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
        energy_int = safe(lambda: A.series_port_energy(pts_int, "SI"), len(pts_int))
        energy_ex = safe(lambda: A.series_port_energy(pts_ex, "SI"), len(pts_ex))
        energy_density_int = safe(lambda: A.series_port_energy_density(pts_int, "SI"), len(pts_int))
        energy_density_ex = safe(lambda: A.series_port_energy_density(pts_ex, "SI"), len(pts_ex))
        observed_int = safe(lambda: A.series_cfm_per_sq_area(pts_int, "SI"), len(pts_int))
        observed_ex = safe(lambda: A.series_cfm_per_sq_area(pts_ex, "SI"), len(pts_ex))
        swirl_int = A.series_swirl(pts_int)
        swirl_ex = A.series_swirl(pts_ex)
        units_map = {
            "flow": "m³/min",
            "vel": "m/s",
            "energy": "J/m",
            "energy_density": "J/m³",
            "observed_per_area": "m³/min/mm²",
            "cd": "-",
            "swirl": "-",
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
                "swirl_int": swirl_int, "swirl_ex": swirl_ex,
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
        # Build points per side (SI shape)
        x_lift = [float(r.get("lift_mm", 0.0)) for r in si_rows]
        d_in = float(header.get("d_valve_in_mm", 0.0))
        d_ex = float(header.get("d_valve_ex_mm", 0.0))
        pts_int: List[Dict[str, Any]] = []
        pts_ex: List[Dict[str, Any]] = []
        # Pre-compute mean areas and window caps in SI
        try:
            a_mean_in_m2 = None
            a_mean_ex_m2 = None
            if header.get("port_area_mm2"):
                a = float(header["port_area_mm2"]) * 1e-6
                a_mean_in_m2 = a
                a_mean_ex_m2 = a
            win_in_m2 = F.area_port_window_radiused(
                float(header.get("in_width_mm", 0.0))/1000.0,
                float(header.get("in_height_mm", 0.0))/1000.0,
                float(header.get("in_r_top_mm", 0.0))/1000.0,
                float(header.get("in_r_bot_mm", 0.0))/1000.0,
            ) if header.get("in_width_mm") and header.get("in_height_mm") else None
            win_ex_m2 = F.area_port_window_radiused(
                float(header.get("ex_width_mm", 0.0))/1000.0,
                float(header.get("ex_height_mm", 0.0))/1000.0,
                float(header.get("ex_r_top_mm", 0.0))/1000.0,
                float(header.get("ex_r_bot_mm", 0.0))/1000.0,
            ) if header.get("ex_width_mm") and header.get("ex_height_mm") else None
            thr_in_m2 = F.area_throat(float(header.get("d_throat_in_mm", 0.0))/1000.0, float(header.get("d_stem_in_mm", 0.0))/1000.0) if header.get("d_throat_in_mm") else None
            thr_ex_m2 = F.area_throat(float(header.get("d_throat_ex_mm", 0.0))/1000.0, float(header.get("d_stem_ex_mm", 0.0))/1000.0) if header.get("d_throat_ex_mm") else None
            if a_mean_in_m2 is None:
                a_mean_in_m2 = win_in_m2 or thr_in_m2
            if a_mean_ex_m2 is None:
                a_mean_ex_m2 = win_ex_m2 or thr_ex_m2
        except Exception:
            a_mean_in_m2 = None
            a_mean_ex_m2 = None
            win_in_m2 = None
            win_ex_m2 = None
        for r in si_rows:
            lift = float(r.get("lift_mm", 0.0))
            dp = float(r.get("dp_inH2O", 28.0))
            pts_int.append({
                "q_m3min": float(r.get("q_in_m3min", 0.0)),
                "a_ref_mm2": math.pi * d_in * lift,
                "dp_inH2O": dp,
                "a_mean_mm2": r.get("a_mean_mm2") or (a_mean_in_m2 * 1e6 if a_mean_in_m2 else None),
                "a_eff_mm2": None,
                "lift_mm": lift,
                "d_valve_mm": d_in,
                "swirl": r.get("swirl"),
            })
            pts_ex.append({
                "q_m3min": float(r.get("q_ex_m3min", 0.0)),
                "a_ref_mm2": math.pi * d_ex * lift,
                "dp_inH2O": dp,
                "a_mean_mm2": r.get("a_mean_mm2") or (a_mean_ex_m2 * 1e6 if a_mean_ex_m2 else None),
                "a_eff_mm2": None,
                "lift_mm": lift,
                "d_valve_mm": d_ex,
                "swirl": r.get("swirl"),
            })
        # Derive effective area using min-rule and cap by window
        try:
            dv_in = float(header.get("d_valve_in_mm", 0.0)) / 1000.0
            dt_in = float(header.get("d_throat_in_mm", 0.0)) / 1000.0
            ds_in = float(header.get("d_stem_in_mm", 0.0)) / 1000.0
            sa_in = float(header.get("seat_angle_in_deg", 0.0))
            sw_in = float(header.get("seat_width_in_mm", 0.0)) / 1000.0
            dv_ex_m = float(header.get("d_valve_ex_mm", 0.0)) / 1000.0
            dt_ex = float(header.get("d_throat_ex_mm", 0.0)) / 1000.0
            ds_ex = float(header.get("d_stem_ex_mm", 0.0)) / 1000.0
            sa_ex = float(header.get("seat_angle_ex_deg", 0.0))
            sw_ex = float(header.get("seat_width_ex_mm", 0.0)) / 1000.0
            for p in pts_int:
                if dv_in > 0 and dt_in > 0 and sa_in > 0 and sw_in >= 0:
                    a = F.effective_area_min_model(p["lift_mm"]/1000.0, dv_in, dt_in, ds_in, sa_in, sw_in, win_in_m2 if 'win_in_m2' in locals() else None)
                    p["a_eff_mm2"] = a * 1e6
            for p in pts_ex:
                if dv_ex_m > 0 and dt_ex > 0 and sa_ex > 0 and sw_ex >= 0:
                    a = F.effective_area_min_model(p["lift_mm"]/1000.0, dv_ex_m, dt_ex, ds_ex, sa_ex, sw_ex, win_ex_m2 if 'win_ex_m2' in locals() else None)
                    p["a_eff_mm2"] = a * 1e6
        except Exception:
            pass
        # Build table rows (intake-side areas as display)
        rows_for_table: List[Dict[str, Any]] = []
        for i, r in enumerate(si_rows):
            base = {**r}
            if not base.get("d_valve_mm"):
                base["d_valve_mm"] = float(header.get("d_valve_in_mm", 0.0))
            if not base.get("a_mean_mm2") and i < len(pts_int) and pts_int[i].get("a_mean_mm2"):
                base["a_mean_mm2"] = pts_int[i]["a_mean_mm2"]
            if not base.get("a_eff_mm2") and i < len(pts_int) and pts_int[i].get("a_eff_mm2"):
                base["a_eff_mm2"] = pts_int[i]["a_eff_mm2"]
            rows_for_table.append(base)
        table_rows = A.flowtest_tables_SI(rows_for_table)
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
        energy_int = safe(lambda: A.series_port_energy(pts_int, "SI"), len(pts_int))
        energy_ex = safe(lambda: A.series_port_energy(pts_ex, "SI"), len(pts_ex))
        energy_density_int = safe(lambda: A.series_port_energy_density(pts_int, "SI"), len(pts_int))
        energy_density_ex = safe(lambda: A.series_port_energy_density(pts_ex, "SI"), len(pts_ex))
        observed_int = safe(lambda: A.series_cfm_per_sq_area(pts_int, "SI"), len(pts_int))
        observed_ex = safe(lambda: A.series_cfm_per_sq_area(pts_ex, "SI"), len(pts_ex))
        swirl_int = A.series_swirl(pts_int)
        swirl_ex = A.series_swirl(pts_ex)
        units_map = {
            "flow": "m³/min",
            "vel": "m/s",
            "energy": "J/m",
            "energy_density": "J/m³",
            "observed_per_area": "m³/min/mm²",
            "cd": "-",
            "swirl": "-",
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
                "swirl_int": swirl_int, "swirl_ex": swirl_ex,
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
