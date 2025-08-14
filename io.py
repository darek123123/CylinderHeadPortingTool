"""
Lightweight parsers for DV IOP-style TXT reports (SI and US fixtures).

These parsers target the simplified, labeled format used in tests/fixtures.
They normalize decimal commas for SI and return dicts consumable by our APIs.
"""
from __future__ import annotations

from typing import Any, Dict, List
import math


def _norm_number(s: str) -> float:
    s_clean = s.strip().replace("\u00A0", "").replace(" ", "").replace(",", ".")
    try:
        return float(s_clean)
    except ValueError as e:
        raise ValueError(f"Invalid numeric value: '{s}'") from e


def _parse_kv(lines: List[str]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for ln in lines:
        if ":" not in ln:
            continue
        k, v = ln.split(":", 1)
        out[k.strip().lower()] = _norm_number(v)
    return out


def parse_iop_report_si(text: str) -> Dict[str, Any]:
    lines = [ln.strip() for ln in text.splitlines()]
    main_idx = lines.index("[MAIN]") if "[MAIN]" in lines else -1
    flow_idx = lines.index("[FLOWTEST]") if "[FLOWTEST]" in lines else -1
    rows_idx = lines.index("[ROWS]") if "[ROWS]" in lines else -1
    if main_idx == -1 or flow_idx == -1 or rows_idx == -1:
        missing = [name for name, idx in (('MAIN', main_idx), ('FLOWTEST', flow_idx), ('ROWS', rows_idx)) if idx == -1]
        raise ValueError(f"Invalid SI report fixture: missing sections {missing}")
    main_block = [ln for ln in lines[main_idx + 1 : flow_idx] if ln]
    flow_block = [ln for ln in lines[flow_idx + 1 : rows_idx] if ln]
    rows_block = [ln for ln in lines[rows_idx + 1 :] if ln]

    kv_main = _parse_kv(main_block)
    kv_flow = _parse_kv(flow_block)

    main = {
        "mach": kv_main["mach"],
        "mean_port_area_mm2": kv_main["meanportarea_mm2"],
        "bore_mm": kv_main["bore_mm"],
        "stroke_mm": kv_main["stroke_mm"],
        "n_cyl": int(kv_main["cylinders"]),
        "ve": kv_main.get("ve", 1.0),
        "n_ports_eff": kv_main.get("portseff", kv_main.get("n_ports_eff", 2.0)),
        "cr": kv_main.get("cr", 10.5),
    }

    flow_header: Dict[str, Any] = {
        "in_width_mm": kv_flow["inlet_width_mm"],
        "in_height_mm": kv_flow["inlet_height_mm"],
        "in_r_top_mm": kv_flow["inlet_rtop_mm"],
        "in_r_bot_mm": kv_flow["inlet_rbot_mm"],
        "ex_width_mm": kv_flow["exhaust_width_mm"],
        "ex_height_mm": kv_flow["exhaust_height_mm"],
        "ex_r_top_mm": kv_flow["exhaust_rtop_mm"],
        "ex_r_bot_mm": kv_flow["exhaust_rbot_mm"],
        "d_valve_in_mm": kv_flow["valve_in_mm"],
        "d_valve_ex_mm": kv_flow["valve_ex_mm"],
        "cr": kv_main.get("cr", 10.5),
        "max_lift_mm": kv_flow["maxlift_mm"],
        "rows_in": [],
        "rows_ex": [],
    }

    rows: List[Dict[str, Any]] = []
    # Rows format: lift;Qin;Qex;dp;[a_mean_mm2];[a_eff_mm2];[d_valve_mm]
    for ln in rows_block:
        if not ln or ln.startswith("#"):
            continue
        parts = [p.strip() for p in ln.split(";")]
        if len(parts) < 4:
            raise ValueError(f"Malformed SI row (need at least 4 columns): '{ln}'")
        lift_mm = _norm_number(parts[0])
        q_in_m3min = _norm_number(parts[1])
        q_ex_m3min = _norm_number(parts[2])
        dp_inH2O = _norm_number(parts[3])
        row: Dict[str, Any] = {
            "lift_mm": lift_mm,
            "q_in_m3min": q_in_m3min,
            "q_ex_m3min": q_ex_m3min,
            "dp_inH2O": dp_inH2O,
            "a_mean_mm2": kv_main.get("meanportarea_mm2", 0.0),
            "d_valve_mm": kv_flow.get("valve_in_mm", 0.0),
        }
        if len(parts) >= 5 and parts[4]:
            row["a_mean_mm2"] = _norm_number(parts[4])
        if len(parts) >= 6 and parts[5]:
            row["a_eff_mm2"] = _norm_number(parts[5])
        if len(parts) >= 7 and parts[6]:
            row["d_valve_mm"] = _norm_number(parts[6])
        # Helpers for SAE-CD in SI
        try:
            d_m = row["d_valve_mm"] / 1000.0
            a_curt_m2 = math.pi * d_m * (row["lift_mm"] / 1000.0)
            row["a_ref_mm2"] = a_curt_m2 * 1e6
            row["dp_Pa"] = 249.0889 * row["dp_inH2O"]
        except Exception:
            pass
        rows.append(row)
        # Accumulate per-row header flows for totals/averages (correctable to 28")
        flow_header["rows_in"].append({"m3min_corr": q_in_m3min, "dp_inH2O": dp_inH2O})
        flow_header["rows_ex"].append({"m3min_corr": q_ex_m3min, "dp_inH2O": dp_inH2O})

    # Hints for header ratio computation (to align with specific report anchor semantics)
    if len(flow_header["rows_in"]) >= 2 and len(flow_header["rows_ex"]) >= 2:
        flow_header["rows_for_ratio_in"] = flow_header["rows_in"][:2]
        flow_header["rows_for_ratio_ex"] = flow_header["rows_ex"][:2]
        flow_header["exint_apply_calibration"] = False
    return {"main": main, "flow_header": flow_header, "flow_rows": rows}


def parse_iop_report_us(text: str) -> Dict[str, Any]:
    lines = [ln.strip() for ln in text.splitlines()]
    main_idx = lines.index("[MAIN]") if "[MAIN]" in lines else -1
    flow_idx = lines.index("[FLOWTEST]") if "[FLOWTEST]" in lines else -1
    rows_idx = lines.index("[ROWS]") if "[ROWS]" in lines else -1
    if main_idx == -1 or flow_idx == -1 or rows_idx == -1:
        missing = [name for name, idx in (('MAIN', main_idx), ('FLOWTEST', flow_idx), ('ROWS', rows_idx)) if idx == -1]
        raise ValueError(f"Invalid US report fixture: missing sections {missing}")
    main_block = [ln for ln in lines[main_idx + 1 : flow_idx] if ln]
    flow_block = [ln for ln in lines[flow_idx + 1 : rows_idx] if ln]
    rows_block = [ln for ln in lines[rows_idx + 1 :] if ln]
    kv_main = _parse_kv(main_block)
    kv_flow = _parse_kv(flow_block)
    main = {
        "mach": kv_main["mach"],
        "mean_port_area_in2": kv_main.get("meanportarea_in2", 0.0),
        "bore_in": kv_main.get("bore_in", 0.0),
        "stroke_in": kv_main.get("stroke_in", 0.0),
        "n_cyl": int(kv_main.get("cylinders", 1)),
        "ve": kv_main.get("ve", 1.0),
        "n_ports_eff": kv_main.get("portseff", kv_main.get("n_ports_eff", 2.0)),
        "cr": kv_main.get("cr", 10.5),
    }
    flow_header: Dict[str, Any] = {
        "in_width_mm": kv_flow.get("inlet_width_mm", 0.0),
        "in_height_mm": kv_flow.get("inlet_height_mm", 0.0),
        "in_r_top_mm": kv_flow.get("inlet_rtop_mm", 0.0),
        "in_r_bot_mm": kv_flow.get("inlet_rbot_mm", 0.0),
        "ex_width_mm": kv_flow.get("exhaust_width_mm", 0.0),
        "ex_height_mm": kv_flow.get("exhaust_height_mm", 0.0),
        "ex_r_top_mm": kv_flow.get("exhaust_rtop_mm", 0.0),
        "ex_r_bot_mm": kv_flow.get("exhaust_rbot_mm", 0.0),
        "d_valve_in_mm": kv_flow.get("valve_in_mm", 0.0),
        "d_valve_ex_mm": kv_flow.get("valve_ex_mm", 0.0),
        "cr": kv_main.get("cr", 10.5),
        "max_lift_mm": kv_flow.get("maxlift_mm", 0.0),
        "rows_in": [],
        "rows_ex": [],
    }
    rows: List[Dict[str, Any]] = []
    for ln in rows_block:
        if not ln or ln.startswith("#"):
            continue
        parts = [p.strip() for p in ln.split(";")]
        if len(parts) < 4:
            raise ValueError(f"Malformed US row (need at least 4 columns): '{ln}'")
        lift_in = _norm_number(parts[0])
        q_in_cfm = _norm_number(parts[1])
        q_ex_cfm = _norm_number(parts[2])
        dp_inH2O = _norm_number(parts[3])
        row = {
            "lift_in": lift_in,
            "q_cfm": q_in_cfm,
            "dp_inH2O": dp_inH2O,
        }
        if len(parts) >= 5 and parts[4]:
            row["a_mean_in2"] = _norm_number(parts[4])
        if len(parts) >= 6 and parts[5]:
            row["a_eff_in2"] = _norm_number(parts[5])
        rows.append(row)
    flow_header["rows_in"].append({"m3min_corr": q_in_cfm * 0.028316846592, "dp_inH2O": dp_inH2O})
    flow_header["rows_ex"].append({"m3min_corr": q_ex_cfm * 0.028316846592, "dp_inH2O": dp_inH2O})
    return {"main": main, "flow_header": flow_header, "flow_rows": rows}
