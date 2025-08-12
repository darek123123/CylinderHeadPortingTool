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
# Anchor example: 740 HP @ 1720 CFM → K_CFM_TO_HP set via set_calibration in tests.
K_CFM_TO_HP: float = 0.0  # [HP/CFM@28]; set in tests to match specific screens

# Port Area HP limit uses ft^3/min chain:
# HP = K_CSA_HP * (A_mean[in^2] / 144) * (Mach * a0[ft/s]) * 60 * (n_ports_eff)
# Anchor example: 685 HP @ A=2.75 in^2, Mach=0.5475, N=4 → K_CSA_HP set via tests.
K_CSA_HP: float = 0.0     # [HP/(ft^3/min)]

# Effective port distribution factor used only as a multiplier on n_ports_eff in RPM↔CSA.
# Anchor: 2.75 in^2 ↔ 7037 RPM (CID=427.7, VE=1.0, Mach≈0.5475, N=4) → K_PORT_DIST≈0.3085..0.3086
K_PORT_DIST: float = 0.3086

# Compression-ratio correction placeholder (exposed for future use)
K_CR: float = 1.0

# Existing EX/IN ratio GUI tweak: GUI reports slightly higher than raw ratio.
# Anchor: 84.1/114.5 → 0.745 → factor ≈ 1.0143, capped at 1.0.
K_EXINT_RATIO: float = 1.0143

# Mode for existing EX/IN ratio aggregation (header): "avg" or "total".
EXINT_RATIO_MODE: str = "avg"

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
