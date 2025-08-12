# --- SI Flow Test series and header/table packers ---
def series_in_ex_ratio_per_point(test_rows):
    """Return [Q_ex / Q_in] for each row (per-point In/Ex flow ratio)."""
    return [F.in_ex_ratio_per_point(r["q_in_m3min"], r["q_ex_m3min"]) for r in test_rows]

def series_observed_per_sq_mm(test_rows):
    """Return observed_per_sq_mm(q_m3min, d_valve_mm, lift_mm) for each row."""
    return [F.observed_per_sq_mm(r["q_in_m3min"], r["d_valve_mm"], r["lift_mm"]) for r in test_rows]

def flowtest_header_metrics_SI(inputs: dict) -> dict:
    """Return dict of header metrics for SI Flow Test Page 1/2."""
    # Required: port window dims, valve dims, mean areas, etc.
    # Inputs: width/height/radii for in/ex, valve diameters, etc.
    # All units mm or mm^2.
    # Port window area (rect_with_2r model)
    area_window_in_mm2 = F.area_port_window_radiused(
        inputs["in_width_mm"], inputs["in_height_mm"], inputs["in_r_top_mm"], inputs["in_r_bot_mm"], model="rect_with_2r") * 1e6
    area_window_ex_mm2 = F.area_port_window_radiused(
        inputs["ex_width_mm"], inputs["ex_height_mm"], inputs["ex_r_top_mm"], inputs["ex_r_bot_mm"], model="rect_with_2r") * 1e6
    valve_area_in_mm2 = F.piston_area_mm2(inputs["d_valve_in_mm"])
    valve_area_ex_mm2 = F.piston_area_mm2(inputs["d_valve_ex_mm"])
    area_ratio_in = F.area_ratio(area_window_in_mm2, valve_area_in_mm2)
    area_ratio_ex = F.area_ratio(area_window_ex_mm2, valve_area_ex_mm2)
    quarterD_in_mm = F.quarter_D_mm(inputs["d_valve_in_mm"])
    quarterD_ex_mm = F.quarter_D_mm(inputs["d_valve_ex_mm"])
    avg_m3min_in = F.avg_m3min(inputs["rows_in"])
    avg_m3min_ex = F.avg_m3min(inputs["rows_ex"])
    total_m3min_in = F.total_m3min(inputs["rows_in"])
    total_m3min_ex = F.total_m3min(inputs["rows_ex"])
    # Convert max_lift_mm to inches for required_ex_int_ratio calibration
    max_lift_in = inputs["max_lift_mm"] / 25.4
    required_ratio = F.required_ex_int_ratio(inputs["cr"], max_lift_in)
    existing_ratio = F.existing_ex_int_ratio(avg_m3min_ex, avg_m3min_in)
    return dict(
        area_window_in_mm2=area_window_in_mm2,
        area_window_ex_mm2=area_window_ex_mm2,
        valve_area_in_mm2=valve_area_in_mm2,
        valve_area_ex_mm2=valve_area_ex_mm2,
        area_ratio_in=area_ratio_in,
        area_ratio_ex=area_ratio_ex,
        quarterD_in_mm=quarterD_in_mm,
        quarterD_ex_mm=quarterD_ex_mm,
        avg_m3min_in=avg_m3min_in,
        avg_m3min_ex=avg_m3min_ex,
        total_m3min_in=total_m3min_in,
        total_m3min_ex=total_m3min_ex,
        required_ratio=required_ratio,
        existing_ratio=existing_ratio,
    )

def flowtest_tables_SI(test_rows):
    """Return list-of-dict for all columns of Flow Test Page 1/2 (SI)."""
    # This is a stub: in practice, would map all formulas to columns as per screenshots.
    # For now, just return the input rows with computed columns added.
    out = []
    for r in test_rows:
        row = dict(r)
        row["observed_per_sq_mm"] = F.observed_per_sq_mm(r["q_in_m3min"], r["d_valve_mm"], r["lift_mm"])
        row["in_ex_ratio"] = F.in_ex_ratio_per_point(r["q_in_m3min"], r["q_ex_m3min"])
        out.append(row)
    return out
"""
Series generators for FLOW/IOP graphs (backend-only). Returns lists; no plotting.
Uses formulas and centralized calibration constants.
"""
from typing import List, Dict, Literal
from . import formulas as F
from .calibration import A0_FT_S, A0_M_S, RHO_SLUG_FT3, RHO_KGM3_STD

# Minimal shape for a flow test point used by series generators
# Each point is a dict with keys at minimum: lift_in (or lift_mm), q_cfm (or q_m3min),
# a_mean_in2 (or a_mean_mm2), dp_inH2O (or dp_Pa), rho (kg/m^3), d_valve_in/mm, d_stem_in/mm, d_throat_in/mm


def series_flow_vs_lift(points: List[Dict], units: Literal["US", "SI"] = "US") -> List[float]:
    key_q = "q_cfm" if units == "US" else "q_m3min"
    return [p[key_q] for p in points]


def series_cfm28_vs_lift(points: List[Dict], units: Literal["US", "SI"] = "US") -> List[float]:
    """Flow referenced to 28" H2O vs lift.
    For US: returns CFM@28; requires dp_inH2O and AirState-like inputs optional.
    For SI: returns m^3/min@28; accepts dp_Pa or dp_inH2O.
    Minimal: if air states missing, assume standard air for both measured and reference.
    """
    out: List[float] = []
    for p in points:
        # Build AirState from optional fields; fall back to standard
        meas = F.AirState(101325.0, F.C_to_K(20.0), 0.0)
        ref = meas
        dp_in = p.get("dp_inH2O")
        dp_pa = p.get("dp_Pa")
        if dp_in is None and dp_pa is None:
            dp_in = 28.0
        if units == "US":
            q_m3s = F.cfm_to_m3s(p["q_cfm"]) if "q_cfm" in p else F.cfm_to_m3s(F.m3min_to_cfm(p["q_m3min"]))
            dp_meas_in = dp_in if dp_in is not None else F.pa_to_in_h2o(dp_pa)
            q28_m3s = F.flow_to_28inH2O(q_m3s, dp_meas_in, meas, ref)
            out.append(F.m3s_to_cfm(q28_m3s))
        else:
            q_m3s = (p["q_m3min"] / 60.0) if "q_m3min" in p else F.cfm_to_m3s(p["q_cfm"])
            dp_meas_in = dp_in if dp_in is not None else F.pa_to_in_h2o(dp_pa)
            q28_m3s = F.flow_to_28inH2O(q_m3s, dp_meas_in, meas, ref)
            out.append(q28_m3s * 60.0)
    return out


def series_flow_vs_ld(points: List[Dict], units: Literal["US", "SI"] = "US", axis_round: bool = True) -> List[float]:
    vals = []
    if units == "US":
        for p in points:
            ld = F.ld_ratio(p["lift_in"], p["d_valve_in"])  # lift and d in same units
            vals.append(F.ld_axis_tick(ld) if axis_round else ld)
    else:
        for p in points:
            ld = F.ld_ratio(p["lift_mm"], p["d_valve_mm"])
            vals.append(F.ld_axis_tick(ld) if axis_round else ld)
    return vals


def series_cfm_per_sq_in(points: List[Dict]) -> List[float]:
    return [F.observed_cfm_per_sq_in(p["q_cfm"], p["d_valve_in"], p["lift_in"]) for p in points]


def series_cfm_per_sq_mm(points: List[Dict]) -> List[float]:
    return [F.observed_per_sq_mm(p["q_m3min"], p["d_valve_mm"], p["lift_mm"]) for p in points]


def series_cfm_per_sq_area(points: List[Dict], units: Literal["US","SI"]) -> List[float]:
    """Observed per area on the curtain: US→CFM/in², SI→m³/min/mm²."""
    return series_cfm_per_sq_in(points) if units == "US" else series_cfm_per_sq_mm(points)


def series_sae_cd(points: List[Dict], units: Literal["US", "SI"] = "US") -> List[float]:
    cds = []
    for p in points:
        if units == "US":
            a_ref_m2 = F.mm2_to_in2(p["a_ref_mm2"])  # If provided in mm^2, convert; else require m^2
            # Prefer a_ref in m^2 for SAE; for simplicity accept provided 'a_ref_m2'
            a_ref = p.get("a_ref_m2")
            if a_ref is None:
                a_ref = (p["a_ref_mm2"]) * 1e-6
            q_m3s = F.cfm_to_m3s(p["q_cfm"])
            dp_Pa = F.in_h2o_to_pa(p["dp_inH2O"]) if "dp_inH2O" in p else F.in_h2o_to_pa(28.0)
            rho = p.get("rho_kgm3", 1.225)
            cds.append(F.cd(q_m3s, a_ref, dp_Pa, rho))
        else:
            q_m3s = p["q_m3min"] / 60.0
            a_ref = (p["a_ref_mm2"]) * 1e-6
            dp_Pa = p.get("dp_Pa", F.in_h2o_to_pa(28.0))
            rho = p.get("rho_kgm3", 1.225)
            cds.append(F.cd(q_m3s, a_ref, dp_Pa, rho))
    return cds


def series_effective_sae_cd(points: List[Dict], units: Literal["US", "SI"] = "US") -> List[float]:
    cds = []
    for p in points:
        if units == "US":
            cds.append(F.effective_sae_cd(p["q_cfm"], p.get("dp_inH2O", 28.0), p.get("rho_kgm3", 1.225), p["a_eff_in2"]))
        else:
            # Convert to US helper by converting A_eff to in^2 and Q to CFM
            a_eff_in2 = F.mm2_to_in2(p["a_eff_mm2"]) if "a_eff_mm2" in p else p["a_eff_in2"]
            q_cfm = F.m3min_to_cfm(p["q_m3min"]) if "q_m3min" in p else p["q_cfm"]
            cds.append(F.effective_sae_cd(q_cfm, p.get("dp_inH2O", 28.0), p.get("rho_kgm3", 1.225), a_eff_in2))
    return cds


def series_ld_ratio(points: List[Dict], units: Literal["US", "SI"] = "US", axis_round: bool = True) -> List[float]:
    vals = []
    if units == "US":
        for p in points:
            ld = F.ld_ratio(p["lift_in"], p["d_valve_in"])  # lift and d in same units
            vals.append(F.ld_axis_tick(ld) if axis_round else ld)
    else:
        for p in points:
            ld = F.ld_ratio(p["lift_mm"], p["d_valve_mm"])
            vals.append(F.ld_axis_tick(ld) if axis_round else ld)
    return vals


def series_port_velocity(points: List[Dict], units: Literal["US", "SI"] = "US") -> List[float]:
    vals = []
    for p in points:
        if units == "US":
            vals.append(F.port_velocity(p["q_cfm"], p["a_mean_in2"]))
        else:
            q_cfm = F.m3min_to_cfm(p["q_m3min"]) if "q_m3min" in p else p["q_cfm"]
            a_in2 = F.mm2_to_in2(p["a_mean_mm2"]) if "a_mean_mm2" in p else p["a_mean_in2"]
            vals.append(F.port_velocity(q_cfm, a_in2))
    return vals


def series_effective_velocity(points: List[Dict], units: Literal["US", "SI"] = "US") -> List[float]:
    vals = []
    for p in points:
        if units == "US":
            vals.append(F.effective_velocity(p["q_cfm"], p["a_eff_in2"]))
        else:
            q_cfm = F.m3min_to_cfm(p["q_m3min"]) if "q_m3min" in p else p["q_cfm"]
            a_in2 = F.mm2_to_in2(p["a_eff_mm2"]) if "a_eff_mm2" in p else p["a_eff_in2"]
            vals.append(F.effective_velocity(q_cfm, a_in2))
    return vals


def series_port_energy_density(points: List[Dict], units: Literal["US", "SI"] = "US") -> List[float]:
    vals = []
    for p in points:
        if units == "US":
            v = F.port_velocity(p["q_cfm"], p["a_mean_in2"])  # ft/s
            vals.append(F.port_energy_density_gui_ftlbs_per_in2ft(F.RHO_SLUG_FT3, v))
        else:
            v_ms = F.fts_to_ms(F.port_velocity(F.m3min_to_cfm(p["q_m3min"]), F.mm2_to_in2(p["a_mean_mm2"])) )
            vals.append(F.port_energy_density_si_j_per_m3(1.225, v_ms))
    return vals


def series_port_energy(points: List[Dict], units: Literal["US", "SI"] = "US") -> List[float]:
    vals = []
    for p in points:
        if units == "US":
            v = F.port_velocity(p["q_cfm"], p["a_mean_in2"])  # ft/s
            vals.append(F.port_energy_gui_ftlbs(p["a_mean_in2"], v))
        else:
            v_ms = F.fts_to_ms(F.port_velocity(F.m3min_to_cfm(p["q_m3min"]), F.mm2_to_in2(p["a_mean_mm2"])) )
            e_density = F.port_energy_density_si_j_per_m3(1.225, v_ms)
            vals.append(e_density * (p["a_mean_mm2"] * 1e-6))
    return vals


def series_swirl(points: List[Dict]) -> List[float]:
    return [p.get("swirl", 0.0) for p in points]


def series_percent(points_A: List[Dict], points_B: List[Dict], metric: str, mode: Literal["lift", "ld"] = "lift") -> List[float]:
    vals: List[float] = []
    for a, b in zip(points_A, points_B):
        va = a[metric]
        vb = b[metric]
        if vb == 0:
            vals.append(None)  # protected division
        else:
            vals.append(F.percent_change(va, vb))
    return vals


def compare_two_tests(testA: List[Dict], testB: List[Dict], *, mode: Literal["lift","ld"] = "lift", units: Literal["US","SI"] = "SI") -> Dict[str, List[float]]:
    """Aggregate comparison for two flow tests returning A, B and %Δ series for key metrics."""
    # X-axis
    xA = [p["lift_in"] if units == "US" else p["lift_mm"] for p in testA]
    xB = [p["lift_in"] if units == "US" else p["lift_mm"] for p in testB]
    if mode == "ld":
        xA = series_flow_vs_ld(testA, units, axis_round=True)
        xB = series_flow_vs_ld(testB, units, axis_round=True)
    # Flow
    flowA = series_flow_vs_lift(testA, units)
    flowB = series_flow_vs_lift(testB, units)
    # Observed per area
    areaA = series_cfm_per_sq_area(testA, units)
    areaB = series_cfm_per_sq_area(testB, units)
    # SAE CD
    cdA = series_sae_cd(testA, units)
    cdB = series_sae_cd(testB, units)
    effcdA = series_effective_sae_cd(testA, units)
    effcdB = series_effective_sae_cd(testB, units)
    # Velocities
    vA = series_port_velocity(testA, units)
    vB = series_port_velocity(testB, units)
    veA = series_effective_velocity(testA, units)
    veB = series_effective_velocity(testB, units)
    # Energy
    eA = series_port_energy(testA, units)
    eB = series_port_energy(testB, units)
    edA = series_port_energy_density(testA, units)
    edB = series_port_energy_density(testB, units)
    # Swirl
    sA = series_swirl(testA)
    sB = series_swirl(testB)

    def pct(a, b):
        out = []
        for aa, bb in zip(a, b):
            out.append(None if bb == 0 else F.percent_change(aa, bb))
        return out

    return {
        "xA": xA, "xB": xB,
        "flowA": flowA, "flowB": flowB, "flowPct": pct(flowA, flowB),
        "areaA": areaA, "areaB": areaB, "areaPct": pct(areaA, areaB),
        "cdA": cdA, "cdB": cdB, "cdPct": pct(cdA, cdB),
        "effcdA": effcdA, "effcdB": effcdB, "effcdPct": pct(effcdA, effcdB),
        "velA": vA, "velB": vB, "velPct": pct(vA, vB),
        "effvelA": veA, "effvelB": veB, "effvelPct": pct(veA, veB),
        "energyA": eA, "energyB": eB, "energyPct": pct(eA, eB),
        "energyDensityA": edA, "energyDensityB": edB, "energyDensityPct": pct(edA, edB),
        "swirlA": sA, "swirlB": sB,
    }


# =============================
# Main screen computations (SI/US)
# =============================

def compute_main_screen_SI(inputs: Dict) -> Dict:
    """Compute SI Main screen outputs from inputs.
    Required keys in inputs:
      mach, mean_port_area_mm2, bore_mm, stroke_mm, n_cyl, ve, n_ports_eff, cr
    """
    mach = float(inputs["mach"])  # 0..1
    Amean_mm2 = float(inputs["mean_port_area_mm2"])  # mm^2
    bore_mm = float(inputs["bore_mm"])  # mm
    stroke_mm = float(inputs["stroke_mm"])  # mm
    n_cyl = int(inputs["n_cyl"])  # count
    ve = float(inputs.get("ve", 1.0))
    n_ports_eff = float(inputs.get("n_ports_eff", n_cyl/2.0))
    cr = float(inputs.get("cr", 10.5))

    v_port_ms = F.port_velocity_from_mach(mach, units="SI")
    disp_L = F.engine_displacement_L(bore_mm, stroke_mm, n_cyl)
    disp_cyl_L = F.cylinder_displacement_L(bore_mm, stroke_mm)

    rpm_peak = F.peak_rpm_from_csa_SI(Amean_mm2, mach, disp_L, ve, n_ports_eff)
    rpm_shift = F.shift_rpm(rpm_peak)
    mps = F.mean_piston_speed_m_min(stroke_mm, rpm_peak)

    kw_csa = F.kw_limit_from_csa_SI(Amean_mm2, mach, n_ports_eff)
    # Airflow limit: use engine_flow at peak RPM referenced to 28" (approx via GUI flow factor)
    q_m3min = F.engine_flow_m3min_at(rpm_peak, ve, disp_L)
    kw_flow = F.kw_limit_from_airflow_SI(q_m3min)

    best_torque = F.best_torque_Nm(min(kw_csa, kw_flow), rpm_peak, cr)

    # Per-unit metrics
    cid_in3 = F.cc_to_in3(disp_L * 1000.0)  # L → cc → in^3
    tpci = F.torque_per_cuin_Nm(cid_in3, best_torque)
    tpl = F.torque_per_liter_Nm(best_torque, disp_L)
    kw_pci = F.kw_per_cuin(min(kw_csa, kw_flow), cid_in3)
    kw_pl = F.kw_per_liter(min(kw_csa, kw_flow), disp_L)

    return {
        "mean_port_velocity_ms": v_port_ms,
        "mean_port_area_mm2": Amean_mm2,
        "engine_ld_L": disp_L,
        "cylinder_ld_L": disp_cyl_L,
        "peak_rpm": rpm_peak,
        "shift_rpm": rpm_shift,
        "mean_piston_speed_m_min": mps,
        "kw_limit_csa": kw_csa,
        "kw_limit_flow": kw_flow,
        "best_torque_Nm": best_torque,
        "torque_per_cuin_Nm": tpci,
        "torque_per_liter_Nm": tpl,
        "kw_per_cuin": kw_pci,
        "kw_per_liter": kw_pl,
    }


def compute_main_screen_US(inputs: Dict) -> Dict:
    """Compute US Main screen outputs from inputs by converting to SI, computing, then converting back."""
    mach = float(inputs["mach"])  # 0..1
    Amean_in2 = float(inputs["mean_port_area_in2"])  # in^2
    bore_in = float(inputs["bore_in"])  # in
    stroke_in = float(inputs["stroke_in"])  # in
    n_cyl = int(inputs["n_cyl"])  # count
    ve = float(inputs.get("ve", 1.0))
    n_ports_eff = float(inputs.get("n_ports_eff", n_cyl/2.0))
    cr = float(inputs.get("cr", 10.5))

    Amean_mm2 = F.in2_to_mm2(Amean_in2)
    bore_mm = F.in_to_mm(bore_in)
    stroke_mm = F.in_to_mm(stroke_in)

    si = compute_main_screen_SI({
        "mach": mach,
        "mean_port_area_mm2": Amean_mm2,
        "bore_mm": bore_mm,
        "stroke_mm": stroke_mm,
        "n_cyl": n_cyl,
        "ve": ve,
        "n_ports_eff": n_ports_eff,
        "cr": cr,
    })

    # Convert selected outputs to US where appropriate; keep others SI-equivalent
    cid_in3 = F.cc_to_in3(si["engine_ld_L"] * 1000.0)
    return {
        **si,
        "mean_port_velocity_fts": F.ms_to_fts(si["mean_port_velocity_ms"]),
        "engine_ld_in3": cid_in3,
        "cylinder_ld_in3": F.cc_to_in3(si["cylinder_ld_L"] * 1000.0),
    }


if __name__ == "__main__":
    # Backend self-check for series generation (no GUI). Uses fixtures or synthetic data.
    print("[analysis] self-check: generating series on sample data")
    try:
        from tests.fixtures_report import make_point_us, make_point_si  # type: ignore
    except Exception:
        # Local fallback if tests package not available
        def make_point_us(lift_in, q_cfm, a_mean_in2, d_valve_in):
            return {"lift_in": lift_in, "q_cfm": q_cfm, "a_mean_in2": a_mean_in2, "d_valve_in": d_valve_in}
        def make_point_si(lift_mm, q_m3min, a_mean_mm2, d_valve_mm):
            return {"lift_mm": lift_mm, "q_m3min": q_m3min, "a_mean_mm2": a_mean_mm2, "d_valve_mm": d_valve_mm}

    us = [
        make_point_us(0.050, 40.0, 1.80, 1.74),
        make_point_us(0.100, 80.0, 2.10, 1.74),
        make_point_us(0.200, 140.0, 2.40, 1.74),
    ]
    si = [
        make_point_si(F.in_to_mm(p["lift_in"]), F.cfm_to_m3min(p["q_cfm"]), F.in2_to_mm2(p["a_mean_in2"]), F.in_to_mm(p["d_valve_in"]))
        for p in us
    ]

    # Compute all series to ensure no exceptions and rough consistency
    _ = series_flow_vs_lift(us, "US"); _ = series_flow_vs_lift(si, "SI")
    _ = series_cfm28_vs_lift(us, "US"); _ = series_cfm28_vs_lift(si, "SI")
    _ = series_cfm_per_sq_in(us); _ = series_cfm_per_sq_mm(si)
    _ = series_port_velocity(us, "US"); _ = series_port_velocity(si, "SI")
    eff_us = [{**us[i], "a_eff_in2": us[i]["a_mean_in2"]*0.9} for i in range(len(us))]
    eff_si = [{**si[i], "a_eff_mm2": si[i]["a_mean_mm2"]*0.9} for i in range(len(si))]
    _ = series_effective_velocity(eff_us, "US"); _ = series_effective_velocity(eff_si, "SI")
    _ = series_port_energy_density(us, "US"); _ = series_port_energy_density(si, "SI")
    _ = series_port_energy(us, "US"); _ = series_port_energy(si, "SI")
    # For SAE CD, provide minimal a_ref and dp
    us_cd_pts = [{**us[i], "a_ref_m2": (F.in2_to_mm2(us[i]["a_mean_in2"]) * 1e-6), "dp_inH2O": 28.0} for i in range(len(us))]
    si_cd_pts = [{**si[i], "a_ref_mm2": si[i]["a_mean_mm2"], "dp_Pa": F.in_h2o_to_pa(28.0)} for i in range(len(si))]
    _ = series_sae_cd(us_cd_pts, "US"); _ = series_sae_cd(si_cd_pts, "SI")
    eff_us_cd = [{**eff_us[i], "a_eff_in2": eff_us[i]["a_eff_in2"], "dp_inH2O": 28.0} for i in range(len(eff_us))]
    eff_si_cd = [{**eff_si[i], "dp_inH2O": 28.0} for i in range(len(eff_si))]
    _ = series_effective_sae_cd(eff_us_cd, "US"); _ = series_effective_sae_cd(eff_si_cd, "SI")
    _ = series_ld_ratio(us, "US"); _ = series_ld_ratio(si, "SI")
    print("[analysis] self-check: OK")
