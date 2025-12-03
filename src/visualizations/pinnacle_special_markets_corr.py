from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

try:
    import plotly.graph_objects as go
except Exception as exc:  # pragma: no cover - runtime guard
    raise SystemExit(
        "plotly is required for this script. Install with `pip install plotly`."
    ) from exc


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_WIDE_CSV = ROOT_DIR / "src" / "visualizations" / "plots" / "pinnacle_special_markets_wide.csv"
PLOTS_DIR = ROOT_DIR / "src" / "visualizations" / "plots"
DEFAULT_OUTPUT = PLOTS_DIR / "pinnacle_special_markets_corr_heatmap.html"


def load_wide_csv(path: Path) -> Tuple[List[str], np.ndarray]:
    """
    Load the wide CSV (first column is fetched_at) and return column names and data matrix.
    """
    if not path.exists():
        raise FileNotFoundError(f"Wide CSV not found: {path}")

    columns: List[str] = []
    rows: List[List[float]] = []
    with path.open("r", encoding="utf-8") as f:
        # Skip optional comment/header lines
        first = f.readline()
        if not first.startswith("#"):
            f.seek(0)
        reader = csv.DictReader(f)
        raw_fields = reader.fieldnames or []
        columns = [c for c in raw_fields if c and c != "fetched_at"]
        for record in reader:
            row_vals = []
            for col in columns:
                val = record.get(col, "")
                if val is None or val == "":
                    row_vals.append(np.nan)
                else:
                    try:
                        row_vals.append(float(val))
                    except ValueError:
                        row_vals.append(np.nan)
            rows.append(row_vals)

    if not rows or not columns:
        raise ValueError("No data found in the wide CSV to build correlations.")

    return columns, np.array(rows, dtype=float)


def pairwise_nan_corr(data: np.ndarray) -> np.ndarray:
    """
    Compute pairwise Pearson correlations, skipping NaNs.
    """
    n_cols = data.shape[1]
    corr = np.full((n_cols, n_cols), np.nan)
    for i in range(n_cols):
        for j in range(n_cols):
            col_i = data[:, i]
            col_j = data[:, j]
            mask = ~np.isnan(col_i) & ~np.isnan(col_j)
            if mask.sum() < 2:
                continue
            corr[i, j] = np.corrcoef(col_i[mask], col_j[mask])[0, 1]
    return corr


def select_changing_columns(
    columns: List[str], data: np.ndarray, limit: int = 10
) -> Tuple[List[str], np.ndarray]:
    """
    Keep columns that vary across the timeseries (exclude constant / all-NaN).
    Return up to `limit` columns, prioritizing those with the largest std deviation.
    """
    keep: List[Tuple[float, int]] = []
    for idx, col in enumerate(columns):
        col_data = data[:, idx]
        mask = ~np.isnan(col_data)
        if mask.sum() < 2:
            continue
        vals = col_data[mask]
        if np.allclose(vals, vals[0]):
            continue
        std = np.nanstd(col_data)
        changes = np.count_nonzero(np.diff(vals))
        keep.append((idx, changes, std))

    # sort by changes then std, descending
    keep_sorted = sorted(keep, key=lambda t: (t[1], t[2]), reverse=True)[:limit]
    if not keep_sorted:
        raise ValueError("No varying markets found to plot.")

    selected_indices = [k[0] for k in keep_sorted]
    sel_columns = [columns[i] for i in selected_indices]
    sel_data = data[:, selected_indices]
    return sel_columns, sel_data


def plot_corr(columns: List[str], corr: np.ndarray, output: Path):
    fig = go.Figure(
        data=go.Heatmap(
            z=corr,
            x=columns,
            y=columns,
            colorscale="RdBu",
            zmin=-1,
            zmax=1,
            colorbar=dict(title="Correlation"),
        )
    )
    fig.update_layout(
        title="Special Markets Odds Correlation",
        xaxis_title="Market",
        yaxis_title="Market",
        height=900,
        width=900,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output, include_plotlyjs="cdn")
    print(f"Saved correlation heatmap to {output}")


def main():
    parser = argparse.ArgumentParser(
        description="Compute correlation matrix of special markets wide CSV and plot as heatmap."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_WIDE_CSV,
        help=f"Path to the wide CSV. Default: {DEFAULT_WIDE_CSV}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Path to write the heatmap HTML. Default: {DEFAULT_OUTPUT}",
    )
    args = parser.parse_args()

    columns, data = load_wide_csv(args.input)
    sel_cols, sel_data = select_changing_columns(columns, data, limit=10)
    corr = pairwise_nan_corr(sel_data)
    plot_corr(sel_cols, corr, args.output)


if __name__ == "__main__":
    main()
