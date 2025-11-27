from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Dict, List

try:
    import plotly.graph_objects as go
except Exception as exc:  # pragma: no cover - runtime guard
    raise SystemExit(
        "plotly is required for this script. Install with `pip install plotly`."
    ) from exc


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_FETCH_PATH = ROOT_DIR / "src" / "apis" / "pinnacle-odds" / "data-fetch.py"
PLOTS_DIR = ROOT_DIR / "src" / "visualizations" / "plots"


def load_data_fetch_module():
    """Load the data-fetch module despite the dash in its directory name."""
    spec = importlib.util.spec_from_file_location("pinnacle_data_fetch", DATA_FETCH_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {DATA_FETCH_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["pinnacle_data_fetch"] = module
    spec.loader.exec_module(module)
    return module


def events_to_records(events: Dict[str, Dict]) -> List[Dict[str, str]]:
    """Flatten the events dictionary into a list of rows for plotting."""
    rows: List[Dict[str, str]] = []
    for _, event in events.items():
        periods = event.get("periods", {}).get("num_0", {})
        money_line = periods.get("money_line")
        if not money_line:
            continue
        rows.append(
            {
                "match": f"{event.get('league_name', 'Unknown')} | {event.get('home', '?')} vs {event.get('away', '?')}",
                "home": money_line.get("home"),
                "draw": money_line.get("draw"),
                "away": money_line.get("away"),
            }
        )
    return rows


def implied_prob(odds: float | None) -> float:
    return 0 if odds in (None, 0) else 1 / float(odds)


def plot_records(rows: List[Dict[str, str]], limit: int = 100):
    """Plot the first N events as stacked bars of implied probabilities."""
    if not rows:
        raise ValueError("No odds to visualize.")

    # Sort descending by implied probability of home win.
    rows = sorted(rows, key=lambda r: implied_prob(r.get("home")), reverse=True)[:limit]
    matches = [row["match"] for row in rows]

    home_probs = [implied_prob(row["home"]) for row in rows]
    draw_probs = [implied_prob(row["draw"]) for row in rows]
    away_probs = [implied_prob(row["away"]) for row in rows]

    labels = [m[:80] + ("..." if len(m) > 80 else "") for m in matches]

    fig = go.Figure()
    fig.add_bar(name="Home", x=labels, y=home_probs, marker_color="#4C78A8")
    fig.add_bar(name="Draw", x=labels, y=draw_probs, marker_color="#F2CF5B")
    fig.add_bar(name="Away", x=labels, y=away_probs, marker_color="#E45756")

    fig.update_layout(
        barmode="stack",
        title=f"Pinnacle odds implied probabilities (home-sorted, top {len(rows)})",
        xaxis_title="Match",
        yaxis_title="Implied probability",
        xaxis_tickangle=90,
        yaxis=dict(range=[0, 1.2]),
        legend_title="Outcome",
        height=700,
    )

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PLOTS_DIR / "pinnacle_odds.html"
    fig.write_html(output_path, include_plotlyjs="cdn")
    print(f"Saved interactive plot to {output_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Visualize Pinnacle odds")
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of matches to plot (after filtering). Default: 10",
    )
    args = parser.parse_args()

    data_fetch = load_data_fetch_module()
    events = data_fetch.get_markets(
        data_fetch.FOOTBALL_SPORT_ID,
        prematch=True,
        leagues=data_fetch.MAIN_FOOTBALL_LEAGUE_IDS_SHORT,
        has_odds=True,
    )
    rows = events_to_records(events)
    print(f"Loaded {len(rows)} matches.")

    plot_records(rows, limit=args.limit)


if __name__ == "__main__":
    main()
