"""
Centralized calibration and GUI constants for DV IOP (FLOW) screen-match.

Values are sourced from anchors.ANCHORS to stabilize calibration. Update
anchors.py deliberately when retuning and adjust golden tests accordingly.
"""
from .anchors import ANCHORS

# --- GUI main screen: fixed speed of sound (Mach ↔ mean port velocity) ---
# Source: Vizard GUI main shows a0 = 1125 ft/s ≈ 343.2 m/s
A0_FT_S: float = float(ANCHORS["A0_FT_S"])  # [ft/s]
A0_M_S: float = float(ANCHORS["A0_M_S"])    # [m/s]

# --- Standard air density and gravity (for energy density, etc.) ---
# Source: Standard sea-level air and g for GUI reference calcs
RHO_SLUG_FT3: float = float(ANCHORS["RHO_SLUG_FT3"])  # [slug/ft^3]
G_FTPS2: float = float(ANCHORS["G_FTPS2"])            # [ft/s^2]
RHO_KGM3_STD: float = float(ANCHORS["RHO_KGM3_STD"])  # [kg/m^3]
G_M_S2: float = float(ANCHORS["G_M_S2"])              # [m/s^2]

# --- Screen-match calibration knobs (tuned to report and BMP anchors) ---
# These are intentionally mutable; use formulas.set_calibration to adjust from tests or tools.

# Airflow HP limit: HP = K_CFM_TO_HP * CFM@28
# Anchors: 708 HP @ 322 CFM; 740 HP @ 1720 CFM (DV reports)
K_CFM_TO_HP: float = float(ANCHORS["K_CFM_TO_HP"])  # [HP/CFM@28]

# Port Area HP limit uses ft^3/min chain:
# HP = K_CSA_HP * (A_mean[in^2] / 144) * (Mach * a0[ft/s]) * 60 * (n_ports_eff)
# Anchor: 685 HP @ 2.75 in², Mach≈0.5475, n_ports_eff=4
K_CSA_HP: float = float(ANCHORS["K_CSA_HP"])     # [HP/(ft^3/min)]

# Effective port distribution factor used only as a multiplier on n_ports_eff in RPM↔CSA.
# Anchor: 2.75 in^2 ↔ 7037 RPM (CID=427.7, VE=1.0, Mach≈0.5475, N=4) → K_PORT_DIST≈0.3085..0.3086
K_PORT_DIST: float = float(ANCHORS["K_PORT_DIST"])  # multiplier only (ports distribution)

# (reserved: compression-ratio correction placeholder removed; see SI block below)

# Existing EX/IN ratio GUI tweak: GUI reports slightly higher than raw ratio.
# Anchor-calibrated factor; capped at 1.0.
K_EXINT_RATIO: float = float(ANCHORS["K_EXINT_RATIO"])  # capped in use-site

# Mode for existing EX/IN ratio aggregation (header): "avg" or "total".
# Default to totals (matches report header semantics more often).
EXINT_RATIO_MODE: str = "total"

# --- SI main screen calibration ---
# Shift RPM = peak_rpm * (1 + SHIFT_ALPHA)
SHIFT_ALPHA: float = float(ANCHORS["SHIFT_ALPHA"])  # shift = peak * (1+alpha)

# kW limits: calibrated to match SI main screen anchors (Port Area ≈ 522 kW, Airflow ≈ 528 kW)
# Units: [kW per (m^3/min)]
K_CSA_kW: float = float(ANCHORS["K_CSA_kW"])
K_FLOW_kW: float = float(ANCHORS["K_FLOW_kW"])

# Compression ratio correction factor for "Best Torque" and related estimates.
# f_cr(cr) = K_CR * (1 + K_CR_SLOPE * (cr - K_CR_REF))
K_CR: float = float(ANCHORS["K_CR"])
K_CR_REF: float = float(ANCHORS["K_CR_REF"])
K_CR_SLOPE: float = float(ANCHORS["K_CR_SLOPE"])

# --- Exhaust pipe effect (Flow Test) ---
# When enabled, applies a multiplicative factor to exhaust-side corrected flow only.
EX_PIPE_ENABLED_DEFAULT: bool = False
K_EX_PIPE: float = 1.00  # typical 1.03..1.08 when enabled; 1.00 means no effect

# --- Optional dynamic air-state overrides (opt-in) ---
# When enabled, use ideal-gas a0(T) and rho(T,p) instead of GUI fixed constants for main-screen velocity.
AIR_STATE_USE_DYNAMIC: bool = False
AIR_T_C: float = 15.0
AIR_P_kPa: float = 101.325

# Required ratio strategy (placeholder for future piecewise/CR-Lmax models)
REQUIRED_RATIO_STRATEGY: str = "linear"

# --- Helper: allow tests/tools to override standard SI density (e.g., DV 70°F ~ 1.204 kg/m^3) ---
def set_standard_si_density(rho_kgm3: float) -> None:
	"""Override the standard SI air density used by GUI helpers. Safe for tests.
	Pass a positive value, e.g., 1.204 for ~70°F. This only affects helpers reading
	calibration at call time.
	"""
	global RHO_KGM3_STD
	if rho_kgm3 <= 0:
		raise ValueError("rho_kgm3 must be > 0")
	RHO_KGM3_STD = float(rho_kgm3)
