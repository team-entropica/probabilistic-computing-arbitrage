"""
Plotly network graph of football betting markets for a single match.
"""

from pathlib import Path
import plotly.graph_objects as go

ROOT_DIR = Path(__file__).resolve().parents[2]
PLOTS_DIR = ROOT_DIR / "src" / "visualizations" / "plots"
DEFAULT_OUTPUT = PLOTS_DIR / "odds_network.html"


NODES = [
    {"id": "HW", "label": "HW", "group": "Match Odds", "x": 0, "y": 3},
    {"id": "D", "label": "D", "group": "Match Odds", "x": 0, "y": 2},
    {"id": "AW", "label": "AW", "group": "Match Odds", "x": 0, "y": 1},
    {"id": "HFH", "label": "HF H", "group": "1st Half Result", "x": 0, "y": -1},
    {"id": "HFD", "label": "HF D", "group": "1st Half Result", "x": 0, "y": -2},
    {"id": "HFA", "label": "HF A", "group": "1st Half Result", "x": 0, "y": -3},
    {"id": "O25", "label": "O2.5", "group": "O/U 2.5", "x": 1, "y": 2.5},
    {"id": "U25", "label": "U2.5", "group": "O/U 2.5", "x": 1, "y": 1.5},
    {"id": "BTTSY", "label": "BTTS Y", "group": "BTTS", "x": 2, "y": 2.5},
    {"id": "BTTSN", "label": "BTTS N", "group": "BTTS", "x": 2, "y": 1.5},
    {"id": "O35", "label": "O3.5", "group": "O/U 3.5", "x": 3, "y": 2.5},
    {"id": "U35", "label": "U3.5", "group": "O/U 3.5", "x": 3, "y": 1.5},
    {"id": "CS10", "label": "1-0", "group": "Correct Score", "x": 4, "y": 2.5},
    {"id": "CS11", "label": "1-1", "group": "Correct Score", "x": 4, "y": 1.5},
    {"id": "AHH", "label": "H-1", "group": "Asian Hcp", "x": 1, "y": -1.5},
    {"id": "AHA", "label": "Opp+1", "group": "Asian Hcp", "x": 1, "y": -2.5},
    {"id": "HTO15", "label": "H>1.5", "group": "Home Goals O/U 1.5", "x": 2, "y": -1.5},
    {"id": "HTU15", "label": "H≤1.5", "group": "Home Goals O/U 1.5", "x": 2, "y": -2.5},
    {"id": "CO45", "label": "C>4.5", "group": "Cards O/U 4.5", "x": 3, "y": -1.5},
    {"id": "CU45", "label": "C≤4.5", "group": "Cards O/U 4.5", "x": 3, "y": -2.5},
    {"id": "CORO", "label": ">9.5", "group": "Corners O/U 9.5", "x": 4, "y": -1.5},
    {"id": "CORU", "label": "≤9.5", "group": "Corners O/U 9.5", "x": 4, "y": -2.5},
]

NODE_INDEX = {n["id"]: i for i, n in enumerate(NODES)}

EDGES = [
    ("HW", "O25", "pos"),
    ("HW", "BTTSY", "pos"),
    ("HW", "O35", "pos"),
    ("O25", "BTTSY", "pos"),
    ("BTTSY", "O35", "pos"),
    ("U25", "BTTSN", "pos"),
    ("U25", "CS10", "pos"),
    ("U35", "CS11", "pos"),
    ("HFH", "HW", "pos"),
    ("CO45", "BTTSY", "pos"),
    ("CORO", "O25", "pos"),
    ("HW", "AW", "neg"),
    ("HW", "D", "neg"),
    ("AW", "D", "neg"),
    ("O25", "U25", "neg"),
    ("O35", "U35", "neg"),
    ("BTTSY", "BTTSN", "neg"),
    ("HTO15", "U25", "neg"),
    ("CO45", "CU45", "neg"),
]


def build_traces():
    x_nodes = [n["x"] for n in NODES]
    y_nodes = [n["y"] for n in NODES]
    labels = [n["label"] for n in NODES]
    groups = [n["group"] for n in NODES]

    edge_pos_x, edge_pos_y = [], []
    edge_neg_x, edge_neg_y = [], []

    for src, dst, kind in EDGES:
        i, j = NODE_INDEX[src], NODE_INDEX[dst]
        x0, y0 = NODES[i]["x"], NODES[i]["y"]
        x1, y1 = NODES[j]["x"], NODES[j]["y"]
        if kind == "pos":
            edge_pos_x += [x0, x1, None]
            edge_pos_y += [y0, y1, None]
        else:
            edge_neg_x += [x0, x1, None]
            edge_neg_y += [y0, y1, None]

    edge_pos_trace = go.Scatter(
        x=edge_pos_x,
        y=edge_pos_y,
        mode="lines",
        line=dict(width=2),
        hoverinfo="none",
        name="Positive correlation",
    )

    edge_neg_trace = go.Scatter(
        x=edge_neg_x,
        y=edge_neg_y,
        mode="lines",
        line=dict(width=2, dash="dot"),
        hoverinfo="none",
        name="Negative / mutually exclusive",
    )

    node_trace = go.Scatter(
        x=x_nodes,
        y=y_nodes,
        mode="markers+text",
        text=labels,
        textposition="middle center",
        marker=dict(size=24, line=dict(width=1, color="black")),
        hovertext=[
            f"{nid}<br>{grp}" for nid, grp in zip([n["id"] for n in NODES], groups)
        ],
        hoverinfo="text",
        name="Bets",
    )

    return edge_pos_trace, edge_neg_trace, node_trace


def build_fig():
    edge_pos_trace, edge_neg_trace, node_trace = build_traces()
    fig = go.Figure(data=[edge_pos_trace, edge_neg_trace, node_trace])
    fig.update_layout(
        title="Correlated Betting Markets for a Single Match",
        showlegend=True,
        legend=dict(x=0.01, y=0.99),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor="white",
        margin=dict(l=20, r=20, t=60, b=20),
    )
    return fig


def main(output_path: Path = DEFAULT_OUTPUT):
    fig = build_fig()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path, include_plotlyjs="cdn")
    print(f"Saved odds network graph to {output_path}")


if __name__ == "__main__":
    main()
