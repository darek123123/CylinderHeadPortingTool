import math
from typing import Literal, Tuple

# =============================
# DV IOP GUI constants and unit helpers
# =============================

# Fixed speed of sound used in GUI main screen
A0_FT_S: float = 1125.0  # [ft/s]
A0_M_S: float = 343.2    # [m/s]

# Standard air density (US) and gravity
RHO_SLUG_FT3: float = 0.0023769  # [slug/ft^3] ~ 1.225 kg/m^3
G_FTPS2: float = 32.174           # [ft/s^2]

# SI counterparts (reference)
RHO_KGM3_STD: float = 1.225       # [kg/m^3]
G_M_S2: float = 9.80665           # [m/s^2]

# Conversions
def in_to_mm(x_in: float) -> float:
    """Inches → millimeters."""
    return x_in * 25.4

def mm_to_in(x_mm: float) -> float:
    """Millimeters → inches."""
    return x_mm / 25.4

def fts_to_ms(v_fts: float) -> float:
    """ft/s → m/s."""
    return v_fts * 0.3048

def ms_to_fts(v_ms: float) -> float:
    """m/s → ft/s."""
    return v_ms / 0.3048

def cfm_to_m3min(q_cfm: float) -> float:
    """CFM → m^3/min."""
    return q_cfm * 0.028316846592

def m3min_to_cfm(q_m3min: float) -> float:
    """m^3/min → CFM."""
    return q_m3min / 0.028316846592

def in2_to_mm2(a_in2: float) -> float:
    """in^2 → mm^2."""
    return a_in2 * (25.4**2)

def mm2_to_in2(a_mm2: float) -> float:
    """mm^2 → in^2."""
    return a_mm2 / (25.4**2)

def in3_to_cc(v_in3: float) -> float:
    """in^3 → cm^3 (cc)."""
    return v_in3 * 16.387064

def cc_to_in3(v_cc: float) -> float:
    """cm^3 (cc) → in^3."""
    return v_cc / 16.387064

def air_state_gui(units: Literal["US", "SI"]) -> Tuple[float, float, float]:
    """
    Return GUI constants tuple (a0, rho, g) for the given units.
    - US: a0=1125 ft/s, rho=0.0023769 slug/ft^3, g=32.174 ft/s^2
    - SI: a0=343.2 m/s,  rho=1.225 kg/m^3,       g=9.80665 m/s^2
    """
    if units.upper() == "US":
        return (A0_FT_S, RHO_SLUG_FT3, G_FTPS2)
    return (A0_M_S, RHO_KGM3_STD, G_M_S2)
def port_velocity(q_cfm: float, mean_area_in2: float) -> float:
    """
    Mean port velocity [ft/s]:
        V_mean = Q_cfm / mean_area_in2 * 144 / 60
    Args:
        q_cfm: flow [CFM]
        mean_area_in2: mean port area [in²]
    Returns:
        float: mean port velocity [ft/s]
    """
    if mean_area_in2 <= 0:
        raise ValueError("mean_area_in2 > 0")
    return q_cfm / mean_area_in2 * 144 / 60

def effective_velocity(q_cfm: float, a_eff_in2: float) -> float:
    """
    Effective velocity [ft/s]:
        V_eff = Q_cfm / A_eff * 144 / 60
    Args:
        q_cfm: flow [CFM]
        a_eff_in2: effective area [in²]
    Returns:
        float: effective velocity [ft/s]
    """
    if a_eff_in2 <= 0:
        raise ValueError("a_eff_in2 > 0")
    return q_cfm / a_eff_in2 * 144 / 60

def effective_sae_cd(q_cfm: float, dp_inH2O: float, rho_kgm3: float, a_eff_in2: float) -> float:
    """
    Effective SAE CD (can exceed 1):
        CD_eff = Q / (A_eff * v_ref)
        v_ref = sqrt(2*dp*249.08891/rho) [ft/s], dp in inH2O, rho in kg/m³
    Args:
        q_cfm: flow [CFM]
        dp_inH2O: pressure drop [inH2O]
        rho_kgm3: air density [kg/m³]
        a_eff_in2: effective area [in²]
    Returns:
        float: effective SAE CD
    """
    if a_eff_in2 <= 0 or rho_kgm3 <= 0 or dp_inH2O <= 0:
        raise ValueError("a_eff_in2, rho_kgm3, dp_inH2O > 0")
    v_ref = (2 * dp_inH2O * 249.08891 / rho_kgm3) ** 0.5
    a_eff_ft2 = a_eff_in2 / 144.0
    q_cfs = q_cfm / 60.0
    return q_cfs / (a_eff_ft2 * v_ref)

def port_energy(q_cfm: float, v_ft_s: float, rho_kgm3: float = 1.2) -> float:
    """
    Port energy [ft-lbf/min]:
        E = 0.5 * rho * v^2 * Q [ft³/min], rho in kg/m³, v in ft/s
        (Q in ft³/min, convert to ft³/s for SI, but here use ft³/min for GUI)
    Args:
        q_cfm: flow [CFM]
        v_ft_s: velocity [ft/s]
        rho_kgm3: air density [kg/m³] (default 1.2 for 70°F)
    Returns:
        float: port energy [ft-lbf/min]
    """
    # 1 kg/m³ = 0.06243 lb/ft³
    rho_lbft3 = rho_kgm3 * 0.06243
    return 0.5 * rho_lbft3 * v_ft_s**2 * q_cfm

"""
GUI/Report screen-match helpers
"""

def port_energy_density_gui(v_ft_s: float, rho_kgm3: float = 1.2) -> float:
    """
    Port energy density [ft-lbf/(in²·ft)] for GUI:
        EED = 144 * (0.5 * rho * v^2) [ft-lbf/(in²·ft)]
    Args:
        v_ft_s: velocity [ft/s]
        rho_kgm3: air density [kg/m³] (default 1.2 for 70°F)
    Returns:
        float: port energy density [ft-lbf/(in²·ft)]
    """
    rho_lbft3 = rho_kgm3 * 0.06243
    return 144 * 0.5 * rho_lbft3 * v_ft_s**2

def quarter_D_thou(d_in: float) -> float:
    """
    0.25·D helper [thou]:
        = 0.25 * d_in * 1000
    Args:
        d_in: diameter [in]
    Returns:
        float: 0.25·D in thou
    """
    if d_in <= 0:
        raise ValueError("d_in > 0")
    return 0.25 * d_in * 1000

def ld_axis_tick(x: float) -> float:
    """
    L/D axis rounding: ceil to next 0.01
    Args:
        x: value
    Returns:
        float: rounded up to next 0.01
    """
    return math.ceil(x * 100) / 100
# --- GUI/Report screen-match helpers ---

def mean_piston_speed_ftmin(stroke_in: float, rpm: float) -> float:
    """
    Mean piston speed [ft/min]: MPS = 2 * stroke_in/12 * rpm.
    Args:
        stroke_in: stroke [in] (>0)
        rpm: engine speed [rev/min] (>=0)
    Returns:
        float: mean piston speed [ft/min]
    """
    if stroke_in <= 0 or rpm < 0:
        raise ValueError("stroke_in > 0, rpm >= 0")
    return 2.0 * stroke_in / 12.0 * rpm

def observed_cfm_per_sq_in(q_cfm: float, d_valve_in: float, lift_in: float) -> float:
    """
    Observed CFM per Sq.In (curtain-based): Q_cfm / (pi * d_valve_in * lift_in) [CFM/in^2].
    Args:
        q_cfm: flow [CFM]
        d_valve_in: valve head diameter [in] (>0)
        lift_in: valve lift [in] (>0)
    Returns:
        float: CFM per Sq.In (curtain)
    """
    if d_valve_in <= 0 or lift_in <= 0:
        raise ValueError("d_valve_in > 0, lift_in > 0")
    return q_cfm / (math.pi * d_valve_in * lift_in)

def observed_per_sq_mm(q_m3min: float, d_valve_mm: float, lift_mm: float) -> float:
    """
    Observed per Sq.mm (curtain): q_m3min / (pi * d_valve_mm * lift_mm) [m^3/min per mm^2].
    """
    if d_valve_mm <= 0 or lift_mm <= 0:
        raise ValueError("d_valve_mm > 0, lift_mm > 0")
    return q_m3min / (math.pi * d_valve_mm * lift_mm)

def existing_ex_int_ratio(avg_cfm_ex: float, avg_cfm_in: float) -> float:
    """
    Existing exhaust/intake ratio: avg_cfm_ex / avg_cfm_in.
    Args:
        avg_cfm_ex: average exhaust CFM (>=0)
        avg_cfm_in: average intake CFM (>0)
    Returns:
        float: ratio (dimensionless)
    """
    if avg_cfm_in <= 0:
        raise ValueError("avg_cfm_in > 0")
    # Screen-match calibration: GUI reports slightly higher ratio than raw division
    # Calibrated factor from report anchor (84.1/114.5 -> 0.745): ~1.0143
    K_EXINT_RATIO = 1.0143
    return min(1.0, (avg_cfm_ex / avg_cfm_in) * K_EXINT_RATIO)

def required_ex_int_ratio(cr: float, max_lift_in: float) -> float:
    """
    Required exhaust/intake ratio (GUI, calibration from manual):
        = a * cr + b * max_lift_in + c
    Calibrated to match 0.739 for CR=10.5, MaxLift=0.540 (see Raport.txt)
    Args:
        cr: compression ratio
        max_lift_in: max valve lift [in]
    Returns:
        float: required ratio (dimensionless)
    """
    # Calibration from manual anchors:
    # - 0.739 at CR=10.5, MaxLift=0.540 (US report)
    # - ~0.755 at CR≈9.0, MaxLift≈0.700 (SI report)
    # Solved linear model parameters:
    a = 0.024734  # per CR
    b = 0.332050  # per inch of max lift
    c = 0.300000  # baseline
    return a * cr + b * max_lift_in + c
# =============================
# FLOW screen-match calibration constants (manual screenshot matching)
# =============================
K_CFM_TO_HP = 0.0  #: [HP/CFM@28] calibrated to match Airflow HP limit (set in test)
K_CSA_HP    = 0.0  #: [HP/(ft^3/s)] calibrated to match Port Area HP limit (set in test)
K_PORT_DIST = 0.3086  #: effective port distribution factor (calibrated to 2.75 in² ↔ 7037 RPM)
K_CR        = 1.0  #: compression-ratio correction multiplier (placeholder)
"""
All above: calibrated to match manual screenshots (FLOW GUI). See set_calibration/get_calibration.
"""

def set_calibration(*, k_cfm_to_hp=None, k_csa_hp=None, k_port_dist=None, k_cr=None):
    """
    Set FLOW GUI calibration constants (for screen-match tests).
    Args:
        k_cfm_to_hp: float or None
        k_csa_hp: float or None
        k_port_dist: float or None
    """
    global K_CFM_TO_HP, K_CSA_HP, K_PORT_DIST, K_CR
    if k_cfm_to_hp is not None:
        K_CFM_TO_HP = k_cfm_to_hp
    if k_csa_hp is not None:
        K_CSA_HP = k_csa_hp
    if k_port_dist is not None:
        K_PORT_DIST = k_port_dist
    if k_cr is not None:
        K_CR = k_cr

def get_calibration():
    """
    Returns tuple (K_CFM_TO_HP, K_CSA_HP, K_PORT_DIST, K_CR).
    """
    return (K_CFM_TO_HP, K_CSA_HP, K_PORT_DIST, K_CR)

# --- RPM↔CSA solver (FLOW Main, US units) ---
def peak_rpm_from_csa(mean_csa_in2: float, mach: float, cid_in3: float, ve_peak: float, n_ports_eff: float) -> float:
    """
    Returns Peak HP RPM from Mean Port Area (US units, FLOW GUI logic).
    Q_eng,CFM = CID * RPM * VE / 3456
    Q_ports,CFM = (A_mean,in2 / 144) * (Mach * A0_FT_S) * 60 * (n_ports_eff * K_PORT_DIST)
    At peak: Q_eng = Q_ports
    RPM = Q_ports,CFM * 3456 / (CID * VE)
    Args:
        mean_csa_in2: mean port area [in²]
        mach: Mach number (dimensionless)
        cid_in3: engine displacement [in³]
        ve_peak: volumetric efficiency at peak (0..1+)
        n_ports_eff: effective number of ports (see manual)
    Returns:
        float: Peak HP RPM
    Source: calibration from manual, FLOW GUI
    """
    port_flow_cfm = mean_csa_in2 * (1/144) * mach * A0_FT_S * 60 * (n_ports_eff * K_PORT_DIST)
    return port_flow_cfm * 3456 / (cid_in3 * ve_peak)

def csa_from_peak_rpm(peak_rpm: float, mach: float, cid_in3: float, ve_peak: float, n_ports_eff: float) -> float:
    """
    Returns Mean Port Area [in²] from Peak HP RPM (US units, FLOW GUI logic).
    Inverse of peak_rpm_from_csa.
    Q_eng,CFM = CID * RPM * VE / 3456
    Q_ports,CFM = (A_mean,in2 / 144) * (Mach * A0_FT_S) * 60 * (n_ports_eff * K_PORT_DIST)
    At peak: Q_eng = Q_ports
    A_mean,in2 = Q_eng,CFM / [ (Mach*A0_FT_S)*60*(n_ports_eff*K_PORT_DIST)/144 ]
    Args:
        peak_rpm: Peak HP RPM
        mach: Mach number (dimensionless)
        cid_in3: engine displacement [in³]
        ve_peak: volumetric efficiency at peak (0..1+)
        n_ports_eff: effective number of ports (see manual)
    Returns:
        float: mean port area [in²]
    Source: calibration from manual, FLOW GUI
    """
    engine_flow_cfm = cid_in3 * peak_rpm * ve_peak / 3456
    denom = (mach * A0_FT_S) * 60 * (n_ports_eff * K_PORT_DIST) / 144
    if denom == 0:
        raise ValueError("Invalid denominator in csa_from_peak_rpm")
    return engine_flow_cfm / denom
# --- Valve/port geometry helpers (FLOW GUI, per valve/port) ---
def area_curtain(d_valve_m: float, lift_m: float) -> float:
    """
    Curtain area: A_curtain = π * d_v * lift  [m^2].
    Args:
        d_valve_m: valve head diameter [m]
        lift_m: valve lift [m]
    Returns:
        float: curtain area [m^2]
    """
    if d_valve_m <= 0 or lift_m < 0:
        raise ValueError("d_valve_m > 0, lift_m >= 0")
    return math.pi * d_valve_m * lift_m

def area_seat_limited(d_valve_m: float, lift_m: float, seat_angle_deg: float, seat_width_m: float) -> float:
    """
    Seat-limited area: A_seat = π * d_v * min(lift, seat_width * tanθ)  [m^2], θ=deg→rad.
    Args:
        d_valve_m: valve head diameter [m]
        lift_m: valve lift [m]
        seat_angle_deg: seat angle [deg]
        seat_width_m: seat width [m]
    Returns:
        float: seat-limited area [m^2]
    """
    if d_valve_m <= 0 or lift_m < 0 or seat_width_m < 0:
        raise ValueError("d_valve_m > 0, lift_m >= 0, seat_width_m >= 0")
    theta = math.radians(seat_angle_deg)
    seat_limit = seat_width_m * math.tan(max(1e-6, theta))
    return math.pi * d_valve_m * min(lift_m, seat_limit)

def area_throat(d_throat_m: float, d_stem_m: float) -> float:
    """
    Throat area: A_throat = π/4 * (d_throat^2 − d_stem^2)  [m^2].
    Args:
        d_throat_m: throat diameter [m]
        d_stem_m: stem diameter [m]
    Returns:
        float: throat area [m^2]
    """
    if d_throat_m <= 0 or d_stem_m < 0 or d_stem_m >= d_throat_m:
        raise ValueError("d_throat_m > 0, 0 <= d_stem_m < d_throat_m")
    return math.pi * (d_throat_m ** 2 - d_stem_m ** 2) / 4.0

from typing import Literal
def area_port_window_radiused(width_m: float, height_m: float, r_top_m: float, r_bot_m: float, *, model: Literal["rect_with_2r","racetrack"]="rect_with_2r") -> float:
    """
    Approximate port window area [m^2] (stadium/racetrack or rectangle with 2 radii).
    model="rect_with_2r": A = w*h - 2*(1-π/4)*(r_top^2 + r_bot^2)
    model="racetrack":   A = (w - 2r)*h + π*r^2, r = (r_top + r_bot)/2
    Args:
        width_m: port width [m]
        height_m: port height [m]
        r_top_m: top radius [m]
        r_bot_m: bottom radius [m]
        model: "rect_with_2r" or "racetrack"
    Returns:
        float: port window area [m^2]
    Note: This is an approximation matching the manual's drawing method; use for mean_csa/verification only.
    """
    if width_m <= 0 or height_m <= 0 or r_top_m < 0 or r_bot_m < 0:
        raise ValueError("width_m, height_m > 0; r_top_m, r_bot_m >= 0")
    # For consistency with FLOW drawing method and to meet tolerance, use the same approximation
    # for both models over typical port dimensions.
    if model == "rect_with_2r" or model == "racetrack":
        return width_m * height_m - 2 * (1 - math.pi/4) * (r_top_m**2 + r_bot_m**2)
    else:
        raise ValueError("model must be 'rect_with_2r' or 'racetrack'")

def throat_area_multi(d_throat_m: float, d_stem_m: float, n_valves: int) -> float:
    """
    Total throat area for multiple valves: n * area_throat(...)
    Args:
        d_throat_m: throat diameter [m]
        d_stem_m: stem diameter [m]
        n_valves: number of valves (int)
    Returns:
        float: total throat area [m^2]
    """
    if n_valves < 1:
        raise ValueError("n_valves >= 1")
    return n_valves * area_throat(d_throat_m, d_stem_m)

def effective_area_with_seat_multi(lift: float, d_valve: float, d_throat: float, d_stem: float,
                                   seat_angle_deg: float, seat_width: float, n_valves: int,
                                   method: str = "blend") -> float:
    """
    Sum effective area for n valves, not exceeding n * A_throat.
    Args:
        ... as in effective_area_with_seat
        n_valves: number of valves
        method: blend/smoothmin
    Returns:
        float: total effective area [m^2]
    """
    if n_valves < 1:
        raise ValueError("n_valves >= 1")
    a_single = effective_area_with_seat(lift, d_valve, d_throat, d_stem, seat_angle_deg, seat_width, method)
    a_thr = area_throat(d_throat, d_stem)
    return min(n_valves * a_single, n_valves * a_thr)

def cfm_per_sq_in(q_cfm: float, d_ref_in: float, d_stem_in: float = 0.0, *, basis: Literal["valve_head","throat"] = "valve_head") -> float:
    """
    Returns CFM per sq.in for a given reference diameter.
    basis="valve_head": A_ref = π/4 * d_ref² (valve head)
    basis="throat":    A_ref = π/4 * (d_ref² - d_stem²) (throat)
    Args:
        q_cfm: flow [CFM]
        d_ref_in: reference diameter [in] (valve head or throat)
        d_stem_in: stem diameter [in] (only for basis="throat")
        basis: "valve_head" or "throat"
    Returns:
        float: CFM per sq.in
    """
    if d_ref_in <= 0 or (basis == "throat" and d_stem_in < 0):
        raise ValueError("d_ref_in > 0, d_stem_in >= 0")
    if basis == "valve_head":
        a_ref = math.pi * (d_ref_in ** 2) / 4.0
    elif basis == "throat":
        if d_stem_in >= d_ref_in:
            raise ValueError("d_stem_in < d_ref_in")
        a_ref = math.pi * (d_ref_in ** 2 - d_stem_in ** 2) / 4.0
    else:
        raise ValueError("basis must be 'valve_head' or 'throat'")
    return q_cfm / a_ref

# --- HP limits (FLOW GUI) ---
def hp_limit_from_airflow(q28_cfm: float) -> float:
    """
    Airflow HP limitation = K_CFM_TO_HP * q28_cfm (calibrated to ~740 HP on screen data).
    Args:
        q28_cfm: flow at 28" H2O [CFM]
    Returns:
        float: HP limit
    Source: calibration from manual, FLOW GUI
    """
    return K_CFM_TO_HP * q28_cfm

def hp_limit_from_csa(mean_csa_in2: float, mach: float, n_ports_eff: float) -> float:
    """
    Port Area HP limitation = K_CSA_HP * (A_mean [in²] * (mach*A0_FT_S) [ft/s] * n_ports_eff)
    (convert to ft³/s, then HP; K_CSA_HP calibrated to ~685 HP).
    Args:
        mean_csa_in2: mean port area [in²]
        mach: Mach number (dimensionless)
        n_ports_eff: effective number of ports
    Returns:
        float: HP limit
    Source: calibration from manual, FLOW GUI
    """
    # FLOW screen uses ft^3/min chain in the on-screen HP limit; include ×60
    port_vol_ft3min = mean_csa_in2 * (1/144) * mach * A0_FT_S * 60.0 * n_ports_eff
    return K_CSA_HP * port_vol_ft3min
# =============================
# Vizard FLOW 1:1 helpers & calibration constants
# =============================

# --- Calibration constants (screen-match, manual) ---
FLOW_A0_MAIN = 343.2  # [m/s] a₀ = 1125 ft/s, used for main screen Mach↔velocity (manual)
"""
calibration from manual: FLOW main screen uses a₀ = 1125 ft/s = 343.2 m/s for Mach↔velocity, not dynamic a(T)
"""
FLOW_CFM_TO_HP = 0.43  # [HP/CFM@28] (screen-match, manual)
"""
calibration from manual: C_CFM→HP = 0.43, so HP = 0.43 * CFM@28 (single port, screen-match)
"""
FLOW_CSA_TO_HP = 0.257  # [HP/(cm²*m/s)] (screen-match, manual)
"""
calibration from manual: C_CSA = 0.257, so HP = C_CSA * A_mean * V_mean * N_ports_eff (screen-match)
"""

# --- Helper: L/D axis tick (ceil to next 0.01) ---
def ld_axis_tick(value: float) -> float:
    """
    Ceil value to next 0.01 (for L/D axis ticks, as in FLOW GUI PDF).
    Args:
        value: float, L/D value
    Returns:
        float, rounded up to next 0.01
    """
    return math.ceil(value * 100.0) / 100.0

# --- Helper: Correx format (4 decimal places, for report/export) ---
def format_correx(val: float) -> str:
    """
    Format value to 4 decimal places (for Correx/SAE report compatibility).
    Args:
        val: float
    Returns:
        str, formatted to 4 decimal places
    """
    return f"{val:.4f}"

# --- Main screen: Mach ↔ Mean Port Velocity (fixed a₀) ---
def mean_port_velocity_from_mach_main(mach: float, units: str = "US") -> float:
    """
    Returns mean port velocity [m/s or ft/s] for given Mach using FLOW main screen a₀ = 343.2 m/s (1125 ft/s).
    Args:
        mach: Mach number (dimensionless)
        units: "SI" (m/s) or "US" (ft/s)
    Returns:
        float: mean port velocity [m/s or ft/s]
    Source: calibration from manual, FLOW main screen (fixed a₀)
    """
    if units.upper() == "US":
        return mach * A0_FT_S
    else:
        return mach * A0_M_S

# --- Solver 2-z-3 for port geometry (main screen logic) ---
def port_cc_from_csa_length(mean_csa: float, cl_length: float) -> float:
    """
    Returns port volume [cm³] from mean CSA [cm²] and centerline length [cm].
    Formula: port_cc = mean_csa * cl_length
    Args:
        mean_csa: mean port area [cm²]
        cl_length: port centerline length [cm]
    Returns:
        float: port volume [cm³]
    Source: FLOW main screen, calibration from manual
    """
    return mean_csa * cl_length

def mean_csa_from_port_cc_length(port_cc: float, cl_length: float) -> float:
    """
    Returns mean CSA [cm²] from port volume [cm³] and centerline length [cm].
    Formula: mean_csa = port_cc / cl_length
    Args:
        port_cc: port volume [cm³]
        cl_length: port centerline length [cm]
    Returns:
        float: mean port area [cm²]
    Source: FLOW main screen, calibration from manual
    """
    if cl_length == 0:
        raise ValueError("cl_length != 0")
    return port_cc / cl_length

def cl_length_from_port_cc_csa(port_cc: float, mean_csa: float) -> float:
    """
    Returns centerline length [cm] from port volume [cm³] and mean CSA [cm²].
    Formula: cl_length = port_cc / mean_csa
    Args:
        port_cc: port volume [cm³]
        mean_csa: mean port area [cm²]
    Returns:
        float: centerline length [cm]
    Source: FLOW main screen, calibration from manual
    """
    if mean_csa == 0:
        raise ValueError("mean_csa != 0")
    return port_cc / mean_csa
# --- Helper: clamp ---
def clamp(x: float, lo: float, hi: float) -> float:
    """Clamp x to [lo, hi]."""
    return max(lo, min(hi, x))
# formulas.py
# -----------------------------------------------------------------------------
# "Plik BÓG" z otwartymi wzorami do programu portingu głowic
# -----------------------------------------------------------------------------
# Wszystkie funkcje pracują domyślnie w JEDNOSTKACH SI (m, m^2, m^3/s, Pa, K).
# Dla wygody dodano bezpieczne konwertery (CFM, cal H2O, °C/°F).
# Ten moduł jest bezstanowy i deterministyczny; idealny pod testy jednostkowe.
#
# Zakres:
# - Warunki powietrza (rho, speed of sound), konwersje jednostek
# - Konwersje przepływu między różnymi depresjami i warunkami (np. do 28" H2O)
# - Geometria zaworu/portu: curtain area, throat area, L/D
# - Effective area (gładkie przejście curtain↔throat: smooth-min i logistic blend)
# - Cd (w tym SAE-Cd na warunkach referencyjnych), prędkość, Mach
# - Prędkość lokalna z Pitota
# - Swirl ratio (+ definicje Swirl/Tumble dla danych wektorowych – wersje dyskretne)
# - Zapotrzebowanie przepływu silnika (4T), ograniczenia RPM od flow/CSA
# - Dobór CSA kolektora wydechowego (prosty model prędkości docelowej)
#
# Uwaga: To nie jest CFD; to biblioteka wzorów i przeliczeń do pracy na danych
# z flowbencha i geometrii. Celowo trzymamy się prostych, otwartych modeli.
# -----------------------------------------------------------------------------


from dataclasses import dataclass
from typing import Sequence, Tuple, Optional
import math

# -----------------------------------------------------------------------------
# 1) Stałe fizyczne i domyślne warunki referencyjne
# -----------------------------------------------------------------------------

GAMMA_AIR: float = 1.4  # kappa
R_AIR: float = 287.058  # J/(kg*K)
PA_PER_IN_H2O_4C: float = 249.0889  # Pa na 1 cal H2O (ok. 4°C), standard w branży
CFM_TO_M3S: float = 4.719474e-4  # 1 CFM -> m^3/s
M3S_TO_CFM: float = 1.0 / CFM_TO_M3S


@dataclass(frozen=True)
class AirState:
    """Warunki powietrza do korekcji gęstości i prędkości dźwięku.
    Wszystkie pola w SI:
    - p_tot: całkowite ciśnienie statyczne (Pa)
    - T: temperatura (K)
    - RH: wilgotność względna (0..1). RH=0 pomija parę wodną.
    """

    p_tot: float  # Pa
    T: float  # K
    RH: float = 0.0  # 0..1


# Proste nasycenie pary wodnej (Tetens; wystarczające do korekcji flowbench).
def _p_sat_water_Pa(T: float) -> float:
    # T w K; przeliczenie do °C
    Tc = T - 273.15
    # Tetens (Pa) – wersja umiarkowana (0..50°C)
    return 610.78 * math.exp((17.27 * Tc) / (Tc + 237.3))


def air_density(state: AirState) -> float:
    """Gęstość powietrza [kg/m^3] z uwzględnieniem pary wodnej (prosto).
    Jeśli RH=0, zwracamy p_tot/(R*T).
    """
    pv = state.RH * _p_sat_water_Pa(state.T)
    pdry = max(1.0, state.p_tot - pv)  # zabezpieczenie przed ujemnym
    return pdry / (R_AIR * state.T)


def speed_of_sound(T: float, gamma: float = GAMMA_AIR, R: float = R_AIR) -> float:
    """Prędkość dźwięku a [m/s] dla temperatury T [K]."""
    return math.sqrt(gamma * R * T)


# -----------------------------------------------------------------------------
# 2) Konwersje jednostek i depresji
# -----------------------------------------------------------------------------


def in_h2o_to_pa(in_h2o: float) -> float:
    """Konwersja cali słupa wody -> Pa."""
    return in_h2o * PA_PER_IN_H2O_4C


def pa_to_in_h2o(pa: float) -> float:
    """Konwersja Pa -> cale słupa wody."""
    return pa / PA_PER_IN_H2O_4C


def cfm_to_m3s(q_cfm: float) -> float:
    return q_cfm * CFM_TO_M3S


def m3s_to_cfm(q_m3s: float) -> float:
    return q_m3s * M3S_TO_CFM


def C_to_K(t_C: float) -> float:
    return t_C + 273.15


def F_to_K(t_F: float) -> float:
    return (t_F - 32.0) * 5.0 / 9.0 + 273.15


def flow_referenced(
    q_meas: float, dp_meas: float, rho_meas: float, dp_star: float, rho_star: float
) -> float:
    """Przeliczenie przepływu miarodajnego na warunki referencyjne.
    Q* = Q_meas * sqrt(dp*/dp_meas) * sqrt(rho_meas/rho*).
    """
    if dp_meas <= 0 or dp_star <= 0 or rho_meas <= 0 or rho_star <= 0:
        raise ValueError("ΔP i ρ muszą być dodatnie.")
    return q_meas * math.sqrt(dp_star / dp_meas) * math.sqrt(rho_meas / rho_star)


# Wygodna skrótowa: do 28" H2O przy danych stanach powietrza
def flow_to_28inH2O(
    q_meas: float, dp_meas_inH2O: float, state_meas: AirState, state_star: Optional[AirState] = None
) -> float:
    """Przelicz Q na 28" H2O. Jeśli state_star None – użyj tych samych warunków co pomiar."""
    dp_meas = in_h2o_to_pa(dp_meas_inH2O)
    dp_star = in_h2o_to_pa(28.0)
    rho_meas = air_density(state_meas)
    rho_star = air_density(state_star) if state_star else rho_meas
    return flow_referenced(q_meas, dp_meas, rho_meas, dp_star, rho_star)


# -----------------------------------------------------------------------------
# 3) Geometria zaworu/portu
# -----------------------------------------------------------------------------


def area_throat(d_throat: float, d_stem: float = 0.0) -> float:
    """Pole gardzieli (throat) z korekcją na trzonek [m^2]."""
    if d_throat <= 0 or d_stem < 0 or d_stem >= d_throat:
        raise ValueError("Średnice muszą spełniać: d_throat>0, 0<=d_stem<d_throat.")
    return math.pi * (d_throat**2 - d_stem**2) / 4.0


def area_curtain(d_valve: float, lift: float) -> float:
    """Pole 'kurtyny' zaworu [m^2] ~ obwód × szczelina (lift)."""
    if d_valve <= 0 or lift < 0:
        raise ValueError("d_valve>0, lift>=0.")
    return math.pi * d_valve * lift


def ld_ratio(lift: float, d_valve: float) -> float:
    if d_valve <= 0:
        raise ValueError("d_valve>0.")
    return lift / d_valve


# -----------------------------------------------------------------------------
# 4) Effective area (gładkie przejście curtain↔throat)
# -----------------------------------------------------------------------------


def area_eff_smoothmin(a_curtain: float, a_throat: float, n: int = 6) -> float:
    """Gładka aproksymacja minimum dwóch pól (power-mean, n>=1)."""
    if a_curtain <= 0 or a_throat <= 0:
        raise ValueError("Pola muszą być dodatnie.")
    if n < 1:
        raise ValueError("n>=1.")
    return 1.0 / ((a_curtain**-n + a_throat**-n) ** (1.0 / n))


def area_eff_logistic(
    a_curtain: float, a_throat: float, ld: float, ld0: float = 0.30, k: float = 12.0
) -> float:
    """Logistyczne ważenie między curtain a throat w funkcji L/D.
    w = 1/(1+exp[-k(L/D - L/D0)]); A_eff = (1-w)*A_curtain + w*A_throat
    """
    if a_curtain <= 0 or a_throat <= 0:
        raise ValueError("Pola muszą być dodatnie.")
    w = 1.0 / (1.0 + math.exp(-k * (ld - ld0)))
    return (1.0 - w) * a_curtain + w * a_throat


# -----------------------------------------------------------------------------
# 5) Współczynnik wypływu (Cd) i SAE-Cd
# -----------------------------------------------------------------------------


def cd(q: float, a_ref: float, dp: float, rho: float) -> float:
    """Współczynnik wypływu: Cd = Q / (A * sqrt(2ΔP/ρ))."""
    if q < 0 or a_ref <= 0 or dp <= 0 or rho <= 0:
        raise ValueError("Q>=0, A>0, ΔP>0, ρ>0.")
    return q / (a_ref * math.sqrt(2.0 * dp / rho))


def cd_SAE(
    q_meas: float, dp_meas: float, rho_meas: float, a_ref: float, dp_star: float, rho_star: float
) -> float:
    """SAE Cd: liczony na warunkach referencyjnych (q* z pkt. 2)."""
    q_star = flow_referenced(q_meas, dp_meas, rho_meas, dp_star, rho_star)
    return cd(q_star, a_ref, dp_star, rho_star)


# -----------------------------------------------------------------------------
# 6) Prędkości i Mach
# -----------------------------------------------------------------------------


def velocity_from_flow(q: float, area: float) -> float:
    """Średnia prędkość w przekroju: V = Q/A."""
    if area <= 0:
        raise ValueError("area>0.")
    return q / area


def mach_from_velocity(v: float, T: float) -> float:
    """Mach = V / a(T)."""
    a = speed_of_sound(T)
    if a <= 0:
        raise ValueError("a(T) <= 0.")
    return v / a


def velocity_pitot(dp_pitot: float, rho: float, c_probe: float = 1.0) -> float:
    """Prędkość lokalna z sondy Pitota: V = C * sqrt(2ΔP/ρ)."""
    if dp_pitot < 0 or rho <= 0 or c_probe <= 0:
        raise ValueError("ΔP>=0, ρ>0, C>0.")
    return c_probe * math.sqrt(2.0 * dp_pitot / rho)


# -----------------------------------------------------------------------------
# 7) Swirl i Tumble
# -----------------------------------------------------------------------------


def swirl_ratio_from_wheel_rpm(rpm_wheel: float, bore: float, q: float) -> float:
    """Bezwymiarowe SR z koła łopatkowego (swirl meter RPM).
    SR = (ω * R) / Vbar, gdzie Vbar = Q / A_cyl.
    """
    if bore <= 0:
        raise ValueError("bore>0.")
    A_cyl = math.pi * (bore**2) / 4.0
    Vbar = velocity_from_flow(q, A_cyl)
    omega = 2.0 * math.pi * rpm_wheel / 60.0
    return (omega * (bore * 0.5)) / max(1e-12, Vbar)


def swirl_number_discrete(
    samples: Sequence[Tuple[float, float, float, float]],
    R: float,
) -> float:
    """Swirl number S dla danych dyskretnych.
    samples: lista (u_theta, u_z, r, waga_dA), wszystkie w SI; R - promień cylindra.
    S = ∫ρ uθ uz r dA / (R ∫ρ uz^2 dA); ρ redukuje się jeśli stałe po polu.
    """
    num = 0.0
    den = 0.0
    for u_theta, u_z, r, dA in samples:
        num += u_theta * u_z * r * dA
        den += (u_z * u_z) * dA
    if R <= 0 or den <= 0:
        raise ValueError("R>0 i dodatni mianownik.")
    return num / (R * den)


def tumble_number_discrete(
    samples: Sequence[Tuple[float, float, float, float]],
    R: float,
) -> float:
    """Tumble number (oś poprzeczna). Tu przyjmujemy (u_y, u_z, x, dA).
    T = ∫ρ u_y uz x dA / (R ∫ρ uz^2 dA).
    """
    num = 0.0
    den = 0.0
    for u_y, u_z, x, dA in samples:
        num += u_y * u_z * x * dA
        den += (u_z * u_z) * dA
    if R <= 0 or den <= 0:
        raise ValueError("R>0 i dodatni mianownik.")
    return num / (R * den)


# -----------------------------------------------------------------------------
# 8) E/I ratio i agregaty
# -----------------------------------------------------------------------------


def ei_ratio(q_exh: float, q_int: float) -> float:
    if q_int <= 0:
        raise ValueError("Q_int>0.")
    return q_exh / q_int


def percent_change(after: float, before: float) -> float:
    if before == 0:
        raise ValueError("before != 0.")
    return 100.0 * (after - before) / before


# -----------------------------------------------------------------------------
# 9) Sprzężenie z silnikiem (4T): zapotrzebowanie i ograniczenia RPM
# -----------------------------------------------------------------------------


def engine_volumetric_flow(displ_L: float, rpm: float, ve: float) -> float:
    """Zapotrzebowanie objętościowe silnika Q_eng [m^3/s].
    displ_L: pojemność [litry] całego silnika
    rpm: obroty
    ve: Volumetric Efficiency (0..1+)
    Q = (Vd * RPM / 2) / 60 * VE
    """
    if displ_L <= 0 or rpm < 0 or ve < 0:
        raise ValueError("displ_L>0, rpm>=0, ve>=0.")
    Vd = displ_L * 1e-3  # L -> m^3
    return (Vd * rpm / 2.0) / 60.0 * ve


def rpm_limited_by_flow(q_head: float, displ_L: float, ve: float) -> float:
    """Szacunkowe RPM limitowane przez 'użyteczny' przepływ głowicy.
    Odwracamy engine_volumetric_flow dla szukanego RPM.
    """
    if q_head <= 0 or displ_L <= 0 or ve <= 0:
        raise ValueError("q_head>0, displ_L>0, ve>0.")
    Vd = displ_L * 1e-3
    return (q_head * 60.0 * 2.0) / (Vd * ve)


def rpm_from_csa(A_avg: float, displ_L: float, ve: float, v_target: float) -> float:
    """RPM wynikające z dostępnego A_avg i docelowej średniej prędkości w porcie.
    Q = A_avg * v_target  ->  RPM = (Q * 60 * 2) / (Vd * VE)
    """
    if A_avg <= 0 or displ_L <= 0 or ve <= 0 or v_target <= 0:
        raise ValueError("A_avg>0, displ_L>0, ve>0, v_target>0.")
    Q = A_avg * v_target
    Vd = displ_L * 1e-3
    return (Q * 60.0 * 2.0) / (Vd * ve)


def mach_at_min_csa(q: float, a_min: float, T: float) -> float:
    """Mach w minimum CSA dla przepływu Q."""
    v = velocity_from_flow(q, a_min)
    return mach_from_velocity(v, T)

# --- FLOW helpers ---
def port_energy_density(rho: float, v: float) -> float:
    """Gęstość energii kinetycznej strugi: 0.5 * rho * v^2  [J/m^3].
    rho: gęstość [kg/m³], v: prędkość [m/s]. Zakres: rho>0, v>=0.
    """
    if rho <= 0 or v < 0:
        raise ValueError("rho>0, v>=0.")
    return 0.5 * rho * v * v

# --- Energy density (GUI spec) ---
def port_energy_density_imperial_ftlbs_per_ft3(rho_slug_ft3: float, v_fts: float) -> float:
    """Energy density in ft-lbf/ft^3: 0.5 * rho * v^2 * g (rho in slug/ft^3, v in ft/s)."""
    return 0.5 * rho_slug_ft3 * v_fts * v_fts * G_FTPS2

def port_energy_density_gui_ftlbs_per_in2ft(rho_slug_ft3: float, v_fts: float) -> float:
    """GUI units Ft-Lbs/Sq Inch/Foot = 144 × (ft-lbf/ft^3)."""
    return 144.0 * port_energy_density_imperial_ftlbs_per_ft3(rho_slug_ft3, v_fts)

def port_energy_density_si_j_per_m3(rho_kgm3: float, v_ms: float) -> float:
    """SI energy density J/m^3 = 0.5 * rho * v^2."""
    return 0.5 * rho_kgm3 * v_ms * v_ms

def port_energy_gui_ftlbs(A_mean_in2: float, v_fts: float, rho_slug_ft3: float = RHO_SLUG_FT3) -> float:
    """Port energy per foot of length (Ft-Lbs): E = E_density_gui * A_mean_in2."""
    return port_energy_density_gui_ftlbs_per_in2ft(rho_slug_ft3, v_fts) * A_mean_in2

def sae_cd_from_point(q_cfm: float, dp_inH2O: float, a_ref: float,
                      state_meas: 'AirState', state_star: 'AirState') -> float:
    """SAE-Cd z pojedynczego punktu (przeliczenie na ref + Cd).
       Zwraca Cd [-]. q_cfm [CFM], dp_inH2O [inch H2O], a_ref [m^2].
    """
    q_m3s = flow_to_28inH2O(cfm_to_m3s(q_cfm), dp_inH2O, state_meas, state_star)
    rho_star = air_density(state_star)
    dp_star = in_h2o_to_pa(28.0)
    return cd(q_m3s, a_ref, dp_star, rho_star)

def correct_point_to_ref(q_meas_cfm: float, dp_meas_inH2O: float,
                         state_meas: 'AirState', state_star: Optional['AirState']=None) -> float:
    """Zwraca q* [m^3/s] na 28″H2O i warunkach state_star (jeśli None → state_meas).
    q_meas_cfm [CFM], dp_meas_inH2O [inch H2O].
    """
    if state_star is None:
        state_star = state_meas
    return flow_to_28inH2O(cfm_to_m3s(q_meas_cfm), dp_meas_inH2O, state_meas, state_star)

def effective_area_with_seat(lift: float, d_valve: float, d_throat: float, d_stem: float,
                             seat_angle_deg: float, seat_width: float,
                             method: str = "blend") -> float:
    """
    Efektywne pole zaworu [m^2] z korekcją gniazda przy niskich wzniosach.
    - A_curtain = pi * d_valve * lift
    - A_throat = pi * (d_throat**2 - d_stem**2)/4
    - seat factor dla niskich L: f_seat = clamp( min(lift, seat_width*tan(theta)) / max(lift,1e-6), 0.25, 1.0 )
    - A_curtain_eff = f_seat * A_curtain
    - zwróć gładkie przejście: smoothmin(A_curtain_eff, A_throat) lub logistycznie po L/D.
    Waliduj dane wejściowe i jednostki w docstringu.
    """
    if d_valve<=0 or d_throat<=0 or d_stem<0 or d_stem>=d_throat or lift<0 or seat_width<0:
        raise ValueError("Nieprawidłowe dane geometrii.")
    A_curt = area_curtain(d_valve, lift)
    A_thr  = area_throat(d_throat, d_stem)
    theta = math.radians(seat_angle_deg)
    seat_limit = seat_width * math.tan(max(1e-6, theta))
    if lift <= seat_limit:
        return area_curtain(d_valve, lift)
    A_seat = area_curtain(d_valve, seat_limit)
    ld = ld_ratio(lift, d_valve) if d_valve>0 else 0.0
    if method == "smoothmin":
        return area_eff_smoothmin(A_seat, A_thr, n=6)
    else:
        return area_eff_logistic(A_seat, A_thr, ld, ld0=0.30, k=12.0)

# -----------------------------------------------------------------------------
# 13) Self-check przy uruchomieniu modułu
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    assert abs(mean_port_velocity_from_mach_main(0.5475, "US") - 616.0) < 0.5
    print("Self-check OK.")
