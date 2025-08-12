"""
Minimal CLI for backend smoke-tests (no GUI).

Usage examples:
  python -m CylinderHeadPortingTool.cli main-si --input inputs.json
  python -m CylinderHeadPortingTool.cli flowtest-si --input flowtest.json

Commands:
  - main-si: computes SI main screen outputs from JSON inputs
  - flowtest-si: computes SI Flow Test header metrics and sample table rows
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List
import csv
import os

from . import analysis as A
from . import calibration as CAL
from .anchors import ANCHORS
from . import schemas as S


def _read_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _fail_on_drift() -> None:
    guarded = [
        "K_PORT_DIST","K_EXINT_RATIO","K_CFM_TO_HP","K_CSA_HP","K_CSA_kW","K_FLOW_kW","SHIFT_ALPHA",
    ]
    mismatches: List[str] = []
    for k in guarded:
        if float(ANCHORS[k]) != float(getattr(CAL, k)):
            mismatches.append(f"{k}: anchors={ANCHORS[k]!r} vs calibration={getattr(CAL,k)!r}")
    if mismatches:
        raise SystemExit("Calibration drift detected (anchors vs runtime):\n" + "\n".join(" - "+m for m in mismatches))


def _write_output(obj: Any, path: str | None) -> None:
    if not path:
        json.dump(obj, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        return
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False)
    elif ext == ".csv":
        # Flatten dict-of-scalars or dict-of-lists
        if isinstance(obj, dict) and all(not isinstance(v, list) for v in obj.values()):
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(list(obj.keys()))
                w.writerow([obj[k] for k in obj.keys()])
        elif isinstance(obj, dict) and any(isinstance(v, list) for v in obj.values()):
            keys = list(obj.keys())
            n = max(len(v) if isinstance(v, list) else 1 for v in obj.values())
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(keys)
                for i in range(n):
                    row = []
                    for k in keys:
                        v = obj[k]
                        if isinstance(v, list):
                            row.append(v[i] if i < len(v) else "")
                        else:
                            row.append(v if i == 0 else "")
                    w.writerow(row)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(str(obj))
    else:
        raise SystemExit(f"Unsupported output extension: {ext} (use .json or .csv)")


def cmd_main_si(args: argparse.Namespace) -> int:
    if args.fail_on_drift:
        _fail_on_drift()
    data = _read_json(args.input)
    # Validate
    _ = S.MainInputsSI.model_validate(data)
    out = A.compute_main_screen_SI(data)
    _write_output(out, args.output)
    return 0


def cmd_flowtest_si(args: argparse.Namespace) -> int:
    if args.fail_on_drift:
        _fail_on_drift()
    data = _read_json(args.input)
    # Validate header shape
    _ = S.FlowHeaderInputsSI.model_validate(data)
    header = A.flowtest_header_metrics_SI(data)
    rows_in = data.get("rows_in_full") or data.get("rows_in") or []
    # Produce a small preview table if detailed rows provided
    table = A.flowtest_tables_SI(rows_in) if rows_in else []
    out = {"header": header, "table_preview": table[:5]}
    _write_output(out, args.output)
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    if args.fail_on_drift:
        _fail_on_drift()
    dataA = _read_json(args.a)
    dataB = _read_json(args.b)
    out = A.compare_two_tests(dataA, dataB, mode=args.mode, units=args.units)
    if not args.percent:
        # Remove percent series for cleaner output when not requested
        for k in list(out.keys()):
            if k.endswith("Pct"):
                out.pop(k, None)
    _write_output(out, args.output)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="CylinderHeadPortingTool.cli", description="DV/IOP backend CLI (no GUI)")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_main_si = sub.add_parser("main-si", help="Compute SI Main screen outputs from JSON input")
    p_main_si.add_argument("--input", required=True, help="Path to JSON input file")
    p_main_si.add_argument("--output", required=False, help="Output file (.json or .csv)")
    p_main_si.add_argument("--fail-on-drift", action="store_true", help="Fail if calibration differs from anchors")
    p_main_si.set_defaults(func=cmd_main_si)

    p_ft_si = sub.add_parser("flowtest-si", help="Compute SI Flow Test header metrics and table preview from JSON input")
    p_ft_si.add_argument("--input", required=True, help="Path to JSON input file")
    p_ft_si.add_argument("--output", required=False, help="Output file (.json or .csv)")
    p_ft_si.add_argument("--fail-on-drift", action="store_true", help="Fail if calibration differs from anchors")
    p_ft_si.set_defaults(func=cmd_flowtest_si)

    p_cmp = sub.add_parser("compare", help="Compare two flow tests and return series and percent deltas")
    p_cmp.add_argument("--a", required=True, help="Path to JSON input file for Test A")
    p_cmp.add_argument("--b", required=True, help="Path to JSON input file for Test B")
    p_cmp.add_argument("--units", choices=["US","SI"], default="SI")
    p_cmp.add_argument("--mode", choices=["lift","ld"], default="lift")
    p_cmp.add_argument("--percent", action="store_true", help="Include percent delta series in output")
    p_cmp.add_argument("--output", required=False, help="Output file (.json or .csv)")
    p_cmp.add_argument("--fail-on-drift", action="store_true", help="Fail if calibration differs from anchors")
    p_cmp.set_defaults(func=cmd_compare)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
