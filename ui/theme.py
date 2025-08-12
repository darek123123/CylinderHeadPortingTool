from __future__ import annotations

COLORS = {
  "intake": "#00C853",
  "exhaust": "#FF6D00",
  "percent_pos": "#00B0FF",
  "percent_neg": "#E91E63",
  "ok": "#00C853",
  "warn": "#FFC400",
  "crit": "#FF1744",
  "neutral": "#90A4AE",
  "bg": "#121212",
  "panel": "#1E1E1E",
  "grid": "#263238",
}

THRESHOLDS = {
  "mach_intake_warn": 0.60, "mach_intake_crit": 0.70,
  "vel_mean_warn_ms": 90.0, "vel_mean_crit_ms": 110.0,
  "vel_eff_warn_ms": 120.0, "vel_eff_crit_ms": 140.0,
  "percent_warn": 5.0,      "percent_crit": 10.0,
}
