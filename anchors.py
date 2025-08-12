"""
Frozen anchor set for calibration constants with brief origin notes.

These values document the intended DV/IOP 1:1 behavior and the report
anchors used to tune them. Tests may assert no drift relative to these values.
Update this file deliberately when retuning, together with golden updates.
"""

ANCHORS: dict[str, float | int | str] = {
    # GUI air/units constants (fixed by DV GUI)
    "A0_FT_S": 1125.0,           # ft/s
    "A0_M_S": 343.2,             # m/s
    "RHO_SLUG_FT3": 0.0023769,   # slug/ft^3
    "G_FTPS2": 32.174,           # ft/s^2
    "RHO_KGM3_STD": 1.225,       # kg/m^3
    "G_M_S2": 9.80665,           # m/s^2

    # FLOW main/flow calibrations
    "K_CFM_TO_HP": 0.411,        # HP per CFM@28
    "K_CSA_HP": 1.0,             # HP per ft^3/min chain
    "K_PORT_DIST": 0.3086,       # effective distribution
    "K_EXINT_RATIO": 1.0143,     # small uplift on existing E/I
    "SHIFT_ALPHA": 0.07,         # shift = peak * (1+alpha)

    # SI kW calibration (FLOW main in SI)
    "K_CSA_kW": 6.534,
    "K_FLOW_kW": 21.42,

    # Compression-ratio correction
    "K_CR": 1.1207,
    "K_CR_REF": 10.5,
    "K_CR_SLOPE": 0.0,
}

# Origins (free-text for docs)
ORIGINS: dict[str, str] = {
    "K_PORT_DIST": "2.75 in², Mach≈0.5475, N=4 → ~7037 RPM (manual)",
    "K_EXINT_RATIO": "Header existing ratio uplift matching DV report (84.1/114.5)",
    "K_CFM_TO_HP": "HP ≈ 0.411 × CFM@28; tuned to DV screen examples",
    "K_CSA_kW": "Port area kW to match SI main page anchors",
}
