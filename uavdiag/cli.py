from __future__ import annotations

import argparse
from pathlib import Path

from .pipeline import analyze_scenario, run_benchmark
from .simulate import generate_scenario


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="uavdiag",
        description="Reproducible timing, synchronization and trajectory diagnostics for UAV experiments.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    benchmark = subparsers.add_parser("benchmark", help="regenerate and analyze baseline/degraded scenarios")
    benchmark.add_argument("--project-root", type=Path, default=PROJECT_ROOT)

    generate = subparsers.add_parser("generate", help="generate one deterministic scenario")
    generate.add_argument("scenario", choices=("baseline", "degraded"))
    generate.add_argument("output_dir", type=Path)

    analyze = subparsers.add_parser("analyze", help="analyze trajectory and timing CSV files")
    analyze.add_argument("scenario_dir", type=Path)
    analyze.add_argument("output_dir", type=Path)
    analyze.add_argument("--label", default="experiment")
    analyze.add_argument("--config", type=Path, default=PROJECT_ROOT / "config" / "quality_gates.json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "generate":
        generate_scenario(args.scenario, args.output_dir)
        print(f"Generated {args.scenario} scenario in {args.output_dir}")
        return 0
    if args.command == "analyze":
        result = analyze_scenario(args.scenario_dir, args.config, args.output_dir, args.label)
        print(f"{args.label}: {'PASS' if result.passed else 'FAIL'}")
        return 0 if result.passed else 2

    results = run_benchmark(args.project_root)
    for name, result in results.items():
        failed = sum(not check.passed for check in result.checks)
        print(f"{name}: {'PASS' if result.passed else 'FAIL'} ({failed} failed gates)")
    expected = results["baseline"].passed and not results["degraded"].passed
    return 0 if expected else 1
