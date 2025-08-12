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
from typing import Any, Dict

from . import analysis as A


def _read_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def cmd_main_si(args: argparse.Namespace) -> int:
    data = _read_json(args.input)
    out = A.compute_main_screen_SI(data)
    json.dump(out, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


def cmd_flowtest_si(args: argparse.Namespace) -> int:
    data = _read_json(args.input)
    header = A.flowtest_header_metrics_SI(data)
    rows_in = data.get("rows_in_full") or data.get("rows_in") or []
    # Produce a small preview table if detailed rows provided
    table = A.flowtest_tables_SI(rows_in) if rows_in else []
    out = {"header": header, "table_preview": table[:5]}
    json.dump(out, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    dataA = _read_json(args.a)
    dataB = _read_json(args.b)
    out = A.compare_two_tests(dataA, dataB, mode=args.mode, units=args.units)
    if not args.percent:
        # Remove percent series for cleaner output when not requested
        for k in list(out.keys()):
            if k.endswith("Pct"):
                out.pop(k, None)
    json.dump(out, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="CylinderHeadPortingTool.cli", description="DV/IOP backend CLI (no GUI)")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_main_si = sub.add_parser("main-si", help="Compute SI Main screen outputs from JSON input")
    p_main_si.add_argument("--input", required=True, help="Path to JSON input file")
    p_main_si.set_defaults(func=cmd_main_si)

    p_ft_si = sub.add_parser("flowtest-si", help="Compute SI Flow Test header metrics and table preview from JSON input")
    p_ft_si.add_argument("--input", required=True, help="Path to JSON input file")
    p_ft_si.set_defaults(func=cmd_flowtest_si)

    p_cmp = sub.add_parser("compare", help="Compare two flow tests and return series and percent deltas")
    p_cmp.add_argument("--a", required=True, help="Path to JSON input file for Test A")
    p_cmp.add_argument("--b", required=True, help="Path to JSON input file for Test B")
    p_cmp.add_argument("--units", choices=["US","SI"], default="SI")
    p_cmp.add_argument("--mode", choices=["lift","ld"], default="lift")
    p_cmp.add_argument("--percent", action="store_true", help="Include percent delta series in output")
    p_cmp.set_defaults(func=cmd_compare)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
