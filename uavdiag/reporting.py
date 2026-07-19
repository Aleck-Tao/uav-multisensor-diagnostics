from __future__ import annotations

import json
from pathlib import Path
from xml.sax.saxutils import escape

from .models import AnalysisResult, GateCheck


def _normalize_floats(value: object, decimal_places: int = 12) -> object:
    """Remove platform-level floating-point noise from committed JSON output."""
    if isinstance(value, float):
        return round(value, decimal_places)
    if isinstance(value, dict):
        return {key: _normalize_floats(item, decimal_places) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_floats(item, decimal_places) for item in value]
    return value


def _format_value(check: GateCheck) -> str:
    if check.unit == "ratio":
        return f"{check.value * 100:.2f}%"
    if check.unit == "count":
        return f"{check.value:.0f}"
    if check.unit == "%":
        return f"{check.value:.2f}%"
    return f"{check.value:.3f} {check.unit}"


def write_markdown_report(result: AnalysisResult, path: Path) -> None:
    verdict = "PASS" if result.passed else "FAIL"
    lines = [
        f"# {result.scenario.title()} Scenario Diagnostic Report",
        "",
        f"**Quality-gate verdict: {verdict}**",
        "",
        "> This is a deterministic fault-injection benchmark. It validates the analysis pipeline; it is not presented as a real-flight accuracy result.",
        "",
        "## Trajectory metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Samples | {result.trajectory.sample_count} |",
        f"| ATE RMSE | {result.trajectory.ate_rmse_m:.4f} m |",
        f"| ATE 95th percentile | {result.trajectory.ate_p95_m:.4f} m |",
        f"| RPE RMSE (1 s) | {result.trajectory.rpe_rmse_m:.4f} m |",
        f"| Final drift | {result.trajectory.final_drift_m:.4f} m |",
        f"| Heading RMSE | {result.trajectory.heading_rmse_deg:.3f} deg |",
        f"| Path-length error | {result.trajectory.path_length_error_pct:.2f}% |",
        "",
        "## Sensor timing",
        "",
        "| Sensor | Samples | Observed rate | Jitter RMS | Max gap | Dropouts | Dropout rate | Out-of-order |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in result.timing:
        lines.append(
            f"| {item.sensor} | {item.sample_count} | {item.observed_hz:.2f} Hz | "
            f"{item.jitter_rms_ms:.3f} ms | {item.max_gap_ms:.2f} ms | {item.estimated_dropouts} | "
            f"{item.dropout_rate * 100:.2f}% | {item.out_of_order_count} |"
        )
    lines.extend(
        [
            "",
            f"Camera–LiDAR nearest-frame synchronization error (95th percentile): **{result.camera_lidar_sync_p95_ms:.3f} ms**.",
            "",
            "## Quality gates",
            "",
            "| Check | Value | Limit | Result |",
            "|---|---:|---:|:---:|",
        ]
    )
    for check in result.checks:
        limit = f"{check.threshold * 100:.2f}%" if check.unit == "ratio" else f"{check.threshold:g} {check.unit}".strip()
        lines.append(f"| `{check.name}` | {_format_value(check)} | {limit} | {'PASS' if check.passed else 'FAIL'} |")
    lines.extend(
        [
            "",
            "## Reproducibility",
            "",
            "Input file SHA-256 hashes are stored in `metrics.json`. Re-run `python -m uavdiag benchmark` from the project directory to regenerate both scenarios and reports.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_svg_dashboard(result: AnalysisResult, path: Path) -> None:
    selected_names = {
        "trajectory.ate_rmse",
        "trajectory.rpe_rmse",
        "trajectory.final_drift",
        "trajectory.heading_rmse",
        "sync.camera_lidar_p95",
    }
    selected = [check for check in result.checks if check.name in selected_names]
    width, row_height = 900, 62
    height = 110 + row_height * len(selected)
    verdict_color = "#15803d" if result.passed else "#b91c1c"
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#0f172a"/>',
        '<style>text{font-family:Segoe UI,Arial,sans-serif;fill:#e2e8f0}.label{font-size:15px}.small{font-size:12px;fill:#94a3b8}</style>',
        f'<text x="35" y="38" font-size="23" font-weight="700">{escape(result.scenario.title())} diagnostic benchmark</text>',
        f'<text x="790" y="38" text-anchor="end" font-size="19" font-weight="700" fill="{verdict_color}">{"PASS" if result.passed else "FAIL"}</text>',
        '<text x="35" y="66" class="small">Bar length is normalized to the configured acceptance limit; the marker denotes the limit.</text>',
    ]
    for index, check in enumerate(selected):
        y = 94 + index * row_height
        ratio = min(check.value / check.threshold if check.threshold else 0.0, 1.35)
        bar_width = 500 * ratio
        color = "#22c55e" if check.passed else "#ef4444"
        svg.extend(
            [
                f'<text x="35" y="{y}" class="label">{escape(check.name)}</text>',
                f'<rect x="285" y="{y - 16}" width="500" height="18" rx="4" fill="#1e293b"/>',
                f'<rect x="285" y="{y - 16}" width="{bar_width:.1f}" height="18" rx="4" fill="{color}"/>',
                f'<line x1="785" y1="{y - 21}" x2="785" y2="{y + 7}" stroke="#f8fafc" stroke-width="2"/>',
                f'<text x="795" y="{y}" class="small">{escape(_format_value(check))} / {check.threshold:g} {escape(check.unit)}</text>',
            ]
        )
    svg.append("</svg>")
    path.write_text("\n".join(svg), encoding="utf-8")


def write_outputs(result: AnalysisResult, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metrics.json").write_text(
        json.dumps(_normalize_floats(result.to_dict()), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_markdown_report(result, output_dir / "report.md")
    write_svg_dashboard(result, output_dir / "dashboard.svg")
