"""
Series generators for FLOW/IOP graphs (backend-only). Returns lists; no plotting.
"""
from typing import List, Dict, Literal
from . import formulas as F

# Minimal shape for a flow test point used by series generators
# Each point is a dict with keys at minimum: lift_in (or lift_mm), q_cfm (or q_m3min),
# a_mean_in2 (or a_mean_mm2), dp_inH2O (or dp_Pa), rho (kg/m^3), d_valve_in/mm, d_stem_in/mm, d_throat_in/mm


def series_flow_vs_lift(points: List[Dict], units: Literal["US", "SI"] = "US") -> List[float]:
    key_q = "q_cfm" if units == "US" else "q_m3min"
    return [p[key_q] for p in points]


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
    vals = []
    for a, b in zip(points_A, points_B):
        va = a[metric]
        vb = b[metric]
        vals.append(F.percent_change(va, vb))
    return vals
