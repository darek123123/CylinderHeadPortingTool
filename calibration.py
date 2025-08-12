"""
Centralized calibration and GUI constants for DV IOP (FLOW) screen-match.

This module is the single source of truth for:
- GUI air/units constants used on screens (fixed a0 for Mach velocity, standard air density, gravity)
- Screen-match calibration scalars (HP limits, effective port distribution, ratio tweaks)

All values here are documented with their source/anchor from Vizard's GUI and reports.
"""

# --- GUI main screen: fixed speed of sound (Mach ↔ mean port velocity) ---
# Source: Vizard GUI main shows a0 = 1125 ft/s ≈ 343.2 m/s
A0_FT_S: float = 1125.0  # [ft/s] GUI fixed a0 for US
A0_M_S: float = 343.2    # [m/s]  GUI fixed a0 for SI

# --- Standard air density and gravity (for energy density, etc.) ---
# Source: Standard sea-level air and g for GUI reference calcs
RHO_SLUG_FT3: float = 0.0023769  # [slug/ft^3] ~ 1.225 kg/m^3
G_FTPS2: float = 32.174          # [ft/s^2]
RHO_KGM3_STD: float = 1.225      # [kg/m^3]
G_M_S2: float = 9.80665          # [m/s^2]

# --- Screen-match calibration knobs (tuned to report and BMP anchors) ---
# These are intentionally mutable; use formulas.set_calibration to adjust from tests or tools.

# Airflow HP limit: HP = K_CFM_TO_HP * CFM@28
# Anchors: 708 HP @ 322 CFM; 740 HP @ 1720 CFM (DV reports)
K_CFM_TO_HP: float = 0.411  # [HP/CFM@28] default; tests may override via set_calibration

# Port Area HP limit uses ft^3/min chain:
# HP = K_CSA_HP * (A_mean[in^2] / 144) * (Mach * a0[ft/s]) * 60 * (n_ports_eff)
# Anchor: 685 HP @ 2.75 in², Mach≈0.5475, n_ports_eff=4
K_CSA_HP: float = 1.0     # [HP/(ft^3/min)] default; tests may override

# Effective port distribution factor used only as a multiplier on n_ports_eff in RPM↔CSA.
# Anchor: 2.75 in^2 ↔ 7037 RPM (CID=427.7, VE=1.0, Mach≈0.5475, N=4) → K_PORT_DIST≈0.3085..0.3086
K_PORT_DIST: float = 0.3086

# (reserved: compression-ratio correction placeholder removed; see SI block below)

# Existing EX/IN ratio GUI tweak: GUI reports slightly higher than raw ratio.
# Anchor-calibrated factor; capped at 1.0.
K_EXINT_RATIO: float = 1.0143

# Mode for existing EX/IN ratio aggregation (header): "avg" or "total".
# Default to totals (matches report header semantics more often).
EXINT_RATIO_MODE: str = "total"

# --- SI main screen calibration ---
# Shift RPM = peak_rpm * (1 + SHIFT_ALPHA)
SHIFT_ALPHA: float = 0.07

# kW limits: calibrated to match SI main screen anchors (Port Area ≈ 522 kW, Airflow ≈ 528 kW)
# Units: [kW per (m^3/min)]
K_CSA_kW: float = 6.534
K_FLOW_kW: float = 21.42

# Compression ratio correction factor for "Best Torque" and related estimates.
# f_cr(cr) = K_CR * (1 + K_CR_SLOPE * (cr - K_CR_REF))
K_CR: float = 1.1207
K_CR_REF: float = 10.5
K_CR_SLOPE: float = 0.0

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
