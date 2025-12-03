"""
NetworkX + Plotly network graph of the top 10 varying special markets,
with edges weighted/signed by their correlations.
"""

from pathlib import Path
from typing import Dict, List, Tuple
import csv

import networkx as nx
import numpy as np
import plotly.graph_objects as go

ROOT_DIR = Path(__file__).resolve().parents[3]
PLOTS_DIR = ROOT_DIR / "src" / "visualizations" / "plots"
DEFAULT_WIDE_CSV = PLOTS_DIR / "pinnacle_special_markets_wide.csv"
DEFAULT_OUTPUT = PLOTS_DIR / "odds_network.html"


def load_wide_csv(path: Path) -> Tuple[List[str], np.ndarray]:
    if not path.exists():
        raise FileNotFoundError(f"Wide CSV not found: {path}")

    columns: List[str] = []
    rows: List[List[float]] = []
    with path.open("r", encoding="utf-8") as f:
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
        raise ValueError("No data found in the wide CSV.")
    return columns, np.array(rows, dtype=float)


def select_changing_columns(columns: List[str], data: np.ndarray, limit: int = 10):
    keep: List[Tuple[int, int, float]] = []
    for idx, _col in enumerate(columns):
        col_data = data[:, idx]
        mask = ~np.isnan(col_data)
        if mask.sum() < 2:
            continue
        vals = col_data[mask]
        if np.allclose(vals, vals[0]):
            continue
        std = float(np.nanstd(col_data))
        changes = int(np.count_nonzero(np.diff(vals)))
        keep.append((idx, changes, std))

    if not keep:
        raise ValueError("No varying markets found.")

    top = sorted(keep, key=lambda t: (t[1], t[2]), reverse=True)[:limit]
    sel_idx = [t[0] for t in top]
    sel_cols = [columns[i] for i in sel_idx]
    sel_data = data[:, sel_idx]
    return sel_cols, sel_data


def pairwise_nan_corr(data: np.ndarray) -> np.ndarray:
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


def build_graph(cols: List[str], corr: np.ndarray, threshold: float = 0.4) -> nx.Graph:
    g = nx.Graph()
    for col in cols:
        g.add_node(col, label=col)
    n = len(cols)
    for i in range(n):
        for j in range(i + 1, n):
            val = corr[i, j]
            if np.isnan(val) or abs(val) < threshold:
                continue
            g.add_edge(cols[i], cols[j], weight=abs(val), kind="pos" if val > 0 else "neg", corr=val)
    return g


def layout_positions(g: nx.Graph) -> Dict[str, Tuple[float, float]]:
    return nx.spring_layout(g, seed=11, k=1.0, iterations=200)


def build_traces(g: nx.Graph, pos: Dict[str, Tuple[float, float]]):
    edge_pos_x, edge_pos_y = [], []
    edge_neg_x, edge_neg_y = [], []
    edge_pos_hover, edge_neg_hover = [], []

    for u, v, data in g.edges(data=True):
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        corr = data.get("corr", 0)
        hover = f"{u} ↔ {v}<br>corr: {corr:.2f}"
        if data.get("kind") == "pos":
            edge_pos_x += [x0, x1, None]
            edge_pos_y += [y0, y1, None]
            edge_pos_hover.append(hover)
        else:
            edge_neg_x += [x0, x1, None]
            edge_neg_y += [y0, y1, None]
            edge_neg_hover.append(hover)

    edge_pos_trace = go.Scatter(
        x=edge_pos_x,
        y=edge_pos_y,
        mode="lines",
        line=dict(width=2),
        hoverinfo="text",
        text=edge_pos_hover,
        name="Positive correlation",
    )

    edge_neg_trace = go.Scatter(
        x=edge_neg_x,
        y=edge_neg_y,
        mode="lines",
        line=dict(width=2, dash="dot"),
        hoverinfo="text",
        text=edge_neg_hover,
        name="Negative correlation",
    )

    node_x = [pos[node][0] for node in g.nodes()]
    node_y = [pos[node][1] for node in g.nodes()]
    labels = [g.nodes[node]["label"] for node in g.nodes()]

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=[lbl[:16] + ("…" if len(lbl) > 16 else "") for lbl in labels],
        textposition="middle center",
        marker=dict(size=34, line=dict(width=1, color="black")),
        hovertext=[g.nodes[node].get("full_hover", lbl) for node, lbl in zip(g.nodes(), labels)],
        hoverinfo="text",
        name="Markets",
    )

    return edge_pos_trace, edge_neg_trace, node_trace


def build_fig(cols: List[str], corr: np.ndarray):
    g = build_graph(cols, corr)
    if g.number_of_edges() == 0:
        raise ValueError("No edges meet the correlation threshold.")
    pos = layout_positions(g)
    edge_pos_trace, edge_neg_trace, node_trace = build_traces(g, pos)
    fig = go.Figure(data=[edge_pos_trace, edge_neg_trace, node_trace])
    fig.update_layout(
        title="Top Varying Special Markets (Correlation Network)",
        showlegend=True,
        legend=dict(x=0.01, y=0.99),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor="white",
        margin=dict(l=20, r=20, t=60, b=20),
    )
    return fig


def main(input_path: Path = DEFAULT_WIDE_CSV, output_path: Path = DEFAULT_OUTPUT):
    columns, data = load_wide_csv(input_path)
    sel_cols, sel_data = select_changing_columns(columns, data, limit=10)
    corr = pairwise_nan_corr(sel_data)
    fig = build_fig(sel_cols, corr)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path, include_plotlyjs="cdn")
    print(f"Saved odds network graph to {output_path}")


if __name__ == "__main__":
    main()
