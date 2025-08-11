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
def mean_port_velocity_from_mach_main(mach: float, units: str = "SI") -> float:
    """
    Returns mean port velocity [m/s or ft/s] for given Mach using FLOW main screen a₀ = 343.2 m/s (1125 ft/s).
    Args:
        mach: Mach number (dimensionless)
        units: "SI" (m/s) or "US" (ft/s)
    Returns:
        float: mean port velocity [m/s or ft/s]
    Source: calibration from manual, FLOW main screen (fixed a₀)
    """
    v = mach * FLOW_A0_MAIN
    if units.upper() == "US":
        return v * 3.28084  # m/s to ft/s
    return v

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

# --- FLOW helpers ---
def port_energy_density(rho: float, v: float) -> float:
    """Gęstość energii kinetycznej strugi: 0.5 * rho * v^2  [J/m^3].
    rho: gęstość [kg/m³], v: prędkość [m/s]. Zakres: rho>0, v>=0.
    """
    if rho <= 0 or v < 0:
        raise ValueError("rho>0, v>=0.")
    return 0.5 * rho * v * v

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
    # Szybki sanity-test dla effective_area_with_seat
    try:
        A = effective_area_with_seat(
            lift=0.0005, d_valve=0.046, d_throat=0.034, d_stem=0.007,
            seat_angle_deg=45.0, seat_width=0.0015
        )
        print("Self-check OK.")
    except Exception as e:
        print(f"Self-check FAIL: {e}")
